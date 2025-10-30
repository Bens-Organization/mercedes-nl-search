# Typesense Native NL Search Setup Guide

This guide explains how to set up and use the Typesense native NL search integration with corrected boolean parameters.

## Branch Information

- **Branch**: `feature/typesense-middleware-corrected`
- **Based on**: `staging` + `feature/typesense-nls-category`
- **Status**: ✅ All parameters corrected to use booleans

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
3. **src/openai_middleware.py** - Fixed `nl_query: False` (line 166)
4. **src/search_middleware.py** - Fixed `nl_query: False` (lines 186, 289)
5. **src/setup_nl_model.py** - Added: Script to register OpenAI model with Typesense
6. **src/config.py** - Added: ENVIRONMENT variable for environment identification

## Architecture

This implementation uses **Typesense's native NL search** feature:

```
User Query
    ↓
Flask API (app.py)
    ↓
NaturalLanguageSearch (search.py)
    ↓
Typesense Native NL Search (nl_query=True)
    ↓
Typesense → OpenAI GPT-4o-mini → Structured Parameters
    ↓
Typesense Search with Extracted Filters
    ↓
Results
```

### Key Features
- ✅ Single LLM call (Typesense handles it)
- ✅ Automatic filter extraction (price, stock, categories)
- ✅ Native embedding support (automatic when nl_query=True)
- ✅ Built-in query debugging (nl_query_debug=True)
- ✅ No circular dependencies (unlike decoupled middleware)
- ✅ Simpler deployment (no separate middleware service)

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

### Step 1: Register the NL Model with Typesense

**CRITICAL**: This step must be done **once** before using the native NL search.

```bash
# Register the OpenAI model with Typesense
python src/setup_nl_model.py
```

This script will:
1. Register `openai/gpt-4o-mini-2024-07-18` model with Typesense
2. Configure the system prompt with category mappings
3. Set temperature to 0.0 for deterministic results
4. Enable the `nl_query=True` feature

**Check if model is registered:**
```bash
python src/setup_nl_model.py check
```

**Expected output:**
```
✓ Model 'openai-gpt4o-mini' exists
Configuration: {'id': 'openai-gpt4o-mini', 'model_name': 'openai/gpt-4o-mini-2024-07-18', ...}
```

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
