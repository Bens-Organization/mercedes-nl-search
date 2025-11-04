# Test Results - Historical Data

**Last Updated**: November 4, 2025

## comparison_results.json

**Date**: October 30, 2025
**Status**: ⚠️ **HISTORICAL DATA** - Does not reflect current implementation

### What This Data Shows

This file contains comparison test results between two **older architectures**:
- **"rag"**: Dual LLM RAG (v2.2.0) - still in production on main branch
- **"middleware"**: Decoupled Middleware (v3.1) - superseded by v3.3

### Current Implementation (Not Tested Here)

**Staging branch** now uses **Typesense NL Integration (v3.3)** as of November 3, 2025:
- Single API call to Typesense with `nl_query=true`
- Typesense internally calls middleware for RAG classification
- Simpler architecture than both tested approaches
- Same performance as Decoupled Middleware (~4-5s)
- Same cost ($0.01 per query)

### Why This Data is Historical

1. **Typesense NL Integration (v3.3)** was successfully implemented on Nov 3, 2025
2. This test was run on Oct 30, before v3.3 existed
3. The "middleware" results show the older Decoupled Middleware (v3.1) approach
4. Current staging uses a newer, simpler architecture (v3.3)

### Architecture Evolution

```
Oct 30, 2025: comparison_results.json created
├─ Dual LLM RAG (v2.2.0) - "rag" in results
├─ Decoupled Middleware (v3.1) - "middleware" in results
└─ Comparison showed middleware was faster (4-5s vs 6-8s)

Oct 31, 2025: First attempt at Typesense NL
└─ ❌ Failed due to api_base parameter issue

Nov 3, 2025: Typesense NL Integration (v3.3) SUCCESS
├─ Fixed using api_url instead of api_base
├─ Deployed to staging
└─ ✅ This is now the CURRENT staging implementation
```

### Current Status

| Branch | Architecture | Version | Status |
|--------|--------------|---------|--------|
| **main** | Dual LLM RAG | v2.2.0 | ✅ Production |
| **staging** | Typesense NL | v3.3 | ✅ Current (Nov 3, 2025) |
| ~~Decoupled Middleware~~ | ~~v3.1~~ | Historical | Superseded by v3.3 |

### For Updated Comparisons

See:
- `docs/SEARCH_ARCHITECTURES_COMPARISON.md` - Updated Nov 4, 2025 with v3.3
- `src/search.py` - Current staging implementation (Typesense NL v3.3)

---

**Note**: This data is kept for historical reference and to show the evolution of the architecture. It does not reflect the current staging implementation.
