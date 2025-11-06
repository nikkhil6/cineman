// static/js/movie-integration.js
// Fetch combined movie data and display poster + rating in the chat UI.

async function fetchMovieCombined(title) {
  const url = `/api/movie?title=${encodeURIComponent(title)}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Movie API returned ${resp.status}`);
  return resp.json();
}

function buildPosterCard(title, data) {
  const poster =
    data.poster ||
    (data.omdb && data.omdb.Poster_URL) ||
    (data.tmdb && data.tmdb.poster_url) ||
    null;

  const rating = data.rating;
  const ratingSource = data.rating_source;
  const note = data.note;

  const wrapper = document.createElement('div');
  wrapper.className = 'message-container';

  const img = document.createElement('img');
  img.className = 'agent-avatar';
  img.alt = `${title} poster`;
  if (poster) {
    img.src = poster;
  } else {
    img.src = '/static/cineman1.jpg';
  }
  img.onerror = () => { img.style.display = 'none'; };

  const content = document.createElement('div');
  content.className = 'agent-message';

  let html = '';
  const t = (data.tmdb && data.tmdb.title) || (data.omdb && data.omdb.Title) || title;
  const y = (data.tmdb && data.tmdb.year) || (data.omdb && data.omdb.Year) || '';
  html += `<strong>${t}</strong> ${y ? `(${y})` : ''}<br/>`;
  if (rating) html += `<span style="font-weight:600">${ratingSource}:</span> ${rating}<br/>`;
  if (poster) {
    html += `<div style="margin-top:8px;">
               <img src="${poster}" alt="poster" style="width:160px;max-width:40vw;border-radius:6px;box-shadow:0 6px 18px rgba(0,0,0,0.12)">
             </div>`;
  } else {
    html += `<div style="margin-top:8px;color:#666;font-size:0.95rem">Poster not available</div>`;
  }
  if (note) {
    html += `<div style="margin-top:6px;font-size:0.85rem;color:#b85a00">Note: IMDb unavailable; using TMDb score.</div>`;
  }

  content.innerHTML = html;
  wrapper.appendChild(img);
  wrapper.appendChild(content);
  return wrapper;
}

/*
  Integration helper:
  - title: movie title string
  - container: DOM element to append poster card into (#chatbox)
*/
async function fetchAndRenderMovie(title, container = document.getElementById('chatbox')) {
  if (!title || !container) return;
  try {
    const data = await fetchMovieCombined(title);
    const card = buildPosterCard(title, data);
    container.appendChild(card);
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    console.error('fetchAndRenderMovie error:', err);
  }
}