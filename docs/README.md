# Documentation Index

This directory contains all project documentation organized by category.

## Quick Links

- **Production App**: [https://mercedes-nl-search.vercel.app](https://mercedes-nl-search.vercel.app)
- **API Endpoint**: [https://mercedes-search-api.onrender.com](https://mercedes-search-api.onrender.com)
- **Main README**: [../README.md](../README.md)
- **AI Assistant Context**: [../CLAUDE.md](../CLAUDE.md)

---

## 📦 Deployment Guides

Step-by-step guides for deploying the application to production.

### Getting Started

1. **[Quick Start (30 min)](deployment/DEPLOYMENT_QUICKSTART.md)** ⭐ START HERE
   - Fast deployment guide for production
   - All platforms in one place
   - Prerequisites and common issues

2. **[Environment Variables Setup](deployment/ENV_SETUP.md)**
   - Complete reference for all environment variables
   - How to obtain API keys
   - Platform-specific configuration

3. **[Typesense Cloud Setup](deployment/TYPESENSE_CLOUD_SETUP.md)**
   - Create Typesense Cloud cluster
   - Get credentials and API keys
   - Memory sizing guide

### Platform Guides

4. **[Complete Deployment Guide](deployment/DEPLOYMENT.md)**
   - Comprehensive deployment reference
   - Multiple platform options
   - Architecture diagrams
   - Troubleshooting

5. **[Next Steps After Deployment](deployment/NEXT_STEPS.md)**
   - Post-deployment checklist
   - Testing your deployment
   - Monitoring and maintenance

---

## 📚 Reference Documentation

Alternative setups, comparisons, and advanced topics.

### Infrastructure Options

- **[Self-Hosted vs Cloud Comparison](reference/SELF_HOSTED_VS_CLOUD.md)**
  - Cost analysis
  - Pros and cons
  - Decision framework

- **[Typesense on DigitalOcean](reference/TYPESENSE_DIGITALOCEAN_SETUP.md)**
  - Self-hosting Typesense on DigitalOcean
  - $12/month alternative to Typesense Cloud
  - Complete setup guide

- **[Scaling Strategy](reference/SCALING_STRATEGY.md)**
  - Multi-tenant architecture
  - Memory requirements
  - Cost projections

### Alternative Deployments

- **[GitHub Pages Deployment](reference/DEPLOY_GITHUB_PAGES.md)**
  - Deploy frontend to GitHub Pages (alternative to Vercel)
  - Static export configuration
  - Limitations and considerations

### API Documentation

- **[Mercedes Scientific GraphQL API](reference/mercedes-scientific-graphql-api.md)**
  - GraphQL schema reference
  - Available queries and fields
  - Rate limits and pagination

---

## 🏗️ Architecture & Design

Technical deep-dives into how the system works.

- **[How It Works](architecture/HOW_IT_WORKS.md)**
  - Hybrid search architecture
  - Query translation flow
  - Semantic vs keyword search
  - Embedding generation

---

## 🧪 Testing

Test files and testing documentation.

Located in `/tests` directory:
- `test_config.py` - Configuration validation tests
- `test_hybrid_approach.py` - Hybrid search validation

---

## 📋 Document Categories

### By Purpose

**For First-Time Deployment**:
1. [DEPLOYMENT_QUICKSTART.md](deployment/DEPLOYMENT_QUICKSTART.md)
2. [ENV_SETUP.md](deployment/ENV_SETUP.md)
3. [TYPESENSE_CLOUD_SETUP.md](deployment/TYPESENSE_CLOUD_SETUP.md)

**For Understanding the System**:
1. [../README.md](../README.md)
2. [../CLAUDE.md](../CLAUDE.md)
3. [HOW_IT_WORKS.md](architecture/HOW_IT_WORKS.md)

**For Advanced Topics**:
1. [SCALING_STRATEGY.md](reference/SCALING_STRATEGY.md)
2. [SELF_HOSTED_VS_CLOUD.md](reference/SELF_HOSTED_VS_CLOUD.md)
3. [TYPESENSE_DIGITALOCEAN_SETUP.md](reference/TYPESENSE_DIGITALOCEAN_SETUP.md)

---

## 🔧 Quick Commands Reference

### Local Development

```bash
# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Setup NL model (required)
python src/setup_nl_model.py

# Index products (choose one)
python src/indexer_neon.py      # RECOMMENDED: 34k+ products
python src/indexer.py           # LEGACY: 5-10k products

# Start backend
python src/app.py

# Start frontend (in another terminal)
cd frontend-next
npm install
npm run dev
```

### Production Deployment

```bash
# See DEPLOYMENT_QUICKSTART.md for complete guide

# Backend: Deploy to Render
# Frontend: Deploy to Vercel
# Search: Typesense Cloud (8GB cluster)
# Database: Neon PostgreSQL
```

### Testing

```bash
# Test API
curl https://mercedes-search-api.onrender.com/health

# Test search
curl -X POST https://mercedes-search-api.onrender.com/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gloves under $50"}'
```

---

## 📝 Contributing to Documentation

When adding new documentation:

1. Place files in the appropriate directory:
   - `/docs/deployment/` - Deployment and setup guides
   - `/docs/reference/` - Reference materials and comparisons
   - `/docs/architecture/` - Technical architecture docs

2. Update this README.md index

3. Link from main README.md if it's a key document

4. Keep CLAUDE.md updated for AI assistant context

---

## 🆘 Need Help?

1. Check the [DEPLOYMENT_QUICKSTART.md](deployment/DEPLOYMENT_QUICKSTART.md) troubleshooting section
2. Review [../CLAUDE.md](../CLAUDE.md) for common issues
3. Check platform-specific docs (Typesense, OpenAI, etc.)

---

**Last Updated**: 2025-10-16

**Production Status**: ✅ Live and operational
