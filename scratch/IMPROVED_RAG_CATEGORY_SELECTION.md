# Improved RAG Category Selection (Match Dual-LLM Approach)

**Date**: November 3, 2025
**Issue**: Middleware had too many hardcoded rules, not using pure RAG approach

---

## The Problem

### Old Approach (Too Prescriptive)

The middleware prompt had **many hardcoded examples and rules**:
```
"gloves" → "Products/Gloves & Apparel/Gloves"
"pipettes" → "Products/Pipettes"
"centrifuge tubes" → "Products/Glass & Plasticware/Tubes/Centrifuge Tubes"
...
```

**Problems**:
- ❌ Required explicit category mappings
- ❌ Couldn't handle new categories without updating prompt
- ❌ LLM might match to hardcoded examples instead of retrieved products
- ❌ Not true RAG (Retrieval-Augmented Generation)

---

## The Dual-LLM RAG Approach (Reference)

The dual-LLM approach does it correctly:

1. **Retrieve products** matching the query
2. **Extract categories** from retrieved products:
   ```json
   "top_categories": [
       "Products/Glass & Plasticware/Tubes/Test Tubes",
       "Brand: Fisher Scientific",
       "Size: 16mm",
       ...
   ]
   ```
3. **Ask LLM to pick** the best matching category from what was retrieved
4. **No hardcoded mappings** - categories come from actual data!

**Example**:
```
Query: "test tubes glass in stock"
Retrieved: [products with "Products/Glass & Plasticware/Tubes/Test Tubes"]
RAG decision: "Best match is Test Tubes because products have that category"
Result: ✅ Correct category detected
```

---

## New Approach (Pure RAG)

### Simplified Prompt

**Old prompt** (~1000 lines):
```
CRITICAL RULES:
1. Single attribute word...
2. Brand name only...
3. Generic attribute categories...
4. Highly ambiguous product types...

Examples:
- "gloves" → "Products/Gloves & Apparel/Gloves"
- "pipettes" → "Products/Pipettes"
...
```

**New prompt** (~300 lines):
```
Retrieved Product Categories:
{
  "Products/Glass & Plasticware/Tubes/Test Tubes": [...],
  "Brand: Fisher Scientific": [...],
  ...
}

Task:
- Look at the categories above
- Pick the BEST matching category
- ONLY choose categories starting with "Products/"
- If no good match, return null
```

**Key Differences**:
- ✅ **Focus on retrieved products** (not hardcoded examples)
- ✅ **Simple rules** (pick from what you see)
- ✅ **True RAG** (decisions based on actual retrieval)

---

## Prompt Improvements

### 1. Clear RAG Instructions

**Old**:
```
Determine which category best matches based on retrieved products.
[Then 100 lines of hardcoded rules and examples]
```

**New**:
```
**Category Classification (RAG Approach)**:
- Look at the categories in the retrieved products above
- Pick the category that BEST matches the user's query intent
- ONLY choose categories that start with "Products/"
- SKIP categories that start with "Brand:", "Size:", "Color:"
- If no good match exists, return null
```

**Benefits**:
- ✅ Focuses attention on retrieved categories
- ✅ Clear what to do (pick from above)
- ✅ Simple rule (Products/ only)

---

### 2. RAG-Based Examples

**Old** (Hardcoded mappings):
```
Query: "gloves"
→ detected_category: "Products/Gloves & Apparel/Gloves"

Query: "pipettes"
→ detected_category: "Products/Pipettes"
```

**New** (Retrieved context):
```
Example 1:
Query: "test tubes glass"
Retrieved categories: ["Products/Glass & Plasticware/Tubes/Test Tubes", "Brand: Fisher", ...]
→ detected_category: "Products/Glass & Plasticware/Tubes/Test Tubes"
Reasoning: "Exact match - 'test tubes' in retrieved products"

Example 2:
Query: "clear"
Retrieved categories: ["Products/.../Beakers", "Products/.../Containers", ...]
→ detected_category: null
Reasoning: "Query is only an attribute - too ambiguous"
```

**Benefits**:
- ✅ Shows HOW to use retrieved context
- ✅ Demonstrates picking from actual categories
- ✅ Models the RAG decision process

---

### 3. Simplified Confidence Guidelines

**Old** (Overly specific):
```
- Exact match (SKU or exact product name): 0.9-1.0
- Clear product type (gloves, pipettes, beakers): 0.75-0.9
- Product type + attributes: 0.75-0.9
- Brand + product type: 0.7-0.85
- Ambiguous: 0.0-0.5
[Then detailed rules for each case]
```

**New** (Simple, RAG-focused):
```
- 0.9-1.0: Exact product type match (e.g., "test tubes" → "Test Tubes")
- 0.8-0.9: Clear product type match (e.g., "gloves" → "Gloves")
- 0.75-0.85: Product type with material (e.g., "nitrile gloves" → "Gloves")
- < 0.75: Too ambiguous, return null
```

**Benefits**:
- ✅ Focuses on matching quality
- ✅ Easier for LLM to apply
- ✅ Less prescriptive

---

## How It Works

### Step-by-Step Process

```
1. User Query: "test tubes glass"
   ↓
2. Retrieval Search (no category filter)
   → Finds 20 products
   ↓
3. Extract Categories from Retrieved Products:
   {
     "Products/Glass & Plasticware/Tubes/Test Tubes": [
       {"name": "Fisher Test Tube 16x100mm", ...},
       {"name": "Eisco Test Tube 12x75mm", ...}
     ],
     "Brand: Fisher Scientific": [...],
     "Size: 16mm": [...]
   }
   ↓
4. Send to Middleware LLM:
   "Given query 'test tubes glass' and these retrieved categories,
    pick the best matching category..."
   ↓
5. LLM Decision:
   - Looks at retrieved categories
   - Sees "Products/Glass & Plasticware/Tubes/Test Tubes"
   - Matches "test tubes" in query to "Test Tubes" in category
   - Returns: detected_category = "Products/Glass & Plasticware/Tubes/Test Tubes"
   ↓
6. Final Search:
   categories:= "Products/Glass & Plasticware/Tubes/Test Tubes"
```

**Key Point**: Category comes from **retrieved products**, not hardcoded mappings!

---

## Comparison: Old vs New

### Test Query: "test tubes glass"

**Old Approach** (Hardcoded):
```
1. LLM sees query "test tubes glass"
2. LLM remembers examples: "test tubes" → might map to something
3. LLM might pick category from memory/examples
4. Category might not match what was actually retrieved
```

**New Approach** (Pure RAG):
```
1. LLM sees query "test tubes glass"
2. LLM sees retrieved categories: ["Products/.../Test Tubes", ...]
3. LLM picks from retrieved categories (NOT from memory)
4. Category is guaranteed to exist in retrieved products
```

---

## Benefits

### 1. No Category Hardcoding Required ✅

**Old**:
```python
# Prompt had to list all possible categories
"gloves" → "Products/Gloves & Apparel/Gloves"
"pipettes" → "Products/Pipettes"
"beakers" → "Products/Lab Glassware/Beakers"
# ... hundreds of mappings
```

**New**:
```python
# Prompt just says "pick from retrieved products"
# Categories discovered dynamically from data
```

---

### 2. Handles New Categories Automatically 🚀

**Old**:
- New product category added to database
- ❌ Middleware doesn't know about it
- ❌ Need to update prompt with new mapping
- ❌ Redeploy middleware

**New**:
- New product category added to database
- ✅ Retrieval search finds products with new category
- ✅ LLM sees new category in retrieved products
- ✅ LLM can pick it (no prompt update needed!)

---

### 3. True RAG (Data-Driven Decisions) 🎯

**Definition of RAG**:
> Retrieval-Augmented Generation uses retrieved data to inform LLM decisions

**Old approach**: ❌ Partially RAG
- Retrieved products for context
- But still relied on hardcoded category mappings

**New approach**: ✅ Pure RAG
- Retrieved products provide categories
- LLM picks from actual retrieved categories
- Zero hardcoded mappings

---

### 4. Simpler Prompt (Easier to Maintain) 🛠️

**Line Count**:
- Old: ~1000 lines (rules, examples, mappings)
- New: ~300 lines (focus on RAG process)

**Complexity**:
- Old: LLM had to remember many rules and examples
- New: LLM just picks from what it sees

**Maintenance**:
- Old: Update prompt when categories change
- New: Categories come from data (no updates needed)

---

## Testing

### Test Cases

```bash
./venv/bin/python test_rag_category_selection.py
```

**Expected Results**:
```
1. Query: "test tubes glass"
   ✅ Should detect "Products/Glass & Plasticware/Tubes/Test Tubes"

2. Query: "nitrile gloves"
   ✅ Should detect "Products/Gloves & Apparel/Gloves"

3. Query: "pipettes"
   ✅ Should detect "Products/Pipettes"

4. Query: "clear"
   ✅ Should return null (ambiguous)
```

---

## Edge Cases Handled

### Multiple Matching Categories

**Query**: "tubes"
**Retrieved**: ["Products/.../Test Tubes", "Products/.../Centrifuge Tubes", ...]
**Decision**: Pick most popular category OR return null if ambiguous
**Result**: ✅ Conservative approach (null is safe)

### Attribute-Only Queries

**Query**: "blue"
**Retrieved**: ["Products/.../Gloves", "Products/.../Tubes", ...]
**Decision**: No category matches "blue" (it's an attribute)
**Result**: ✅ Return null (correct behavior)

### Brand-Only Queries

**Query**: "Mercedes Scientific"
**Retrieved**: ["Brand: Mercedes Scientific", "Products/.../Gloves", "Products/.../Pipettes"]
**Decision**: Skip "Brand:" category, but multiple "Products/" categories exist
**Result**: ✅ Return null (too ambiguous)

---

## Architecture Comparison

| Aspect | Old (Hardcoded) | New (Pure RAG) |
|--------|----------------|----------------|
| **Category Source** | Hardcoded in prompt | Retrieved from products |
| **Scalability** | ❌ Requires prompt updates | ✅ Scales automatically |
| **Accuracy** | ⚠️ Depends on examples | ✅ Data-driven |
| **Maintenance** | ❌ High (update mappings) | ✅ Low (no mappings) |
| **RAG Purity** | ⚠️ Partial RAG | ✅ Pure RAG |
| **Prompt Size** | ❌ ~1000 lines | ✅ ~300 lines |

---

## Summary

### What Changed

❌ **Old**: Middleware had hardcoded category mappings and prescriptive rules
```
"gloves" → "Products/Gloves & Apparel/Gloves"  (hardcoded)
```

✅ **New**: Middleware picks from actual retrieved product categories
```
Retrieved: ["Products/Gloves & Apparel/Gloves", ...]
LLM: "I see Gloves category in retrieved products, that's the best match"
```

### Why This Is Better

1. ✅ **True RAG** - Decisions based on retrieved data
2. ✅ **Scalable** - New categories handled automatically
3. ✅ **Simpler** - Less prompt complexity
4. ✅ **Maintainable** - No hardcoded mappings to update
5. ✅ **Matches dual-LLM** - Same RAG approach

### Bottom Line

The middleware now works **exactly like the dual-LLM RAG approach**:
- Retrieves products
- Extracts their categories
- Picks the best matching category
- No hardcoded mappings needed

This is **pure RAG** - letting the data drive decisions! 🎉
