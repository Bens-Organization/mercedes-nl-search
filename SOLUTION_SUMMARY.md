# Typesense NL Middleware Issue - Quick Solution Guide

**TL;DR**: Wrong parameter name. Use `api_url` with vLLM provider instead of `api_base` with OpenAI provider.

---

## 🔴 The Problem

Typesense is not calling your Railway middleware because **`api_base` is not a valid parameter** for NL search models.

**Current configuration (BROKEN)**:
```json
{
  "model_name": "openai/gpt-4o-mini-2024-07-18",
  "api_base": "https://web-production-a5d93.up.railway.app",  // ❌ Not recognized
  "api_key": "sk-proj-..."
}
```

**What happens**:
1. Typesense sees `openai/` provider + valid API key
2. Ignores unrecognized `api_base` parameter
3. Calls OpenAI directly at `https://api.openai.com/v1/chat/completions`
4. Railway middleware never receives requests

---

## ✅ The Solution

### Option A: vLLM Provider (RECOMMENDED)

**Use vLLM provider with `api_url` parameter**:

```bash
# 1. Delete old model
curl -X DELETE "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/nl_search_models/middleware-rag-gpt4o-mini" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz"

# 2. Register with vLLM format
curl -X POST "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/nl_search_models" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "middleware-rag-vllm",
    "model_name": "vllm/gpt-4o-mini",
    "api_url": "https://web-production-a5d93.up.railway.app/v1/chat/completions",
    "api_key": "dummy-key",
    "max_bytes": 16000,
    "temperature": 0.0
  }'
```

**OR use the provided script**:
```bash
./test_vllm_model_registration.sh
```

**Then update your search requests**:
```bash
# Change nl_model_id to the new model
nl_model_id=middleware-rag-vllm
```

**Why this works**:
- ✅ vLLM provider explicitly supports custom endpoints via `api_url`
- ✅ Designed for OpenAI-compatible APIs
- ✅ No confusion with OpenAI's default endpoint

### Option B: Try openai_url (EXPERIMENTAL)

**Use `openai_url` + `openai_path` parameters**:

```bash
./test_openai_url_model_registration.sh
```

**Note**: These parameters are documented for conversation models, not NL search models. May or may not work.

---

## 🧪 Testing

After registration, test with:

```bash
# 1. Watch Railway logs
# Open Railway dashboard and monitor logs

# 2. Test search
curl "https://azj9dh4uxovql07tp-1.a1.typesense.net/search" \
  --data-urlencode "q=nitrile gloves under 50 dollars" \
  --data-urlencode "nl_query=true" \
  --data-urlencode "nl_model_id=middleware-rag-vllm"

# 3. Verify Railway logs show:
#    ==========================================
#    INCOMING REQUEST FROM TYPESENSE
#    ==========================================
#    [RAG] Retrieved products: X products
#    [RAG] Category detected: Products/Gloves & Apparel/Gloves
#    [RAG] Category filter applied
```

**Success = Railway logs show incoming requests**

---

## 📊 Before vs After

| Metric | Before (api_base) | After (api_url) |
|--------|-------------------|-----------------|
| **Middleware called?** | ❌ No | ✅ Yes |
| **RAG context?** | ❌ None | ✅ Full |
| **Category filter?** | ❌ Missing | ✅ Applied |
| **Search quality** | ⚠️ Too broad | ✅ Precise |

---

## 🔗 Quick Links

**Test Scripts**:
- `./test_vllm_model_registration.sh` - Register vLLM model (recommended)
- `./test_openai_url_model_registration.sh` - Register with openai_url (experimental)

**Full Analysis**:
- `docs/TYPESENSE_NL_MIDDLEWARE_ROOT_CAUSE_ANALYSIS.md` - Complete investigation

**Related Docs**:
- `docs/TYPESENSE_NL_MIDDLEWARE_NOT_CALLED_ISSUE.md` - Original issue
- `docs/RAG_DUAL_LLM_APPROACH.md` - RAG implementation guide

---

## ❓ Why Did This Happen?

**Parameter confusion**:
- `api_base` - Used in OpenAI Python client (not Typesense API)
- `openai_url` - Typesense parameter for conversation models
- `api_url` - Typesense parameter for vLLM models
- ❌ `api_base` - **Not recognized by Typesense**

**Provider behavior**:
- `openai/` provider: Defaults to `api.openai.com` when custom endpoint not recognized
- `vllm/` provider: Requires `api_url` (no default endpoint)

---

## 🚀 Next Steps

1. ✅ **Register vLLM model**: `./test_vllm_model_registration.sh` (DONE)
2. ✅ **Test search**: Watch Railway logs for incoming requests (VERIFIED)
3. ✅ **Update backend**: Changed `nl_model_id` to `middleware-rag-vllm` in `src/search.py`
4. ✅ **Verify quality**: Category filters are applied correctly
5. ✅ **UI Transparency**: Backend now always includes `extracted_query` and `filters_applied`
6. **Deploy**: Update production after staging validation

---

## 🎨 UI Transparency Feature (NEW - Nov 3, 2025)

**What Changed**:
- Backend now **always** includes `extracted_query` and `filters_applied` in response
- Frontend displays the middleware's interpreted query (not the original user input)
- Users see exactly what was searched: `{"q":"nitrile glove", "filter_by":"categories:=Gloves && price:<50"}`

**Benefits**:
- ✅ Full transparency into query interpretation
- ✅ Users understand how their search was processed
- ✅ Helps debug unexpected results
- ✅ Educational for users learning the system

**Implementation**:
- `src/search.py`: Always includes extracted parameters in response (not just debug mode)
- `frontend-next/app/page.tsx`: Already supports displaying extracted query (no changes needed)

---

**Need Help?**
- Read: `docs/TYPESENSE_NL_MIDDLEWARE_ROOT_CAUSE_ANALYSIS.md`
- Check: Railway logs for middleware activity
- Test: Direct middleware call to verify it's working
