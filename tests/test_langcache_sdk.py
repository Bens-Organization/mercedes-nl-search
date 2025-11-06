#!/usr/bin/env python3
"""
Test script for LangCache SDK integration
"""
import os
import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

async def test_langcache_sdk():
    """Test the LangCache SDK with proper configuration"""
    from src.cache_layer import get_cache

    print("="*60)
    print("Testing LangCache SDK Integration")
    print("="*60)

    # Get cache instance
    cache = get_cache()
    await cache.initialize()

    # Test cache configuration
    print(f"\nCache Mode: {cache.mode}")
    print(f"LangCache URL: {os.getenv('LANGCACHE_API_URL')}")
    print(f"LangCache Cache ID: {os.getenv('LANGCACHE_CACHE_ID')}")
    print(f"LangCache API Key: {os.getenv('LANGCACHE_API_KEY')[:20]}..." if os.getenv('LANGCACHE_API_KEY') else "Not set")

    # Test 1: Cache miss + set
    print("\n" + "="*60)
    print("Test 1: Cache MISS + SET")
    print("="*60)
    test_query = "What are nitrile gloves?"
    test_response = {
        "answer": "Nitrile gloves are synthetic rubber gloves commonly used in medical and laboratory settings.",
        "timestamp": "2025-01-06T12:00:00Z"
    }

    # Should be a miss
    print(f"\n1. Searching for: '{test_query}'")
    cached = await cache.get_cached_response(test_query)
    if cached:
        print(f"   ⚠️  Unexpected cache hit: {cached}")
    else:
        print("   ✅ Cache MISS (expected)")

    # Set the response
    print(f"\n2. Caching response...")
    await cache.cache_response(test_query, test_response)
    print("   ✅ Response cached")

    # Test 2: Cache hit
    print("\n" + "="*60)
    print("Test 2: Cache HIT (exact match)")
    print("="*60)
    print(f"\n1. Searching again for: '{test_query}'")
    cached = await cache.get_cached_response(test_query)
    if cached:
        print(f"   ✅ Cache HIT!")
        print(f"   Response: {cached}")
    else:
        print("   ❌ Cache MISS (unexpected)")

    # Test 3: Semantic matching
    print("\n" + "="*60)
    print("Test 3: Semantic Matching")
    print("="*60)
    similar_query = "What is a nitrile glove?"  # Slightly different wording
    print(f"\n1. Searching for similar query: '{similar_query}'")
    cached = await cache.get_cached_response(similar_query)
    if cached:
        print(f"   ✅ Semantic match found!")
        print(f"   Response: {cached}")
    else:
        print("   ⚠️  No semantic match (similarity threshold may be too high)")

    # Test 4: Different query (should miss)
    print("\n" + "="*60)
    print("Test 4: Different Query (should MISS)")
    print("="*60)
    different_query = "What are pipettes used for?"
    print(f"\n1. Searching for: '{different_query}'")
    cached = await cache.get_cached_response(different_query)
    if cached:
        print(f"   ⚠️  Unexpected cache hit: {cached}")
    else:
        print("   ✅ Cache MISS (expected - different topic)")

    # Show metrics
    print("\n" + "="*60)
    print("Cache Metrics")
    print("="*60)
    stats = cache.metrics.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Cleanup
    await cache.close()
    print("\n✅ Test completed!\n")

if __name__ == "__main__":
    asyncio.run(test_langcache_sdk())
