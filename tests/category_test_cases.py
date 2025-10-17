"""
Test cases for category classification evaluation.

This dataset contains diverse query examples to test different category classification approaches.
Each test case includes the query, expected category behavior, and notes about why it's interesting.
"""

from typing import List, Dict, Any, Optional
from enum import Enum


class QueryType(str, Enum):
    """Type of query for categorization."""
    EXACT_MATCH = "exact_match"  # Exact SKU or product name
    GENERIC = "generic"  # Generic product type (e.g., "gloves")
    AMBIGUOUS = "ambiguous"  # Could match multiple categories
    SPECIFIC = "specific"  # Specific but not exact (e.g., "nitrile gloves")
    BRAND = "brand"  # Brand name query
    MULTI_CATEGORY = "multi_category"  # Products in multiple categories


class CategoryTestCase:
    """A single test case for category classification."""

    def __init__(
        self,
        query: str,
        query_type: QueryType,
        expected_category: Optional[str],
        should_apply_filter: bool,
        min_confidence: float,
        notes: str,
        alternative_categories: Optional[List[str]] = None
    ):
        """
        Initialize a test case.

        Args:
            query: The search query to test
            query_type: Type of query (exact, generic, ambiguous, etc.)
            expected_category: Expected category to be detected (None if ambiguous)
            should_apply_filter: Whether category filter should be applied
            min_confidence: Minimum acceptable confidence score (0-1)
            notes: Explanation of why this test case is important
            alternative_categories: Other acceptable categories (if multiple are valid)
        """
        self.query = query
        self.query_type = query_type
        self.expected_category = expected_category
        self.should_apply_filter = should_apply_filter
        self.min_confidence = min_confidence
        self.notes = notes
        self.alternative_categories = alternative_categories or []


# Test dataset
CATEGORY_TEST_CASES: List[CategoryTestCase] = [
    # === EXACT MATCH QUERIES ===
    # These should find exact products and prioritize them

    CategoryTestCase(
        query="Ansell gloves ANS 5789911",
        query_type=QueryType.EXACT_MATCH,
        expected_category="Gloves",
        should_apply_filter=True,
        min_confidence=0.7,
        notes="Real product example: Should prioritize exact SKU match even if other categories have more results"
    ),

    # === GENERIC QUERIES ===
    # Broad product types that should have high confidence

    CategoryTestCase(
        query="nitrile gloves",
        query_type=QueryType.GENERIC,
        expected_category="Gloves",
        should_apply_filter=True,
        min_confidence=0.8,
        notes="Generic product type, should have very high confidence"
    ),

    CategoryTestCase(
        query="pipettes",
        query_type=QueryType.GENERIC,
        expected_category="Pipettes",
        should_apply_filter=True,
        min_confidence=0.8,
        notes="Simple product category, clear intent"
    ),

    CategoryTestCase(
        query="microscope slides",
        query_type=QueryType.GENERIC,
        expected_category="Slides",
        should_apply_filter=True,
        min_confidence=0.7,
        notes="Common lab equipment, should map to slides category",
        alternative_categories=["Microscopy", "Slides & Coverslips"]
    ),

    CategoryTestCase(
        query="lab coats",
        query_type=QueryType.GENERIC,
        expected_category="Lab Coats",
        should_apply_filter=True,
        min_confidence=0.7,
        notes="Standard lab safety equipment",
        alternative_categories=["Safety Equipment", "Apparel"]
    ),

    # === SPECIFIC QUERIES ===
    # More specific than generic, but not exact matches

    CategoryTestCase(
        query="blue nitrile gloves size medium",
        query_type=QueryType.SPECIFIC,
        expected_category="Gloves",
        should_apply_filter=True,
        min_confidence=0.7,
        notes="Specific attributes but still clearly in gloves category"
    ),

    CategoryTestCase(
        query="sterile surgical gloves",
        query_type=QueryType.SPECIFIC,
        expected_category="Gloves",
        should_apply_filter=True,
        min_confidence=0.7,
        notes="Specific type of gloves with medical context",
        alternative_categories=["Surgical Supplies"]
    ),

    CategoryTestCase(
        query="1000μL adjustable pipette",
        query_type=QueryType.SPECIFIC,
        expected_category="Pipettes",
        should_apply_filter=True,
        min_confidence=0.7,
        notes="Specific volume and type, clearly pipettes"
    ),

    # === BRAND QUERIES ===
    # Brand names that span multiple categories

    CategoryTestCase(
        query="Mercedes Scientific",
        query_type=QueryType.BRAND,
        expected_category=None,  # Too broad
        should_apply_filter=False,
        min_confidence=0.0,
        notes="Brand name alone - should NOT apply category filter (products span many categories)"
    ),

    CategoryTestCase(
        query="Yamato",
        query_type=QueryType.BRAND,
        expected_category=None,  # Ambiguous
        should_apply_filter=False,
        min_confidence=0.3,
        notes="Ben's example: Brand with products in many categories (accessories, water purifiers, etc.)"
    ),

    CategoryTestCase(
        query="Thermo Fisher pipettes",
        query_type=QueryType.BRAND,
        expected_category="Pipettes",
        should_apply_filter=True,
        min_confidence=0.6,
        notes="Brand + product type should detect category"
    ),

    # === AMBIGUOUS QUERIES ===
    # Queries that could match multiple categories

    CategoryTestCase(
        query="filters",
        query_type=QueryType.AMBIGUOUS,
        expected_category=None,
        should_apply_filter=False,
        min_confidence=0.4,
        notes="Could be water filters, air filters, pipette filters, etc.",
        alternative_categories=["Water Purifiers", "Lab Equipment", "Filtration"]
    ),

    CategoryTestCase(
        query="tubes",
        query_type=QueryType.AMBIGUOUS,
        expected_category=None,
        should_apply_filter=False,
        min_confidence=0.5,
        notes="Could be test tubes, centrifuge tubes, storage tubes, etc.",
        alternative_categories=["Test Tubes", "Centrifuge", "Storage"]
    ),

    CategoryTestCase(
        query="containers",
        query_type=QueryType.AMBIGUOUS,
        expected_category=None,
        should_apply_filter=False,
        min_confidence=0.4,
        notes="Very broad - storage containers, sample containers, chemical containers, etc.",
        alternative_categories=["Storage", "Labware", "Containers"]
    ),

    # === MULTI-CATEGORY QUERIES ===
    # Products that legitimately belong in multiple categories

    CategoryTestCase(
        query="safety goggles",
        query_type=QueryType.MULTI_CATEGORY,
        expected_category="Safety Equipment",
        should_apply_filter=True,
        min_confidence=0.6,
        notes="Could be in 'Safety Equipment', 'Lab Supplies', or 'PPE'",
        alternative_categories=["PPE", "Lab Supplies", "Eye Protection"]
    ),

    CategoryTestCase(
        query="autoclave sterilization bags",
        query_type=QueryType.MULTI_CATEGORY,
        expected_category="Sterilization",
        should_apply_filter=True,
        min_confidence=0.6,
        notes="Could be in 'Sterilization', 'Bags', or 'Autoclave Supplies'",
        alternative_categories=["Bags", "Autoclave Supplies", "Biohazard"]
    ),

    # === EDGE CASES ===
    # Tricky queries that test system limits

    CategoryTestCase(
        query="clear",
        query_type=QueryType.AMBIGUOUS,
        expected_category=None,
        should_apply_filter=False,
        min_confidence=0.0,
        notes="Color attribute, not a product type - should not apply category filter"
    ),

    CategoryTestCase(
        query="large",
        query_type=QueryType.AMBIGUOUS,
        expected_category=None,
        should_apply_filter=False,
        min_confidence=0.0,
        notes="Size attribute, not a product type - should not apply category filter"
    ),

    CategoryTestCase(
        query="sterile",
        query_type=QueryType.AMBIGUOUS,
        expected_category=None,
        should_apply_filter=False,
        min_confidence=0.0,
        notes="Property attribute, could apply to many product types"
    ),

    CategoryTestCase(
        query="products under $50",
        query_type=QueryType.AMBIGUOUS,
        expected_category=None,
        should_apply_filter=False,
        min_confidence=0.0,
        notes="Price filter only, no category intent"
    ),

    # === QUERIES WITH FILTERS ===
    # Queries that include filters alongside category intent

    CategoryTestCase(
        query="gloves under $50",
        query_type=QueryType.SPECIFIC,
        expected_category="Gloves",
        should_apply_filter=True,
        min_confidence=0.7,
        notes="Category + price filter - should still detect category"
    ),

    CategoryTestCase(
        query="pipettes in stock between $100 and $500",
        query_type=QueryType.SPECIFIC,
        expected_category="Pipettes",
        should_apply_filter=True,
        min_confidence=0.7,
        notes="Category + stock + price range - should detect category"
    ),

    CategoryTestCase(
        query="Mercedes Scientific nitrile gloves size medium",
        query_type=QueryType.SPECIFIC,
        expected_category="Gloves",
        should_apply_filter=True,
        min_confidence=0.7,
        notes="Brand + category + size filter - should prioritize category"
    ),

    # === SEMANTIC SIMILARITY TESTS ===
    # Queries that use different terms for same concept

    CategoryTestCase(
        query="hand protection",
        query_type=QueryType.GENERIC,
        expected_category="Gloves",
        should_apply_filter=True,
        min_confidence=0.6,
        notes="Semantic match to 'gloves' - tests embedding quality",
        alternative_categories=["Safety Equipment", "PPE"]
    ),

    CategoryTestCase(
        query="liquid transfer tools",
        query_type=QueryType.GENERIC,
        expected_category="Pipettes",
        should_apply_filter=True,
        min_confidence=0.6,
        notes="Semantic match to 'pipettes' - tests understanding",
        alternative_categories=["Lab Equipment", "Liquid Handling"]
    ),

    CategoryTestCase(
        query="specimen viewing equipment",
        query_type=QueryType.GENERIC,
        expected_category="Microscopes",
        should_apply_filter=True,
        min_confidence=0.5,
        notes="Semantic match to 'microscopes' - tests conceptual understanding",
        alternative_categories=["Microscopy", "Slides"]
    ),
]


def get_test_cases_by_type(query_type: QueryType) -> List[CategoryTestCase]:
    """Get all test cases of a specific type."""
    return [tc for tc in CATEGORY_TEST_CASES if tc.query_type == query_type]


def get_test_cases_requiring_filter() -> List[CategoryTestCase]:
    """Get test cases that should apply category filter."""
    return [tc for tc in CATEGORY_TEST_CASES if tc.should_apply_filter]


def get_ambiguous_test_cases() -> List[CategoryTestCase]:
    """Get test cases that should NOT apply category filter."""
    return [tc for tc in CATEGORY_TEST_CASES if not tc.should_apply_filter]


if __name__ == "__main__":
    # Print test dataset summary
    print(f"Total test cases: {len(CATEGORY_TEST_CASES)}\n")

    print("Breakdown by query type:")
    for query_type in QueryType:
        cases = get_test_cases_by_type(query_type)
        print(f"  {query_type.value}: {len(cases)}")

    print(f"\nShould apply filter: {len(get_test_cases_requiring_filter())}")
    print(f"Should NOT apply filter: {len(get_ambiguous_test_cases())}")

    print("\n" + "="*60)
    print("Sample Test Cases:")
    print("="*60)

    for i, tc in enumerate(CATEGORY_TEST_CASES[:5], 1):
        print(f"\n{i}. Query: '{tc.query}'")
        print(f"   Type: {tc.query_type.value}")
        print(f"   Expected Category: {tc.expected_category or 'None (ambiguous)'}")
        print(f"   Apply Filter: {tc.should_apply_filter}")
        print(f"   Min Confidence: {tc.min_confidence}")
        print(f"   Notes: {tc.notes}")
