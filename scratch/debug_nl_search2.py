#!/usr/bin/env python3
"""Debug - print parsed_nl_query"""

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

search_params = {
    "q": query,
    "query_by": "name,description,short_description,sku,categories",
    "nl_query": True,
    "nl_model_id": "custom-rag-middleware-v2",
    "per_page": 3
}

print(f"Query: '{query}'")
print("=" * 80)

result = client.collections['mercedes_products'].documents.search(search_params)

# Print parsed_nl_query
if 'parsed_nl_query' in result:
    print("\nparsed_nl_query:")
    print(json.dumps(result['parsed_nl_query'], indent=2))
else:
    print("\nNo parsed_nl_query in response!")

print(f"\nFound: {result.get('found', 0)} results")

# Print full response structure
print("\nFull response keys:")
for key in result.keys():
    print(f"  - {key}")
