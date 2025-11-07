# Railway Backend Migration Status

**Date**: 2025-11-07
**Branch**: `feature/railway-backend-migration`
**Status**: Backend deployed ✅ | Middleware needs fix ⚠️

## What's Been Done

### ✅ Backend Deployment (Working)
- Created `Dockerfile` for FastAPI backend
- Fixed Python module imports with `PYTHONPATH`
- Deployed to Railway staging environment
- Public URL: `https://mercedes-nl-search-staging.up.railway.app`
- Health check: Working ✅
- Search endpoint: Working ✅

### ✅ CORS Configuration
- Fixed wildcard CORS using `allow_origin_regex`
- Pattern: `r"https://.*\.vercel\.app"` matches all Vercel domains
- Includes staging and preview deployments

### ✅ Configuration Cleanup
- Renamed `railway.toml` to `railway.middleware.toml`
- Prevents global Dockerfile config from interfering
- Removed Vercel backend artifacts (vercel.json, api/index.py)

### ✅ Documentation
- Created `docs/RAILWAY_BACKEND_DEPLOYMENT.md`
- Step-by-step deployment guide
- Environment variable configuration
- Troubleshooting section

## Current Issue ⚠️

### Middleware 404 Error

**Problem**: Middleware is returning 404 for `/v1/chat/completions` endpoint

**Evidence from logs** (`scratch/logs/`):
```
[middleware] INFO: "POST /v1/chat/completions HTTP/1.1" 404 Not Found
[backend] 'error': 'Error generating search parameters: Failed to get response from OpenAI: 404'
```

**Impact**:
- Search still works (Typesense falls back to original query)
- BUT: No filter extraction or category detection
- Response shows empty filters: `"filters_applied": ""`

**Root Cause**:
The middleware at `https://web-production-a5d93.up.railway.app` doesn't have the `/v1/chat/completions` endpoint, or the endpoint path is different.

**Likely Fix**:
Check `middleware/openai_middleware.py` or `src/openai_middleware.py` to verify:
1. The endpoint route is correctly defined
2. The middleware is properly deployed
3. The URL in Typesense NL model config is correct

## How Search Currently Works

1. ✅ Frontend → Backend API (Railway)
2. ✅ Backend → Typesense with `nl_query=true`
3. ❌ Typesense → Middleware (404 error)
4. ✅ Typesense → Falls back to original query
5. ✅ Backend → Returns results (without filters)

**Example Response**:
```json
{
  "results": [...],  // ✅ Results returned
  "extracted_query": "available gloves below $50",  // ✅ Query passes through
  "filters_applied": "",  // ❌ Empty (middleware failed)
  "error in middleware": "Failed to get response from OpenAI: 404"
}
```

## Testing Checklist

### Backend Tests (All Passing ✅)
- [x] Health endpoint: `curl https://mercedes-nl-search-staging.up.railway.app/health`
- [x] Search endpoint: `curl -X POST ... /api/search`
- [x] CORS headers: Works with Vercel frontend
- [x] Environment variables: Configured correctly

### Middleware Tests (Failing ❌)
- [ ] Middleware health: `curl https://web-production-a5d93.up.railway.app/health`
- [ ] Chat completions: `curl -X POST ... /v1/chat/completions`
- [ ] Typesense can reach middleware
- [ ] Middleware returns proper OpenAI-compatible response

## Next Steps

1. **Investigate middleware 404**:
   ```bash
   # Check middleware health
   curl https://web-production-a5d93.up.railway.app/health

   # Check available endpoints
   curl https://web-production-a5d93.up.railway.app/
   ```

2. **Verify middleware deployment**:
   - Check Railway middleware service logs
   - Verify it's using `Dockerfile.middleware`
   - Confirm environment variables are set

3. **Fix middleware endpoint**:
   - Check if endpoint exists in middleware code
   - Verify routing configuration
   - Test with direct curl request

4. **Update Typesense NL model** (if middleware URL changed):
   ```python
   python src/setup_middleware_model.py
   ```

5. **Test end-to-end flow**:
   - Frontend search → Backend → Typesense → Middleware → Results
   - Verify filters are extracted correctly
   - Check category detection works

## Files Changed

```
Created:
- Dockerfile                              # Backend container config
- docs/RAILWAY_BACKEND_DEPLOYMENT.md      # Deployment guide
- docs/RAILWAY_MIGRATION_STATUS.md        # This file

Modified:
- src/app.py                              # CORS configuration
- railway.toml → railway.middleware.toml  # Renamed to prevent conflicts

Removed:
- vercel.json                            # Backend config (not needed)
- api/index.py                           # Vercel entry point (not needed)
- .vercelignore                          # Blocking frontend (not needed)
- ignore-build-backend.sh                # Build script (not needed)
```

## Commits in This Branch

```
7d98697 Merge branch 'staging' into feature/railway-backend-migration
3837c17 fix: Add PYTHONPATH to Dockerfile for relative imports
b84327b refactor: Rename railway.toml to avoid global Dockerfile config
6fc2dc0 fix: Use allow_origin_regex for Vercel wildcard CORS
406447e chore: Remove Vercel backend artifacts
720a12d docs: Add comprehensive Railway backend deployment guide
ba4d562 feat: Add Dockerfile for FastAPI backend Railway deployment
```

## Environment Variables Needed

### Backend Service (Railway)
```bash
OPENAI_API_KEY=<your-key>
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
TYPESENSE_API_KEY=<your-key>
TYPESENSE_HOST=<your-host>
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https
NEON_DATABASE_URL=<your-connection-string>
ENVIRONMENT=staging
SERVER_PORT=8000
MIDDLEWARE_URL=https://web-production-a5d93.up.railway.app
```

### Frontend (Vercel)
```bash
NEXT_PUBLIC_API_URL=https://mercedes-nl-search-staging.up.railway.app
```

---

**Summary**: Backend deployment successful ✅, but middleware needs debugging to enable filter extraction and category detection.
