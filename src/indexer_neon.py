"""Script to index Mercedes products from Neon database into Typesense."""
import os
import json
import typesense
import psycopg2
from typing import List, Dict, Any
from config import Config
from models import Product

# Validate configuration
Config.validate()


class NeonProductIndexer:
    """Index Mercedes Scientific products from Neon database to Typesense."""

    def __init__(self):
        """Initialize indexer."""
        self.typesense_client = typesense.Client(Config.get_typesense_config())
        self.collection_name = Config.TYPESENSE_COLLECTION_NAME

        # Get Neon connection string from environment
        self.neon_connection_string = os.getenv("NEON_DATABASE_URL")
        if not self.neon_connection_string:
            raise ValueError("NEON_DATABASE_URL environment variable is required")

    def create_collection(self):
        """Create Typesense collection with schema."""
        schema = {
            "name": self.collection_name,
            "fields": [
                {"name": "product_id", "type": "string"},  # Using SKU as product_id
                {"name": "sku", "type": "string"},
                {"name": "name", "type": "string", "sort": True},
                {"name": "url_key", "type": "string"},
                {"name": "stock_status", "type": "string", "facet": True},
                {"name": "product_type", "type": "string", "facet": True},
                {"name": "description", "type": "string", "optional": True},
                {"name": "short_description", "type": "string", "optional": True},
                {"name": "price", "type": "float", "optional": True, "facet": True},
                {"name": "special_price", "type": "float", "optional": True, "facet": True},  # Sale price
                {"name": "currency", "type": "string"},
                {"name": "image_url", "type": "string", "optional": True},
                {"name": "categories", "type": "string[]", "facet": True},
                # Product attributes from additional_attributes
                {"name": "brand", "type": "string", "facet": True, "optional": True},
                {"name": "size", "type": "string", "facet": True, "optional": True},
                {"name": "color", "type": "string", "facet": True, "optional": True},
                {"name": "physical_form", "type": "string", "facet": True, "optional": True},
                {"name": "cas_number", "type": "string", "optional": True},
                # Inventory and shipping
                {"name": "qty", "type": "float", "optional": True},
                {"name": "weight", "type": "float", "optional": True},
                # Temporal fields for "latest" queries
                {"name": "created_at", "type": "int64", "optional": True, "sort": True},
                {"name": "updated_at", "type": "int64", "optional": True, "sort": True},
                # Embedding field for semantic search (now includes brand, size, color)
                {
                    "name": "embedding",
                    "type": "float[]",
                    "embed": {
                        "from": ["name", "description", "short_description", "categories", "brand", "size", "color", "physical_form"],
                        "model_config": {
                            "model_name": f"openai/{Config.OPENAI_EMBEDDING_MODEL}",
                            "api_key": Config.OPENAI_API_KEY,
                        }
                    }
                }
            ]
        }

        try:
            # Delete existing collection if it exists
            try:
                self.typesense_client.collections[self.collection_name].delete()
                print(f"✓ Deleted existing collection: {self.collection_name}")
            except Exception:
                pass

            # Create new collection
            self.typesense_client.collections.create(schema)
            print(f"✓ Created collection: {self.collection_name}")

        except Exception as e:
            print(f"✗ Error creating collection: {e}")
            raise

    def fetch_products_from_neon(self, limit: int = None) -> List[Dict[str, Any]]:
        """Fetch products from Neon database, merging store views."""
        print(f"\nConnecting to Neon database...")

        try:
            # Connect to Neon
            conn = psycopg2.connect(self.neon_connection_string)
            cursor = conn.cursor()

            # Build query that merges store_view_code = null and 'mercedesscientific'
            # Prioritize NULL row for most data (has price, full descriptions, specs)
            # Group by SKU to get one product per SKU
            query = """
                WITH merged_products AS (
                    SELECT
                        sku,
                        -- Prioritize NULL row for name, description (has better data)
                        MAX(CASE WHEN store_view_code IS NULL THEN name END) as name_null,
                        MAX(CASE WHEN store_view_code = 'mercedesscientific' THEN name END) as name_mercedes,
                        MAX(CASE WHEN store_view_code IS NULL THEN description END) as description,
                        MAX(CASE WHEN store_view_code IS NULL THEN short_description END) as short_description,
                        MAX(CASE WHEN store_view_code IS NULL THEN price END) as price,
                        MAX(CASE WHEN store_view_code IS NULL THEN special_price END) as special_price,
                        MAX(CASE WHEN store_view_code IS NULL THEN product_type END) as product_type,
                        MAX(CASE WHEN store_view_code IS NULL THEN url_key END) as url_key,
                        MAX(CASE WHEN store_view_code IS NULL THEN base_image END) as base_image,
                        MAX(CASE WHEN store_view_code IS NULL THEN categories END) as categories,
                        MAX(CASE WHEN store_view_code IS NULL THEN additional_attributes END) as additional_attributes,
                        MAX(CASE WHEN store_view_code IS NULL THEN weight END) as weight,
                        MAX(CASE WHEN store_view_code IS NULL THEN qty END) as qty,
                        MAX(CASE WHEN store_view_code IS NULL THEN created_at END) as created_at,
                        MAX(CASE WHEN store_view_code IS NULL THEN updated_at END) as updated_at,
                        MAX(is_in_stock) as is_in_stock
                    FROM catalog_products
                    WHERE (store_view_code IS NULL OR store_view_code = 'mercedesscientific')
                      AND is_in_stock = '1'
                      AND sku IS NOT NULL
                    GROUP BY sku
                )
                SELECT
                    sku,
                    COALESCE(name_null, name_mercedes) as name,
                    description,
                    short_description,
                    price,
                    special_price,
                    product_type,
                    url_key,
                    base_image,
                    categories,
                    additional_attributes,
                    weight,
                    qty,
                    created_at,
                    updated_at,
                    is_in_stock
                FROM merged_products
                WHERE COALESCE(name_null, name_mercedes) IS NOT NULL
            """

            if limit:
                query += f" LIMIT {limit}"

            print(f"Fetching products from Neon database...")
            print(f"Strategy: Merging store_view_code NULL + 'mercedesscientific'")
            if limit:
                print(f"Limit: {limit:,} products")
            else:
                print("Fetching all unique products")
            print(f"Note: This query may take 1-3 minutes depending on database size\n")

            # Execute query with timing
            import time
            query_start = time.time()
            print("⏳ Executing database query...")
            cursor.execute(query)
            query_time = time.time() - query_start
            print(f"✓ Query executed in {query_time:.1f}s\n")

            # Fetch rows in chunks with progress indicator
            print("⏳ Fetching and transforming products...")
            fetch_start = time.time()
            products = []
            batch_size = 1000  # Fetch 1000 rows at a time
            total_fetched = 0

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                # Transform rows
                for row in rows:
                    product = self._transform_neon_product(row)
                    if product:
                        products.append(product)

                total_fetched += len(rows)

                # Show progress every 1000 products
                elapsed = time.time() - fetch_start
                rate = total_fetched / elapsed if elapsed > 0 else 0
                print(f"  Fetched {total_fetched:,} rows ({rate:.0f} rows/sec)...")

                # If we've hit the limit, stop
                if limit and total_fetched >= limit:
                    break

            fetch_time = time.time() - fetch_start
            print(f"✓ Fetch completed in {fetch_time:.1f}s")

            cursor.close()
            conn.close()

            print(f"{'='*60}")
            print(f"✓ Total unique products fetched: {len(products):,}")
            print(f"{'='*60}")

            return products

        except Exception as e:
            print(f"✗ Error fetching from Neon: {e}")
            raise

    def _clean_and_deduplicate_categories(self, raw_categories: List[str]) -> List[str]:
        """
        Clean and deduplicate category names.

        Removes "Mercedes Scientific Main Store/" prefix and deduplicates categories
        that have the same end path (e.g., multiple "Shop By Lab" variations).
        Prefers shorter, more direct paths (Products over Shop By Lab).
        """
        if not raw_categories:
            return []

        # Step 1: Clean category names by removing prefix
        cleaned = []
        for cat in raw_categories:
            # Remove the "Mercedes Scientific Main Store/" prefix
            cleaned_cat = cat.replace("Mercedes Scientific Main Store/", "")
            if cleaned_cat:
                cleaned.append(cleaned_cat)

        # Step 2: Deduplicate by end path
        # Keep track of end paths we've seen (after last '/')
        seen_end_paths = {}
        unique_categories = []

        for cat in cleaned:
            # Extract the end path (e.g., "Specimen Collection/Cytology")
            parts = cat.split('/')

            # Consider the last 2 segments as the "end path" for deduplication
            # This handles cases like "Products/Gloves" vs "Shop By Lab/Chemistry/Gloves"
            if len(parts) >= 2:
                end_path = '/'.join(parts[-2:])
            else:
                end_path = cat

            # If we haven't seen this end path, or if this is a shorter path, keep it
            if end_path not in seen_end_paths:
                seen_end_paths[end_path] = cat
                unique_categories.append(cat)
            else:
                # If this path is shorter, replace the existing one
                existing = seen_end_paths[end_path]
                if len(cat) < len(existing):
                    # Remove the old one and add the new shorter one
                    if existing in unique_categories:
                        unique_categories.remove(existing)
                    seen_end_paths[end_path] = cat
                    unique_categories.append(cat)

        # Step 3: Sort to have "Products" paths first, then others
        unique_categories.sort(key=lambda x: (not x.startswith('Products/'), len(x), x))

        return unique_categories

    def _transform_neon_product(self, row) -> Dict[str, Any]:
        """Transform Neon database row to Typesense document."""
        try:
            sku, name, description, short_description, price, special_price, product_type, url_key, base_image, categories, additional_attributes, weight, qty, created_at, updated_at, is_in_stock = row

            # Parse categories (comma-separated string to list)
            raw_category_list = []
            if categories:
                raw_category_list = [cat.strip() for cat in categories.split(',') if cat.strip()]

            # Clean and deduplicate categories
            category_list = self._clean_and_deduplicate_categories(raw_category_list)

            # Parse additional_attributes to extract product specs
            specs = self._parse_additional_attributes(additional_attributes)

            # Add important specs to categories for better searchability
            if specs.get('brand'):
                category_list.append(f"Brand: {specs['brand']}")
            if specs.get('grade'):
                category_list.append(f"Grade: {specs['grade']}")
            if specs.get('size'):
                category_list.append(f"Size: {specs['size']}")

            # Enrich description with specs if available
            description_clean = self._clean_html(description) if description else None
            if description_clean and specs:
                # Keep description as-is, specs are already in additional_attributes
                pass
            elif not description_clean and specs:
                # If no description, create one from specs
                spec_desc = []
                for key in ['brand', 'grade', 'size', 'color', 'physical_form']:
                    if specs.get(key):
                        spec_desc.append(f"{key.replace('_', ' ').title()}: {specs[key]}")
                if spec_desc:
                    description_clean = "; ".join(spec_desc)

            short_desc_clean = self._clean_html(short_description) if short_description else None

            # Map stock status
            stock_status = "IN_STOCK" if is_in_stock == '1' else "OUT_OF_STOCK"

            # Build image URL
            image_url = None
            if base_image:
                image_url = f"https://www.mercedesscientific.com/media/catalog/product{base_image}"

            # Parse timestamps to Unix epoch (int64)
            created_ts = None
            updated_ts = None
            if created_at:
                try:
                    from datetime import datetime
                    # Format: "2025-01-15 10:30:45" or similar
                    dt = datetime.fromisoformat(created_at.replace(' ', 'T'))
                    created_ts = int(dt.timestamp())
                except:
                    pass

            if updated_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated_at.replace(' ', 'T'))
                    updated_ts = int(dt.timestamp())
                except:
                    pass

            return {
                "product_id": sku,  # Use SKU as product_id
                "sku": sku,
                "name": name,
                "url_key": url_key or "",
                "stock_status": stock_status,
                "product_type": product_type or "simple",
                "description": description_clean,
                "short_description": short_desc_clean,
                "price": float(price) if price else None,
                "special_price": float(special_price) if special_price else None,
                "currency": "USD",
                "image_url": image_url,
                "categories": category_list,
                # Product attributes from additional_attributes
                "brand": specs.get('brand'),
                "size": specs.get('size'),
                "color": specs.get('color'),
                "physical_form": specs.get('physical_form'),
                "cas_number": specs.get('cas_number'),
                # Inventory and shipping
                "qty": float(qty) if qty else None,
                "weight": float(weight) if weight else None,
                # Temporal fields
                "created_at": created_ts,
                "updated_at": updated_ts,
            }

        except Exception as e:
            print(f"  ⚠ Error transforming product {row[0] if row else 'unknown'}: {e}")
            return None

    def _parse_additional_attributes(self, attrs_string: str) -> Dict[str, str]:
        """Parse additional_attributes string to extract product specs."""
        specs = {}

        if not attrs_string:
            return specs

        try:
            # Format: key1=value1,key2=value2,key3={...}
            # Split by comma but respect nested braces
            pairs = []
            current = []
            brace_depth = 0

            for char in attrs_string:
                if char == '{':
                    brace_depth += 1
                elif char == '}':
                    brace_depth -= 1
                elif char == ',' and brace_depth == 0:
                    pairs.append(''.join(current))
                    current = []
                    continue
                current.append(char)

            if current:
                pairs.append(''.join(current))

            # Parse each key=value pair
            for pair in pairs:
                if '=' not in pair:
                    continue

                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Extract important specs
                if key in ['brand', 'grade', 'size', 'color', 'physical_form', 'cas_number', 'type_attribute']:
                    # Clean value (remove quotes, braces for simple values)
                    if value.startswith('{') or value.startswith('['):
                        continue  # Skip complex nested values
                    value = value.strip('"').strip("'")
                    specs[key] = value

        except Exception as e:
            # Silently ignore parsing errors
            pass

        return specs

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags from string."""
        import re
        if not html:
            return ""
        clean = re.sub('<[^<]+?>', '', html)
        clean = clean.strip()
        return clean[:500] if len(clean) > 500 else clean  # Limit length

    def _check_nl_model(self):
        """Check if natural language search model is configured."""
        import requests

        model_id = "openai-gpt4o-mini"
        base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"

        headers = {
            "X-TYPESENSE-API-KEY": Config.TYPESENSE_API_KEY,
            "Content-Type": "application/json"
        }

        try:
            check_url = f"{base_url}/nl_search_models/{model_id}"
            response = requests.get(check_url, headers=headers, timeout=5)

            if response.status_code == 200:
                print(f"\n✓ Natural Language Search model '{model_id}' is configured")
            else:
                print(f"\n⚠ WARNING: Natural Language Search model not configured!")
                print(f"   Model '{model_id}' does not exist in Typesense.")
                print(f"   Your search will work, but NL features (filter extraction, etc.) will be limited.")
                print(f"   Run: python src/setup_nl_model.py")
        except Exception:
            print(f"\n⚠ WARNING: Natural Language Search model not configured!")
            print(f"   Model '{model_id}' does not exist in Typesense.")
            print(f"   Your search will work, but NL features (filter extraction, etc.) will be limited.")
            print(f"   Run: python src/setup_nl_model.py")
        print()

    def index_products(self, products: List[Dict[str, Any]], batch_size: int = 100):
        """Index products to Typesense with auto-embeddings."""
        total_batches = (len(products) + batch_size - 1) // batch_size
        print(f"\nIndexing {len(products):,} products to Typesense...")
        print(f"Batches: {total_batches} (batch size: {batch_size})")
        print(f"Note: Embeddings are generated automatically during indexing\n")

        total_indexed = 0
        failed_count = 0

        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batch_num = i // batch_size + 1

            try:
                # Import documents (embeddings generated automatically by Typesense)
                result = self.typesense_client.collections[self.collection_name].documents.import_(
                    batch,
                    {"action": "create"}
                )

                # Count successful imports
                success_count = 0
                batch_failed = 0

                for item in result:
                    # Handle both string and dict responses
                    if isinstance(item, str):
                        parsed = json.loads(item)
                    else:
                        parsed = item

                    if parsed.get("success"):
                        success_count += 1
                    else:
                        batch_failed += 1
                        # Print errors for debugging
                        if "error" in parsed:
                            print(f"    ⚠ Error in batch {batch_num}: {parsed.get('error')}")

                total_indexed += success_count
                failed_count += batch_failed

                # Progress indicator
                progress = (total_indexed / len(products)) * 100
                print(f"  Batch {batch_num}/{total_batches}: Indexed {success_count}/{len(batch)} products "
                      f"(Total: {total_indexed:,}/{len(products):,} | {progress:.1f}% complete)")

            except Exception as e:
                print(f"✗ Error indexing batch {batch_num}: {e}")
                failed_count += len(batch)

        print(f"\n{'='*60}")
        print(f"✓ Successfully indexed: {total_indexed:,} products")
        if failed_count > 0:
            print(f"⚠ Failed to index: {failed_count} products")
        print(f"{'='*60}")

    def run(self, max_products: int = None):
        """Run the complete indexing process."""
        print("=" * 60)
        print("Mercedes Scientific Product Indexer (Neon → Typesense)")
        print("=" * 60)

        if max_products:
            print(f"Mode: Testing (indexing first {max_products:,} products)")
        else:
            print(f"Mode: Full indexing (all products from Neon)")

        print(f"Source: Neon Database (catalog_products)")
        print(f"Embedding Model: {Config.OPENAI_EMBEDDING_MODEL}")
        print(f"Collection: {self.collection_name}")
        print("=" * 60)

        # Check if NL search model is configured
        self._check_nl_model()

        try:
            # Create collection
            self.create_collection()

            # Fetch products from Neon
            products = self.fetch_products_from_neon(limit=max_products)

            if not products:
                print("✗ No products to index")
                return

            # Index products (with embeddings)
            print(f"\n{'='*60}")
            print(f"Starting indexing with auto-embeddings...")
            print(f"This may take 20-40 minutes for full catalog (34k+ products)")
            print(f"{'='*60}")
            self.index_products(products)

            print("\n" + "=" * 60)
            print("✓ Indexing completed successfully!")
            print(f"✓ Total products indexed: {len(products):,}")
            print(f"✓ Semantic search is now enabled!")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Indexing failed: {e}")
            raise


if __name__ == "__main__":
    import time
    start_time = time.time()

    indexer = NeonProductIndexer()

    # Index all products from Neon database
    # To test with limited products, use: indexer.run(max_products=1000)
    indexer.run()  # Full indexing

    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)

    print(f"\n{'='*60}")
    print(f"Indexing completed in {minutes}m {seconds}s")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("  1. Start API: python src/app.py")
    print("  2. Test search with semantic understanding!")
    print("\nTo re-index with limited products for testing:")
    print("  indexer.run(max_products=1000)")
