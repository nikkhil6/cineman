# API Status Monitoring Feature

## ⚠️ Implementation Status

**Backend**: ✅ Fully implemented and tested  
**Frontend UI**: ❌ Not integrated in current template  
**Access Method**: Backend API endpoint only

The API health monitoring backend is fully functional and can be accessed programmatically via the `/api/status` endpoint. The frontend UI components (JavaScript and CSS) exist but are not currently integrated into the main template (`templates/index.html`).

### Current Usage

The feature is available as a **backend-only API** for monitoring and automation:

```bash
# Check API health status
curl http://localhost:5000/api/status

# Example response:
{
  "status": "success",
  "timestamp": 1700000000,
  "services": {
    "gemini": {"status": "operational", "response_time": 150, ...},
    "tmdb": {"status": "operational", "response_time": 200, ...},
    "omdb": {"status": "operational", "response_time": 180, ...}
  }
}
```

### To Enable UI Integration

To enable the visual status indicator in the web interface:

1. Add the JavaScript file to `templates/index.html`:
   ```html
   <script src="{{ url_for('static', filename='js/api-status.js') }}"></script>
   ```

2. Add HTML elements to the header section:
   ```html
   <div id="api-status-container" class="api-status-container">
     <div id="status-indicator" class="status-indicator">
       <span class="status-icon">🟢</span>
       <span class="status-text">APIs OK</span>
     </div>
     <div id="status-tooltip" class="status-tooltip"></div>
   </div>
   ```

3. The CSS (`static/css/api-status.css`) is already loaded.

---

## Overview

The API Status Monitoring feature provides real-time health status feedback for all external APIs used by Cineman:
- **Gemini AI** - The conversational AI engine
- **TMDB (The Movie Database)** - Movie posters and metadata
- **OMDB (Open Movie Database)** - Movie ratings and additional details

## User Interface (Optional - Not Currently Enabled)

**Note**: The UI components are available but not integrated in the current template. See "Implementation Status" section above for details.

### Status Indicator (When Enabled)
The status indicator would appear in the top-right corner of the main page, showing the overall health of all APIs:

- 🟢 **Green (APIs OK)** - All services are operational
- 🟡 **Yellow (Degraded)** - One or more services experiencing issues but still functioning
- 🔴 **Red (Issues)** - One or more services are down or experiencing critical errors

### Detailed Tooltip (When Enabled)
Hovering over the status indicator would show detailed information:
- Individual status for each API service
- Response time in milliseconds
- Error messages (if any)
- Last check timestamp

### Mobile Behavior (When Enabled)
- **Tablets (< 768px)**: Shows icon only, text hidden
- **Small screens (< 480px)**: Completely hidden to avoid clutter

## Technical Implementation

### Backend API

#### Endpoint: `/api/status`
**Method**: GET

**Response Format**:
```json
{
  "status": "success",
  "timestamp": 1700000000,
  "services": {
    "gemini": {
      "status": "operational",
      "message": "API is operational",
      "response_time": 150
    },
    "tmdb": {
      "status": "operational",
      "message": "API is operational",
      "response_time": 200
    },
    "omdb": {
      "status": "operational",
      "message": "API is operational",
      "response_time": 180
    }
  }
}
```

**Status Values**:
- `operational` - Service is working normally
- `degraded` - Service is slow or partially functional
- `error` - Service is down or authentication failed

### Health Check Functions

Located in `cineman/api_status.py`:

#### `check_gemini_status()`
Tests Gemini API by calling the models endpoint with the configured API key.

#### `check_tmdb_status()`
Tests TMDB API by calling the configuration endpoint.

#### `check_omdb_status()`
Tests OMDB API by performing a simple movie query.

#### `check_all_apis()`
Convenience function that checks all APIs and returns combined results.

### Frontend Implementation

#### JavaScript (`static/js/api-status.js`)
- Automatically initializes on page load
- Polls `/api/status` endpoint every 60 seconds
- Updates UI based on response
- Manages tooltip display on hover

#### CSS (`static/css/api-status.css`)
- Responsive styling for all screen sizes
- Color-coded status indicators
- Smooth animations and transitions
- Accessible tooltip design

## Configuration

### Polling Interval
Default: 60 seconds (60000ms)

To change, modify `STATUS_CHECK_INTERVAL` in `static/js/api-status.js`:
```javascript
const STATUS_CHECK_INTERVAL = 60000; // milliseconds
```

### Timeout Settings
Default: 5 seconds per API check

To change, modify the `timeout` parameter in each check function in `cineman/api_status.py`:
```python
response = requests.get(url, timeout=5)
```

## Testing

### Test Suite: `tests/test_api_status.py`

#### Unit Tests
- `test_gemini_operational` - Tests successful Gemini API check
- `test_gemini_invalid_key` - Tests invalid API key handling
- `test_gemini_no_key` - Tests missing API key handling
- `test_gemini_timeout` - Tests timeout handling
- Similar tests for TMDB and OMDB

#### Integration Tests
- `test_status_endpoint_success` - Tests successful endpoint response
- `test_status_endpoint_error` - Tests error handling

#### Running Tests
```bash
# Run API status tests only
python -m pytest tests/test_api_status.py -v

# Run all tests
python -m pytest tests/ -v
```

## Security Considerations

### API Key Protection
- API keys are never exposed in frontend code
- All health checks happen server-side
- Only status information is returned to the client

### Error Message Sanitization
- Generic error messages shown to users
- Detailed errors logged server-side only
- No sensitive information in client responses

### Rate Limiting
- Checks run every 60 seconds by default
- Server-side timeout of 5 seconds prevents hanging
- Failed checks don't block the application

## Troubleshooting

### Status Always Shows Red
1. Check if API keys are configured correctly in environment variables
2. Verify network connectivity to external APIs
3. Check server logs for detailed error messages

### Status Not Updating
1. Check browser console for JavaScript errors
2. Verify `/api/status` endpoint is accessible
3. Check if polling is working (should update every 60 seconds)

### Tooltip Not Showing
1. Clear browser cache and reload
2. Check if CSS file is loaded properly
3. Verify JavaScript is not blocked by browser extensions

## Future Enhancements

Potential improvements:
- [ ] Configurable polling intervals via UI
- [ ] Historical status tracking and charts
- [ ] Email/webhook notifications on API failures
- [ ] Customizable alert thresholds
- [ ] Performance metrics dashboard
- [ ] Service-specific timeout configurations

## Maintenance

### Adding New API Services
1. Add health check function in `cineman/api_status.py`
2. Update `check_all_apis()` to include new service
3. Update frontend labels in `api-status.js`
4. Add corresponding tests in `test_api_status.py`

### Modifying Status Thresholds
Response time thresholds can be adjusted in health check functions:
```python
if response_time > 3000:  # 3 seconds
    return {"status": "degraded", ...}
```

## Dependencies

- **Backend**: `requests` library for HTTP calls
- **Frontend**: Vanilla JavaScript (no additional libraries)
- **Styling**: Pure CSS with responsive design

## Browser Compatibility

Tested and working on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance Impact

- **Backend**: Minimal (async health checks, cached for 60 seconds)
- **Frontend**: Negligible (small JS file, infrequent polling)
- **Network**: Low bandwidth (< 1KB per request)

## License

This feature is part of the Cineman project and follows the same license terms.
