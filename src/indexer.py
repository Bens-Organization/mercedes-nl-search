"""Script to index Mercedes products into Typesense."""
import json
import requests
import typesense
from typing import List, Dict, Any
from config import Config
from models import Product

# Validate configuration
Config.validate()


class MercedesProductIndexer:
    """Index Mercedes Scientific products to Typesense."""

    def __init__(self):
        """Initialize indexer."""
        self.client = typesense.Client(Config.get_typesense_config())
        self.collection_name = Config.TYPESENSE_COLLECTION_NAME
        self.graphql_url = Config.MERCEDES_GRAPHQL_URL

    def create_collection(self):
        """Create Typesense collection with schema."""
        schema = {
            "name": self.collection_name,
            "fields": [
                {"name": "product_id", "type": "int32"},
                {"name": "uid", "type": "string"},
                {"name": "name", "type": "string", "sort": True},
                {"name": "sku", "type": "string"},
                {"name": "url_key", "type": "string"},
                {"name": "stock_status", "type": "string", "facet": True},
                {"name": "type_id", "type": "string", "facet": True},
                {"name": "description", "type": "string", "optional": True},
                {"name": "short_description", "type": "string", "optional": True},
                {"name": "price", "type": "float", "optional": True, "facet": True},
                {"name": "currency", "type": "string"},
                {"name": "image_url", "type": "string", "optional": True},
                {"name": "categories", "type": "string[]", "facet": True},
                {"name": "category_ids", "type": "int32[]", "facet": True},
                # Embedding field for semantic search
                {
                    "name": "embedding",
                    "type": "float[]",
                    "embed": {
                        "from": ["name", "description", "short_description", "categories"],
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
                self.client.collections[self.collection_name].delete()
                print(f"✓ Deleted existing collection: {self.collection_name}")
            except Exception:
                pass

            # Create new collection
            self.client.collections.create(schema)
            print(f"✓ Created collection: {self.collection_name}")

        except Exception as e:
            print(f"✗ Error creating collection: {e}")
            raise

    def _get_search_terms(self) -> List[str]:
        """
        Generate search terms from actual Mercedes Scientific categories.

        The Mercedes API limits results to 500 products per query,
        but different search terms return different products.
        We use category names and key product types for maximum coverage.
        """
        terms = []

        # Real product categories from Mercedes Scientific
        # Source: GraphQL categoryList query
        # These are the actual category names with verified product counts
        real_categories = [
            # Main product categories (33 categories, 23,571 products total)
            'absorbent sheets', 'pads', 'mats',
            'bags',
            'blades', 'handles',
            'calibrators', 'controls',
            'chemicals', 'stains',
            'cleaners',
            'deep well plates', 'accessories',
            'drug tests',
            'embedding', 'cryotomy', 'grossing',
            'equipment',
            'filtration',
            'furniture',
            'glass', 'plasticware',
            'gloves', 'apparel',  # 380 products
            'labels', 'labeling tape',
            'laboratory essentials',
            'medsurg', 'exam room supplies',
            'microscope slides', 'coverslips', 'control slides',  # 508 products
            'needles', 'syringes',
            'pens', 'pencils', 'markers',
            'phlebotomy supplies',
            'pipettes', 'pipettors', 'tips',  # 1,024 products
            'rapid diagnostic testing',
            'reagents',  # 5,083 products - largest category
            'safety',
            'scales', 'weighing',
            'specimen collection',
            'standards',
            'storage',
            'surgical instruments',  # 896 products
            'sutures', 'suture removal',
            'thermometers', 'meters',

            # Lab types (helps find specialized products)
            'cannabis lab',
            'chemistry',
            'chromatography',
            'drug testing', 'screening',
            'general lab',
            'hematology',
            'histology', 'cytology',
            'immunoassay',
            'medical', 'surgical',
            'microbiology',
            'serology',
            'toxicology',
            'urinalysis',
            'veterinary',
        ]

        terms.extend(real_categories)

        # Add single high-value words from category names
        # These catch products that don't match full category names
        key_words = [
            'gloves', 'pipette', 'slide', 'reagent', 'tube', 'syringe',
            'needle', 'surgical', 'sterile', 'diagnostic', 'test', 'kit',
            'microscope', 'blade', 'stain', 'specimen', 'culture',
            'filter', 'bottle', 'vial', 'plate', 'rack', 'tip'
        ]

        terms.extend(key_words)

        return terms

    def fetch_products(self, page_size: int = 100, max_products: int = None) -> List[Dict[str, Any]]:
        """
        Fetch products from Mercedes GraphQL API using multi-search strategy.

        Note: The API limits results to 500 products per query, so we use
        multiple search terms to collect unique products across different queries.
        """
        all_products = {}  # Use dict to track unique products by SKU
        search_terms = self._get_search_terms()

        print(f"\nFetching products from {self.graphql_url}...")
        print(f"Strategy: Multi-search to bypass API's 500-product limit")
        print(f"Search terms: {len(search_terms)} different queries")
        if max_products:
            print(f"Limit: First {max_products:,} products")
        print()

        for term_idx, search_term in enumerate(search_terms, 1):
            if max_products and len(all_products) >= max_products:
                break

            # Fetch products for this search term
            term_products = self._fetch_products_for_search(
                search_term,
                page_size=page_size,
                max_products=max_products - len(all_products) if max_products else None
            )

            # Add unique products (by SKU)
            before_count = len(all_products)
            for product in term_products:
                sku = product.get("sku")
                if sku and sku not in all_products:
                    all_products[sku] = product

            new_count = len(all_products) - before_count

            print(f"  [{term_idx:3d}/{len(search_terms)}] Search '{search_term:15s}': "
                  f"{len(term_products):3d} products, {new_count:3d} new unique "
                  f"(Total: {len(all_products):,})")

        print(f"\n{'='*60}")
        print(f"✓ Total unique products collected: {len(all_products):,}")
        print(f"✓ Used {term_idx} search terms")
        print(f"{'='*60}")

        return list(all_products.values())

    def _fetch_products_for_search(
        self,
        search_term: str,
        page_size: int = 100,
        max_products: int = None
    ) -> List[Dict[str, Any]]:
        """Fetch products for a single search term."""
        products = []
        current_page = 1
        total_fetched = 0

        while True:
            # GraphQL query with search term
            query = """
            {
              products(
                search: "%s"
                pageSize: %d
                currentPage: %d
              ) {
                total_count
                items {
                  id
                  uid
                  name
                  sku
                  url_key
                  stock_status
                  type_id
                  description {
                    html
                  }
                  short_description {
                    html
                  }
                  price_range {
                    minimum_price {
                      regular_price {
                        value
                        currency
                      }
                    }
                  }
                  image {
                    url
                    label
                  }
                  categories {
                    id
                    name
                    url_path
                  }
                }
                page_info {
                  current_page
                  total_pages
                }
              }
            }
            """ % (search_term, page_size, current_page)

            try:
                response = requests.post(
                    self.graphql_url,
                    json={"query": query},
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    # Silently skip errors for individual search terms
                    break

                product_data = data.get("data", {}).get("products", {})
                items = product_data.get("items", [])
                page_info = product_data.get("page_info", {})
                total_count = product_data.get("total_count", 0)

                if not items:
                    break

                # Transform products
                for item in items:
                    product = self._transform_product(item)
                    products.append(product)
                    total_fetched += 1

                    if max_products and total_fetched >= max_products:
                        break

                if max_products and total_fetched >= max_products:
                    break

                # For multi-search, we typically only need first page per term
                # to maximize variety. Fetching all pages would be redundant.
                if current_page >= min(page_info.get("total_pages", 1), 5):
                    break

                current_page += 1

            except Exception as e:
                # Silently skip errors for individual search terms
                break

        return products

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

    def _transform_product(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Transform GraphQL product to Typesense document."""
        # Extract price
        price = None
        currency = "USD"
        price_range = item.get("price_range", {}).get("minimum_price", {})
        regular_price = price_range.get("regular_price", {})
        if regular_price:
            price = regular_price.get("value")
            currency = regular_price.get("currency", "USD")

        # Extract image URL
        image_url = None
        image = item.get("image", {})
        if image:
            image_url = image.get("url")

        # Extract and clean categories
        raw_categories = [cat.get("name", "") for cat in item.get("categories", [])]
        category_ids = [cat.get("id") for cat in item.get("categories", [])]

        # Clean and deduplicate categories
        categories = self._clean_and_deduplicate_categories(raw_categories)

        # Clean HTML from descriptions
        description = self._clean_html(item.get("description", {}).get("html", ""))
        short_description = self._clean_html(item.get("short_description", {}).get("html", ""))

        return {
            "product_id": item.get("id"),
            "uid": item.get("uid", ""),
            "name": item.get("name", ""),
            "sku": item.get("sku", ""),
            "url_key": item.get("url_key", ""),
            "stock_status": item.get("stock_status", "OUT_OF_STOCK"),
            "type_id": item.get("type_id", "simple"),
            "description": description if description else None,
            "short_description": short_description if short_description else None,
            "price": price,
            "currency": currency,
            "image_url": image_url,
            "categories": categories,
            "category_ids": category_ids,
        }

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
                result = self.client.collections[self.collection_name].documents.import_(
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
        print("Mercedes Scientific Product Indexer")
        print("=" * 60)

        if max_products:
            print(f"Mode: Testing (indexing first {max_products:,} products)")
        else:
            print(f"Mode: Full indexing (all products)")

        print(f"Embedding Model: {Config.OPENAI_EMBEDDING_MODEL}")
        print(f"Collection: {self.collection_name}")
        print("=" * 60)

        # Check if NL search model is configured
        self._check_nl_model()

        try:
            # Create collection
            self.create_collection()

            # Fetch products
            products = self.fetch_products(page_size=100, max_products=max_products)

            if not products:
                print("✗ No products to index")
                return

            # Index products (with embeddings)
            print(f"\n{'='*60}")
            print(f"Starting indexing with auto-embeddings...")
            print(f"This may take 15-30 minutes for full catalog")
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

    indexer = MercedesProductIndexer()

    # Index all ~27k products
    # To test with limited products, use: indexer.run(max_products=1000)
    indexer.run()

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
