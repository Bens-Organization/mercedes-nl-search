# Typesense NL Integration - Middleware Not Being Called (2025-11-03)

## 🎯 What We're Trying to Achieve

Implement a **single LLM call architecture** using Typesense's native NL search integration that combines:

1. **Filter Extraction** (price, stock, etc.) from query text
2. **RAG Category Classification** using retrieved product context

**Expected Flow**:
```
User searches "gloves under $50" from UI
    ↓
Frontend → API (Render)
    ↓
API → Typesense with nl_query=True
    ↓
Typesense → Middleware (Railway) /v1/chat/completions
    ↓
Middleware:
  - Retrieves 20 products (nl_query=False to avoid circular dependency)
  - Extracts RAG context (groups by category)
  - Calls OpenAI GPT-4o-mini with enriched context
  - Returns: {"q": "glove", "filter_by": "categories:=`Products/Gloves & Apparel/Gloves` && price:<50"}
    ↓
Typesense parses response and applies filters
    ↓
Results: Only gloves under $50 returned
```

**Benefits**:
- ✅ Single LLM call (~3-4 seconds)
- ✅ Combines filter extraction + RAG classification
- ✅ Native Typesense integration
- ✅ Category filter applied automatically

## 🚨 Current Blocker

**Middleware is NOT being called by Typesense when searches originate from the UI.**

### Evidence

**Test 1: Direct curl to Typesense REST API**
```bash
curl "https://azj9dh4uxovql07tp-1.a1.typesense.net/search?q=gloves+under+50+dollars&nl_query=true&nl_model_id=middleware-rag-gpt4o-mini"
```
- ✅ Railway logs show incoming request
- ✅ Middleware returns: `{"filter_by": "categories:=`Products/Gloves & Apparel/Gloves` && price:<50"}`
- ✅ Price filter works (all 50 results under $50)
- ❌ **BUT**: Category filter gets stripped (33 gloves + 17 other items)

**Test 2: UI Search → API → Typesense**
```
User searches "gloves under $50" from https://mercedes-nl-search-git-staging-alvin-jbbgis-projects.vercel.app
```
- ❌ **Railway logs: NO incoming requests**
- ❌ Results show 51 items (no category filtering)
- ⚠️ Typesense returns `parsed_nl_query` field with `parse_time_ms: 1877` (LLM was called somewhere)
- ⚠️ But `filter_by` only contains `price:<50` (NO category)

### What This Tells Us

**Typesense IS calling an LLM** (based on parse time), but **NOT our Railway middleware**.

Two possibilities:
1. **Typesense calls OpenAI directly** (ignoring `api_base` parameter)
2. **Typesense has cached/fallback behavior** when middleware fails

## 📊 What We've Done So Far

### 1. ✅ Verified Middleware Works Perfectly

**Direct test to middleware**:
```bash
curl -X POST "https://web-production-a5d93.up.railway.app/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "gloves under 50 dollars"}]}'
```

**Result**:
```json
{
  "choices": [{
    "message": {
      "content": "{\"q\": \"glove\", \"filter_by\": \"categories:=`Products/Gloves & Apparel/Gloves` && price:<50\"}"
    }
  }]
}
```

**Railway logs show**:
```
[RAG] Retrieved products from Typesense: 2 products
[RAG] Category detected: Products/Gloves & Apparel/Gloves
[RAG] Confidence: 0.80 (threshold: 0.75)
[RAG] ✅ Category filter applied: 'Products/Gloves & Apparel/Gloves'
[RESPONSE] Final params: {"q": "glove", "filter_by": "categories:=`Products/Gloves & Apparel/Gloves` && price:<50"}
```

**Conclusion**: Middleware RAG classification works perfectly! ✅

### 2. ✅ Fixed Category Name Escaping

**Issue**: Category names like `Products/Gloves & Apparel/Gloves` contain `&` which conflicts with Typesense's `&&` operator.

**Fix**: Wrapped category names in backticks:
```python
category_filter = f"categories:=`{escaped_category}`"
```

**Result**: Middleware now returns properly escaped filter. ✅

### 3. ✅ Deleted Duplicate NL Model

**Discovery**: Found TWO NL models registered:
1. `middleware-rag-gpt4o-mini` → Points to Railway (does RAG) ✅
2. `openai-gpt4o-mini` → Calls OpenAI directly (NO RAG) ❌

The old model had this in its system prompt:
```
"DO NOT extract category filters - RAG handles category detection"
```

But since it calls OpenAI directly (no middleware), there's NO RAG!

**Fix**: Deleted `openai-gpt4o-mini` model. Now only `middleware-rag-gpt4o-mini` exists. ✅

### 4. ✅ Added Comprehensive Debug Logging

**API logs now show**:
```
[Typesense NL] DEBUG - Search params: {...}
[Typesense NL] DEBUG - Full result keys: [...]
[Typesense NL] DEBUG - Request params from Typesense: {...}
[Typesense NL] DEBUG - Parsed NL query (what middleware returned): {...}
```

### 5. ✅ Confirmed Model Configuration

**Current registration**:
```json
{
  "id": "middleware-rag-gpt4o-mini",
  "model_name": "openai/gpt-4o-mini-2024-07-18",
  "api_base": "https://web-production-a5d93.up.railway.app",
  "api_key": "sk-proj-...",  // OpenAI API key
  "max_bytes": 16000,
  "temperature": 0.0
}
```

## 🔍 Key Finding: Typesense May Call OpenAI Directly

**Hypothesis**: When we provide both `api_base` AND a valid OpenAI `api_key`, Typesense might:
1. Try `api_base` first
2. Fall back to OpenAI directly if middleware fails
3. OR always prefer OpenAI direct when the key is valid

**Evidence**:
- **Test with dummy key**: When we registered with `api_key: "dummy-key"`, Typesense returned:
  ```
  "OpenAI API error: Incorrect API key provided: dummy-ke..."
  ```
  This proves Typesense attempted to call **OpenAI directly** (not the middleware).

- **Current behavior**: UI searches get NL processing (`parse_time_ms: 1877`), but Railway shows NO requests.

**Conclusion**: Typesense is calling OpenAI directly, bypassing the Railway middleware entirely.

## 🔴 Current Blocker

**Typesense ignores `api_base` parameter and calls OpenAI directly when a valid OpenAI key is provided.**

This means:
- ❌ No RAG context passed to LLM
- ❌ No category classification
- ❌ Only basic filter extraction (price, stock)
- ❌ Middleware code never executes for UI searches

## 🤔 Why curl Works But UI Doesn't

**Theory**: The difference isn't curl vs UI - it's timing/caching.

- Initial curl tests after deleting old model → Typesense may have briefly called middleware
- Later tests (including UI) → Typesense reverted to calling OpenAI directly
- Typesense may cache model configurations or have fallback behavior

## 📋 What We're Trying to Resolve

1. **Force Typesense to use `api_base` (Railway middleware)** instead of calling OpenAI directly
2. **Ensure Railway middleware receives ALL NL query requests**, not just initial tests
3. **Apply RAG category classification** to narrow search results

## 🎯 Next Steps

### Immediate Actions

1. **Contact Typesense Support** about `api_base` behavior
   - Question: "When both `api_base` and valid `api_key` are provided, which one takes precedence?"
   - Documentation: https://typesense.org/docs/29.0/api/natural-language-search.html#registering-a-model

2. **Test with Invalid OpenAI Key** (force api_base usage)
   - Register model with `api_key: "railway-middleware-key"` (custom value)
   - Middleware validates ANY key (doesn't check OpenAI)
   - This might force Typesense to use `api_base`

3. **Investigate Typesense Cloud Settings**
   - Check if there's a default NL model at account level
   - Check for any caching/fallback configurations
   - Verify model registration actually saved

4. **Try Alternative Model Name Format**
   ```json
   {
     "model_name": "gpt-4o-mini-2024-07-18",  // Without "openai/" prefix
     "api_base": "https://web-production-a5d93.up.railway.app"
   }
   ```
   The "openai/" prefix might trigger direct OpenAI calling.

### Alternative Solutions

#### Option A: Use Python Typesense Client with Manual Orchestration

Instead of relying on Typesense NL integration, manually orchestrate in API:

```python
# 1. Call middleware directly
middleware_response = await call_middleware(query)
params = parse_middleware_response(middleware_response)

# 2. Call Typesense with extracted params (nl_query=False)
results = typesense_client.search(
    q=params["q"],
    filter_by=params["filter_by"],
    nl_query=False  # Don't use NL integration
)
```

**Pros**:
- ✅ Full control over flow
- ✅ Guaranteed middleware execution
- ✅ Same single LLM call benefit

**Cons**:
- ❌ Bypasses Typesense NL integration feature
- ❌ Custom orchestration code

#### Option B: Keep Current Decoupled Architecture

Use `search_middleware.py` (2 searches):
1. Retrieval search (get products)
2. Call middleware with context
3. Final search with middleware params

**Pros**:
- ✅ Already working
- ✅ Full category metadata
- ✅ No dependency on Typesense NL integration

**Cons**:
- ❌ 2 LLM calls (~5-6 seconds)
- ❌ More complex orchestration

## 📁 Files Modified Today

1. `src/openai_middleware.py` - Fixed category escaping with backticks
2. `src/search.py` - Added debug logging for `parsed_nl_query`
3. `check_nl_models.sh` - Script to list registered NL models
4. `delete_old_model.sh` - Deleted duplicate `openai-gpt4o-mini` model
5. `reregister_model.sh` - Re-register middleware model

## 🔗 Related Documentation

- `docs/TYPESENSE_NL_INTEGRATION_DEBUG.md` - Previous investigation (Oct 31) about JSON parsing
- `docs/RAG_DUAL_LLM_APPROACH.md` - Comprehensive guide to RAG implementation
- `docs/DECOUPLED_MIDDLEWARE_ARCHITECTURE.md` - Current workaround architecture
- `docs/SINGLE_LLM_RAG_ARCHITECTURE.md` - Ideal architecture (blocked by this issue)

## 📊 Timeline of This Issue

**Previous Encounter** (Oct 31, 2025):
- Issue: Typesense's JSON parser couldn't handle custom metadata fields
- Solution: Removed metadata, put category directly in filter_by
- Status: Partially resolved (parser works, but inconsistent behavior)

**Today** (Nov 3, 2025):
- Issue: Typesense not calling Railway middleware at all
- Discovery: Typesense calls OpenAI directly when valid key provided
- Status: **BLOCKED** - Need Typesense to honor `api_base` parameter

## 🎓 Lessons Learned

1. **Typesense NL integration behavior is unclear** when both `api_base` and valid OpenAI key are provided
2. **Railway middleware works perfectly** when called directly
3. **Dual-LLM RAG approach is sound** (filter extraction + category classification)
4. **Category name escaping matters** (use backticks for special characters)
5. **Debug logging is essential** for distributed systems debugging

## ✅ What Actually Works

- ✅ Middleware RAG classification (when called directly)
- ✅ Dual-LLM approach (filter extraction + RAG)
- ✅ Category detection with 0.75 confidence threshold
- ✅ Price/stock filter extraction
- ✅ Backtick escaping for category names with `&`

## ❌ What Doesn't Work

- ❌ Typesense calling Railway middleware for UI searches
- ❌ `api_base` parameter being honored by Typesense
- ❌ Category filter application (because middleware not called)
- ❌ Consistent behavior between curl and UI

---

**Last Updated**: 2025-11-03 15:30 UTC
**Status**: 🔴 **BLOCKED** - Typesense not calling middleware
**Priority**: **HIGH** - Blocking production deployment of RAG category classification
**Next Action**: Test with invalid OpenAI key or contact Typesense support
