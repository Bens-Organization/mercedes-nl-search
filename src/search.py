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
from typing import List, Dict, Any
from config import Config
from models import SearchResponse, Product
import time


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

    async def search(
        self,
        query: str,
        max_results: int = 20,
        debug: bool = False
    ) -> SearchResponse:
        """
        Execute natural language search using Typesense NL integration.

        Args:
            query: User's natural language query
            max_results: Maximum number of results to return
            debug: Enable debug mode (shows NL processing details)

        Returns:
            SearchResponse with products and metadata
        """
        start_time = time.time()

        # Typesense NL search parameters
        search_params = {
            "q": query,
            "query_by": "name,sku,name_normalized,sku_normalized,description,short_description,categories",
            "query_by_weights": "100,100,4,4,3,3,1",
            "per_page": max_results,
            "nl_query": True,  # Enable natural language processing
            "nl_model_id": "middleware-rag-vllm",  # Use our vLLM middleware model
            "prefix": "true,true,true,true,false,false,false",
            "num_typos": 2,
            "typo_tokens_threshold": 1,
            "drop_tokens_threshold": 2,
            # Note: sort_by is handled by middleware to avoid conflicts
        }

        # Add debug mode if enabled
        if debug:
            search_params["nl_query_debug"] = True

        print(f"[Typesense NL] Searching with query: '{query}'")
        print(f"[Typesense NL] NL Model: middleware-rag-vllm")
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

        # Transform results
        products = self._transform_results(result.get('hits', []))
        total_found = result.get('found', 0)

        # Build response metadata
        typesense_query = {
            "approach": "typesense_nl",
            "original_query": query,
            "nl_model_id": "middleware-rag-vllm",
            "middleware_url": "https://web-production-a5d93.up.railway.app",
            "results_found": total_found,
            "results_returned": len(products),
        }

        # Always include middleware-extracted parameters (not just in debug mode)
        if "request_params" in result:
            typesense_query["extracted_query"] = result.get("request_params", {}).get("q")
            typesense_query["filters_applied"] = result.get("request_params", {}).get("filter_by", "")
            typesense_query["sort_applied"] = result.get("request_params", {}).get("sort_by")

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
                uid=doc.get('uid', ''),
                name=doc.get('name', ''),
                sku=doc.get('sku', ''),
                url_key=doc.get('url_key', ''),
                stock_status=doc.get('stock_status', ''),
                product_type=doc.get('type_id', ''),
                description=doc.get('description'),
                short_description=doc.get('short_description'),
                price=doc.get('price'),
                currency=doc.get('currency', 'USD'),
                image_url=doc.get('image_url'),
                categories=doc.get('categories', []),
                category_ids=doc.get('category_ids', [])
            )

            products.append(product)

        return products
