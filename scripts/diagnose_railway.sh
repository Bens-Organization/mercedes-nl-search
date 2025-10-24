#!/bin/bash

# Diagnose Railway Middleware Deployment Issues

set -e

RAILWAY_URL="https://web-production-a5d93.up.railway.app"

echo "======================================================"
echo "Railway Middleware Diagnostics"
echo "======================================================"
echo ""
echo "Middleware URL: $RAILWAY_URL"
echo ""

# Test 1: Health endpoint
echo "Test 1: Health Endpoint"
echo "----------------------------------------"
echo "Checking if middleware is responding..."
echo ""

if curl -s --max-time 5 "$RAILWAY_URL/health" > /dev/null 2>&1; then
    echo "✅ Middleware is responding!"
    echo ""
    echo "Health response:"
    curl -s "$RAILWAY_URL/health" | python3 -m json.tool 2>/dev/null || echo "Invalid JSON response"
    echo ""
else
    echo "❌ Middleware is NOT responding"
    echo ""
    echo "Possible causes:"
    echo "  1. Middleware is still starting up (wait 1-2 minutes)"
    echo "  2. Deployment failed (check Railway logs)"
    echo "  3. Port binding issue (check Railway logs)"
    echo "  4. Missing environment variables"
    echo ""
    echo "Next steps:"
    echo "  - Check Railway logs in dashboard"
    echo "  - Or run: railway logs (if CLI is set up)"
    echo ""
    exit 1
fi

# Test 2: Root endpoint
echo "Test 2: Root Endpoint"
echo "----------------------------------------"
echo "Checking service info..."
echo ""

curl -s "$RAILWAY_URL/" | python3 -m json.tool 2>/dev/null || echo "Invalid JSON response"
echo ""

# Test 3: Stats endpoint
echo "Test 3: Stats Endpoint (Typesense connection)"
echo "----------------------------------------"
echo "Checking if middleware can connect to Typesense..."
echo ""

STATS=$(curl -s "$RAILWAY_URL/stats" 2>/dev/null)
if echo "$STATS" | python3 -m json.tool > /dev/null 2>&1; then
    echo "✅ Middleware can connect to Typesense!"
    echo ""
    echo "$STATS" | python3 -m json.tool
    echo ""
else
    echo "❌ Middleware cannot connect to Typesense"
    echo ""
    echo "Response:"
    echo "$STATS"
    echo ""
    echo "Possible causes:"
    echo "  - Missing TYPESENSE_* environment variables"
    echo "  - Invalid Typesense API key"
    echo "  - Typesense host unreachable"
    echo ""
    exit 1
fi

# Test 4: OpenAI compatibility endpoint
echo "Test 4: OpenAI-Compatible Endpoint"
echo "----------------------------------------"
echo "Testing /v1/chat/completions endpoint..."
echo ""

CHAT_RESPONSE=$(curl -s -X POST "$RAILWAY_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer test" \
    -d '{
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a search parser."},
            {"role": "user", "content": "test query"}
        ]
    }' 2>/dev/null)

if echo "$CHAT_RESPONSE" | python3 -c "import sys, json; json.load(sys.stdin)" > /dev/null 2>&1; then
    echo "✅ Chat completions endpoint is working!"
    echo ""
    echo "Sample response (truncated):"
    echo "$CHAT_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps({'id': d.get('id'), 'model': d.get('model'), 'has_choices': len(d.get('choices', [])) > 0}, indent=2))"
    echo ""
else
    echo "❌ Chat completions endpoint failed"
    echo ""
    echo "Response:"
    echo "$CHAT_RESPONSE"
    echo ""
fi

# Summary
echo "======================================================"
echo "Summary"
echo "======================================================"
echo ""
echo "If all tests passed:"
echo "  ✅ Middleware is healthy and ready"
echo "  ✅ Retry Typesense registration:"
echo "     ./venv/bin/python src/setup_middleware_model.py update \\"
echo "       https://web-production-a5d93.up.railway.app"
echo ""
echo "If tests failed:"
echo "  ❌ Check Railway logs for errors"
echo "  ❌ Verify environment variables are set"
echo "  ❌ Wait 1-2 minutes for deployment to complete"
echo ""
