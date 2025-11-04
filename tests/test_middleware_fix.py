#!/usr/bin/env python3
"""Test middleware fix - verify normalized fields work for model number search."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.config import Config
import typesense
import json

def test_middleware_retrieval():
    """
    Test that middleware's retrieval search uses normalized fields correctly.
    This simulates the retrieve_products() function in openai_middleware.py
    """
    print("=" * 70)
    print("MIDDLEWARE RETRIEVAL SEARCH - MODEL NUMBER FIX TEST")
    print("=" * 70)

    client = typesense.Client(Config.get_typesense_config())
    collection = Config.TYPESENSE_COLLECTION_NAME

    # Test query: "tnr700s" (should find "TNR 700S" gloves, NOT "TN7000" microtome)
    query = "tnr700s"

    print(f"\nTest Query: '{query}'")
    print(f"Expected: TNR 700S (BluTouch gloves)")
    print(f"NOT: TN7000 (microtome - wrong product)\n")

    # Simulate middleware's retrieve_products() with FIXED parameters
    search_params = {
        "q": query,
        "query_by": "name,sku,name_normalized,sku_normalized,description,short_description,categories",
        "query_by_weights": "100,100,4,4,3,3,1",  # NEW: Added normalized fields with correct weighting
        "per_page": 20,
        "prefix": "true,true,true,true,false,false,false",
        "num_typos": 2,
        "typo_tokens_threshold": 1,
        "drop_tokens_threshold": 2,
        "sort_by": "_text_match:desc",
        "nl_query": False
    }

    print("Search parameters:")
    print(f"  query_by: {search_params['query_by']}")
    print(f"  query_by_weights: {search_params['query_by_weights']}")
    print()

    # Execute search
    result = client.collections[collection].documents.search(search_params)
    found = result.get('found', 0)

    print(f"Results found: {found}")
    print()

    # Check top results
    success = False
    for i, hit in enumerate(result.get('hits', [])[:5], 1):
        doc = hit['document']
        sku = doc.get('sku', '')
        name = doc.get('name', '')
        categories = doc.get('categories', [])

        print(f"{i}. SKU: {sku}")
        print(f"   Name: {name[:70]}")
        print(f"   Categories: {', '.join(categories[:2])}")

        # Check if this is the CORRECT product (TNR 700S gloves)
        if sku == "TNR 700S" and i == 1:
            print(f"   ✅ CORRECT - Found TNR 700S as top result!")
            success = True
        elif sku == "TNR TN7000" and i == 1:
            print(f"   ❌ WRONG - TN7000 microtome is top result (should be TNR 700S)")
        print()

    # Summary
    print("=" * 70)
    if success:
        print("✅ TEST PASSED - Middleware will now find correct products!")
        print("   'tnr700s' → TNR 700S (gloves) ✓")
    else:
        print("❌ TEST FAILED - Fix didn't work as expected")
        if found > 0:
            print("   Check if TNR 700S product exists in the collection")
    print("=" * 70)

    return success

if __name__ == "__main__":
    success = test_middleware_retrieval()
    sys.exit(0 if success else 1)
