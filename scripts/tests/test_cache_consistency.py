#!/usr/bin/env python3
"""
Test script to verify cache consistency fix (JAI-2202).

This script:
1. Clears the cache
2. Makes first request (CACHE MISS)
3. Makes second request (CACHE HIT)
4. Compares results to ensure consistency

Expected: Both requests should return identical results (same total, same filter_by)
"""

import requests
import json
import sys
import time

# Configuration
API_URL = "http://localhost:5001/api/search"

# Test queries that trigger partial match logic
TEST_QUERIES = [
    "alcohol",      # Should match: Alcohol, Isopropyl Alcohol, Ethyl Alcohol, Acid Alcohol
    "gloves",       # Should match: Nitrile Gloves, Latex Gloves, Vinyl Gloves
    "stains",       # Should match: Gram Stains, Eosin Stains, H&E Stains
]

def clear_cache():
    """Clear Redis cache before testing"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.flushdb()
        print("✅ Cache cleared")
        return True
    except Exception as e:
        print(f"⚠️  Could not clear cache: {e}")
        print("   Continuing anyway - results may be from previous cache")
        return False

def search(query):
    """Make search request and return response"""
    response = requests.post(
        API_URL,
        json={"query": query},
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

    return response.json()

def compare_results(query, first_result, second_result):
    """Compare two search results for consistency"""
    print(f"\n{'='*80}")
    print(f"Testing query: '{query}'")
    print(f"{'='*80}")

    # Extract key metrics
    first_total = first_result.get('total', 0)
    second_total = second_result.get('total', 0)

    first_filter = first_result.get('typesense_query', {}).get('filters_applied', '')
    second_filter = second_result.get('typesense_query', {}).get('filters_applied', '')

    first_query = first_result.get('typesense_query', {}).get('extracted_query', '')
    second_query = second_result.get('typesense_query', {}).get('extracted_query', '')

    # Print results
    print(f"\n1️⃣  FIRST REQUEST (CACHE MISS):")
    print(f"   Total: {first_total}")
    print(f"   Query: {first_query}")
    print(f"   Filter: {first_filter}")

    print(f"\n2️⃣  SECOND REQUEST (CACHE HIT):")
    print(f"   Total: {second_total}")
    print(f"   Query: {second_query}")
    print(f"   Filter: {second_filter}")

    # Compare
    success = True

    if first_total != second_total:
        print(f"\n❌ FAILED: Total mismatch ({first_total} vs {second_total})")
        success = False
    else:
        print(f"\n✅ Total matches: {first_total} products")

    if first_filter != second_filter:
        print(f"❌ FAILED: Filter mismatch")
        print(f"   MISS: {first_filter}")
        print(f"   HIT:  {second_filter}")
        success = False
    else:
        print(f"✅ Filter matches: {first_filter}")

    if first_query != second_query:
        print(f"❌ FAILED: Query mismatch")
        print(f"   MISS: {first_query}")
        print(f"   HIT:  {second_query}")
        success = False
    else:
        print(f"✅ Query matches: {first_query}")

    return success

def main():
    print("=" * 80)
    print("Cache Consistency Test (JAI-2202)")
    print("=" * 80)

    # Clear cache
    print("\n🔄 Clearing cache...")
    clear_cache()

    # Test each query
    all_passed = True
    results_summary = []

    for query in TEST_QUERIES:
        print(f"\n\n{'='*80}")
        print(f"Testing: '{query}'")
        print(f"{'='*80}")

        # First request (CACHE MISS)
        print("\n📤 Making first request (CACHE MISS)...")
        first_result = search(query)
        if not first_result:
            print(f"❌ First request failed for '{query}'")
            all_passed = False
            results_summary.append((query, False, "First request failed"))
            continue

        # Wait a bit to ensure cache is written
        time.sleep(0.5)

        # Second request (CACHE HIT)
        print("📤 Making second request (CACHE HIT)...")
        second_result = search(query)
        if not second_result:
            print(f"❌ Second request failed for '{query}'")
            all_passed = False
            results_summary.append((query, False, "Second request failed"))
            continue

        # Compare
        success = compare_results(query, first_result, second_result)

        if success:
            results_summary.append((query, True, f"{first_result.get('total', 0)} products"))
        else:
            all_passed = False
            results_summary.append((query, False, "Results mismatch"))

    # Final summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    for query, passed, details in results_summary:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - '{query}': {details}")

    print(f"\n{'='*80}")
    if all_passed:
        print("✅ ALL TESTS PASSED - Cache consistency fixed!")
        print(f"{'='*80}\n")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Cache inconsistency still present")
        print(f"{'='*80}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
