"""
Decoupled Middleware Search

This module implements the decoupled RAG architecture where:
1. API does retrieval search (gets product context)
2. API calls middleware directly with context
3. Middleware returns search params with category
4. API does final search with middleware params

This avoids circular dependency by NOT using Typesense's nl_search_models integration.

Flow:
    User → API → Typesense (retrieval) → API → Middleware → API → Typesense (final) → User
           ↑                              ↓                 ↓
           └──────────────────────────────┴─────────────────┘
           All orchestration happens in API layer
"""

import httpx
import json
from typing import List, Dict, Any, Optional
from src.config import Config
import typesense


class MiddlewareSearch:
    """
    Search engine that uses middleware for query translation with RAG context.

    Decoupled architecture where the API layer handles all orchestration
    to avoid circular dependency.
    """

    def __init__(self):
        """Initialize Typesense client and middleware URL."""
        self.typesense_client = typesense.Client({
            'api_key': Config.TYPESENSE_API_KEY,
            'nodes': [{
                'host': Config.TYPESENSE_HOST,
                'port': Config.TYPESENSE_PORT,
                'protocol': Config.TYPESENSE_PROTOCOL
            }],
            'connection_timeout_seconds': 60
        })

        # Middleware URL (Railway deployment)
        self.middleware_url = "https://web-production-a5d93.up.railway.app"
        self.collection_name = Config.TYPESENSE_COLLECTION_NAME

    async def search(
        self,
        query: str,
        max_results: int = 20,
        debug: bool = False,
        confidence_threshold: float = 0.75
    ) -> Dict[str, Any]:
        """
        Execute search using decoupled middleware architecture.

        Steps:
        1. Do retrieval search (no category filter)
        2. Extract context from results
        3. Call middleware with context
        4. Parse middleware response
        5. Do final search with middleware params
        6. Return results

        Args:
            query: User's natural language query
            max_results: Maximum number of results to return
            debug: Enable debug mode (show reasoning)
            confidence_threshold: Minimum confidence for category filter

        Returns:
            Dictionary with results and metadata
        """
        import time
        start_time = time.time()

        # Step 1: Retrieval search (get context)
        print(f"[Step 1] Retrieval search for: {query}")
        retrieval_results = self._retrieval_search(query, limit=20)

        # Step 2: Extract context from retrieval results
        print(f"[Step 2] Extract context from {len(retrieval_results)} products")
        context = self._extract_context(retrieval_results)

        # Step 3: Call middleware with context
        print(f"[Step 3] Call middleware with {len(context)} products in context")
        middleware_response = await self._call_middleware(query, context)

        # Step 4: Parse middleware response
        print(f"[Step 4] Parse middleware response")
        search_params = self._parse_middleware_response(middleware_response)

        # Extract category info for response
        detected_category = search_params.get("detected_category")
        category_confidence = search_params.get("category_confidence", 0.0)
        category_reasoning = search_params.get("category_reasoning", "")

        # Apply category if confident
        category_applied = False
        if detected_category and category_confidence >= confidence_threshold:
            filter_by = search_params.get("filter_by", "")
            if filter_by:
                filter_by += " && "
            filter_by += f"categories:={detected_category}"
            search_params["filter_by"] = filter_by
            category_applied = True

        # Step 5: Final search with middleware params
        print(f"[Step 5] Final search with params: {search_params}")
        final_results = self._final_search(search_params, max_results)

        query_time_ms = (time.time() - start_time) * 1000

        # Step 6: Build response
        from src.models import SearchResponse, Product

        products = []
        for hit in final_results.get("hits", []):
            doc = hit.get("document", {})
            try:
                product = Product(
                    product_id=str(doc.get("product_id", "")),
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
                    categories=doc.get("categories", [])
                )
                products.append(product)
            except Exception as e:
                print(f"Error transforming product: {e}")
                continue

        response = SearchResponse(
            results=products,
            primary_results=products,
            additional_results=None,
            detected_category=detected_category,
            category_confidence=category_confidence,
            category_applied=category_applied,
            confidence_threshold=confidence_threshold,
            total=final_results.get("found", 0),
            query_time_ms=query_time_ms,
            typesense_query={
                "approach": "decoupled_middleware",
                "middleware_url": self.middleware_url,
                "original_query": query,
                "extracted_query": search_params.get("q", ""),  # Show extracted q
                "filters_applied": search_params.get("filter_by", ""),  # Show filters
                "retrieval_count": len(retrieval_results),
                "middleware_params": search_params if debug else {
                    "q": search_params.get("q", ""),
                    "filter_by": search_params.get("filter_by", ""),
                    "sort_by": search_params.get("sort_by", "")
                },
                "category_reasoning": category_reasoning if debug else category_reasoning if category_applied else "",
                "search_time_ms": final_results.get("search_time_ms", 0)
            }
        )

        return response.model_dump()

    def _retrieval_search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Step 1: Do retrieval search to get product context.

        This search does NOT use category filters or NL models.
        It's a simple search to get relevant products for context.
        """
        search_params = {
            "q": query,
            "query_by": "name,description,short_description,sku,categories,brand,size,color",
            "per_page": limit,
            "prefix": "true,true,true,false,false,false,false,false",
            "num_typos": 2,
            "sort_by": "_text_match:desc",
            "nl_query": "false"  # NO NL model (avoid circular dependency)
        }

        result = self.typesense_client.collections[self.collection_name].documents.search(search_params)

        products = []
        for hit in result.get('hits', []):
            doc = hit['document']
            products.append({
                'name': doc.get('name', ''),
                'sku': doc.get('sku', ''),
                'price': doc.get('price'),
                'categories': doc.get('categories', []),
                'brand': doc.get('brand'),
                'size': doc.get('size'),
                'color': doc.get('color'),
                'stock_status': doc.get('stock_status'),
                'description': doc.get('short_description', doc.get('description', ''))[:200]
            })

        return products

    def _extract_context(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 2: Extract context from retrieval results.

        Group products by category and return top categories with sample products.
        """
        # Group by category
        category_groups = {}
        for product in products:
            for category in product.get('categories', []):
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(product)

        # Sort by product count
        sorted_categories = sorted(
            category_groups.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        # Build context (top 5 categories, 3 products each)
        context = []
        for category, items in sorted_categories[:5]:
            for product in items[:3]:
                context.append({
                    "name": product.get('name', ''),
                    "sku": product.get('sku', ''),
                    "price": product.get('price'),
                    "categories": product.get('categories', []),
                    "brand": product.get('brand'),
                    "stock_status": product.get('stock_status')
                })

        return context

    async def _call_middleware(self, query: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Step 3: Call middleware with query and context.

        The middleware will:
        1. Receive query + context
        2. Build enriched prompt
        3. Call OpenAI for category classification
        4. Return search parameters
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.middleware_url}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": query}
                    ],
                    "context": context  # Pass pre-retrieved context
                }
            )

            if response.status_code != 200:
                raise Exception(f"Middleware error: {response.text}")

            return response.json()

    def _parse_middleware_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: Parse middleware response to extract search parameters.
        """
        content = response["choices"][0]["message"]["content"]
        params = json.loads(content)
        return params

    def _final_search(self, params: Dict[str, Any], max_results: int) -> Dict[str, Any]:
        """
        Step 5: Execute final search with middleware parameters.
        """
        search_params = {
            "q": params.get("q", ""),
            "query_by": "name,sku,name_normalized,sku_normalized,description,short_description,categories",
            "query_by_weights": "100,100,4,4,3,3,1",
            "per_page": max_results,
            "sort_by": params.get("sort_by", "brand_priority:desc,_text_match:desc,price:asc"),
            "nl_query": "false"  # NO NL model
        }

        if params.get("filter_by"):
            search_params["filter_by"] = params["filter_by"]

        result = self.typesense_client.collections[self.collection_name].documents.search(search_params)
        return result
