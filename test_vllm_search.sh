#!/bin/bash
# Test search with new vLLM model

echo "Testing search with vLLM model..."
echo ""

curl -s "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/collections/mercedes_products/documents/search" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz" \
  -G \
  --data-urlencode "q=nitrile gloves under 50 dollars" \
  --data-urlencode "nl_query=true" \
  --data-urlencode "nl_model_id=middleware-rag-vllm" \
  --data-urlencode "query_by=name,description,sku" \
  --data-urlencode "per_page=5" > /tmp/vllm_test_response.json

echo "Response saved to /tmp/vllm_test_response.json"
echo ""

# Parse and display results
python3 << 'EOF'
import json

with open('/tmp/vllm_test_response.json', 'r') as f:
    data = json.load(f)

print(f"Found: {data['found']} results")
print(f"Query time: {data.get('search_time_ms', 0)}ms")
print()

if 'parsed_nl_query' in data:
    print('✅ NL Query was parsed!')
    parsed = data['parsed_nl_query']
    print(f"Parse time: {parsed.get('parse_time_ms', 0)}ms")
    gen_params = parsed.get('generated_params', {})
    print(f"Generated query (q): {gen_params.get('q', 'N/A')}")
    print(f"Generated filter: {gen_params.get('filter_by', 'N/A')}")

    aug_params = parsed.get('augmented_params', {})
    if aug_params:
        print(f"\nAugmented filter (final): {aug_params.get('filter_by', 'N/A')}")
else:
    print('❌ NL Query was NOT parsed')

print()
print('Top 3 results:')
for i, hit in enumerate(data.get('hits', [])[:3], 1):
    doc = hit['document']
    print(f"{i}. {doc['name'][:70]}")
    print(f"   Price: ${doc.get('price', 0):.2f}")
    cats = doc.get('categories', [])
    print(f"   Categories: {', '.join(cats[:2])}")
    print()
EOF
