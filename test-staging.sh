#!/bin/bash
# test-staging.sh - Automated staging tests

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
STAGING_API="https://mercedes-search-api-staging.onrender.com"
TIMEOUT=30

echo "🧪 Running Staging Tests..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Function to test endpoint
test_endpoint() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local jq_filter="$5"

    echo -n "Testing $test_name... "

    if [ "$method" = "POST" ]; then
        response=$(curl -s -m $TIMEOUT -X POST "$STAGING_API$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1)
    else
        response=$(curl -s -m $TIMEOUT "$STAGING_API$endpoint" 2>&1)
    fi

    if [ $? -eq 0 ] && [ -n "$response" ]; then
        if echo "$response" | jq -e "$jq_filter" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ PASS${NC}"
            if [ -n "$jq_filter" ] && [ "$jq_filter" != "." ]; then
                echo "$response" | jq "$jq_filter"
            fi
            return 0
        else
            echo -e "${RED}✗ FAIL${NC} (Invalid response)"
            echo "$response" | head -n 5
            return 1
        fi
    else
        echo -e "${RED}✗ FAIL${NC} (Connection error or timeout)"
        return 1
    fi
}

# Test counter
total_tests=0
passed_tests=0

# Test 1: Health Check
echo "1️⃣  Health Check"
if test_endpoint "Health endpoint" "GET" "/health" "" ".status"; then
    ((passed_tests++))
fi
((total_tests++))
echo ""

# Test 2: Basic Search
echo "2️⃣  Basic Search"
if test_endpoint "Basic search" "POST" "/api/search" '{"query": "nitrile gloves"}' ".total"; then
    ((passed_tests++))
fi
((total_tests++))
echo ""

# Test 3: Filter Extraction
echo "3️⃣  Filter Extraction"
if test_endpoint "Price filter" "POST" "/api/search" '{"query": "gloves under $50"}' ".typesense_query.nl_extracted_filters"; then
    ((passed_tests++))
fi
((total_tests++))
echo ""

# Test 4: Stock Filter
echo "4️⃣  Stock Filter"
if test_endpoint "Stock filter" "POST" "/api/search" '{"query": "pipettes in stock"}' ".typesense_query.nl_extracted_filters"; then
    ((passed_tests++))
fi
((total_tests++))
echo ""

# Test 5: Category Detection
echo "5️⃣  Category Detection"
if test_endpoint "Category detection" "POST" "/api/search" '{"query": "powder-free nitrile gloves"}' ".detected_category, .category_confidence"; then
    ((passed_tests++))
fi
((total_tests++))
echo ""

# Test 6: Model Number Search
echo "6️⃣  Model Number Search"
if test_endpoint "Model number" "POST" "/api/search" '{"query": "TNR700S"}' ".total"; then
    ((passed_tests++))
fi
((total_tests++))
echo ""

# Test 7: Brand Search
echo "7️⃣  Brand Search"
if test_endpoint "Brand search" "POST" "/api/search" '{"query": "Mercedes Scientific pipettes"}' ".total"; then
    ((passed_tests++))
fi
((total_tests++))
echo ""

# Test 8: Temporal Search
echo "8️⃣  Temporal Search"
if test_endpoint "Latest products" "POST" "/api/search" '{"query": "latest microscopes"}' ".total"; then
    ((passed_tests++))
fi
((total_tests++))
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
if [ $passed_tests -eq $total_tests ]; then
    echo -e "${GREEN}✅ All tests passed! ($passed_tests/$total_tests)${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some tests failed: $passed_tests/$total_tests passed${NC}"
    exit 1
fi
