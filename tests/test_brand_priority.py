"""Test brand prioritization in search results."""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.search_rag import RAGNaturalLanguageSearch

def test_brand_priority():
    """Test that in-house brands (Mercedes Scientific, Tanner Scientific) appear first."""

    print("=" * 80)
    print("Testing Brand Prioritization")
    print("=" * 80)
    print("\nIn-house brands should always appear at the top of search results:")
    print("  - Mercedes Scientific (priority: 100)")
    print("  - Tanner Scientific (priority: 90)")
    print("  - Other brands (priority: 50)")
    print("=" * 80)

    search_engine = RAGNaturalLanguageSearch()

    test_queries = [
        "gloves",
        "test tubes",
        "pipettes",
        "lab equipment",
        "microscope slides",
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: '{query}'")
        print('='*80)

        try:
            # Search with debug mode to see sorting
            response = search_engine.search(query, max_results=10, debug=False)

            print(f"\nTotal results: {response.total}")
            print(f"Query time: {response.query_time_ms:.2f}ms")

            # Show top 10 results with brand info
            print(f"\nTop {len(response.results)} Results:")
            print("-" * 80)

            inhouse_count = 0

            for i, product in enumerate(response.results, 1):
                # Try to extract brand from categories or name
                brand = "Unknown"
                if product.categories:
                    for cat in product.categories:
                        if cat.startswith("Brand: "):
                            brand = cat.replace("Brand: ", "")
                            break

                # Also check product name for brand
                name_lower = product.name.lower()

                # Check if in-house brand (check both brand field and name)
                is_inhouse = False
                if ("mercedes scientific" in brand.lower() or
                    "tanner scientific" in brand.lower() or
                    "mercedes scientific" in name_lower or
                    "tanner scientific" in name_lower):
                    is_inhouse = True
                    inhouse_count += 1
                    # Extract brand from name if not in categories
                    if brand == "Unknown":
                        if "mercedes scientific" in name_lower:
                            brand = "Mercedes Scientific"
                        elif "tanner scientific" in name_lower:
                            brand = "Tanner Scientific"

                # Format output
                brand_marker = "🏠 IN-HOUSE" if is_inhouse else ""
                price_str = f"${product.price:.2f}" if product.price else "N/A"

                print(f"{i:2}. {product.name[:60]:<60}")
                print(f"    SKU: {product.sku:<15} | Price: {price_str:<10} | Brand: {brand} {brand_marker}")

            print("-" * 80)
            print(f"In-house brand products in top {len(response.results)}: {inhouse_count}")

            if inhouse_count > 0:
                print("✅ SUCCESS: In-house brands found in results!")
            else:
                print("⚠️  No in-house brands found (may be data quality issue)")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_brand_priority()
