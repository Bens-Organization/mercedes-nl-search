# Mercedes Scientific Natural Language Search

AI-powered natural language search for Mercedes Scientific products using **RAG Dual LLM Approach** (Retrieval-Augmented Generation) with Typesense and OpenAI.

## Production Deployment

**Status**: ✅ **LIVE (v2.2.0)**

- **Frontend**: [https://mercedes-nl-search.vercel.app](https://mercedes-nl-search.vercel.app)
- **Backend API**: [https://mercedes-search-api.onrender.com](https://mercedes-search-api.onrender.com)
- **Search Engine**: Typesense Cloud (8GB cluster)
- **Database**: Neon PostgreSQL
- **AI Models**: OpenAI GPT-4o-mini (dual LLM) + text-embedding-3-small

**Deployed Stack**: 34,607 products indexed with full semantic search and intelligent category classification.

**Documentation**:
- **Production Deployment**: See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **For AI Assistants**: See [CLAUDE.md](CLAUDE.md) for detailed project context

## Features

- 🤖 **Dual LLM RAG Approach**: Two-stage AI processing for superior accuracy (84.6%)
- 🔍 **Intelligent Category Classification**: Context-aware category detection with confidence scoring
- 🧠 **Semantic Understanding**: Uses OpenAI embeddings to understand query intent
- 🎯 **Smart Query Translation**: GPT-4o-mini extracts filters, sorts, and attributes
- ⚡ **Fast Hybrid Search**: Powered by Typesense vector + keyword search
- 📊 **34,000+ Products**: Direct access via Neon PostgreSQL database (no API limits!)
- 🏷️ **Advanced Filtering**: Price, brand, size, color, stock, temporal queries
- 🎨 **Rich Product Attributes**: Brand, size, color, physical form, sale prices
- 💰 **Cost Optimized**: Uses `text-embedding-3-small` for affordable semantic search
- 🔒 **Conservative Classification**: Returns null for ambiguous queries (no false positives)

## Architecture

### RAG Dual LLM Flow

The system uses a **two-stage AI processing approach** for superior search accuracy:

```mermaid
flowchart TB
    A["👤 User Query<br/>nitrile gloves, powder-free, in stock, under $30"]
    B["🤖 LLM Call 1: Query Translation<br/>Extracts: price, stock, brand, size, color"]
    C["🔍 Retrieval Search<br/>20 products using Semantic + Keyword Search"]
    D["🤖 LLM Call 2: RAG Category Classification<br/>Analyzes context<br/>Detects: Products/Gloves & Apparel/Gloves<br/>Confidence: 0.85"]
    E["🎯 Final Search<br/>Combined filters: categories + price + stock"]
    F["✨ Results<br/>3 relevant products"]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F

    style A fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    style B fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    style C fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000
    style D fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000
    style E fill:#c8e6c9,stroke:#388e3c,stroke-width:2px,color:#000
    style F fill:#b2ebf2,stroke:#0097a7,stroke-width:3px,color:#000
```

**Full Documentation**: See [`docs/RAG_DUAL_LLM_APPROACH.md`](docs/RAG_DUAL_LLM_APPROACH.md)

### Why RAG Dual LLM?

1. **Two-Stage Intelligence**:
   - **Stage 1**: NL model extracts filters (price, stock, attributes)
   - **Stage 2**: RAG analyzes retrieved products for category detection

2. **Context-Aware Classification**:
   - LLM sees actual product context before deciding category
   - Handles exact matches and semantic queries correctly
   - Conservative on ambiguous queries (returns null when uncertain)

3. **Superior Accuracy**:
   - **84.6% accuracy** on test dataset
   - Improved handling of edge cases vs. single LLM approach
   - Transparent reasoning (debug mode shows LLM's decision process)

4. **Hybrid Search Foundation**:
   - **Semantic Search**: Finds products by meaning (embeddings)
   - **Keyword Search**: Finds exact matches (SKUs, brands)
   - **Combined Ranking**: Best of both worlds

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

# Flask Configuration
FLASK_ENV=development
FLASK_PORT=5001
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

### 4. Start Middleware Server

```bash
# Start OpenAI-compatible middleware for category classification
python src/openai_middleware.py
```

The middleware provides intelligent query parsing and category detection using GPT-4o-mini.

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

### 1. Query Translation (GPT-4)

User query is sent to GPT-4 which extracts:
- Search terms (`q`)
- Filters (`filter_by`): price ranges, stock status, categories
- Sorting (`sort_by`)

Example:
```
Input: "gloves under $50"
Output: {
  "q": "gloves",
  "filter_by": "price:[0..50]",
  "sort_by": "price:asc"
}
```

### 2. Hybrid Search (Typesense)

The structured query is executed with:

**a) Semantic Search** (vector embeddings)
- Generates embedding for query using `text-embedding-3-small`
- Searches against product embeddings (generated from: name, description, categories)
- Finds semantically similar products

**b) Keyword Search**
- Traditional text search across fields
- Fuzzy matching, typo tolerance

**c) Filtering & Ranking**
- Applies price/stock/category filters
- Ranks results by relevance (semantic + keyword scores)
- Returns top matches

### 3. Why text-embedding-3-small?

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
│   ├── app.py                    # Flask API server
│   ├── config.py                 # Configuration management
│   ├── models.py                 # Pydantic data models
│   ├── search_middleware.py      # Middleware search (CURRENT - decoupled architecture)
│   ├── openai_middleware.py      # OpenAI-compatible middleware server
│   ├── indexer_neon.py           # Neon database indexer (34k+ products)
│   └── utilities/                # Utility scripts
│       ├── export_collection.py
│       ├── export_nl_system_prompt.py
│       └── setup_synonyms.py
├── docs/
│   ├── RAG_DUAL_LLM_APPROACH.md              # RAG implementation guide
│   ├── CATEGORY_CLASSIFICATION_APPROACHES.md # Technical comparison
│   └── SYNONYM_TESTING_GUIDE.md              # Synonym testing documentation
├── tests/
│   ├── test_category_classification.py  # RAG test suite (26 cases)
│   ├── category_test_cases.py           # Test dataset
│   ├── test_synonyms.py                 # Comprehensive synonym testing
│   ├── EVALUATION_RESULTS_FINAL.md      # RAG evaluation results
│   ├── EVALUATION_RESULTS.md            # Initial evaluation
│   └── FINAL_SUMMARY.md                 # Implementation summary
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

- **Backend**: Python 3.9+, Flask
- **Search Engine**: Typesense (vector + keyword search)
- **AI/ML**:
  - OpenAI GPT-4 (query translation)
  - OpenAI text-embedding-3-small (semantic embeddings)
- **Data Source**: Mercedes Scientific GraphQL API
- **Frontend**: React, Vite, Tailwind CSS
- **Data Models**: Pydantic v2

## Troubleshooting

### Natural Language Search not working

If you see "Middleware connection errors":

1. **Ensure middleware is running**:
   ```bash
   # Start the middleware server
   python src/openai_middleware.py
   ```

2. **Verify middleware URL**:
   ```bash
   # Check MIDDLEWARE_URL in .env
   echo $MIDDLEWARE_URL
   ```

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

Edit `src/openai_middleware.py` to customize:
- Category classification prompt
- Confidence thresholds
- Filter extraction logic

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

This project is deployed in production. See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment instructions including:
- Environment variables setup
- Backend deployment (Render)
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

Built with Typesense, OpenAI, and Python • Deployed on Vercel + Render + Typesense Cloud
