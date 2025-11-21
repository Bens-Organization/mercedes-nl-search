#!/bin/bash
# Test cache consistency fix on staging middleware (JAI-2202)
# This script manually tests the alcohol query twice and compares results

STAGING_API="https://mercedes-nl-search-staging.up.railway.app/api/search"

echo "=========================================="
echo "Testing Cache Consistency Fix (JAI-2202)"
echo "=========================================="
echo ""

# Function to extract total and filter from response
extract_info() {
    local response=$1
    local total=$(echo "$response" | jq -r '.total')
    local filter=$(echo "$response" | jq -r '.typesense_query.filters_applied')
    echo "Total: $total | Filter: $filter"
}

# Test query
QUERY="alcohol"

echo "Query: '$QUERY'"
echo ""

# First request (might be MISS or HIT depending on cache state)
echo "1️⃣  Making first request..."
RESPONSE1=$(curl -s -X POST "$STAGING_API" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"$QUERY\"}")

INFO1=$(extract_info "$RESPONSE1")
echo "   $INFO1"

# Wait a bit
sleep 2

# Second request (should be HIT if first was MISS)
echo ""
echo "2️⃣  Making second request..."
RESPONSE2=$(curl -s -X POST "$STAGING_API" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"$QUERY\"}")

INFO2=$(extract_info "$RESPONSE2")
echo "   $INFO2"

# Extract values for comparison
TOTAL1=$(echo "$RESPONSE1" | jq -r '.total')
TOTAL2=$(echo "$RESPONSE2" | jq -r '.total')
FILTER1=$(echo "$RESPONSE1" | jq -r '.typesense_query.filters_applied')
FILTER2=$(echo "$RESPONSE2" | jq -r '.typesense_query.filters_applied')

# Compare
echo ""
echo "=========================================="
echo "RESULT"
echo "=========================================="

if [ "$TOTAL1" == "$TOTAL2" ] && [ "$FILTER1" == "$FILTER2" ]; then
    echo "✅ PASS - Results are consistent!"
    echo "   Both requests returned $TOTAL1 products"
    echo "   Both used filter: $FILTER1"
    exit 0
else
    echo "❌ FAIL - Results are inconsistent!"
    echo ""
    echo "First request:  $TOTAL1 products, filter: $FILTER1"
    echo "Second request: $TOTAL2 products, filter: $FILTER2"
    exit 1
fi
