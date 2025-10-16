# 🚀 Deployment Quick Start

**Goal:** Deploy your Mercedes Scientific NL Search app online in ~30 minutes

## Prerequisites

- [ ] GitHub account
- [ ] Git installed locally
- [ ] All API keys ready (see ENV_SETUP.md if you need help getting these):
  - OpenAI API key
  - Typesense API key & host
  - Neon database connection string

---

## Step 1: Push to GitHub (5 minutes)

```bash
# 1. Initialize git (if not already done)
git init

# 2. Verify .gitignore is working (should NOT show .env files)
git status

# 3. Add all files
git add .

# 4. Make first commit
git commit -m "Initial commit: Mercedes Scientific NL Search"

# 5. Create GitHub repo
# Go to github.com → New Repository → Create
# Name it: mercedes-nl-search
# Don't initialize with README (you already have one)

# 6. Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/mercedes-nl-search.git
git branch -M main
git push -u origin main
```

**✅ Checkpoint:** Your code should now be visible on GitHub at:
`https://github.com/YOUR_USERNAME/mercedes-nl-search`

---

## Step 2: Deploy Backend to Render (10 minutes)

### 2.1: Create Render Account & Deploy

1. Go to [render.com](https://render.com)
2. Sign up with GitHub (easiest)
3. Click **"New +"** → **"Web Service"**
4. Click **"Connect a repository"** → Select your repo
5. Configure:
   - **Name:** `mercedes-search-api`
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python src/app.py`
   - **Plan:** Free (or Starter for better performance)

### 2.2: Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"** and add these:

```
OPENAI_API_KEY=your_actual_key_here
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
TYPESENSE_API_KEY=your_actual_key_here
TYPESENSE_HOST=your_host.a1.typesense.net
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https
NEON_DATABASE_URL=postgresql://your_connection_string
FLASK_ENV=production
FLASK_PORT=5001
```

**Pro tip:** Copy from your local `.env` file

6. Click **"Create Web Service"**
7. Wait 5-10 minutes for build to complete

### 2.3: Save Your API URL

Once deployed, you'll see a URL like:
```
https://mercedes-search-api.onrender.com
```

**Save this!** You'll need it for the frontend.

**✅ Checkpoint:** Test your API is working:
```bash
curl https://YOUR-API-URL.onrender.com/health
# Should return: {"status":"healthy"}
```

---

## Step 3: Set Up Search Index (15 minutes)

### 3.1: Register NL Search Model

**Option A: Via Render Shell (Recommended)**
1. In Render dashboard → Your service → **Shell** tab
2. Run: `python src/setup_nl_model.py`
3. Wait for success message

**Option B: Via Local Machine**
```bash
# Temporarily set production env vars locally
export TYPESENSE_API_KEY=your_key
export TYPESENSE_HOST=your_host
export OPENAI_API_KEY=your_key

# Run setup
python src/setup_nl_model.py
```

### 3.2: Index Products

**Option A: Run Locally (Faster - Recommended)**
```bash
python src/indexer_neon.py
```

**Option B: Run on Render**
1. Render Dashboard → Create **"Background Worker"**
2. Same repo, command: `python src/indexer_neon.py`
3. Start worker, wait 35-45 minutes
4. Delete worker when done (to avoid charges)

**Note:** Indexing only needs to be done once (or when you want to refresh product data)

**✅ Checkpoint:** Your Typesense collection should now have 34,000+ products

---

## Step 4: Deploy Frontend to Vercel (5 minutes)

### 4.1: Update Frontend API URL

Create `frontend-next/.env.production`:
```bash
NEXT_PUBLIC_API_URL=https://YOUR-RENDER-API-URL.onrender.com
```

### 4.2: Deploy to Vercel

**Option A: CLI (Recommended)**
```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to frontend
cd frontend-next

# Login
vercel login

# Deploy
vercel --prod

# Follow prompts:
# - Link to existing project? No
# - What's your project's name? mercedes-nl-search
# - In which directory is your code located? ./
```

**Option B: Vercel Dashboard**
1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub
3. Click **"Add New..."** → **"Project"**
4. Import your GitHub repo
5. Configure:
   - **Framework Preset:** Next.js (auto-detected)
   - **Root Directory:** `frontend-next`
   - **Build Command:** `npm run build`
6. Add Environment Variable:
   ```
   NEXT_PUBLIC_API_URL=https://YOUR-RENDER-URL.onrender.com
   ```
7. Click **"Deploy"**

### 4.3: Update CORS in Backend

Now that you have your Vercel URL (e.g., `https://mercedes-nl-search.vercel.app`):

1. Update `src/app.py` line 17-24
2. Add your actual Vercel URL:
   ```python
   CORS(app, origins=[
       "http://localhost:3000",
       "https://*.vercel.app",
       "https://mercedes-nl-search.vercel.app",  # Add your actual URL
   ])
   ```
3. Commit and push:
   ```bash
   git add src/app.py
   git commit -m "Update CORS for production frontend"
   git push
   ```
4. Render will auto-redeploy (wait ~2 minutes)

**✅ Checkpoint:** Your frontend should now be live!

---

## Step 5: Test Everything (2 minutes)

### Test Backend API

```bash
curl -X POST https://YOUR-RENDER-URL.onrender.com/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sterile gloves under $50"}'
```

Should return JSON with search results.

### Test Frontend

1. Visit `https://YOUR-VERCEL-URL.vercel.app`
2. Type a query: "nitrile gloves under $30"
3. Verify results appear

**If you see results: 🎉 Success! Your app is fully deployed!**

---

## Your Live URLs

After deployment, you'll have:

| Service | URL | Purpose |
|---------|-----|---------|
| Backend API | `https://mercedes-search-api.onrender.com` | Search API |
| Frontend | `https://mercedes-nl-search.vercel.app` | User interface |
| GitHub | `https://github.com/YOUR_USERNAME/mercedes-nl-search` | Source code |

**Share your frontend URL with users!**

---

## Common Issues & Fixes

### Backend Issues

**❌ "Application failed to start"**
- Check Render logs for errors
- Verify all environment variables are set
- Check requirements.txt includes all dependencies

**❌ "No results returned"**
- Run the indexer: `python src/indexer_neon.py`
- Verify products were indexed in Typesense Cloud dashboard

**❌ "OpenAI API error"**
- Verify API key is correct
- Check you have billing enabled and credits in OpenAI account

### Frontend Issues

**❌ "Failed to fetch" or CORS errors**
- Verify `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Check CORS is updated in `src/app.py` with your Vercel URL
- Redeploy backend after CORS update

**❌ "Environment variable not found"**
- Ensure it starts with `NEXT_PUBLIC_`
- Redeploy frontend after adding env var
- Clear browser cache

**❌ Results load slowly or timeout**
- Render free tier sleeps after 15min inactivity (first request slow)
- Consider Render paid tier for production
- Or use UptimeRobot to keep it awake

---

## Post-Deployment Optimization

### Keep Render Backend Awake (Optional)

Render free tier sleeps after 15 minutes of inactivity. To keep it awake:

1. Sign up at [uptimerobot.com](https://uptimerobot.com) (free)
2. Create new monitor:
   - Type: HTTP(s)
   - URL: `https://YOUR-RENDER-URL.onrender.com/health`
   - Interval: 5 minutes
3. Your backend will stay awake 24/7

### Add Custom Domain (Optional)

**Frontend (Vercel):**
1. Vercel Dashboard → Your Project → Settings → Domains
2. Add your domain (e.g., `search.yourdomain.com`)
3. Update DNS as instructed

**Backend (Render):**
1. Render Dashboard → Your Service → Settings → Custom Domain
2. Add your domain (e.g., `api.yourdomain.com`)
3. Update DNS as instructed

### Monitor Costs

Set up billing alerts:
- **OpenAI:** platform.openai.com/account/billing → Usage limits
- **Typesense Cloud:** Check dashboard for usage
- **Render:** Free tier = free, but monitor if upgraded
- **Vercel:** Free tier = 100GB/month bandwidth

---

## Next Steps

After successful deployment:

- [ ] Share your live URL with stakeholders
- [ ] Set up custom domain (optional)
- [ ] Monitor error logs in Render & Vercel
- [ ] Set up billing alerts
- [ ] Consider adding analytics (Google Analytics, etc.)
- [ ] Plan for updates: `git push` auto-deploys to both platforms!

---

## Getting Help

**Documentation:**
- Full deployment guide: `DEPLOYMENT.md`
- Environment variables: `ENV_SETUP.md`
- Project details: `CLAUDE.md`

**Platform Docs:**
- Render: https://render.com/docs
- Vercel: https://vercel.com/docs
- Typesense: https://typesense.org/docs/guide/
- Neon: https://neon.tech/docs

**Logs:**
- Render: Dashboard → Your Service → Logs
- Vercel: Dashboard → Your Project → Deployments → Function Logs

---

## Total Time

- ✅ Step 1: Push to GitHub → 5 min
- ✅ Step 2: Deploy Backend → 10 min
- ✅ Step 3: Set Up Search Index → 15 min
- ✅ Step 4: Deploy Frontend → 5 min
- ✅ Step 5: Test → 2 min

**Total: ~30-40 minutes** (excluding indexing wait time)

**Your app is now live and fully functional!** 🚀

---

**Questions?** Review the full `DEPLOYMENT.md` for more detailed explanations and alternative deployment options.
