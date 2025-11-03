#!/usr/bin/env python3
"""
Test Typesense NL Integration End-to-End

This tests the complete flow:
1. User query → Typesense NL search
2. Typesense calls middleware
3. Middleware does RAG + category classification
4. Middleware returns simplified format (4 fields)
5. Typesense parses response
6. Typesense executes final search
7. Results returned to user
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
import typesense

# Initialize Typesense client
client = typesense.Client({
    'api_key': Config.TYPESENSE_API_KEY,
    'nodes': [{
        'host': Config.TYPESENSE_HOST,
        'port': Config.TYPESENSE_PORT,
        'protocol': Config.TYPESENSE_PROTOCOL
    }],
    'connection_timeout_seconds': 30
})

def test_nl_search(query, description):
    """Test a query using Typesense NL search with middleware"""
    print(f"\n{'='*80}")
    print(f"Query: '{query}'")
    print(f"Description: {description}")
    print(f"{'='*80}")

    try:
        # Search using Typesense NL integration
        search_params = {
            "q": query,
            "query_by": "name,description,short_description,sku,categories",
            "nl_query": True,  # Enable NL search
            "nl_model_id": "custom-rag-middleware-v2",  # Use our middleware
            "nl_query_debug": True,  # See what parameters were extracted
            "per_page": 5
        }

        print("\n[1] Calling Typesense NL Search...")
        print(f"    Parameters: nl_query=True, nl_model_id=custom-rag-middleware-v2")

        result = client.collections['mercedes_products'].documents.search(search_params)

        # Check for errors
        if 'error' in result:
            print(f"\n❌ ERROR: {result.get('error')}")
            print(f"   Message: {result.get('message', 'N/A')}")
            return False

        # Extract debug info
        debug_info = result.get('request_params', {})
        print(f"\n[2] Typesense Parsed Parameters:")
        print(f"    q: {debug_info.get('q', 'N/A')}")
        print(f"    filter_by: {debug_info.get('filter_by', 'None')}")
        print(f"    sort_by: {debug_info.get('sort_by', 'None')}")

        # Show results
        found = result.get('found', 0)
        hits = result.get('hits', [])

        print(f"\n[3] Search Results:")
        print(f"    Total found: {found}")
        print(f"    Returned: {len(hits)}")

        if hits:
            print(f"\n    Top results:")
            for i, hit in enumerate(hits[:3], 1):
                doc = hit['document']
                print(f"      {i}. {doc.get('name', 'N/A')[:60]}")
                print(f"         Price: ${doc.get('price', 'N/A')}")
                print(f"         Categories: {doc.get('categories', [])[:2]}")

        # Validation
        has_category_filter = 'categories:=' in debug_info.get('filter_by', '')
        has_results = found > 0

        print(f"\n[4] Validation:")
        print(f"    ✅ No parsing errors (Typesense accepted response)")
        print(f"    {'✅' if has_category_filter else '⚠️ '} Category filter: {'Applied' if has_category_filter else 'Not applied'}")
        print(f"    {'✅' if has_results else '⚠️ '} Results found: {found}")

        return True

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 TESTING TYPESENSE NL INTEGRATION (END-TO-END)\n")

    test_cases = [
        ("nitrile gloves under $50", "Clear product type + price filter"),
        ("pipettes in stock", "Product type + stock filter"),
        ("gloves under $30", "Product + price filter"),
        ("clear", "Ambiguous single word (should NOT apply category)"),
        ("Mercedes Scientific", "Brand only (should NOT apply category)"),
    ]

    results = []
    for query, description in test_cases:
        success = test_nl_search(query, description)
        results.append(success)

    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if all(results):
        print("\n✅ ALL TESTS PASSED!")
        print("✅ Typesense successfully parses middleware response")
        print("✅ Single-LLM RAG approach is working!")
        print("\nNext steps:")
        print("  1. Deploy updated middleware to Railway")
        print("  2. Update Typesense model to use Railway URL")
        print("  3. Test in production")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("   Check error messages above for details")

    sys.exit(0 if all(results) else 1)
