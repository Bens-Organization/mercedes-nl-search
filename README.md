# Mercedes Scientific Natural Language Search

AI-powered natural language search for Mercedes Scientific products using **Hybrid Search** (Semantic + Keyword) with Typesense and OpenAI.

## Features

- 🔍 **Hybrid Search**: Combines semantic (meaning-based) and keyword search for best results
- 🧠 **Semantic Understanding**: Uses OpenAI embeddings to understand query intent
- 🤖 **Smart Query Translation**: GPT-4o-mini converts natural language to structured filters
- ⚡ **Fast Search**: Powered by Typesense vector + keyword search
- 📊 **34,000+ Products**: Direct access via Neon PostgreSQL database (no API limits!)
- 🎯 **Advanced Filtering**: Price, brand, size, color, stock, temporal queries
- 🏷️ **Rich Product Attributes**: Brand, size, color, physical form, sale prices
- 💰 **Cost Optimized**: Uses `text-embedding-3-small` for affordable semantic search

## Architecture

### Hybrid Search Flow

```mermaid
flowchart TD
    A["👤 User Query"] --> B["🤖 GPT-4o-mini<br/>Query Translation"]
    B --> C["📊 Extract:<br/>filters, intents, criteria"]
    C --> D["🔍 Typesense<br/>Hybrid Search"]
    D --> E["🧠 Semantic Search<br/>(text-embedding-3-small)<br/>Finds products by meaning"]
    D --> F["🔤 Keyword Search<br/>Finds products by exact/fuzzy match"]
    E --> G["✨ Combined & Ranked Results"]
    F --> G

    style A fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    style B fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    style C fill:#f5f5f5,stroke:#616161,stroke-width:2px,color:#000
    style D fill:#e8f5e9,stroke:#388e3c,stroke-width:3px,color:#000
    style E fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000
    style F fill:#fff9c4,stroke:#f9a825,stroke-width:2px,color:#000
    style G fill:#e1bee7,stroke:#7b1fa2,stroke-width:3px,color:#000
```

### Why Hybrid Search?

1. **Semantic Search**: Finds products by meaning
   - "protective hand covering" → finds "gloves"
   - "liquid measurement tool" → finds "pipettes"
   - "slides for microscopy" → finds "microscope slides"

2. **Keyword Search**: Finds exact matches
   - SKU numbers, product codes
   - Specific brand names
   - Exact product names

3. **Combined**: Best of both worlds with intelligent ranking

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

### 3. Setup Natural Language Search Model

```bash
# Register OpenAI model with Typesense (required for NL search)
python src/setup_nl_model.py
```

This enables natural language features like:
- "latest microscopes" → temporal sorting
- "Mercedes Scientific gloves" → brand filtering
- "products on sale" → special_price filtering

### 4. Index Products with Embeddings

**Option A: Neon Database (RECOMMENDED - 34k+ products)**

```bash
# Fetch products from Neon PostgreSQL and index to Typesense
python src/indexer_neon.py
```

**Option B: GraphQL API (LEGACY - 5-10k products)**

```bash
# Fetch products from Mercedes GraphQL API and index to Typesense
python src/indexer.py
```

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

**Option B: GraphQL API Indexer (LEGACY)**

The GraphQL indexer uses a **multi-search strategy** to work around the API's 500-product limit:

1. ✓ Creates Typesense collection with basic schema
2. ✓ Fetches products using 100+ different search terms (letters, numbers, product types)
3. ✓ Collects unique products across all searches (typically 5,000-10,000+ products)
4. ✓ Generates embeddings automatically via OpenAI
5. ✓ Indexes products with semantic search enabled

**Timing**: ~10-20 minutes for 5-10k products

#### Indexer Comparison

| Feature | Neon Database (RECOMMENDED) | GraphQL API (LEGACY) |
|---------|----------------------------|---------------------|
| **Products** | 34,000+ | 5,000-10,000 |
| **Indexing Time** | 35-45 min | 10-20 min |
| **API Limits** | None | 500 per query |
| **Product Fields** | 20+ fields | 14 fields |
| **Attributes** | Brand, size, color, etc. | Basic only |
| **Temporal Queries** | ✅ Yes (created_at) | ❌ No |
| **Sale Prices** | ✅ Yes (special_price) | ❌ No |
| **Requirements** | Neon DB access | Public API |

**For testing** (faster indexing with limited products):

```bash
# Neon indexer with 1000 products
python3
>>> from src.indexer_neon import NeonProductIndexer
>>> indexer = NeonProductIndexer()
>>> indexer.run(max_products=1000)

# GraphQL indexer with 1000 products
python3
>>> from src.indexer import MercedesProductIndexer
>>> indexer = MercedesProductIndexer()
>>> indexer.run(max_products=1000)
```

### 4. Run the API Server

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

### Advanced Filter Queries (NEW)
```
"Mercedes Scientific nitrile gloves size medium"  → brand + size filters
"clear liquid chemicals 1 gallon"                → color + physical_form + size
"white lab coats size large"                     → color + size filters
"products on sale under $50"                     → special_price filter
"latest microscopes"                             → temporal sort (created_at)
"recently updated reagents"                      → temporal sort (updated_at)
"in stock items with qty > 50"                   → stock + quantity filters
```

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
│   ├── app.py                 # Flask API server
│   ├── indexer_neon.py        # Neon database indexer (RECOMMENDED)
│   ├── indexer.py            # GraphQL API indexer (LEGACY)
│   ├── search.py             # Hybrid search logic
│   ├── setup_nl_model.py     # Natural language model setup
│   ├── config.py             # Configuration management
│   └── models.py             # Pydantic data models
├── database/                  # Exported product data
│   └── *.csv
├── frontend/                  # React frontend (optional)
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   ├── package.json
│   └── vite.config.js
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .env                     # Your credentials (gitignored)
├── start-ui.sh              # Quick frontend starter script
├── README.md                # This file
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

If you see "WARNING: Natural Language Search model not configured":

```bash
# Setup the NL model (REQUIRED)
python src/setup_nl_model.py

# Verify it was created
python src/setup_nl_model.py check
```

This enables advanced filters like brand, size, color, temporal sorting, etc.

### Embeddings not working

If you see "Fallback: Using keyword-only search":

1. **Check Typesense version**: Requires v29.0+
   ```bash
   # Check your Typesense version in the admin dashboard
   ```

2. **Verify schema**: Collection must have embedding field
   ```bash
   # Re-run indexer to recreate collection with embeddings
   python src/indexer_neon.py  # RECOMMENDED
   # or
   python src/indexer.py       # LEGACY
   ```

3. **Check OpenAI API key**: Typesense needs valid API key for auto-embeddings
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

3. **Alternative**: Use GraphQL indexer (limited to 5-10k products):
   ```bash
   python src/indexer.py
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

**Use the Neon Database Indexer** (RECOMMENDED):
- Direct database access via `indexer_neon.py`
- No API limitations
- Requires `NEON_DATABASE_URL` in `.env`
- Full catalog with all product attributes

**GraphQL API Limitation** (LEGACY):
- Public GraphQL API limits results to 500 products per query
- Multi-search strategy yields only 5,000-10,000 products
- Missing advanced product attributes (brand, size, color, etc.)

## Advanced Configuration

### Customize Embedding Fields

Edit `src/indexer.py` line 45-47:

```python
"embed": {
    "from": ["name", "description", "short_description", "categories"],
    # Add or remove fields to change what's embedded
}
```

### Adjust Semantic Search Weight

Edit `src/search.py` line 188:

```python
"vector_query": f"embedding:({query.q}, k:{query.per_page * 2})",
# Increase k for more semantic results
```

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
# Neon database (RECOMMENDED - 34k+ products)
python src/indexer_neon.py

# GraphQL API (LEGACY - 5-10k products)
python src/indexer.py
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

- Issues: https://github.com/yourusername/mercedes-natural-language-search/issues
- Typesense Docs: https://typesense.org/docs/guide/semantic-search.html
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings

---

Built with ❤️ using Typesense, OpenAI, and Python
