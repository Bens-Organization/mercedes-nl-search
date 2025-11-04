#!/usr/bin/env python3
"""Test model number search fix - verifies normalized fields work correctly."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.config import Config
import typesense

def test_model_number_search():
    """Test that model number variations are found correctly."""
    print("=" * 70)
    print("MODEL NUMBER SEARCH FIX - VERIFICATION TESTS")
    print("=" * 70)

    client = typesense.Client(Config.get_typesense_config())
    collection = Config.TYPESENSE_COLLECTION_NAME

    # Test cases
    test_cases = [
        {
            "query": "tnr700s",
            "expected_sku": "TNR 700S",
            "description": "Search without spaces/separators should find product with spaces"
        },
        {
            "query": "TNR-700S",
            "expected_sku": "TNR 700S",
            "description": "Search with dashes should find product with spaces"
        },
        {
            "query": "blu touch",
            "expected_contains": "BluTouch",
            "description": "Search with space should find camelCase product name"
        },
        {
            "query": "blutouch",
            "expected_contains": "BluTouch",
            "description": "Search without space should find camelCase product name"
        }
    ]

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"  Query: '{test['query']}'")

        # Execute search
        result = client.collections[collection].documents.search({
            'q': test['query'],
            'query_by': 'name,sku,name_normalized,sku_normalized',
            'query_by_weights': '100,100,4,4',
            'per_page': 5
        })

        found = result.get('found', 0)
        print(f"  Results: {found}")

        # Check if expected result is found
        passed = False
        if found > 0:
            hits = result.get('hits', [])

            # Check for expected SKU or name content
            for hit in hits[:3]:
                doc = hit['document']
                sku = doc.get('sku', '')
                name = doc.get('name', '')

                if 'expected_sku' in test and sku == test['expected_sku']:
                    passed = True
                    print(f"  ✅ PASS - Found expected SKU: {sku}")
                    print(f"     Product: {name[:60]}")
                    break
                elif 'expected_contains' in test and test['expected_contains'] in name:
                    passed = True
                    print(f"  ✅ PASS - Found product with '{test['expected_contains']}' in name")
                    print(f"     Product: {name[:60]}")
                    print(f"     SKU: {sku}")
                    break

        if not passed:
            print(f"  ❌ FAIL - Expected result not found")
            all_passed = False

            # Show what was found instead
            if found > 0:
                print(f"  Found instead:")
                for hit in result.get('hits', [])[:3]:
                    doc = hit['document']
                    print(f"    - {doc.get('name', '')[:50]} | SKU: {doc.get('sku', '')}")

    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Model number search fix is working!")
    else:
        print("❌ SOME TESTS FAILED - Model number search fix needs attention")
    print("=" * 70)

    return all_passed

if __name__ == "__main__":
    success = test_model_number_search()
    sys.exit(0 if success else 1)
