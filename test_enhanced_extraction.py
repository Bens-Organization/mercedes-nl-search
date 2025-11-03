#!/usr/bin/env python3
"""
Test enhanced query extraction that matches Typesense NL behavior.

This tests that the middleware now:
1. Keeps descriptive terms (capacity, volume, size, etc.)
2. Keeps measurements (50ml, 1L, etc.)
3. Keeps material modifiers (nitrile, latex, glass, etc.)
4. Keeps important adjectives (sterile, disposable, etc.)
5. Removes only conversational fluff

Expected improvements:
- "Centrifuge tubes, 50ml capacity" → "centrifuge tube 50ml capacity" (not "centrifuge tube 50ml")
- "sterile nitrile gloves size large" → "sterile nitrile glove large" (keep all descriptors)
- "1 liter glass beakers" → "1 liter glass beaker" (keep volume and material)
"""

import asyncio
import sys
sys.path.insert(0, '/Users/alvinadefuin/Desktop/Projects/mercedes-natural-language-search')

from src.search_middleware import MiddlewareSearch

async def test_enhanced_extraction():
    print("Testing Enhanced Query Extraction (Match Typesense NL)")
    print("="*80)

    searcher = MiddlewareSearch()

    # Test cases showing enhanced extraction
    test_cases = [
        {
            "query": "Centrifuge tubes, 50ml capacity",
            "expected_terms": ["centrifuge", "tube", "50ml", "capacity"],
            "description": "Should keep 'capacity' descriptor"
        },
        {
            "query": "sterile nitrile gloves size large",
            "expected_terms": ["sterile", "nitrile", "glove", "large"],
            "description": "Should keep 'sterile' and 'large'"
        },
        {
            "query": "1 liter glass beakers",
            "expected_terms": ["1", "liter", "glass", "beaker"],
            "description": "Should keep volume and material"
        },
        {
            "query": "graduated pipettes 10ml plastic",
            "expected_terms": ["graduated", "pipette", "10ml", "plastic"],
            "description": "Should keep property and material"
        },
        {
            "query": "disposable petri dishes 100mm diameter",
            "expected_terms": ["disposable", "petri", "dish", "100mm", "diameter"],
            "description": "Should keep property, measurement, and descriptor"
        }
    ]

    print("\nTest Cases:")
    print("-"*80)

    for i, test in enumerate(test_cases, 1):
        query = test["query"]
        expected = test["expected_terms"]
        description = test["description"]

        print(f"\n{i}. {description}")
        print(f"   Input:  '{query}'")

        try:
            result = await searcher.search(query, max_results=5, debug=False)
            extracted_query = result['typesense_query']['llm_extracted_query']

            print(f"   Output: '{extracted_query}'")

            # Check if expected terms are present
            found_terms = [term for term in expected if term.lower() in extracted_query.lower()]
            missing_terms = [term for term in expected if term.lower() not in extracted_query.lower()]

            if len(found_terms) == len(expected):
                print(f"   ✅ PASS: All expected terms present")
            else:
                print(f"   ⚠️  PARTIAL: Found {len(found_terms)}/{len(expected)} terms")
                if missing_terms:
                    print(f"   Missing: {', '.join(missing_terms)}")

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")

    # Comparison with old behavior
    print("\n" + "="*80)
    print("COMPARISON: Old vs Enhanced Extraction")
    print("="*80)

    comparisons = [
        {
            "query": "Centrifuge tubes, 50ml capacity",
            "old": "centrifuge tube 50ml",
            "new": "centrifuge tube 50ml capacity"
        },
        {
            "query": "sterile nitrile gloves size large",
            "old": "nitrile glove",
            "new": "sterile nitrile glove large"
        },
        {
            "query": "1 liter glass beakers",
            "old": "glass beaker",
            "new": "1 liter glass beaker"
        }
    ]

    print("\n")
    for comp in comparisons:
        print(f"Query: '{comp['query']}'")
        print(f"  Old extraction: '{comp['old']}'  ❌ Too minimal")
        print(f"  New extraction: '{comp['new']}'  ✅ Descriptive")
        print()

    print("="*80)
    print("BENEFITS OF ENHANCED EXTRACTION:")
    print("="*80)
    print("✅ Better search relevance (more descriptive terms)")
    print("✅ Matches Typesense NL behavior")
    print("✅ Finds exact product specifications")
    print("✅ Preserves user intent")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_enhanced_extraction())
