# Typesense NL Search Setup Guide (Corrected Parameters)

This guide explains how to set up and use Typesense NL search integration with corrected boolean parameters. This branch includes **TWO approaches**:

1. **Native NL Search** (Simple) - Basic filter extraction via OpenAI
2. **RAG Middleware** (Advanced) - Filter extraction + category classification in one LLM call

## Branch Information

- **Branch**: `feature/typesense-middleware-corrected`
- **Based on**: `staging` + `feature/typesense-nls-category`
- **Status**: ✅ All parameters corrected to use booleans
- **Available Approaches**: Native NL (simple) + RAG Middleware (advanced)

## What Was Fixed

### Parameter Corrections
All `nl_query` parameters now use proper boolean values instead of strings:

```python
# ❌ Before (Incorrect)
"nl_query": "true"   # String
"nl_query": "false"  # String

# ✅ After (Correct)
"nl_query": True   # Boolean
"nl_query": False  # Boolean
```

### Files Modified
1. **src/search.py** - Main search implementation using Typesense native NL
2. **src/app.py** - Flask API using `NaturalLanguageSearch` class
3. **src/openai_middleware.py** - RAG middleware service + fixed `nl_query: False` (line 166)
4. **src/search_middleware.py** - Fixed `nl_query: False` (lines 186, 289)
5. **src/setup_nl_model.py** - Added: Script to register OpenAI model for native NL
6. **src/setup_middleware_model.py** - Added: Script to register RAG middleware as NL model
7. **src/config.py** - Added: ENVIRONMENT variable for environment identification

## Two Approaches Available

This branch provides **two ways** to use Typesense NL search:

### Approach 1: Native NL Search (Simple)
- **Best for**: Basic filter extraction (price, stock, sort)
- **Setup**: `python src/setup_nl_model.py`
- **Model**: Direct OpenAI GPT-4o-mini
- **Pros**: ✅ Simple, fast, no separate service
- **Cons**: ❌ No RAG context, basic category detection
- **LLM Calls**: 1 (Typesense → OpenAI)

### Approach 2: RAG Middleware (Advanced)
- **Best for**: Advanced category classification with product context
- **Setup**: `python src/setup_middleware_model.py`
- **Model**: Custom middleware (vllm/gpt-4o-mini with RAG)
- **Pros**: ✅ RAG context, better category detection, still 1 LLM call
- **Cons**: ⚠️ Requires middleware service running
- **LLM Calls**: 1 (Typesense → Middleware → OpenAI with context)

**Recommendation**: Use **Approach 2 (RAG Middleware)** for production - it provides better accuracy with the same single LLM call cost.

## Architecture

### Approach 1: Native NL Search

```
User Query
    ↓
Flask API (app.py)
    ↓
NaturalLanguageSearch (search.py)
    ↓
Typesense NL Search (nl_query=True, nl_model_id="openai-gpt4o-mini")
    ↓
Typesense → OpenAI GPT-4o-mini → Structured Parameters
    ↓
Typesense Search with Extracted Filters
    ↓
Results
```

**Key Features**:
- ✅ Single LLM call (Typesense → OpenAI)
- ✅ Automatic filter extraction (price, stock)
- ✅ Basic category detection from schema mappings
- ✅ No separate middleware service needed

### Approach 2: RAG Middleware (Recommended)

```
User Query
    ↓
Flask API (app.py)
    ↓
NaturalLanguageSearch (search.py)
    ↓
Typesense NL Search (nl_query=True, nl_model_id="custom-rag-middleware-v2")
    ↓
Typesense → Middleware Service
                ↓
           Retrieve Products (RAG context)
                ↓
           Enrich Prompt with Context
                ↓
           OpenAI GPT-4o-mini (BOTH filter extraction + category classification)
                ↓
           Returns: {q, filter_by (with category), sort_by}
                ↓
Typesense ← Structured Parameters
    ↓
Typesense Search with Extracted Filters + Category
    ↓
Results
```

**Key Features**:
- ✅ Single LLM call (end-to-end)
- ✅ RAG-enhanced context (retrieves relevant products first)
- ✅ Advanced category classification (analyzes actual products)
- ✅ Combined approach: filter extraction + category detection
- ✅ Native embedding support (automatic when nl_query=True)
- ✅ Built-in query debugging (nl_query_debug=True)
- ⚠️ Requires middleware service running (Railway deployment available)

## Setup Instructions

### Prerequisites
Ensure you have these environment variables in `.env`:

```bash
# Required
OPENAI_API_KEY=sk-...
TYPESENSE_API_KEY=...
TYPESENSE_HOST=...

# Optional (have defaults)
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https
FLASK_ENV=development
FLASK_PORT=5001
ENVIRONMENT=development
```

### Step 1: Choose Your Approach and Register Model

**CRITICAL**: You must register a model **once** before using NL search.

#### Option A: Native NL Search (Simple)

```bash
# Register the OpenAI model with Typesense
python src/setup_nl_model.py

# Check if registered
python src/setup_nl_model.py check
```

This registers `openai/gpt-4o-mini-2024-07-18` directly with Typesense.

#### Option B: RAG Middleware (Recommended for Production)

**Step 1a: Start the Middleware Service**

```bash
# Middleware needs to be running before registration
python src/openai_middleware.py
# Or use the Railway deployment: https://web-production-a5d93.up.railway.app
```

**Step 1b: Register Middleware with Typesense**

```bash
# Register the middleware as a custom NL model
python src/setup_middleware_model.py

# For production middleware URL:
python src/setup_middleware_model.py register https://web-production-a5d93.up.railway.app

# Check if registered
python src/setup_middleware_model.py check
```

This registers the RAG middleware service (model ID: `custom-rag-middleware-v2`) with Typesense.

**Expected output:**
```
✓ Successfully registered middleware model!

Model ID: custom-rag-middleware-v2
Middleware URL: https://web-production-a5d93.up.railway.app

To use this model in searches:
  "nl_model_id": "custom-rag-middleware-v2"
```

### Step 1c: Configure Which Model to Use

Edit `src/search.py` line 16 to select your approach:

```python
# Option A: Native NL (simple)
self.nl_model_id = "openai-gpt4o-mini"

# Option B: RAG Middleware (recommended)
self.nl_model_id = "custom-rag-middleware-v2"
```

**Note**: The model ID must match what you registered in Step 1.

### Step 2: Start the API Server

```bash
python src/app.py
```

The server will start on `http://localhost:5001`

### Step 3: Test the Search

```bash
# Test a simple query
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "nitrile gloves under $50"}'

# Test with debug mode
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "nitrile gloves under $50", "debug": true}'
```

**Expected response structure:**
```json
{
  "results": [...],
  "total": 25,
  "query_time_ms": 150,
  "typesense_query": {
    "original_query": "nitrile gloves under $50",
    "nl_query": true,
    "nl_model_id": "openai-gpt4o-mini",
    "parsed": {
      "q": "nitrile glove",
      "filter_by": "categories:=Products/Gloves & Apparel/Gloves && price:<50"
    }
  },
  "detected_category": "Products/Gloves & Apparel/Gloves",
  "category_confidence": 0.85
}
```

## How It Works

### 1. Query Translation (Typesense → OpenAI)
When you send a query with `nl_query=True`:
- Typesense automatically calls the registered OpenAI model
- Sends the query + schema to GPT-4o-mini
- GPT-4o-mini returns structured parameters (q, filter_by, sort_by)

### 2. Filter Extraction
The system prompt instructs the LLM to extract:
- **Categories**: When product type is mentioned ("gloves" → categories filter)
- **Price**: When any price is mentioned ("under $50" → price:<50)
- **Stock**: When stock is mentioned ("in stock" → stock_status:=IN_STOCK)
- **Sort**: When sorting is requested ("cheapest" → sort_by:price:asc)

### 3. Search Execution
Typesense executes the search with extracted parameters:
```python
{
  "q": "nitrile glove",
  "filter_by": "categories:=Products/Gloves & Apparel/Gloves && price:<50",
  "sort_by": "_text_match:desc,price:asc"
}
```

## Debugging

### Enable Debug Mode
Add `"debug": true` to your request to see LLM reasoning:

```bash
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "nitrile gloves", "debug": true}'
```

### Check Model Status
```bash
python src/setup_nl_model.py check
```

### View Typesense Logs
If using Typesense Cloud, check the dashboard for query logs.

### Common Issues

**Issue**: `Model 'openai-gpt4o-mini' not found`
- **Solution**: Run `python src/setup_nl_model.py` to register the model

**Issue**: `nl_query parameter must be a boolean`
- **Solution**: This branch has fixed this - ensure you're using boolean `True/False`, not string `"true"/"false"`

**Issue**: `OpenAI API key is invalid`
- **Solution**: Check your `OPENAI_API_KEY` in `.env`

**Issue**: `Cannot connect to Typesense`
- **Solution**: Verify `TYPESENSE_HOST`, `TYPESENSE_PORT`, and `TYPESENSE_API_KEY` in `.env`

## Comparison with Other Approaches

| Approach | Architecture | Pros | Cons |
|----------|-------------|------|------|
| **Native NL (this branch)** | Typesense → OpenAI | ✅ Simple<br>✅ 1 LLM call<br>✅ No circular deps | ⚠️ Limited customization<br>⚠️ System prompt constraints |
| **Decoupled Middleware** | Typesense → Middleware → OpenAI | ✅ Full control<br>✅ RAG context | ❌ Complex<br>❌ 2 LLM calls<br>❌ Separate service |
| **RAG (staging)** | Direct → OpenAI (2 calls) | ✅ Best accuracy<br>✅ Context-aware | ❌ Slower<br>❌ 2 LLM calls |

## Migration Notes

### From Staging Branch
If you were using the decoupled middleware approach (`search_middleware.py`):

**Changes needed:**
1. Stop using `MiddlewareSearch` class
2. Use `NaturalLanguageSearch` class instead
3. No need to run separate middleware service
4. Must register NL model first: `python src/setup_nl_model.py`

**Code changes:**
```python
# ❌ Old (staging)
from search_middleware import MiddlewareSearch
search_engine = MiddlewareSearch()

# ✅ New (this branch)
from search import NaturalLanguageSearch
search_engine = NaturalLanguageSearch()
```

### To Staging Branch
If you want to go back to the decoupled middleware approach:

```bash
git checkout staging
# Restart the middleware service if needed
python src/openai_middleware.py
```

## Testing

### Quick Tests
```bash
# Category detection
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gloves"}'

# Price filtering
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "pipettes under $100"}'

# Stock filtering
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "beakers in stock"}'

# Combined filters
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "nitrile gloves in stock under $30"}'
```

## Files Reference

### Core Files
- **src/search.py**: Main search implementation (NaturalLanguageSearch class)
- **src/app.py**: Flask API server
- **src/setup_nl_model.py**: NL model registration script
- **src/config.py**: Configuration management

### Utility Files
- **src/openai_middleware.py**: Middleware service (for reference/backup)
- **src/search_middleware.py**: Decoupled middleware (for reference/backup)
- **src/indexer_neon.py**: Product indexer from Neon database

### Documentation
- **README.md**: Main project documentation
- **CLAUDE.md**: AI assistant context
- **DEPLOYMENT.md**: Deployment guide
- **TYPESENSE_MIDDLEWARE_SETUP.md**: This file

## Next Steps

1. **Test thoroughly**: Verify all queries work as expected
2. **Compare performance**: Benchmark against staging branch
3. **Update frontend**: If needed, update frontend to use this API
4. **Deploy**: Follow DEPLOYMENT.md for production deployment
5. **Monitor**: Watch query performance and LLM costs

## Support

For issues or questions:
1. Check this guide first
2. Review CLAUDE.md for technical context
3. Test with debug mode enabled
4. Check Typesense and OpenAI logs

---

**Last Updated**: 2025-10-30
**Branch**: feature/typesense-middleware-corrected
**Status**: ✅ Ready for testing
