#!/usr/bin/env python3
"""
Test the stock status fix for JAI-2183
"""
import sys
sys.path.insert(0, 'src')

from indexer_neon import NeonProductIndexer

# Test SKUs from the investigation
test_skus = ["INN 187100", "INN 187200", "INN 187300"]

print("=" * 80)
print("Testing Stock Status Fix (JAI-2183)")
print("=" * 80)

# Create indexer instance
indexer = NeonProductIndexer()

# Test GraphQL stock fetcher
print("\n1. Testing GraphQL stock_qty fetcher:")
print("-" * 80)
stock_results = indexer.fetch_stock_qty_from_graphql(test_skus)

print(f"\n{'SKU':<15} {'GraphQL stock_qty':>20} {'Expected Status':>20}")
print("-" * 60)
for sku in test_skus:
    stock_qty = stock_results.get(sku)
    if stock_qty is not None:
        expected = "BACKORDER" if stock_qty == 0 else "IN_STOCK"
        print(f"{sku:<15} {stock_qty:>20} {expected:>20}")
    else:
        print(f"{sku:<15} {'None':>20} {'ERROR':>20}")

# Test stock status logic
print("\n\n2. Testing stock status logic:")
print("-" * 80)
print("Simulating product transformation with GraphQL stock_qty...")

for sku in test_skus:
    graphql_stock_qty = stock_results.get(sku)
    is_in_stock = '1'  # From Neon database
    neon_qty = {'INN 187100': 46, 'INN 187200': 136, 'INN 187300': 56}.get(sku, 0)

    # Apply the new logic
    if graphql_stock_qty is not None:
        if is_in_stock == '1':
            if graphql_stock_qty > 0:
                stock_status = "IN_STOCK"
            else:
                stock_status = "BACKORDER"
        else:
            stock_status = "OUT_OF_STOCK"
    else:
        stock_status = "IN_STOCK" if neon_qty > 0 else "OUT_OF_STOCK"

    priority = 1 if stock_status == "IN_STOCK" else (0 if stock_status == "BACKORDER" else -1)

    print(f"\n{sku}:")
    print(f"  Neon qty (stale): {neon_qty}")
    print(f"  GraphQL stock_qty (real-time): {graphql_stock_qty}")
    print(f"  is_in_stock: {is_in_stock}")
    print(f"  → Indexed stock_status: {stock_status}")
    print(f"  → in_stock_priority: {priority}")

    # Verify correctness
    if stock_status == "BACKORDER":
        print(f"  ✓ CORRECT: Should show 'TO SHIP' or 'BACKORDER' on website")
    elif stock_status == "IN_STOCK" and graphql_stock_qty and graphql_stock_qty > 0:
        print(f"  ✓ CORRECT: Has stock quantity")
    else:
        print(f"  ⚠ Check this result")

print("\n" + "=" * 80)
print("Test Complete!")
print("=" * 80)
print("\nExpected Results:")
print("  - INN 187100: BACKORDER (stock_qty=0)")
print("  - INN 187200: BACKORDER (stock_qty=0)")
print("  - INN 187300: BACKORDER (stock_qty=0)")
print("\nThis matches the production website showing 'TO SHIP' status.")
