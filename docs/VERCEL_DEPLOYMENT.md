# Vercel Backend Deployment Guide

Deploy your FastAPI backend to Vercel to eliminate 30-50 second cold start delays from Render.

## 🎯 Quick Summary

**What**: Deploy backend to Vercel serverless functions
**Why**: Eliminate cold starts (30-50s → 2-4s response time)
**Time**: 15-20 minutes
**Cost**: Free tier (100GB bandwidth, unlimited requests)

## ⚡ Why Vercel?

```
BEFORE (Render):
First search: 30-50 seconds ❌ (cold start)
Subsequent:   2-4 seconds

AFTER (Vercel):
First search:  2-4 seconds ✅ (no cold start!)
Subsequent:    2-4 seconds
```

**Architecture**:
```
Frontend (Vercel) → Backend (Vercel - instant!) → Middleware (Railway) → Typesense
```

---

## Step 1: Deploy Backend to Vercel

### 1.1 Import Project

1. Go to https://vercel.com/new
2. Click **"Import Git Repository"**
3. Select your GitHub repository: `mercedes-nl-search`
4. Click **"Import"**

### 1.2 Configure Project

**Important**: Configure these settings carefully!

- **Framework Preset**: Other
- **Root Directory**: `.` (default - leave as-is)
- **Build Command**: Leave empty
- **Output Directory**: Leave empty

Click **"Continue"**

### 1.3 Add Environment Variables

Copy these **exactly** from your `.env` file:

| Variable | Example Value | Notes |
|----------|---------------|-------|
| `OPENAI_API_KEY` | `sk-proj-...` | Your OpenAI API key |
| `TYPESENSE_HOST` | `xxx.a1.typesense.net` | No `https://` prefix! |
| `TYPESENSE_PORT` | `443` | |
| `TYPESENSE_PROTOCOL` | `https` | |
| `TYPESENSE_API_KEY` | `xyz123...` | Your Typesense admin key |
| `OPENAI_MODEL` | `gpt-4o-mini-2024-07-18` | |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | |
| `ENVIRONMENT` | `production` | Set to `production` |

**⚠️ Important**:
- No quotes needed in Vercel UI
- Apply to **Production** environment
- Double-check `TYPESENSE_HOST` has no protocol prefix

### 1.4 Deploy

1. Click **"Deploy"**
2. Wait 2-3 minutes (grab coffee ☕)
3. You'll see: **"Congratulations! Your project has been deployed"**
4. Copy your backend URL: `https://your-backend-project.vercel.app`

### 1.5 Test Backend

```bash
# Test health endpoint
curl https://your-backend-project.vercel.app/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "api": "ok",
    "typesense": "ok"
  }
}

# Test search (should be ~2-4 seconds)
time curl -X POST https://your-backend-project.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gloves"}'
```

✅ **If both work**, proceed to Step 2!

---

## Step 2: Update Frontend to Use New Backend

Your frontend is already deployed on Vercel. Now update it to use the new backend URL.

### 2.1 Update Environment Variable in Vercel

1. Go to https://vercel.com/dashboard
2. Select your **frontend project** (e.g., `mercedes-nl-search`)
3. Go to **Settings** → **Environment Variables**
4. Find or add: `NEXT_PUBLIC_API_URL`
5. Update value to: `https://your-backend-project.vercel.app`
   - Replace `your-backend-project` with your actual backend project name
6. Click **"Save"**

### 2.2 Redeploy Frontend

1. Go to **Deployments** tab
2. Click **"..."** menu on the latest deployment
3. Select **"Redeploy"**
4. Wait ~2 minutes for redeployment

### 2.3 Test End-to-End

1. Open your frontend: https://mercedes-nl-search.vercel.app
2. Try a search: **"nitrile gloves under $50"**
3. Check browser DevTools → Network tab
4. Search should complete in **2-4 seconds** (not 30-50!)

✅ **Success!** No more cold starts!

---

## Step 3: Verify & Monitor

### 3.1 Test Multiple Queries

Try these in your frontend to verify consistency:
- "sterile gloves under $50"
- "pipettes in stock"
- "lab coats size large"
- "test tubes glass"

**Expected**: All queries complete in 2-4 seconds consistently

### 3.2 Update UptimeRobot (Optional)

If you have UptimeRobot monitoring:
1. Go to https://uptimerobot.com
2. Edit your backend monitor
3. Update URL to: `https://your-backend-project.vercel.app/health`
4. Save

**Note**: With Vercel, cold starts are eliminated, so UptimeRobot is optional (just for uptime monitoring).

### 3.3 Decommission Render (Optional)

Once you verify everything works:
1. Go to https://dashboard.render.com
2. Select your backend service
3. Click **"Delete Service"**
4. Confirm deletion

**Important**: Keep Railway middleware running! It's still needed for RAG classification.

---

## 📊 Architecture After Migration

```
┌────────────────────────────────────────┐
│  USER BROWSER                          │
└─────────────┬──────────────────────────┘
              │
              ▼
┌────────────────────────────────────────┐
│  FRONTEND (Vercel)                     │
│  Next.js on Edge Network               │
│  https://mercedes-nl-search.vercel.app │
└─────────────┬──────────────────────────┘
              │
              ▼
┌────────────────────────────────────────┐
│  BACKEND API (Vercel) ✨ NEW!          │
│  FastAPI serverless functions          │
│  NO COLD STARTS! Instant execution     │
└─────────────┬──────────────────────────┘
              │
              ▼
┌────────────────────────────────────────┐
│  MIDDLEWARE (Railway)                  │
│  RAG-based category classification     │
└─────────────┬──────────────────────────┘
              │
              ▼
┌────────────────────────────────────────┐
│  TYPESENSE (Cloud)                     │
│  34k+ products, semantic search        │
└────────────────────────────────────────┘
```

---

## 🔧 Troubleshooting

### Build/Deploy Errors

**"No Python version specified"**
- Check `runtime.txt` exists in project root
- Should contain: `python-3.9.18`

**"Module not found"**
- Verify `requirements.txt` is in project root
- Check all dependencies are listed

**"Application startup failed"**
- Check environment variables are set correctly
- View logs: Vercel Dashboard → Your Project → Deployments → Click deployment → View Logs

### Runtime Errors

**Backend returns 503 or fails health check**
- Verify `TYPESENSE_HOST` doesn't include `https://`
- Check `TYPESENSE_API_KEY` is correct
- Test Typesense directly: `curl https://TYPESENSE_HOST:443/health`

**"OpenAI API error"**
- Verify `OPENAI_API_KEY` is correct (starts with `sk-proj-...`)
- Check OpenAI account has credits: https://platform.openai.com/usage

**CORS errors in browser console**
- Check `src/app.py` line 27-33 includes your frontend domain
- Frontend URL should be in `allow_origins` list
- Redeploy backend after updating

### Frontend Still Slow

**Check environment variable**:
1. Vercel Dashboard → Frontend Project → Settings → Environment Variables
2. Verify `NEXT_PUBLIC_API_URL` points to Vercel backend (not Render!)
3. Redeploy frontend if you changed it

**Clear browser cache**:
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

---

## 📝 Checklist

- [ ] Backend deployed to Vercel
- [ ] Backend health check passes (`/health` returns 200)
- [ ] Backend search works (test with curl)
- [ ] Frontend env var updated (`NEXT_PUBLIC_API_URL`)
- [ ] Frontend redeployed
- [ ] Frontend search works (2-4s response time)
- [ ] No cold starts (consistent performance)
- [ ] (Optional) UptimeRobot updated
- [ ] (Optional) Render backend deleted

---

## 📚 Resources

- [Vercel Docs](https://vercel.com/docs)
- [Vercel Python Runtime](https://vercel.com/docs/functions/runtimes/python)
- [FastAPI on Vercel](https://vercel.com/guides/fastapi-with-python)

---

**Last Updated**: 2025-11-07
**Branch**: `feature/vercel-backend-migration`
**Status**: Ready for deployment
