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

            # Pre-load ALL option values for performance (avoids N+1 queries)
            print("\n⏳ Loading option values lookup table...")
            import time
            option_start = time.time()
            option_values = self._load_all_option_values(cursor)
            option_time = time.time() - option_start
            print(f"✓ Loaded {len(option_values):,} option values in {option_time:.1f}s")

            # Build query to fetch products from EAV structure
            # This is complex because Magento stores attributes across multiple tables
            query = self._build_product_query(attribute_ids, limit)

            print(f"\n⏳ Fetching products from Magento database...")
            if limit:
                print(f"Limit: {limit:,} products")
            else:
                print("Fetching all products")

            query_start = time.time()
            cursor.execute(query)
            query_time = time.time() - query_start
            print(f"✓ Query executed in {query_time:.1f}s")

            # Fetch all rows first
            rows = cursor.fetchall()
            total_rows = len(rows)
            print(f"✓ Retrieved {total_rows:,} products from database\n")

            # Batch fetch categories for all products (avoids N+1 queries)
            print("⏳ Batch loading categories...")
            cat_start = time.time()
            entity_ids = [row[0] for row in rows]
            all_categories = self._batch_get_categories(cursor, entity_ids)
            cat_time = time.time() - cat_start
            print(f"✓ Loaded categories for {len(all_categories):,} products in {cat_time:.1f}s\n")

            cursor.close()

            # Transform products (using pre-loaded data)
            print(f"⏳ Transforming {total_rows:,} products...")
            products = []

            start_time = time.time()
            last_report = start_time

            for idx, row in enumerate(rows):
                product = self._transform_magento_product(row, attribute_ids, option_values, all_categories)
                if product:
                    products.append(product)

                # Progress report every 1000 products or every 5 seconds
                current_time = time.time()
                if (idx + 1) % 1000 == 0 or (current_time - last_report) >= 5:
                    elapsed = current_time - start_time
                    rate = (idx + 1) / elapsed if elapsed > 0 else 0
                    percent = ((idx + 1) / total_rows * 100)
                    eta = (total_rows - idx - 1) / rate if rate > 0 else 0
                    print(f"  Progress: {idx + 1:,}/{total_rows:,} ({percent:.1f}%) - {rate:.0f} products/sec - ETA: {eta:.0f}s")
                    last_report = current_time

            conn.close()

            print(f"\n{'='*60}")
            print(f"✓ Total products fetched: {len(products):,}")
            print(f"{'='*60}")

            return products

        except Exception as e:
            print(f"✗ Error fetching from Magento: {e}")
            raise

    def _load_all_option_values(self, cursor) -> Dict[str, str]:
        """
        Pre-load ALL option values to avoid N+1 queries during transformation.

        Returns a dictionary: {option_id: text_value}
        """
        query = """
            SELECT option_id, value
            FROM eav_attribute_option_value
            WHERE store_id = 0
        """
        cursor.execute(query)

        option_values = {}
        for option_id, value in cursor.fetchall():
            option_values[str(option_id)] = value

        return option_values

    def _batch_get_categories(self, cursor, entity_ids: List[int]) -> Dict[int, List[str]]:
        """
        Batch fetch categories for multiple products to avoid N+1 queries.

        Returns a dictionary: {entity_id: [category_paths]}
        """
        if not entity_ids:
            return {}

        # Get category name attribute ID
        cursor.execute("""
            SELECT attribute_id
            FROM eav_attribute
            WHERE entity_type_id = (
                SELECT entity_type_id
                FROM eav_entity_type
                WHERE entity_type_code = 'catalog_category'
            )
            AND attribute_code = 'name'
        """)

        result = cursor.fetchone()
        if not result:
            return {}

        cat_name_attr_id = result[0]

        # Fetch all product-category relationships
        placeholders = ','.join(['%s'] * len(entity_ids))
        query = f"""
            SELECT cp.product_id, c.path, c.entity_id
            FROM catalog_category_product cp
            JOIN catalog_category_entity c ON cp.category_id = c.entity_id
            WHERE cp.product_id IN ({placeholders})
        """

        cursor.execute(query, entity_ids)
        product_categories = {}

        for product_id, path, category_id in cursor.fetchall():
            if product_id not in product_categories:
                product_categories[product_id] = []
            product_categories[product_id].append(path)

        # Fetch all category names in one query
        # Get unique category IDs from all paths
        all_category_ids = set()
        for paths in product_categories.values():
            for path in paths:
                category_ids = path.split('/')
                all_category_ids.update(category_ids)

        if not all_category_ids:
            return {}

        # Fetch category names
        cat_id_list = list(all_category_ids)
        placeholders = ','.join(['%s'] * len(cat_id_list))
        query = f"""
            SELECT entity_id, value
            FROM catalog_category_entity_varchar
            WHERE entity_id IN ({placeholders})
            AND attribute_id = %s
            AND store_id = 0
        """

        cursor.execute(query, cat_id_list + [cat_name_attr_id])
        category_names = {}
        for cat_id, name in cursor.fetchall():
            category_names[str(cat_id)] = name

        # Build final category paths (include full path from root)
        result = {}
        for product_id, paths in product_categories.items():
            category_paths = []
            for path in paths:
                category_ids = path.split('/')
                # Include all categories in path (including root catalog and store)
                names = [category_names.get(cat_id, '') for cat_id in category_ids if category_names.get(cat_id)]
                if names:
                    category_paths.append(' / '.join(names))

            if category_paths:
                result[product_id] = category_paths

        return result

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
            'restricted_class', 'created_at', 'updated_at'
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
        - catalog_product_entity_int (integer attributes - with option value decoding)
        - catalog_product_entity_decimal (price attributes)
        - catalog_product_entity_text (text attributes - with option value decoding for multiselect)
        - cataloginventory_stock_item (stock status)
        - eav_attribute_option_value (to decode option IDs to text values)
        """

        # Base query with proper option value JOINs
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

                -- Status (int) - decoded to text
                status_option.value as status,

                -- Visibility (int) - decoded to text
                visibility_option.value as visibility,

                -- Stock status
                stock.is_in_stock,
                stock.qty,

                -- Brand (int) - decoded to text
                brand_option.value as brand,

                -- Size (int) - decoded to text
                size_option.value as size,

                -- Color (int) - decoded to text
                color_option.value as color,

                -- Physical form (text multiselect) - raw value (decode in Python)
                physical_form_attr.value as physical_form,

                -- CAS number (int multiselect) - raw value (decode in Python)
                cas_attr.value as cas_number,

                -- Restricted class (text multiselect) - raw value (decode in Python)
                restricted_attr.value as restricted_class

            FROM catalog_product_entity e

            -- Join varchar attributes
            LEFT JOIN catalog_product_entity_varchar name_attr
                ON e.entity_id = name_attr.entity_id
                AND name_attr.attribute_id = {name_id}
                AND name_attr.store_id = 0

            LEFT JOIN catalog_product_entity_varchar url_attr
                ON e.entity_id = url_attr.entity_id
                AND url_attr.attribute_id = {url_key_id}
                AND url_attr.store_id = 0

            LEFT JOIN catalog_product_entity_varchar image_attr
                ON e.entity_id = image_attr.entity_id
                AND image_attr.attribute_id = {image_id}
                AND image_attr.store_id = 0

            -- Join text attributes
            LEFT JOIN catalog_product_entity_text desc_attr
                ON e.entity_id = desc_attr.entity_id
                AND desc_attr.attribute_id = {description_id}
                AND desc_attr.store_id = 0

            LEFT JOIN catalog_product_entity_text short_desc_attr
                ON e.entity_id = short_desc_attr.entity_id
                AND short_desc_attr.attribute_id = {short_description_id}
                AND short_desc_attr.store_id = 0

            LEFT JOIN catalog_product_entity_text physical_form_attr
                ON e.entity_id = physical_form_attr.entity_id
                AND physical_form_attr.attribute_id = {physical_form_id}
                AND physical_form_attr.store_id = 0

            LEFT JOIN catalog_product_entity_text restricted_attr
                ON e.entity_id = restricted_attr.entity_id
                AND restricted_attr.attribute_id = {restricted_class_id}
                AND restricted_attr.store_id = 0

            -- Join decimal attributes
            LEFT JOIN catalog_product_entity_decimal price_attr
                ON e.entity_id = price_attr.entity_id
                AND price_attr.attribute_id = {price_id}
                AND price_attr.store_id = 0

            LEFT JOIN catalog_product_entity_decimal special_price_attr
                ON e.entity_id = special_price_attr.entity_id
                AND special_price_attr.attribute_id = {special_price_id}
                AND special_price_attr.store_id = 0

            LEFT JOIN catalog_product_entity_decimal weight_attr
                ON e.entity_id = weight_attr.entity_id
                AND weight_attr.attribute_id = {weight_id}
                AND weight_attr.store_id = 0

            -- Join int attributes with option value decoding
            -- Status
            LEFT JOIN catalog_product_entity_int status_attr
                ON e.entity_id = status_attr.entity_id
                AND status_attr.attribute_id = {status_id}
                AND status_attr.store_id = 0
            LEFT JOIN eav_attribute_option_value status_option
                ON status_attr.value = status_option.option_id
                AND status_option.store_id = 0

            -- Visibility
            LEFT JOIN catalog_product_entity_int visibility_attr
                ON e.entity_id = visibility_attr.entity_id
                AND visibility_attr.attribute_id = {visibility_id}
                AND visibility_attr.store_id = 0
            LEFT JOIN eav_attribute_option_value visibility_option
                ON visibility_attr.value = visibility_option.option_id
                AND visibility_option.store_id = 0

            -- Brand
            LEFT JOIN catalog_product_entity_int brand_attr
                ON e.entity_id = brand_attr.entity_id
                AND brand_attr.attribute_id = {brand_id}
                AND brand_attr.store_id = 0
            LEFT JOIN eav_attribute_option_value brand_option
                ON brand_attr.value = brand_option.option_id
                AND brand_option.store_id = 0

            -- Size
            LEFT JOIN catalog_product_entity_int size_attr
                ON e.entity_id = size_attr.entity_id
                AND size_attr.attribute_id = {size_id}
                AND size_attr.store_id = 0
            LEFT JOIN eav_attribute_option_value size_option
                ON size_attr.value = size_option.option_id
                AND size_option.store_id = 0

            -- Color
            LEFT JOIN catalog_product_entity_int color_attr
                ON e.entity_id = color_attr.entity_id
                AND color_attr.attribute_id = {color_id}
                AND color_attr.store_id = 0
            LEFT JOIN eav_attribute_option_value color_option
                ON color_attr.value = color_option.option_id
                AND color_option.store_id = 0

            -- CAS Number (multiselect int - will decode in Python)
            LEFT JOIN catalog_product_entity_int cas_attr
                ON e.entity_id = cas_attr.entity_id
                AND cas_attr.attribute_id = {cas_number_id}
                AND cas_attr.store_id = 0

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
            brand_id=attribute_ids.get('brand', {}).get('id', 0),
            size_id=attribute_ids.get('size', {}).get('id', 0),
            color_id=attribute_ids.get('color', {}).get('id', 0),
            physical_form_id=attribute_ids.get('physical_form', {}).get('id', 0),
            cas_number_id=attribute_ids.get('cas_number', {}).get('id', 0),
            restricted_class_id=attribute_ids.get('restricted_class', {}).get('id', 0),
        )

        if limit:
            query += f" LIMIT {limit}"

        return query

    def _decode_multiselect_options(self, cursor, option_ids_str: str, attribute_id: int) -> str:
        """
        Decode multiselect option IDs to text values.

        Multiselect attributes store option IDs as comma-separated text (e.g., "619,620,621").
        This method converts them to readable text (e.g., "Normal, FORENSIC USE ONLY").

        Args:
            cursor: MySQL cursor
            option_ids_str: Comma-separated option IDs (e.g., "619,620")
            attribute_id: Attribute ID for validation

        Returns:
            Comma-separated text values (e.g., "Normal, FORENSIC USE ONLY")
        """
        if not option_ids_str:
            return None

        # Split comma-separated IDs and clean
        option_ids = [opt_id.strip() for opt_id in str(option_ids_str).split(',') if opt_id.strip()]

        if not option_ids:
            return None

        # Build query to get option text values
        placeholders = ','.join(['%s'] * len(option_ids))
        query = f"""
            SELECT value
            FROM eav_attribute_option_value
            WHERE option_id IN ({placeholders})
            AND store_id = 0
        """

        cursor.execute(query, option_ids)
        text_values = [row[0] for row in cursor.fetchall() if row[0]]

        return ', '.join(text_values) if text_values else None

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

    def _calculate_brand_priority(self, sku: str, brand: str, product_name: str, categories: List[str]) -> int:
        """
        Calculate brand priority for sorting based on category and brand.

        Priority structure varies by category:

        **LCMS/HPLC Solvents** (detected by Grade: HPLC/LCMS in categories):
            100 - Concord Technologies
            90  - Birch Biotech
            80  - Mercedes Scientific
            70  - Tanner Scientific
            50  - Other brands
            0   - No brand

        **Drug Testing** (detected by "Drug Test" in categories):
            100 - Mercedes Scientific
            90  - AllTest
            80  - Tanner Scientific
            70  - Healgen
            60  - Wondfo
            50  - Other brands
            0   - No brand

        **General** (all other categories):
            100 - Mercedes Scientific
            90  - Tanner Scientific
            50  - Other brands
            0   - No brand

        Args:
            sku: Product SKU
            brand: Brand name from database
            product_name: Product name (used as fallback)
            categories: List of category paths

        Returns:
            Priority score (higher = more important)
        """
        # Detect category type
        category_type = self._detect_category_type(categories)

        # Use brand field (already available from Magento)
        brand_lower = (brand or "").lower().strip()
        name_lower = (product_name or "").lower().strip()

        # Fallback: check product name if brand not available
        detected_brand = brand_lower
        if not detected_brand:
            if "mercedes scientific" in name_lower:
                detected_brand = "mercedes scientific"
            elif "tanner scientific" in name_lower:
                detected_brand = "tanner scientific"
            elif "concord" in name_lower:
                detected_brand = "concord technologies"
            elif "birch" in name_lower and "biotech" in name_lower:
                detected_brand = "birch biotech"
            elif "alltest" in name_lower:
                detected_brand = "alltest"
            elif "healgen" in name_lower:
                detected_brand = "healgen"
            elif "wondfo" in name_lower:
                detected_brand = "wondfo"

        if not detected_brand:
            return 0

        # LCMS/HPLC Solvents category
        if category_type == "lcms_hplc":
            if "concord" in detected_brand:
                return 100
            elif "birch" in detected_brand:
                return 90
            elif "mercedes scientific" in detected_brand:
                return 80
            elif "tanner scientific" in detected_brand:
                return 70
            else:
                return 50

        # Drug Testing category
        elif category_type == "drug_testing":
            if "mercedes scientific" in detected_brand:
                return 100
            elif "alltest" in detected_brand:
                return 90
            elif "tanner scientific" in detected_brand:
                return 80
            elif "healgen" in detected_brand:
                return 70
            elif "wondfo" in detected_brand:
                return 60
            else:
                return 50

        # General (all other categories)
        else:
            if "mercedes scientific" in detected_brand:
                return 100
            elif "tanner scientific" in detected_brand:
                return 90
            else:
                return 50 if detected_brand else 0

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags."""
        import re
        if not html:
            return ""
        clean = re.sub('<[^<]+?>', '', html)
        clean = clean.strip()
        return clean[:500] if len(clean) > 500 else clean

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
            cleaned_cat = cleaned_cat.replace("Default Category / ", "")
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

    def _decode_multiselect_from_dict(self, option_ids_str: str, option_values: Dict[str, str]) -> str:
        """
        Decode multiselect option IDs to text values using pre-loaded dictionary.

        Args:
            option_ids_str: Comma-separated option IDs (e.g., "619,620")
            option_values: Pre-loaded dictionary mapping option_id -> text value

        Returns:
            Comma-separated text values (e.g., "Normal, FORENSIC USE ONLY")
        """
        if not option_ids_str:
            return None

        # Split comma-separated IDs and clean
        option_ids = [opt_id.strip() for opt_id in str(option_ids_str).split(',') if opt_id.strip()]

        if not option_ids:
            return None

        # Lookup text values from pre-loaded dictionary
        text_values = [option_values.get(opt_id) for opt_id in option_ids if option_values.get(opt_id)]

        return ', '.join(text_values) if text_values else None

    def _transform_magento_product(self, row, attribute_ids: Dict[str, int],
                                   option_values: Dict[str, str],
                                   all_categories: Dict[int, List[str]]) -> Dict[str, Any]:
        """Transform Magento database row to Typesense document using pre-loaded data."""
        try:
            (entity_id, sku, type_id, created_at, updated_at,
             name, url_key, description, short_description,
             price, special_price, image, weight, status, visibility,
             is_in_stock, qty, brand, size, color, physical_form, cas_number, restricted_class) = row

            # Decode multiselect options using pre-loaded option_values dictionary
            # This eliminates N+1 queries - all option values were loaded in a single query
            cas_number_decoded = self._decode_multiselect_from_dict(cas_number, option_values)
            physical_form_decoded = self._decode_multiselect_from_dict(physical_form, option_values)
            restricted_class_decoded = self._decode_multiselect_from_dict(restricted_class, option_values)

            # Fetch categories from pre-loaded dictionary and clean them
            # This eliminates N+1 queries - all categories were loaded in batch queries
            raw_categories = all_categories.get(entity_id, [])
            categories = self._clean_and_deduplicate_categories(raw_categories)

            # Stock status - prioritize qty over is_in_stock flag
            # If qty > 0, product should be IN_STOCK (source of truth is inventory qty)
            # Fall back to is_in_stock flag if qty is 0/None (trust Magento's logic)
            if qty and qty > 0:
                stock_status = "IN_STOCK"
            elif is_in_stock == 1:
                stock_status = "IN_STOCK"  # Trust Magento if no qty info
            else:
                stock_status = "OUT_OF_STOCK"

            # Image URL (remove cache-busting suffix from filename)
            image_url = None
            if image and image != 'no_selection':
                # Remove cache-busting suffix (e.g., _p6kzqxuyof13syl4 before extension)
                # Pattern: /path/filename_randomchars.ext -> /path/filename.ext
                import re
                clean_image = re.sub(r'_[a-z0-9]{16}(\.[a-zA-Z]+)$', r'\1', image)
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

            # Brand priority (category-aware)
            brand_priority = self._calculate_brand_priority(sku, brand, name, categories)

            # In-stock priority for sorting (in-stock products appear first)
            in_stock_priority = 1 if stock_status == "IN_STOCK" else 0

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
                "categories": categories,  # Now actually fetching categories!
                "brand": brand,
                "brand_priority": brand_priority,
                "size": size,
                "color": color,
                "physical_form": physical_form_decoded,  # Decoded from option IDs
                "cas_number": cas_number_decoded,  # Decoded from option IDs
                "qty": float(qty) if qty else None,
                "weight": float(weight) if weight else None,
                "created_at": created_ts,
                "updated_at": updated_ts,
                "restricted_class": restricted_class_decoded,  # Decoded from option IDs
            }

        except Exception as e:
            print(f"  ⚠ Error transforming product {row[1] if len(row) > 1 else 'unknown'}: {e}")
            import traceback
            traceback.print_exc()
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
