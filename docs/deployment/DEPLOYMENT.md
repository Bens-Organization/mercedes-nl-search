# Deployment Guide - Mercedes Scientific Natural Language Search

This guide will help you deploy both the backend (Flask API) and frontend (Next.js) to production.

**You're using:** ✅ Typesense Cloud (managed search service)

> **Quick Start:** If you want a faster guide, see `DEPLOYMENT_QUICKSTART.md`
> **Typesense Cloud Setup:** See `TYPESENSE_CLOUD_SETUP.md` for getting your credentials

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐
│   Frontend      │ ───────▶│   Backend API    │
│   (Vercel)      │         │   (Render/Fly.io)│
└─────────────────┘         └──────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              ┌──────────┐    ┌──────────┐    ┌──────────┐
              │Typesense │    │  OpenAI  │    │   Neon   │
              │  Cloud   │    │    API   │    │ Database │
              └──────────┘    └──────────┘    └──────────┘
```

## Recommended Deployment Platforms

### Backend (Flask API)
**Top Recommendations:**
1. **Render** - Easy, generous free tier, auto-deploy from GitHub
2. **Railway** - Developer-friendly, usage-based pricing
3. **Fly.io** - Great performance, global edge deployment
4. **Heroku** - Classic choice (paid plans only)

**We'll use Render for this guide** (easiest for beginners)

### Frontend (Next.js)
**Top Recommendations:**
1. **Vercel** - Built by Next.js creators, seamless integration
2. **Netlify** - Great alternative with similar features
3. **Cloudflare Pages** - Fast, generous free tier

**We'll use Vercel for this guide** (best for Next.js)

---

## Part 1: Backend Deployment (Render)

### Step 1: Prepare Backend for Deployment

First, ensure you have these files ready:

1. **Check requirements.txt**
   ```bash
   cat requirements.txt
   ```
   Should include: flask, flask-cors, typesense, openai, pydantic, python-dotenv, requests, gql, psycopg2-binary

2. **Create runtime.txt** (tells Render which Python version)
   ```
   python-3.9.18
   ```

3. **Create Procfile** (tells Render how to start your app)
   ```
   web: python src/app.py
   ```

### Step 2: Push to GitHub

```bash
# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Mercedes Scientific NL Search"

# Create GitHub repo (via GitHub website or CLI)
# Then push
git remote add origin https://github.com/YOUR_USERNAME/mercedes-nl-search.git
git branch -M main
git push -u origin main
```

### Step 3: Deploy to Render

1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `mercedes-search-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python src/app.py`
   - **Instance Type**: Free (or Starter for better performance)

5. Add Environment Variables (click "Advanced" → "Add Environment Variable"):
   ```
   OPENAI_API_KEY=sk-...
   TYPESENSE_API_KEY=...
   TYPESENSE_HOST=...
   TYPESENSE_PORT=443
   TYPESENSE_PROTOCOL=https
   NEON_DATABASE_URL=postgresql://...
   FLASK_ENV=production
   FLASK_PORT=5001
   OPENAI_MODEL=gpt-4o-mini-2024-07-18
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   ```

6. Click "Create Web Service"

7. Wait for deployment (5-10 minutes)

8. Your API will be live at: `https://mercedes-search-api.onrender.com`

### Step 4: Post-Deployment Backend Setup

After deployment, you need to set up the NL search model:

**Option A: Use Render Shell**
1. In Render dashboard, click your service
2. Go to "Shell" tab
3. Run: `python src/setup_nl_model.py`

**Option B: Create a one-time job**
1. In Render, create a "Background Worker" or "Cron Job"
2. Command: `python src/setup_nl_model.py`
3. Run once

**Verify:**
```bash
curl https://YOUR-API-URL.onrender.com/health
```

---

## Part 2: Frontend Deployment (Vercel)

### Step 1: Update Frontend API URL

1. Create environment file for frontend:

**frontend-next/.env.local** (for local dev - don't commit):
```
NEXT_PUBLIC_API_URL=http://localhost:5001
```

**frontend-next/.env.production** (for production):
```
NEXT_PUBLIC_API_URL=https://YOUR-API-URL.onrender.com
```

2. Update your API calls to use environment variable:

**frontend-next/lib/api.ts** (or wherever you make API calls):
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';

export async function searchProducts(query: string) {
  const response = await fetch(`${API_URL}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  return response.json();
}
```

### Step 2: Deploy to Vercel

**Method 1: Vercel CLI (Recommended)**
```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to frontend directory
cd frontend-next

# Login to Vercel
vercel login

# Deploy
vercel --prod

# Follow prompts:
# - Set up and deploy? Yes
# - Which scope? Your account
# - Link to existing project? No
# - Project name? mercedes-nl-search
# - Directory? ./
# - Override settings? No
```

**Method 2: Vercel Dashboard**
1. Go to [vercel.com](https://vercel.com) and sign up/login
2. Click "Add New..." → "Project"
3. Import your GitHub repository
4. Configure project:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend-next`
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `.next` (auto-detected)

5. Add Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://YOUR-API-URL.onrender.com
   ```

6. Click "Deploy"

7. Your app will be live at: `https://mercedes-nl-search.vercel.app`

### Step 3: Update CORS Settings

Now that you have a production frontend URL, update the backend CORS settings:

**src/app.py** - Update CORS configuration:
```python
# Replace this:
CORS(app)

# With this:
CORS(app, origins=[
    "http://localhost:3000",  # Local dev
    "https://mercedes-nl-search.vercel.app",  # Production
    "https://*.vercel.app"  # Vercel preview deployments
])
```

Redeploy the backend (Render will auto-deploy if you push to GitHub).

---

## Part 3: Post-Deployment Setup

### 1. Index Products (One-Time)

You need to populate your Typesense collection with products.

**Option A: Run indexer locally** (Recommended)
```bash
# Your local machine (faster with better internet)
python src/indexer_neon.py
```

**Option B: Run indexer on Render**
- Create a Background Worker on Render
- Command: `python src/indexer_neon.py`
- Run once (will take 35-45 minutes)

### 2. Set Up NL Search Model (One-Time)

```bash
# If not already done in Step 4 of Backend Deployment
python src/setup_nl_model.py
```

### 3. Test Your Deployment

**Test Backend:**
```bash
curl -X POST https://YOUR-API-URL.onrender.com/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sterile gloves under $50"}'
```

**Test Frontend:**
- Visit `https://YOUR-FRONTEND-URL.vercel.app`
- Try searching for "sterile gloves under $50"
- Verify results appear

---

## Environment Variables Reference

### Backend (.env)
```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Typesense
TYPESENSE_API_KEY=...
TYPESENSE_HOST=xxx.a1.typesense.net
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https

# Neon Database
NEON_DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# Flask
FLASK_ENV=production
FLASK_PORT=5001
```

### Frontend (.env.production)
```bash
NEXT_PUBLIC_API_URL=https://YOUR-API-URL.onrender.com
```

---

## Alternative Deployment Platforms

### Backend Alternatives

#### Railway
1. Sign up at [railway.app](https://railway.app)
2. Create new project → Deploy from GitHub
3. Add environment variables
4. Deploy automatically

**Pros**: Simple, great DX, automatic SSL
**Cons**: Usage-based pricing

#### Fly.io
1. Install flyctl: `brew install flyctl` (Mac) or see [fly.io/docs](https://fly.io/docs/getting-started/installing-flyctl/)
2. Login: `fly auth login`
3. Create app: `fly launch`
4. Set secrets: `fly secrets set OPENAI_API_KEY=...`
5. Deploy: `fly deploy`

**Pros**: Edge deployment, fast, generous free tier
**Cons**: More complex setup

### Frontend Alternatives

#### Netlify
1. Sign up at [netlify.com](https://netlify.com)
2. Import GitHub repo
3. Build settings:
   - Base directory: `frontend-next`
   - Build command: `npm run build`
   - Publish directory: `frontend-next/.next`
4. Add environment variables
5. Deploy

---

## Monitoring & Maintenance

### Health Checks

**Backend:**
```bash
curl https://YOUR-API-URL.onrender.com/health
```

**Frontend:**
Visit your app URL and check browser console

### Logs

**Render:**
- Dashboard → Your Service → Logs tab

**Vercel:**
- Dashboard → Your Project → Deployments → View Function Logs

### Cost Monitoring

**Free Tier Limits:**
- **Render**: 750 hours/month (one free service), sleeps after 15min inactivity
- **Vercel**: 100GB bandwidth, unlimited deployments
- **Typesense Cloud**: Check your plan limits
- **OpenAI**: Monitor usage at platform.openai.com/usage
- **Neon**: Check your plan limits

**Keep Render awake** (optional):
Use a service like [UptimeRobot](https://uptimerobot.com) to ping your API every 5 minutes.

---

## Troubleshooting

### Backend Issues

**Issue: "Application error" on Render**
- Check Render logs for errors
- Verify all environment variables are set
- Ensure requirements.txt is complete

**Issue: "Module not found" errors**
- Add missing packages to requirements.txt
- Redeploy

**Issue: CORS errors**
- Verify CORS settings in app.py include your frontend URL
- Check browser console for exact error

### Frontend Issues

**Issue: "API request failed"**
- Verify NEXT_PUBLIC_API_URL is set correctly
- Check backend is running: `curl YOUR-API-URL/health`
- Check browser console for CORS errors

**Issue: Environment variables not working**
- Ensure variables start with `NEXT_PUBLIC_`
- Rebuild and redeploy frontend
- Clear Vercel cache: Deployments → Redeploy

---

## Security Checklist

Before going live:

- [ ] `.env` files are in `.gitignore` (never commit secrets!)
- [ ] All API keys are set as environment variables in deployment platforms
- [ ] CORS is configured with specific origins (not `*`)
- [ ] Rate limiting is considered (add if expecting high traffic)
- [ ] HTTPS is enabled (automatic on Render/Vercel)
- [ ] Typesense API key has appropriate permissions
- [ ] Neon database has connection pooling enabled

---

## Deployment Checklist

### Pre-Deployment
- [ ] Code is committed to GitHub
- [ ] `.gitignore` is properly configured
- [ ] All dependencies are in requirements.txt / package.json
- [ ] Environment variables are documented

### Backend Deployment
- [ ] Backend deployed to Render (or alternative)
- [ ] All environment variables configured
- [ ] Health endpoint returns 200
- [ ] NL search model registered
- [ ] Products indexed to Typesense

### Frontend Deployment
- [ ] Frontend deployed to Vercel (or alternative)
- [ ] API URL environment variable configured
- [ ] CORS configured in backend for frontend URL
- [ ] Test search functionality works

### Post-Deployment
- [ ] Monitor logs for errors
- [ ] Set up uptime monitoring
- [ ] Monitor API usage and costs
- [ ] Share live URL with users!

---

## Next Steps

After deployment:

1. **Custom Domain** (Optional)
   - Render: Settings → Custom Domain
   - Vercel: Settings → Domains

2. **Analytics** (Optional)
   - Add Google Analytics to frontend
   - Track search queries for insights

3. **Monitoring** (Recommended)
   - Set up error tracking (Sentry)
   - Monitor API performance
   - Track OpenAI costs

4. **CI/CD** (Automatic)
   - Both Render and Vercel auto-deploy on git push
   - Set up branch previews for testing

---

## Support

If you encounter issues:
1. Check the logs in your deployment platform
2. Review this guide's Troubleshooting section
3. Check CLAUDE.md for implementation details
4. Test locally first: `python src/app.py` and `npm run dev`

**Your app is now live!** 🚀
