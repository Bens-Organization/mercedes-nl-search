# Typesense NL Middleware Issue - Root Cause Analysis

**Date**: 2025-11-03
**Analyst**: Claude (Sonnet 4.5)
**Issue**: Typesense not calling Railway middleware for NL search queries

---

## 🎯 Executive Summary

**ROOT CAUSE IDENTIFIED**: Using incorrect parameter name for custom endpoint configuration.

The current implementation uses `api_base` parameter, which is:
- ❌ Not documented for NL search models
- ❌ Not recognized by Typesense for `openai/` provider
- ❌ Causing Typesense to call OpenAI API directly instead of Railway middleware

**SOLUTION**: Use correct parameter format based on provider type:
- ✅ **Option A**: vLLM provider with `api_url` parameter (RECOMMENDED)
- ✅ **Option B**: OpenAI provider with `openai_url` + `openai_path` parameters (if supported)

---

## 📋 Investigation Timeline

### Initial Problem Statement
- UI searches → Render API → Typesense with `nl_query=true`
- Railway middleware NOT receiving requests
- Typesense shows `parse_time_ms: 1877` (LLM was called somewhere)
- Results missing category filter (only price filter applied)

### Key Observations
1. **Direct middleware testing**: ✅ Works perfectly (RAG classification, category detection)
2. **Direct Typesense curl**: ✅ Initially showed Railway logs
3. **UI searches**: ❌ Never hit Railway (confirmed by Railway logs)
4. **Typesense behavior**: Processes queries with LLM but bypasses middleware

---

## 🔍 Deep Dive Analysis

### Current Configuration (INCORRECT)

```json
{
  "id": "middleware-rag-gpt4o-mini",
  "model_name": "openai/gpt-4o-mini-2024-07-18",
  "api_base": "https://web-production-a5d93.up.railway.app",
  "api_key": "sk-proj-...",
  "max_bytes": 16000,
  "temperature": 0.0
}
```

**Problems**:
1. `api_base` is not a documented parameter for Typesense v29.0
2. When using `openai/` provider with valid `api_key`, Typesense calls OpenAI directly
3. Custom endpoint is ignored

### Parameter Research Findings

#### From Typesense Documentation (v29.0)

**For Conversation Models** (RAG feature):
- `openai_url` - Base URL of OpenAI API endpoint
- `openai_path` - URL path of OpenAI API endpoint
- Documented at: https://typesense.org/docs/29.0/api/conversational-search-rag.html

**For Natural Language Search Models**:
- `model_name` - Required (e.g., `openai/gpt-4o-mini`, `vllm/model-name`)
- `api_key` - Required for OpenAI
- `api_url` - Documented for vLLM provider only
- **NO explicit documentation for custom OpenAI-compatible endpoints**

#### From GitHub Issues & Community

**Issue #1987**: "Use openAI compatible API on create models"
- Status: ✅ Resolved in v29.0
- Solution: Added `openai_url` and `openai_path` for conversation models
- **Note**: This was for conversation models, not NL search models

**From API Spec** (`openapi.yml`):
- Base schema includes `url` parameter in model_config
- Used for embedding generation configuration
- May work for NL models (untested)

### Provider Analysis

#### OpenAI Provider (`openai/`)
```json
{
  "model_name": "openai/gpt-4o-mini-2024-07-18",
  "api_key": "sk-...",
  "openai_url": "https://custom-endpoint.com",
  "openai_path": "/v1/chat/completions"
}
```

**Behavior**:
- Default: Calls `https://api.openai.com/v1/chat/completions`
- With valid `api_key`: May prioritize OpenAI direct even if custom URL provided
- `openai_url`/`openai_path` support: Documented for conversation models, **unclear for NL models**

#### vLLM Provider (`vllm/`)
```json
{
  "model_name": "vllm/gpt-4o-mini",
  "api_url": "https://custom-endpoint.com/v1/chat/completions",
  "api_key": "any-value"
}
```

**Behavior**:
- Calls custom endpoint specified in `api_url`
- Designed for self-hosted models
- Works with OpenAI-compatible APIs
- **Should work for Railway middleware** (OpenAI-compatible endpoint)

---

## 🔬 Evidence Analysis

### Why `api_base` Doesn't Work

1. **Not in documentation**: No mention of `api_base` parameter in v29.0 docs
2. **Different from conversation models**: Conversation models use `openai_url`, not `api_base`
3. **Different from vLLM**: vLLM uses `api_url`, not `api_base`
4. **Legacy parameter**: `api_base` may be from older OpenAI client libraries (not Typesense API)

### Why Typesense Calls OpenAI Directly

When Typesense sees:
```json
{
  "model_name": "openai/gpt-4o-mini-2024-07-18",
  "api_key": "sk-proj-valid-key...",
  "api_base": "https://railway.app"  // ❌ Not recognized
}
```

Typesense's behavior:
1. Recognizes `openai/` provider
2. Validates `api_key` (valid OpenAI key)
3. Ignores unrecognized `api_base` parameter
4. Uses default OpenAI endpoint: `https://api.openai.com/v1/chat/completions`
5. Calls OpenAI directly (bypassing Railway)

**Result**: LLM is called (hence `parse_time_ms`), but **not** the Railway middleware.

### Test Evidence

**Test with dummy key** (from issue doc):
```
"OpenAI API error: Incorrect API key provided: dummy-ke..."
```

This proves Typesense was calling OpenAI API directly, not the Railway middleware (which doesn't validate keys).

---

## ✅ Recommended Solutions

### Solution A: Use vLLM Provider (RECOMMENDED)

**Rationale**:
- ✅ vLLM explicitly supports custom endpoints via `api_url`
- ✅ Designed for self-hosted / custom OpenAI-compatible APIs
- ✅ Well-documented in Typesense v29.0
- ✅ No ambiguity about endpoint routing

**Configuration**:
```json
{
  "id": "middleware-rag-vllm",
  "model_name": "vllm/gpt-4o-mini",
  "api_url": "https://web-production-a5d93.up.railway.app/v1/chat/completions",
  "api_key": "dummy-key-not-validated",
  "max_bytes": 16000,
  "temperature": 0.0
}
```

**Registration**:
```bash
./test_vllm_model_registration.sh
```

**Search Usage**:
```bash
curl "https://azj9dh4uxovql07tp-1.a1.typesense.net/collections/mercedes_products/documents/search" \
  -H "X-TYPESENSE-API-KEY: ..." \
  --data-urlencode "q=nitrile gloves under $50" \
  --data-urlencode "nl_query=true" \
  --data-urlencode "nl_model_id=middleware-rag-vllm" \
  --data-urlencode "query_by=name,description,sku"
```

**Pros**:
- ✅ Guaranteed to call custom endpoint
- ✅ No confusion with OpenAI API
- ✅ Well-documented approach

**Cons**:
- ⚠️ Model name says "vllm" but actually calls OpenAI (minor cosmetic issue)
- ⚠️ May confuse future developers

### Solution B: Use OpenAI Provider with openai_url (EXPERIMENTAL)

**Rationale**:
- `openai_url` + `openai_path` documented for conversation models
- May work for NL search models (needs testing)
- More semantically correct (using OpenAI provider for OpenAI-compatible API)

**Configuration**:
```json
{
  "id": "middleware-rag-openai-url",
  "model_name": "openai/gpt-4o-mini-2024-07-18",
  "openai_url": "https://web-production-a5d93.up.railway.app",
  "openai_path": "/v1/chat/completions",
  "api_key": "sk-proj-...",
  "max_bytes": 16000,
  "temperature": 0.0
}
```

**Registration**:
```bash
./test_openai_url_model_registration.sh
```

**Pros**:
- ✅ Semantically correct (OpenAI provider for OpenAI-compatible API)
- ✅ Uses documented parameters (from conversation models)

**Cons**:
- ❌ Not explicitly documented for NL search models
- ❌ May still fall back to OpenAI direct
- ❌ Requires testing to verify

### Solution C: Keep Current Decoupled Architecture (FALLBACK)

If neither approach works, use existing `search_middleware.py`:

**Workflow**:
1. API receives search request
2. Call middleware directly with query
3. Parse middleware response (get category + filters)
4. Execute Typesense search with `nl_query=false`

**Pros**:
- ✅ Already working
- ✅ No dependency on Typesense NL model behavior
- ✅ Full control over workflow

**Cons**:
- ❌ More complex orchestration
- ❌ Doesn't leverage Typesense NL integration
- ❌ Higher latency (separate middleware call)

---

## 🧪 Testing Plan

### Phase 1: vLLM Provider Test

```bash
# 1. Register vLLM model
./test_vllm_model_registration.sh

# 2. Monitor Railway logs in separate terminal
railway logs --follow  # Or check Railway dashboard

# 3. Test search from curl
curl "https://azj9dh4uxovql07tp-1.a1.typesense.net/search" \
  --data-urlencode "q=nitrile gloves under 50 dollars" \
  --data-urlencode "nl_query=true" \
  --data-urlencode "nl_model_id=middleware-rag-vllm"

# 4. Verify Railway logs show:
#    - INCOMING REQUEST FROM TYPESENSE
#    - RAG retrieval and classification
#    - Category filter applied

# 5. Test from UI
# Navigate to: https://mercedes-nl-search-git-staging-alvin-jbbgis-projects.vercel.app
# Search: "nitrile gloves under $50"
# Check: Railway logs show request
```

**Success Criteria**:
- ✅ Railway logs show incoming requests
- ✅ Category detected and applied (e.g., "Products/Gloves & Apparel/Gloves")
- ✅ Results filtered by category + price
- ✅ Response includes `detected_category` metadata

### Phase 2: OpenAI URL Test (if Phase 1 fails)

```bash
# 1. Register with openai_url
./test_openai_url_model_registration.sh

# 2. Repeat tests from Phase 1 with nl_model_id=middleware-rag-openai-url
```

### Phase 3: Validation

```bash
# Compare results
# - vLLM model: Should call Railway
# - openai_url model: May call Railway or OpenAI (need to verify)
# - Old api_base model: Calls OpenAI direct (confirmed broken)
```

---

## 📊 Impact Assessment

### Current State (With api_base - BROKEN)
- ❌ Middleware never called from UI searches
- ❌ No RAG context passed to LLM
- ❌ No category classification
- ❌ Poor search results (too broad, no category filtering)
- ✅ Basic filter extraction still works (price, stock) via direct OpenAI

### Expected State (With vLLM provider - FIXED)
- ✅ Middleware called for all searches
- ✅ RAG context enriches LLM prompt
- ✅ Category classification applied (84.6% accuracy)
- ✅ Precise search results (category + filters)
- ✅ Single LLM call (~3-4 seconds total)

---

## 🎓 Key Learnings

### 1. Parameter Naming Matters
- `api_base` ≠ `openai_url` ≠ `api_url`
- Each provider has its own parameter names
- Undocumented parameters are silently ignored

### 2. Provider Namespaces
- `openai/` provider: Optimized for OpenAI API (may hardcode endpoint)
- `vllm/` provider: Explicitly designed for custom endpoints
- Choose provider based on endpoint flexibility needs

### 3. Documentation Gaps
- Conversation models != NL search models
- Parameters may differ between features
- Always test with actual API calls

### 4. Typesense NL Model Behavior
- Valid OpenAI `api_key` may override custom endpoints
- Fallback behavior not well-documented
- vLLM approach more reliable for custom endpoints

---

## 📁 Related Files

**Investigation**:
- `docs/TYPESENSE_NL_MIDDLEWARE_NOT_CALLED_ISSUE.md` - Original issue doc
- `docs/TYPESENSE_NL_INTEGRATION_DEBUG.md` - Previous debugging (Oct 31)

**Test Scripts**:
- `test_vllm_model_registration.sh` - Register vLLM model (RECOMMENDED)
- `test_openai_url_model_registration.sh` - Register with openai_url (EXPERIMENTAL)
- `check_nl_models.sh` - List registered models
- `reregister_model.sh` - Old registration script (uses api_base - broken)

**Implementation**:
- `src/openai_middleware.py` - Railway middleware (RAG logic)
- `src/search.py` - Render API (Typesense integration)
- `src/search_middleware.py` - Decoupled architecture (fallback)

**Documentation**:
- `docs/RAG_DUAL_LLM_APPROACH.md` - RAG implementation guide
- `docs/SINGLE_LLM_RAG_ARCHITECTURE.md` - Target architecture (blocked by this)

---

## 🚀 Next Steps

1. **Run vLLM test** (highest confidence solution)
   ```bash
   ./test_vllm_model_registration.sh
   ```

2. **Verify middleware is called**
   - Check Railway logs during test searches
   - Confirm category detection works

3. **Update frontend** if needed
   - Change `nl_model_id` from `middleware-rag-gpt4o-mini` to `middleware-rag-vllm`

4. **Update documentation**
   - Document correct configuration approach
   - Add troubleshooting guide

5. **Deploy to production**
   - Test thoroughly in staging first
   - Monitor Railway logs and search quality
   - Roll back to decoupled architecture if issues

---

## 🔗 References

**Typesense Documentation**:
- Natural Language Search: https://typesense.org/docs/29.0/api/natural-language-search.html
- Conversational Search: https://typesense.org/docs/29.0/api/conversational-search-rag.html
- Vector Search (embeddings): https://typesense.org/docs/29.0/api/vector-search.html

**Typesense GitHub**:
- Repository: https://github.com/typesense/typesense
- API Spec: https://github.com/typesense/typesense-api-spec
- Issue #1987: https://github.com/typesense/typesense/issues/1987 (OpenAI-compatible APIs)

**Typesense Release Notes**:
- v29.0: https://github.com/typesense/typesense/releases/tag/v29.0

---

**Last Updated**: 2025-11-03
**Status**: 🟡 **SOLUTION IDENTIFIED** - Testing required
**Priority**: **HIGH** - Blocking production RAG deployment
**Next Action**: Run `./test_vllm_model_registration.sh` and verify Railway logs
