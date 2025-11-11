#!/usr/bin/env python3
"""
Verify brand priorities in Typesense index.
Run this AFTER re-indexing to check if category-specific priorities are correctly set.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
import typesense


def verify_priorities():
    """Verify brand priorities for different categories."""
    print("=" * 80)
    print("BRAND PRIORITY VERIFICATION")
    print("=" * 80)
    print()

    client = typesense.Client(Config.get_typesense_config())

    test_cases = [
        {
            "name": "LCMS/HPLC Solvents",
            "query": "HPLC methanol",
            "query_by": "name,categories",
            "expected_brands": ["Concord Technology", "Birch Biotech", "Mercedes Scientific", "Tanner Scientific"],
            "expected_priorities": [100, 90, 80, 70]
        },
        {
            "name": "Drug Testing",
            "query": "drug test cup",
            "query_by": "name,categories",
            "expected_brands": ["Mercedes Scientific", "AllTest", "Tanner Scientific", "Healgen", "Wondfo"],
            "expected_priorities": [100, 90, 80, 70, 60]
        },
        {
            "name": "General Category - Gloves",
            "query": "nitrile gloves",
            "query_by": "name,categories",
            "expected_brands": ["Mercedes Scientific", "Tanner Scientific"],
            "expected_priorities": [100, 90]
        },
    ]

    all_passed = True

    for test in test_cases:
        print(f"Test: {test['name']}")
        print(f"Query: '{test['query']}'")
        print("-" * 80)

        try:
            result = client.collections['mercedes_products'].documents.search({
                'q': test['query'],
                'query_by': test['query_by'],
                'sort_by': 'stock_status:asc,brand_priority:desc,_text_match:desc,price:asc',
                'per_page': 15
            })

            hits = result.get('hits', [])

            if not hits:
                print("⚠️  No results found")
                all_passed = False
                print()
                continue

            # Show top results with priorities
            print(f"\nTop {min(10, len(hits))} Results:")
            brand_priority_map = {}

            for i, hit in enumerate(hits[:10], 1):
                doc = hit['document']
                sku = doc.get('sku', 'N/A')
                brand = doc.get('brand', 'Unknown')
                priority = doc.get('brand_priority', 0)
                name = doc.get('name', 'N/A')[:50]

                # Track unique brand priorities
                if brand not in brand_priority_map:
                    brand_priority_map[brand] = priority

                print(f"  {i}. Priority: {priority:3d} | {brand:30s} | {sku}")
                print(f"     {name}")

            # Verify expected brands and priorities
            print("\nVerification:")
            test_passed = True

            for expected_brand, expected_priority in zip(test['expected_brands'], test['expected_priorities']):
                found = False
                for brand, priority in brand_priority_map.items():
                    if expected_brand.lower() in brand.lower() or brand.lower() in expected_brand.lower():
                        found = True
                        if priority == expected_priority:
                            print(f"  ✅ {expected_brand}: Priority {priority} (expected {expected_priority})")
                        else:
                            print(f"  ❌ {expected_brand}: Priority {priority} (expected {expected_priority})")
                            test_passed = False
                        break

                if not found:
                    print(f"  ⚠️  {expected_brand}: Not found in results")

            if test_passed:
                print(f"\n✅ {test['name']} - PASSED")
            else:
                print(f"\n❌ {test['name']} - FAILED")
                all_passed = False

        except Exception as e:
            print(f"❌ Error: {e}")
            all_passed = False

        print()

    print("=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED - Category-specific brand ranking is working!")
    else:
        print("❌ SOME TESTS FAILED - Check priorities above")
        print("\n⚠️  Did you re-index? Run: ./venv/bin/python3 src/indexer_neon.py")
    print("=" * 80)


if __name__ == "__main__":
    verify_priorities()
