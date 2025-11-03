# Field Names Corrected: nl_* → llm_*

**Date**: November 3, 2025
**Issue**: Field names were misleading about the architecture

---

## The Problem

The field names `nl_extracted_*` and `nl_search_enabled` were **misleading** because they suggested we were using Typesense's NL (Natural Language) search model, when in reality:

❌ **We're NOT using Typesense NL model** (to avoid circular dependency)
✅ **We're using a single middleware LLM** that does EVERYTHING

---

## Architecture Reality Check

### Old Dual LLM Approach (What nl_* fields represented)

```
User Query
    ↓
┌─────────────────────────────────────┐
│ LLM CALL 1: Typesense NL Model      │
│ - Extracts query: "centrifuge tube" │
│ - Extracts filters: "none"          │
│ - Extracts sort: "default"          │
└─────────────────────────────────────┘
    ↓ [nl_extracted_query, nl_extracted_filters, nl_extracted_sort]
    ↓
┌─────────────────────────────────────┐
│ Retrieval Search (20 products)      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ LLM CALL 2: RAG Middleware          │
│ - Detects category: "Centrifuge...  │
│ - Confidence: 0.9                   │
└─────────────────────────────────────┘
    ↓ [detected_category, category_confidence]
    ↓
Final Search
```

**Total**: 2 LLM calls (~5s, $0.02)

---

### Current Decoupled Approach (What llm_* fields represent)

```
User Query
    ↓
┌─────────────────────────────────────┐
│ Retrieval Search (20 products)      │
│ - NO NL model                       │
│ - NO category filter                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ LLM CALL 1: Middleware (DOES BOTH!) │
│ - Extracts query: "centrifuge tube" │ ← llm_extracted_query
│ - Extracts filters: "none"          │ ← llm_extracted_filters
│ - Extracts sort: "default"          │ ← llm_extracted_sort
│ - Detects category: "Centrifuge..." │ ← detected_category
│ - Confidence: 0.9                   │ ← category_confidence
└─────────────────────────────────────┘
    ↓ [ALL fields from ONE LLM call]
    ↓
Final Search
```

**Total**: 1 LLM call (~4s, $0.01)

---

## Field Name Changes

| Old (Misleading) | New (Accurate) | Meaning |
|-----------------|----------------|---------|
| `nl_search_enabled` | `llm_extraction_enabled` | LLM-based extraction (NOT Typesense NL) |
| `nl_extracted_query` | `llm_extracted_query` | Query from middleware LLM |
| `nl_extracted_filters` | `llm_extracted_filters` | Filters from middleware LLM |
| `nl_extracted_sort` | `llm_extracted_sort` | Sort from middleware LLM |

**Why "llm" instead of "nl"?**
- ✅ Accurate: It's the middleware LLM doing the work
- ✅ Not misleading: We're NOT using Typesense's NL model
- ✅ Clear: One LLM does both extraction AND classification

---

## Response Format Comparison

### Before (Misleading - nl_*)

```json
{
  "typesense_query": {
    "approach": "decoupled_middleware",
    "nl_search_enabled": true,              // ❌ Misleading! NO Typesense NL
    "nl_extracted_query": "centrifuge tube",// ❌ Suggests separate NL model
    "nl_extracted_filters": "none",         // ❌ Suggests separate NL model
    "nl_extracted_sort": "default",         // ❌ Suggests separate NL model
    "detected_category": "...",             // From middleware
    "category_confidence": 0.9              // From middleware
  }
}
```

**Problem**: Looks like 2 separate steps (NL + RAG), but it's actually 1 LLM!

---

### After (Accurate - llm_*)

```json
{
  "typesense_query": {
    "approach": "decoupled_middleware",
    "llm_extraction_enabled": true,         // ✅ Clear: LLM-based
    "llm_extracted_query": "centrifuge tube",// ✅ From middleware LLM
    "llm_extracted_filters": "none",        // ✅ From middleware LLM
    "llm_extracted_sort": "default",        // ✅ From middleware LLM
    "detected_category": "...",             // ✅ SAME LLM call
    "category_confidence": 0.9              // ✅ SAME LLM call
  }
}
```

**Benefit**: Accurately reflects that ONE middleware LLM does BOTH jobs!

---

## Key Differences: Dual LLM vs Single LLM

| Aspect | Dual LLM (Old) | Single LLM (Current) |
|--------|----------------|---------------------|
| **LLM Calls** | 2 separate calls | 1 combined call |
| **Query Extraction** | Typesense NL model | Middleware LLM |
| **Filter Extraction** | Typesense NL model | Middleware LLM |
| **Sort Extraction** | Typesense NL model | Middleware LLM |
| **Category Detection** | RAG middleware | Middleware LLM (same call) |
| **Field Prefix** | `nl_` (Natural Language) | `llm_` (Large Language Model) |
| **Circular Dependency** | ❌ Has issue | ✅ Avoided |
| **Response Time** | ~5s | ~4s ⚡ |
| **Cost per Query** | $0.02 | $0.01 💰 |
| **Accuracy** | High | Same |

---

## Implementation Details

### Code Changes

**File**: `src/search_middleware.py`

**Before**:
```python
# Misleading variable names
nl_extracted_query = search_params.get("q", "")
nl_extracted_filters = search_params.get("filter_by", "") or "none"
nl_extracted_sort = search_params.get("sort_by", "") or "default"

response = {
    "nl_search_enabled": True,  # Hardcoded, misleading!
    "nl_extracted_query": nl_extracted_query,
    ...
}
```

**After**:
```python
# Accurate variable names
llm_extracted_query = search_params.get("q", "")
llm_extracted_filters = search_params.get("filter_by", "") or "none"
llm_extracted_sort = search_params.get("sort_by", "") or "default"

response = {
    "llm_extraction_enabled": True,  # Clear: middleware LLM
    "llm_extracted_query": llm_extracted_query,
    ...
}
```

**Comments Added**:
```python
# Note: Single middleware LLM does BOTH extraction AND classification (not separate NL model)
```

---

## What This Means for Users

### 1. Honest Field Names ✅
- No longer pretending we use Typesense NL model
- Clear that one middleware LLM does everything
- Accurate representation of architecture

### 2. Same Functionality 🎯
- Still extracts query, filters, sort
- Still detects category with confidence
- Just uses ONE LLM instead of TWO

### 3. Better Understanding 📚
- Users know exactly what's happening
- Developers won't be confused
- Field names match implementation

---

## Testing

### Old Test (nl_fields)
```bash
./venv/bin/python test_nl_fields.py
```
This will **fail** because fields were renamed.

### New Test (llm_fields)
```bash
./venv/bin/python test_llm_fields.py
```
This will **pass** and verify correct field names.

**Expected Output**:
```
✅ SUCCESS: All LLM extraction fields present!
✅ Correctly reflects single-LLM architecture
```

---

## Migration Guide

If you're using the old field names in your code:

### Frontend Code
```javascript
// BEFORE (wrong field names)
const nlEnabled = data.typesense_query.nl_search_enabled;
const query = data.typesense_query.nl_extracted_query;

// AFTER (correct field names)
const llmEnabled = data.typesense_query.llm_extraction_enabled;
const query = data.typesense_query.llm_extracted_query;
```

### Backend Integration
```python
# BEFORE (wrong field names)
if response['typesense_query']['nl_search_enabled']:
    query = response['typesense_query']['nl_extracted_query']

# AFTER (correct field names)
if response['typesense_query']['llm_extraction_enabled']:
    query = response['typesense_query']['llm_extracted_query']
```

---

## Summary

**Old Field Names** (`nl_*`):
- ❌ Misleading - suggested Typesense NL model
- ❌ Inaccurate - we don't use Typesense NL
- ❌ Confusing - looked like 2 separate steps

**New Field Names** (`llm_*`):
- ✅ Honest - reflects middleware LLM
- ✅ Accurate - matches implementation
- ✅ Clear - single LLM does both jobs

**Bottom Line**: The architecture uses ONE middleware LLM that does BOTH extraction AND classification. The field names now accurately reflect this reality! 🎯
