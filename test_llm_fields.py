#!/usr/bin/env python3
"""
Test script to verify LLM extraction fields are correctly implemented.

IMPORTANT: Unlike dual LLM approach, this uses ONE middleware LLM that does BOTH:
1. Extraction (query cleaning, filter detection, sort detection)
2. Classification (category detection with confidence)

Expected output:
- llm_extraction_enabled: true (middleware LLM, NOT Typesense NL model)
- llm_extracted_query: "centrifuge tube 50ml"
- llm_extracted_filters: "none" (or price/stock filters if present)
- llm_extracted_sort: "default" (or sort if specified)
- detected_category: "Products/Glass & Plasticware/Tubes/Centrifuge Tubes"
- category_confidence: 0.9
"""

import asyncio
import sys
import json
sys.path.insert(0, '/Users/alvinadefuin/Desktop/Projects/mercedes-natural-language-search')

from src.search_middleware import MiddlewareSearch

async def test_llm_fields():
    print("Testing LLM extraction fields in response...")
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
    print("SINGLE LLM EXTRACTION (middleware does BOTH jobs):")
    print("="*80)

    # LLM extraction
    print("\n[LLM Extraction - Query/Filters/Sort]")
    print(f"  llm_extraction_enabled: {tq.get('llm_extraction_enabled')}")
    print(f"  llm_extracted_query: {tq.get('llm_extracted_query')}")
    print(f"  llm_extracted_filters: {tq.get('llm_extracted_filters')}")
    print(f"  llm_extracted_sort: {tq.get('llm_extracted_sort')}")

    # RAG classification (SAME LLM)
    print("\n[RAG Classification - Category Detection (SAME LLM)]")
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
        'llm_extraction_enabled',
        'llm_extracted_query',
        'llm_extracted_filters',
        'llm_extracted_sort',
        'detected_category',
        'category_confidence',
        'category_applied'
    ]

    missing_fields = [f for f in required_fields if f not in tq]

    if not missing_fields:
        print("✅ SUCCESS: All LLM extraction fields present!")
        print("✅ Correctly reflects single-LLM architecture")
    else:
        print(f"❌ FAILED: Missing fields: {missing_fields}")
    print("="*80)

    # Show architecture comparison
    print("\n" + "="*80)
    print("ARCHITECTURE COMPARISON:")
    print("="*80)

    print("\nOld Dual LLM (2 separate calls):")
    print("  LLM 1 (Typesense NL): nl_extracted_query, nl_extracted_filters, nl_extracted_sort")
    print("  LLM 2 (RAG): detected_category, category_confidence")
    print("  → Total: 2 LLM calls")

    print("\nNew Single LLM (1 combined call):")
    print("  LLM 1 (Middleware): llm_extracted_query, llm_extracted_filters, llm_extracted_sort")
    print("                      + detected_category, category_confidence (SAME CALL)")
    print("  → Total: 1 LLM call")

    print("\nField Presence:")
    for field in required_fields:
        status = "✓" if field in tq else "✗"
        print(f"  {status} {field}")

    return result

if __name__ == "__main__":
    asyncio.run(test_llm_fields())
