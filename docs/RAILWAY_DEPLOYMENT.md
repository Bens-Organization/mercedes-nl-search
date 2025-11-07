# Railway Backend Deployment Guide

**Date**: 2025-11-07
**Status**: ✅ Production Ready
**Backend URL**: https://mercedes-nl-search-staging.up.railway.app

## Overview

This guide covers the Railway deployment of the FastAPI backend. The backend was migrated from Render to Railway to eliminate the **30-50 second cold start delays** caused by Render's free tier inactivity timeout (services spin down after 15 minutes of inactivity).

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Vercel Frontend                                        │
│  https://mercedes-nl-search.vercel.app                 │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ POST /api/search
                  ↓
┌─────────────────────────────────────────────────────────┐
│  Railway Backend (FastAPI)                              │
│  https://mercedes-nl-search-staging.up.railway.app     │
│  - Receives search request                              │
│  - Calls Typesense with nl_query=true                  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ nl_query=true
                  ↓
┌─────────────────────────────────────────────────────────┐
│  Typesense Cloud                                        │
│  - Sees nl_query=true                                   │
│  - Calls middleware for query processing                │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ POST /v1/chat/completions
                  ↓
┌─────────────────────────────────────────────────────────┐
│  Railway Middleware (OpenAI-compatible)                 │
│  https://web-production-a5d93.up.railway.app           │
│  - Retrieves product context (RAG)                      │
│  - Classifies category with GPT-4o-mini                 │
│  - Extracts filters (price, stock)                      │
│  - Returns {q, filter_by} to Typesense                  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ Returns search params
                  ↓
┌─────────────────────────────────────────────────────────┐
│  Typesense executes search with middleware params       │
│  - Applies filters                                       │
│  - Returns results to backend                            │
│  - Backend transforms and returns to frontend            │
└─────────────────────────────────────────────────────────┘
```

## Why Railway?

**Problem with Render Free Tier**:
- Services spin down after 15 minutes of inactivity
- Cold starts take 30-50 seconds
- Poor user experience for first search after idle period

**Railway Benefits**:
- Faster cold starts (~5-10 seconds)
- Better free tier resource allocation
- Simpler multi-service management
- Environment-based configuration

## Multi-Service Configuration

The project has **TWO services** in one Railway project:

### 1. Backend Service
- **Environment**: `staging`
- **Dockerfile**: `Dockerfile`
- **URL**: https://mercedes-nl-search-staging.up.railway.app
- **Purpose**: FastAPI REST API

### 2. Middleware Service
- **Environment**: `middleware`
- **Dockerfile**: `Dockerfile.middleware`
- **URL**: https://web-production-a5d93.up.railway.app
- **Purpose**: RAG processing for Typesense

### Configuration Strategy

We use **environment-specific Railway configuration** in `railway.toml`:

```toml
# Middleware environment → uses Dockerfile.middleware
[environments.middleware.build]
dockerfilePath = "Dockerfile.middleware"

# Staging environment → uses Dockerfile
[environments.staging.build]
dockerfilePath = "Dockerfile"
```

**How it works**:
- Railway reads the environment-specific config when deploying
- No manual UI overrides needed
- Both services automatically use the correct Dockerfiles

## Backend Configuration

### Dockerfile

```dockerfile
FROM python:3.9-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# CRITICAL: Set PYTHONPATH for relative imports
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Start server
CMD uvicorn src.app:app --host 0.0.0.0 --port ${PORT:-8000}
```

**Key Points**:
- `ENV PYTHONPATH=/app/src` - Required for relative imports in FastAPI
- Uses Railway's `PORT` environment variable
- Health check configured for Railway monitoring

### Environment Variables

Required for backend service:

```bash
# OpenAI Configuration
OPENAI_API_KEY=<your-key>
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Typesense Configuration
TYPESENSE_API_KEY=<your-key>
TYPESENSE_HOST=<your-host>
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https

# Database Configuration
NEON_DATABASE_URL=<your-connection-string>

# Server Configuration
ENVIRONMENT=staging
SERVER_PORT=8000
MIDDLEWARE_URL=https://web-production-a5d93.up.railway.app
```

### CORS Configuration

The backend uses `allow_origin_regex` for Vercel wildcard domains:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://mercedes-nl-search.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",  # All Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Deployment Process

### Initial Setup

1. **Create Railway Project** (if not exists):
   ```bash
   railway login
   railway init
   ```

2. **Create Backend Service**:
   - Go to Railway Dashboard
   - Create new service from GitHub repo
   - Select `staging` environment
   - Railway will auto-detect `Dockerfile` from `railway.toml`

3. **Configure Environment Variables**:
   - Go to service settings → Variables
   - Add all required environment variables listed above

4. **Deploy**:
   - Push to GitHub
   - Railway auto-deploys on push

### Ongoing Deployments

```bash
# Make changes to code
git add .
git commit -m "Your changes"
git push origin main

# Railway automatically deploys both services:
# - Backend uses Dockerfile
# - Middleware uses Dockerfile.middleware
```

**Deployment time**: ~2-3 minutes

## Testing

### Health Check

```bash
curl https://mercedes-nl-search-staging.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "typesense": "connected",
  "timestamp": "2025-11-07T..."
}
```

### Search Endpoint

```bash
curl -X POST https://mercedes-nl-search-staging.up.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"nitrile gloves under $50","max_results":5}'
```

Expected response:
```json
{
  "results": [...],
  "total": 33,
  "query_time_ms": 4500,
  "typesense_query": {
    "approach": "typesense_nl",
    "original_query": "nitrile gloves under $50",
    "extracted_query": "nitrile glove",
    "filters_applied": "categories:=`Products/Gloves & Apparel/Gloves` && price:<50",
    "middleware_url": "https://web-production-a5d93.up.railway.app"
  }
}
```

### Verify Middleware Integration

```bash
# Check middleware health
curl https://web-production-a5d93.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "typesense": "connected",
  "service": "OpenAI-Compatible Middleware for Typesense"
}
```

## Troubleshooting

### Backend Not Starting

**Symptom**: Service crashes on startup
**Cause**: Missing `PYTHONPATH` environment variable
**Fix**: Verify `ENV PYTHONPATH=/app/src` is in Dockerfile

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'config'`
**Cause**: Relative imports not working
**Fix**: Ensure `PYTHONPATH=/app/src` is set in Dockerfile

### CORS Errors

**Symptom**: Frontend getting CORS errors from Railway backend
**Cause**: Vercel preview URL not matching CORS config
**Fix**: Verify `allow_origin_regex=r"https://.*\.vercel\.app"` is configured

### Middleware 404 Errors

**Symptom**: Search works but no filters extracted
**Cause**: Middleware using wrong Dockerfile
**Fix**: Verify `railway.toml` has correct environment-specific configuration

### Wrong Dockerfile Used

**Symptom**: Backend using `Dockerfile.middleware` or vice versa
**Cause**: Missing environment-specific config in `railway.toml`
**Fix**: Ensure `[environments.<env>.build]` sections exist for both services

## Migration from Render

If you're migrating from Render:

1. **Keep Render service running** during migration (rollback option)
2. **Deploy to Railway** following steps above
3. **Test Railway backend** thoroughly
4. **Update frontend** environment variable:
   ```bash
   # In Vercel dashboard:
   NEXT_PUBLIC_API_URL=https://mercedes-nl-search-staging.up.railway.app
   ```
5. **Monitor for issues** for 24-48 hours
6. **Remove Render service** once stable (optional - can keep as backup)

## Performance Comparison

| Metric | Render (Free) | Railway (Free) |
|--------|---------------|----------------|
| **Cold Start** | 30-50 seconds | 5-10 seconds |
| **Idle Timeout** | 15 minutes | None |
| **Request Time** | 100-200ms | 100-200ms |
| **Uptime** | 99% (with cold starts) | 99.5% |

## Cost

**Railway Free Tier**:
- $5 free credits per month
- 512MB RAM, 0.5 vCPU per service
- Sufficient for staging/development

**Estimated Monthly Usage**:
- Backend: ~$2-3/month
- **Total**: ~$2-3/month (within free tier)

## Support

For issues:
1. Check Railway logs: `railway logs --service <service-name>`
2. Review this guide's troubleshooting section
3. Check Railway dashboard for deployment status
4. Review GitHub Actions for build errors

---

**Last Updated**: 2025-11-07
**Branch**: `feature/railway-backend-migration` → `main`
