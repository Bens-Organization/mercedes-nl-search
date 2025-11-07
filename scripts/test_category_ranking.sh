#!/bin/bash
# Test script to verify category-specific brand ranking
# Run AFTER re-indexing with: ./venv/bin/python3 src/indexer_neon.py

echo "=========================================="
echo "CATEGORY-SPECIFIC BRAND RANKING TEST"
echo "=========================================="
echo ""

# Test 1: LCMS/HPLC Solvents
echo "Test 1: LCMS/HPLC Solvents - HPLC methanol"
echo "Expected order: Concord (100) > Birch (90) > Mercedes (80) > Tanner (70) > Others (50)"
echo "------------------------------------------"
curl -s -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "HPLC methanol",
    "max_results": 10
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Total results: {data.get('total', 0)}\n\")
for i, product in enumerate(data.get('results', [])[:10], 1):
    sku = product.get('sku', 'N/A')
    name = product.get('name', 'N/A')[:60]
    brand = 'N/A'
    for cat in product.get('categories', []):
        if cat.startswith('Brand: '):
            brand = cat.replace('Brand: ', '')
            break
    print(f\"{i}. {sku} | {brand}\")
    print(f\"   {name}\")
print()
"

echo ""
echo "=========================================="
echo ""

# Test 2: Drug Testing
echo "Test 2: Drug Testing - 12-panel drug test"
echo "Expected order: Mercedes (100) > AllTest (90) > Tanner (80) > Healgen (70) > Wondfo (60)"
echo "------------------------------------------"
curl -s -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "12-panel drug test",
    "max_results": 15
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Total results: {data.get('total', 0)}\n\")
for i, product in enumerate(data.get('results', [])[:15], 1):
    sku = product.get('sku', 'N/A')
    name = product.get('name', 'N/A')[:60]
    brand = 'N/A'
    for cat in product.get('categories', []):
        if cat.startswith('Brand: '):
            brand = cat.replace('Brand: ', '')
            break
    print(f\"{i}. {sku} | {brand}\")
    print(f\"   {name}\")
print()
"

echo ""
echo "=========================================="
echo ""

# Test 3: General Category
echo "Test 3: General Category - nitrile gloves"
echo "Expected order: Mercedes (100) > Tanner (90) > Others (50)"
echo "------------------------------------------"
curl -s -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "nitrile gloves",
    "max_results": 10
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Total results: {data.get('total', 0)}\n\")
for i, product in enumerate(data.get('results', [])[:10], 1):
    sku = product.get('sku', 'N/A')
    name = product.get('name', 'N/A')[:60]
    brand = 'N/A'
    for cat in product.get('categories', []):
        if cat.startswith('Brand: '):
            brand = cat.replace('Brand: ', '')
            break
    print(f\"{i}. {sku} | {brand}\")
    print(f\"   {name}\")
print()
"

echo ""
echo "=========================================="
echo "✅ Testing complete!"
echo ""
echo "What to look for:"
echo "- LCMS/HPLC: Concord/Birch should be at top"
echo "- Drug Testing: Mercedes > AllTest > Tanner > Healgen > Wondfo"
echo "- General: Mercedes/Tanner at top"
echo "=========================================="
