"""
Natural Language Search Implementation

This module provides search functionality using Typesense's native NL integration.
The search flow leverages middleware for RAG-based category classification.

Architecture:
    API → Typesense (nl_query=true) → Middleware (RAG classification) → Results

How it works:
    1. API calls Typesense with nl_query=true
    2. Typesense calls middleware for query processing
    3. Middleware performs RAG category classification
    4. Middleware returns search parameters (q, filter_by with category)
    5. Typesense executes search and returns results
"""

import typesense
from typing import List, Dict, Any, Optional, Tuple
from config import Config
from models import SearchResponse, Product
import time
import re


class Search:
    """Search implementation using Typesense NL integration."""

    def __init__(self):
        """Initialize Typesense client."""
        self.typesense_client = typesense.Client({
            'api_key': Config.TYPESENSE_API_KEY,
            'nodes': [{
                'host': Config.TYPESENSE_HOST,
                'port': Config.TYPESENSE_PORT,
                'protocol': Config.TYPESENSE_PROTOCOL
            }],
            'connection_timeout_seconds': 30  # Longer timeout for NL queries
        })
        self.collection_name = Config.TYPESENSE_COLLECTION_NAME

    def _detect_size_pattern(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Detect size pattern in query (e.g., "22x22", "24 x 60").

        Returns:
            Tuple of (width, height) if size detected, None otherwise
        """
        # Pattern: NNxNN or NN x NN (with optional mm/cm)
        pattern = r'\b(\d{1,3})\s*[xX×]\s*(\d{1,3})\s*(mm|cm)?\b'
        match = re.search(pattern, query)
        if match:
            return (match.group(1), match.group(2))
        return None

    def _product_matches_size(self, product: Dict[str, Any], width: str, height: str) -> bool:
        """
        Check if product matches the detected size.

        Checks in: size field, name, and short_description
        Handles formats: "22x22", "22 x 22", "22x22mm", "22 x 22mm"
        """
        # Generate all possible size format variations
        size_variations = [
            f"{width}x{height}",
            f"{width} x {height}",
            f"{width}x{height}mm",
            f"{width} x {height}mm",
        ]

        # Check size field
        product_size = product.get('size', '')
        if product_size:
            for variation in size_variations:
                if variation.lower() in product_size.lower():
                    return True

        # Check name
        product_name = product.get('name', '')
        if product_name:
            for variation in size_variations:
                if variation.lower() in product_name.lower():
                    return True

        # Check short_description
        product_desc = product.get('short_description', '')
        if product_desc:
            for variation in size_variations:
                if variation.lower() in product_desc.lower():
                    return True

        return False

    def _filter_by_size(self, products: List[Product], width: str, height: str) -> List[Product]:
        """
        Filter products to only those matching the detected size.

        Only filters if exact matches exist - otherwise returns all (fallback behavior).
        """
        # Convert Product objects to dicts for checking
        matching_products = []
        for product in products:
            # Check if product matches size
            product_dict = product.model_dump() if hasattr(product, 'model_dump') else product.__dict__
            if self._product_matches_size(product_dict, width, height):
                matching_products.append(product)

        # Only return filtered results if we found exact matches
        # Otherwise return all (user might be searching for non-existent size)
        if len(matching_products) > 0:
            return matching_products
        else:
            return products  # Fallback: show all results if no exact matches

    async def search(
        self,
        query: str,
        max_results: int = 20,
        debug: bool = False,
        restriction_filter: str = ""
    ) -> SearchResponse:
        """
        Execute natural language search using Typesense NL integration.

        Args:
            query: User's natural language query
            max_results: Maximum number of results to return
            debug: Enable debug mode (shows NL processing details)
            restriction_filter: Optional filter to exclude restricted items

        Returns:
            SearchResponse with products and metadata
        """
        start_time = time.time()

        # Detect size pattern early to adjust search parameters
        size_pattern = self._detect_size_pattern(query)

        # If size pattern detected, fetch more results from Typesense to ensure we get all matches
        # before filtering (since "22x22" vs "22 x 22" may rank differently)
        fetch_results = 100 if size_pattern else max_results

        # Typesense NL search parameters
        search_params = {
            "q": query,
            "query_by": "name,sku,size,name_normalized,sku_normalized,description,short_description,categories",
            "query_by_weights": "100,100,150,4,4,3,3,500",  # Boosted category weight to prioritize main products over accessories
            "text_match_type": "max_weight",  # Use highest weighted field's score (not just tie-breaker)
            "per_page": fetch_results,  # Fetch more if size pattern detected
            "nl_query": True,  # Enable natural language processing
            "nl_model_id": Config.NL_MODEL_ID,  # Use configured NL model (environment-specific)
            "prefix": "true,true,false,true,true,false,false,false",  # Disable prefix for size (exact match)
            "num_typos": 2,
            "typo_tokens_threshold": 1,
            "drop_tokens_threshold": 2,
            # Note: sort_by is handled by middleware to avoid conflicts
        }

        # Apply restriction filter if provided
        if restriction_filter:
            search_params["filter_by"] = restriction_filter

        # Add debug mode if enabled
        if debug:
            search_params["nl_query_debug"] = True

        print(f"[Typesense NL] Searching with query: '{query}'")
        print(f"[Typesense NL] NL Model: {Config.NL_MODEL_ID}")
        print(f"[Typesense NL] DEBUG - Search params: {search_params}")

        # Execute search
        result = self.typesense_client.collections[self.collection_name].documents.search(search_params)

        # DEBUG: Print full result to see what Typesense returned
        print(f"[Typesense NL] DEBUG - Full result keys: {list(result.keys())}")
        if 'request_params' in result:
            print(f"[Typesense NL] DEBUG - Request params from Typesense: {result['request_params']}")
        if 'parsed_nl_query' in result:
            print(f"[Typesense NL] DEBUG - Parsed NL query (what middleware returned): {result['parsed_nl_query']}")
        if 'nl_debug' in result:
            print(f"[Typesense NL] DEBUG - NL Debug info: {result['nl_debug']}")

        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000

        # Get raw hits
        hits = result.get('hits', [])
        total_found = result.get('found', 0)
        original_total_found = total_found  # Store original count for metadata

        # Filter by size if pattern was detected (size_pattern set earlier)
        size_filtered = False
        if size_pattern:
            width, height = size_pattern
            print(f"[Size Filter] Detected size pattern: {width}x{height}")
            original_count = len(hits)

            # Filter hits based on size
            matching_hits = []
            for hit in hits:
                doc = hit['document']
                if self._product_matches_size(doc, width, height):
                    matching_hits.append(hit)

            if len(matching_hits) > 0:
                hits = matching_hits
                size_filtered = True
                print(f"[Size Filter] Filtered from {original_count} to {len(hits)} products (exact size matches only)")
            else:
                print(f"[Size Filter] No exact matches found, showing all {original_count} results (fallback)")

        # Limit to max_results after filtering
        hits = hits[:max_results]

        # Transform filtered results to Product objects
        products = self._transform_results(hits)

        # Update total_found to reflect filtered count when size filtering is applied
        # This ensures the UI shows "Found 4 results" instead of "Found 63 results"
        if size_filtered:
            total_found = len(products)
            print(f"[Size Filter] Updated total from Typesense count to filtered count: {total_found}")

        # Build response metadata
        typesense_query = {
            "approach": "typesense_nl",
            "original_query": query,
            "nl_model_id": Config.NL_MODEL_ID,
            "middleware_url": Config.MIDDLEWARE_URL,
            "results_found": total_found,
            "results_returned": len(products),  # Updated count after size filtering
        }

        # Add size filtering info if applied
        if size_pattern:
            width, height = size_pattern
            typesense_query["size_detected"] = f"{width}x{height}"
            typesense_query["size_filtered"] = size_filtered
            if size_filtered:
                # Include original Typesense count for debugging
                typesense_query["typesense_total_found"] = original_total_found

        # Always include middleware-extracted parameters (not just in debug mode)
        # Read from parsed_nl_query.augmented_params (contains middleware-processed params)
        if "parsed_nl_query" in result and "augmented_params" in result["parsed_nl_query"]:
            augmented = result["parsed_nl_query"]["augmented_params"]
            typesense_query["extracted_query"] = augmented.get("q", query)
            typesense_query["filters_applied"] = augmented.get("filter_by", "")
            typesense_query["sort_applied"] = augmented.get("sort_by")
        else:
            # Fallback to original query if middleware didn't process it
            typesense_query["extracted_query"] = query
            typesense_query["filters_applied"] = ""
            typesense_query["sort_applied"] = None

        # Include additional debug info if requested
        if debug and "parsed_nl_query" in result:
            typesense_query["parsed_nl_query"] = result.get("parsed_nl_query")

        print(f"[Typesense NL] Found {total_found} results in {query_time_ms:.0f}ms")

        return SearchResponse(
            results=products,
            total=total_found,
            query_time_ms=query_time_ms,
            typesense_query=typesense_query
        )

    def _transform_results(self, hits: List[Dict[str, Any]]) -> List[Product]:
        """Transform Typesense hits into Product objects."""
        products = []

        for hit in hits:
            doc = hit['document']

            product = Product(
                product_id=doc.get('product_id', ''),
                name=doc.get('name', ''),
                sku=doc.get('sku', ''),
                url_key=doc.get('url_key', ''),
                stock_status=doc.get('stock_status', ''),
                product_type=doc.get('product_type', 'simple'),
                description=doc.get('description'),
                short_description=doc.get('short_description'),
                price=doc.get('price'),
                currency=doc.get('currency', 'USD'),
                image_url=doc.get('image_url'),
                categories=doc.get('categories', []),
                brand=doc.get('brand'),
                restricted_class=doc.get('restricted_class')
            )

            products.append(product)

        return products
