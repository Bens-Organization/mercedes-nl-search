# Category Classification Approaches

This document compares different approaches to category classification in the natural language search system.

**Status**: ✅ **RAG APPROACH IMPLEMENTED AND DEPLOYED**

## Version History

### v2.2.0 (Oct 17, 2025) - RAG Dual LLM Approach ✅ CURRENT
- **Implementation**: `src/search_rag.py` (`RAGNaturalLanguageSearch`)
- **Accuracy**: 84.6% on 26-test dataset
- **Status**: Production-deployed
- **Documentation**: See `docs/RAG_DUAL_LLM_APPROACH.md`

### v2.1.0 (Oct 15, 2025) - Semantic Search with Confidence Scoring (LEGACY)
- **Implementation**: `src/search.py` (`NaturalLanguageSearch`)
- **Status**: Deprecated (superseded by RAG approach)

---

## Current Approach: RAG-Based Category Classification (v2.2.0)

### Overview

**Location**: `src/search_rag.py` (`RAGNaturalLanguageSearch`)

The system now uses a **dual LLM approach** for improved category classification:

1. **LLM Call 1**: Typesense NL model extracts filters (price, stock, brand, size, color)
2. **LLM Call 2**: GPT-4o-mini analyzes retrieved products and classifies category

### How It Works

**Step 1: NL Query Translation**
- Typesense NL model (GPT-4o-mini) extracts filters from query
- Example: "nitrile gloves under $30" → `price:<30`
- Does NOT extract category (RAG handles this)

**Step 2: Retrieval Search**
- Search with NL-extracted filters, no category filter yet
- Retrieve top 20 products for context

**Step 3: Category Context Extraction**
```python
# Group products by category, sample 2 products per category
category_context = {
    "Products/Gloves & Apparel/Gloves": [
        {"name": "Nitrile Gloves Blue Large", "sku": "GLV-200"},
        {"name": "Powder-Free Exam Gloves", "sku": "GLV-150"}
    ],
    "Products/PPE/Safety Equipment": [
        {"name": "Safety Gloves Kit", "sku": "PPE-100"},
        {"name": "Protective Gear Set", "sku": "PPE-201"}
    ],
    # ... up to 10 categories
}
```

**Step 4: LLM Category Classification**
```python
# GPT-4o-mini analyzes context and returns:
{
    "category": "Products/Gloves & Apparel/Gloves",
    "confidence": 0.85,
    "reasoning": "The query specifically mentions 'nitrile gloves'..."
}
```

**Step 5: Apply Category Filter (if confident)**
- If confidence >= 0.75 (default): Apply category filter
- Combine with NL-extracted filters
- Execute final search

### Conservative Rules

To prevent false positives, the system returns `null` for:
- **Single-word attributes**: "clear", "large", "sterile"
- **Brand-only queries**: "Mercedes Scientific", "Ansell"
- **Highly ambiguous queries**: "filters" (water/air/syringe?)

### Performance Metrics

- **Accuracy**: 84.6% (22/26 test cases)
- **Query Time**: ~3.5-4.5 seconds (2x slower than single LLM)
- **Cost**: ~$20 per 1,000 queries (2x cost of single LLM)
- **Improvements over baseline**: 3 new correct classifications
  - Lab coats (was returning single coat)
  - Autoclave bags (was filtering incorrectly)
  - Semantic matches (better context understanding)

### Advantages Over Old Approach

1. ✅ **Smarter Decisions**: LLM sees actual product context
2. ✅ **Exact Match Detection**: Handles SKU matches correctly
3. ✅ **Better Semantic Understanding**: Context-based classification
4. ✅ **Explainable**: Provides reasoning for category choice
5. ✅ **Conservative**: Avoids false positives on ambiguous queries

---

## Legacy Approach: Semantic Search with Confidence Scoring (v2.1.0)

### How It Works

**Location**: `src/search.py:331-359` (`_calculate_category_confidence`)

1. **Typesense NL Search** extracts category from query using GPT-4o-mini
   - Example: "gloves under $50" → `filter_by: "categories:=Gloves && price:[0..50]"`

2. **Confidence Calculation** based on result distribution:
   ```python
   confidence = matching_count / total_results
   ```
   - If 5/6 results match the category → confidence = 0.83
   - If 1/6 results match the category → confidence = 0.16

3. **Threshold-based Filter Application**:
   - If confidence >= 0.80 (default): Apply category filter
   - If confidence < 0.80: Split results into primary (matching) and additional (non-matching)

### Confidence Scale

- **0.8-1.0 (Very High)**: 80-100% of results match category
- **0.6-0.8 (High)**: 60-80% of results match
- **0.4-0.6 (Moderate)**: 40-60% of results match
- **0.2-0.4 (Low)**: 20-40% match
- **0.0-0.2 (Very Low)**: 0-20% match

### Example Flow

**Query**: "Ansell gloves ANS 5789911"

1. NL search finds:
   - Multiple results in "Gloves" category
   - Possibly some results in other categories (if SKU matches)

2. Confidence calculation:
   - matching_count = count in "Gloves" category
   - total = all results
   - confidence = matching_count / total

3. Filter applied:
   - If confidence >= threshold (0.80) ✓
   - Results filtered to only "Gloves" category
   - **Problem**: If exact match appears in different category, it gets excluded!

### Problems Identified

**Issue #1: Exact Matches Get Filtered Out**
- Query: "Ansell gloves ANS 5789911"
- If there's 1 exact match but it appears in multiple categories, results may be filtered incorrectly
- Confidence-based filtering penalizes precision

**Issue #2: Multi-Category Products**
- Products can appear in dozens of categories
- Example: "yamato" might return:
  - 50 matches in "Accessories"
  - 5 matches in "Water Purifiers"
- Confidence (5/55 = 0.09) too low, but "Water Purifiers" might be the right category

**Issue #3: Category Distribution Doesn't Equal Relevance**
- More results ≠ better category
- Semantic search might work well, but confidence scoring breaks it

**Ben's Assessment**: "This is a dead end"

---

## Original Proposal: RAG-Based Category Classification

**Status**: ✅ **IMPLEMENTED AND DEPLOYED (v2.2.0)**

This section documents the original proposal that led to the current implementation.

### Concept

Instead of using result distribution as a proxy for confidence, use **Retrieval-Augmented Generation (RAG)**:

1. **Retrieve**: Semantic search to get top N results (e.g., 20)
2. **Extract**: Get top 10 categories from those results
3. **Augment**: For each category, include 2 sample products as context
4. **Generate**: LLM decides which category is most relevant based on retrieved context

**Implementation Note**: This approach has been successfully implemented in `src/search_rag.py`

### How It Would Work

**Step 1: Semantic Search**
```python
# Get top 20 results using semantic search (no category filter)
results = typesense_search(query, per_page=20)
```

**Step 2: Extract Category Context**
```python
# Extract categories with sample products
category_context = {
    "Gloves": [
        {"name": "Ansell Gloves ANS 5789911", "sku": "ANS5789911"},
        {"name": "Nitrile Gloves Blue Large", "sku": "GLV-200"}
    ],
    "PPE": [
        {"name": "Safety Gloves Powder-Free", "sku": "PPE-100"},
        {"name": "Protective Equipment Kit", "sku": "PPE-201"}
    ],
    # ... up to 10 categories
}
```

**Step 3: LLM Classification**
```python
prompt = f"""
Given the user query: "{query}"

Here are the top categories with sample products:
{json.dumps(category_context, indent=2)}

Which category is most relevant? Consider:
1. Exact matches (SKU, product name)
2. Semantic similarity to query intent
3. Context from sample products

Return:
- category: the most relevant category name
- confidence: 0-1 score
- reasoning: why this category was chosen
"""

llm_response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
)
```

**Step 4: Apply Filter (if confident)**
```python
if llm_response.confidence >= 0.7:
    # Apply category filter for final search
    apply_category_filter(llm_response.category)
else:
    # Return semantic search results without filter
    return semantic_results
```

### Advantages

1. **Smarter Decisions**: LLM sees actual context (product names, SKUs)
2. **Exact Match Detection**: LLM can identify "ABC-12" matches the exact product
3. **Semantic Understanding**: Better than simple division confidence
4. **Explainable**: LLM provides reasoning for category choice

### Trade-offs

**Pros**:
- More accurate category detection
- Handles exact matches correctly
- Better for multi-category products
- Provides reasoning/transparency

**Cons**:
- **2 LLM calls** instead of 1:
  1. Typesense NL search (already using GPT-4o-mini)
  2. RAG category classification (additional LLM call)
- Slightly higher cost (~$0.02 per 1000 searches)
- ~100-200ms additional latency

### Ben's Recommendation

> "Yeah we need to try it out, but my gut tells me this is a dead end. Just to stay in this example, with 'Ansell' in the query string, we might find hundreds of products in dozen different categories, lets say accessories might have 50 matches, and gloves just 5.
>
> Thats why I think its easier to try to pull this information from the llm model itself, and let the llm decide on how confident it is that an 'Ansell gloves ANS 5789911' is actually a glove product. If its not confident, then we skip the category filter
>
> What might improve the accuracy is to do a semantic full text search before the llm and then give it the 20 closest results or something, similar to RAG"

**Refined Approach**:
- Give LLM the 10 closest product categories
- For each category, include first 2 closest products as inspiration
- Let LLM decide confidence based on actual product context

---

## Implementation Plan

### Phase 1: Create Test Dataset
Create comprehensive test queries with expected outcomes:

```python
test_cases = [
    {
        "query": "Ansell gloves ANS 5789911",
        "expected_category": "Gloves",
        "expected_match_type": "exact",
        "notes": "Should prioritize exact SKU match"
    },
    {
        "query": "nitrile gloves",
        "expected_category": "Gloves",
        "expected_match_type": "semantic",
        "notes": "Generic query, high confidence expected"
    },
    {
        "query": "Ansell",
        "expected_category": None,  # Ambiguous
        "expected_match_type": "ambiguous",
        "notes": "Should NOT apply category filter (brand only, low confidence)"
    },
    # ... more test cases
]
```

### Phase 2: Implement RAG Approach

**New Module**: `src/search_rag.py`
- `_get_semantic_results()`: Get top N results
- `_extract_category_context()`: Build category context with samples
- `_classify_category_with_llm()`: LLM classification
- `_apply_category_filter()`: Final filtered search

**Updated Response Model**: `src/models.py`
```python
class RAGCategoryClassification(BaseModel):
    category: str
    confidence: float
    reasoning: str
    top_categories: List[Dict[str, Any]]  # Debug: categories considered
```

### Phase 3: Build Evaluation Framework

**New Script**: `tests/evaluate_category_classification.py`
- Load test dataset
- Run both approaches (old confidence vs new RAG)
- Compare accuracy, performance, edge case handling
- Generate comparison report

### Phase 4: Experiment & Iterate

1. Run evaluation on test dataset
2. Analyze results:
   - Accuracy improvement?
   - Performance impact acceptable?
   - Edge cases handled better?
3. Tune parameters:
   - How many results to retrieve? (20? 50?)
   - How many categories to consider? (10? 15?)
   - How many sample products per category? (2? 3?)
4. Document findings

---

## Implementation Status

1. ✅ Create branch: `feature/rag-category-classification`
2. ✅ Document current approach (this file)
3. ✅ Create test dataset (`tests/category_test_cases.py`)
4. ✅ Implement RAG approach (`src/search_rag.py`)
5. ✅ Build evaluation script (`tests/test_category_classification.py`)
6. ✅ Run experiments and analyze results
7. ✅ Deploy to production (`src/app.py` now uses `RAGNaturalLanguageSearch`)
8. ✅ Update frontend to display combined filters (`frontend-next/app/page.tsx`)
9. ✅ Fix model ID resolution issue (UUID vs string)
10. ✅ Add auto-debug mode for localhost
11. ✅ Document implementation (`docs/RAG_DUAL_LLM_APPROACH.md`)

### Results Summary

- **Accuracy**: 84.6% (22/26 test cases)
- **Improvements**: 3 new correct classifications vs baseline
- **Trade-off**: 2x query time, 2x cost, but better accuracy and transparency
- **Status**: ✅ Production-deployed and active

**Detailed Results**: See `tests/EVALUATION_RESULTS_FINAL.md` and `tests/FINAL_SUMMARY.md`

### Future Improvements

See `docs/RAG_DUAL_LLM_APPROACH.md` for detailed improvement roadmap:
- Increase retrieval_count (20 → 30)
- Fix remaining retrieval issue
- Add caching for frequent queries
- Hybrid retrieval (text + semantic)
- A/B testing vs baseline

---

**Created**: 2025-10-17
**Last Updated**: 2025-10-17
**Status**: ✅ **COMPLETED AND DEPLOYED**
