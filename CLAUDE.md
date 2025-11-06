# Project Context for AI Assistants

This file provides context for AI assistants (like Claude) working on this codebase.

## Project Overview

**Mercedes Scientific Natural Language Search** is a **production-deployed** search system that enables users to search through 34,000+ medical and scientific products using natural language queries.

## Production Deployment

**Status**: ✅ **LIVE IN PRODUCTION**

**Stack**:
- **Frontend**: Vercel (https://mercedes-nl-search.vercel.app)
- **Backend API**: Render (https://mercedes-search-api.onrender.com)
- **Search Engine**: Typesense Cloud (8GB cluster)
- **Database**: Neon PostgreSQL (free tier)
- **AI Services**: OpenAI (GPT-4o-mini + text-embedding-3-small)

**Infrastructure**:
- 34,607 products indexed with semantic embeddings
- ~700MB memory usage (embeddings + data)
- Natural language model registered and active
- CORS configured for production frontend

**Documentation**: See `DEPLOYMENT.md` for deployment guide

**Two Indexing Options**:
1. **Neon Database Indexer** (RECOMMENDED): Direct access to 34,000+ products from Neon PostgreSQL database
2. **GraphQL API Indexer** (LEGACY): Limited to 5,000-10,000 products due to API's 500-product limit

### Key Innovation: Typesense NL + RAG Middleware

The system uses **Typesense NL integration with RAG middleware** that combines:
1. **Single API call** to Typesense with natural language processing enabled
2. **Middleware handles RAG internally**: Retrieves context, performs category classification with GPT-4o-mini
3. **Typesense executes search** with middleware-generated parameters (query + filters + category)

This provides intelligent category detection with transparent reasoning while maintaining a simple single-call API.

**Full Documentation**: See `docs/FEATURE_STATUS.md` for comprehensive details.

## Architecture

```mermaid
flowchart TB
    A["👤 User Query<br/>nitrile gloves, powder-free, in stock, under $30"]
    B["🌐 FastAPI Backend<br/>/api/search"]
    C["🔍 Typesense NL Search<br/>nl_query=true, nl_model_id=middleware-rag-vllm"]
    D["🤖 Railway Middleware<br/>RAG Processing"]
    E["📦 Retrieves 20 Products<br/>Groups by categories"]
    F["🧠 GPT-4o-mini Classification<br/>Analyzes context, detects category"]
    G["📤 Returns Search Params<br/>q: nitrile glove powder-free<br/>filter_by: categories:=Gloves && stock_status:=IN_STOCK && price:<30"]
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
    style B fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    style C fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    style D fill:#fce4ec,stroke:#c2185b,stroke-width:3px,color:#000
    style E fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000
    style F fill:#fff9c4,stroke:#f9a825,stroke-width:2px,color:#000
    style G fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px,color:#000
    style H fill:#c8e6c9,stroke:#388e3c,stroke-width:2px,color:#000
    style I fill:#b2ebf2,stroke:#0097a7,stroke-width:3px,color:#000
```

## Tech Stack

### Backend
- **Language**: Python 3.9+
- **Web Framework**: FastAPI
- **Data Validation**: Pydantic v2
- **Environment**: python-dotenv

### Search & AI
- **Search Engine**: Typesense (vector + full-text)
- **LLM**: OpenAI GPT-4 (query translation)
- **Embeddings**: OpenAI text-embedding-3-small
- **Data Source**: Mercedes Scientific GraphQL API

### Frontend (Optional)
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS

## File Structure

```
src/
├── app.py                    # FastAPI server (REST endpoints with automatic OpenAPI docs)
├── config.py                 # Configuration management
├── models.py                 # Pydantic data models
├── search.py                 # Search implementation (CURRENT - Typesense NL with vLLM middleware)
├── setup_middleware_model.py # Register vLLM middleware model in Typesense
├── indexer_neon.py           # Neon database indexer (RECOMMENDED - 34k+ products)
└── utilities/                # Utility scripts
    ├── export_collection.py          # Export Typesense data
    ├── export_nl_system_prompt.py    # Export NL model config
    └── setup_synonyms.py             # Synonym management

src/openai_middleware.py  # OpenAI-compatible RAG middleware (deployed on Railway)

docs/                   # Technical documentation
├── FEATURE_STATUS.md                     # Latest feature implementation status
├── DEPLOYMENT.md                         # Production deployment guide
├── CATEGORY_CLASSIFICATION_APPROACHES.md # Technical comparison of approaches
├── BRAND_PRIORITY_IMPLEMENTATION.md      # Brand priority feature documentation
├── SYNONYM_TESTING_GUIDE.md              # Synonym testing documentation
└── README_TESTS.md                       # Test documentation

tests/                  # Tests and evaluation
├── test_category_classification.py  # Category classification tests (26 cases)
├── test_model_number_search.py      # Model number search fix tests
├── test_middleware_fix.py           # Middleware retrieval tests
├── test_full_middleware_flow.py     # End-to-end middleware flow tests
├── test_synonyms.py                 # Comprehensive synonym testing
├── test_brand_priority.py           # Brand priority feature tests
├── test_hybrid_approach.py          # Hybrid search approach tests
└── category_test_cases.py           # Test dataset

scripts/tests/          # Shell test scripts
├── test_rest_api.sh                 # REST API tests
├── test_staging_api.sh              # Staging environment tests
└── ... (9 shell test scripts)

database/
├── qg91lms7w5rveht3p-1.a1.typesense.net/  # Typesense instance exports (organized by host)
│   ├── nl_model_system_prompt.txt         # NL model system prompt (exported)
│   └── nl_model_system_prompt.json        # Full NL model config (exported)
└── mercedes_products_*.csv                # Product data exports

frontend-next/
├── app/
│   ├── page.tsx        # Main search page with middleware integration
│   └── components/
└── package.json

# Root-level documentation
├── README.md           # User-facing documentation
└── CLAUDE.md          # AI assistant context (this file)
```

**Important**:
- **Technical docs** are in `docs/` directory
- **Tests** are in `tests/` directory
- **Shell scripts** are in `scripts/tests/` directory
- All flowcharts use **Mermaid markdown** with dark text on light backgrounds

## Key Files Explained

### src/config.py
Manages all configuration via environment variables:
- OpenAI API keys and models
- Typesense connection settings
- FastAPI server config

**Important**: All secrets come from `.env` file (never hardcode!)

### src/indexer_neon.py (RECOMMENDED)
Fetches products from Neon PostgreSQL database and indexes to Typesense.

**Key Advantages Over GraphQL Indexer**:
- ✅ **Full catalog access**: 34,000+ products (no API limitations!)
- ✅ **Enhanced schema**: 10+ additional product fields
- ✅ **Faster indexing**: Direct database queries (no pagination needed)
- ✅ **Rich attributes**: Brand, size, color, physical_form, CAS numbers
- ✅ **Temporal data**: created_at, updated_at for "latest/newest" queries
- ✅ **Sale prices**: special_price field for discounted items

**New Schema Fields**:
- `brand`: Product brand (e.g., "Mercedes Scientific", "Greiner Bio-One")
- `size`: Product size (e.g., "1 Gallon", "2 x 2", "Large")
- `color`: Product color (e.g., "Clear", "White", "Blue")
- `physical_form`: Form factor (e.g., "Liquid", "Solid", "Powder")
- `cas_number`: Chemical Abstract Service number
- `special_price`: Sale/discounted price
- `qty`: Quantity available in stock
- `weight`: Product weight
- `created_at`: Unix timestamp (for "latest" queries)
- `updated_at`: Unix timestamp (for "recently updated")

**Key Features**:
- **Store view merging**: Combines NULL and 'mercedesscientific' store views for complete data
- **Attribute parsing**: Extracts specs from additional_attributes JSON
- **Category enrichment**: Adds "Brand: X", "Size: Y" to categories for better search
- **Enhanced embeddings**: Now includes brand, size, color, physical_form in semantic search
- **Progress tracking**: Shows fetch progress with rate indicators
- **Batch processing**: 1000 products per fetch batch, 100 per index batch

**Usage**:
```bash
# Full indexing (all 34k+ products)
python src/indexer_neon.py

# Test with limited products
python3
>>> from src.indexer_neon import NeonProductIndexer
>>> indexer = NeonProductIndexer()
>>> indexer.run(max_products=1000)
```

**Requirements**:
- Neon database connection string in `.env`: `NEON_DATABASE_URL`
- Database table: `catalog_products` with proper schema

**Typical Performance**:
- Database query: 1-3 minutes for full catalog
- Fetch & transform: ~5-10 minutes
- Embedding generation: ~25-35 minutes for 34k products
- **Total time**: ~35-45 minutes for full catalog

**Normalized Fields for Model Number Search**:
The indexer includes special normalized fields to handle model number and SKU variations (CEO's feedback fix):

- `sku_normalized`: Removes all separators and lowercases SKUs
  - "TNR 700S" → "tnr700s"
  - "K83-913" → "k83913"

- `name_normalized`: Removes all separators and lowercases product names
  - "Gloves, Nitrile, BluTouch" → "glovesnitrileblutouch"
  - "Tanner Scientific® BluTouch®" → "tannerscientificblutouch"

These fields enable users to search with or without spaces/dashes:
- ✅ "TNR700S" finds "TNR 700S"
- ✅ "blu touch" finds "BluTouch" products
- ✅ Case-insensitive matching works automatically

**Search Configuration** (Extreme Weighting Strategy):
```python
"query_by": "name,sku,name_normalized,sku_normalized,description,short_description,categories"
"query_by_weights": "100,100,4,4,3,3,1"
```

**Weighting Rationale (100:4 ratio)**:
- **Original fields (100)**: Token separators handle 99% of queries optimally
- **Normalized fields (4)**: Fallback for edge cases without degrading general search
- This balance ensures excellent search quality for both general queries AND edge cases

See `MODEL_NUMBER_SEARCH_FIX.md` for comprehensive documentation of this feature.

### src/search.py (CURRENT)
Implements Typesense native NL integration with vLLM middleware for RAG-based search.

**Class**: `Search`

**Architecture** (Typesense NL with vLLM Middleware):
- **Typesense native NL** - Uses `nl_query=true` parameter
- **vLLM middleware** - Railway-deployed OpenAI-compatible endpoint
- **Single API call** - Typesense handles middleware communication internally
- **Model**: `middleware-rag-vllm` (vLLM provider with `api_url`)

**How It Works**:
1. API calls Typesense with `nl_query=true` and `nl_model_id="middleware-rag-vllm"`
2. Typesense automatically calls Railway middleware for query processing
3. Middleware performs RAG-based category classification
4. Middleware returns search parameters (extracted query, filters, sort)
5. Typesense executes search with middleware parameters and returns results

**Key Methods**:
- `search()`: Main entry point, calls Typesense with NL parameters
- `_transform_results()`: Converts Typesense hits to Product objects

**Response Structure**:
```python
{
    "results": [...],
    "total": 33,
    "query_time_ms": 4500,
    "typesense_query": {
        "approach": "typesense_nl",
        "original_query": "nitrile gloves under $50",
        "extracted_query": "nitrile glove",  # Always included (from middleware)
        "filters_applied": "categories:=Gloves && price:<50",  # Always included
        "nl_model_id": "middleware-rag-vllm",
        "middleware_url": "https://web-production-a5d93.up.railway.app",
        "results_found": 33,
        "results_returned": 20
    }
}
```

**Performance**:
- **Query Time**: ~4-5 seconds (includes middleware RAG processing)
- **Model**: vLLM provider with `api_url` pointing to Railway
- **Reliable**: Proper parameter passing (`api_url` vs deprecated `api_base`)

**UI Display**:
The frontend automatically displays the middleware's extracted query and filters (not the original user query), giving users transparency into how their query was interpreted:
- Shows: `{"q":"nitrile glove", "filter_by":"categories:=Gloves && price:<50"}`
- Instead of: `ng:"nitrile gloves under $50"`

### middleware/openai_middleware.py
OpenAI-compatible RAG middleware deployed on Railway.

**Purpose**: Receives queries from Typesense, performs RAG-based category classification, returns search parameters.

**Features**:
- OpenAI-compatible `/v1/chat/completions` endpoint
- Retrieves product context from Typesense (prevents circular dependency)
- Uses GPT-4o-mini for category classification
- Returns structured JSON: `{"q": "...", "filter_by": "..."}`
- Deployed independently on Railway for scalability

**Architecture**:
- **Deployed**: Railway (https://web-production-a5d93.up.railway.app)
- **Called by**: Typesense NL model (not directly by API)
- **Returns**: Extracted query + filters for Typesense to execute

### src/utilities/export_nl_system_prompt.py
Exports the registered NL model's system prompt from Typesense (if using NL models).

**Purpose**: Retrieve and inspect system prompts from Typesense.

**Features**:
- Retrieves model configuration from Typesense API
- Exports system prompt to `database/{TYPESENSE_HOST}/nl_model_system_prompt.txt`
- Saves full model config as `database/{TYPESENSE_HOST}/nl_model_system_prompt.json`
- Shows prompt statistics (length, lines, preview)
- Automatically organizes exports by Typesense host

### src/utilities/setup_synonyms.py
Manages synonym groups in Typesense for improved search matching.

**Purpose**: Configure explicit synonym mappings for domain-specific terms.

**Features**:
- 35+ predefined synonym groups (materials, equipment, measurements)
- Easy add/remove/list/clear operations
- Testing capabilities to verify synonym matching

**Usage**:
```bash
# Export system prompt (saves to database/{TYPESENSE_HOST}/)
python src/export_nl_system_prompt.py

# Export with comparison to setup file
python src/export_nl_system_prompt.py --compare

# Custom output file
python src/export_nl_system_prompt.py -o my_prompt.txt
```

**Output Location**:
- Default: `database/{TYPESENSE_HOST}/` directory (e.g., `database/qg91lms7w5rveht3p-1.a1.typesense.net/`)
- Organized by Typesense host for multi-instance support
- Alongside other database exports (product CSVs)

**Use Cases**:
- Verify what prompt is actually deployed in production
- Debug filter extraction issues
- Compare local vs deployed model configurations
- Document the current NL model setup

**Hybrid Approach System Prompt** (SCALABLE ✨):
The system prompt uses a **minimal, schema-driven approach** that scales to unlimited categories:

**Key Characteristics**:
- ✅ **No hardcoded category mappings** - relies on semantic search instead
- ✅ **Conservative filtering** - only price, stock, special_price, temporal (reliable fields)
- ✅ **Semantic attributes** - brand, size, color go in query (not strict filters)
- ✅ **~2,300 characters** (~574 tokens) - stays constant regardless of catalog size
- ✅ **Scales to 100s-1000s of categories** without prompt bloat
- ✅ **13 focused examples** demonstrating filter extraction and semantic matching

**Why This Approach?**:
```
Traditional Approach (DOESN'T SCALE):
├─ Hardcode all category mappings in prompt
├─ 9 categories = ~2K chars
├─ 100+ categories = ~20K chars (10x increase!)
└─ ❌ Token limits, higher costs, slower responses

Conservative Hybrid Approach (SCALES INFINITELY):
├─ NO category mappings in prompt
├─ Semantic search handles product types AND attributes (color, size, brand)
├─ Filter extraction ONLY for reliable fields (price, stock, special_price, temporal)
└─ ✅ Constant prompt size, fast, accurate, better recall
```

**Conservative Filter Extraction** (Reliable Fields Only):
```
"nitrile gloves under $30" → price filter
"pipettes in stock" → stock filter
"products on sale under $50" → special_price filter
"latest microscopes" → temporal sort (created_at:desc)
```

**Semantic Search Handling** (No Strict Filtering):
```
"blue gloves" → q: "blue glove" (semantic search, not color:=Blue filter)
"Mercedes Scientific pipettes" → q: "Mercedes Scientific pipette" (semantic, not brand filter)
"clear chemicals 1 gallon" → q: "clear chemical 1 gallon" (semantic, not color/size filters)
"white lab coats size large" → q: "white lab coat large" (semantic, not color/size filters)
```

**Why Conservative Approach?**:
- ✅ **Better recall**: Attributes (color, size, brand) have shallow/incomplete data
- ✅ **Strict filtering excludes products**: `color:=Blue` removes items without color field
- ✅ **Semantic search is fuzzy**: Naturally boosts matching attributes without excluding nulls
- ✅ **Reliable filters only**: price, stock, special_price, temporal (consistently populated)

**How Categories Are Handled**:
- Product types go in `q` field: "glove", "pipette", "microscope"
- Attributes go in `q` field: "blue", "large", "Mercedes Scientific"
- Typesense's semantic search matches to correct categories and attributes automatically
- No need to maintain category or attribute mapping lists!

**Usage**:
```bash
# Setup/register model (run once)
python src/setup_nl_model.py

# Check model status
python src/setup_nl_model.py check

# Test the hybrid approach
python test_hybrid_approach.py
```

**Prompt Size Comparison**:
| Approach | Prompt Size | Scales To |
|----------|-------------|-----------|
| **Old (Hardcoded)** | ~2,500 chars (9 categories) | ❌ ~20K chars (100+ categories) |
| **New (Hybrid)** | ~2,300 chars | ✅ Constant (unlimited categories) |

### src/app.py
FastAPI REST API with CORS enabled and automatic OpenAPI documentation.

**Endpoints**:
- `POST /api/search`: Main search endpoint (JSON body)
- `GET /api/search`: Alternative search (query params)
- `GET /health`: Health check
- `GET /`: API info
- `GET /docs`: Interactive Swagger UI documentation
- `GET /redoc`: Alternative ReDoc documentation
- `GET /openapi.json`: OpenAPI schema

### src/models.py
Pydantic v2 models for type safety:
- `SearchQuery`: Validates user input
- `SearchResponse`: Search results + metadata
- `Product`: Product data model
- `TypesenseQuery`: Internal query representation

## Important Implementation Details

### Natural Language Search Setup (REQUIRED)

**Typesense v29.0+** includes native NL search that requires a one-time model registration:

```bash
# Register OpenAI model with Typesense (run once)
python src/setup_nl_model.py
```

**What this does**:
- Registers `openai/gpt-4o-mini` model with Typesense
- Allows Typesense to use the LLM for query interpretation
- Enables automatic filter extraction (e.g., "gloves under $50" → `price:[0..50]`)
- No custom prompt needed - Typesense generates prompts from your schema

**Model Configuration**:
```python
{
    "id": "openai-gpt4o-mini",
    "model_name": "openai/gpt-4o-mini",  # Provider/model format
    "api_key": "YOUR_OPENAI_API_KEY",
    "max_bytes": 16000,
    "temperature": 0.0  # Deterministic results
}
```

**Check model status**:
```bash
python src/setup_nl_model.py check
```

**Why separate from embeddings?**
- Embeddings: Used for semantic similarity (vector search)
- NL model: Used for query understanding (filter/sort extraction)
- Both work together for optimal search results

### Pydantic V2 Migration
✅ **Already migrated** from Pydantic v1 to v2:
- Use `.model_dump()` instead of `.dict()`
- Use `.model_dump_json()` instead of `.json()`

### Typesense Embedding Configuration
The embedding field in the schema uses Typesense's auto-embedding feature:

```python
{
    "name": "embedding",
    "type": "float[]",
    "embed": {
        "from": ["name", "description", "short_description", "categories"],
        "model_config": {
            "model_name": "openai/text-embedding-3-small",
            "api_key": Config.OPENAI_API_KEY,
        }
    }
}
```

This means:
- Embeddings are generated **automatically** during indexing
- No need to manually call OpenAI embedding API
- Typesense handles rate limiting internally

### Native Natural Language Search Query
```python
search_params = {
    "q": "sterile gloves under $50",
    "query_by": "name,description,short_description,sku,categories",
    "nl_query": "true",              # Enable native NL search
    "nl_model_id": "openai-gpt4o-mini",  # Registered model ID
    "nl_query_debug": "true",        # Optional: see LLM reasoning
    "per_page": 20
}
```

**How it works**:
1. Typesense sends your query + schema to the registered LLM
2. LLM returns structured parameters (filters, sorts, query text)
3. Typesense executes the search with those parameters
4. No custom prompt needed - Typesense handles it

**Note**: When `nl_query=true`, Typesense automatically uses embeddings if available. You don't need to manually specify `vector_query`.

## Common Tasks

### Adding a New Field to Products

1. Update GraphQL query in `indexer.py` (line 70+)
2. Update schema in `indexer.py` (line 24+)
3. Update `Product` model in `models.py`
4. Update `_transform_product()` in `indexer.py`
5. Re-run indexer to recreate collection

### Changing Embedding Model

1. Update `.env`: `OPENAI_EMBEDDING_MODEL=text-embedding-3-large`
2. Update schema in `indexer.py` line 48
3. Re-run indexer (embeddings will regenerate)

### Adjusting Search Relevance

**More semantic results**:
```python
"vector_query": f"embedding:({query.q}, k:{query.per_page * 4})"  # Increase k
```

**More keyword results**:
```python
# Decrease k or remove vector_query entirely
```

**Boost specific fields**:
```python
"query_by": "name,description,short_description,sku,categories",
"query_by_weights": "5,2,2,3,1"  # Boost name 5x
```

### Adding New Filters

1. Update GPT-4 system prompt in `search.py` line 108-137
2. Add examples for the new filter type
3. GPT-4 will automatically extract it

Example for adding brand filter:
```python
# In system prompt, add:
"- Brand match: brand:=value"

# Example:
"Query: 'Thermo Fisher pipettes'
Output: {"q": "pipettes", "filter_by": "brand:=Thermo Fisher"}"
```

## Cost Optimization

### Current Costs (per 1000 searches)
- GPT-4 query translation: ~$0.01 × 1000 = $10
- text-embedding-3-small: ~$0.0001 × 1000 = $0.10
- **Total**: ~$10.10 per 1000 searches

### Cost Reduction Options

**Option 1**: Use GPT-4o-mini for query translation
```bash
OPENAI_MODEL=gpt-4o-mini  # ~75% cost reduction
```

**Option 2**: ✅ **Semantic query caching (IMPLEMENTED)**
```python
# Redis LangCache SDK with cache-first architecture
# Cache hit: ~1.1s (skips RAG + OpenAI)
# Cache miss: ~4-5s (RAG + OpenAI + cache store)
# Result: 3-4x faster on cache hits, 40-60% cost reduction
```
See `docs/REDIS_CACHE_IMPLEMENTATION.md` for full details.

**Option 3**: Batch similar queries
- Group queries by intent
- Translate in batch with GPT-4

## Testing

### Manual Testing

```bash
# Test query translation
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gloves under $50"}'

# Test semantic search
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "protective hand covering"}'  # Should find gloves

# Test filters
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "pipettes in stock between $100 and $500"}'
```

### Unit Tests (to be added)

Suggested test coverage:
- `test_query_translation()`: GPT-4 output validation
- `test_hybrid_search()`: Semantic + keyword combination
- `test_filters()`: Price, stock, category filters
- `test_fallback()`: Keyword-only when vector search fails

## Debugging

### Enable Verbose Logging

```python
# In search.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

**1. Middleware connection errors**
- Cause: OpenAI middleware service not running or unreachable
- Fix: Ensure middleware is deployed and `MIDDLEWARE_URL` is correct
- Debug: Check middleware logs for errors

**2. Slow indexing**
- Cause: OpenAI rate limits during embedding generation
- Solution: Reduce batch size or upgrade OpenAI tier
- Monitor: Check OpenAI dashboard for rate limit usage
- Normal time: 35-45 minutes for full 34k product catalog

**3. Poor category classification**
- Cause: Insufficient or irrelevant product context
- Debug: Enable `debug=true` to see middleware reasoning
- Debug: Check retrieval results quality
- Solution: Adjust retrieval search parameters

**4. Empty results**
- Cause: Filters too restrictive from middleware
- Debug: Check `typesense_query.filters_applied` in response
- Debug: Try simpler queries to isolate issue
- Monitor: Use debug mode to see what filters were extracted

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
TYPESENSE_API_KEY=...
TYPESENSE_HOST=...

# Neon Database (for indexer_neon.py)
NEON_DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require

# Optional (have defaults)
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https
ENVIRONMENT=development    # Environment: development, staging, production
SERVER_PORT=5001           # Port for FastAPI server

# Backward Compatibility (deprecated, but still supported)
# FLASK_ENV=development    # Use ENVIRONMENT instead
# FLASK_PORT=5001          # Use SERVER_PORT instead
```

## Data Models Reference

### SearchQuery (input)
```python
{
    "query": str,           # Required: User's natural language query
    "max_results": int      # Optional: Default 20
}
```

### SearchResponse (output)
```python
{
    "results": List[Product],      # List of products
    "total": int,                  # Total matches
    "query_time_ms": float,        # Search time
    "typesense_query": dict        # Debug: structured query used
}
```

### Product
```python
{
    "product_id": int,
    "uid": str,
    "name": str,
    "sku": str,
    "url_key": str,
    "stock_status": str,           # "IN_STOCK" or "OUT_OF_STOCK"
    "type_id": str,                # "simple" or "configurable"
    "description": Optional[str],
    "short_description": Optional[str],
    "price": Optional[float],
    "currency": str,               # "USD"
    "image_url": Optional[str],
    "categories": List[str],
    "category_ids": List[int]
}
```

## API Response Examples

### Successful Search
```json
{
  "results": [...],
  "total": 25,
  "query_time_ms": 145.23,
  "typesense_query": {
    "q": "sterile gloves",
    "filter_by": "price:[0..100]",
    "sort_by": "price:asc",
    "per_page": 20
  }
}
```

### Error Response
```json
{
  "error": "Missing 'query' in request body",
  "message": "An error occurred while processing your search"
}
```

## Security Considerations

1. **API Keys**: Never commit `.env` to git
2. **CORS**: Currently allows all origins (fine for development)
3. **Rate Limiting**: Not implemented (add for production)
4. **Input Validation**: Pydantic handles basic validation
5. **SQL Injection**: Not applicable (NoSQL database)

## Performance Benchmarks

### Indexing
- 1,000 products: ~2-3 minutes
- 5,000-10,000 products (typical): ~10-20 minutes
- Bottleneck: OpenAI embedding generation + API queries
- Multi-search strategy: 110 queries × ~2-5 seconds each = ~5-10 minutes for fetching
- Embedding generation: ~5-10 minutes for 5,000-10,000 products

### Search
- Average query time: 100-200ms
  - GPT-4 call: 50-100ms
  - Typesense search: 10-50ms
  - Data transformation: <10ms

## Future Enhancements

### Short Term
- [x] ✅ **Add caching layer** (Redis LangCache SDK - implemented with 3-4x speedup, see `docs/REDIS_CACHE_IMPLEMENTATION.md`)
- [ ] Implement rate limiting
- [ ] Add query analytics
- [ ] Support pagination

### Medium Term
- [ ] Multi-language support
- [ ] Faceted search UI
- [ ] Search suggestions/autocomplete
- [ ] A/B test semantic vs keyword

### Long Term
- [ ] Image search
- [ ] Conversational search (multi-turn)
- [ ] Personalized results
- [ ] Alternative embedding providers (Cohere, Voyage AI)

## Development Workflow

1. **Setup**: Clone → Install deps → Configure .env → **Setup NL model** → Index data
2. **Run**: Start FastAPI server → Start frontend (optional)
3. **Test**: Send test queries → Verify results → Check Swagger docs
4. **Iterate**: Monitor debug output → Adjust if needed
5. **Deploy**: (Not yet implemented)

## Useful Commands

```bash
# 1. Index products from Neon database (34k+ products)
python src/indexer_neon.py

# 2. Register vLLM middleware model in Typesense (one-time setup)
python src/setup_middleware_model.py

# 3. Start API server
python src/app.py

# 4. Start frontend
./start-ui.sh

# 5. Test search
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "your query here"}'

# 6. Test with debug mode
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "nitrile gloves under $50", "debug": true}'

# 7. Check health
curl http://localhost:5001/health

# 8. Setup synonyms (OPTIONAL - improves matching)
python src/utilities/setup_synonyms.py          # Configure synonym groups
python src/utilities/setup_synonyms.py --list   # List current synonyms
python src/utilities/setup_synonyms.py --test   # Test synonym matching

# 9. Test synonym behavior (comprehensive tests)
./venv/bin/python3 tests/test_synonyms.py  # All synonym tests in one file
```

## Synonym Handling

The system uses a **three-layer approach** for synonym matching:

### 1. Semantic Embeddings (Automatic)
OpenAI's text-embedding-3-small naturally understands many synonyms:
- ✅ **Works automatically**: No configuration needed
- ✅ **Broad coverage**: Handles common scientific terms
- ✅ **Examples**: "pipette" ≈ "pipettor", "protective" ≈ "safety"

### 2. Typesense Synonyms (Explicit Control)
For domain-specific terms, configure explicit synonym groups:
- ✅ **Guaranteed matching**: PTFE ⟷ Teflon ⟷ Polytetrafluoroethylene
- ✅ **35+ synonym groups**: Materials, equipment, measurements, common terms
- ✅ **Easy management**: Add/remove synonym groups programmatically

**Setup**:
```bash
# Configure all synonym groups
python src/utilities/setup_synonyms.py

# List current synonyms
python src/utilities/setup_synonyms.py --list

# Test synonym matching
python src/utilities/setup_synonyms.py --test

# Clear all synonyms
python src/utilities/setup_synonyms.py --clear
```

**Example Synonym Groups**:
```python
# Materials
"ptfe" ⟷ "teflon" ⟷ "polytetrafluoroethylene"
"nitrile" ⟷ "nbr" ⟷ "nitrile rubber"
"pvc" ⟷ "vinyl" ⟷ "polyvinyl chloride"

# Equipment
"pipette" ⟷ "pipettor" ⟷ "pipet" ⟷ "micropipette"
"centrifuge" ⟷ "spinner" ⟷ "microcentrifuge"
"autoclave" ⟷ "sterilizer" ⟷ "steam sterilizer"

# Measurements
"ml" ⟷ "milliliter" ⟷ "millilitre" ⟷ "mL"
"mg" ⟷ "milligram" ⟷ "milligramme"

# Common terms
"sterile" ⟷ "aseptic" ⟷ "sterilized"
"powder-free" ⟷ "powder free" ⟷ "powderfree" ⟷ "non-powdered"
```

**Adding Custom Synonyms**:
Edit `src/utilities/setup_synonyms.py` → `get_synonym_groups()`:
```python
{
    "id": "my-synonym-group",
    "synonyms": ["term1", "term2", "term3"]
}
```

### 3. Hybrid Approach (Best Results)
The search combines both layers:
- **Semantic search**: Handles fuzzy matching and related concepts
- **Explicit synonyms**: Guarantees exact term equivalence
- **NL query translation**: Expands queries intelligently

**Example**:
```
Query: "ptfe gloves under $50"

1. NL model extracts: q="ptfe gloves", filter_by="price:<50"
2. Typesense expands: "ptfe" → ["ptfe", "teflon", "polytetrafluoroethylene"]
3. Semantic search: Finds similar products via embeddings
4. Results: All Teflon/PTFE gloves under $50
```

**Testing**:
```bash
# Run comprehensive synonym tests (all-in-one)
./venv/bin/python3 tests/test_synonyms.py

# This will test:
# 1. Direct Typesense synonym matching
# 2. Synonyms with real products (Pipette ⟷ Pipettor, Nitrile ⟷ NBR, etc.)
# 3. NL model query extraction
# 4. Product availability check
# 5. Semantic vs explicit synonyms
```

**Important**: Test with products that exist in your catalog! For example:
- ✅ "pipette tips" vs "pipettor tips" (both exist)
- ✅ "nitrile gloves" vs "nbr gloves" (both exist)
- ❌ NOT "ptfe gloves" (product doesn't exist in catalog)

See `docs/SYNONYM_TESTING_GUIDE.md` for comprehensive testing documentation.

### Why This Approach?

| Method | Pros | Cons |
|--------|------|------|
| **Semantic only** | ✅ Works automatically<br>✅ Handles related concepts | ❌ May miss exact synonyms<br>❌ Less predictable |
| **Synonyms only** | ✅ Guaranteed matching<br>✅ Explicit control | ❌ Requires maintenance<br>❌ Limited to exact terms |
| **Hybrid (both)** | ✅ Best of both worlds<br>✅ Comprehensive coverage | ⚠️ Requires initial setup |

## Dependencies

### Python (requirements.txt)
- fastapi: Modern web framework with automatic OpenAPI docs
- uvicorn[standard]: ASGI server for FastAPI
- typesense: Typesense client
- openai: OpenAI API client
- pydantic: Data validation (v2+)
- python-dotenv: Environment variables
- requests: HTTP client
- httpx: Async HTTP client
- gql[all]: GraphQL client (for legacy indexer)
- psycopg2-binary: PostgreSQL client (for Neon indexer)

### Node.js (frontend/package.json)
- react: UI framework
- vite: Build tool
- tailwindcss: CSS framework
- axios: HTTP client

## Contact & Support

For questions or issues:
1. Check README.md troubleshooting section
2. Review this CLAUDE.md file
3. Check Typesense docs: https://typesense.org/docs/
4. Check OpenAI docs: https://platform.openai.com/docs/

---

**Last Updated**: 2025-11-04

**Project Status**: Production-ready with Typesense NL + RAG middleware

**Version**: 2.3.0 (Model Number Search + Synonym Matching + Codebase Cleanup)

**Recent Changes**:

**v2.3.0** (Nov 4, 2025):
- ✅ **MODEL NUMBER SEARCH FIX**: Implemented normalized fields for SKU/model variations
- ✅ **Middleware retrieval fix**: Updated `retrieve_products()` to use normalized fields with proper weighting
- ✅ **Synonym matching**: 35 synonym groups configured and tested (pipette/pipettor, nitrile/nbr, etc.)
- ✅ **Codebase cleanup**: Organized tests, docs, removed obsolete files
- ✅ **Documentation updates**: Updated CLAUDE.md to reflect Typesense NL + middleware architecture
- ✅ Tests: "tnr700s" → "TNR 700S", "blu touch" → "BluTouch" products working correctly

**v2.2.1** (Oct 21, 2025):
- ✅ **CONSERVATIVE FILTERING**: Switched from aggressive to conservative attribute filtering
- ✅ **Better recall**: Color, size, brand now use semantic search (not strict filters)
- ✅ **Reliable filters only**: Price, stock, special_price, temporal (consistently populated fields)
- ✅ **Fixed low result counts**: "blue gloves" now returns all gloves (semantic boost), not just those with color:=Blue
- ✅ **Shallow data handling**: Attributes with incomplete data won't exclude products
- ✅ **Updated system prompt**: Removed color/size/brand from filter extraction rules
- ✅ **Documentation updates**: CLAUDE.md and README.md reflect conservative approach

**v2.2.0** (Oct 17, 2025):
- ✅ **TYPESENSE NL + MIDDLEWARE**: Implemented single-call architecture with Railway middleware
- ✅ **RAG category classification**: Middleware handles RAG internally with GPT-4o-mini
- ✅ **Conservative category detection** with confidence thresholds
- ✅ **Fixed vLLM provider setup**: Used `api_url` parameter (not deprecated `api_base`)
- ✅ **Updated frontend**: Displays middleware-extracted query and filters
- ✅ **Auto-enabled debug mode** for localhost development
- ✅ **Improved handling** of ambiguous queries ("clear", "filters", etc.)

**v2.1.0** (Oct 15, 2025):
- ✅ **SCALABILITY FIX**: Implemented hybrid approach for unlimited category support
- ✅ Removed hardcoded category mappings from system prompt
- ✅ Reduced prompt from ~2.5K → 2.3K chars (stays constant with catalog growth)
- ✅ System now scales to 100s-1000s of categories without prompt bloat
- ✅ Created `test_hybrid_approach.py` for validation
- ✅ Updated documentation with Mermaid diagrams

**v2.0.0** (Oct 14, 2025):
- ✅ Added Neon database indexer (34k+ products, no API limits)
- ✅ Enhanced schema with 10+ new fields (brand, size, color, temporal, etc.)
- ✅ Improved NL model system prompt with advanced filters
- ✅ Added support for "on sale", "latest", "newest" queries
- ✅ Better embeddings including product attributes
