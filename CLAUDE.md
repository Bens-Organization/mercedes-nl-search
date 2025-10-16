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

### Key Innovation: Hybrid Search with Native NL

The system uses **hybrid search** combining:
1. **Native NL Search** via Typesense v29.0+ (built-in query translation with GPT-4o-mini)
2. **Semantic search** via OpenAI embeddings (text-embedding-3-small)
3. **Keyword search** via Typesense full-text search

## Architecture

```mermaid
flowchart TB
    A["👤 User Query<br/>'sterile gloves under $100'"] --> B["🤖 GPT-4o-mini Query Translation<br/>Extracts: terms, filters, intents"]
    B --> C["📋 Structured Query<br/>{<br/>  q: 'sterile gloves',<br/>  filter_by: 'price:[0..100]'<br/>}"]
    C --> D["🔍 Typesense Hybrid Search"]
    D --> E["🧠 Semantic Search<br/>OpenAI Embeddings<br/>(text-embedding-3-small)"]
    D --> F["🔤 Keyword Search<br/>Full-text Index"]
    E --> G["✨ Ranked Results"]
    F --> G

    style A fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    style B fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    style C fill:#f5f5f5,stroke:#616161,stroke-width:2px,color:#000
    style D fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000
    style E fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000
    style F fill:#fff9c4,stroke:#f9a825,stroke-width:2px,color:#000
    style G fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px,color:#000
```

## Tech Stack

### Backend
- **Language**: Python 3.9+
- **Web Framework**: Flask
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
├── app.py              # Flask API server (REST endpoints)
├── config.py           # Configuration management
├── indexer_neon.py     # Neon database indexer (RECOMMENDED - 26k+ products)
├── indexer.py          # GraphQL API indexer (LEGACY - 5-10k products)
├── search.py           # Hybrid search implementation
├── setup_nl_model.py   # Natural language model registration
└── models.py           # Pydantic data models

database/
└── mercedes_products_*.csv  # Exported product data

frontend/
├── src/
│   ├── App.jsx
│   └── components/
└── package.json
```

## Key Files Explained

### src/config.py
Manages all configuration via environment variables:
- OpenAI API keys and models
- Typesense connection settings
- Flask server config

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

### src/indexer.py (LEGACY)
Fetches products from Mercedes GraphQL API and indexes to Typesense.

**Key Features**:
- **Multi-search strategy** to bypass API's 500-product limit
- Auto-generates embeddings via Typesense's OpenAI integration
- Batch processing (100 products per batch)
- Error handling for failed imports
- Configurable max_products for testing

**Multi-Search Strategy** (Critical Implementation Detail):

The Mercedes Scientific GraphQL API has a **hard limit of 500 products** per query, regardless of parameters used (`search`, `filter`, pagination, etc.). To work around this:

1. **Generate 110+ search terms** (`_get_search_terms()`):
   - Single letters (a-z)
   - Numbers (0-9)
   - Product categories (gloves, pipette, slide, reagent, etc.)
   - Medical/lab terms (sterile, surgical, diagnostic, etc.)

2. **Fetch products for each term** (`_fetch_products_for_search()`):
   - Each search term can return up to 500 products
   - Fetches first 5 pages (up to 500 products) per term
   - Silently handles errors for individual searches

3. **De-duplicate by SKU** (`fetch_products()`):
   - Tracks unique products in dictionary keyed by SKU
   - Typically yields 5,000-10,000+ unique products
   - Much better than single query (limited to 500)

**Example Output**:
```
Search terms: 110 different queries
  [  1/110] Search 'a              ':  100 products,  100 new unique (Total: 100)
  [  2/110] Search 'b              ':  100 products,  100 new unique (Total: 200)
  [ 50/110] Search 'gloves         ':  100 products,   96 new unique (Total: 5,234)
  ...
✓ Total unique products collected: 8,547
```

**To increase product coverage**:
- Add more search terms to `_get_search_terms()`
- Use brand names, SKU patterns, specific categories
- Increase pages per search (currently limited to 5)

**Schema**:
- Standard fields: product_id, name, sku, price, description, etc.
- **Embedding field**: Auto-generated from [name, description, short_description, categories]

### src/search.py
Implements natural language search using Typesense's native NL feature.

**Flow**:
1. `_execute_nl_search()`: Executes search with `nl_query=true` - Typesense automatically extracts filters, sorts, etc.
2. `_transform_results()`: Maps Typesense documents → Pydantic Product models
3. Category detection: Automatically detects category filters and provides additional results

**Features**:
- Uses Typesense native NL search (v29.0+) with registered OpenAI model
- Automatic filter extraction (price, stock, categories)
- Debug mode to see how LLM interprets queries
- Fallback to keyword-only search if NL fails

### src/setup_nl_model.py
Registers the OpenAI model with Typesense for native NL search.

**Important**: This must be run once before using natural language search features. The script:
- Registers GPT-4o-mini with Typesense via the `/nl_search_models` API
- Includes comprehensive system prompt for filter extraction
- Checks if model already exists
- Allows updating/recreating the model

**Hybrid Approach System Prompt** (SCALABLE ✨):
The system prompt uses a **minimal, schema-driven approach** that scales to unlimited categories:

**Key Characteristics**:
- ✅ **No hardcoded category mappings** - relies on semantic search instead
- ✅ **Filter rules only** - brand, size, color, price, stock, temporal
- ✅ **~2,300 characters** (~574 tokens) - stays constant regardless of catalog size
- ✅ **Scales to 100s-1000s of categories** without prompt bloat
- ✅ **7 focused examples** demonstrating filter extraction

**Why This Approach?**:
```
Traditional Approach (DOESN'T SCALE):
├─ Hardcode all category mappings in prompt
├─ 9 categories = ~2K chars
├─ 100+ categories = ~20K chars (10x increase!)
└─ ❌ Token limits, higher costs, slower responses

Hybrid Approach (SCALES INFINITELY):
├─ NO category mappings in prompt
├─ Semantic search handles product type matching
├─ Filter extraction for exact attributes
└─ ✅ Constant prompt size, fast, accurate
```

**Supported Filter Extraction**:
```
"nitrile gloves under $30" → price filter
"Mercedes Scientific pipettes in stock" → brand + stock filters
"clear liquid chemicals 1 gallon" → color + size filters
"products on sale under $50" → special_price filter
"latest microscopes" → temporal sort (created_at:desc)
"white lab coats size large" → color + size filters
```

**How Categories Are Handled**:
- Product types go in `q` field: "glove", "pipette", "microscope"
- Typesense's semantic search matches to correct categories automatically
- No need to maintain category mapping lists!

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
Flask REST API with CORS enabled.

**Endpoints**:
- `POST /api/search`: Main search endpoint (JSON body)
- `GET /api/search`: Alternative search (query params)
- `GET /health`: Health check
- `GET /`: API info

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

**Option 2**: Cache frequent queries (Redis)
```python
# Before calling OpenAI, check cache
if query in cache:
    return cache[query]
```

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

**1. "NL search model not configured" warning**
- Cause: OpenAI model not registered with Typesense
- Fix: Run `python src/setup_nl_model.py`
- Verify: Run `python src/setup_nl_model.py check`
- Required for: Native NL search features (filter extraction, etc.)

**2. "Fallback: Using keyword-only search"**
- Cause: NL search failed (likely model not configured)
- Debug: Check Typesense version (need v29.0+)
- Debug: Verify NL model exists: `python src/setup_nl_model.py check`
- Debug: Check OpenAI API key is valid

**3. Slow indexing**
- Cause: OpenAI rate limits or many API queries (multi-search)
- Solution: Reduce batch size or upgrade OpenAI tier
- Monitor: Check OpenAI dashboard for rate limit usage
- Normal time: 10-20 minutes for full index with multi-search

**4. Only 500 products indexed**
- Cause: Multi-search strategy not working
- Debug: Check if `_get_search_terms()` is returning enough terms
- Debug: Verify `_fetch_products_for_search()` is being called
- Fix: Ensure `fetch_products()` uses the multi-search approach

**5. Poor filter extraction from queries**
- Cause: NL model not understanding queries correctly
- Debug: Enable `nl_query_debug=true` to see LLM reasoning
- Debug: Check response's `parsed_nl_query` field
- Note: Typesense auto-generates prompts from schema - no manual prompt editing needed

**6. Empty results**
- Cause: Filters too restrictive from NL extraction
- Debug: Check `parsed_nl_query` in response
- Debug: Try simpler queries to isolate issue
- Monitor: Use debug mode to see what filters were extracted

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
TYPESENSE_API_KEY=...
TYPESENSE_HOST=...

# Neon Database (for indexer_neon.py - RECOMMENDED)
NEON_DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require

# Mercedes GraphQL API (for indexer.py - LEGACY)
MERCEDES_GRAPHQL_URL=https://www.mercedesscientific.com/graphql

# Optional (have defaults)
OPENAI_MODEL=gpt-4o-mini-2024-07-18
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https
FLASK_ENV=development
FLASK_PORT=5001
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
- [ ] Add caching layer (Redis)
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
2. **Run**: Start Flask API → Start frontend (optional)
3. **Test**: Send test queries → Verify results
4. **Iterate**: Monitor debug output → Adjust if needed
5. **Deploy**: (Not yet implemented)

## Useful Commands

```bash
# 1. Setup NL search model (REQUIRED - run once)
python src/setup_nl_model.py

# 2. Check NL model status
python src/setup_nl_model.py check

# 3a. Index products from Neon database (RECOMMENDED - 34k+ products)
python src/indexer_neon.py

# 3b. Index products from GraphQL API (LEGACY - 5-10k products)
python src/indexer.py

# 4. Start API server
python src/app.py

# 5. Start frontend
./start-ui.sh

# 6. Test search
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "your query here"}'

# 7. Test new filters (brand, size, color, temporal)
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "latest microscopes"}'

curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Mercedes Scientific nitrile gloves size medium"}'

# 8. Check health
curl http://localhost:5001/health

# 9. Test NL search directly
python src/search.py  # Runs test queries with debug output
```

## Dependencies

### Python (requirements.txt)
- flask: Web framework
- flask-cors: CORS support
- typesense: Typesense client
- openai: OpenAI API client
- pydantic: Data validation (v2+)
- python-dotenv: Environment variables
- requests: HTTP client
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

**Last Updated**: 2025-10-15

**Project Status**: Production-ready with Neon database integration

**Version**: 2.1.0 (Hybrid Scalable Approach + Neon Database)

**Recent Changes**:

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
