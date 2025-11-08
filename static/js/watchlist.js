// static/js/watchlist.js
// Watchlist modal functionality

(function() {
  'use strict';
  
  // Get modal elements
  const watchlistModal = document.getElementById('watchlist-modal-overlay');
  const watchlistBtn = document.getElementById('watchlist-btn');
  const watchlistCloseBtn = document.getElementById('watchlist-modal-close');
  const watchlistBody = document.getElementById('watchlist-modal-body');
  const watchlistItems = document.getElementById('watchlist-items');
  const watchlistEmpty = document.getElementById('watchlist-empty');
  const watchlistCount = document.getElementById('watchlist-count');
  
  // Open watchlist modal
  function openWatchlistModal() {
    loadWatchlist();
    watchlistModal.classList.add('is-open');
    watchlistModal.setAttribute('aria-hidden', 'false');
  }
  
  // Close watchlist modal
  function closeWatchlistModal() {
    watchlistModal.classList.remove('is-open');
    watchlistModal.setAttribute('aria-hidden', 'true');
  }
  
  // Load watchlist from server
  async function loadWatchlist() {
    try {
      const response = await fetch('/api/watchlist');
      if (!response.ok) throw new Error('Failed to load watchlist');
      
      const data = await response.json();
      if (data.status === 'success') {
        renderWatchlist(data.watchlist);
      }
    } catch (err) {
      console.error('Failed to load watchlist:', err);
      watchlistItems.innerHTML = '<div class="watchlist-empty"><p>Failed to load watchlist. Please try again.</p></div>';
    }
  }
  
  // Render watchlist items
  function renderWatchlist(items) {
    if (!items || items.length === 0) {
      watchlistEmpty.style.display = 'block';
      watchlistItems.innerHTML = '';
      return;
    }
    
    watchlistEmpty.style.display = 'none';
    watchlistItems.innerHTML = '';
    
    items.forEach(item => {
      const itemEl = document.createElement('div');
      itemEl.className = 'watchlist-item';
      
      const posterUrl = item.movie_poster_url || '/static/placeholder-poster.png';
      
      itemEl.innerHTML = `
        <img src="${posterUrl}" alt="${item.movie_title} poster" class="watchlist-item-poster" onerror="this.src='/static/placeholder-poster.png'">
        <div class="watchlist-item-content">
          <div class="watchlist-item-title">${item.movie_title}</div>
          <div class="watchlist-item-meta">
            ${item.movie_year ? item.movie_year : ''}
            ${item.director ? ' • Dir: ' + item.director : ''}
            ${item.imdb_rating ? ' • IMDB: ' + item.imdb_rating : ''}
          </div>
          <div class="watchlist-item-actions">
            <button class="watchlist-remove-btn" data-title="${item.movie_title}">Remove from Watchlist</button>
          </div>
        </div>
      `;
      
      // Add remove button handler
      const removeBtn = itemEl.querySelector('.watchlist-remove-btn');
      removeBtn.addEventListener('click', async () => {
        await removeFromWatchlist(item.movie_title);
        loadWatchlist();
        updateWatchlistCount();
      });
      
      watchlistItems.appendChild(itemEl);
    });
  }
  
  // Remove movie from watchlist
  async function removeFromWatchlist(movieTitle) {
    try {
      const response = await fetch('/api/interaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          movie_title: movieTitle,
          action: 'watchlist',
          value: false
        })
      });
      
      if (!response.ok) throw new Error('Failed to remove from watchlist');
      
      const result = await response.json();
      if (result.status !== 'success') {
        throw new Error('Failed to remove from watchlist');
      }
    } catch (err) {
      console.error('Failed to remove from watchlist:', err);
      alert('Failed to remove movie from watchlist. Please try again.');
    }
  }
  
  // Update watchlist count badge
  async function updateWatchlistCount() {
    try {
      const response = await fetch('/api/watchlist');
      if (!response.ok) return;
      
      const data = await response.json();
      if (data.status === 'success') {
        const count = data.watchlist.length;
        if (count > 0) {
          watchlistCount.textContent = count;
          watchlistCount.style.display = 'inline-block';
        } else {
          watchlistCount.style.display = 'none';
        }
      }
    } catch (err) {
      console.error('Failed to update watchlist count:', err);
    }
  }
  
  // Event listeners
  if (watchlistBtn) {
    watchlistBtn.addEventListener('click', openWatchlistModal);
  }
  
  if (watchlistCloseBtn) {
    watchlistCloseBtn.addEventListener('click', closeWatchlistModal);
  }
  
  if (watchlistModal) {
    watchlistModal.addEventListener('click', (e) => {
      if (e.target === watchlistModal) closeWatchlistModal();
    });
  }
  
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && watchlistModal.classList.contains('is-open')) {
      closeWatchlistModal();
    }
  });
  
  // Initialize watchlist count on page load
  document.addEventListener('DOMContentLoaded', () => {
    updateWatchlistCount();
  });
  
  // Expose functions globally
  window.updateWatchlistCount = updateWatchlistCount;
  window.openWatchlistModal = openWatchlistModal;
  window.closeWatchlistModal = closeWatchlistModal;
})();
