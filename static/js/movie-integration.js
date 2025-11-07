// static/js/movie-integration.js
// Manifest-driven poster placement helpers (centered posters, show IMDB + Rotten Tomatoes, use "Dir" label).

(async () => {})();

// Fetch combined movie data
async function fetchMovieCombined(title) {
  const url = `/api/movie?title=${encodeURIComponent(title)}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Movie API returned ${resp.status}`);
  return resp.json();
}

// Robust director extraction helper
function extractDirector(data) {
  if (!data) return null;
  if (data.director && String(data.director).trim()) return String(data.director).trim();
  if (data.omdb && (data.omdb.Director || data.omdb.director)) return data.omdb.Director || data.omdb.director;
  if (data.tmdb && data.tmdb.director) return data.tmdb.director;
  if (data.tmdb && data.tmdb.credits && Array.isArray(data.tmdb.credits.crew)) {
    const dir = data.tmdb.credits.crew.find(c => c.job === 'Director' || c.department === 'Directing');
    if (dir && dir.name) return dir.name;
  }
  if (data.directors && Array.isArray(data.directors) && data.directors.length > 0) return data.directors[0];
  return null;
}

// Extract IMDB and RT ratings from combined data (flexible)
function extractRatings(data) {
  const imdb = data.imdb_rating || (data.omdb && (data.omdb.imdbRating || data.omdb.IMDbRating)) || null;
  // try dedicated fields from API
  const rtTomatometer = data.rt_tomatometer || (data.omdb && data.omdb.RottenTomatoes_Tomatometer) || null;
  const rtAudience = data.rt_audience || (data.omdb && data.omdb.RottenTomatoes_Audience) || null;

  // Some OMDb responses include Ratings array with Source entries
  if ((!rtTomatometer || !rtAudience) && data.omdb && Array.isArray(data.omdb.Ratings)) {
    for (const r of data.omdb.Ratings) {
      if (!rtTomatometer && r.Source && r.Source.toLowerCase().includes('rotten')) rtTomatometer = r.Value;
      if (!imdb && r.Source && r.Source.toLowerCase().includes('imdb')) imdb = r.Value;
    }
  }

  return { imdb: imdb || null, rtTomatometer: rtTomatometer || null, rtAudience: rtAudience || null };
}

// Build poster card (returns DOM element)
function buildPosterCard(title, data) {
  const poster = data.poster || (data.omdb && (data.omdb.Poster || data.omdb.Poster_URL)) || (data.tmdb && data.tmdb.poster_url) || null;
  const { imdb, rtTomatometer, rtAudience } = extractRatings(data);
  const director = extractDirector(data);

  const card = document.createElement('div');
  card.className = 'poster-card';
  card.tabIndex = 0;

  if (poster) {
    const img = document.createElement('img');
    img.src = poster;
    img.alt = `${title} poster`;
    img.className = 'poster-image';
    img.onerror = () => { img.style.display = 'none'; };
    card.appendChild(img);
  } else {
    const placeholder = document.createElement('div');
    placeholder.style.height = '220px';
    placeholder.style.display = 'flex';
    placeholder.style.alignItems = 'center';
    placeholder.style.justifyContent = 'center';
    placeholder.style.color = '#666';
    placeholder.textContent = 'Poster not available';
    card.appendChild(placeholder);
  }

  const meta = document.createElement('div');
  meta.className = 'meta';

  const t = (data.tmdb && data.tmdb.title) || (data.omdb && data.omdb.Title) || title;
  const y = (data.tmdb && data.tmdb.year) || (data.omdb && data.omdb.Year) || '';

  const titleEl = document.createElement('div'); titleEl.className = 'title'; titleEl.textContent = t; meta.appendChild(titleEl);
  if (y) { const yearEl = document.createElement('div'); yearEl.className='year'; yearEl.textContent = y; meta.appendChild(yearEl); }

  // show director as "Dir"
  if (director) { const dirEl = document.createElement('div'); dirEl.className='director'; dirEl.textContent = `Dir: ${director}`; meta.appendChild(dirEl); }

  // show IMDB + Rotten Tomatoes (if available)
  if (imdb || rtTomatometer || rtAudience) {
    const ratingsRow = document.createElement('div');
    ratingsRow.style.marginTop = '6px';
    ratingsRow.style.display = 'flex';
    ratingsRow.style.gap = '8px';
    ratingsRow.style.flexWrap = 'wrap';
    ratingsRow.style.justifyContent = 'center';
    if (imdb) {
      const imdbBadge = document.createElement('div');
      imdbBadge.className = 'rating-badge';
      imdbBadge.textContent = `IMDB: ${imdb}`;
      ratingsRow.appendChild(imdbBadge);
    }
    if (rtTomatometer) {
      const rtBadge = document.createElement('div');
      rtBadge.className = 'rating-badge';
      rtBadge.textContent = `RT: ${rtTomatometer}`;
      ratingsRow.appendChild(rtBadge);
    } else if (rtAudience) {
      const rtBadge = document.createElement('div');
      rtBadge.className = 'rating-badge';
      rtBadge.textContent = `RT-Aud: ${rtAudience}`;
      ratingsRow.appendChild(rtBadge);
    }
    meta.appendChild(ratingsRow);
  }

  if (data.note) { const noteEl = document.createElement('div'); noteEl.style.marginTop='8px'; noteEl.style.color='#b85a00'; noteEl.textContent = data.note; meta.appendChild(noteEl); }

  card.appendChild(meta);
  return card;
}

// parse manifest appended to assistant reply and strip "Ratings" word in the visible text
function parseManifestAndStrip(replyText) {
  if (!replyText || typeof replyText !== 'string') return { manifest: null, assistantText: replyText || '', jsonText: null };
  const twoNewlineIdx = replyText.lastIndexOf('\n\n{');
  let startIdx = -1;
  if (twoNewlineIdx !== -1) startIdx = twoNewlineIdx + 2;
  else startIdx = replyText.lastIndexOf('{');
  if (startIdx === -1) return { manifest: null, assistantText: replyText, jsonText: null };

  const possible = replyText.slice(startIdx);
  try {
    const parsed = JSON.parse(possible);
    if (parsed && Array.isArray(parsed.movies) && parsed.movies.length === 3) {
      let assistantText = replyText.slice(0, startIdx).trim();

      // Remove visible anchor tokens like (anchor:m1) so UI looks clean
      for (const m of parsed.movies) {
        if (m.anchor_id) {
          const tokens = [` (anchor:${m.anchor_id})`, `(anchor:${m.anchor_id})`, ` [anchor:${m.anchor_id}]`, `[anchor:${m.anchor_id}]`];
          for (const t of tokens) assistantText = assistantText.replaceAll(t, '');
        }
      }

      // Remove the redundant word "Ratings" in any header like "* **Ratings:** ..." or "Ratings:"
      assistantText = assistantText.replace(/\*\*\s*Ratings\s*\:\s*\*\*/gi, '');
      assistantText = assistantText.replace(/\*?\s*Ratings\s*:\s*/gi, '');

      return { manifest: parsed, assistantText, jsonText: possible };
    }
  } catch (e) {
    // invalid JSON
  }
  return { manifest: null, assistantText: replyText, jsonText: null };
}

function normalizeForMatch(s) {
  return (s || '').replace(/[\u2018\u2019\u201C\u201D"'`]/g, '').replace(/[^\w\s()\-:]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function findElementForAnchor(agentBubble, anchorText, anchorId) {
  if (!agentBubble) return null;
  if (anchorId) {
    const lit1 = `(anchor:${anchorId})`;
    const lit2 = `[anchor:${anchorId}]`;
    const elByLit = Array.from(agentBubble.querySelectorAll('*')).find(el => (el.textContent || '').includes(lit1) || (el.textContent || '').includes(lit2));
    if (elByLit) return elByLit;
  }
  if (!anchorText) return null;
  const anchorNorm = normalizeForMatch(anchorText);
  const elements = agentBubble.querySelectorAll('*');
  for (const el of elements) {
    const t = (el.textContent || '').trim();
    if (!t) continue;
    if (t.includes(anchorText)) return el;
    if (t.toLowerCase().includes(anchorText.toLowerCase())) return el;
  }
  for (const el of elements) {
    const t = (el.textContent || '').trim();
    if (!t) continue;
    if (normalizeForMatch(t).includes(anchorNorm)) return el;
  }
  const lines = (agentBubble.innerText || '').split('\n').map(l => l.trim()).filter(Boolean);
  for (const line of lines) {
    if (normalizeForMatch(line).includes(anchorNorm)) {
      for (const el of elements) if ((el.textContent || '').trim() === line) return el;
    }
  }
  return null;
}

function appendCollapsedPosterTray(agentBubble, cards) {
  if (!agentBubble || !Array.isArray(cards) || cards.length === 0) return;
  const wrapper = document.createElement('div');
  wrapper.className = 'poster-collapsed-tray';
  const btn = document.createElement('button');
  btn.className = 'poster-tray-btn';
  btn.setAttribute('aria-expanded', 'false');
  btn.textContent = 'Posters ';
  const badge = document.createElement('span');
  badge.className = 'badge';
  badge.textContent = `${cards.length}`;
  badge.style.marginLeft = '6px';
  btn.appendChild(badge);
  const tray = document.createElement('div');
  tray.className = 'poster-row';
  tray.style.display = 'none';
  tray.style.marginTop = '6px';
  for (const c of cards) tray.appendChild(c);
  btn.addEventListener('click', () => {
    const expanded = tray.style.display !== 'none';
    tray.style.display = expanded ? 'none' : 'flex';
    btn.setAttribute('aria-expanded', String(!expanded));
    btn.textContent = expanded ? 'Posters ' : 'Hide posters ';
    const newBadge = document.createElement('span'); newBadge.className = 'badge'; newBadge.textContent = `${cards.length}`; newBadge.style.marginLeft='6px';
    btn.appendChild(newBadge);
  });
  wrapper.appendChild(btn);
  wrapper.appendChild(tray);
  agentBubble.appendChild(wrapper);
  if (typeof chatbox !== 'undefined') chatbox.scrollTop = chatbox.scrollHeight;
}

async function handleAssistantReplyWithManifest(data) {
  const raw = (typeof data.response === 'string') ? data.response : '';
  const { manifest, assistantText } = parseManifestAndStrip(raw);
  const assistantBubble = (typeof addMessage === 'function') ? addMessage('Agent', assistantText || raw || 'No response from AI.') : null;
  if (!manifest) return;
  const unmatched = [];
  for (const m of manifest.movies) {
    if (!m || !m.title) continue;
    const anchor = m.anchor_text || m.title;
    const anchorId = m.anchor_id || null;
    try {
      const movieData = await fetchMovieCombined(m.title);
      const posterUrl = movieData.poster || (movieData.omdb && (movieData.omdb.Poster || movieData.omdb.Poster_URL)) || (movieData.tmdb && movieData.tmdb.poster_url) || null;
      const hasMeta = (movieData.tmdb && movieData.tmdb.title) || (movieData.omdb && movieData.omdb.Title);
      if (!posterUrl && !hasMeta) {
        console.debug('Skipping manifest entry (no poster/metadata):', m.title);
        continue;
      }
      const card = buildPosterCard(m.title, movieData);
      const matchEl = findElementForAnchor(assistantBubble, anchor, anchorId);
      if (matchEl) {
        const wrapper = document.createElement('div'); wrapper.className='poster-row inline-poster-row'; wrapper.style.justifyContent='center'; wrapper.style.marginTop='8px';
        wrapper.appendChild(card);
        matchEl.insertAdjacentElement('afterend', wrapper);
        if (typeof chatbox !== 'undefined') chatbox.scrollTop = chatbox.scrollHeight;
      } else {
        unmatched.push(card);
      }
    } catch (err) {
      console.warn('Failed prefetch/insert for manifest entry', m.title, err);
    }
  }
  if (unmatched.length > 0) appendCollapsedPosterTray(assistantBubble, unmatched);
}

// Exports
window.fetchMovieCombined = fetchMovieCombined;
window.buildPosterCard = buildPosterCard;
window.handleAssistantReplyWithManifest = handleAssistantReplyWithManifest;
window.parseManifestAndStrip = parseManifestAndStrip;