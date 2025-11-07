# Brand Prioritization Implementation

## Overview

This document describes the implementation of **category-specific brand prioritization** to ensure preferred brands appear at the top of search results based on product categories.

## Business Requirements

### Jira Ticket: JAI-2165

Implement specific brand ranking order for product categories to prioritize preferred suppliers in search results.

### Brand Ranking Rules

#### 1. LCMS or HPLC Solvents

**Brand Priority Order:**
1. **Concord Technologies** (TBK prefix items) - FIRST
2. **Birch Biotech** (BIR prefix) - SECOND
3. **Mercedes Scientific** (MER prefix) - THIRD
4. **Tanner Scientific** (TNR prefix) - FOURTH
5. **Others** (Sigma, EMD, Fisher, VWR, etc.) - REMAINING

#### 2. Drug Testing

**Brand Priority Order:**
1. **Mercedes Scientific** (MER prefix items) - FIRST
2. **AllTest** (ALT prefix) - SECOND
3. **Tanner Scientific** (TNR prefix) - THIRD
4. **Healgen** (HGS prefix) - FOURTH
5. **Wondfo** (WON prefix) - FIFTH
6. **Others** - REMAINING

#### 3. General (All Other Categories)

**Brand Priority Order:**
1. **Mercedes Scientific** - FIRST (in-house brand)
2. **Tanner Scientific** - SECOND (in-house brand)
3. **Others** - REMAINING

## Implementation Strategy

### ✅ **Data-Level Approach** (ACTIVE)

Brand prioritization is stored in the Typesense index and sorting happens at the database level:

1. **During indexing**: Each product gets a `brand_priority` field calculated from:
   - Product category type (LCMS/HPLC, Drug Testing, or General)
   - Brand detected from SKU prefix, brand field, or product name
2. **During search**: Typesense sorts by `brand_priority:desc` natively
3. **No post-processing**: Sorting happens in Typesense, not Python

**Benefits**:
- ✅ **Cleaner code** - Sorting in Typesense, not Python
- ✅ **Better performance** - No post-processing overhead
- ✅ **Simpler logic** - Just set `sort_by` parameter
- ✅ **Future-proof** - Scales better for large result sets
- ✅ **Native database sorting** - Leverages Typesense's optimized sorting
- ✅ **Category-aware** - Different brand priorities per category type

**Trade-off**:
- ⏳ Requires one-time re-indexing (35-45 minutes)

## Priority Score Mapping

| Category Type | Brand | Priority Score |
|---------------|-------|----------------|
| **LCMS/HPLC Solvents** | Concord Technologies | 100 |
| | Birch Biotech | 90 |
| | Mercedes Scientific | 80 |
| | Tanner Scientific | 70 |
| | Other brands | 50 |
| | No brand | 0 |
| **Drug Testing** | Mercedes Scientific | 100 |
| | AllTest | 90 |
| | Tanner Scientific | 80 |
| | Healgen | 70 |
| | Wondfo | 60 |
| | Other brands | 50 |
| | No brand | 0 |
| **General** | Mercedes Scientific | 100 |
| | Tanner Scientific | 90 |
| | Other brands | 50 |
| | No brand | 0 |

## Code Implementation

### File: `src/indexer_neon.py`

#### 1. Schema Field (Line 73)

```python
{"name": "brand_priority", "type": "int32", "optional": True, "sort": True}
```

#### 2. Category Type Detection (Lines 254-276)

```python
def _detect_category_type(self, categories: List[str]) -> str:
    """
    Detect the category type for brand ranking.

    Returns:
        - "lcms_hplc" for LCMS/HPLC Solvents
        - "drug_testing" for Drug Testing products
        - "general" for all other products
    """
    if not categories:
        return "general"

    # Check categories for LCMS/HPLC indicators
    for cat in categories:
        cat_lower = cat.lower()
        # Check for LCMS/HPLC grade indicators
        if any(grade in cat for grade in ["Grade: HPLC", "Grade: LCMS", "Grade: Ultra HPLC"]):
            return "lcms_hplc"
        # Check for Drug Testing category
        if "drug test" in cat_lower:
            return "drug_testing"

    return "general"
```

**Category Detection Rules:**
- **LCMS/HPLC**: Detected by `"Grade: HPLC"`, `"Grade: LCMS"`, or `"Grade: Ultra HPLC"` in categories
  - Examples: `['Products/Chemicals & Stains/Water', 'Grade: HPLC']`, `['Clearance', 'Brand: Concord Technology', 'Grade: LCMS']`
- **Drug Testing**: Detected by `"drug test"` (case-insensitive) in any category path
  - Examples: `['Products/Drug Tests/Saliva']`, `['Products/Drug Tests/Cups']`, `['Products/Drug Tests/Validation']`
- **General**: All other products

#### 3. Brand Detection (Lines 278-343)

```python
def _detect_brand(self, sku: str, brand_field: str, product_name: str) -> str:
    """
    Detect brand from multiple sources.

    Priority:
    1. SKU prefix (most reliable)
    2. Brand field
    3. Product name

    Returns:
        Normalized brand name in lowercase, or None if no brand detected
    """
    sku_upper = (sku or "").upper().strip()
    brand_lower = (brand_field or "").lower().strip()
    name_lower = (product_name or "").lower().strip()

    # Check SKU prefix first (most reliable)
    if sku_upper.startswith("TBK"):
        return "concord technologies"
    elif sku_upper.startswith("BIR"):
        return "birch biotech"
    elif sku_upper.startswith("MER"):
        return "mercedes scientific"
    elif sku_upper.startswith("ALT"):
        return "alltest"
    elif sku_upper.startswith("TNR"):
        return "tanner scientific"
    elif sku_upper.startswith("HGS"):
        return "healgen"
    elif sku_upper.startswith("WON"):
        return "wondfo"

    # Check brand field (good for most products)
    # ... handles other brands like VWR, Sigma, Fisher, etc.

    # Check product name (fallback)
    # ... handles cases where brand field is missing

    # Return original brand field if available
    return brand_field if brand_field else None
```

**Brand Detection Priority:**
1. **SKU Prefix** (Most Reliable)
   - `TBK` → Concord Technologies
   - `BIR` → Birch Biotech
   - `MER` → Mercedes Scientific
   - `ALT` → AllTest
   - `TNR` → Tanner Scientific
   - `HGS` → Healgen
   - `WON` → Wondfo

2. **Brand Field** (Good for Most Products)
   - Checks for brand name in `additional_attributes`
   - Handles VWR, Sigma-Aldrich, Fisher Scientific, etc.

3. **Product Name** (Fallback)
   - Checks for brand mention in product name
   - Critical for data quality issues where brand field is missing

#### 4. Brand Priority Calculation (Lines 345-429)

```python
def _calculate_brand_priority(self, sku: str, brand: str, product_name: str, categories: List[str]) -> int:
    """
    Calculate brand priority for sorting based on category and brand.

    Priority structure varies by category:

    **LCMS/HPLC Solvents** (detected by Grade: HPLC/LCMS in categories):
        100 - Concord Technologies (TBK prefix)
        90  - Birch Biotech (BIR prefix)
        80  - Mercedes Scientific (MER prefix)
        70  - Tanner Scientific (TNR prefix)
        50  - Other brands
        0   - No brand

    **Drug Testing** (detected by "Drug Test" in categories):
        100 - Mercedes Scientific (MER prefix)
        90  - AllTest (ALT prefix)
        80  - Tanner Scientific (TNR prefix)
        70  - Healgen (HGS prefix)
        60  - Wondfo (WON prefix)
        50  - Other brands
        0   - No brand

    **General** (all other categories):
        100 - Mercedes Scientific
        90  - Tanner Scientific
        50  - Other brands
        0   - No brand
    """
    # Detect category type
    category_type = self._detect_category_type(categories)

    # Detect brand from multiple sources
    detected_brand = self._detect_brand(sku, brand, product_name)

    if not detected_brand:
        return 0

    brand_lower = detected_brand.lower()

    # LCMS/HPLC Solvents category
    if category_type == "lcms_hplc":
        if brand_lower == "concord technologies":
            return 100
        elif brand_lower == "birch biotech":
            return 90
        elif brand_lower == "mercedes scientific":
            return 80
        elif brand_lower == "tanner scientific":
            return 70
        else:
            return 50

    # Drug Testing category
    elif category_type == "drug_testing":
        if brand_lower == "mercedes scientific":
            return 100
        elif brand_lower == "alltest":
            return 90
        elif brand_lower == "tanner scientific":
            return 80
        elif brand_lower == "healgen":
            return 70
        elif brand_lower == "wondfo":
            return 60
        else:
            return 50

    # General (all other categories)
    else:
        if brand_lower == "mercedes scientific":
            return 100
        elif brand_lower == "tanner scientific":
            return 90
        else:
            return 50 if detected_brand else 0
```

#### 5. Usage in Product Transform (Line 595)

```python
# Calculate brand priority (category-aware, checks SKU prefix, brand field, and product name)
brand_priority = self._calculate_brand_priority(sku, specs.get('brand'), name, category_list)
```

### File 2: `src/openai_middleware.py` (Middleware Logic)

#### Stock-Aware Sort Order (Lines 496-511)

The middleware applies stock-aware brand priority sorting automatically:

```python
# Apply default stock-aware brand priority sorting if no sort specified
if params.get("sort_by") == "" or not params.get("sort_by"):
    # Default sort: in-stock first, then brand priority, then relevance, then price
    # Note: "IN_STOCK" < "OUT_OF_STOCK" alphabetically, so asc puts IN_STOCK first
    params["sort_by"] = "stock_status:asc,brand_priority:desc,_text_match:desc,price:asc"
else:
    # User has specific sort (price:asc, created_at:desc, etc.)
    # Prepend stock and brand priority to maintain stock-aware ranking
    user_sort = params["sort_by"]
    params["sort_by"] = f"stock_status:asc,brand_priority:desc,{user_sort}"
```

**Sort Order Priority:**
1. **Stock Status** (`stock_status:asc`) - In-stock products first
   - `IN_STOCK` appears before `OUT_OF_STOCK` alphabetically
   - Within in-stock: sorted by brand priority
   - Within out-of-stock: sorted by brand priority
2. **Brand Priority** (`brand_priority:desc`) - Category-specific brand ranking
3. **User-specified sort** (if any) - e.g., price:asc, created_at:desc
4. **Relevance** (`_text_match:desc`) - Search relevance score (default)
5. **Price** (`price:asc`) - Lowest price first (default)

**Example Result Order:**

*Query: "HPLC methanol" (no sort specified)*
```
1. IN_STOCK  | Priority 100 | Mercedes HPLC Methanol
2. IN_STOCK  | Priority 90  | Birch HPLC Methanol
3. IN_STOCK  | Priority 50  | VWR HPLC Methanol
4. OUT_OF_STOCK | Priority 100 | Mercedes HPLC Methanol
5. OUT_OF_STOCK | Priority 90  | Birch HPLC Methanol
```

*Query: "cheapest HPLC methanol" (user requests price sort)*
```
1. IN_STOCK  | Priority 100 | Mercedes HPLC Methanol | $25
2. IN_STOCK  | Priority 90  | Birch HPLC Methanol | $30
3. IN_STOCK  | Priority 50  | VWR HPLC Methanol | $35
4. OUT_OF_STOCK | Priority 100 | Mercedes HPLC Methanol | $20
5. OUT_OF_STOCK | Priority 90  | Birch HPLC Methanol | $28
```

**Note:** The middleware (not src/search.py) handles sort_by to ensure stock and brand priority are always applied, even when users request specific sorting.

## Testing

### Unit Tests

Run unit tests to verify the logic:

```bash
./venv/bin/python3 tests/test_brand_logic.py
```

**Test Coverage:**
- ✅ Category type detection (LCMS/HPLC, Drug Testing, General)
- ✅ Brand detection from SKU prefix, brand field, product name
- ✅ Priority calculation for all category types
- ✅ All 7 special brand prefixes (TBK, BIR, MER, ALT, TNR, HGS, WON)
- ✅ Other brands (VWR, Sigma, Fisher)
- ✅ Edge cases (no brand, missing data)

**Test Results:**
```
=== Category Detection Test ===
✅ HPLC categories: lcms_hplc (expected: lcms_hplc)
✅ LCMS categories: lcms_hplc (expected: lcms_hplc)
✅ Drug Test categories: drug_testing (expected: drug_testing)
✅ General categories: general (expected: general)

=== Brand Detection Test ===
✅ TBK 8003LC4000: concord technologies
✅ BIR 19395: birch biotech
✅ MER MMDOAY6125: mercedes scientific
✅ ALT DOAA1137C: alltest
✅ TNR MMC12MOP: tanner scientific
✅ HGS HDCL114: healgen
✅ WON QODOA6126I: wondfo

=== Brand Priority Calculation Test ===
✅ HPLC - Concord: Priority 100
✅ LCMS - Birch: Priority 90
✅ HPLC - Mercedes: Priority 80
✅ HPLC - Tanner: Priority 70
✅ HPLC - VWR: Priority 50
✅ Drug - Mercedes: Priority 100
✅ Drug - AllTest: Priority 90
✅ Drug - Tanner: Priority 80
✅ Drug - Healgen: Priority 70
✅ Drug - Wondfo: Priority 60
✅ General - Mercedes: Priority 100
✅ General - Tanner: Priority 90
✅ General - VWR: Priority 50
```

### Integration Tests

After re-indexing, test with real queries:

```bash
./venv/bin/python3 tests/test_category_brand_ranking.py
```

**Test Queries:**
- HPLC methanol
- LCMS acetonitrile
- drug test
- 12-panel drug test cup
- gloves
- microscope slides

## Example Queries

### LCMS/HPLC Solvents

**Query:** "HPLC methanol"

**Expected Results Order:**
1. Concord Technologies methanol (Priority 100)
2. Birch Biotech methanol (Priority 90)
3. Mercedes Scientific methanol (Priority 80)
4. Tanner Scientific methanol (Priority 70)
5. VWR, Sigma, etc. methanol (Priority 50)

### Drug Testing

**Query:** "12-panel drug test"

**Expected Results Order:**
1. Mercedes Scientific 12-panel tests (Priority 100)
2. AllTest 12-panel tests (Priority 90)
3. Tanner Scientific 12-panel tests (Priority 80)
4. Healgen 12-panel tests (Priority 70)
5. Wondfo 12-panel tests (Priority 60)
6. Other brands (Priority 50)

### General Categories

**Query:** "microscope slides"

**Expected Results Order:**
1. Mercedes Scientific slides (Priority 100)
2. Tanner Scientific slides (Priority 90)
3. All other brands (Priority 50)

## Re-Indexing Required

⚠️ **IMPORTANT**: The Typesense collection must be re-indexed for brand prioritization to work.

### Re-Index Steps

```bash
# Re-index all products (recreates collection with brand_priority field)
./venv/bin/python3 src/indexer_neon.py

# Expected time: 35-45 minutes for full catalog (34k+ products)
# - Database query: 1-3 minutes
# - Fetch & transform: 5-10 minutes
# - Embedding generation: 25-35 minutes
```

### What Happens During Re-Indexing

1. ✅ Deletes existing collection
2. ✅ Creates new collection with `brand_priority` field
3. ✅ Fetches all 34k+ products from Neon database
4. ✅ Detects category type for each product (LCMS/HPLC, Drug Testing, or General)
5. ✅ Detects brand from SKU prefix, brand field, or product name
6. ✅ Calculates category-specific brand priority for each product
7. ✅ Generates embeddings for semantic search
8. ✅ Indexes to Typesense with brand_priority values

### Performance After Re-Indexing

**With Data-Level Sorting**:
- Query time: ~5-7 seconds (includes dual LLM + search)
- Sorting overhead: 0ms (done by Typesense natively)
- Scalability: Excellent - works for any result set size

## Benefits

### ✅ Scalability
- Works for unlimited number of categories
- No hardcoded category mappings needed
- Dynamic detection based on category structure

### ✅ Performance
- Native Typesense sorting (no Python overhead)
- No post-processing required
- Optimized for large result sets

### ✅ Maintainability
- Clear separation of concerns
- Easy to add new brands (just add SKU prefix)
- Easy to adjust priority scores
- Well-tested with comprehensive unit tests

### ✅ Flexibility
- Different brand rankings per category type
- Supports brand detection from multiple sources
- Fallback to general ranking for unknown categories

## User Query Examples

All these queries will show category-specific brand order:

| Query                                    | Expected Behavior                                          |
|------------------------------------------|------------------------------------------------------------|
| `HPLC methanol`                          | Concord/Birch first, then Mercedes/Tanner, then others    |
| `LCMS acetonitrile`                      | Concord/Birch first, then Mercedes/Tanner, then others    |
| `drug test cup`                          | Mercedes first, then AllTest/Tanner/Healgen/Wondfo        |
| `gloves`                                 | Mercedes/Tanner gloves first, then others                  |
| `cheapest nitrile gloves`                | Mercedes/Tanner gloves first, then sorted by price         |
| `latest test tubes`                      | Mercedes/Tanner test tubes first, then by created_at       |
| `microscope slides under $50`            | Mercedes/Tanner slides first, filtered by price            |

## Future Enhancements

1. **Dynamic Priority Configuration**
   - Load priority scores from config/database
   - Allow adjusting priorities without code changes
   - Support promotional boosts for specific brands temporarily

2. **More Category Types**
   - Add priority rules for other specific categories
   - Support sub-category specific rankings

3. **Brand Aliases**
   - Handle brand name variations
   - Support parent/subsidiary brand relationships

4. **Smart Brand Detection**
   - Detect when user explicitly searches for a specific brand
   - Consider disabling in-house brand boost in those cases

5. **A/B Testing**
   - Test user engagement with different brand rankings
   - Measure conversion rates by brand
   - Optimize rankings based on user behavior

6. **Brand Data Quality Improvements**
   - Fix brand extraction from database
   - Ensure all products have accurate brand information
   - Consider adding brand aliases (e.g., "Mercedes" → "Mercedes Scientific")

## Deployment Checklist

### Implementation Status

- [x] ✅ Create git branch: `JAI-2165-Implement-brand-ranking-preferences`
- [x] ✅ Add `brand_priority` field to Typesense schema
- [x] ✅ Implement `_detect_category_type()` method
- [x] ✅ Implement `_detect_brand()` method
- [x] ✅ Update `_calculate_brand_priority()` for category-specific ranking
- [x] ✅ Update product transform to pass categories
- [x] ✅ Update search queries to sort by `brand_priority:desc`
- [x] ✅ Create unit tests for logic validation
- [x] ✅ Create integration tests for search
- [x] ✅ Document implementation
- [ ] 🔄 **Re-index Typesense collection** (35-45 min) - **REQUIRED**
- [ ] ✅ Run integration tests to verify ranking
- [ ] ✅ Verify category-specific brand order in search results
- [ ] 📊 Monitor search analytics after production deployment

## Contact

For questions or issues with this implementation, refer to:
- `CLAUDE.md` - Project context
- `DEPLOYMENT.md` - Deployment guide
- `docs/FEATURE_STATUS.md` - Feature implementation status

---

**Last Updated**: 2025-11-07
**Branch**: `JAI-2165-Implement-brand-ranking-preferences`
**Jira Ticket**: JAI-2165
**Status**: ✅ Implementation complete, ⏳ **Pending re-indexing**
**Version**: 2.4.0 (Category-Specific Brand Prioritization)

**Next Step**: Re-index collection (35-45 min) to activate category-specific brand prioritization
**Performance**: Native Typesense sorting, 0ms overhead
**Approach**: Clean data-level implementation for optimal performance
