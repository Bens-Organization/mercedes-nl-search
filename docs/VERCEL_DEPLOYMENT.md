# Vercel Backend Deployment Guide

This guide walks you through deploying the FastAPI backend to Vercel to eliminate cold start delays.

## Why Vercel?

- ✅ **No cold starts** - Instant serverless function execution
- ✅ **Free tier** - 100GB bandwidth, unlimited requests
- ✅ **Same platform** as frontend - Simpler deployment, faster response times
- ✅ **Edge Network** - Global CDN for low latency

## Current vs New Architecture

```
BEFORE (Render + Railway):
Frontend (Vercel) → Backend (Render - 30-50s cold starts!) → Middleware (Railway)

AFTER (Vercel + Railway):
Frontend (Vercel) → Backend (Vercel - instant!) → Middleware (Railway)
```

## Prerequisites

- Vercel account (free tier: https://vercel.com/signup)
- Project pushed to GitHub
- Environment variables ready (from `.env` file)

## Step 1: Install Vercel CLI (Optional)

You can deploy via Vercel Dashboard (easier) or CLI (more control).

### Option A: Dashboard Only (Recommended for First Deploy)
Skip to Step 2.

### Option B: CLI Deployment
```bash
# Install Vercel CLI globally
npm install -g vercel

# Login to Vercel
vercel login

# Deploy (follow prompts)
vercel
```

## Step 2: Deploy Backend via Vercel Dashboard

### 2.1 Import Project

1. Go to https://vercel.com/new
2. Click **"Import Git Repository"**
3. Select your GitHub repository: `mercedes-nl-search`
4. Click **"Import"**

### 2.2 Configure Project

**Project Settings:**
- **Framework Preset**: Other
- **Root Directory**: `.` (leave as default)
- **Build Command**: Leave empty
- **Output Directory**: Leave empty

Click **"Continue"**

### 2.3 Add Environment Variables

Click **"Environment Variables"** section and add these:

| Variable | Value | Source |
|----------|-------|--------|
| `OPENAI_API_KEY` | `sk-...` | From your `.env` file |
| `TYPESENSE_HOST` | `xxx.a1.typesense.net` | From your `.env` file |
| `TYPESENSE_PORT` | `443` | From your `.env` file |
| `TYPESENSE_PROTOCOL` | `https` | From your `.env` file |
| `TYPESENSE_API_KEY` | `xyz...` | From your `.env` file |
| `OPENAI_MODEL` | `gpt-4o-mini-2024-07-18` | From your `.env` file |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | From your `.env` file |
| `ENVIRONMENT` | `production` | Set to `production` |

**Important Notes:**
- ✅ Make sure all values are **exactly** as they appear in your `.env` file
- ✅ No quotes needed in Vercel UI (they're automatically handled)
- ✅ Apply to **Production** environment

### 2.4 Deploy

1. Click **"Deploy"**
2. Wait 2-3 minutes for deployment (first deploy takes longer)
3. You'll see a success screen with your backend URL

**Your backend URL will be**: `https://your-project-name.vercel.app`

### 2.5 Test Backend Deployment

Open your browser or use curl:

```bash
# Test health endpoint
curl https://your-project-name.vercel.app/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "api": "ok",
    "typesense": "ok"
  }
}

# Test search endpoint
curl -X POST https://your-project-name.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gloves"}'
```

## Step 3: Update Frontend Configuration

Now that your backend is deployed, update the frontend to use the new Vercel backend URL.

### 3.1 Update Frontend Environment Variables

**Option A: Vercel Dashboard (Recommended)**

1. Go to your frontend project in Vercel: https://vercel.com/dashboard
2. Click your frontend project (e.g., `mercedes-nl-search`)
3. Go to **Settings** → **Environment Variables**
4. Find `NEXT_PUBLIC_API_URL` (or add it if missing)
5. Update value to: `https://your-backend-project-name.vercel.app`
6. Click **"Save"**
7. Go to **Deployments** tab
8. Click **"..."** menu on latest deployment → **"Redeploy"**

**Option B: Update Code (for local testing)**

Edit `frontend-next/.env.local` (create if doesn't exist):

```bash
# Vercel backend URL
NEXT_PUBLIC_API_URL=https://your-backend-project-name.vercel.app
```

### 3.2 Test Frontend

1. Open your frontend: https://mercedes-nl-search.vercel.app
2. Try a search query: "nitrile gloves under $50"
3. Check response time (should be 2-4 seconds, not 30-50 seconds!)

## Step 4: Verify Everything Works

### 4.1 Check Response Times

```bash
# Test backend health (should be < 2 seconds)
time curl https://your-backend-project-name.vercel.app/health

# Test search (should be 2-4 seconds)
time curl -X POST https://your-backend-project-name.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gloves"}'
```

### 4.2 Test Multiple Queries

Try these queries in your frontend:
- "sterile gloves under $50"
- "pipettes in stock"
- "lab coats size large"

Expected behavior:
- ✅ First query: 2-4 seconds (no cold start!)
- ✅ Subsequent queries: 2-4 seconds (consistent)
- ✅ No 30-50 second delays

## Step 5: Update UptimeRobot (Optional)

If you previously set up UptimeRobot to ping Render, update it:

1. Go to https://uptimerobot.com
2. Edit your monitor for the backend
3. Update URL to: `https://your-backend-project-name.vercel.app/health`
4. Save

**Note**: With Vercel serverless functions, UptimeRobot is less critical (no cold starts), but it's still useful for monitoring uptime.

## Architecture After Migration

```
┌─────────────────────────────────────────────────────────┐
│                    USER BROWSER                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (Vercel Serverless)                           │
│  • Next.js app on Vercel Edge Network                   │
│  • URL: https://mercedes-nl-search.vercel.app           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  BACKEND API (Vercel Serverless - NEW!)                 │
│  • FastAPI on Vercel serverless functions               │
│  • URL: https://your-backend-project.vercel.app         │
│  • NO COLD STARTS! (instant execution)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MIDDLEWARE (Railway)                                    │
│  • OpenAI-compatible RAG middleware                      │
│  • URL: https://web-production-a5d93.up.railway.app     │
│  • Handles category classification                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  TYPESENSE (Cloud)                                       │
│  • Search engine with 34k+ products                      │
│  • Semantic + keyword search                             │
└─────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Build Errors

**Error: "No Python version specified"**
- Vercel auto-detects Python version from `runtime.txt`
- Create `runtime.txt` in project root: `python-3.9` or `python-3.11`

**Error: "Module not found"**
- Check `requirements.txt` is in project root
- Verify all dependencies are listed

**Error: "Application startup failed"**
- Check environment variables are set correctly
- View deployment logs in Vercel dashboard

### Runtime Errors

**Error: "Typesense connection failed"**
- Verify `TYPESENSE_HOST`, `TYPESENSE_PORT`, `TYPESENSE_PROTOCOL` are correct
- Check `TYPESENSE_API_KEY` is valid

**Error: "OpenAI API error"**
- Verify `OPENAI_API_KEY` is correct
- Check OpenAI account has sufficient credits

### CORS Errors

If you see CORS errors in browser console:
1. Check `src/app.py` line 27-33 includes your frontend domain
2. Redeploy backend after updating CORS settings

## Cost Comparison

### Render (Before)
- **Free Tier**: 750 hours/month
- **Spin Down**: After 15 minutes inactivity
- **Cold Start**: 30-50 seconds
- **Bandwidth**: 100GB/month

### Vercel (After)
- **Free Tier**: Unlimited serverless invocations
- **Cold Start**: None (instant)
- **Bandwidth**: 100GB/month
- **Build Time**: 100 hours/month

**Winner**: Vercel (better performance, same cost)

## Next Steps

1. ✅ Backend deployed to Vercel
2. ✅ Frontend updated with new backend URL
3. ✅ Test everything works
4. 🔄 (Optional) Decommission Render backend
5. 🔄 (Optional) Update documentation

## Decommissioning Render (Optional)

Once you verify Vercel is working:

1. Go to https://dashboard.render.com
2. Select your backend service
3. Click **"Delete Service"**
4. Confirm deletion

**Note**: Keep your Railway middleware running (it's still needed!)

## Questions?

- Vercel Docs: https://vercel.com/docs
- Vercel Python Runtime: https://vercel.com/docs/functions/runtimes/python
- FastAPI on Vercel: https://vercel.com/guides/fastapi-with-python

---

**Last Updated**: 2025-11-07
**Status**: Ready for deployment
