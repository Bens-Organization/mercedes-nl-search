# Deployment Guide

Complete guide for deploying Mercedes Scientific NL Search to production.

## Production Stack

This project is deployed using:
- **Frontend**: Vercel (Next.js)
- **Backend API**: Railway (FastAPI/Python)
- **Middleware**: Railway (OpenAI-compatible RAG)
- **Search Engine**: Typesense Cloud (8GB cluster)
- **Database**: Neon PostgreSQL
- **AI Services**: OpenAI (GPT-4o-mini + text-embedding-3-small)

**Live URLs**:
- Frontend: https://mercedes-nl-search.vercel.app
- Backend: https://mercedes-nl-search-staging.up.railway.app
- Middleware: https://web-production-a5d93.up.railway.app

**Why Railway?** Backend migrated from Render to eliminate 30-50 second cold start delays caused by free tier inactivity timeout.

---

## Prerequisites

- GitHub account
- OpenAI API key ([platform.openai.com](https://platform.openai.com))
- Typesense Cloud account ([cloud.typesense.org](https://cloud.typesense.org))
- Neon PostgreSQL database ([neon.tech](https://neon.tech))
- Railway account ([railway.app](https://railway.app))
- Vercel account ([vercel.com](https://vercel.com))

---

## Quick Deployment (30 minutes)

### 1. Push to GitHub

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Deploy Backend (Railway)

**For detailed Railway deployment guide, see [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)**

Quick steps:

1. Go to [railway.app](https://railway.app) → New Project
2. Connect your GitHub repository
3. Railway will auto-detect `Dockerfile` from `railway.toml`
4. Select `staging` environment
5. Add environment variables (see Environment Variables section below)
6. Deploy - Railway will use the correct Dockerfile automatically
7. Wait 2-3 minutes for deployment
8. Save your API URL: `https://your-service.up.railway.app`

**Note**: The `railway.toml` file uses environment-specific configuration to manage both backend and middleware services.

### 3. Setup Search Engine

**Register NL Model** (run once):
```bash
# Locally (with production credentials in .env)
python src/setup_middleware_model.py
```

**Index Products** (run once):
```bash
# Recommended: Run locally pointing to production Typesense
python src/indexer_neon.py
# Takes ~35-45 minutes, indexes all 34,607 products
```

### 4. Deploy Frontend (Vercel)

**Option A: Vercel Dashboard**
1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repo
3. Configure:
   ```
   Framework: Next.js
   Root Directory: frontend-next
   Build Command: npm run build
   ```
4. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-service.up.railway.app
   ```
5. Deploy

**Option B: Vercel CLI**
```bash
npm i -g vercel
cd frontend-next
vercel --prod
```

### 5. Update CORS

Add your Vercel URL to `src/app.py`:
```python
CORS(app, origins=[
    "http://localhost:3000",
    "https://*.vercel.app",
    "https://your-app.vercel.app",  # Your actual URL
])
```

Commit and push (Railway will auto-deploy).

### 6. Test

```bash
# Test backend
curl https://your-service.up.railway.app/health

# Test search
curl -X POST https://your-service.up.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gloves under $50"}'

# Test frontend
# Visit: https://your-app.vercel.app
```

---

## Environment Variables

### Backend (Railway)

Required variables for your Railway service:

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Typesense Cloud
TYPESENSE_API_KEY=your_admin_api_key
TYPESENSE_HOST=xxx.a1.typesense.net
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https

# Neon Database
NEON_DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require

# Server Configuration
ENVIRONMENT=production
SERVER_PORT=5001

# Backward Compatibility (deprecated)
# FLASK_ENV=production  # Use ENVIRONMENT instead
# FLASK_PORT=5001       # Use SERVER_PORT instead
```

**How to get these:**

**OpenAI**:
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create new secret key
3. Copy and save (shown only once)

**Typesense Cloud**:
1. Go to [cloud.typesense.org](https://cloud.typesense.org)
2. Create or select your cluster (recommended: 8GB for 34k+ products)
3. Copy Host, Port (443), Protocol (https)
4. Generate API Key (use Admin key, not Search-only)

**Neon PostgreSQL**:
1. Go to [neon.tech](https://neon.tech)
2. Create project or use existing
3. Get connection string from dashboard
4. Should include `?sslmode=require` at the end

### Frontend (Vercel)

Required variables for your Vercel project:

```bash
NEXT_PUBLIC_API_URL=https://your-service.up.railway.app
```

**Important**: Must start with `NEXT_PUBLIC_` for Next.js client-side access.

---

## Typesense Memory Requirements

Products are stored with semantic embeddings in RAM:

| Products | Memory Needed | Typesense Cloud Plan |
|----------|---------------|---------------------|
| 5,000    | ~100MB        | 0.5GB ($22/mo)      |
| 10,000   | ~200MB        | 0.5GB ($22/mo)      |
| 34,000   | ~700MB        | 2GB ($88/mo) or 8GB ($350/mo) |

**Recommended**: 8GB cluster for production (handles growth + traffic spikes)

**Memory breakdown**:
- Text data: ~100MB (product names, descriptions, etc.)
- Embeddings: ~600MB (1536-dim vectors × 34k products)

**Without embeddings**: Could fit on 0.5GB cluster, but loses semantic search capability.

---

## Troubleshooting

### Backend Issues

**"Application failed to start"**
- Check Railway logs for Python errors
- Verify all environment variables are set correctly
- Ensure Dockerfile has correct `PYTHONPATH` setting
- Check that `railway.toml` is configured properly

**"Search not returning results"**
- Run indexer: `python src/indexer_neon.py`
- Check Typesense Cloud dashboard for indexed documents
- Verify collection exists and has data

**"Query translation not working"**
- Ensure middleware model is registered: `python src/setup_middleware_model.py`
- Check `search.py` uses correct model ID: `"middleware-rag-vllm"`
- Verify in Railway logs that `nl_query=true` is being used
- Check middleware service is running: `curl https://web-production-a5d93.up.railway.app/health`

**"OpenAI API error"**
- Verify API key is valid
- Check billing is enabled at [platform.openai.com/account/billing](https://platform.openai.com/account/billing)
- Ensure you have credits/payment method

**"Typesense connection failed"**
- Verify host, port, protocol, API key are correct
- Check Typesense Cloud cluster is running
- Try API key regeneration if issues persist

### Frontend Issues

**"Failed to fetch" or CORS errors**
- Verify `NEXT_PUBLIC_API_URL` in Vercel matches Railway URL
- Check CORS in `src/app.py` includes your Vercel URL
- Ensure `allow_origin_regex` is configured for wildcard domains
- Redeploy backend after CORS changes
- Clear browser cache

**"Environment variable not found"**
- Ensure it starts with `NEXT_PUBLIC_` prefix
- Redeploy frontend after adding/changing env vars
- Check Vercel dashboard → Settings → Environment Variables

**"TypeScript build errors"**
- Check for null-safety issues (use `value ? value : default`)
- Verify all imports are correct
- Run `npm run build` locally to reproduce

### Deployment Issues

**Railway not auto-deploying on git push**
- Check GitHub integration is connected
- Verify branch is configured in Railway settings
- Check repository webhook in GitHub Settings → Webhooks
- Try manual deploy to verify it works

**Wrong Dockerfile being used**
- Verify `railway.toml` has environment-specific configuration
- Check Railway dashboard shows correct Dockerfile path for each service
- See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for multi-service setup

**Vercel deployment failing**
- Check build logs for errors
- Verify root directory is set to `frontend-next`
- Ensure all dependencies are in `package.json`
- Try deploying via CLI for more detailed errors

---

## Indexing

### Full Indexing (34,607 products)

```bash
# Recommended: Run locally with production credentials
python src/indexer_neon.py
```

**Time**: ~35-45 minutes
- Database query: 1-3 minutes
- Fetch & transform: 5-10 minutes
- Embedding generation: 25-35 minutes

**Cost**: ~$0.60-0.80 for embeddings (one-time per full re-index)

### Test Indexing (Limited Products)

```bash
python3
>>> from src.indexer_neon import NeonProductIndexer
>>> indexer = NeonProductIndexer()
>>> indexer.run(max_products=1000)  # Index only 1000 products
```

**Time**: ~3-5 minutes for 1000 products

### Re-indexing

Re-run the indexer anytime to:
- Refresh product data from database
- Update after schema changes
- Add new products

**Note**: Indexer automatically deletes and recreates the collection.

---

## Post-Deployment

### Railway Free Tier Notes

**Good news!** Railway free tier doesn't have the aggressive sleep policy that Render does:
- No 15-minute inactivity timeout
- Faster cold starts (~5-10 seconds vs 30-50 seconds)
- Better resource allocation
- No need for uptime monitoring services

This is why we migrated from Render to Railway - to eliminate the cold start delays that were impacting user experience.

### Custom Domain

**Vercel**:
1. Dashboard → Project → Settings → Domains
2. Add your domain
3. Update DNS as instructed

**Render**:
1. Dashboard → Service → Settings → Custom Domain
2. Add your domain
3. Update DNS as instructed

### Monitor Costs

**OpenAI**: [platform.openai.com/usage](https://platform.openai.com/usage)
- Set usage limits to avoid surprises
- ~$0.01 per search (query translation + embedding)

**Typesense Cloud**: [cloud.typesense.org](https://cloud.typesense.org)
- Check dashboard for usage
- 8GB cluster: $350/month

**Render**: [dashboard.render.com/billing](https://dashboard.render.com/billing)
- Free tier: $0 (sleeps after 15min)
- Paid: $7-25/month (no sleep)

**Vercel**: [vercel.com/usage](https://vercel.com/usage)
- Free tier: 100GB bandwidth/month
- Typically sufficient for most use cases

### Enable Analytics (Optional)

Add to `frontend-next/app/layout.tsx`:

```typescript
// Google Analytics
<Script src="https://www.googletagmanager.com/gtag/js?id=GA_ID" />
<Script id="google-analytics">
  {`
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'GA_ID');
  `}
</Script>
```

---

## Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│  Frontend (Vercel)          │
│  - Next.js                  │
│  - Tailwind CSS             │
└──────────┬──────────────────┘
           │ HTTPS
           ▼
┌─────────────────────────────┐
│  Backend API (Render)       │
│  - FastAPI/Python           │
│  - Query translation        │
│  - CORS handling            │
└──────┬──────────────────┬───┘
       │                  │
       │ REST API         │ Database queries
       ▼                  ▼
┌──────────────────┐  ┌─────────────┐
│  Typesense Cloud │  │ Neon        │
│  - Hybrid search │  │ PostgreSQL  │
│  - Embeddings    │  │ - Products  │
│  - NL model      │  │ - 34k rows  │
└────────┬─────────┘  └─────────────┘
         │
         │ Query translation & embeddings
         ▼
┌─────────────────────┐
│  OpenAI API         │
│  - GPT-4o-mini      │
│  - text-embed-3-sm  │
└─────────────────────┘
```

---

## Updating the Deployment

To update your live deployment:

```bash
# 1. Make changes locally
# 2. Test locally
# 3. Commit and push
git add .
git commit -m "Update: description of changes"
git push

# 4. Auto-deploys to:
#    - Render (backend) - ~2-3 minutes
#    - Vercel (frontend) - ~1-2 minutes
```

**Note**: Auto-deploy must be enabled on both platforms.

---

## Logs & Debugging

**Render Logs**:
- Dashboard → Your Service → Logs
- Real-time logging
- Filter by severity

**Vercel Logs**:
- Dashboard → Deployment → Function Logs
- View specific deployment logs
- Check build errors

**Typesense Cloud**:
- No logging available in dashboard
- Debug via your backend logs

---

## Security Checklist

- [ ] `.env` file is in `.gitignore` (never commit secrets)
- [ ] All API keys rotated after any public exposure
- [ ] CORS restricted to your actual domains (not `*`)
- [ ] Typesense Admin API key not exposed to frontend
- [ ] OpenAI usage limits set to prevent abuse
- [ ] Render environment variables marked as "secret"
- [ ] Regular security updates: `pip install --upgrade -r requirements.txt`

---

## Support

**Platform Documentation**:
- Render: https://render.com/docs
- Vercel: https://vercel.com/docs
- Typesense: https://typesense.org/docs
- Neon: https://neon.tech/docs
- OpenAI: https://platform.openai.com/docs

**Common Questions**:
- See `CLAUDE.md` for detailed project context
- See `README.md` for local development setup
- Check GitHub Issues for known problems

---

**Last Updated**: 2025-10-16

**Deployment Status**: ✅ Live and operational
