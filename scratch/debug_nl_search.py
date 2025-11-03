#!/usr/bin/env python3
"""Debug Typesense NL search to see what's actually happening"""

import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
import typesense

client = typesense.Client({
    'api_key': Config.TYPESENSE_API_KEY,
    'nodes': [{
        'host': Config.TYPESENSE_HOST,
        'port': Config.TYPESENSE_PORT,
        'protocol': Config.TYPESENSE_PROTOCOL
    }],
    'connection_timeout_seconds': 30
})

query = "nitrile gloves under $50"

print(f"Query: '{query}'")
print("=" * 80)

# Test WITH nl_query
print("\n[TEST 1] WITH nl_query=True and nl_model_id")
search_params = {
    "q": query,
    "query_by": "name,description,short_description,sku,categories",
    "nl_query": True,
    "nl_model_id": "custom-rag-middleware-v2",
    "nl_query_debug": True,
    "per_page": 3
}

print(f"Request params: {json.dumps(search_params, indent=2)}")

result = client.collections['mercedes_products'].documents.search(search_params)

print(f"\nResponse keys: {result.keys()}")
print(f"Found: {result.get('found', 0)}")

# Check if there's error
if 'error' in result:
    print(f"ERROR: {result['error']}")

# Check request_params (what Typesense actually used)
if 'request_params' in result:
    print(f"\nRequest params used by Typesense:")
    print(json.dumps(result['request_params'], indent=2))

# Check for nl_query_debug info
if 'nl_query_debug' in result:
    print(f"\nNL Query Debug:")
    print(json.dumps(result['nl_query_debug'], indent=2))

# Show a result
if result.get('hits'):
    hit = result['hits'][0]
    doc = hit['document']
    print(f"\nFirst result:")
    print(f"  Name: {doc.get('name', 'N/A')[:60]}")
    print(f"  Price: ${doc.get('price', 'N/A')}")
    print(f"  Categories: {doc.get('categories', [])[:2]}")

# Test WITHOUT nl_query (normal search)
print("\n\n" + "=" * 80)
print("[TEST 2] WITHOUT nl_query (normal search)")
search_params_no_nl = {
    "q": query,
    "query_by": "name,description,short_description,sku,categories",
    "per_page": 3
}

result_no_nl = client.collections['mercedes_products'].documents.search(search_params_no_nl)
print(f"Found: {result_no_nl.get('found', 0)}")

if result_no_nl.get('hits'):
    hit = result_no_nl['hits'][0]
    doc = hit['document']
    print(f"\nFirst result:")
    print(f"  Name: {doc.get('name', 'N/A')[:60]}")
    print(f"  Price: ${doc.get('price', 'N/A')}")

print("\n" + "=" * 80)
print("COMPARISON:")
print(f"  WITH nl_query: {result.get('found', 0)} results")
print(f"  WITHOUT nl_query: {result_no_nl.get('found', 0)} results")

if result.get('found') == result_no_nl.get('found'):
    print(f"  ⚠️  SAME number of results - NL query might not be working!")
else:
    print(f"  ✅ Different results - NL query is modifying the search")
