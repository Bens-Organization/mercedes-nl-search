#!/usr/bin/env python3
"""
Test script to verify NL extraction fields are now included.

Expected output should match old dual LLM format:
- nl_search_enabled: true
- nl_extracted_query: "centrifuge tube 50ml"
- nl_extracted_filters: "none" (or price/stock filters if present)
- nl_extracted_sort: "default" (or sort if specified)
- detected_category: "Products/Glass & Plasticware/Tubes/Centrifuge Tubes"
- category_confidence: 0.9
"""

import asyncio
import sys
import json
sys.path.insert(0, '/Users/alvinadefuin/Desktop/Projects/mercedes-natural-language-search')

from src.search_middleware import MiddlewareSearch

async def test_nl_fields():
    print("Testing NL extraction fields in response...")
    print("="*80)

    searcher = MiddlewareSearch()

    # Test query
    query = "Centrifuge tubes, 50ml capacity"
    print(f"\nQuery: {query}\n")

    # Execute search
    result = await searcher.search(query, max_results=20, debug=True)

    # Extract typesense_query section
    tq = result.get('typesense_query', {})

    print("\n" + "="*80)
    print("NL EXTRACTION FIELDS (should match old dual LLM format):")
    print("="*80)

    # NL extraction
    print("\n[NL Model Extraction]")
    print(f"  nl_search_enabled: {tq.get('nl_search_enabled')}")
    print(f"  nl_extracted_query: {tq.get('nl_extracted_query')}")
    print(f"  nl_extracted_filters: {tq.get('nl_extracted_filters')}")
    print(f"  nl_extracted_sort: {tq.get('nl_extracted_sort')}")

    # RAG classification
    print("\n[RAG Category Classification]")
    print(f"  detected_category: {tq.get('detected_category')}")
    print(f"  category_confidence: {tq.get('category_confidence')}")
    print(f"  category_applied: {tq.get('category_applied')}")
    print(f"  category_reasoning: {tq.get('category_reasoning')}")

    # Final execution
    print("\n[Final Search Execution]")
    print(f"  filters_applied: {tq.get('filters_applied')}")
    print(f"  total_results: {result.get('total')}")

    # Verify all required fields are present
    print("\n" + "="*80)
    required_fields = [
        'nl_search_enabled',
        'nl_extracted_query',
        'nl_extracted_filters',
        'nl_extracted_sort',
        'detected_category',
        'category_confidence',
        'category_applied'
    ]

    missing_fields = [f for f in required_fields if f not in tq]

    if not missing_fields:
        print("✅ SUCCESS: All NL extraction fields present!")
        print("✅ Response format now matches old dual LLM transparency")
    else:
        print(f"❌ FAILED: Missing fields: {missing_fields}")
    print("="*80)

    # Show comparison
    print("\n" + "="*80)
    print("COMPARISON:")
    print("="*80)
    print("\nOld Dual LLM Format:")
    print("  ✓ nl_search_enabled")
    print("  ✓ nl_extracted_query")
    print("  ✓ nl_extracted_filters")
    print("  ✓ nl_extracted_sort")
    print("  ✓ detected_category")
    print("  ✓ category_confidence")

    print("\nNew Decoupled Format (after fix):")
    for field in required_fields:
        status = "✓" if field in tq else "✗"
        print(f"  {status} {field}")

    return result

if __name__ == "__main__":
    asyncio.run(test_nl_fields())
