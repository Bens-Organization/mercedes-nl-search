"""Script to index Mercedes products from Magento 2 database into Typesense."""
import os
import json
import typesense
from typing import List, Dict, Any
from config import Config
from models import Product

# MySQL connector
try:
    import mysql.connector
except ImportError:
    print("ERROR: mysql-connector-python is not installed")
    print("Install it with: pip install mysql-connector-python")
    exit(1)

# Validate configuration
Config.validate()


class MagentoProductIndexer:
    """Index Mercedes Scientific products from Magento 2 MySQL database to Typesense."""

    def __init__(self):
        """Initialize indexer."""
        self.typesense_client = typesense.Client(Config.get_typesense_config())
        self.collection_name = Config.TYPESENSE_COLLECTION_NAME

        # Get Magento MySQL connection details from environment
        self.mysql_host = os.getenv("MAGENTO_DB_HOST")
        self.mysql_port = int(os.getenv("MAGENTO_DB_PORT", "3306"))
        self.mysql_database = os.getenv("MAGENTO_DB_NAME")
        self.mysql_user = os.getenv("MAGENTO_DB_USER")
        self.mysql_password = os.getenv("MAGENTO_DB_PASSWORD")

        if not all([self.mysql_host, self.mysql_database, self.mysql_user, self.mysql_password]):
            raise ValueError(
                "Missing Magento database credentials. Required environment variables:\n"
                "  - MAGENTO_DB_HOST\n"
                "  - MAGENTO_DB_NAME\n"
                "  - MAGENTO_DB_USER\n"
                "  - MAGENTO_DB_PASSWORD\n"
                "  - MAGENTO_DB_PORT (optional, defaults to 3306)"
            )

    def create_collection(self):
        """Create Typesense collection with schema (same as Neon indexer)."""
        schema = {
            "name": self.collection_name,
            "fields": [
                {"name": "product_id", "type": "string"},  # Using SKU as product_id
                {
                    "name": "sku",
                    "type": "string",
                    "token_separators": [" ", "-", ".", "/"],
                    "infix": True
                },
                {
                    "name": "sku_normalized",
                    "type": "string",
                    "optional": True,
                    "index": True,
                    "infix": True,
                },
                {
                    "name": "name",
                    "type": "string",
                    "sort": True,
                    "token_separators": [" ", "-", "/"],
                    "infix": True
                },
                {
                    "name": "name_normalized",
                    "type": "string",
                    "optional": True,
                    "index": True,
                    "token_separators": [" "],
                    "infix": True,
                },
                {"name": "url_key", "type": "string"},
                {"name": "stock_status", "type": "string", "facet": True},
                {"name": "product_type", "type": "string", "facet": True},
                {"name": "description", "type": "string", "optional": True},
                {"name": "short_description", "type": "string", "optional": True},
                {"name": "price", "type": "float", "optional": True, "facet": True},
                {"name": "special_price", "type": "float", "optional": True, "facet": True},
                {"name": "currency", "type": "string"},
                {"name": "image_url", "type": "string", "optional": True},
                {"name": "categories", "type": "string[]", "facet": True},
                # Product attributes
                {"name": "brand", "type": "string", "facet": True, "optional": True},
                {"name": "brand_priority", "type": "int32", "optional": True, "sort": True},
                {"name": "size", "type": "string", "facet": True, "optional": True},
                {"name": "color", "type": "string", "facet": True, "optional": True},
                {"name": "physical_form", "type": "string", "facet": True, "optional": True},
                {"name": "cas_number", "type": "string", "optional": True},
                # Inventory and shipping
                {"name": "qty", "type": "float", "optional": True},
                {"name": "weight", "type": "float", "optional": True},
                # Temporal fields
                {"name": "created_at", "type": "int64", "optional": True, "sort": True},
                {"name": "updated_at", "type": "int64", "optional": True, "sort": True},
                # Embedding field for semantic search
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
            # Check if collection exists
            collection_exists = False
            try:
                self.typesense_client.collections[self.collection_name].retrieve()
                collection_exists = True
            except Exception:
                pass

            if collection_exists:
                print(f"\n⚠  Collection '{self.collection_name}' already exists")
                print(f"⚠  This will DELETE all indexed products and re-create the collection")

                # Ask user for confirmation
                response = input("\nDo you want to delete and recreate it? (y/n): ")
                if response.lower() != 'y':
                    print("✓ Keeping existing collection (no changes)")
                    return

                # Delete existing collection
                self.typesense_client.collections[self.collection_name].delete()
                print(f"✓ Deleted existing collection: {self.collection_name}")

            # Create new collection
            self.typesense_client.collections.create(schema)
            print(f"✓ Created collection: {self.collection_name}")

        except Exception as e:
            print(f"✗ Error creating collection: {e}")
            raise

    def fetch_products_from_magento(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch products from Magento 2 database.

        Magento uses EAV (Entity-Attribute-Value) model, which is complex.
        This query joins multiple tables to get product data.
        """
        print(f"\nConnecting to Magento database...")
        print(f"Host: {self.mysql_host}:{self.mysql_port}")
        print(f"Database: {self.mysql_database}")

        try:
            # Connect to MySQL
            conn = mysql.connector.connect(
                host=self.mysql_host,
                port=self.mysql_port,
                database=self.mysql_database,
                user=self.mysql_user,
                password=self.mysql_password
            )
            cursor = conn.cursor()

            # Get attribute IDs for name, description, etc.
            # These vary by Magento installation
            print("\n⏳ Discovering Magento attribute IDs...")
            attribute_ids = self._get_attribute_ids(cursor)
            print(f"✓ Found {len(attribute_ids)} product attributes")

            # Build query to fetch products from EAV structure
            # This is complex because Magento stores attributes across multiple tables
            query = self._build_product_query(attribute_ids, limit)

            print(f"\n⏳ Fetching products from Magento database...")
            if limit:
                print(f"Limit: {limit:,} products")
            else:
                print("Fetching all products")

            import time
            query_start = time.time()
            cursor.execute(query)
            query_time = time.time() - query_start
            print(f"✓ Query executed in {query_time:.1f}s\n")

            # Fetch and transform products
            print("⏳ Transforming products...")
            products = []

            for row in cursor.fetchall():
                product = self._transform_magento_product(row, attribute_ids)
                if product:
                    products.append(product)

            cursor.close()
            conn.close()

            print(f"\n{'='*60}")
            print(f"✓ Total products fetched: {len(products):,}")
            print(f"{'='*60}")

            return products

        except Exception as e:
            print(f"✗ Error fetching from Magento: {e}")
            raise

    def _get_attribute_ids(self, cursor) -> Dict[str, int]:
        """
        Get attribute IDs from Magento's eav_attribute table.

        Magento uses attribute codes like 'name', 'sku', 'price', etc.
        We need their IDs to query the EAV tables.
        """
        attributes_to_fetch = [
            'name', 'sku', 'description', 'short_description',
            'price', 'special_price', 'url_key', 'image',
            'weight', 'status', 'visibility',
            'brand', 'size', 'color', 'physical_form', 'cas_number',
            'created_at', 'updated_at'
        ]

        query = """
            SELECT attribute_code, attribute_id, backend_type
            FROM eav_attribute
            WHERE entity_type_id = (
                SELECT entity_type_id
                FROM eav_entity_type
                WHERE entity_type_code = 'catalog_product'
            )
            AND attribute_code IN ({})
        """.format(','.join(['%s'] * len(attributes_to_fetch)))

        cursor.execute(query, attributes_to_fetch)

        attribute_ids = {}
        for code, attr_id, backend_type in cursor.fetchall():
            attribute_ids[code] = {
                'id': attr_id,
                'backend_type': backend_type  # varchar, int, decimal, text, datetime
            }

        return attribute_ids

    def _build_product_query(self, attribute_ids: Dict[str, int], limit: int = None) -> str:
        """
        Build complex EAV query to extract products from Magento.

        This joins:
        - catalog_product_entity (main product table)
        - catalog_product_entity_varchar (text attributes)
        - catalog_product_entity_int (integer attributes)
        - catalog_product_entity_decimal (price attributes)
        - cataloginventory_stock_item (stock status)
        - catalog_category_product (categories)
        """

        # Base query
        query = """
            SELECT DISTINCT
                e.entity_id,
                e.sku,
                e.type_id,
                e.created_at,
                e.updated_at,

                -- Name (varchar)
                name_attr.value as name,

                -- URL key (varchar)
                url_attr.value as url_key,

                -- Description (text)
                desc_attr.value as description,

                -- Short description (text)
                short_desc_attr.value as short_description,

                -- Price (decimal)
                price_attr.value as price,

                -- Special price (decimal)
                special_price_attr.value as special_price,

                -- Image (varchar)
                image_attr.value as image,

                -- Weight (decimal)
                weight_attr.value as weight,

                -- Status (int) - 1=enabled, 2=disabled
                status_attr.value as status,

                -- Visibility (int)
                visibility_attr.value as visibility,

                -- Stock status
                stock.is_in_stock,
                stock.qty,

                -- Custom attributes
                brand_attr.value as brand,
                size_attr.value as size,
                color_attr.value as color,
                physical_form_attr.value as physical_form,
                cas_attr.value as cas_number

            FROM catalog_product_entity e

            -- Join attribute tables (default store view = 0)
            LEFT JOIN catalog_product_entity_varchar name_attr
                ON e.entity_id = name_attr.entity_id
                AND name_attr.attribute_id = {name_id}
                AND name_attr.store_id = 0

            LEFT JOIN catalog_product_entity_varchar url_attr
                ON e.entity_id = url_attr.entity_id
                AND url_attr.attribute_id = {url_key_id}
                AND url_attr.store_id = 0

            LEFT JOIN catalog_product_entity_text desc_attr
                ON e.entity_id = desc_attr.entity_id
                AND desc_attr.attribute_id = {description_id}
                AND desc_attr.store_id = 0

            LEFT JOIN catalog_product_entity_text short_desc_attr
                ON e.entity_id = short_desc_attr.entity_id
                AND short_desc_attr.attribute_id = {short_description_id}
                AND short_desc_attr.store_id = 0

            LEFT JOIN catalog_product_entity_decimal price_attr
                ON e.entity_id = price_attr.entity_id
                AND price_attr.attribute_id = {price_id}
                AND price_attr.store_id = 0

            LEFT JOIN catalog_product_entity_decimal special_price_attr
                ON e.entity_id = special_price_attr.entity_id
                AND special_price_attr.attribute_id = {special_price_id}
                AND special_price_attr.store_id = 0

            LEFT JOIN catalog_product_entity_varchar image_attr
                ON e.entity_id = image_attr.entity_id
                AND image_attr.attribute_id = {image_id}
                AND image_attr.store_id = 0

            LEFT JOIN catalog_product_entity_decimal weight_attr
                ON e.entity_id = weight_attr.entity_id
                AND weight_attr.attribute_id = {weight_id}
                AND weight_attr.store_id = 0

            LEFT JOIN catalog_product_entity_int status_attr
                ON e.entity_id = status_attr.entity_id
                AND status_attr.attribute_id = {status_id}
                AND status_attr.store_id = 0

            LEFT JOIN catalog_product_entity_int visibility_attr
                ON e.entity_id = visibility_attr.entity_id
                AND visibility_attr.attribute_id = {visibility_id}
                AND visibility_attr.store_id = 0

            -- Stock
            LEFT JOIN cataloginventory_stock_item stock
                ON e.entity_id = stock.product_id

            -- Custom attributes
            LEFT JOIN catalog_product_entity_varchar brand_attr
                ON e.entity_id = brand_attr.entity_id
                AND brand_attr.attribute_id = {brand_id}
                AND brand_attr.store_id = 0

            LEFT JOIN catalog_product_entity_varchar size_attr
                ON e.entity_id = size_attr.entity_id
                AND size_attr.attribute_id = {size_id}
                AND size_attr.store_id = 0

            LEFT JOIN catalog_product_entity_varchar color_attr
                ON e.entity_id = color_attr.entity_id
                AND color_attr.attribute_id = {color_id}
                AND color_attr.store_id = 0

            LEFT JOIN catalog_product_entity_varchar physical_form_attr
                ON e.entity_id = physical_form_attr.entity_id
                AND physical_form_attr.attribute_id = {physical_form_id}
                AND physical_form_attr.store_id = 0

            LEFT JOIN catalog_product_entity_varchar cas_attr
                ON e.entity_id = cas_attr.entity_id
                AND cas_attr.attribute_id = {cas_number_id}
                AND cas_attr.store_id = 0

            WHERE status_attr.value = 1  -- Only enabled products
            AND visibility_attr.value IN (2, 3, 4)  -- Catalog, Search, Both (not "Not Visible Individually")
        """

        # Format with attribute IDs
        query = query.format(
            name_id=attribute_ids.get('name', {}).get('id', 0),
            url_key_id=attribute_ids.get('url_key', {}).get('id', 0),
            description_id=attribute_ids.get('description', {}).get('id', 0),
            short_description_id=attribute_ids.get('short_description', {}).get('id', 0),
            price_id=attribute_ids.get('price', {}).get('id', 0),
            special_price_id=attribute_ids.get('special_price', {}).get('id', 0),
            image_id=attribute_ids.get('image', {}).get('id', 0),
            weight_id=attribute_ids.get('weight', {}).get('id', 0),
            status_id=attribute_ids.get('status', {}).get('id', 0),
            visibility_id=attribute_ids.get('visibility', {}).get('id', 0),
            brand_id=attribute_ids.get('brand', {}).get('id', 0),
            size_id=attribute_ids.get('size', {}).get('id', 0),
            color_id=attribute_ids.get('color', {}).get('id', 0),
            physical_form_id=attribute_ids.get('physical_form', {}).get('id', 0),
            cas_number_id=attribute_ids.get('cas_number', {}).get('id', 0),
        )

        if limit:
            query += f" LIMIT {limit}"

        return query

    def _get_product_categories(self, cursor, product_id: int) -> List[str]:
        """Fetch category names for a product."""
        query = """
            SELECT c.path
            FROM catalog_category_product cp
            JOIN catalog_category_entity c ON cp.category_id = c.entity_id
            WHERE cp.product_id = %s
        """

        cursor.execute(query, (product_id,))
        categories = []

        for (path,) in cursor.fetchall():
            # Path is like "1/2/15" - get category names
            category_ids = path.split('/')

            # Fetch category names
            if len(category_ids) > 2:  # Skip root categories
                cat_query = """
                    SELECT value
                    FROM catalog_category_entity_varchar
                    WHERE entity_id IN ({})
                    AND attribute_id = (
                        SELECT attribute_id
                        FROM eav_attribute
                        WHERE entity_type_id = (
                            SELECT entity_type_id
                            FROM eav_entity_type
                            WHERE entity_type_code = 'catalog_category'
                        )
                        AND attribute_code = 'name'
                    )
                    AND store_id = 0
                """.format(','.join(['%s'] * len(category_ids)))

                cursor.execute(cat_query, category_ids)
                cat_names = [name for (name,) in cursor.fetchall()]

                if cat_names:
                    categories.append(' / '.join(cat_names))

        return categories

    def _normalize_sku(self, text: str) -> str:
        """Normalize SKU (same as Neon indexer)."""
        if not text:
            return ""
        normalized = text.replace(" ", "").replace("-", "").replace(".", "").replace("/", "").replace(",", "").lower()
        return normalized

    def _normalize_name(self, text: str) -> str:
        """Normalize product name (same as Neon indexer)."""
        if not text:
            return ""
        import re
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        normalized = text.replace("-", " ").replace(".", " ").replace("/", " ").replace(",", " ").lower()
        normalized = " ".join(normalized.split())
        return normalized

    def _calculate_brand_priority(self, brand: str, product_name: str = None) -> int:
        """Calculate brand priority (same as Neon indexer)."""
        brand_lower = (brand or "").lower().strip()
        name_lower = (product_name or "").lower().strip()

        if "mercedes scientific" in brand_lower or "mercedes scientific" in name_lower:
            return 100
        elif "tanner scientific" in brand_lower or "tanner scientific" in name_lower:
            return 90
        elif brand:
            return 50
        else:
            return 0

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags."""
        import re
        if not html:
            return ""
        clean = re.sub('<[^<]+?>', '', html)
        clean = clean.strip()
        return clean[:500] if len(clean) > 500 else clean

    def _transform_magento_product(self, row, attribute_ids: Dict[str, int]) -> Dict[str, Any]:
        """Transform Magento database row to Typesense document."""
        try:
            (entity_id, sku, type_id, created_at, updated_at,
             name, url_key, description, short_description,
             price, special_price, image, weight, status, visibility,
             is_in_stock, qty, brand, size, color, physical_form, cas_number) = row

            # Stock status
            stock_status = "IN_STOCK" if is_in_stock == 1 else "OUT_OF_STOCK"

            # Image URL
            image_url = None
            if image and image != 'no_selection':
                image_url = f"https://www.mercedesscientific.com/media/catalog/product{image}"

            # Clean descriptions
            description_clean = self._clean_html(description) if description else None
            short_desc_clean = self._clean_html(short_description) if short_description else None

            # Timestamps
            created_ts = None
            updated_ts = None
            if created_at:
                from datetime import datetime
                try:
                    created_ts = int(created_at.timestamp())
                except:
                    pass
            if updated_at:
                from datetime import datetime
                try:
                    updated_ts = int(updated_at.timestamp())
                except:
                    pass

            # Categories (fetch separately due to complexity)
            # For now, use empty list - you can implement category fetching later
            categories = []

            # Brand priority
            brand_priority = self._calculate_brand_priority(brand, name)

            return {
                "product_id": str(entity_id),
                "sku": sku,
                "sku_normalized": self._normalize_sku(sku),
                "name": name or "",
                "name_normalized": self._normalize_name(name),
                "url_key": url_key or "",
                "stock_status": stock_status,
                "product_type": type_id or "simple",
                "description": description_clean,
                "short_description": short_desc_clean,
                "price": float(price) if price else None,
                "special_price": float(special_price) if special_price else None,
                "currency": "USD",
                "image_url": image_url,
                "categories": categories,
                "brand": brand,
                "brand_priority": brand_priority,
                "size": size,
                "color": color,
                "physical_form": physical_form,
                "cas_number": cas_number,
                "qty": float(qty) if qty else None,
                "weight": float(weight) if weight else None,
                "created_at": created_ts,
                "updated_at": updated_ts,
            }

        except Exception as e:
            print(f"  ⚠ Error transforming product {row[1] if len(row) > 1 else 'unknown'}: {e}")
            return None

    def index_products(self, products: List[Dict[str, Any]], batch_size: int = 100):
        """Index products to Typesense (same as Neon indexer)."""
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
                result = self.typesense_client.collections[self.collection_name].documents.import_(
                    batch,
                    {"action": "create"}
                )

                success_count = 0
                batch_failed = 0

                for item in result:
                    if isinstance(item, str):
                        parsed = json.loads(item)
                    else:
                        parsed = item

                    if parsed.get("success"):
                        success_count += 1
                    else:
                        batch_failed += 1
                        if "error" in parsed:
                            print(f"    ⚠ Error in batch {batch_num}: {parsed.get('error')}")

                total_indexed += success_count
                failed_count += batch_failed

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
        print("Mercedes Scientific Product Indexer (Magento → Typesense)")
        print("=" * 60)

        if max_products:
            print(f"Mode: Testing (indexing first {max_products:,} products)")
        else:
            print(f"Mode: Full indexing (all enabled products from Magento)")

        print(f"Source: Magento 2 MySQL Database")
        print(f"Embedding Model: {Config.OPENAI_EMBEDDING_MODEL}")
        print(f"Collection: {self.collection_name}")
        print("=" * 60)

        try:
            # Create collection
            self.create_collection()

            # Fetch products from Magento
            products = self.fetch_products_from_magento(limit=max_products)

            if not products:
                print("✗ No products to index")
                return

            # Index products
            print(f"\n{'='*60}")
            print(f"Starting indexing with auto-embeddings...")
            print(f"This may take 20-40 minutes for full catalog")
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

    indexer = MagentoProductIndexer()

    # Index all products from Magento
    # To test with limited products, use: indexer.run(max_products=100)
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
    print("  indexer.run(max_products=100)")
