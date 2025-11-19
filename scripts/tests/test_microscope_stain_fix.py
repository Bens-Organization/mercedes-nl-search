#!/usr/bin/env python3
"""
Test file for JAI-2194: Search issues for microscope, stains, and slide

This test validates the fix for the retrieval weight configuration that was
causing accessories to rank higher than main products.

Issue: Category weight (1x) vs Name weight (100x) caused:
- "microscope" → covers/accessories instead of actual microscopes
- "stains" → staining dishes instead of actual stains
- "slide" → specialized slides (IHC) instead of general-purpose slides
- "microscope slide" → storage boxes instead of actual slides

Fix: Increase category weight to prioritize main products over accessories
"""

import asyncio
from src.openai_middleware import retrieve_products


async def test_query(query: str, expected_category_patterns: list[str], avoid_patterns: list[str] = None):
    """
    Test a query and check if results match expected patterns.

    Args:
        query: Search query
        expected_category_patterns: List of category substrings we expect to see
        avoid_patterns: List of name/category patterns we should avoid
    """
    print(f"\n{'='*80}")
    print(f"Testing query: '{query}'")
    print(f"{'='*80}")

    products = await retrieve_products(query, limit=20)

    print(f"\nRetrieved {len(products)} products:")
    print(f"\nTop 5 results:")
    for i, product in enumerate(products[:5]):
        print(f"\n{i+1}. {product['name']}")
        print(f"   SKU: {product['sku']}")
        print(f"   Price: ${product['price']:.2f}" if product.get('price') else "   Price: N/A")
        print(f"   Categories: {product.get('categories', [])[:2]}")  # Show first 2 categories

    # Check for expected categories
    print(f"\n--- Validation ---")
    found_expected = False
    for product in products[:10]:  # Check top 10 results
        categories = product.get('categories', [])
        for expected in expected_category_patterns:
            if any(expected.lower() in cat.lower() for cat in categories):
                print(f"✅ Found expected category pattern '{expected}' in top 10 results")
                found_expected = True
                break
        if found_expected:
            break

    if not found_expected:
        print(f"❌ Expected category patterns {expected_category_patterns} NOT found in top 10 results")

    # Check for patterns to avoid
    if avoid_patterns:
        found_avoid = False
        for product in products[:5]:  # Check top 5 results
            name = product.get('name', '').lower()
            categories = ' '.join(product.get('categories', [])).lower()

            for avoid in avoid_patterns:
                if avoid.lower() in name or avoid.lower() in categories:
                    print(f"⚠️  WARNING: Found avoid pattern '{avoid}' in top 5: {product['name']}")
                    found_avoid = True

        if not found_avoid:
            print(f"✅ Avoid patterns {avoid_patterns} not found in top 5 results")

    return products


async def main():
    """Run all test cases from JAI-2194"""

    print("\n" + "="*80)
    print("JAI-2194: Test Suite for Microscope, Stains, and Slide Search Issues")
    print("="*80)

    # Issue 1: "microscope" - should return actual microscopes, not accessories
    await test_query(
        query="microscope",
        expected_category_patterns=["Microscope"],  # Should find microscope category
        avoid_patterns=["Cover", "Slide"]  # Avoid accessories
    )

    # Issue 2: "stains" - should return actual stain products, not staining dishes
    await test_query(
        query="stains",
        expected_category_patterns=["Stains", "Chemicals"],  # Should find stain products
        avoid_patterns=["Dish", "Dipper", "Rack"]  # Avoid staining accessories
    )

    # Issue 3: "slide" - should prioritize general-purpose slides over specialized ones
    await test_query(
        query="slide",
        expected_category_patterns=["Microscope Slides"],  # Should find slide category
        avoid_patterns=["Storage", "Mailer", "Box"]  # Avoid storage accessories (first few results)
    )

    # Issue 4: "microscope slide" - should return actual slides, not storage
    await test_query(
        query="microscope slide",
        expected_category_patterns=["Microscope Slides"],  # Should find slide category
        avoid_patterns=["Storage", "Mailer", "Box", "Cabinet"]  # Avoid storage accessories
    )

    print("\n" + "="*80)
    print("Test suite completed")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
