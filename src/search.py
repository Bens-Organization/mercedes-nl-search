"""Natural language search using Typesense native NL search."""
import time
import typesense
from typing import Dict, Any, List
from config import Config
from models import SearchResponse, Product

# Validate configuration
Config.validate()


class NaturalLanguageSearch:
    """Natural language search engine using Typesense native NL search."""

    def __init__(self):
        """Initialize search engine."""
        self.typesense_client = typesense.Client(Config.get_typesense_config())
        self.collection_name = Config.TYPESENSE_COLLECTION_NAME
        # Use the registered NL model ID
        self.nl_model_id = "openai-gpt4o-mini"

    def search(self, query: str, max_results: int = 20, debug: bool = False,
               confidence_threshold: float = 0.80) -> SearchResponse:
        """
        Search products using natural language via Typesense native NL search.

        Args:
            query: Natural language search query
            max_results: Maximum number of results to return
            debug: Enable debug mode to see LLM reasoning
            confidence_threshold: Minimum confidence score to apply category filter (0-1, default: 0.80)

        Returns:
            SearchResponse with results and metadata
        """
        start_time = time.time()

        # Check if query contains explicit limit (e.g., "5 most expensive", "top 10")
        extracted_limit = self._extract_limit_from_query(query)
        if extracted_limit:
            max_results = extracted_limit

        # Execute primary search using Typesense native NL search
        results = self._execute_nl_search(query, max_results, debug)

        # Transform results
        products = self._transform_results(results.get("hits", []))

        # Extract the actual Typesense query used (from parsed_nl_query)
        typesense_query = {
            "original_query": query,
            "nl_query": True,
            "nl_model_id": self.nl_model_id,
            "max_results": max_results,  # Show the limit used (may be extracted from query)
        }

        # Extract parsed query info if available
        if "parsed_nl_query" in results:
            typesense_query["parsed"] = results["parsed_nl_query"]["generated_params"]

        # Extract category from filter_by if LLM detected it
        detected_category = None
        category_confidence = 0.0
        category_applied = False
        primary_results = products
        additional_results = None

        if "parsed_nl_query" in results and "generated_params" in results["parsed_nl_query"]:
            filter_by = results["parsed_nl_query"]["generated_params"].get("filter_by", "")
            if filter_by and "categories:=" in filter_by:
                # Extract category from filter
                detected_category = self._extract_category_from_filter(filter_by)

                if detected_category:
                    # Calculate confidence based on result match
                    category_confidence = self._calculate_category_confidence(products, detected_category)
                    category_applied = True

                    # If confidence is below threshold, get additional results without category filter
                    if category_confidence < confidence_threshold and products:
                        # Get non-category filters
                        other_filters = self._remove_category_filter(filter_by)

                        # Search without category to find related products
                        all_results = self._search_without_category(query, max_results, other_filters)

                        # Split results: primary (matching category) vs additional (other categories)
                        primary_results = [p for p in all_results if self._product_matches_category(p, detected_category)]
                        additional_results = [p for p in all_results if not self._product_matches_category(p, detected_category)]

                        # Limit additional results
                        additional_results = additional_results[:max_results] if additional_results else None

        query_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            results=products,  # Keep all results for backwards compatibility
            primary_results=primary_results,
            additional_results=additional_results if additional_results else None,
            detected_category=detected_category,
            category_confidence=category_confidence,
            category_applied=category_applied,
            confidence_threshold=confidence_threshold,
            total=results.get("found", 0),
            query_time_ms=query_time_ms,
            typesense_query=typesense_query
        )

    def _extract_limit_from_query(self, query: str) -> int:
        """
        Extract result limit from query if explicitly mentioned.

        Examples:
        - "5 most expensive" → 5
        - "top 10 reagents" → 10
        - "first 3 gloves" → 3

        Args:
            query: Natural language query

        Returns:
            Extracted limit or None if not found
        """
        import re

        # Pattern: number followed by superlatives/keywords
        patterns = [
            r'^(\d+)\s+(?:most|least|top|best|worst|cheapest|expensive)',  # "5 most expensive"
            r'top\s+(\d+)',  # "top 10"
            r'first\s+(\d+)',  # "first 3"
            r'^(\d+)\s+\w+',  # "5 gloves" (number at start)
        ]

        query_lower = query.lower().strip()

        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                limit = int(match.group(1))
                # Sanity check: limit between 1 and 100
                if 1 <= limit <= 100:
                    return limit

        return None

    def _execute_nl_search(self, query: str, max_results: int, debug: bool = False) -> Dict[str, Any]:
        """
        Execute natural language search using Typesense native NL search.

        Args:
            query: Natural language query
            max_results: Maximum results to return (default, can be overridden by NL extraction)
            debug: Enable debug mode

        Returns:
            Search results from Typesense
        """
        search_params = {
            "q": query,
            "query_by": "name,description,short_description,sku,categories",
            "nl_query": "true",  # Enable native NL search
            "nl_model_id": self.nl_model_id,
            "per_page": max_results,  # Default, will be overridden if NL query extracts a limit
            "sort_by": "_text_match:desc,price:asc",  # Default sort, will be overridden if NL query extracts sort
        }

        # Note: vector_query interferes with NL search's filter extraction
        # Typesense will automatically use embeddings when nl_query=true
        # So we DON'T need to manually add vector_query here

        # Always enable debug mode to see how LLM interprets the query
        search_params["nl_query_debug"] = "true"

        try:
            results = self.typesense_client.collections[self.collection_name].documents.search(
                search_params
            )

            # Debug: Print what Typesense actually returned
            print(f"\n=== Typesense Response Debug ===")
            print(f"Search parameters in response: {results.get('search_parameters', {})}")
            if 'request_params' in results:
                print(f"Request params: {results['request_params']}")
            if 'parsed_nl_query' in results:
                print(f"Parsed NL query: {results['parsed_nl_query']}")
            print(f"================================\n")

            return results

        except typesense.exceptions.RequestUnauthorized:
            print("Error: Typesense authentication failed")
            raise Exception("Search service authentication failed")
        except typesense.exceptions.HTTPStatus0Error as e:
            print(f"Error: Cannot connect to Typesense: {e}")
            raise Exception("Search service is temporarily unavailable")
        except typesense.exceptions.ServiceUnavailable as e:
            print(f"Error: Typesense service unavailable: {e}")
            raise Exception("Search service is temporarily unavailable")
        except typesense.exceptions.ServerError as e:
            print(f"Error: Typesense server error: {e}")
            raise Exception("Search service is temporarily unavailable")
        except typesense.exceptions.TypesenseClientError as e:
            print(f"Error: Typesense client error: {e}")
            raise Exception(f"Search service error: {str(e)}")
        except Exception as e:
            print(f"Error executing Typesense NL search: {e}")

            # Fallback to keyword-only search without NL
            try:
                fallback_params = {
                    "q": query,
                    "query_by": "name,description,short_description,sku,categories",
                    "per_page": max_results,
                }
                results = self.typesense_client.collections[self.collection_name].documents.search(
                    fallback_params
                )
                print("  Fallback: Using keyword-only search (NL search failed)")
                return results
            except typesense.exceptions.HTTPStatus0Error as e2:
                print(f"Error in fallback search - connection failed: {e2}")
                raise Exception("Search service is temporarily unavailable")
            except typesense.exceptions.ServiceUnavailable as e2:
                print(f"Error in fallback search - service unavailable: {e2}")
                raise Exception("Search service is temporarily unavailable")
            except Exception as e2:
                print(f"Error in fallback search: {e2}")
                raise Exception("Search service is temporarily unavailable")

    def _transform_results(self, hits: List[Dict[str, Any]]) -> List[Product]:
        """
        Transform Typesense hits to Product models.

        Args:
            hits: Search hits from Typesense

        Returns:
            List of Product models
        """
        products = []

        for hit in hits:
            doc = hit.get("document", {})

            try:
                product = Product(
                    product_id=doc.get("product_id"),
                    sku=doc.get("sku", ""),
                    name=doc.get("name", ""),
                    url_key=doc.get("url_key", ""),
                    stock_status=doc.get("stock_status", "OUT_OF_STOCK"),
                    product_type=doc.get("product_type", "simple"),
                    description=doc.get("description"),
                    short_description=doc.get("short_description"),
                    price=doc.get("price"),
                    currency=doc.get("currency", "USD"),
                    image_url=doc.get("image_url"),
                    categories=doc.get("categories", []),
                )
                products.append(product)

            except Exception as e:
                print(f"Error transforming product: {e}")
                continue

        return products

    def _extract_category_from_filter(self, filter_by: str) -> str:
        """
        Extract category value from filter_by string.

        Args:
            filter_by: Filter string (e.g., "categories:=Gloves" or "categories:=[Gloves] && price:<50")

        Returns:
            Category name (e.g., "Gloves")
        """
        import re

        # Match patterns like "categories:=Value" or "categories:=[Value, ...]"
        # Stop at && or ) or ] to avoid capturing other filters
        match = re.search(r'categories:=\[?([^\],\)&]+)', filter_by)
        if match:
            category = match.group(1).strip()
            # Remove trailing whitespace and special characters
            category = category.rstrip(' &')
            return category

        return None

    def _product_matches_category(self, product: Product, category: str) -> bool:
        """
        Check if a product matches the detected category.

        Args:
            product: Product to check
            category: Category to match against

        Returns:
            True if product has this category (or contains it as a prefix)
        """
        if not product.categories:
            return False

        # Case-insensitive match - check if detected category is contained in any product category
        category_lower = category.lower()
        return any(category_lower in cat.lower() for cat in product.categories)

    def _remove_category_filter(self, filter_by: str) -> str:
        """
        Remove category filter from filter_by string.

        Args:
            filter_by: Filter string (e.g., "categories:=Gloves && price:<50")

        Returns:
            Filter string without category (e.g., "price:<50")
        """
        # Split by " && " to get individual filter parts
        # Note: using " && " (with spaces) to avoid splitting category values that contain "&"
        filters = filter_by.split(' && ')

        # Keep only filters that don't start with "categories"
        remaining_filters = [f for f in filters if not f.strip().startswith('categories')]

        # Rejoin with " && "
        result = ' && '.join(remaining_filters).strip()

        return result if result else ""

    def _calculate_category_confidence(self, products: List[Product], detected_category: str) -> float:
        """
        Calculate confidence score for detected category based on search results.

        Confidence Score Scale (0.0 - 1.0):
        - 0.8-1.0: Very High - Clear, explicit, unambiguous category match (80-100% of results match)
        - 0.6-0.8: High - Strong evidence, minor ambiguity possible (60-80% of results match)
        - 0.4-0.6: Moderate - Partial evidence, some uncertainty remains (40-60% of results match)
        - 0.2-0.4: Low - Weak inference, ambiguous or conflicting indicators (20-40% match)
        - 0.0-0.2: Very Low - Pure guess, no supporting evidence found (0-20% match)

        Args:
            products: List of product results
            detected_category: Category detected from query

        Returns:
            Confidence score (0-1) based on percentage of results matching the category
        """
        if not detected_category or not products:
            return 0.0

        # Count how many products match the detected category
        matching_count = sum(1 for product in products
                            if self._product_matches_category(product, detected_category))

        # Calculate confidence as ratio of matching products
        confidence = matching_count / len(products) if products else 0.0

        return round(confidence, 2)

    def _search_without_category(self, query: str, max_results: int, filter_by: str) -> List[Product]:
        """
        Execute search without category filter to find related products.

        Args:
            query: Original search query
            max_results: Maximum results to return
            filter_by: Filter without category (e.g., "price:<50")

        Returns:
            List of products from other categories
        """
        try:
            search_params = {
                "q": query,
                "query_by": "name,description,short_description,sku,categories",
                "per_page": max_results,
            }

            # Add non-category filters if they exist
            if filter_by:
                search_params["filter_by"] = filter_by

            results = self.typesense_client.collections[self.collection_name].documents.search(
                search_params
            )

            return self._transform_results(results.get("hits", []))

        except typesense.exceptions.RequestUnauthorized:
            print("Error: Typesense authentication failed in search without category")
            raise Exception("Search service authentication failed")
        except typesense.exceptions.HTTPStatus0Error as e:
            print(f"Error: Connection failed in search without category: {e}")
            raise Exception("Search service is temporarily unavailable")
        except typesense.exceptions.ServiceUnavailable as e:
            print(f"Error: Service unavailable in search without category: {e}")
            raise Exception("Search service is temporarily unavailable")
        except typesense.exceptions.ServerError as e:
            print(f"Error: Typesense server error in search without category: {e}")
            raise Exception("Search service is temporarily unavailable")
        except Exception as e:
            print(f"Error in search without category: {e}")
            # For additional results, we can return empty list as it's not critical
            return []


if __name__ == "__main__":
    # Test the search
    import json

    search_engine = NaturalLanguageSearch()

    test_queries = [
        "gloves under $50",
        "pipettes in stock between $100 and $500",
        "microscope slides",
        "sterile surgical instruments under $200",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)

        # Run with debug mode to see LLM reasoning
        response = search_engine.search(query, max_results=5, debug=True)

        print(f"\nTypesense Query: {json.dumps(response.typesense_query, indent=2)}")
        print(f"Total Results: {response.total}")
        print(f"Query Time: {response.query_time_ms:.2f}ms")

        print(f"\nTop {len(response.results)} Results:")
        for i, product in enumerate(response.results, 1):
            print(f"\n{i}. {product.name}")
            print(f"   SKU: {product.sku}")
            print(f"   Price: ${product.price:.2f}" if product.price else "   Price: N/A")
            print(f"   Stock: {product.stock_status}")
            if product.categories:
                print(f"   Categories: {', '.join(product.categories[:3])}")
