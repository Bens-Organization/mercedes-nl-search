#!/bin/bash
# Test registering NL model using vLLM format (supports custom endpoints)
#
# vLLM format uses api_url parameter for custom endpoints
# This should allow Typesense to call our Railway middleware

echo "=== TESTING vLLM FORMAT NL MODEL REGISTRATION ==="
echo ""
echo "Approach: Use vllm/ provider instead of openai/ to enable custom endpoint"
echo ""

# Delete existing model first
echo "1. Deleting existing openai/ model..."
curl -X DELETE "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/nl_search_models/middleware-rag-gpt4o-mini" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz"

echo ""
echo ""

# Register with vLLM format
echo "2. Registering model with vLLM format..."
curl -X POST "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/nl_search_models" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "middleware-rag-vllm",
    "model_name": "vllm/gpt-4o-mini",
    "api_url": "https://web-production-a5d93.up.railway.app/v1/chat/completions",
    "api_key": "dummy-key-not-used",
    "max_bytes": 16000,
    "temperature": 0.0
  }'

echo ""
echo ""

# List all models to verify
echo "3. Verifying registration..."
curl -s "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/nl_search_models" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz" | python3 -m json.tool

echo ""
echo ""
echo "✅ Model registered with vLLM format!"
echo ""
echo "Next steps:"
echo "  1. Test search with: nl_query=true&nl_model_id=middleware-rag-vllm"
echo "  2. Check Railway logs to verify middleware is called"
echo "  3. Verify category filter is applied correctly"
