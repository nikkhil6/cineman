# Troubleshooting

Common issues and solutions for Cineman.

## Installation Issues

### Dependencies Not Found

**Symptom:** Import errors or module not found

**Solution:**
```bash
# Verify dependencies
python scripts/verify_dependencies.py

# Reinstall
pip install -r requirements.txt

# If issues persist, upgrade pip
pip install --upgrade pip
pip install -r requirements.txt
```

### Virtual Environment Issues

**Symptom:** Wrong Python version or packages not isolated

**Solution:**
```bash
# Remove old environment
rm -rf venv

# Create fresh environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## API Key Issues

### GEMINI_API_KEY Not Set

**Error:** `GEMINI_API_KEY environment variable is not set`

**Solution:**
1. Create `.env` file with your key
2. Or export in terminal: `export GEMINI_API_KEY='your_key'`
3. Verify with: `echo $GEMINI_API_KEY`

See [API Keys](API-Keys.md) for detailed setup.

### Invalid or Expired API Keys

**Symptoms:**
- 401 Unauthorized errors
- API calls failing
- Authentication errors

**Solution:**
1. Verify keys are copied correctly (no spaces)
2. Check key hasn't been revoked
3. Generate new keys if needed
4. Ensure using correct API version (TMDB v3, not v4)

### Rate Limiting

**Error:** Too many requests or API limit exceeded

**Solution:**
- OMDb: Free tier is 1,000 requests/day
- TMDB: 40 requests per 10 seconds
- Wait for reset or upgrade to paid tier
- Implement caching in future updates

## Application Issues

### Flask App Won't Start

**Error:** Address already in use or startup failures

**Solution:**
```bash
# Check if port 5000 is in use
lsof -i :5000  # Mac/Linux
netstat -ano | findstr :5000  # Windows

# Kill process using port
kill -9 <PID>  # Mac/Linux

# Or run on different port
# Modify run.py: app.run(port=5001)
```

### Template Not Found Error

**Error:** `TemplateNotFound: index.html`

**Solution:**
1. Verify `templates/` directory exists
2. Check `index.html` is in templates folder
3. Run from project root: `python run.py`
4. Don't run from subdirectories

### Chain Initialization Failed

**Error:** "Failed to load AI Chain"

**Solutions:**
1. Check GEMINI_API_KEY is set
2. Verify internet connection
3. Check prompt file exists: `prompts/cineman_system_prompt.txt`
4. Review error message for specific issue

## Runtime Issues

### AI Responses Taking Too Long

**Symptom:** Timeout or very slow responses

**Solutions:**
- Check internet connection speed
- Verify Gemini API status
- Consider reducing temperature in `chain.py`
- Check if hitting API rate limits

### No Movie Results

**Symptom:** AI can't find movie information

**Solutions:**
- Verify TMDB/OMDb keys are configured
- Check movie title spelling
- Try alternative movie titles
- Check API service status pages

### Chat Interface Not Responding

**Solutions:**
1. Open browser console (F12) for errors
2. Check Flask server logs
3. Verify `/chat` endpoint is accessible
4. Test with curl:
```bash
curl -X POST http://127.0.0.1:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}'
```

## Testing Issues

### Tests Failing

**Solution:**
```bash
# Ensure in virtual environment
source venv/bin/activate

# Check API keys are set
python tests/test_tmdb.py
python tests/test_omdb.py

# Run with verbose output
python -v tests/test_tmdb.py
```

### Import Errors in Tests

**Solution:**
```bash
# Run tests as modules from project root
cd /path/to/cineman
python -m tests.test_tmdb
python -m tests.test_omdb
```

## Deployment Issues

### Render Deployment Failing

**Common causes:**
- Missing environment variables
- Wrong Python version
- Missing dependencies

**Solution:**
1. Check Render dashboard logs
2. Verify all API keys are set in Render
3. Ensure `requirements.txt` is complete
4. Check `render.yaml` configuration

### Health Check Failing

**Solution:**
- Verify `/health` endpoint responds
- Check application is fully started
- Review Render logs for errors

## Performance Issues

### High Memory Usage

**Solutions:**
- Restart application periodically
- Implement response caching
- Monitor Gemini API usage

### Slow Response Times

**Solutions:**
- Check network latency
- Verify API service performance
- Consider using faster Gemini model
- Implement timeout handling

## Getting More Help

If problems persist:

1. **Check Logs:**
   - Flask console output
   - Browser console (F12)
   - Deployment platform logs

2. **Verify Setup:**
   - Run `python scripts/verify_dependencies.py`
   - Check all [API Keys](API-Keys.md)
   - Review [Getting Started](Getting-Started.md)

3. **Debug Mode:**
   ```python
   # In run.py or app.py
   app.run(debug=True)  # Shows detailed errors
   ```

4. **Community Support:**
   - Open GitHub issue with error details
   - Include version information
   - Provide minimal reproduction steps

## Quick Diagnostic Checklist

Run through this checklist:

- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip list`)
- [ ] API keys configured and valid
- [ ] Running from project root directory
- [ ] Port 5000 available
- [ ] Internet connection working
- [ ] Python 3.8+ installed
- [ ] Prompt file exists in `prompts/`
- [ ] Templates directory contains `index.html`
