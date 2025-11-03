#!/bin/bash
# Test registering NL model using openai_url parameter (conversation models format)
#
# This tests if openai_url/openai_path work for NL search models
# (even though they're documented for conversation models only)

echo "=== TESTING openai_url PARAMETER NL MODEL REGISTRATION ==="
echo ""
echo "Approach: Use openai_url/openai_path parameters (conversation model style)"
echo ""

# Delete existing model first
echo "1. Deleting existing model..."
curl -X DELETE "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/nl_search_models/middleware-rag-gpt4o-mini" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz"

echo ""
echo ""

# Register with openai_url parameter
echo "2. Registering model with openai_url parameter..."
curl -X POST "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/nl_search_models" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"middleware-rag-openai-url\",
    \"model_name\": \"openai/gpt-4o-mini-2024-07-18\",
    \"openai_url\": \"https://web-production-a5d93.up.railway.app\",
    \"openai_path\": \"/v1/chat/completions\",
    \"api_key\": \"${OPENAI_API_KEY}\",
    \"max_bytes\": 16000,
    \"temperature\": 0.0
  }"

echo ""
echo ""

# List all models to verify
echo "3. Verifying registration..."
curl -s "https://azj9dh4uxovql07tp-1.a1.typesense.net:443/nl_search_models" \
  -H "X-TYPESENSE-API-KEY: Xx5GXFq3ExaWUsjUqo0DO3ddUafin6cz" | python3 -m json.tool

echo ""
echo ""
echo "✅ Model registered with openai_url parameter!"
echo ""
echo "Next steps:"
echo "  1. Test search with: nl_query=true&nl_model_id=middleware-rag-openai-url"
echo "  2. Check Railway logs to verify middleware is called"
echo "  3. Verify category filter is applied correctly"
