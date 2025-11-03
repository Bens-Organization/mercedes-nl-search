#!/bin/bash
# Test Typesense REST API with NL query

curl -s -G "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/collections/mercedes_products/documents/search" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz" \
  --data-urlencode "q=gloves under 50 dollars" \
  --data-urlencode "query_by=name,sku,description" \
  --data-urlencode "per_page=3" \
  --data-urlencode "nl_query=true" \
  --data-urlencode "nl_model_id=middleware-rag-vllm"
