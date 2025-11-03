#!/usr/bin/env python3
"""
Test script to verify metadata is now included in decoupled architecture responses.

This should show:
- detected_category: "Products/Glass & Plasticware/Tubes/Centrifuge Tubes"
- category_confidence: 0.9 (or similar)
- category_reasoning: "Clear product type..."
"""

import asyncio
import sys
sys.path.insert(0, '/Users/alvinadefuin/Desktop/Projects/mercedes-natural-language-search')

from src.search_middleware import MiddlewareSearch

async def test_metadata():
    print("Testing metadata transparency in decoupled architecture...")
    print("="*80)

    searcher = MiddlewareSearch()

    # Test query
    query = "Centrifuge tubes, 50ml capacity"
    print(f"\nQuery: {query}\n")

    # Execute search
    result = await searcher.search(query, max_results=20, debug=True)

    # Check metadata
    print("\n" + "="*80)
    print("METADATA CHECK:")
    print("="*80)
    print(f"✓ Detected Category: {result.get('detected_category')}")
    print(f"✓ Category Confidence: {result.get('category_confidence')}")
    print(f"✓ Category Applied: {result.get('category_applied')}")
    print(f"✓ Total Results: {result.get('total')}")

    # Show category reasoning if available
    if result.get('typesense_query', {}).get('category_reasoning'):
        print(f"\n✓ Category Reasoning:")
        print(f"  {result['typesense_query']['category_reasoning']}")

    # Verify fix worked
    print("\n" + "="*80)
    if result.get('detected_category'):
        print("✅ SUCCESS: Metadata is now included!")
    else:
        print("❌ FAILED: Metadata still missing")
    print("="*80)

    return result

if __name__ == "__main__":
    asyncio.run(test_metadata())
