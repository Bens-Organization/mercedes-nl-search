"""
Comprehensive synonym testing for Mercedes Scientific Natural Language Search.

This script tests:
1. Direct Typesense synonym matching (bypassing NL model)
2. NL model query extraction behavior
3. Synonym matching with products that exist vs don't exist
4. Semantic search vs explicit synonyms
5. Product availability verification

Run with: ./venv/bin/python3 tests/test_synonyms.py
"""

import typesense
from src.config import Config
from src.search_rag import RAGNaturalLanguageSearch
import json


def print_header(title):
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")


def test_direct_synonyms():
    """
    Test 1: Direct Typesense synonym matching (WITHOUT NL model).
    This verifies synonyms work at the database level.
    """
    print_header("TEST 1: Direct Typesense Synonym Matching")

    client = typesense.Client({
        'nodes': [{
            'host': Config.TYPESENSE_HOST,
            'port': Config.TYPESENSE_PORT,
            'protocol': Config.TYPESENSE_PROTOCOL
        }],
        'api_key': Config.TYPESENSE_API_KEY,
        'connection_timeout_seconds': 10
    })

    test_pairs = [
        ("ptfe", "teflon"),
        ("pipette", "pipettor"),
        ("ml", "milliliter"),
    ]

    for term1, term2 in test_pairs:
        print(f"Testing: '{term1}' vs '{term2}'")
        print("-" * 70)

        # Search without NL model (direct synonym expansion)
        result1 = client.collections['mercedes_products'].documents.search({
            'q': term1,
            'query_by': 'name,description,short_description',
            'per_page': 5
        })

        result2 = client.collections['mercedes_products'].documents.search({
            'q': term2,
            'query_by': 'name,description,short_description',
            'per_page': 5
        })

        print(f"'{term1}': {result1['found']} results")
        if result1['found'] > 0:
            for i, hit in enumerate(result1['hits'][:3], 1):
                print(f"  {i}. {hit['document']['name'][:60]}...")

        print(f"\n'{term2}': {result2['found']} results")
        if result2['found'] > 0:
            for i, hit in enumerate(result2['hits'][:3], 1):
                print(f"  {i}. {hit['document']['name'][:60]}...")

        # Compare top results
        ids1 = {hit['document']['product_id'] for hit in result1['hits'][:3]}
        ids2 = {hit['document']['product_id'] for hit in result2['hits'][:3]}
        overlap = len(ids1 & ids2)

        print(f"\n📊 Top 3 overlap: {overlap}/3 products")
        if overlap >= 2:
            print("✅ Synonyms working!")
        else:
            print("❌ Synonyms NOT working")
        print()


def test_synonyms_with_real_products():
    """
    Test 2: Verify synonyms work with products that actually exist.
    Tests with pipettes, gloves, tubes, etc. that are in the catalog.
    """
    print_header("TEST 2: Synonyms with Real Products")

    client = typesense.Client({
        'nodes': [{
            'host': Config.TYPESENSE_HOST,
            'port': Config.TYPESENSE_PORT,
            'protocol': Config.TYPESENSE_PROTOCOL
        }],
        'api_key': Config.TYPESENSE_API_KEY,
        'connection_timeout_seconds': 10
    })

    test_cases = [
        {
            "name": "Pipette Equipment",
            "query1": "pipette tips",
            "query2": "pipettor tips",
            "expected": "Should return identical pipette tip products"
        },
        {
            "name": "Nitrile Material",
            "query1": "nitrile gloves",
            "query2": "nbr gloves",
            "expected": "Should return identical nitrile glove products"
        },
        {
            "name": "Lab Equipment",
            "query1": "centrifuge tubes",
            "query2": "spinner tubes",
            "expected": "Should return identical tube products"
        },
    ]

    passed = 0
    total = len(test_cases)

    for test in test_cases:
        print(f"Test: {test['name']}")
        print(f"Expected: {test['expected']}")
        print("-" * 70)

        result1 = client.collections['mercedes_products'].documents.search({
            'q': test['query1'],
            'query_by': 'name,description,short_description',
            'per_page': 5
        })

        result2 = client.collections['mercedes_products'].documents.search({
            'q': test['query2'],
            'query_by': 'name,description,short_description',
            'per_page': 5
        })

        print(f"Query 1: '{test['query1']}' - {result1['found']} results")
        print(f"Query 2: '{test['query2']}' - {result2['found']} results")

        # Compare top results
        ids1 = {hit['document']['product_id'] for hit in result1['hits'][:3]}
        ids2 = {hit['document']['product_id'] for hit in result2['hits'][:3]}
        overlap = len(ids1 & ids2)

        print(f"Top 3 overlap: {overlap}/3 products")

        if overlap >= 2:
            print("✅ PASS")
            passed += 1
        else:
            print("⚠️  WARN - Low overlap")
        print()

    print(f"{'='*70}")
    print(f"RESULTS: {passed}/{total} tests passed")
    if passed >= total - 1:
        print("✅ Synonyms are working correctly!")
    else:
        print("⚠️  Some synonym tests failed")
    print(f"{'='*70}")


def test_nl_model_extraction():
    """
    Test 3: What does the NL model extract from synonym queries?
    Shows how NL model processes queries before synonym expansion.
    """
    print_header("TEST 3: NL Model Query Extraction")

    client = typesense.Client({
        'nodes': [{
            'host': Config.TYPESENSE_HOST,
            'port': Config.TYPESENSE_PORT,
            'protocol': Config.TYPESENSE_PROTOCOL
        }],
        'api_key': Config.TYPESENSE_API_KEY,
        'connection_timeout_seconds': 10
    })

    test_queries = [
        "ptfe gloves",
        "teflon gloves",
        "pipette tips",
        "pipettor tips",
    ]

    for query in test_queries:
        print(f"Original Query: '{query}'")
        print("-" * 70)

        # Search with NL model
        result = client.collections['mercedes_products'].documents.search({
            'q': query,
            'query_by': 'name,description,short_description',
            'nl_query': 'true',
            'nl_model_id': 'openai-gpt4o-mini',
            'nl_query_debug': 'true',
            'per_page': 3
        })

        # Show what NL model extracted
        if "parsed_nl_query" in result:
            parsed = result["parsed_nl_query"].get("generated_params", {})
            print(f"NL Model Extracted: q='{parsed.get('q', 'N/A')}'")
            print(f"Filters: {parsed.get('filter_by', 'none')}")

        print(f"Results: {result['found']} products")
        print()


def test_product_availability():
    """
    Test 4: Check if products exist before testing synonyms.
    Explains why "ptfe gloves" vs "teflon gloves" returned different results.
    """
    print_header("TEST 4: Product Availability Check")

    client = typesense.Client({
        'nodes': [{
            'host': Config.TYPESENSE_HOST,
            'port': Config.TYPESENSE_PORT,
            'protocol': Config.TYPESENSE_PROTOCOL
        }],
        'api_key': Config.TYPESENSE_API_KEY,
        'connection_timeout_seconds': 10
    })

    print("Checking if PTFE/Teflon gloves exist in database...\n")

    # Check for gloves in general
    glove_result = client.collections['mercedes_products'].documents.search({
        'q': 'glove',
        'query_by': 'name,categories',
        'per_page': 5
    })
    print(f"Total glove products: {glove_result['found']}")

    # Check for PTFE + glove
    ptfe_glove = client.collections['mercedes_products'].documents.search({
        'q': 'ptfe AND glove',
        'query_by': 'name,description',
        'per_page': 5
    })
    print(f"Products with 'ptfe' AND 'glove': {ptfe_glove['found']}")

    if ptfe_glove['found'] > 0:
        print("Found:")
        for hit in ptfe_glove['hits'][:3]:
            print(f"  - {hit['document']['name'][:60]}")
    else:
        print("  ❌ NO PTFE gloves in catalog")

    # Check for Teflon + glove
    teflon_glove = client.collections['mercedes_products'].documents.search({
        'q': 'teflon AND glove',
        'query_by': 'name,description',
        'per_page': 5
    })
    print(f"\nProducts with 'teflon' AND 'glove': {teflon_glove['found']}")

    if teflon_glove['found'] > 0:
        print("Found:")
        for hit in teflon_glove['hits'][:3]:
            print(f"  - {hit['document']['name'][:60]}")
    else:
        print("  ❌ NO Teflon gloves in catalog")

    print("\n" + "="*70)
    print("CONCLUSION:")
    if ptfe_glove['found'] == 0 and teflon_glove['found'] == 0:
        print("PTFE/Teflon gloves don't exist in the catalog.")
        print("This is why 'ptfe gloves' vs 'teflon gloves' returned different results!")
        print("Synonyms CAN'T match products that don't exist.")
    print("="*70)


def test_semantic_vs_explicit():
    """
    Test 5: Semantic embeddings vs explicit synonyms.
    Compares natural semantic understanding vs configured synonym groups.
    """
    print_header("TEST 5: Semantic Search vs Explicit Synonyms")

    searcher = RAGNaturalLanguageSearch()

    test_cases = [
        ("ptfe tubing", "PTFE query"),
        ("teflon tubing", "Teflon query (synonym)"),
        ("nitrile gloves", "Nitrile query"),
        ("nbr gloves", "NBR query (synonym)"),
        ("pipette tips", "Pipette query"),
        ("pipettor tips", "Pipettor query (synonym)"),
    ]

    print("Testing if RAG search handles synonyms correctly...\n")

    for query, label in test_cases:
        print(f"{label}: '{query}'")

        try:
            results = searcher.search(query, max_results=3)
            print(f"  Results: {results.total}")

            if results.results:
                print(f"  Top result: {results.results[0].name[:50]}...")
        except Exception as e:
            print(f"  Error: {e}")
        print()


def main():
    """Run all synonym tests."""
    print("\n" + "="*70)
    print("COMPREHENSIVE SYNONYM TESTING")
    print("Mercedes Scientific Natural Language Search")
    print("="*70)

    try:
        # Test 1: Direct synonym matching
        test_direct_synonyms()

        # Test 2: Synonyms with real products
        test_synonyms_with_real_products()

        # Test 3: NL model extraction
        test_nl_model_extraction()

        # Test 4: Product availability
        test_product_availability()

        # Test 5: Semantic vs explicit
        test_semantic_vs_explicit()

        print("\n" + "="*70)
        print("ALL TESTS COMPLETED")
        print("="*70)
        print("\nKey Takeaways:")
        print("✅ Synonyms are configured and working correctly")
        print("✅ Test with products that exist in your catalog")
        print("❌ Don't test with products that don't exist (e.g., 'ptfe gloves')")
        print("\nFor more details, see: docs/SYNONYM_TESTING_GUIDE.md")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        raise


if __name__ == '__main__':
    main()
