# Mercedes Scientific Natural Language Search

AI-powered natural language search for Mercedes Scientific products using **Typesense NL + RAG Middleware** (Retrieval-Augmented Generation) with single-call architecture.

## Production Deployment

**Status**: ✅ **LIVE (v2.3.0)**

- **Frontend**: [https://mercedes-nl-search.vercel.app](https://mercedes-nl-search.vercel.app) (Vercel)
- **Backend API**: [https://mercedes-nl-search-production.up.railway.app](https://mercedes-nl-search-production.up.railway.app) (Railway)
- **Backend API (Staging)**: [https://mercedes-nl-search-staging.up.railway.app](https://mercedes-nl-search-staging.up.railway.app) (Railway)
- **Search Engine**: Typesense Cloud (8GB cluster)
- **Middleware**: [https://web-production-a5d93.up.railway.app](https://web-production-a5d93.up.railway.app) (Railway)
- **Database**: Neon PostgreSQL
- **AI Models**: OpenAI GPT-4o-mini (RAG middleware) + text-embedding-3-small

**Why Railway?** Backend migrated from Render to eliminate 30-50 second cold start delays caused by free tier inactivity timeout. See [docs/RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md).

**Deployed Stack**: 34,607 products indexed with full semantic search, intelligent category classification, and synonym matching.

**Documentation**:
- **Production Deployment**: See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **For AI Assistants**: See [CLAUDE.md](CLAUDE.md) for detailed project context

## Features

- 🚀 **Single-Call Architecture**: Typesense NL + Railway middleware in one API call
- 🤖 **RAG Category Classification**: Middleware handles intelligent context-aware classification
- 🔍 **Model Number Search**: Handles SKU variations ("tnr700s" → "TNR 700S")
- 📚 **Synonym Matching**: 35 synonym groups (pipette/pipettor, nitrile/nbr, etc.)
- 🧠 **Semantic Understanding**: OpenAI embeddings for query intent
- 🎯 **Smart Query Translation**: Automatic filter extraction (price, stock, temporal)
- ⚡ **Fast Hybrid Search**: Typesense vector + keyword search
- 📊 **34,000+ Products**: Direct access via Neon PostgreSQL database
- 🏷️ **Advanced Filtering**: Price, stock, brand, size, color, sale prices
- 🎨 **Rich Product Attributes**: Brand, size, color, physical form, CAS numbers
- 💰 **Cost Optimized**: Uses `text-embedding-3-small` for embeddings
- 🔒 **Conservative Classification**: High-confidence category detection only

## Architecture

### Typesense NL + Middleware Architecture

The system uses **single-call architecture** with Railway middleware for RAG-based category classification:

```mermaid
flowchart TB
    A["👤 User Query<br/>nitrile gloves, powder-free, in stock, under $30"]
    B["🌐 FastAPI Backend<br/>(/api/search)"]
    C["🔍 Typesense NL Search<br/>nl_query=true, nl_model_id='middleware-rag-vllm'"]
    D["🤖 Railway Middleware<br/>RAG Processing<br/>https://web-production-a5d93.up.railway.app"]
    E["📦 Retrieves 20 Products<br/>Using normalized fields"]
    F["🧠 GPT-4o-mini Classification<br/>Context-aware category detection"]
    G["📤 Returns Search Params<br/>{q: 'nitrile glove powder-free', filter_by: 'categories:=Gloves && stock_status:=IN_STOCK && price:<30'}"]
    H["🎯 Typesense Executes Search<br/>With middleware parameters"]
    I["✨ Results<br/>3 nitrile gloves, powder-free, in stock, under $30"]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I

    style A fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    style B fill:#fff9c4,stroke:#f9a825,stroke-width:2px,color:#000
    style C fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000
    style D fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    style E fill:#f5f5f5,stroke:#616161,stroke-width:2px,color:#000
    style F fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000
    style G fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px,color:#000
    style H fill:#c8e6c9,stroke:#388e3c,stroke-width:2px,color:#000
    style I fill:#b2ebf2,stroke:#0097a7,stroke-width:3px,color:#000
```

**Full Documentation**: See [`docs/FEATURE_STATUS.md`](docs/FEATURE_STATUS.md) for implementation details.

### Why Typesense NL + Middleware?

1. **Single-Call Architecture**:
   - **One API call**: Typesense handles middleware communication internally
   - **Railway middleware**: OpenAI-compatible endpoint for RAG processing
   - **Automatic integration**: Typesense NL calls middleware, executes search, returns results

2. **Context-Aware RAG Classification**:
   - Retrieves 20 products as context (using normalized fields for model number search)
   - GPT-4o-mini analyzes product context for category detection
   - Conservative on ambiguous queries (returns null when uncertain)
   - **84.6% accuracy** on test dataset

3. **Model Number Search**:
   - Normalized fields (`sku_normalized`, `name_normalized`) handle SKU variations
   - "tnr700s" → finds "TNR 700S" products
   - "blu touch" → finds "BluTouch" products
   - 100:4 weighting ratio prioritizes original fields while supporting edge cases

4. **Hybrid Search Foundation**:
   - **Semantic Search**: Finds products by meaning (OpenAI embeddings)
   - **Keyword Search**: Finds exact matches (SKUs, brands)
   - **Synonym Matching**: 35 synonym groups (pipette/pipettor, nitrile/nbr, etc.)
   - **Combined Ranking**: Best of all approaches

## Prerequisites

- Python 3.9+
- OpenAI API Key (for GPT-4o-mini and embeddings)
- Typesense Cloud account or self-hosted instance (v29.0+)
- Neon PostgreSQL database (for full 34k+ product catalog access)

## Setup

### 1. Clone and Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini-2024-07-18          # For query translation
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # For semantic search

# Typesense Configuration
TYPESENSE_HOST=your-cluster.a1.typesense.net
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https
TYPESENSE_API_KEY=your-admin-api-key

# Neon Database (RECOMMENDED - for 34k+ products)
NEON_DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require

# Mercedes GraphQL API (LEGACY - for 5-10k products)
MERCEDES_GRAPHQL_URL=https://www.mercedesscientific.com/graphql

# Server Configuration
ENVIRONMENT=development    # Environment: development, staging, production
SERVER_PORT=5001           # Port for FastAPI server

# Backward Compatibility (deprecated, use above instead)
# FLASK_ENV=development    # Old name, still supported
# FLASK_PORT=5001          # Old name, still supported
```

### 3. Index Products with Embeddings

```bash
# Fetch products from Neon PostgreSQL and index to Typesense
python src/indexer_neon.py
```

This will:
- Fetch all 34,000+ products from Neon database
- Generate embeddings using OpenAI's text-embedding-3-small
- Index products with semantic search capabilities
- Typical time: ~35-45 minutes for full catalog

### 4. Register vLLM Middleware Model

```bash
# One-time setup: Register vLLM middleware model in Typesense
python src/setup_middleware_model.py
```

**Note**: The middleware is deployed on Railway (https://web-production-a5d93.up.railway.app). This command registers the model in Typesense to use the Railway endpoint. The middleware provides intelligent query parsing and category detection using GPT-4o-mini.

#### What Happens During Indexing

**Option A: Neon Database Indexer (RECOMMENDED)**

The Neon indexer provides direct database access with no limitations:

1. ✓ Creates Typesense collection with enhanced schema (10+ new fields)
2. ✓ Connects to Neon PostgreSQL database
3. ✓ Fetches all 34,000+ products with single optimized query
4. ✓ Merges store views for complete product data
5. ✓ Parses additional_attributes for product specs (brand, size, color, etc.)
6. ✓ Generates embeddings automatically via OpenAI (`text-embedding-3-small`)
7. ✓ Indexes products with enhanced semantic search

**Expected Output:**
```
============================================================
Mercedes Scientific Product Indexer (Neon → Typesense)
============================================================
Mode: Full indexing (all products from Neon)
Source: Neon Database (catalog_products)
Embedding Model: text-embedding-3-small
Collection: mercedes_products
============================================================

Connecting to Neon database...
⏳ Executing database query...
✓ Query executed in 2.3s

⏳ Fetching and transforming products...
  Fetched 10,000 rows (4347 rows/sec)...
  Fetched 20,000 rows (4521 rows/sec)...
  Fetched 34,607 rows (4423 rows/sec)...
✓ Fetch completed in 7.8s

============================================================
✓ Total unique products fetched: 34,607
============================================================

Indexing 34,607 products to Typesense...
  Batch 1/347: Indexed 100/100 products (Total: 100/34,607 | 0.3% complete)
  ...
✓ Successfully indexed: 34,607 products
```

**Timing**: ~35-45 minutes for full catalog

**For testing** (faster indexing with limited products):

```bash
# Neon indexer with 1000 products
python3
>>> from src.indexer_neon import NeonProductIndexer
>>> indexer = NeonProductIndexer()
>>> indexer.run(max_products=1000)
```

### 5. Run the API Server

```bash
python src/app.py
```

Server runs on `http://localhost:5001`

You should see:
```
============================================================
Mercedes Scientific Natural Language Search API
============================================================
Environment: development
Server: http://localhost:5001
Typesense: https://your-cluster.a1.typesense.net:443
Collection: mercedes_products
OpenAI Model: gpt-4
============================================================
```

### 5. Start the Frontend UI (Optional)

```bash
# In a new terminal
./start-ui.sh
```

Frontend will be available at `http://localhost:5173`

**Or manually:**
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Search Products

**POST /api/search**

```bash
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "gloves under $50",
    "max_results": 20
  }'
```

Response:
```json
{
  "results": [
    {
      "product_id": 12345,
      "name": "ProAdvantage® Vinyl Exam Gloves, Powder-Free, Clear, Medium",
      "sku": "PRA P359403",
      "price": 40.00,
      "stock_status": "IN_STOCK",
      "categories": ["Gloves & Apparel"],
      "description": "Vinyl exam gloves, powder-free, latex-free...",
      "image_url": "https://...",
      "url_key": "proadvantage-vinyl-exam-gloves"
    }
  ],
  "total": 25,
  "query_time_ms": 150,
  "typesense_query": {
    "q": "gloves",
    "filter_by": "price:[0..50]",
    "sort_by": "price:asc",
    "per_page": 20
  }
}
```

**GET /api/search** (alternative)

```bash
curl "http://localhost:5001/api/search?q=pipettes%20under%20$50&limit=10"
```

### Health Check

```bash
curl http://localhost:5001/health
```

## Example Queries

The system understands natural language and extracts:
- Product types
- Price ranges (including sale prices)
- Stock requirements and quantities
- Brand filters
- Product attributes (size, color, physical form)
- Temporal sorting (latest, newest)
- Categories
- Semantic meaning

### Basic Queries
```
"gloves under $50"
"pipettes in stock"
"microscope slides over $500"
"surgical scissors under $100"
```

### Advanced Queries (NEW - Conservative Filtering Approach)
```
# Reliable filters (price, stock, special_price, temporal)
"products on sale under $50"                     → special_price + price filters
"latest microscopes"                             → temporal sort (created_at)
"recently updated reagents"                      → temporal sort (updated_at)
"pipettes in stock under $100"                   → stock + price filters

# Semantic matching (color, size, brand in query - not strict filters)
"Mercedes Scientific nitrile gloves size medium" → semantic brand + size matching
"clear liquid chemicals 1 gallon"                → semantic color + size matching
"white lab coats size large"                     → semantic color + size matching
"blue gloves powder-free"                        → semantic color matching
```

**Why Conservative?** Attributes (color, size, brand) have incomplete data. Semantic matching provides better recall without excluding products with missing attributes.

### Semantic Queries (powered by embeddings)
```
"protective hand covering for medical use"  → finds gloves
"liquid measurement tools"                   → finds pipettes
"glass slides for viewing samples"          → finds microscope slides
"chemical solutions for lab testing"        → finds reagents
"sterile instruments for cutting tissue"    → finds surgical blades
```

### Complex Queries
```
"vinyl exam gloves powder-free under $50"
"serological pipettes in stock between $100 and $200"
"surgical instruments in stock"
"nitrile gloves latex-free under $40"
"Greiner Bio-One petri dishes on sale"       → brand + special_price
"cheapest centrifuge"                        → price sort ascending
```

## How It Works

### 1. Single-Call Architecture (Typesense NL)

User query goes through a **single API call** with automatic middleware integration:

1. **FastAPI Backend** receives query → calls Typesense with `nl_query=true`
2. **Typesense NL** automatically calls Railway middleware for processing
3. **Railway Middleware** performs RAG-based category classification
4. **Typesense** executes search with middleware parameters and returns results

Example:
```
Input: "gloves under $50"

Typesense → Middleware:
  Middleware retrieves 20 products as context
  GPT-4o-mini analyzes context and extracts:
    - q: "gloves"
    - filter_by: "categories:=Gloves && price:<50"

Middleware → Typesense:
  Returns search parameters

Typesense → API:
  Executes search and returns results
```

### 2. Middleware RAG Processing

**a) Product Retrieval** (context gathering)
- Retrieves 20 relevant products using normalized fields
- Groups products by category
- Samples products per category for context

**b) Category Classification** (GPT-4o-mini)
- Analyzes product context
- Detects relevant category with confidence score
- Conservative approach (returns null when uncertain)

**c) Filter Extraction**
- Price ranges, stock status, special prices (reliable fields)
- Temporal sorting (latest, newest)
- **Conservative filtering**: Attributes (color, size, brand) use semantic matching (not strict filters)

### 3. Hybrid Search (Typesense)

The middleware parameters are executed with:

**a) Semantic Search** (vector embeddings)
- Uses `text-embedding-3-small` for query and product embeddings
- Embeddings generated from: name, description, categories, brand
- Finds semantically similar products

**b) Keyword Search**
- Traditional text search with fuzzy matching
- Typo tolerance and prefix matching
- Model number search using normalized fields

**c) Synonym Matching**
- 35 synonym groups expand queries automatically
- Materials: PTFE ⟷ Teflon, Nitrile ⟷ NBR
- Equipment: Pipette ⟷ Pipettor
- Measurements: ml ⟷ milliliter

**d) Filtering & Ranking**
- Applies middleware-extracted filters
- Ranks by relevance (semantic + keyword + category scores)
- Returns top matches with metadata

### 4. Why text-embedding-3-small?

| Model | Cost per 1M tokens | Use Case | Speed |
|-------|-------------------|----------|-------|
| text-embedding-3-small | $0.02 | Embeddings (this project) | Fast |
| text-embedding-3-large | $0.13 | Higher accuracy needed | Fast |
| GPT-4 | $2.50-$7.50 | Query translation only | Medium |

**Benefits:**
- 100x cheaper than GPT-4 for embeddings
- Fast inference
- Good accuracy for product search
- Pre-computed embeddings (only query needs embedding at search time)

**Cost Example** (indexing 27k products):
- Embeddings: ~$0.50 (one-time)
- Per search: ~$0.0001 (query embedding) + ~$0.01 (GPT-4 query translation)

## Project Structure

```
mercedes-natural-language-search/
├── src/
│   ├── app.py                    # FastAPI server (with automatic OpenAPI docs)
│   ├── config.py                 # Configuration management
│   ├── models.py                 # Pydantic data models
│   ├── search.py                 # Search implementation (CURRENT - Typesense NL with vLLM)
│   ├── setup_middleware_model.py # Register vLLM middleware model
│   ├── indexer_neon.py           # Neon database indexer (34k+ products)
│   └── utilities/                # Utility scripts
│       ├── export_collection.py
│       ├── export_nl_system_prompt.py
│       └── setup_synonyms.py
├── middleware/
│   └── openai_middleware.py            # Railway middleware (RAG processing)
├── docs/
│   ├── FEATURE_STATUS.md                     # Current implementation status
│   ├── MODEL_NUMBER_SEARCH_FIX.md            # Model number search documentation
│   ├── CATEGORY_CLASSIFICATION_APPROACHES.md # Technical comparison
│   └── SYNONYM_TESTING_GUIDE.md              # Synonym testing documentation
├── tests/
│   ├── test_category_classification.py  # RAG test suite (26 cases)
│   ├── category_test_cases.py           # Test dataset
│   ├── test_synonyms.py                 # Comprehensive synonym testing
│   ├── test_model_number_search.py      # Model number search tests
│   ├── EVALUATION_RESULTS_FINAL.md      # RAG evaluation results
│   └── EVALUATION_RESULTS.md            # Initial evaluation
├── scripts/
│   └── tests/                           # Test shell scripts
├── database/                  # Exported product data
├── frontend-next/            # Next.js frontend
│   ├── app/
│   │   ├── page.tsx          # Main search page (RAG integration)
│   │   └── components/
│   └── package.json
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── README.md                # This file
├── DEPLOYMENT.md            # Deployment guide
└── CLAUDE.md                # AI assistant context
```

## Technologies

- **Backend**: Python 3.9+, FastAPI
- **Search Engine**: Typesense (vector + keyword search + NL)
- **Middleware**: Railway-deployed OpenAI-compatible RAG service
- **AI/ML**:
  - OpenAI GPT-4o-mini (middleware RAG processing)
  - OpenAI text-embedding-3-small (semantic embeddings)
- **Data Source**: Neon PostgreSQL (34k+ products)
- **Frontend**: Next.js, React, Tailwind CSS
- **Data Models**: Pydantic v2

## Troubleshooting

### Natural Language Search not working

If you see "Middleware connection errors":

1. **Verify middleware model is registered**:
   ```bash
   # Check if vLLM middleware model is registered in Typesense
   python src/setup_middleware_model.py check
   ```

2. **Check Railway middleware status**:
   - The middleware is deployed at: https://web-production-a5d93.up.railway.app
   - Check Railway dashboard for service health
   - Verify middleware logs for incoming requests

### Embeddings not working

If semantic search isn't working:

1. **Verify schema**: Collection must have embedding field
   ```bash
   # Re-run indexer to recreate collection with embeddings
   python src/indexer_neon.py
   ```

2. **Check OpenAI API key**: Typesense needs valid API key for auto-embeddings
   ```bash
   # Verify in .env file
   echo $OPENAI_API_KEY
   ```

### Cannot connect to Neon database

If you see "NEON_DATABASE_URL environment variable is required":

1. **Add Neon connection string to `.env`**:
   ```bash
   NEON_DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require
   ```

2. **Verify connection**:
   ```bash
   # Test database connection
   python3 -c "import psycopg2; import os; psycopg2.connect(os.getenv('NEON_DATABASE_URL'))"
   ```

### Slow indexing

- Embeddings are generated on-the-fly during indexing
- Rate limits: OpenAI has rate limits (check your tier)
- Solution: Index in smaller batches or upgrade OpenAI tier

### Search not returning results

1. **Check if products are indexed**:
   ```bash
   curl "http://localhost:5001/api/search?q=*&limit=1"
   ```

2. **Try simple query first**:
   ```bash
   curl -X POST http://localhost:5001/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "gloves"}'
   ```

3. **Check API logs** for errors

### Pydantic deprecation warnings

If you see warnings about `.dict()`:
- Already fixed in v1.1+ (uses `.model_dump()`)
- Update your code if you see these warnings

### How to get all 34,000+ products?

**Use the Neon Database Indexer**:
- Direct database access via `indexer_neon.py`
- No API limitations
- Requires `NEON_DATABASE_URL` in `.env`
- Full catalog with all product attributes

## Advanced Configuration

### Customize Embedding Fields

Edit `src/indexer_neon.py` - modify the embedding field configuration in the schema:

```python
"embed": {
    "from": ["name", "description", "short_description", "categories", "brand"],
    # Add or remove fields to change what's embedded
}
```

### Adjust Middleware Parameters

The middleware is deployed on Railway. To customize:
- **Category classification prompt**: Edit system prompt in middleware deployment
- **Confidence thresholds**: Adjust in middleware code
- **Filter extraction logic**: Modify middleware's category classification logic

**Note**: The middleware uses vLLM provider (`middleware-rag-vllm`) registered in Typesense via `src/setup_middleware_model.py`.

### Use Different Embedding Model

Edit `.env`:

```bash
# For higher accuracy (more expensive)
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# For legacy compatibility
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

### Change Query Translation Model

Edit `.env`:

```bash
# For cost savings (may reduce accuracy)
OPENAI_MODEL=gpt-4o-mini

# For best results
OPENAI_MODEL=gpt-4
```

## Performance Tips

1. **Index incrementally**: For large catalogs, index in batches
2. **Use CDN for images**: Cache product images
3. **Cache frequent queries**: Add Redis for repeated searches
4. **Pagination**: Use `per_page` parameter wisely
5. **Monitoring**: Track query times and adjust k parameter

## Re-indexing

To re-index with new data or after schema changes:

```bash
python src/indexer_neon.py
```

**Note**: Re-indexing will regenerate all embeddings (costs ~$0.60-0.80 for 34k products)

## API Rate Limits

**OpenAI**:
- Embeddings: 3,000 RPM (requests per minute) on free tier
- GPT-4: Varies by tier

**Typesense**:
- No rate limits (self-hosted)
- Cloud: Check your plan

## Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Deployment

This project is deployed in production. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete deployment instructions including:
- Environment variables setup
- Backend deployment (Railway) - [docs/RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md)
- Frontend deployment (Vercel)
- Typesense configuration
- Troubleshooting guide

## Roadmap

- [ ] Add more embedding models (Cohere, Voyage AI)
- [ ] Implement query caching
- [ ] Add analytics dashboard
- [ ] Support for image search
- [ ] Multi-language support
- [ ] Faceted search UI
- [ ] A/B testing semantic vs keyword

## License

MIT

## Support

- Typesense Docs: https://typesense.org/docs/guide/semantic-search.html
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings

---

Built with Typesense, OpenAI, and Python • Deployed on Vercel + Railway + Typesense Cloud
