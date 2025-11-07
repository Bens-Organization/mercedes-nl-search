# Railway Backend Deployment Guide

This guide walks you through deploying the FastAPI backend to Railway with staging and production environments.

## Overview

**Architecture:**
- **Project**: Journey AI Mercedes Search (existing)
- **Environments**:
  - `middleware` (existing - for RAG middleware)
  - `staging` (NEW - for backend API staging)
  - `production` (NEW - for backend API production)
- **Services**:
  - `web` (middleware service - already deployed)
  - `backend-api` (NEW - FastAPI backend)

## Prerequisites

- Railway account with CLI installed and authenticated
- Repository: `Bens-Organization/mercedes-nl-search`
- Branch: `feature/railway-backend-migration` → `staging` → `main`

## Step 1: Create Staging Environment

1. Go to your Railway project: https://railway.com/project/5b7b2ee5-6273-4627-96b9-2a310547d63b
2. Click the **environment dropdown** (currently shows "middleware")
3. Click **"+ New Environment"**
4. Name it: `staging`
5. Click **Create**

## Step 2: Create Production Environment

1. In the same environment dropdown
2. Click **"+ New Environment"** again
3. Name it: `production`
4. Click **Create**

## Step 3: Deploy Backend to Staging

1. **Switch to staging environment**:
   - Click environment dropdown → Select `staging`

2. **Create new service**:
   - Click **"+ Create"** button
   - Select **"GitHub Repo"**
   - Choose: `Bens-Organization/mercedes-nl-search`
   - Click **"Add Service"**

3. **Configure service**:
   - Railway will auto-detect the `Dockerfile` in the root
   - Service name will be auto-generated (you can rename to `backend-api`)

4. **Configure deployment branch**:
   - Click on the service card
   - Go to **Settings** tab
   - Under **Source**, set:
     - **Branch**: `staging`
   - Under **Build**, verify:
     - **Builder**: Docker
     - **Dockerfile Path**: `Dockerfile` (auto-detected)

5. **Configure port** (optional - Railway auto-detects):
   - Under **Settings** → **Networking**
   - Railway will automatically assign a public domain
   - The app uses `$PORT` environment variable (Railway provides this)

## Step 4: Configure Environment Variables

### Required Environment Variables

In the `staging` environment for `backend-api` service:

1. Click on the **service card** → **Variables** tab
2. Add the following variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=<your-openai-api-key>
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Typesense Configuration
TYPESENSE_API_KEY=<your-typesense-api-key>
TYPESENSE_HOST=<your-typesense-host>
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https

# Neon Database (for indexing)
NEON_DATABASE_URL=<your-neon-postgres-connection-string>

# Application Configuration
ENVIRONMENT=staging
SERVER_PORT=8000

# Middleware Configuration
MIDDLEWARE_URL=https://web-production-a5d93.up.railway.app
```

### Where to Find These Values

1. **OpenAI API Key**: https://platform.openai.com/api-keys
2. **Typesense credentials**: From your Typesense Cloud dashboard
3. **Neon Database URL**: From your Neon project dashboard
4. **Middleware URL**: Your existing Railway middleware service URL

## Step 5: Deploy

1. **Trigger deployment**:
   - Railway automatically deploys when you push to the `staging` branch
   - Or manually trigger: Click **"Deploy"** in the service card

2. **Monitor deployment**:
   - Click on the service → **Deployments** tab
   - Watch the build logs
   - Should take 2-3 minutes

3. **Get your deployment URL**:
   - Once deployed, go to **Settings** → **Networking**
   - Copy the **Public Domain**
   - Example: `https://backend-api-staging.up.railway.app`

## Step 6: Test Deployment

```bash
# Test health endpoint
curl https://your-backend-url.up.railway.app/health

# Expected response:
{
  "status": "healthy",
  "service": "Mercedes Scientific Search API",
  "environment": "staging"
}

# Test search endpoint
curl -X POST https://your-backend-url.up.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "nitrile gloves", "max_results": 5}'
```

## Step 7: Deploy to Production

Once staging is tested and working:

1. **Switch to production environment**:
   - Click environment dropdown → Select `production`

2. **Create backend service** (same as staging):
   - Click **"+ Create"** → **GitHub Repo**
   - Select: `Bens-Organization/mercedes-nl-search`
   - Configure branch: `main` (not staging!)

3. **Configure environment variables**:
   - Same variables as staging
   - Change `ENVIRONMENT=production`
   - Use production Typesense/Neon if you have separate instances

4. **Deploy and test**

## Step 8: Update Frontend

Update your Vercel frontend environment variables:

### Staging Frontend
```bash
NEXT_PUBLIC_API_URL=https://your-staging-backend.up.railway.app
```

### Production Frontend
```bash
NEXT_PUBLIC_API_URL=https://your-production-backend.up.railway.app
```

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│     Railway Project: Journey AI Mercedes    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │ Environment │  │ Services             │ │
│  ├─────────────┤  ├──────────────────────┤ │
│  │ middleware  │  │ • web (middleware)   │ │
│  │             │  │   Port: 8080         │ │
│  │             │  │   Branch: main       │ │
│  └─────────────┘  └──────────────────────┘ │
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │ staging     │  │ • backend-api        │ │
│  │             │  │   Port: 8000         │ │
│  │             │  │   Branch: staging    │ │
│  └─────────────┘  └──────────────────────┘ │
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │ production  │  │ • backend-api        │ │
│  │             │  │   Port: 8000         │ │
│  │             │  │   Branch: main       │ │
│  └─────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────┘
```

## Git Workflow

```bash
# Work on feature branch
git checkout feature/railway-backend-migration

# Make changes and commit
git add .
git commit -m "Your changes"

# Merge to staging for testing
git checkout staging
git merge feature/railway-backend-migration
git push origin staging
# → Triggers staging deployment

# After testing, merge to main for production
git checkout main
git merge staging
git push origin main
# → Triggers production deployment
```

## Monitoring & Logs

1. **View logs**:
   - Click on service → **Logs** tab
   - Real-time logs from your FastAPI app

2. **Monitor metrics**:
   - Click on service → **Metrics** tab
   - CPU, Memory, Network usage

3. **Check deployments**:
   - Click on service → **Deployments** tab
   - See all deployment history and status

## Troubleshooting

### Build Fails

**Check Dockerfile syntax**:
```bash
docker build -t test-backend .
```

**Check Railway build logs**:
- Go to Deployments tab → Click on failed deployment → View logs

### Service Not Starting

**Check environment variables**:
- Ensure all required variables are set
- Check for typos in variable names

**Check port configuration**:
- Railway provides `$PORT` environment variable
- Dockerfile CMD uses `${PORT:-8000}`

### 502 Bad Gateway

**Service might be unhealthy**:
- Check logs for startup errors
- Verify dependencies are installed
- Check database connections

## Cost Considerations

**Railway Free Tier**:
- $5 credit per month
- Includes execution time and memory
- Monitor usage in project settings

**Typical Usage**:
- Backend API: ~$2-3/month (depending on traffic)
- Middleware: ~$1-2/month (lower traffic)
- **Total**: ~$3-5/month (well within free tier)

## Cleanup (Remove Vercel Backend)

Once Railway backend is confirmed working:

1. **Remove Vercel backend project**:
   - Go to Vercel dashboard
   - Delete the backend project (keep frontend!)

2. **Remove Vercel artifacts from repo**:
   ```bash
   git rm vercel.json api/index.py .vercelignore
   git commit -m "chore: Remove Vercel backend artifacts"
   ```

3. **Update documentation**:
   - Remove Vercel backend references from README
   - Update DEPLOYMENT.md

## Support

- Railway docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Project issues: https://github.com/Bens-Organization/mercedes-nl-search/issues

---

**Last Updated**: 2025-11-07
