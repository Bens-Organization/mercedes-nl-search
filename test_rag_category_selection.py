#!/usr/bin/env python3
"""
Test RAG-based category selection (like dual-LLM approach).

The middleware should:
1. Look at categories in retrieved products
2. Pick the BEST matching category
3. NOT rely on hardcoded category mappings

Expected behavior:
- "test tubes glass" → Should find "Products/Glass & Plasticware/Tubes/Test Tubes"
- "nitrile gloves" → Should find "Products/Gloves & Apparel/Gloves"
- "pipettes" → Should find "Products/Pipettes"
- "clear" → Should return null (ambiguous)
"""

import asyncio
import sys
sys.path.insert(0, '/Users/alvinadefuin/Desktop/Projects/mercedes-natural-language-search')

from src.search_middleware import MiddlewareSearch

async def test_rag_category_selection():
    print("Testing RAG-Based Category Selection (like dual-LLM)")
    print("="*80)

    searcher = MiddlewareSearch()

    # Test cases showing RAG category selection
    test_cases = [
        {
            "query": "test tubes glass",
            "expected_category_contains": "Test Tubes",
            "description": "Should detect Test Tubes category from retrieved products"
        },
        {
            "query": "nitrile gloves",
            "expected_category_contains": "Gloves",
            "description": "Should detect Gloves category from retrieved products"
        },
        {
            "query": "pipettes",
            "expected_category_contains": "Pipettes",
            "description": "Should detect Pipettes category from retrieved products"
        },
        {
            "query": "beakers 1 liter",
            "expected_category_contains": "Beakers",
            "description": "Should detect Beakers category from retrieved products"
        },
        {
            "query": "clear",
            "expected_category_contains": None,
            "description": "Should return null for ambiguous attribute-only query"
        }
    ]

    print("\nTest Cases:")
    print("-"*80)

    results = []
    for i, test in enumerate(test_cases, 1):
        query = test["query"]
        expected = test["expected_category_contains"]
        description = test["description"]

        print(f"\n{i}. {description}")
        print(f"   Query: '{query}'")

        try:
            result = await searcher.search(query, max_results=20, debug=False)
            detected_category = result.get('detected_category')
            category_confidence = result.get('category_confidence', 0.0)
            category_applied = result.get('category_applied', False)

            print(f"   Detected: '{detected_category}'")
            print(f"   Confidence: {category_confidence}")
            print(f"   Applied: {category_applied}")

            # Check if expected category was found
            if expected is None:
                # Should be null
                if detected_category is None:
                    print(f"   ✅ PASS: Correctly returned null for ambiguous query")
                    results.append(True)
                else:
                    print(f"   ❌ FAIL: Should have returned null but got '{detected_category}'")
                    results.append(False)
            else:
                # Should contain expected text
                if detected_category and expected.lower() in detected_category.lower():
                    print(f"   ✅ PASS: Found expected category")
                    results.append(True)
                else:
                    print(f"   ❌ FAIL: Expected category containing '{expected}'")
                    results.append(False)

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            results.append(False)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("✅ All tests passed! RAG category selection working correctly.")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Review category selection logic.")

    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_rag_category_selection())
