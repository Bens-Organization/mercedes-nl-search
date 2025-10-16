# Environment Variables Setup Guide

This document lists all required environment variables for deploying the Mercedes Scientific Natural Language Search application.

## Required Services

Before deployment, you need accounts and API keys from:

1. **OpenAI** - For LLM and embeddings
   - Sign up: https://platform.openai.com
   - Get API key: https://platform.openai.com/api-keys

2. **Typesense Cloud** - For search engine
   - Sign up: https://cloud.typesense.org
   - Create cluster and get API key

3. **Neon** - For PostgreSQL database
   - Sign up: https://neon.tech
   - Create project and get connection string

---

## Backend Environment Variables

### Local Development (.env)

Create a `.env` file in the project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-xxx...
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Typesense Configuration
TYPESENSE_API_KEY=your_api_key_here
TYPESENSE_HOST=xxx.a1.typesense.net
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https

# Neon Database Configuration
NEON_DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# Flask Configuration
FLASK_ENV=development
FLASK_PORT=5001
```

### Production (Render/Railway/Fly.io)

Set these as environment variables in your deployment platform:

| Variable | Example Value | Required | Description |
|----------|---------------|----------|-------------|
| `OPENAI_API_KEY` | `sk-proj-xxx...` | ✅ Yes | OpenAI API key for LLM and embeddings |
| `OPENAI_MODEL` | `gpt-4o-mini-2024-07-18` | No (has default) | Model for query translation |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | No (has default) | Model for semantic search |
| `TYPESENSE_API_KEY` | `xyz123...` | ✅ Yes | Typesense Cloud API key |
| `TYPESENSE_HOST` | `xxx.a1.typesense.net` | ✅ Yes | Typesense Cloud hostname |
| `TYPESENSE_PORT` | `443` | No (default: 443) | Typesense port (usually 443) |
| `TYPESENSE_PROTOCOL` | `https` | No (default: https) | Protocol for Typesense |
| `NEON_DATABASE_URL` | `postgresql://...` | ✅ Yes | Full Neon database connection string |
| `FLASK_ENV` | `production` | No (default: dev) | Flask environment mode |
| `FLASK_PORT` | `5001` | No (default: 5001) | Port for Flask to listen on |

---

## Frontend Environment Variables

### Local Development (.env.local)

Create `frontend-next/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:5001
```

### Production (Vercel/Netlify)

Set in your deployment platform:

| Variable | Example Value | Required | Description |
|----------|---------------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://your-api.onrender.com` | ✅ Yes | Backend API URL |

**Important:** Next.js requires variables exposed to the browser to be prefixed with `NEXT_PUBLIC_`.

---

## How to Get Each API Key

### 1. OpenAI API Key

1. Go to https://platform.openai.com
2. Sign up or log in
3. Navigate to API Keys: https://platform.openai.com/api-keys
4. Click "Create new secret key"
5. Copy the key (starts with `sk-proj-` or `sk-`)
6. **Important:** Add credits to your account (paid service)
   - Go to Billing: https://platform.openai.com/account/billing
   - Add at least $10-20 for initial testing

**Cost estimate:** ~$0.01 per search query

### 2. Typesense Cloud API Key

1. Go to https://cloud.typesense.org
2. Sign up or log in
3. Click "Create Cluster"
4. Select plan:
   - **Free**: 1M docs, good for testing
   - **Paid**: Starts at $0.03/hour for production
5. Once cluster is created, click on it
6. Copy the **API Key** (usually shown on the cluster dashboard)
7. Copy the **Host** (e.g., `xxx.a1.typesense.net`)

**Note:** Port is usually `443` and protocol is `https`

### 3. Neon Database Connection String

1. Go to https://neon.tech
2. Sign up or log in
3. Click "Create Project"
4. Name your project (e.g., "mercedes-products")
5. Select region (closest to your users)
6. Once created, click on the project
7. Go to "Connection Details"
8. Copy the **Connection string** (starts with `postgresql://`)
   - Example: `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

**Note:** Free tier includes 0.5GB storage, good for 30k+ products

---

## Setting Environment Variables in Deployment Platforms

### Render

1. Go to your service in Render dashboard
2. Click "Environment" in sidebar
3. Click "Add Environment Variable"
4. Enter key and value
5. Click "Save Changes"
6. Service will auto-redeploy

**Via render.yaml:**
- Non-secret values are in `render.yaml`
- Secret values (API keys) must be added manually via dashboard

### Vercel

1. Go to your project in Vercel dashboard
2. Click "Settings" → "Environment Variables"
3. Enter variable name and value
4. Select environments (Production, Preview, Development)
5. Click "Save"
6. Redeploy for changes to take effect

**Via CLI:**
```bash
vercel env add NEXT_PUBLIC_API_URL production
# Enter value when prompted
```

### Railway

1. Go to your project in Railway dashboard
2. Click on your service
3. Click "Variables" tab
4. Click "New Variable"
5. Enter key and value
6. Deploy will trigger automatically

### Fly.io

```bash
# Set secrets via CLI
fly secrets set OPENAI_API_KEY=sk-proj-xxx
fly secrets set TYPESENSE_API_KEY=xyz123
fly secrets set NEON_DATABASE_URL=postgresql://...

# View all secrets
fly secrets list
```

---

## Verification Checklist

After setting all environment variables:

### Backend Verification

```bash
# Test locally
python src/app.py

# Should see:
# - No validation errors
# - Server starts successfully
# - Shows all configuration details
```

**Test API:**
```bash
curl http://localhost:5001/health
# Should return: {"status": "healthy"}
```

### Frontend Verification

```bash
# In frontend-next directory
npm run dev

# Should see:
# - No environment variable warnings
# - App starts successfully
```

**Test in browser:**
- Open http://localhost:3000
- Open browser console (F12)
- Look for any API connection errors

---

## Security Best Practices

1. **Never commit `.env` files** to Git
   - Already in `.gitignore`
   - Always use `.env.example` as template

2. **Rotate API keys regularly**
   - Every 3-6 months
   - Immediately if compromised

3. **Use different keys for dev/prod**
   - Separate OpenAI projects
   - Separate Typesense clusters
   - Separate Neon databases

4. **Monitor API usage**
   - Set up billing alerts in OpenAI
   - Monitor Typesense query volume
   - Track Neon database size

5. **Restrict API key permissions**
   - OpenAI: Use project-specific keys
   - Neon: Use read-only roles where possible

---

## Troubleshooting

### "Invalid API key" errors

**OpenAI:**
- Verify key starts with `sk-` or `sk-proj-`
- Check billing is enabled: https://platform.openai.com/account/billing
- Try creating a new key

**Typesense:**
- Verify you're using the **Admin API Key**, not Search-only key
- Check cluster status in Typesense Cloud dashboard

**Neon:**
- Verify connection string includes `?sslmode=require`
- Check database is not suspended (free tier limitation)

### "Connection refused" errors

**Typesense:**
- Ping the host: `ping xxx.a1.typesense.net`
- Verify port is `443` and protocol is `https`
- Check firewall/network settings

**Neon:**
- Test connection: `psql "postgresql://..."`
- Verify SSL mode is required
- Check IP allowlist (if enabled)

### Environment variables not loading

**Backend:**
- Verify `.env` file is in project root (not in `src/`)
- Check for typos in variable names
- Run `python test_config.py` to verify

**Frontend:**
- Verify variables start with `NEXT_PUBLIC_`
- Restart dev server after changing `.env.local`
- Clear Next.js cache: `rm -rf .next`

---

## Cost Optimization Tips

1. **Use smaller OpenAI models**
   - Current: `gpt-4o-mini` (already optimized)
   - Embeddings: `text-embedding-3-small` (cheapest)

2. **Cache frequent queries**
   - Implement Redis caching
   - Reduce redundant OpenAI calls

3. **Optimize Typesense plan**
   - Start with free tier
   - Upgrade only when needed
   - Use smallest cluster that meets needs

4. **Monitor and alert**
   - Set up billing alerts in all services
   - Track usage patterns
   - Identify and optimize expensive queries

---

## Quick Reference

**Check all environment variables are set:**

```bash
# Backend (from project root)
python -c "from config import Config; Config.validate(); print('✅ All required env vars set!')"

# Frontend (from frontend-next/)
echo $NEXT_PUBLIC_API_URL
```

**Export environment variables from .env:**

```bash
# Load .env into current shell (for testing)
export $(cat .env | xargs)
```

**Test connections:**

```bash
# Test OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | head

# Test Typesense
curl "https://$TYPESENSE_HOST/health" \
  -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"

# Test Neon (requires psql)
psql "$NEON_DATABASE_URL" -c "SELECT version();"
```

---

## Support

If you encounter issues:

1. Check this document first
2. Review DEPLOYMENT.md for platform-specific guidance
3. Check the service status pages:
   - OpenAI: https://status.openai.com
   - Typesense: https://status.typesense.org
   - Neon: https://status.neon.tech

**Still stuck?** Review error messages carefully - they usually indicate which variable is missing or invalid.
