#!/usr/bin/env python3
"""
End-to-end test for JAI-2194 using the actual search API

This test calls the actual search module (not just middleware retrieval)
to verify the category weight fix works in production.
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from search import Search


async def test_query(query: str, expected_category_patterns: list[str], avoid_patterns: list[str] = None):
    """
    Test a query using the actual search API.

    Args:
        query: Search query
        expected_category_patterns: List of category substrings we expect to see
        avoid_patterns: List of name/category patterns we should avoid in top results
    """
    print(f"\n{'='*80}")
    print(f"Testing query: '{query}'")
    print(f"{'='*80}")

    search = Search()
    response = await search.search(query, max_results=20, debug=False)

    print(f"\nTotal found: {response.total}")
    print(f"\nTop 5 results:")
    for i, product in enumerate(response.results[:5]):
        print(f"\n{i+1}. {product.name}")
        print(f"   SKU: {product.sku}")
        print(f"   Price: ${product.price:.2f}" if product.price else "   Price: N/A")
        print(f"   Stock: {product.stock_status}")
        print(f"   Categories: {product.categories[:2]}")  # Show first 2 categories

    # Check for expected categories
    print(f"\n--- Validation ---")
    found_expected = False
    for product in response.results[:10]:  # Check top 10 results
        for expected in expected_category_patterns:
            if any(expected.lower() in cat.lower() for cat in product.categories):
                print(f"✅ Found expected category pattern '{expected}' in top 10 results")
                found_expected = True
                break
        if found_expected:
            break

    if not found_expected:
        print(f"❌ Expected category patterns {expected_category_patterns} NOT found in top 10 results")

    # Check for patterns to avoid
    if avoid_patterns:
        found_avoid = []
        for i, product in enumerate(response.results[:5]):  # Check top 5 results
            name = product.name.lower()
            categories = ' '.join(product.categories).lower()

            for avoid in avoid_patterns:
                if avoid.lower() in name or avoid.lower() in categories:
                    found_avoid.append(f"  Position {i+1}: {product.name}")

        if found_avoid:
            print(f"⚠️  WARNING: Found avoid patterns in top 5:")
            for item in found_avoid:
                print(item)
        else:
            print(f"✅ Avoid patterns {avoid_patterns} not found in top 5 results")

    return response


async def main():
    """Run all test cases from JAI-2194"""

    print("\n" + "="*80)
    print("JAI-2194: End-to-End Search API Test")
    print("="*80)

    # Issue 1: "microscope" - should return actual microscopes, not accessories
    await test_query(
        query="microscope",
        expected_category_patterns=["Microscope"],
        avoid_patterns=["Cover"]  # Microscope covers should not be in top results
    )

    # Issue 2: "stains" - should return actual stain products, not staining dishes
    await test_query(
        query="stains",
        expected_category_patterns=["Stains", "Chemicals"],
        avoid_patterns=["Dish", "Dipper", "Rack"]
    )

    # Issue 3: "slide" - should prioritize general-purpose slides over storage
    await test_query(
        query="slide",
        expected_category_patterns=["Microscope Slides"],
        avoid_patterns=["Storage", "Mailer", "Box"]
    )

    # Issue 4: "microscope slide" - should return actual slides, not storage
    await test_query(
        query="microscope slide",
        expected_category_patterns=["Microscope Slides"],
        avoid_patterns=["Storage", "Mailer", "Box", "Cabinet"]
    )

    print("\n" + "="*80)
    print("Test suite completed")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
