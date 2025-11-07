# Vercel Backend Deployment - Quick Start

This is your quick reference guide for deploying the backend to Vercel.

## ⚡ Why This Migration?

**Problem**: Render free tier has 30-50 second cold starts
**Solution**: Vercel serverless functions (instant, no cold starts!)

## 📋 What Changed?

### New Files Added:
- ✅ `vercel.json` - Vercel deployment configuration
- ✅ `.vercelignore` - Files to exclude from deployment
- ✅ `docs/VERCEL_DEPLOYMENT.md` - Complete step-by-step guide
- ✅ `frontend-next/.env.example` - Updated with Vercel URL example

### Existing Files (No Changes Needed):
- ✅ `runtime.txt` - Already compatible (Python 3.9.18)
- ✅ `requirements.txt` - Already complete
- ✅ `src/app.py` - Already Vercel-compatible
- ✅ `.env.example` - Already complete

## 🚀 Deployment Steps (Summary)

### 1. Deploy Backend to Vercel

1. Go to https://vercel.com/new
2. Import your GitHub repository
3. Configure project:
   - Framework: Other
   - Root Directory: `.` (default)
   - Leave Build/Output empty
4. Add environment variables (from your `.env` file):
   - `OPENAI_API_KEY`
   - `TYPESENSE_HOST`
   - `TYPESENSE_PORT`
   - `TYPESENSE_PROTOCOL`
   - `TYPESENSE_API_KEY`
   - `OPENAI_MODEL`
   - `OPENAI_EMBEDDING_MODEL`
   - `ENVIRONMENT=production`
5. Click Deploy (takes 2-3 minutes)
6. Copy your backend URL: `https://your-project.vercel.app`

### 2. Update Frontend Configuration

**Option A: Via Vercel Dashboard (Recommended)**
1. Go to your frontend project in Vercel
2. Settings → Environment Variables
3. Update `NEXT_PUBLIC_API_URL` to your new backend URL
4. Redeploy frontend

**Option B: For Local Testing**
Create `frontend-next/.env.local`:
```bash
NEXT_PUBLIC_API_URL=https://your-backend-project.vercel.app
```

### 3. Test Everything

```bash
# Test backend health
curl https://your-backend-project.vercel.app/health

# Test search
curl -X POST https://your-backend-project.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gloves"}'

# Test frontend
# Visit: https://mercedes-nl-search.vercel.app
```

## 📚 Need More Details?

See `docs/VERCEL_DEPLOYMENT.md` for:
- Complete step-by-step guide with screenshots
- Environment variable details
- Troubleshooting section
- Architecture diagrams
- Cost comparison

## ⏱️ Expected Results

### Before (Render):
- First search: **30-50 seconds** (cold start)
- Subsequent: 2-4 seconds

### After (Vercel):
- First search: **2-4 seconds** (no cold start!)
- Subsequent: 2-4 seconds
- **Consistent performance** 🎉

## 🛠️ Files Created in This Branch

```
.
├── vercel.json                      # Vercel config (NEW)
├── .vercelignore                    # Deployment exclusions (NEW)
├── VERCEL_QUICK_START.md           # This file (NEW)
├── docs/
│   └── VERCEL_DEPLOYMENT.md        # Complete guide (NEW)
└── frontend-next/
    └── .env.example                # Updated with Vercel URL
```

## 🎯 Current Architecture

```
Frontend (Vercel) → Backend (Vercel - instant!) → Middleware (Railway) → Typesense
```

## ✅ Checklist

- [ ] Backend deployed to Vercel
- [ ] Backend health check passes
- [ ] Frontend updated with new backend URL
- [ ] Frontend redeployed
- [ ] Search functionality works
- [ ] Response times are 2-4 seconds (no cold starts!)
- [ ] (Optional) Render backend decommissioned
- [ ] (Optional) UptimeRobot updated

## 🆘 Need Help?

Check `docs/VERCEL_DEPLOYMENT.md` for:
- Detailed troubleshooting
- Common errors and solutions
- Vercel documentation links

---

**Branch**: `feature/vercel-backend-migration`
**Status**: Ready for deployment
**Last Updated**: 2025-11-07
