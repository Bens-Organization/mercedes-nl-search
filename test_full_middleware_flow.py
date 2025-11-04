#!/usr/bin/env python3
"""Test full middleware flow with the model number search fix."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
import json
from src.openai_middleware import retrieve_products, build_enriched_prompt, call_openai, apply_category_filter

async def test_full_flow():
    """Test the complete middleware flow for 'tnr700s' query."""
    print("=" * 70)
    print("FULL MIDDLEWARE FLOW TEST - MODEL NUMBER SEARCH FIX")
    print("=" * 70)

    query = "tnr700s"
    print(f"\nQuery: '{query}'")
    print(f"Expected:")
    print(f"  - Retrieval: TNR 700S (gloves)")
    print(f"  - Category: Products/Gloves & Apparel/Gloves")
    print(f"  - NOT: TN7000 (microtome)\n")

    # Step 1: Retrieve products (using fixed search parameters)
    print("Step 1: Retrieving products...")
    products = await retrieve_products(query, limit=20)
    print(f"  Retrieved: {len(products)} products")

    if products:
        print(f"\n  Top 3 products:")
        for i, p in enumerate(products[:3], 1):
            print(f"    {i}. {p['name'][:60]} | SKU: {p['sku']}")
            print(f"       Categories: {', '.join(p.get('categories', [])[:2])}")

        # Check if TNR 700S is in top results
        top_skus = [p['sku'] for p in products[:3]]
        if "TNR 700S" in top_skus:
            print(f"\n  ✅ TNR 700S found in top results!")
        else:
            print(f"\n  ❌ TNR 700S NOT in top results")
            print(f"  Top SKUs: {top_skus}")

    # Step 2: Build enriched prompt
    print(f"\nStep 2: Building enriched prompt with RAG context...")
    system_prompt = "Extract search parameters from natural language queries for medical/scientific products."
    enriched_messages = build_enriched_prompt(query, products, system_prompt)
    print(f"  Messages: {len(enriched_messages)}")

    # Step 3: Call OpenAI (this will do category classification)
    print(f"\nStep 3: Calling OpenAI for category classification...")
    openai_response = await call_openai(enriched_messages, model="gpt-4o-mini")

    # Step 4: Apply category filter
    print(f"\nStep 4: Applying category filter...")
    final_response = apply_category_filter(openai_response, for_typesense_nl=True)

    # Parse the final parameters
    final_params = json.loads(final_response["choices"][0]["message"]["content"])

    print(f"\n{'='*70}")
    print("FINAL MIDDLEWARE OUTPUT:")
    print(f"{'='*70}")
    print(json.dumps(final_params, indent=2))

    # Verify results
    print(f"\n{'='*70}")
    print("VERIFICATION:")
    print(f"{'='*70}")

    query_correct = final_params.get("q") == "tnr700s" or "700" in final_params.get("q", "")
    category_correct = "Gloves" in final_params.get("filter_by", "")

    print(f"✓ Extracted query: {final_params.get('q')}")
    print(f"✓ Filter applied: {final_params.get('filter_by', 'none')}")

    if query_correct and category_correct:
        print(f"\n✅ SUCCESS - Middleware will correctly find TNR 700S gloves!")
        return True
    else:
        print(f"\n❌ ISSUE - Check the output above")
        if not query_correct:
            print(f"  - Query extraction might be off")
        if not category_correct:
            print(f"  - Category classification incorrect")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_flow())
    sys.exit(0 if success else 1)
