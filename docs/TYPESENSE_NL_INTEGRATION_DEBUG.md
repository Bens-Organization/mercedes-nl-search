# Typesense NL Integration - Debug Notes

## Goal: Single LLM Call Architecture

The ideal architecture uses Typesense's native NL search integration to achieve **1 LLM call** that combines:
1. Filter extraction (from query text)
2. RAG category classification (from retrieved context)

## Architecture Diagram

```
User Query: "Gloves in stock under $50"
    ↓
Typesense NL Search (nl_query: True)
    ↓
Calls Middleware at: /v1/chat/completions
    ↓
Middleware Flow:
    1. Retrieves products (nl_query: False to avoid circular dependency)
    2. Extracts RAG context (groups by category)
    3. Calls OpenAI with context
    4. Returns combined result: filters + category metadata
    ↓
Typesense parses middleware response
    ↓
Typesense executes final search with extracted params
    ↓
Results returned to user
```

## Benefits of This Approach

✅ **Single LLM call** - Combines filter extraction + RAG classification
✅ **Faster** - ~3-4 seconds vs ~5-6 seconds (current decoupled approach)
✅ **Native integration** - Uses Typesense's built-in NL search feature
✅ **Cleaner** - No manual orchestration needed in API layer

## The Error We're Getting

When Typesense calls the middleware, we get:

```
'error': 'Error generating search parameters: Regex JSON parse failed on content'
```

**What this means**: Typesense's regex parser cannot parse the JSON response from the middleware.

## What We've Tried

### 1. ✅ Fixed Boolean Parameters
**Problem**: Used `"nl_query": "false"` (string) instead of `"nl_query": False` (boolean)
**Fixed in**: Multiple files (search_middleware.py, openai_middleware.py)
**Result**: Fixed, but error persists

### 2. ✅ Tested Middleware Directly
```bash
curl -X POST https://web-production-a5d93.up.railway.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{"model": "gpt-4o-mini", "messages": [...]}'
```

**Result**: Middleware works perfectly! Returns valid JSON:
```json
{
  "choices": [{
    "message": {
      "content": "{\"q\": \"glove\", \"filter_by\": \"price:<50 && stock_status:IN_STOCK\", ...}"
    }
  }]
}
```

### 3. ✅ Simplified Category Names
**Problem**: Full paths like `Products/Gloves & Apparel/Gloves` have special chars (/, &, spaces)
**Tried**: Using only last segment: "Gloves" instead of full path
**Result**: Still got regex parse error

### 4. ✅ Removed Empty Fields
**Problem**: Empty strings for `sort_by` might confuse parser
**Tried**: Removing empty `sort_by` and `filter_by` fields entirely
**Result**: Still got regex parse error

### 5. ✅ Used OpenAI-Compatible Format
**Problem**: Maybe vLLM format wasn't working
**Tried**: Changed from `vllm/gpt-4o-mini` to `openai/gpt-4o-mini` with `api_base`
**Result**: Different error - "Regex JSON parse failed" instead of "No valid response"

## Suspected Root Cause

Typesense's regex parser for extracting search parameters from LLM responses is **VERY strict** and may not handle:

1. **Custom metadata fields** - We're returning 7 fields but Typesense expects only 4:
   - Expected: `q`, `filter_by`, `sort_by`, `per_page`
   - We return: + `detected_category`, `category_confidence`, `category_reasoning`

2. **OpenAI response wrapper** - The response is wrapped in OpenAI's format:
   ```json
   {
     "choices": [{
       "message": {
         "content": "{\"q\": \"glove\", ...}"
       }
     }]
   }
   ```
   Typesense needs to extract the inner JSON string from `choices[0].message.content`

3. **Special characters in values** - Even though we simplified, there might be other chars breaking the regex

## Debugging Steps to Try

### Option 1: Match Native OpenAI Response Format Exactly

Check what the native `openai-gpt4o-mini` model returns and match that format exactly:

```python
# Test with native OpenAI model
results = client.collections['mercedes_products'].documents.search({
    'q': 'Gloves in stock under $50',
    'nl_query': True,
    'nl_model_id': 'openai-gpt4o-mini',  # Native, not middleware
    'nl_query_debug': True,
    'per_page': 5
})

print(results['parsed_nl_query']['llm_response'])
# This shows EXACTLY what format Typesense expects
```

### Option 2: Return Only 4 Standard Fields

Strip all custom metadata before returning to Typesense:

```python
# In middleware response
params = {
    "q": "glove",
    "filter_by": "price:<50 && stock_status:IN_STOCK",
    "sort_by": "",
    "per_page": 20
    # NO: detected_category, category_confidence, category_reasoning
}
```

But then we lose the category metadata! This defeats the RAG purpose.

### Option 3: Custom Response Parsing Hook

Check if Typesense has configuration for custom response parsing (unlikely).

### Option 4: Contact Typesense Support

Ask about:
- Exact JSON format expected for OpenAI-compatible endpoints
- How to include custom metadata in responses
- Examples of working custom middleware integrations

## Current Workaround: Decoupled Architecture

Since we couldn't get Typesense NL integration working, we switched to a decoupled approach:

**File**: `src/search_middleware.py`

**Flow**:
1. API does retrieval search (no NL, no category)
2. API extracts context from results
3. API calls middleware directly with context
4. Middleware returns category + filters
5. API does final search with middleware params

**Trade-offs**:
- ✅ Works reliably
- ✅ Full control over flow
- ❌ 2 Typesense searches instead of 1
- ❌ Slower (~5-6 seconds)
- ❌ More complex orchestration

## Next Steps to Debug NL Integration

1. **Create test branch**: `feature/typesense-nl-integration-debug`

2. **Test native OpenAI response format**:
   ```python
   # Compare what native model returns vs our middleware
   ```

3. **Try minimal response** (4 fields only):
   ```python
   # Remove all custom metadata, see if parsing works
   ```

4. **Check Typesense logs** (if accessible):
   ```bash
   # Look for more detailed error messages
   ```

5. **Inspect Typesense source code**:
   ```bash
   # Find the regex parser code to understand expectations
   ```

## Files Involved

- `src/setup_middleware_model.py` - Registers NL model with Typesense
- `src/openai_middleware.py` - Middleware `/v1/chat/completions` endpoint
- `src/search.py` - Original Typesense NL integration attempt
- `src/search_middleware.py` - Current decoupled workaround

## Related Issues

- Boolean parameter issue: Fixed in commits 5f75d3a, 8bb0237
- Duplicate category filters: Fixed in commit bbbe1d6
- System prompt update: Fixed in commit f79f944

---

**Last Updated**: 2025-10-31
**Status**: Blocked by Typesense JSON parsing error
**Priority**: Medium (workaround exists, but less efficient)
