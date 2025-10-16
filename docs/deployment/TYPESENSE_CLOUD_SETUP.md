# Using Typesense Cloud

**You're using Typesense Cloud** - a fully managed search service. No server setup needed! ✅

## What You Have

- ✅ Typesense Cloud cluster (launched)
- ✅ 30-day free trial ($0.03/hr after)
- ✅ Built-in high availability
- ✅ Automatic backups
- ✅ Zero maintenance

**Monthly cost after trial:** ~$22/month for 0.5GB cluster (plenty for 34k products)

---

## Getting Your Credentials

1. Go to [cloud.typesense.org](https://cloud.typesense.org)
2. Log in and click on your cluster
3. You'll see your cluster details:

**Copy these values:**
```
Host: xxx.a1.typesense.net
Port: 443
Protocol: https
API Key: (shown in dashboard or generate new)
```

---

## Update Your Local .env File

Update your `.env` file with Typesense Cloud credentials:

```bash
# Typesense Cloud Configuration
TYPESENSE_HOST=xxx.a1.typesense.net  # Your cluster host
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https
TYPESENSE_API_KEY=your_api_key_here

# Keep the rest as is:
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
NEON_DATABASE_URL=postgresql://...
FLASK_ENV=development
FLASK_PORT=5001
```

**Important:** Replace `xxx.a1.typesense.net` and `your_api_key_here` with your actual values from Typesense Cloud dashboard.

---

## Test Your Connection

```bash
# Test from local machine
python src/app.py

# In another terminal
curl http://localhost:5001/health
```

Should return: `{"status":"healthy"}`

---

## Next Steps: Index Your Products

Now that your Typesense Cloud cluster is ready:

### 1. Register NL Search Model

```bash
# This tells Typesense to use GPT-4o-mini for natural language queries
python src/setup_nl_model.py
```

You should see:
```
✓ Successfully registered NL search model: openai-gpt4o-mini
```

### 2. Index Products to Typesense Cloud

```bash
# This will upload all 34k products to your Typesense Cloud cluster
python src/indexer_neon.py
```

**This takes 35-45 minutes** due to:
- Fetching 34k products from Neon database (~5 min)
- Generating embeddings via OpenAI (~30 min)
- Uploading to Typesense Cloud (~5 min)

**Progress indicators:**
```
Fetching products from Neon database...
✓ Fetched 34,247 products

Indexing to Typesense...
Batch 1/343: 100 products indexed
Batch 2/343: 100 products indexed
...
✓ Successfully indexed 34,247 products
```

### 3. Test Search

```bash
# Test a search query
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sterile gloves under $50"}'
```

Should return JSON with search results!

---

## Typesense Cloud Dashboard

Visit [cloud.typesense.org](https://cloud.typesense.org) to:

- ✅ View cluster status
- ✅ Monitor usage (queries, bandwidth)
- ✅ Check billing
- ✅ Manage API keys
- ✅ View cluster metrics (CPU, RAM, disk)

---

## What's Different from Self-Hosted?

| Feature | Typesense Cloud | Self-Hosted |
|---------|----------------|-------------|
| **Setup** | ✅ 2 minutes | ⚠️ 20 minutes |
| **Cost** | $22/month | $6/month |
| **Maintenance** | ✅ Zero | Need to update/monitor |
| **High Availability** | ✅ Built-in | Need to set up |
| **Backups** | ✅ Automatic | Need to configure |
| **Scaling** | ✅ Automatic | Manual upgrade |
| **Support** | ✅ Priority (paid) | Community only |

**You chose Cloud = Zero hassle, enterprise features!** ✅

---

## Deployment with Typesense Cloud

When deploying to Render/Vercel (see DEPLOYMENT_QUICKSTART.md):

**Use the same Typesense Cloud credentials:**
```
TYPESENSE_HOST=xxx.a1.typesense.net
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https
TYPESENSE_API_KEY=your_api_key
```

**Local and production use the same Typesense cluster!**

---

## Cost Management

### Free Trial
- ✅ 720 hours (30 days) FREE
- ✅ No credit card required initially
- ⚠️ After 30 days: $0.03/hr = ~$22/month

### Monitor Usage

1. Go to Typesense Cloud dashboard
2. Click "Billing"
3. View current usage and costs
4. Set up billing alerts

### Cost Optimization Tips

**If cost becomes an issue:**

1. **Reduce cluster size** (if you're using oversized cluster)
   - 0.5GB is enough for 34k products

2. **Optimize queries** to reduce API calls
   - Implement caching in your app
   - Cache frequent searches

3. **Consider self-hosting** later
   - Switch to DigitalOcean ($6/month)
   - See TYPESENSE_DIGITALOCEAN_SETUP.md
   - Easy migration (1-2 hours)

---

## Migration Path (If Needed Later)

**If you decide to switch to self-hosted later:**

See `SELF_HOSTED_VS_CLOUD.md` for comparison and `TYPESENSE_DIGITALOCEAN_SETUP.md` for migration guide.

**Migration is easy:**
1. Set up DigitalOcean droplet (20 min)
2. Update .env with new host
3. Re-run indexer
4. Switch traffic
5. Cancel Typesense Cloud

**Downtime:** < 5 minutes

---

## Troubleshooting

### Can't connect to Typesense Cloud

**Check:**
```bash
# Test connection directly
curl "https://YOUR_HOST.a1.typesense.net/health" \
  -H "X-TYPESENSE-API-KEY: YOUR_API_KEY"
```

Should return: `{"ok":true}`

**If error:**
- ✅ Verify API key is correct (copy from dashboard)
- ✅ Verify host is correct (should end in .typesense.net)
- ✅ Check cluster is running (dashboard should show "Active")

### Indexing is slow

**This is normal!** Indexing 34k products takes 35-45 minutes due to:
- OpenAI embedding generation (rate limits)
- Network upload time

**Speed it up:**
- Can't be avoided for initial index
- Subsequent re-indexes are faster (use update instead of recreate)

### High costs after trial

**Options:**
1. **Downgrade cluster** (if using larger than needed)
2. **Optimize usage** (reduce unnecessary searches)
3. **Migrate to self-hosted** ($6/month on DigitalOcean)

---

## Quick Reference

**Get cluster info:**
```bash
# Visit dashboard
https://cloud.typesense.org

# Or API
curl "https://YOUR_HOST/collections" \
  -H "X-TYPESENSE-API-KEY: YOUR_API_KEY"
```

**Check collection status:**
```bash
curl "https://YOUR_HOST/collections/mercedes_products" \
  -H "X-TYPESENSE-API-KEY: YOUR_API_KEY"
```

**Test search:**
```bash
curl "https://YOUR_HOST/collections/mercedes_products/documents/search?q=gloves" \
  -H "X-TYPESENSE-API-KEY: YOUR_API_KEY"
```

---

## Summary

✅ **You're all set with Typesense Cloud!**

**Next steps:**
1. Update `.env` with Typesense Cloud credentials
2. Run `python src/setup_nl_model.py`
3. Run `python src/indexer_neon.py`
4. Follow `DEPLOYMENT_QUICKSTART.md` to deploy

**Benefits:**
- Zero server management
- Enterprise-grade reliability
- Automatic backups & scaling
- Focus on your app, not infrastructure

**Cost:** ~$22/month (30-day free trial)

**Questions?** Check the Typesense Cloud docs: https://typesense.org/docs/guide/
