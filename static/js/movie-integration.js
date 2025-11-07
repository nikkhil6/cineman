// static/js/movie-integration.js
// Manifest-driven poster flip-card UI and helpers.
// This file intentionally exposes its main helpers on window so the page script can call them.

(async () => {})();

/* ----- Fetch helpers ----- */
async function fetchMovieCombined(title) {
  const url = `/api/movie?title=${encodeURIComponent(title)}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Movie API returned ${resp.status}`);
  return resp.json();
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

/* ----- Manifest parsing and section extraction ----- */
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

function extractMovieSection(assistantRaw, movieAnchorText, movieAnchorId) {
  if (!assistantRaw) return null;
  let startIdx = -1;
  if (movieAnchorText && assistantRaw.indexOf(movieAnchorText) !== -1) startIdx = assistantRaw.indexOf(movieAnchorText);
  if (startIdx === -1 && movieAnchorId) {
    const token1 = `(anchor:${movieAnchorId})`;
    const token2 = `[anchor:${movieAnchorId}]`;
    startIdx = assistantRaw.indexOf(token1);
    if (startIdx === -1) startIdx = assistantRaw.indexOf(token2);
  }
  if (startIdx === -1 && movieAnchorText) {
    const lower = assistantRaw.toLowerCase();
    const found = lower.indexOf(movieAnchorText.toLowerCase());
    if (found !== -1) startIdx = found;
  }
  if (startIdx === -1) return null;
  const afterHeaderIdx = assistantRaw.indexOf('\n', startIdx);
  let contentStart = afterHeaderIdx !== -1 ? afterHeaderIdx + 1 : startIdx;
  let endIdx = assistantRaw.length;
  const anchorPositions = [];
  const anchorRegex = /\(anchor:([^)]+)\)|\[anchor:([^\]]+)\]|\n####/g;
  let m;
  while ((m = anchorRegex.exec(assistantRaw)) !== null) {
    const pos = m.index;
    if (pos > startIdx) anchorPositions.push(pos);
  }
  if (anchorPositions.length > 0) endIdx = Math.min(...anchorPositions);
  const section = assistantRaw.slice(contentStart, endIdx).trim();
  return section;
}

/* ----- Build flip-card DOM (used by handleAssistantReplyWithManifest) ----- */
function buildFlipCard(movie, movieData, movieMarkdown) {
  const { imdb, rt_tomatometer, rt_audience } = extractRatings(movieData);
  const director = extractDirector(movieData);

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
  const posterUrl = movieData.poster || (movieData.omdb && (movieData.omdb.Poster || movieData.omdb.Poster_URL)) || (movieData.tmdb && movieData.tmdb.poster_url) || null;
  if (posterUrl) {
    const img = document.createElement('img');
    img.className = 'poster-image';
    img.src = posterUrl;
    img.alt = `${movie.title} poster`;
    img.onerror = () => { img.style.display = 'none'; };
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

  const meta = document.createElement('div');
  meta.className = 'poster-meta';
  const titleEl = document.createElement('div');
  titleEl.className = 'title';
  titleEl.textContent = movieData.tmdb?.title || movieData.omdb?.Title || movie.title;
  meta.appendChild(titleEl);
  const year = movieData.tmdb?.year || movieData.omdb?.Year || movie.year || '';
  if (year) {
    const yEl = document.createElement('div');
    yEl.className = 'year';
    yEl.textContent = year;
    meta.appendChild(yEl);
  }
  if (director) {
    const dEl = document.createElement('div');
    dEl.className = 'dir';
    dEl.textContent = `Dir: ${director}`;
    meta.appendChild(dEl);
  }

  const ratingRow = document.createElement('div');
  ratingRow.style.marginTop = '8px';
  ratingRow.style.display = 'flex';
  ratingRow.style.justifyContent = 'center';
  ratingRow.style.flexWrap = 'wrap';
  ratingRow.style.gap = '8px';
  if (imdb) {
    const imdbBadge = document.createElement('div');
    imdbBadge.className = 'rating-badge';
    imdbBadge.textContent = `IMDB: ${imdb}`;
    ratingRow.appendChild(imdbBadge);
  }
  if (rt_tomatometer) {
    const rtBadge = document.createElement('div');
    rtBadge.className = 'rating-badge';
    rtBadge.textContent = `RT: ${rt_tomatometer}`;
    ratingRow.appendChild(rtBadge);
  } else if (rt_audience) {
    const rtBadge = document.createElement('div');
    rtBadge.className = 'rating-badge';
    rtBadge.textContent = `RT-Aud: ${rt_audience}`;
    ratingRow.appendChild(rtBadge);
  }
  meta.appendChild(ratingRow);
  front.appendChild(meta);

  // BACK
  const back = document.createElement('div');
  back.className = 'flip-card-face flip-card-back';
  back.style.overflow = 'auto';
  const backContent = document.createElement('div');
  backContent.className = 'card-back-content';
  backContent.innerHTML = movieMarkdown ? (window.marked ? marked.parse(movieMarkdown) : movieMarkdown) : '<div class="small">No summary available.</div>';
  back.appendChild(backContent);

  inner.appendChild(front);
  inner.appendChild(back);

  // toggles
  function toggleFlip() {
    flipCard.classList.toggle('is-flipped');
  }
  flipCard.addEventListener('click', (e) => {
    if (e.target.closest('a')) return;
    toggleFlip();
  });
  flipCard.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleFlip(); }
    if (e.key === 'Escape') flipCard.classList.remove('is-flipped');
  });

  return flipCard;
}

/* ----- Main: handle assistant reply, build and insert cards ----- */
async function handleAssistantReplyWithManifest(data) {
  const raw = (typeof data.response === 'string') ? data.response : '';
  const { manifest, assistantTextClean, assistantTextRaw } = parseManifestAndStrip(raw);

  const posterArea = document.getElementById('poster-area');
  if (!posterArea) return;
  // clear current cards for each request
  posterArea.innerHTML = '';

  if (!manifest) {
    // fallback: show assistantTextClean in chat area as a message bubble
    if (assistantTextClean) {
      const bubbleWrap = document.createElement('div');
      bubbleWrap.className = 'message-container';
      const bubble = document.createElement('div');
      bubble.className = 'agent-message';
      bubble.innerHTML = window.marked ? marked.parse(assistantTextClean) : assistantTextClean;
      bubbleWrap.appendChild(bubble);
      const chatbox = document.getElementById('chatbox');
      if (chatbox) chatbox.appendChild(bubbleWrap);
    }
    return;
  }

  const unmatchedCards = [];
  for (const m of manifest.movies) {
    if (!m || !m.title) continue;
    const movieSectionMarkdown = extractMovieSection(assistantTextRaw, m.anchor_text, m.anchor_id) || '';
    try {
      const movieData = await fetchMovieCombined(m.title);
      const hasMeta = movieData.tmdb?.title || movieData.omdb?.Title || movieData.poster;
      if (!hasMeta) {
        console.debug('Skipping manifest entry (no poster/metadata):', m.title);
        continue;
      }
      const card = buildFlipCard(m, movieData, movieSectionMarkdown);
      posterArea.appendChild(card);
    } catch (err) {
      console.warn('Failed to fetch/build card:', m.title, err);
      const fallbackCard = document.createElement('div');
      fallbackCard.className = 'poster-card';
      fallbackCard.textContent = m.title;
      unmatchedCards.push(fallbackCard);
    }
  }

  if (unmatchedCards.length > 0) {
    const trayWrapper = document.createElement('div');
    trayWrapper.className = 'poster-collapsed-tray';
    const btn = document.createElement('button'); btn.className = 'poster-tray-btn'; btn.setAttribute('aria-expanded', 'false'); btn.textContent = 'Posters ';
    const badge = document.createElement('span'); badge.className = 'badge'; badge.textContent = `${unmatchedCards.length}`; badge.style.marginLeft = '6px'; btn.appendChild(badge);
    const tray = document.createElement('div'); tray.className = 'poster-row'; tray.style.display = 'none'; tray.style.marginTop = '6px';
    for (const c of unmatchedCards) tray.appendChild(c);
    btn.addEventListener('click', () => {
      const expanded = tray.style.display !== 'none';
      tray.style.display = expanded ? 'none' : 'flex';
      btn.setAttribute('aria-expanded', String(!expanded));
      btn.textContent = expanded ? 'Posters ' : 'Hide posters ';
      const newBadge = document.createElement('span'); newBadge.className = 'badge'; newBadge.textContent = `${unmatchedCards.length}`; newBadge.style.marginLeft = '6px';
      btn.appendChild(newBadge);
    });
    trayWrapper.appendChild(btn); trayWrapper.appendChild(tray);
    posterArea.appendChild(trayWrapper);
  }
}

/* ----- Export to window (ensure globals exist for template) ----- */
window.fetchMovieCombined = fetchMovieCombined;
window.handleAssistantReplyWithManifest = handleAssistantReplyWithManifest;
window.parseManifestAndStrip = parseManifestAndStrip;
window.buildFlipCard = buildFlipCard;