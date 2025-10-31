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

## ✅ ROOT CAUSE IDENTIFIED

**Problem**: We're returning 7 fields but Typesense expects only 2-4:
- Native OpenAI returns: `q`, `filter_by` (omits empty fields)
- Our middleware returns: `q`, `filter_by`, `sort_by`, `per_page`, `detected_category`, `category_confidence`, `category_reasoning`

**Evidence**:
1. Tested native `openai-gpt4o-mini` model - it works fine with only `q` and `filter_by`
2. Native response format:
   ```json
   {
     "q": "glove",
     "filter_by": "stock_status:=IN_STOCK && price:<50"
   }
   ```
3. Multi-line JSON with newlines works fine (not the issue)
4. Typesense successfully parses the native response

**The extra 3 fields break Typesense's parser**: `detected_category`, `category_confidence`, `category_reasoning`

## 💡 PROPOSED SOLUTION

Since Typesense can't handle custom metadata fields, we have two options:

### Option A: Include Category in filter_by (Recommended)

**Approach**: Put category directly in the filter, like native model does:

```json
{
  "q": "glove",
  "filter_by": "categories:=Products/Gloves & Apparel/Gloves && price:<50 && stock_status:IN_STOCK"
}
```

**Pros**:
- ✅ Typesense can parse it (standard 2 fields)
- ✅ Category filter gets applied
- ✅ Single LLM call (efficient!)
- ✅ Uses Typesense NL integration as intended

**Cons**:
- ❌ Lose category confidence score
- ❌ Lose category reasoning
- ❌ Can't show "Did you mean?" suggestions
- ❌ Can't apply confidence threshold (always applies category or doesn't)

**When to use**: If you don't need category metadata (confidence, reasoning, threshold logic)

### Option B: Keep Decoupled Architecture (Current)

**Approach**: API orchestrates everything, calls middleware separately

**Pros**:
- ✅ Full category metadata (confidence, reasoning)
- ✅ Can apply confidence threshold
- ✅ Can show alternative results
- ✅ Complete control over flow

**Cons**:
- ❌ 2 Typesense searches (slower ~5-6s)
- ❌ More complex code
- ❌ Doesn't use Typesense NL integration

**When to use**: If you need full RAG transparency and conservative category filtering

## 🎯 RECOMMENDATION

**Use Option B (Current Decoupled Approach)** because:

1. **Conservative filtering is valuable** - Confidence threshold prevents wrong categories
2. **Transparency matters** - Users see why category was chosen
3. **Performance is acceptable** - 5-6s is fine for complex RAG queries
4. **Maintainability** - Easier to debug and modify

**When to reconsider Option A**:
- Performance becomes critical (< 3s required)
- Confidence threshold not needed
- Simple category detection sufficient

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
