// static/js/movie-integration.js
// Manifest-driven poster UI and modal. v15.3
// - Fix: improved findBestMovieSection to capture the full movie block (not just first paragraph)
// - Keeps robust extraction, modal formatting, compact-summary fallback, and runtime debug from v15.2
// - Exposes helpers on window and stores lastAssistantRaw for debugging

(function () { })();

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
  return String(s).replace(/[&<>"']/g, function (m) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]); });
}

/* ----- Data extraction helpers ----- */
function extractDirector(data) {
  if (!data) return null;
  // Priority 1: New Backend-Enriched field
  if (data.director) return String(data.director).trim();
  // Priority 2: Injected from LLM or other levels
  if (data.omdb && (data.omdb.Director || data.omdb.director)) return data.omdb.Director || data.omdb.director;
  if (data.tmdb && data.tmdb.director) return data.tmdb.director;
  return null;
}

function extractRatings(data) {
  if (!data) return { imdb: null, rt_tomatometer: null, rt_audience: null };

  // Priority 1: New Backend-Enriched ratings object
  if (data.ratings) {
    return {
      imdb: data.ratings.imdb_rating || null,
      rt_tomatometer: data.ratings.rt_tomatometer || null,
      rt_audience: data.ratings.rt_audience || null
    };
  }

  // Priority 2: Legacy fallback
  let imdb = data.imdb_rating || (data.omdb && (data.omdb.imdbRating || data.omdb.IMDb_Rating)) || null;
  let rtTom = data.rt_tomatometer || (data.omdb && (data.omdb.Rotten_Tomatoes || data.omdb.RottenTomatoes_Tomatometer)) || null;
  let rtAud = data.rt_audience || (data.omdb && data.omdb.RottenTomatoes_Audience) || null;

  return { imdb, rt_tomatometer: rtTom, rt_audience: rtAud };
}

/* ----- Manifest parsing (Legacy Fallback) ----- */
function parseManifestAndStrip(replyText) {
  if (!replyText || typeof replyText !== 'string') return { manifest: null, assistantTextClean: replyText || '', assistantTextRaw: '' };
  const possibleIdx = replyText.lastIndexOf('\n\n{');
  let startIdx = (possibleIdx !== -1) ? possibleIdx + 2 : replyText.lastIndexOf('{');
  if (startIdx === -1) return { manifest: null, assistantTextClean: replyText, assistantTextRaw: replyText };
  const possible = replyText.slice(startIdx);
  try {
    const parsed = JSON.parse(possible);
    if (parsed && Array.isArray(parsed.movies)) {
      return { manifest: parsed, assistantTextClean: replyText.slice(0, startIdx).trim(), assistantTextRaw: replyText };
    }
  } catch (e) { }
  return { manifest: null, assistantTextClean: replyText, assistantTextRaw: replyText };
}

// DELETED redundant section parsing and compact summary logic

/* ----- Build flip card DOM ----- */
function buildFlipCard(movie) {
  const flipCard = document.createElement('div');
  flipCard.className = 'flip-card';
  flipCard.tabIndex = 0;

  const inner = document.createElement('div');
  inner.className = 'flip-card-inner';
  flipCard.appendChild(inner);

  const front = document.createElement('div');
  front.className = 'flip-card-face flip-card-front';

  // movie is now assumed to be an enriched object from the backend
  const { imdb, rt_tomatometer, rt_audience } = extractRatings(movie);
  const director = extractDirector(movie);
  const posterUrl = movie.poster_url || null;
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

  // front meta block
  const meta = document.createElement('div');
  meta.className = 'poster-meta';
  const titleEl = document.createElement('div'); titleEl.className = 'title'; titleEl.textContent = movie.title;
  meta.appendChild(titleEl);
  const year = movie.year || '';
  if (year) { const yEl = document.createElement('div'); yEl.className = 'year'; yEl.textContent = year; meta.appendChild(yEl); }
  if (director) { const dEl = document.createElement('div'); dEl.className = 'dir'; dEl.textContent = `Dir: ${director}`; meta.appendChild(dEl); }

  const ratingRow = document.createElement('div');
  ratingRow.style.marginTop = '8px';
  ratingRow.style.display = 'flex';
  ratingRow.style.justifyContent = 'center';
  ratingRow.style.flexWrap = 'wrap';
  ratingRow.style.gap = '8px';

  let hasRatings = false;

  if (imdb) {
    const imdbBadge = document.createElement('div');
    imdbBadge.className = 'rating-badge';
    imdbBadge.textContent = `⭐ ${imdb}`;
    imdbBadge.title = 'IMDB Rating';
    ratingRow.appendChild(imdbBadge);
    hasRatings = true;
  }
  if (rt_tomatometer) {
    const rtBadge = document.createElement('div');
    rtBadge.className = 'rating-badge';
    rtBadge.textContent = `🍅 ${rt_tomatometer}`;
    rtBadge.title = 'Rotten Tomatoes';
    ratingRow.appendChild(rtBadge);
    hasRatings = true;
  }
  else if (rt_audience) {
    const rtBadge = document.createElement('div');
    rtBadge.className = 'rating-badge';
    rtBadge.textContent = `🍅 ${rt_audience}`;
    rtBadge.title = 'Rotten Tomatoes Audience';
    ratingRow.appendChild(rtBadge);
    hasRatings = true;
  }

  // Only append rating row if there are ratings to show
  if (hasRatings) {
    meta.appendChild(ratingRow);
  }

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

  // BACK - full detailed content with poster on left
  const back = document.createElement('div');
  back.className = 'flip-card-face flip-card-back';

  // Create two-column layout container
  const backLayout = document.createElement('div');
  backLayout.style.display = 'flex';
  backLayout.style.gap = '16px';
  backLayout.style.flex = '1';
  backLayout.style.minHeight = '0';
  backLayout.style.minHeight = '0';
  // backLayout.style.overflow = 'hidden'; // Removed to allow dropdowns

  // LEFT COLUMN - Poster
  const leftColumn = document.createElement('div');
  leftColumn.style.flex = '0 0 240px';
  leftColumn.style.display = 'flex';
  leftColumn.style.flexDirection = 'column';

  const backPoster = document.createElement('img');
  backPoster.className = 'back-poster-image';
  backPoster.src = posterUrl || '';
  backPoster.alt = `${movie.title} poster`;
  backPoster.style.width = '100%';
  backPoster.style.borderRadius = '8px';
  backPoster.style.objectFit = 'cover';
  backPoster.style.maxHeight = '360px';
  backPoster.onerror = () => { backPoster.style.display = 'none'; };

  leftColumn.appendChild(backPoster);



  // RIGHT COLUMN - Content
  const rightColumn = document.createElement('div');
  rightColumn.style.flex = '1';
  rightColumn.style.display = 'flex';
  rightColumn.style.flexDirection = 'column';
  rightColumn.style.minHeight = '0';
  rightColumn.style.minHeight = '0';
  // rightColumn.style.overflow = 'hidden'; // Removed to allow dropdowns

  // Add movie title and metadata at the top of right column
  const backHeader = document.createElement('div');
  backHeader.className = 'back-header';
  backHeader.style.marginBottom = '12px';
  backHeader.style.borderBottom = '2px solid #e5e7eb';
  backHeader.style.paddingBottom = '10px';
  backHeader.style.flexShrink = '0';

  // Title row with ratings on the right
  const titleRow = document.createElement('div');
  titleRow.style.display = 'flex';
  titleRow.style.justifyContent = 'space-between';
  titleRow.style.alignItems = 'flex-start';
  titleRow.style.gap = '12px';
  titleRow.style.marginBottom = '4px';

  const backTitle = document.createElement('div');
  backTitle.style.fontWeight = '700';
  backTitle.style.fontSize = '1.15rem';
  backTitle.style.flex = '1';
  backTitle.style.minWidth = '0';
  backTitle.textContent = movie.title;

  const backRatings = document.createElement('div');
  backRatings.style.fontSize = '0.85rem';
  backRatings.style.color = '#374151';
  backRatings.style.fontWeight = '600';
  backRatings.style.display = 'flex';
  backRatings.style.alignItems = 'center';
  backRatings.style.gap = '8px';
  backRatings.style.flexWrap = 'nowrap';
  backRatings.style.flexShrink = '0';
  backRatings.style.whiteSpace = 'nowrap';

  if (imdb) {
    const imdbSpan = document.createElement('span');
    imdbSpan.textContent = `⭐ ${imdb}`;
    imdbSpan.title = `IMDB: ${imdb}`;
    backRatings.appendChild(imdbSpan);
  }
  if (rt_tomatometer) {
    const rtSpan = document.createElement('span');
    rtSpan.textContent = `🍅 ${rt_tomatometer}`;
    rtSpan.title = `Rotten Tomatoes: ${rt_tomatometer}`;
    backRatings.appendChild(rtSpan);
  } else if (rt_audience) {
    const rtSpan = document.createElement('span');
    rtSpan.textContent = `🍅 ${rt_audience}`;
    rtSpan.title = `Rotten Tomatoes Audience: ${rt_audience}`;
    backRatings.appendChild(rtSpan);
  }

  // NEW: Watch Dropdown in Header (Right Side)
  if (movie.streaming && movie.streaming.length > 0) {
    const dropdownContainer = document.createElement('div');
    dropdownContainer.className = 'watch-dropdown-container';

    // Stop propagation on container to prevent card flip or closing
    dropdownContainer.addEventListener('click', (e) => {
      e.stopPropagation();
    });

    const dropBtn = document.createElement('div');
    dropBtn.className = 'watch-dropdown-btn';
    dropBtn.innerHTML = '📺 Watch';

    // Add logic to close other open dropdowns? Maybe simplify to just self-toggle
    const dropMenu = document.createElement('div');
    dropMenu.className = 'watch-dropdown-menu';

    // Populate providers
    movie.streaming.forEach(p => {
      const item = document.createElement('a');
      item.className = 'watch-option';
      const isFree = (p.type || '').toLowerCase() === 'free';

      if (isFree) {
        item.classList.add('free-option');
      }
      item.href = p.url || '#';
      item.target = '_blank';
      item.rel = 'noopener noreferrer';

      if (p.logo_url) {
        const logo = document.createElement('img');
        logo.src = p.logo_url;
        logo.alt = p.name;
        logo.onerror = function () {
          // Replace failed image with fallback icon
          const fallback = document.createElement('span');
          fallback.textContent = '📺';
          fallback.style.fontSize = '20px';
          this.parentNode.replaceChild(fallback, this);
        };
        item.appendChild(logo);
      } else {
        // Fallback icon?
        const fallback = document.createElement('span');
        fallback.textContent = '📺';
        item.appendChild(fallback);
      }

      const nameSpan = document.createElement('span');
      nameSpan.textContent = isFree ? `${p.name} (Free)` : p.name;
      item.appendChild(nameSpan);

      dropMenu.appendChild(item);
    });

    // Toggle logic
    dropBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      // Close any other open menus first
      document.querySelectorAll('.watch-dropdown-menu.show').forEach(m => {
        if (m !== dropMenu) m.classList.remove('show');
      });
      dropMenu.classList.toggle('show');
    });

    // Close when clicking outside - implemented globally or specifically?
    // Let's add a document listener for outside clicks once
    document.addEventListener('click', (e) => {
      if (!dropdownContainer.contains(e.target)) {
        dropMenu.classList.remove('show');
      }
    });

    dropdownContainer.appendChild(dropBtn);
    dropdownContainer.appendChild(dropMenu);

    backRatings.appendChild(dropdownContainer);
  }

  titleRow.appendChild(backTitle);
  // Robust check: append backRatings if it has any children (ratings OR dropdown)
  if (backRatings.hasChildNodes()) {
    titleRow.appendChild(backRatings);
  }

  const backYearDir = document.createElement('div');
  backYearDir.style.color = '#6b7280';
  backYearDir.style.fontSize = '0.85rem';

  backYearDir.textContent = year + (director ? ` • Dir: ${director}` : '');

  backHeader.appendChild(titleRow);
  backHeader.appendChild(backYearDir);
  rightColumn.appendChild(backHeader);

  // Add the structured content
  const backContent = document.createElement('div');
  backContent.className = 'card-back-content';
  backContent.style.flex = '1';
  backContent.style.overflowY = 'auto';
  backContent.style.paddingRight = '8px';
  backContent.style.minHeight = '0';
  backContent.style.overflowX = 'hidden';

  // PRIORITY: Use structured JSON fields if available
  if (movie.quick_pitch || movie.why_matches || movie.award_highlight) {
    let structuredHtml = '';
    if (movie.quick_pitch) {
      structuredHtml += `<h4>The Quick Pitch</h4><p>${escapeHtml(movie.quick_pitch)}</p>`;
    }
    if (movie.why_matches) {
      structuredHtml += `<h4>Why It Matches Your Request</h4><p>${escapeHtml(movie.why_matches)}</p>`;
    }
    if (movie.award_highlight || movie.why_gem) {
      const label = movie.why_gem ? "Why It's a Gem" : "Award & Prestige Highlight";
      structuredHtml += `<h4>${label}</h4><p>${escapeHtml(movie.award_highlight || movie.why_gem)}</p>`;
    }
    backContent.innerHTML = structuredHtml;
  } else {
    backContent.innerHTML = '<div class="small">No summary available.</div>';
  }

  rightColumn.appendChild(backContent);

  // Assemble the layout
  backLayout.appendChild(leftColumn);
  backLayout.appendChild(rightColumn);
  back.appendChild(backLayout);

  // Add action buttons to back side as well
  const backActionButtons = document.createElement('div');
  backActionButtons.className = 'action-buttons';
  backActionButtons.style.marginTop = '12px';
  backActionButtons.style.flexShrink = '0';

  const backLikeBtn = document.createElement('button');
  backLikeBtn.className = 'action-btn like-btn';
  backLikeBtn.innerHTML = '👍';
  backLikeBtn.setAttribute('data-action', 'like');
  backLikeBtn.title = 'Like this movie';

  const backDislikeBtn = document.createElement('button');
  backDislikeBtn.className = 'action-btn dislike-btn';
  backDislikeBtn.innerHTML = '👎';
  backDislikeBtn.setAttribute('data-action', 'dislike');
  backDislikeBtn.title = 'Dislike this movie';

  const backWatchlistBtn = document.createElement('button');
  backWatchlistBtn.className = 'action-btn watchlist-btn';
  backWatchlistBtn.innerHTML = '📋';
  backWatchlistBtn.setAttribute('data-action', 'watchlist');
  backWatchlistBtn.title = 'Add to watchlist';

  backActionButtons.appendChild(backLikeBtn);
  backActionButtons.appendChild(backDislikeBtn);
  backActionButtons.appendChild(backWatchlistBtn);
  back.appendChild(backActionButtons);

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
    if (CI_DEBUG) {
      console.debug('[movie-integration] buildFlipCard:', {
        title: movie.title,
        hasPitch: !!movie.quick_pitch,
        hasWhy: !!movie.why_matches,
        poster: posterUrl ? posterUrl : '<no poster>',
      });
    }
  } catch (e) {
    if (CI_DEBUG) console.warn('[movie-integration] failed to log flipCard debug info', e);
  }

  // Handle action button clicks - sync both front and back buttons
  const handleActionClick = async (action, frontBtn, backBtn) => {
    const isActive = frontBtn.classList.contains('active');
    const newValue = !isActive;

    try {
      const response = await fetch('/api/interaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          movie_title: movie.title,
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
          // Update button states on both front and back
          if (action === 'like') {
            frontBtn.classList.toggle('active', newValue);
            backBtn.classList.toggle('active', newValue);
            if (newValue) {
              dislikeBtn.classList.remove('active');
              backDislikeBtn.classList.remove('active');
            }
          } else if (action === 'dislike') {
            frontBtn.classList.toggle('active', newValue);
            backBtn.classList.toggle('active', newValue);
            if (newValue) {
              likeBtn.classList.remove('active');
              backLikeBtn.classList.remove('active');
            }
          } else if (action === 'watchlist') {
            frontBtn.classList.toggle('active', newValue);
            backBtn.classList.toggle('active', newValue);
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

  // Add click handlers for front buttons
  likeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    handleActionClick('like', likeBtn, backLikeBtn);
  });

  dislikeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    handleActionClick('dislike', dislikeBtn, backDislikeBtn);
  });

  watchlistBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    handleActionClick('watchlist', watchlistBtn, backWatchlistBtn);
  });

  // Add click handlers for back buttons
  backLikeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    handleActionClick('like', likeBtn, backLikeBtn);
  });

  backDislikeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    handleActionClick('dislike', dislikeBtn, backDislikeBtn);
  });

  backWatchlistBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    handleActionClick('watchlist', watchlistBtn, backWatchlistBtn);
  });

  // Load existing interaction state and sync both front and back buttons
  (async () => {
    try {
      const title = movie.title;
      const response = await fetch(`/api/interaction/${encodeURIComponent(title)}`);
      if (response.ok) {
        const result = await response.json();
        if (result.interaction) {
          if (result.interaction.liked) {
            likeBtn.classList.add('active');
            backLikeBtn.classList.add('active');
          }
          if (result.interaction.disliked) {
            dislikeBtn.classList.add('active');
            backDislikeBtn.classList.add('active');
          }
          if (result.interaction.in_watchlist) {
            watchlistBtn.classList.add('active');
            backWatchlistBtn.classList.add('active');
          }
        }
      }
    } catch (err) {
      console.error('Failed to load interaction state:', err);
    }
  })();

  // Click to flip the card or close if already flipped
  flipCard.addEventListener('click', (e) => {
    if (e.target.closest('a') || e.target.closest('.action-btn')) return;

    const posterRow = flipCard.closest('.poster-row');

    // If this card is flipped, ANY click on it should close it
    if (flipCard.classList.contains('is-flipped')) {
      flipCard.classList.remove('is-flipped');
      if (posterRow) {
        posterRow.classList.remove('has-flipped-card');
        document.body.style.overflow = '';
      }
      return;
    }

    // Check if another card is already flipped
    const anyFlipped = posterRow && posterRow.querySelector('.flip-card.is-flipped');

    // If another card is flipped and this isn't it, don't allow flip
    if (anyFlipped) {
      return;
    }

    // Flip this card
    flipCard.classList.add('is-flipped');

    // Toggle backdrop on parent poster-row
    if (posterRow) {
      posterRow.classList.add('has-flipped-card');
      // Prevent scrolling when card is flipped
      document.body.style.overflow = 'hidden';
    }
  });

  // Keyboard navigation
  flipCard.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();

      // Check if another card is already flipped
      const posterRow = flipCard.closest('.poster-row');
      const anyFlipped = posterRow && posterRow.querySelector('.flip-card.is-flipped');

      // If another card is flipped and this isn't it, don't allow flip
      if (anyFlipped && anyFlipped !== flipCard && !flipCard.classList.contains('is-flipped')) {
        return;
      }

      const isFlipped = flipCard.classList.toggle('is-flipped');
      if (posterRow) {
        if (isFlipped) {
          posterRow.classList.add('has-flipped-card');
          document.body.style.overflow = 'hidden';
        } else {
          posterRow.classList.remove('has-flipped-card');
          document.body.style.overflow = '';
        }
      }
    }
    if (e.key === 'Escape') {
      flipCard.classList.remove('is-flipped');
      const posterRow = flipCard.closest('.poster-row');
      if (posterRow) {
        posterRow.classList.remove('has-flipped-card');
        document.body.style.overflow = '';
      }
    }
  });

  // Click backdrop to close
  const handleBackdropClick = (e) => {
    const posterRow = flipCard.closest('.poster-row');
    if (posterRow && posterRow.classList.contains('has-flipped-card')) {
      if (!flipCard.contains(e.target) && e.target !== flipCard) {
        flipCard.classList.remove('is-flipped');
        posterRow.classList.remove('has-flipped-card');
        document.body.style.overflow = '';
      }
    }
  };

  // Add backdrop click handler after a short delay to prevent immediate closing
  setTimeout(() => {
    document.addEventListener('click', handleBackdropClick);
  }, 100);

  // Touch/swipe support for mobile navigation between posters
  let touchStartX = 0;
  let touchStartY = 0;
  let touchEndX = 0;
  let touchEndY = 0;

  flipCard.addEventListener('touchstart', (e) => {
    // Only handle swipes when card is NOT flipped
    if (flipCard.classList.contains('is-flipped')) return;

    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
  }, { passive: true });

  flipCard.addEventListener('touchend', (e) => {
    // Only handle swipes when card is NOT flipped
    if (flipCard.classList.contains('is-flipped')) return;

    touchEndX = e.changedTouches[0].screenX;
    touchEndY = e.changedTouches[0].screenY;

    const deltaX = touchEndX - touchStartX;
    const deltaY = touchEndY - touchStartY;

    // Check if it's a horizontal swipe (more horizontal than vertical)
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
      const posterRow = flipCard.closest('.poster-row');
      if (!posterRow) return;

      const allCards = Array.from(posterRow.querySelectorAll('.flip-card'));
      const currentIndex = allCards.indexOf(flipCard);

      if (deltaX > 0) {
        // Swipe right - go to previous card
        if (currentIndex > 0) {
          allCards[currentIndex - 1].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
      } else {
        // Swipe left - go to next card
        if (currentIndex < allCards.length - 1) {
          allCards[currentIndex + 1].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
      }
    }
  }, { passive: true });

  return flipCard;
}

/* ----- Main handler: Split response into conversation -> posters -> recommendation text ----- */
async function handleAssistantReplyWithManifest(data) {
  // Support both new structured output (response_text + movies) and legacy embedded JSON (response)
  const rawText = data.response_text || data.response || '';

  let manifest = null;
  let assistantTextClean = '';
  let assistantTextRaw = '';

  if (data.movies && Array.isArray(data.movies) && data.movies.length > 0) {
    // New structured path: movies are provided directly
    manifest = { movies: data.movies };
    assistantTextRaw = rawText;
    assistantTextClean = rawText;

    // STRUCTURAL FIX: Robustly strip any anchor tokens (anchor:m1, anchor m2, [anchor:m3], etc)
    const genericAnchorRegex = /[\(\[]?\s*anchor\s*[:\s]\s*m\d+\s*[\)\]]?/gi;
    assistantTextClean = assistantTextClean.replace(genericAnchorRegex, '');

    // Clean ratings headers
    assistantTextClean = assistantTextClean.replace(/\*\*\s*Ratings\s*\:\s*\*\*/gi, '');
    assistantTextClean = assistantTextClean.replace(/\bRatings\s*:\s*/gi, '');

  } else {
    // Legacy path: parse embedded JSON from text
    const result = parseManifestAndStrip(rawText);
    manifest = result.manifest;
    assistantTextClean = result.assistantTextClean;
    assistantTextRaw = result.assistantTextRaw;
  }

  // store for debugging convenience
  window.lastAssistantRaw = assistantTextRaw || '';
  window.lastManifest = manifest || null;
  if (CI_DEBUG) {
    console.debug('[movie-integration] handleAssistantReplyWithManifest invoked', {
      manifest,
      assistantTextClean: assistantTextClean ? assistantTextClean.slice(0, 800) : '',
      assistantTextRaw: assistantTextRaw ? assistantTextRaw.slice(0, 800) : ''
    });
  }

  const chatbox = document.getElementById('chatbox');
  if (!chatbox) {
    if (CI_DEBUG) console.warn('[movie-integration] chatbox element not found');
    return;
  }

  if (!manifest) {
    // no manifest -> just append assistant text and exit
    if (assistantTextClean && typeof window.addMessage === 'function') window.addMessage('Agent', assistantTextClean);
    return;
  }

  // Split response into conversational preface and recommendation details
  // Look for the "### 🍿 CineMan's Curated Recommendation" header or similar
  const recommendationHeaderRegex = /^###?\s*🍿.*?(?:Recommendation|Curated)/mi;
  const match = assistantTextClean.match(recommendationHeaderRegex);

  let conversationalText = '';
  let recommendationText = '';

  if (match && match.index !== undefined) {
    // Split at the recommendation header
    conversationalText = assistantTextClean.slice(0, match.index).trim();
    recommendationText = assistantTextClean.slice(match.index).trim();
  } else {
    // No clear split found, treat first paragraph as conversational if it doesn't contain movie details
    const paragraphs = assistantTextClean.split(/\n\n+/);
    if (paragraphs.length > 1 && !paragraphs[0].includes('Masterpiece') && !paragraphs[0].includes('anchor:')) {
      conversationalText = paragraphs[0].trim();
      recommendationText = paragraphs.slice(1).join('\n\n').trim();
    } else {
      // All is recommendation text
      recommendationText = assistantTextClean;
    }
  }

  // Step 1: Display conversational text first (if any)
  if (conversationalText && typeof window.addMessage === 'function') {
    window.addMessage('Agent', conversationalText);
  }

  // Step 2: After conversational text, append the recommendation text (movie details)
  try {
    if (recommendationText && typeof window.addMessage === 'function') {
      window.addMessage('Agent', recommendationText);
    } else if (recommendationText) {
      const wrap = document.createElement('div');
      wrap.className = 'message-container';
      const bubble = document.createElement('div');
      bubble.className = 'agent-message';
      bubble.innerHTML = window.marked ? marked.parse(recommendationText) : recommendationText;
      wrap.appendChild(bubble);
      chatbox.appendChild(wrap);
    }
  } catch (err) {
    console.warn('Failed to render recommendationText in chat area', err);
  }

  // Step 3: Build and display poster cards directly from manifest metadata
  const posterBubbleWrap = document.createElement('div');
  posterBubbleWrap.className = 'message-container';
  const avatar = document.createElement('img');
  avatar.className = 'agent-avatar';
  avatar.src = '/static/cineman_hero.jpg';
  avatar.alt = 'CineMan';
  avatar.onerror = function () { this.style.display = 'none'; };
  posterBubbleWrap.appendChild(avatar);

  const posterBubble = document.createElement('div');
  posterBubble.className = 'agent-message';

  const posterRow = document.createElement('div');
  posterRow.className = 'poster-row';
  posterBubble.appendChild(posterRow);
  posterBubbleWrap.appendChild(posterBubble);

  chatbox.appendChild(posterBubbleWrap);
  chatbox.scrollTop = chatbox.scrollHeight;

  // Build and display poster cards directly from manifest metadata
  // Optimization: Data is now already enriched by the backend in parallel!
  for (const m of manifest.movies) {
    if (!m || !m.title) continue;

    // The backend now provides poster_url, ratings, and streaming data directly
    const card = buildFlipCard(m);
    posterRow.appendChild(card);
  }

  chatbox.scrollTop = chatbox.scrollHeight;
}

/* ----- Export helpers ----- */
window.fetchMovieCombined = fetchMovieCombined;
window.handleAssistantReplyWithManifest = handleAssistantReplyWithManifest;
window.parseManifestAndStrip = parseManifestAndStrip;
window.buildFlipCard = buildFlipCard;