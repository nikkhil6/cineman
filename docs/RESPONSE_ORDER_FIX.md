# Response Order and Scrolling Fixes

## Issues Addressed

### 1. Response Order Issue
**Problem**: When a user has a conversation and then requests movies, the UI was showing:
- Posters first
- Conversational response text
- Recommendation text

**Expected Behavior**: The correct order should be:
- Conversational response text (e.g., "Great! Based on your preferences...")
- Posters (movie cards)
- Recommendation text (structured movie details)

### 2. Scrolling on Flipped Cards
**Problem**: Text content on flipped poster cards was sometimes clipped without the ability to scroll.

**Expected Behavior**: The flipped card back should have scrollable content when it exceeds the visible area.

## Changes Made

### 1. Response Order Fix (`static/js/movie-integration.js`)

**Modified Function**: `handleAssistantReplyWithManifest()`

**Key Changes**:
- Split the assistant response into two parts:
  - **Conversational text**: Text before the "### 🍿 CineMan's Curated Recommendation" header
  - **Recommendation text**: The structured markdown with movie details

- New display order:
  1. Display conversational text first (if any)
  2. Build and display poster cards
  3. Display recommendation text with movie details

**Code Logic**:
```javascript
// Split response using recommendation header as delimiter
const recommendationHeaderRegex = /^###?\s*🍿.*?(?:Recommendation|Curated)/mi;
const match = assistantTextClean.match(recommendationHeaderRegex);

if (match && match.index !== undefined) {
  conversationalText = assistantTextClean.slice(0, match.index).trim();
  recommendationText = assistantTextClean.slice(match.index).trim();
}

// Display in order:
// 1. Conversational text
if (conversationalText) window.addMessage('Agent', conversationalText);

// 2. Posters
// ... (poster building code)

// 3. Recommendation text
if (recommendationText) window.addMessage('Agent', recommendationText);
```

### 2. Scrolling Fix

**Modified Files**:
- `templates/index.html` - CSS updates
- `static/js/movie-integration.js` - Layout updates

**CSS Changes** (`templates/index.html`):
```css
.flip-card.is-flipped .flip-card-back {
  max-height: 90vh;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}
```

**JavaScript Changes** (`static/js/movie-integration.js`):
- Added `minHeight: '0'` to layout containers to enable proper flex overflow
- Updated `backLayout` and `rightColumn` flex properties
- Ensures content area (`backContent`) has `overflowY: 'auto'` and `flex: '1'`

**How It Works**:
1. The flipped card has a maximum height of 90vh (viewport height)
2. The back face has `overflow-y: auto` to enable vertical scrolling
3. The content area uses flexbox with `flex: 1` and `minHeight: 0` to properly constrain height
4. When content exceeds available space, a scrollbar appears

## Testing

### Manual Testing Steps

1. **Test Response Order**:
   - Start a conversation: "I really enjoy movies with complex plots"
   - Wait for conversational response
   - Request movies: "Now recommend some movies based on what I told you"
   - Verify order: conversational text → posters → recommendation details

2. **Test Scrolling**:
   - Get movie recommendations
   - Click any poster card to flip it
   - Observe the back content
   - If content is long, verify scrollbar appears and scrolling works
   - Test on desktop and mobile

### Expected Results

**Response Order**:
```
User: "I enjoy complex plots"
CineMan: "Excellent taste! Tell me more about your preferences..."

User: "I love Christopher Nolan. Recommend movies"
CineMan: "Perfect! Based on your love for Nolan's style..."
[Poster Cards Appear]
CineMan: "### 🍿 CineMan's Curated Recommendation
         #### 🥇 Masterpiece #1: Arrival (2016)
         ..."
```

**Scrolling**:
- Flipped cards with long content show scrollbar
- Content is fully accessible via scrolling
- No text clipping occurs
- Smooth scrolling behavior

## Browser Compatibility

These changes use standard CSS and JavaScript features supported by all modern browsers:
- Flexbox (CSS)
- CSS `overflow-y: auto`
- JavaScript string manipulation (split, slice, regex)
- DOM manipulation (appendChild, innerHTML)

## Performance Impact

Minimal performance impact:
- Response splitting uses simple regex matching (one-time operation)
- No additional API calls
- DOM operations are batched
- Scrolling is native browser behavior

## Future Enhancements

Possible improvements:
1. Add smooth scroll animation when content is long
2. Add visual indicator when content is scrollable
3. Support custom delimiters for response splitting
4. Add keyboard shortcuts for scrolling (Page Up/Down)
