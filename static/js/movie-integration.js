// static/js/movie-integration.js
// Manifest-driven poster UI and modal. v15.3
// - Fix: improved findBestMovieSection to capture the full movie block (not just first paragraph)
// - Keeps robust extraction, modal formatting, compact-summary fallback, and runtime debug from v15.2
// - Exposes helpers on window and stores lastAssistantRaw for debugging

(function(){})();

/* ----- Config ----- */
const CI_DEBUG = false; // set false to silence verbose logs in production

/* ----- Fetch helpers ----- */
async function fetchMovieCombined(title) {
  const url = `/api/movie?title=${encodeURIComponent(title)}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Movie API returned ${resp.status}`);
  return resp.json();
}

/* ----- Utilities ----- */
function normalizeForMatch(s) {
  return (s || '').replace(/[\u2018\u2019\u201C\u201D"'`]/g, '').replace(/[^\w\s()\-:]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
}
function escapeRegex(str) {
  return String(str).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, function (m) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]); });
}

/* ----- Data extraction helpers ----- */
function extractDirector(data) {
  if (!data) return null;
  if (data.director && String(data.director).trim()) return String(data.director).trim();
  if (data.omdb && (data.omdb.Director || data.omdb.director)) return data.omdb.Director || data.omdb.director;
  if (data.tmdb && data.tmdb.director) return data.tmdb.director;
  if (data.tmdb && data.tmdb.credits && Array.isArray(data.tmdb.credits.crew)) {
    const dir = data.tmdb.credits.crew.find(c => c.job === 'Director' || c.department === 'Directing');
    if (dir && dir.name) return dir.name;
  }
  if (Array.isArray(data.directors) && data.directors.length) return data.directors[0];
  return null;
}

function extractRatings(data) {
  let imdb = data.imdb_rating || (data.omdb && (data.omdb.imdbRating || data.omdb.IMDbRating)) || null;
  let rtTom = data.rt_tomatometer || (data.omdb && data.omdb.RottenTomatoes_Tomatometer) || null;
  let rtAud = data.rt_audience || (data.omdb && data.omdb.RottenTomatoes_Audience) || null;

  if ((!rtTom || !imdb) && data.omdb && Array.isArray(data.omdb.Ratings)) {
    for (const r of data.omdb.Ratings) {
      if (!rtTom && /rotten/i.test(r.Source || '')) rtTom = r.Value;
      if (!imdb && /imdb/i.test(r.Source || '')) imdb = r.Value;
    }
  }
  return { imdb: imdb || null, rt_tomatometer: rtTom || null, rt_audience: rtAud || null };
}

/* ----- Manifest parsing ----- */
function parseManifestAndStrip(replyText) {
  if (!replyText || typeof replyText !== 'string') return { manifest: null, assistantTextClean: replyText || '', assistantTextRaw: '' };
  const twoNewlineIdx = replyText.lastIndexOf('\n\n{');
  let startIdx = -1;
  if (twoNewlineIdx !== -1) startIdx = twoNewlineIdx + 2;
  else startIdx = replyText.lastIndexOf('{');
  if (startIdx === -1) return { manifest: null, assistantTextClean: replyText, assistantTextRaw: replyText };
  const possible = replyText.slice(startIdx);
  try {
    const parsed = JSON.parse(possible);
    if (parsed && Array.isArray(parsed.movies) && parsed.movies.length === 3) {
      let assistantRaw = replyText.slice(0, startIdx).trim();
      let assistantClean = assistantRaw;
      for (const m of parsed.movies) {
        if (m.anchor_id) {
          const tokens = [` (anchor:${m.anchor_id})`, `(anchor:${m.anchor_id})`, ` [anchor:${m.anchor_id}]`, `[anchor:${m.anchor_id}]`];
          for (const t of tokens) assistantClean = assistantClean.replaceAll(t, '');
        }
      }
      assistantClean = assistantClean.replace(/\*\*\s*Ratings\s*\:\s*\*\*/gi, '');
      assistantClean = assistantClean.replace(/\bRatings\s*:\s*/gi, '');
      return { manifest: parsed, assistantTextClean: assistantClean, assistantTextRaw: assistantRaw };
    }
  } catch (e) { /* invalid JSON => no manifest */ }
  return { manifest: null, assistantTextClean: replyText, assistantTextRaw: replyText };
}

/* ----- Section parsing & extraction ----- */
function splitAssistantIntoSections(assistantRaw) {
  const sections = [];
  if (!assistantRaw) return sections;
  const lines = assistantRaw.split(/\r?\n/);
  let current = { header: null, content: [] };
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];
    if (/^#{1,6}\s*/.test(ln)) {
      if (current.header || current.content.length) sections.push({ header: current.header, content: current.content.join('\n').trim() });
      current = { header: ln.trim(), content: [] };
      continue;
    }
    if (ln.trim() === '' && current.content.length > 0) {
      if (current.header || current.content.join('\n').trim()) {
        sections.push({ header: current.header, content: current.content.join('\n').trim() });
        current = { header: null, content: [] };
      }
      continue;
    }
    current.content.push(ln);
  }
  if (current.header || current.content.length) sections.push({ header: current.header, content: current.content.join('\n').trim() });
  return sections;
}

/* ----- Helper: compute end index of current movie block (next anchor token or next header) ----- */
function computeBlockEndIndex(assistantRaw, startIdx) {
  const anchorOrHeaderRegex = /\(anchor:([^)]+)\)|\[anchor:([^\]]+)\]|\n####/g;
  let m;
  let end = assistantRaw.length;
  while ((m = anchorOrHeaderRegex.exec(assistantRaw)) !== null) {
    const pos = m.index;
    if (pos > startIdx && pos < end) end = pos;
  }
  return end;
}

function findBestMovieSection(assistantRaw, movie) {
  if (!assistantRaw) return '';

  // Prefer anchor token-based extraction and capture until next anchor or header, not just first paragraph.
  if (movie.anchor_id) {
    const token1 = `(anchor:${movie.anchor_id})`;
    const token2 = `[anchor:${movie.anchor_id}]`;
    let idx = assistantRaw.indexOf(token1);
    if (idx === -1) idx = assistantRaw.indexOf(token2);
    if (idx !== -1) {
      // find start of content after the header line (move to next newline after token)
      let afterHeaderIdx = assistantRaw.indexOf('\n', idx);
      let contentStart = afterHeaderIdx !== -1 ? afterHeaderIdx + 1 : idx;
      // compute end as next anchor/header occurrence (so we capture multiple paragraphs/lines)
      const endIdx = computeBlockEndIndex(assistantRaw, idx);
      const section = assistantRaw.slice(contentStart, endIdx).trim();
      if (section) return section;
      // fallback: try to capture immediate paragraph if above failed
      const m = assistantRaw.slice(contentStart).match(/([\s\S]*?)(?=\r?\n\r?\n|$)/);
      if (m && m[1]) return m[1].trim();
    }
  }

  // Anchor text exact substring: capture until next anchor/header
  if (movie.anchor_text) {
    const idx = assistantRaw.indexOf(movie.anchor_text);
    if (idx !== -1) {
      let afterHeaderIdx = assistantRaw.indexOf('\n', idx);
      let contentStart = afterHeaderIdx !== -1 ? afterHeaderIdx + 1 : idx;
      const endIdx = computeBlockEndIndex(assistantRaw, idx);
      const section = assistantRaw.slice(contentStart, endIdx).trim();
      if (section) return section;
      const m = assistantRaw.slice(contentStart).match(/([\s\S]*?)(?=\r?\n\r?\n|$)/);
      if (m && m[1]) return m[1].trim();
    }
  }

  // Fuzzy header match: use split sections (headers) and prefer the section whose header best matches title
  const sections = splitAssistantIntoSections(assistantRaw);
  const titleNorm = normalizeForMatch(movie.title || movie.anchor_text || '');
  if (titleNorm) {
    for (const s of sections) {
      if (!s.header) continue;
      const headerNorm = normalizeForMatch(s.header);
      if (headerNorm.includes(titleNorm) || titleNorm.includes(headerNorm)) return s.content || '';
      const titleTokens = titleNorm.split(/\s+/).filter(Boolean);
      const overlap = titleTokens.filter(t => headerNorm.includes(t)).length;
      if (overlap >= Math.max(1, Math.floor(titleTokens.length / 2))) return s.content || '';
    }
  }

  // Fallback: find the first paragraph after the title occurrence anywhere in the raw text
  const rawLower = assistantRaw.toLowerCase();
  const tLower = (movie.title || '').toLowerCase();
  if (tLower && rawLower.indexOf(tLower) !== -1) {
    const idx = rawLower.indexOf(tLower);
    const after = assistantRaw.slice(idx);
    const m = after.match(/(?:\r?\n)+([\s\S]*?)(?=\r?\n#{1,6}\s|\r?\n\s*\r?\n|$)/);
    if (m && m[1]) return m[1].trim();
  }

  return '';
}

/* ----- Modal formatter for three labeled sections ----- */
function formatModalContentForThreeSections(rawMarkdown) {
  if (!rawMarkdown) return '<div class="small">No summary available.</div>';
  const text = rawMarkdown.replace(/\r\n/g, '\n');

  const labels = {
    pitch: ['**The Quick Pitch:**', 'The Quick Pitch:', '**The Quick Pitch**:', 'The Quick Pitch'],
    why: ['**Why It Matches Your Request:**', 'Why It Matches Your Request:', '**Why It Matches Your Request**:', 'Why It Matches Your Request'],
    award: ['**Award & Prestige Highlight:**', 'Award & Prestige Highlight:', '**Award & Prestige Highlight**:', 'Award & Prestige Highlight', 'Award & Prestige']
  };

  function findLabelPos(labelVariants, src) {
    for (const v of labelVariants) {
      const i = src.indexOf(v);
      if (i !== -1) return { pos: i, label: v };
    }
    for (const v of labelVariants) {
      const re = new RegExp(escapeRegex(v), 'i');
      const m = re.exec(src);
      if (m) return { pos: m.index, label: m[0] };
    }
    return null;
  }

  const pPos = findLabelPos(labels.pitch, text);
  const wPos = findLabelPos(labels.why, text);
  const aPos = findLabelPos(labels.award, text);

  if (!pPos && !wPos && !aPos) {
    try { return window.marked ? marked.parse(text) : `<pre>${escapeHtml(text)}</pre>`; } catch (e) { return `<pre>${escapeHtml(text)}</pre>`; }
  }

  const found = [];
  if (pPos) found.push({ key: 'pitch', pos: pPos.pos, label: 'The Quick Pitch' });
  if (wPos) found.push({ key: 'why', pos: wPos.pos, label: 'Why It Matches Your Request' });
  if (aPos) found.push({ key: 'award', pos: aPos.pos, label: 'Award & Prestige Highlight' });
  found.sort((a,b) => a.pos - b.pos);

  const sections = {};
  for (let i = 0; i < found.length; i++) {
    const start = found[i].pos;
    const end = (i + 1 < found.length) ? found[i+1].pos : text.length;
    const rawSlice = text.slice(start, end).trim();
    const firstLineEnd = rawSlice.indexOf('\n');
    let content;
    if (firstLineEnd !== -1) {
      content = rawSlice.slice(firstLineEnd + 1).trim();
      if (!content) {
        const labelText = rawSlice.split(/\n/)[0];
        content = rawSlice.slice(labelText.length).trim();
      }
    } else {
      content = rawSlice.replace(/^.*?:\s*/, '').trim();
    }
    sections[found[i].key] = content || '';
  }

  let out = '';
  if (sections.pitch) out += `<h4>The Quick Pitch</h4>${window.marked ? marked.parse(sections.pitch) : '<p>'+escapeHtml(sections.pitch)+'</p>'}\n`;
  if (sections.why) out += `<h4>Why It Matches Your Request</h4>${window.marked ? marked.parse(sections.why) : '<p>'+escapeHtml(sections.why)+'</p>'}\n`;
  if (sections.award) out += `<h4>Award & Prestige Highlight</h4>${window.marked ? marked.parse(sections.award) : '<p>'+escapeHtml(sections.award)+'</p>'}\n`;

  if (!sections.pitch && (sections.why || sections.award)) {
    const remaining = text;
    out = window.marked ? marked.parse(remaining) : '<p>'+escapeHtml(remaining)+'</p>';
  }

  return out || (window.marked ? marked.parse(text) : '<pre>' + escapeHtml(text) + '</pre>');
}

/* ----- Compact summary extractor for card backs ----- */
function extractCompactSummary(movieMarkdown, movieData) {
  // 1) If movieMarkdown looks like HTML, parse and return first <p> text
  try {
    if (typeof movieMarkdown === 'string' && /<\/?[a-z][\s\S]*>/i.test(movieMarkdown)) {
      const parser = new DOMParser();
      const doc = parser.parseFromString(movieMarkdown, 'text/html');
      const p = doc.querySelector('p');
      if (p && p.textContent.trim()) return p.textContent.trim();
      const blocks = Array.from(doc.body.querySelectorAll('h1,h2,h3,h4,div,li'));
      for (const b of blocks) if (b.textContent && b.textContent.trim()) return b.textContent.trim().slice(0,300);
      const text = doc.body.textContent || '';
      if (text.trim()) return text.trim().split(/\n{1,2}/)[0].trim().slice(0,300);
    }
  } catch (e) {
    if (CI_DEBUG) console.warn('extractCompactSummary: HTML parse failed', e);
  }

  // 2) If movieMarkdown is markdown/plain text: return first non-empty paragraph
  if (typeof movieMarkdown === 'string' && movieMarkdown.trim()) {
    const para = movieMarkdown.split(/\r?\n\r?\n/).find(p => p && p.trim().length > 0);
    if (para && para.trim()) return para.trim().slice(0, 300);
    const first = movieMarkdown.trim().replace(/\s+/g,' ').slice(0,300);
    if (first) return first;
  }

  // 3) Fallback to movieData fields
  if (movieData) {
    if (movieData.tmdb && movieData.tmdb.overview) {
      const t = movieData.tmdb.overview.trim();
      if (t) return t.split(/\r?\n\r?\n/)[0].slice(0,300);
    }
    if (movieData.omdb && (movieData.omdb.Plot || movieData.omdb.Plot)) {
      const t = (movieData.omdb.Plot || '').trim();
      if (t) return t.split(/\r?\n\r?\n/)[0].slice(0,300);
    }
    if (movieData.note && String(movieData.note).trim()) return String(movieData.note).trim().slice(0,300);
  }

  return '';
}

/* ----- Build flip card DOM (click opens modal which receives formatted HTML) ----- */
function buildFlipCard(movie, movieData, movieMarkdown) {
  const { imdb, rt_tomatometer, rt_audience } = extractRatings(movieData || {});
  const director = extractDirector(movieData || {});

  const flipCard = document.createElement('div');
  flipCard.className = 'flip-card';
  flipCard.setAttribute('role', 'listitem');
  flipCard.tabIndex = 0;

  const inner = document.createElement('div');
  inner.className = 'flip-card-inner';
  flipCard.appendChild(inner);

  // FRONT
  const front = document.createElement('div');
  front.className = 'flip-card-face flip-card-front';

  const posterUrl = movieData?.poster || (movieData?.omdb && (movieData.omdb.Poster || movieData.omdb.Poster_URL)) || (movieData?.tmdb && movieData.tmdb.poster_url) || null;
  let img = null;
  if (posterUrl) {
    img = document.createElement('img');
    img.className = 'poster-image';
    img.src = posterUrl;
    img.alt = `${movie.title} poster`;
    img.onerror = () => { img.style.display = 'none'; adjustInnerHeight(); };
    front.appendChild(img);
  } else {
    const placeholder = document.createElement('div');
    placeholder.style.height = '220px';
    placeholder.style.display = 'flex';
    placeholder.style.alignItems = 'center';
    placeholder.style.justifyContent = 'center';
    placeholder.style.color = '#666';
    placeholder.textContent = 'Poster not available';
    front.appendChild(placeholder);
  }

  // meta block
  const meta = document.createElement('div');
  meta.className = 'poster-meta';
  const titleEl = document.createElement('div'); titleEl.className = 'title'; titleEl.textContent = movieData?.tmdb?.title || movieData?.omdb?.Title || movie.title;
  meta.appendChild(titleEl);
  const year = movieData?.tmdb?.year || movieData?.omdb?.Year || movie.year || '';
  if (year) { const yEl = document.createElement('div'); yEl.className = 'year'; yEl.textContent = year; meta.appendChild(yEl); }
  if (director) { const dEl = document.createElement('div'); dEl.className = 'dir'; dEl.textContent = `Dir: ${director}`; meta.appendChild(dEl); }

  const ratingRow = document.createElement('div');
  ratingRow.style.marginTop = '8px';
  ratingRow.style.display = 'flex';
  ratingRow.style.justifyContent = 'center';
  ratingRow.style.flexWrap = 'wrap';
  ratingRow.style.gap = '8px';
  if (imdb) { const imdbBadge = document.createElement('div'); imdbBadge.className = 'rating-badge'; imdbBadge.textContent = `IMDB: ${imdb}`; ratingRow.appendChild(imdbBadge); }
  if (rt_tomatometer) { const rtBadge = document.createElement('div'); rtBadge.className = 'rating-badge'; rtBadge.textContent = `RT: ${rt_tomatometer}`; ratingRow.appendChild(rtBadge); }
  else if (rt_audience) { const rtBadge = document.createElement('div'); rtBadge.className = 'rating-badge'; rtBadge.textContent = `RT-Aud: ${rt_audience}`; ratingRow.appendChild(rtBadge); }
  meta.appendChild(ratingRow);
  
  // Action buttons (like, dislike, watchlist)
  const actionButtons = document.createElement('div');
  actionButtons.className = 'action-buttons';
  
  const likeBtn = document.createElement('button');
  likeBtn.className = 'action-btn like-btn';
  likeBtn.innerHTML = '👍';
  likeBtn.setAttribute('data-action', 'like');
  likeBtn.title = 'Like this movie';
  
  const dislikeBtn = document.createElement('button');
  dislikeBtn.className = 'action-btn dislike-btn';
  dislikeBtn.innerHTML = '👎';
  dislikeBtn.setAttribute('data-action', 'dislike');
  dislikeBtn.title = 'Dislike this movie';
  
  const watchlistBtn = document.createElement('button');
  watchlistBtn.className = 'action-btn watchlist-btn';
  watchlistBtn.innerHTML = '📋';
  watchlistBtn.setAttribute('data-action', 'watchlist');
  watchlistBtn.title = 'Add to watchlist';
  
  actionButtons.appendChild(likeBtn);
  actionButtons.appendChild(dislikeBtn);
  actionButtons.appendChild(watchlistBtn);
  meta.appendChild(actionButtons);
  
  front.appendChild(meta);

  // BACK compact summary (single paragraph)
  const back = document.createElement('div');
  back.className = 'flip-card-face flip-card-back';
  const backContent = document.createElement('div');
  backContent.className = 'card-back-content';

  const compact = extractCompactSummary(movieMarkdown, movieData);
  backContent.innerHTML = compact ? (window.marked ? marked.parse(compact) : '<p>'+escapeHtml(compact)+'</p>') : '<div class="small">No summary available.</div>';
  back.appendChild(backContent);

  inner.appendChild(front);
  inner.appendChild(back);

  function adjustInnerHeight() {
    requestAnimationFrame(() => {
      const rect = front.getBoundingClientRect();
      if (rect && rect.height && rect.height > 0) {
        inner.style.minHeight = Math.ceil(rect.height) + 'px';
        back.style.height = inner.style.minHeight;
        front.style.height = inner.style.minHeight;
      }
    });
  }
  if (img) {
    if (img.complete && img.naturalHeight) adjustInnerHeight();
    else { img.addEventListener('load', adjustInnerHeight); img.addEventListener('error', adjustInnerHeight); }
  } else adjustInnerHeight();

  // store debug data on the DOM node and log if debug enabled
  try {
    flipCard.dataset.extracted = (movieMarkdown || '').slice(0, 1000);
    flipCard.dataset.compact = (compact || '').slice(0, 1000);
    if (CI_DEBUG) {
      console.debug('[movie-integration] buildFlipCard:', {
        title: movie.title,
        extractedSnippet: flipCard.dataset.extracted,
        compactSnippet: flipCard.dataset.compact,
        poster: posterUrl ? posterUrl : '<no poster>',
        tmdbTitle: movieData?.tmdb?.title || '',
      });
    }
  } catch (e) {
    if (CI_DEBUG) console.warn('[movie-integration] failed to set dataset on flipCard', e);
  }

  // Handle action button clicks
  const handleActionClick = async (action, button) => {
    const isActive = button.classList.contains('active');
    const newValue = !isActive;
    
    try {
      const response = await fetch('/api/interaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          movie_title: movieData?.tmdb?.title || movieData?.omdb?.Title || movie.title,
          movie_year: year || '',
          movie_poster_url: posterUrl || '',
          director: director || '',
          imdb_rating: imdb || '',
          action: action,
          value: newValue
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          // Update button states
          if (action === 'like') {
            button.classList.toggle('active', newValue);
            if (newValue) dislikeBtn.classList.remove('active');
          } else if (action === 'dislike') {
            button.classList.toggle('active', newValue);
            if (newValue) likeBtn.classList.remove('active');
          } else if (action === 'watchlist') {
            button.classList.toggle('active', newValue);
          }
          
          // Update watchlist count
          if (typeof window.updateWatchlistCount === 'function') {
            window.updateWatchlistCount();
          }
        }
      }
    } catch (err) {
      console.error('Failed to update interaction:', err);
    }
  };
  
  likeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    handleActionClick('like', likeBtn);
  });
  
  dislikeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    handleActionClick('dislike', dislikeBtn);
  });
  
  watchlistBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    handleActionClick('watchlist', watchlistBtn);
  });
  
  // Load existing interaction state
  (async () => {
    try {
      const title = movieData?.tmdb?.title || movieData?.omdb?.Title || movie.title;
      const response = await fetch(`/api/interaction/${encodeURIComponent(title)}`);
      if (response.ok) {
        const result = await response.json();
        if (result.interaction) {
          if (result.interaction.liked) likeBtn.classList.add('active');
          if (result.interaction.disliked) dislikeBtn.classList.add('active');
          if (result.interaction.in_watchlist) watchlistBtn.classList.add('active');
        }
      }
    } catch (err) {
      console.error('Failed to load interaction state:', err);
    }
  })();

  flipCard.addEventListener('click', (e) => {
    if (e.target.closest('a') || e.target.closest('.action-btn')) return;
    const fullHtml = formatModalContentForThreeSections(movieMarkdown || '');
    if (typeof window.openPosterModal === 'function') {
      window.openPosterModal(movie, movieData, fullHtml);
    } else {
      flipCard.classList.toggle('is-flipped');
    }
  });

  flipCard.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      const fullHtml = formatModalContentForThreeSections(movieMarkdown || '');
      if (typeof window.openPosterModal === 'function') window.openPosterModal(movie, movieData, fullHtml);
      else flipCard.classList.toggle('is-flipped');
    }
    if (e.key === 'Escape') flipCard.classList.remove('is-flipped');
  });

  return flipCard;
}

/* ----- Main handler: insert posters as an agent message bubble THEN append assistant text ----- */
async function handleAssistantReplyWithManifest(data) {
  const raw = (typeof data.response === 'string') ? data.response : '';
  const { manifest, assistantTextClean, assistantTextRaw } = parseManifestAndStrip(raw);

  // store for debugging convenience
  window.lastAssistantRaw = assistantTextRaw || '';
  window.lastManifest = manifest || null;
  if (CI_DEBUG) {
    console.debug('[movie-integration] handleAssistantReplyWithManifest invoked', {
      manifest,
      assistantTextClean: assistantTextClean ? assistantTextClean.slice(0,800) : '',
      assistantTextRaw: assistantTextRaw ? assistantTextRaw.slice(0,800) : ''
    });
  }

  const chatbox = document.getElementById('chatbox');
  if (!chatbox) {
    if (CI_DEBUG) console.warn('[movie-integration] chatbox element not found');
    return;
  }

  // build agent poster bubble
  const posterBubbleWrap = document.createElement('div');
  posterBubbleWrap.className = 'message-container';
  const avatar = document.createElement('img');
  avatar.className = 'agent-avatar';
  avatar.src = '/static/cineman_hero.jpg';
  avatar.alt = 'CineMan';
  avatar.onerror = function() { this.style.display = 'none'; };
  posterBubbleWrap.appendChild(avatar);

  const posterBubble = document.createElement('div');
  posterBubble.className = 'agent-message';

  const posterRow = document.createElement('div');
  posterRow.className = 'poster-row';
  posterBubble.appendChild(posterRow);
  posterBubbleWrap.appendChild(posterBubble);

  // append posters bubble so it appears immediately after user's message
  chatbox.appendChild(posterBubbleWrap);
  chatbox.scrollTop = chatbox.scrollHeight;

  if (!manifest) {
    // no manifest -> append assistant text and exit
    if (assistantTextClean && typeof window.addMessage === 'function') window.addMessage('Agent', assistantTextClean);
    return;
  }

  const unmatched = [];
  for (const m of manifest.movies) {
    if (!m || !m.title) continue;
    const movieSectionMarkdown = findBestMovieSection(assistantTextRaw, m) || findBestMovieSection(assistantTextClean, m) || '';
    if (CI_DEBUG) console.debug('[movie-integration] extracted per-movie markdown for', m.title, movieSectionMarkdown ? movieSectionMarkdown.slice(0,300) : '<empty>');
    try {
      const movieData = await fetchMovieCombined(m.title);
      if (CI_DEBUG) console.debug('[movie-integration] fetched movieData for', m.title, { hasPoster: !!movieData.poster, tmdbTitle: movieData.tmdb?.title || null });
      const hasMeta = movieData.tmdb?.title || movieData.omdb?.Title || movieData.poster;
      if (!hasMeta) { if (CI_DEBUG) console.debug('Skipping manifest entry (no poster/metadata):', m.title); continue; }
      const card = buildFlipCard(m, movieData, movieSectionMarkdown);
      try { card.dataset.extracted = (movieSectionMarkdown || '').slice(0, 1000); } catch (e) {}
      posterRow.appendChild(card);
    } catch (err) {
      console.warn('Failed to fetch/build card:', m.title, err);
      const fallbackCard = document.createElement('div');
      fallbackCard.className = 'poster-card';
      fallbackCard.textContent = m.title;
      unmatched.push(fallbackCard);
    }
  }

  if (unmatched.length > 0) {
    const trayWrapper = document.createElement('div');
    trayWrapper.className = 'poster-collapsed-tray';
    const btn = document.createElement('button'); btn.className = 'poster-tray-btn'; btn.setAttribute('aria-expanded', 'false'); btn.textContent = 'Posters ';
    const badge = document.createElement('span'); badge.className = 'badge'; badge.textContent = `${unmatched.length}`; badge.style.marginLeft = '6px'; btn.appendChild(badge);
    const tray = document.createElement('div'); tray.className = 'poster-row'; tray.style.display = 'none'; tray.style.marginTop = '6px';
    for (const c of unmatched) tray.appendChild(c);
    btn.addEventListener('click', () => {
      const expanded = tray.style.display !== 'none';
      tray.style.display = expanded ? 'none' : 'flex';
      btn.setAttribute('aria-expanded', String(!expanded));
      btn.textContent = expanded ? 'Posters ' : 'Hide posters ';
    });
    trayWrapper.appendChild(btn); trayWrapper.appendChild(tray);
    posterRow.appendChild(trayWrapper);
  }

  // After posters are in view, append the assistant's textual reply (ensures posters appear before text)
  try {
    if (assistantTextClean && typeof window.addMessage === 'function') {
      window.addMessage('Agent', assistantTextClean);
    } else if (assistantTextClean) {
      const wrap = document.createElement('div');
      wrap.className = 'message-container';
      const bubble = document.createElement('div');
      bubble.className = 'agent-message';
      bubble.innerHTML = window.marked ? marked.parse(assistantTextClean) : assistantTextClean;
      wrap.appendChild(bubble);
      chatbox.appendChild(wrap);
    }
  } catch (err) {
    console.warn('Failed to render assistantTextClean in chat area', err);
  }

  chatbox.scrollTop = chatbox.scrollHeight;
}

/* ----- Export helpers ----- */
window.fetchMovieCombined = fetchMovieCombined;
window.handleAssistantReplyWithManifest = handleAssistantReplyWithManifest;
window.parseManifestAndStrip = parseManifestAndStrip;
window.buildFlipCard = buildFlipCard;