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
                {"name": "in_stock_priority", "type": "int32", "sort": True},  # 1=in stock, 0=out of stock (for sorting)
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
                # Restriction field for access control
                {"name": "restricted_class", "type": "string", "facet": True, "optional": True},
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

            # Fetch all rows
            rows = cursor.fetchall()
            print(f"✓ Fetched {len(rows)} products from query\n")

            # Extract product IDs for bulk category fetching
            product_ids = [row[0] for row in rows]  # entity_id is first column

            # Fetch ALL categories in bulk (MUCH faster than per-product queries!)
            print("⏳ Fetching categories for all products (bulk optimization)...")
            product_categories = self._fetch_all_categories_bulk(conn, product_ids)

            # Transform products
            print("⏳ Transforming products...")
            products = []
            total_rows = len(rows)

            for idx, row in enumerate(rows, 1):
                entity_id = row[0]
                categories = product_categories.get(entity_id, [])
                product = self._transform_magento_product(row, categories, attribute_ids)
                if product:
                    products.append(product)

                # Show progress every 1000 products
                if idx % 1000 == 0:
                    progress = (idx / total_rows) * 100
                    print(f"  Transformed {idx:,}/{total_rows:,} products ({progress:.1f}%)")

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
                stock.qty

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
        )

        if limit:
            query += f" LIMIT {limit}"

        return query

    def _fetch_all_categories_bulk(self, conn, product_ids: List[int]) -> Dict[int, List[str]]:
        """
        Fetch all categories for all products in ONE query (bulk optimization).

        Returns:
            Dictionary mapping product_id -> list of category paths
        """
        if not product_ids:
            return {}

        cursor = conn.cursor()

        # Step 1: Get all product-category relationships in one query
        print("  📂 Fetching product-category mappings...")
        placeholders = ','.join(['%s'] * len(product_ids))
        cursor.execute(f"""
            SELECT cp.product_id, c.entity_id, c.path, c.level
            FROM catalog_category_product cp
            JOIN catalog_category_entity c ON cp.category_id = c.entity_id
            WHERE cp.product_id IN ({placeholders})
        """, product_ids)

        product_category_paths = {}
        category_ids_needed = set()

        for product_id, cat_id, path, level in cursor.fetchall():
            if product_id not in product_category_paths:
                product_category_paths[product_id] = []
            product_category_paths[product_id].append(path)

            # Collect all category IDs we need names for
            for cid in path.split('/'):
                if cid:
                    category_ids_needed.add(int(cid))

        print(f"    ✓ Found {len(product_category_paths)} products with categories")
        print(f"    ✓ Need to fetch {len(category_ids_needed)} unique category names")

        # Step 2: Get all category names in one query
        print("  📂 Fetching category names...")
        category_ids_list = list(category_ids_needed)
        placeholders = ','.join(['%s'] * len(category_ids_list))
        cursor.execute(f"""
            SELECT entity_id, value
            FROM catalog_category_entity_varchar
            WHERE entity_id IN ({placeholders})
            AND attribute_id = (
                SELECT attribute_id FROM eav_attribute
                WHERE entity_type_id = (
                    SELECT entity_type_id FROM eav_entity_type
                    WHERE entity_type_code = 'catalog_category'
                )
                AND attribute_code = 'name'
            )
            AND store_id = 0
        """, category_ids_list)

        id_to_name = {int(eid): name for eid, name in cursor.fetchall()}
        print(f"    ✓ Fetched {len(id_to_name)} category names")

        # Step 3: Build category paths for each product
        print("  📂 Building category paths...")
        product_categories = {}

        for product_id, paths in product_category_paths.items():
            categories = []
            for path in paths:
                category_ids = [cid for cid in path.split('/') if cid]

                # Build category path preserving order
                cat_path_names = []
                for cat_id in category_ids:
                    if int(cat_id) in id_to_name:
                        cat_path_names.append(id_to_name[int(cat_id)])

                if cat_path_names:
                    full_path = ' / '.join(cat_path_names)
                    categories.append(full_path)

            product_categories[product_id] = categories

        cursor.close()
        print(f"    ✓ Built category paths for {len(product_categories)} products\n")

        return product_categories

    def _get_product_categories(self, cursor, product_id: int) -> List[str]:
        """
        Fetch category names for a product.
        Returns the full category path for each category (e.g., "Products/Gloves/Nitrile").
        """
        # First get all category IDs for this product
        query = """
            SELECT c.path
            FROM catalog_category_product cp
            JOIN catalog_category_entity c ON cp.category_id = c.entity_id
            WHERE cp.product_id = %s
        """

        cursor.execute(query, (product_id,))
        categories = []

        for (path,) in cursor.fetchall():
            # Path is like "1/2/15" - get category names for entire path
            category_ids = [cid for cid in path.split('/') if cid]

            # Fetch category names for all IDs in the path
            if len(category_ids) >= 2:  # Skip root-only paths
                cat_query = """
                    SELECT entity_id, value
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
                    ORDER BY entity_id
                """.format(','.join(['%s'] * len(category_ids)))

                cursor.execute(cat_query, category_ids)

                # Build a map of entity_id -> name
                id_to_name = {int(eid): name for eid, name in cursor.fetchall()}

                # Build category path preserving order
                cat_path_names = []
                for cat_id in category_ids:
                    if int(cat_id) in id_to_name:
                        cat_path_names.append(id_to_name[int(cat_id)])

                if cat_path_names:
                    # Join with '/' to create full path
                    full_path = '/'.join(cat_path_names)
                    categories.append(full_path)

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

    def _detect_category_type(self, categories: List[str]) -> str:
        """
        Detect the category type for brand ranking.

        Returns:
            - "lcms_hplc" for LCMS/HPLC Solvents
            - "drug_testing" for Drug Testing products
            - "general" for all other products
        """
        if not categories:
            return "general"

        # Check categories for LCMS/HPLC indicators
        for cat in categories:
            cat_lower = cat.lower()
            # Check for LCMS/HPLC grade indicators
            if any(grade in cat for grade in ["Grade: HPLC", "Grade: LCMS", "Grade: Ultra HPLC"]):
                return "lcms_hplc"
            # Check for Drug Testing category
            if "drug test" in cat_lower:
                return "drug_testing"

        return "general"

    def _detect_brand(self, sku: str, brand_field: str, product_name: str) -> str:
        """
        Detect brand from multiple sources.

        Priority:
        1. SKU prefix (most reliable)
        2. Brand field
        3. Product name

        Returns:
            Normalized brand name in lowercase, or None if no brand detected
        """
        sku_upper = (sku or "").upper().strip()
        brand_lower = (brand_field or "").lower().strip()
        name_lower = (product_name or "").lower().strip()

        # Check SKU prefix first (most reliable)
        if sku_upper.startswith("TBK"):
            return "concord technologies"
        elif sku_upper.startswith("BIR"):
            return "birch biotech"
        elif sku_upper.startswith("MER"):
            return "mercedes scientific"
        elif sku_upper.startswith("ALT"):
            return "alltest"
        elif sku_upper.startswith("TNR"):
            return "tanner scientific"
        elif sku_upper.startswith("HGS"):
            return "healgen"
        elif sku_upper.startswith("WON"):
            return "wondfo"

        # Check brand field (good for most products)
        if "concord" in brand_lower and "technology" in brand_lower:
            return "concord technologies"
        elif "birch" in brand_lower and "biotech" in brand_lower:
            return "birch biotech"
        elif "mercedes scientific" in brand_lower:
            return "mercedes scientific"
        elif "alltest" in brand_lower:
            return "alltest"
        elif "tanner scientific" in brand_lower:
            return "tanner scientific"
        elif "healgen" in brand_lower:
            return "healgen"
        elif "wondfo" in brand_lower:
            return "wondfo"

        # Check product name (fallback)
        if "mercedes scientific" in name_lower:
            return "mercedes scientific"
        elif "tanner scientific" in name_lower:
            return "tanner scientific"
        elif "concord" in name_lower:
            return "concord technologies"
        elif "birch" in name_lower and "biotech" in name_lower:
            return "birch biotech"
        elif "alltest" in name_lower:
            return "alltest"
        elif "healgen" in name_lower:
            return "healgen"
        elif "wondfo" in name_lower:
            return "wondfo"

        # Return original brand field if available
        return brand_field if brand_field else None

    def _calculate_brand_priority(self, sku: str, brand: str, product_name: str, categories: List[str]) -> int:
        """
        Calculate brand priority for sorting based on category and brand.

        Priority structure varies by category:

        **LCMS/HPLC Solvents** (detected by Grade: HPLC/LCMS in categories):
            100 - Concord Technologies (TBK prefix)
            90  - Birch Biotech (BIR prefix)
            80  - Mercedes Scientific (MER prefix)
            70  - Tanner Scientific (TNR prefix)
            50  - Other brands
            0   - No brand

        **Drug Testing** (detected by "Drug Test" in categories):
            100 - Mercedes Scientific (MER prefix)
            90  - AllTest (ALT prefix)
            80  - Tanner Scientific (TNR prefix)
            70  - Healgen (HGS prefix)
            60  - Wondfo (WON prefix)
            50  - Other brands
            0   - No brand

        **General** (all other categories):
            100 - Mercedes Scientific
            90  - Tanner Scientific
            50  - Other brands
            0   - No brand

        Args:
            sku: Product SKU (used for prefix detection)
            brand: Brand name from additional_attributes
            product_name: Product name (used as fallback)
            categories: List of category paths

        Returns:
            Priority score (higher = more important)
        """
        # Detect category type
        category_type = self._detect_category_type(categories)

        # Detect brand from multiple sources
        detected_brand = self._detect_brand(sku, brand, product_name)

        if not detected_brand:
            return 0

        brand_lower = detected_brand.lower()

        # LCMS/HPLC Solvents category
        if category_type == "lcms_hplc":
            if brand_lower == "concord technologies":
                return 100
            elif brand_lower == "birch biotech":
                return 90
            elif brand_lower == "mercedes scientific":
                return 80
            elif brand_lower == "tanner scientific":
                return 70
            else:
                return 50

        # Drug Testing category
        elif category_type == "drug_testing":
            if brand_lower == "mercedes scientific":
                return 100
            elif brand_lower == "alltest":
                return 90
            elif brand_lower == "tanner scientific":
                return 80
            elif brand_lower == "healgen":
                return 70
            elif brand_lower == "wondfo":
                return 60
            else:
                return 50

        # General (all other categories)
        else:
            if brand_lower == "mercedes scientific":
                return 100
            elif brand_lower == "tanner scientific":
                return 90
            else:
                return 50 if detected_brand else 0

    def _clean_and_deduplicate_categories(self, raw_categories: List[str]) -> List[str]:
        """
        Clean and deduplicate category names.

        Removes "Root Catalog / Mercedes Scientific Main Store /" prefix and deduplicates categories
        that have the same end path (e.g., multiple "Shop By Lab" variations).
        Prefers shorter, more direct paths (Products over Shop By Lab).
        """
        if not raw_categories:
            return []

        # Step 1: Clean category names by removing prefix
        cleaned = []
        for cat in raw_categories:
            # Remove the "Root Catalog / Mercedes Scientific Main Store /" prefix
            cleaned_cat = cat.replace("Root Catalog / Mercedes Scientific Main Store / ", "")
            # Fallback for variations
            cleaned_cat = cleaned_cat.replace("Root Catalog/Mercedes Scientific Main Store/", "")
            cleaned_cat = cleaned_cat.replace("Mercedes Scientific Main Store/", "")
            cleaned_cat = cleaned_cat.replace("Root Catalog/", "")
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

    def _parse_brand_from_html(self, short_description: str) -> str:
        """
        Parse brand from short_description HTML.

        Looks for patterns like:
        <p><strong>Brand:</strong> Tanner Scientific®</p>
        """
        if not short_description:
            return None

        import re
        # Look for <strong>Brand:</strong> pattern
        match = re.search(r'<strong>Brand:</strong>\s*([^<]+)', short_description, re.IGNORECASE)
        if match:
            brand = match.group(1).strip()
            # Remove ® and ™ symbols
            brand = brand.replace('®', '').replace('™', '').strip()
            return brand if brand else None

        return None

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags."""
        import re
        if not html:
            return ""
        clean = re.sub('<[^<]+?>', '', html)
        clean = clean.strip()
        return clean[:500] if len(clean) > 500 else clean

    def _transform_magento_product(self, row, raw_categories: List[str], attribute_ids: Dict[str, int]) -> Dict[str, Any]:
        """
        Transform Magento database row to Typesense document.

        Args:
            row: Database row from product query
            raw_categories: Pre-fetched category paths for this product
            attribute_ids: Attribute ID mapping (unused but kept for compatibility)
        """
        try:
            (entity_id, sku, type_id, created_at, updated_at,
             name, url_key, description, short_description,
             price, special_price, image, weight, status, visibility,
             is_in_stock, qty) = row

            # Parse brand from short_description HTML
            brand = self._parse_brand_from_html(short_description)

            # Stock status based on actual quantity (not just is_in_stock flag)
            # qty > 0 means actually in stock, regardless of is_in_stock flag
            stock_status = "IN_STOCK" if (qty and float(qty) > 0) else "OUT_OF_STOCK"

            # In-stock priority for sorting (in-stock products appear first)
            in_stock_priority = 1 if stock_status == "IN_STOCK" else 0

            # Image URL - strip cache-busting suffix from Magento
            image_url = None
            if image and image != 'no_selection':
                # Remove Magento's cache-busting suffix (long random strings: _lmiqvlogvlqkiemc.jpg → .jpg)
                # Only remove if suffix is 10+ characters (to avoid removing valid filename parts)
                import re
                clean_image = re.sub(r'_[a-z0-9]{10,}(\.\w+)$', r'\1', image)
                image_url = f"https://www.mercedesscientific.com/media/catalog/product{clean_image}"

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

            # Clean and deduplicate categories (already fetched in bulk)
            categories = self._clean_and_deduplicate_categories(raw_categories)

            # Add brand to categories for better searchability (if we parsed it from HTML)
            if brand:
                categories.append(f"Brand: {brand}")

            # Calculate brand priority (category-aware, checks SKU prefix, brand field, and product name)
            brand_priority = self._calculate_brand_priority(sku, brand, name, categories)

            return {
                "product_id": str(entity_id),
                "sku": sku,
                "sku_normalized": self._normalize_sku(sku),
                "name": name or "",
                "name_normalized": self._normalize_name(name),
                "url_key": url_key or "",
                "stock_status": stock_status,
                "in_stock_priority": in_stock_priority,
                "product_type": type_id or "simple",
                "description": description_clean,
                "short_description": short_desc_clean,
                "price": float(price) if price else None,
                "special_price": float(special_price) if special_price else None,
                "currency": "USD",
                "image_url": image_url,
                "categories": categories,
                "brand": brand,  # Parsed from HTML short_description
                "brand_priority": brand_priority,
                "size": None,  # Not available in Magento (would need to parse from HTML)
                "color": None,  # Not available in Magento (would need to parse from HTML)
                "physical_form": None,  # Not available in Magento
                "cas_number": None,  # Not available in Magento
                "qty": float(qty) if qty else None,
                "weight": float(weight) if weight else None,
                "created_at": created_ts,
                "updated_at": updated_ts,
                # Restriction field (Magento doesn't have this, so set to None)
                "restricted_class": None,
            }

        except Exception as e:
            print(f"  ⚠ Error transforming product {row[1] if len(row) > 1 else 'unknown'}: {e}")
            import traceback
            traceback.print_exc()
            return None

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

        # Check if NL search model is configured
        self._check_nl_model()

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
