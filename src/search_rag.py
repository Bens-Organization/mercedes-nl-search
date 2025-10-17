"""
RAG-based natural language search with dual LLM approach.

This module implements a 2-LLM-call approach combining natural language query
translation with RAG-based category classification.

Workflow (2 LLM calls):
1. LLM Call 1 (via Typesense NL): Extract filters (price, stock, etc.) from query
2. Retrieval: Get top N results with extracted filters (no category filter)
3. Extract categories: Group results by category
4. Build context: For each category, include sample products
5. LLM Call 2 (RAG): Classify best category based on context
6. Apply category filter: If confident, add category filter and re-search with all filters

This approach combines the best of both worlds:
- NL search for filter extraction (price, stock, sort, etc.)
- RAG classification for accurate category detection
"""

import time
import json
import typesense
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from src.config import Config
from src.models import SearchResponse, Product
from openai import OpenAI

# Validate configuration
Config.validate()


class RAGCategoryClassification:
    """Result of RAG-based category classification."""

    def __init__(
        self,
        category: Optional[str],
        confidence: float,
        reasoning: str,
        top_categories: List[Dict[str, Any]],
        llm_response_time_ms: float
    ):
        self.category = category
        self.confidence = confidence
        self.reasoning = reasoning
        self.top_categories = top_categories
        self.llm_response_time_ms = llm_response_time_ms


class RAGNaturalLanguageSearch:
    """Natural language search engine using RAG-based category classification."""

    def __init__(self):
        """Initialize search engine."""
        self.typesense_client = typesense.Client(Config.get_typesense_config())
        self.collection_name = Config.TYPESENSE_COLLECTION_NAME
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        # Use the RAG-optimized NL model (ID from Typesense)
        self.nl_model_id = "9bb52abc-8bf8-4536-80de-8231e77fab14"

    def search(
        self,
        query: str,
        max_results: int = 20,
        debug: bool = False,
        confidence_threshold: float = 0.75,
        retrieval_count: int = 20,
        max_categories: int = 10,
        samples_per_category: int = 2
    ) -> SearchResponse:
        """
        Search products using dual LLM approach: NL query translation + RAG category classification.

        Workflow (2 LLM calls):
        1. LLM Call 1 (Typesense NL): Extract filters (price, stock, etc.) from query
        2. Retrieve top N results with extracted filters (no category filter yet)
        3. Extract top categories with sample products from retrieved results
        4. LLM Call 2 (RAG): Classify category based on retrieved context
        5. If confident, apply category filter + NL-extracted filters for final search

        Args:
            query: Natural language search query (e.g., "nitrile gloves, powder-free, in stock, under $30")
            max_results: Maximum number of results to return
            debug: Enable debug mode to see LLM reasoning and extracted filters
            confidence_threshold: Minimum confidence to apply category filter (0-1, default: 0.75)
            retrieval_count: Number of results to retrieve for context (default: 20)
            max_categories: Maximum categories to consider (default: 10)
            samples_per_category: Sample products per category (default: 2)

        Returns:
            SearchResponse with results and metadata including:
            - results: Final product list
            - detected_category: Category identified by RAG
            - category_confidence: RAG confidence score
            - category_applied: Whether category filter was applied
            - typesense_query: Debug info including NL-extracted filters
        """
        start_time = time.time()

        # Check if query contains explicit limit (e.g., "5 most expensive", "top 10")
        extracted_limit = self._extract_limit_from_query(query)
        if extracted_limit:
            max_results = extracted_limit

        # Step 1: Retrieve top results via semantic search (no category filter)
        retrieval_results = self._retrieve_semantic_results(
            query,
            retrieval_count,
            debug
        )

        # Transform retrieval results to products
        retrieved_products = self._transform_results(retrieval_results.get("hits", []))

        if not retrieved_products:
            # No results found, return empty response
            query_time_ms = (time.time() - start_time) * 1000
            return SearchResponse(
                results=[],
                primary_results=[],
                additional_results=None,
                detected_category=None,
                category_confidence=0.0,
                category_applied=False,
                confidence_threshold=confidence_threshold,
                total=0,
                query_time_ms=query_time_ms,
                typesense_query={
                    "original_query": query,
                    "approach": "rag",
                    "note": "No results found"
                }
            )

        # Step 2: Extract category context from retrieved results
        category_context = self._extract_category_context(
            retrieved_products,
            max_categories,
            samples_per_category
        )

        # Step 3: LLM classifies category based on context
        classification = self._classify_category_with_llm(
            query,
            category_context,
            debug
        )

        # Extract parsed NL query params (filters, sorts) from retrieval
        parsed_params = {}
        if "parsed_nl_query" in retrieval_results:
            parsed_params = retrieval_results["parsed_nl_query"].get("generated_params", {})

        # Step 4: Decide whether to apply category filter
        products = retrieved_products  # Default: use semantic search results
        category_applied = False
        primary_results = retrieved_products
        additional_results = None

        if classification.category and classification.confidence >= confidence_threshold:
            # LLM is confident → Apply category filter
            category_applied = True

            # Execute final search with category filter + NL-extracted filters
            final_results = self._search_with_category_filter(
                query,
                classification.category,
                max_results,
                parsed_params,  # Pass NL-extracted filters
                debug
            )

            products = self._transform_results(final_results.get("hits", []))
            primary_results = products

            if debug:
                print(f"\n✓ Category filter applied: '{classification.category}'")
                print(f"  Confidence: {classification.confidence:.2f}")
                print(f"  Reasoning: {classification.reasoning}")
        else:
            # LLM not confident → Use semantic search results without filter
            products = retrieved_products[:max_results]
            primary_results = products

            if debug:
                print(f"\n✗ Category filter NOT applied")
                print(f"  Detected: {classification.category or 'None'}")
                print(f"  Confidence: {classification.confidence:.2f} (below threshold {confidence_threshold})")
                print(f"  Reasoning: {classification.reasoning}")

        query_time_ms = (time.time() - start_time) * 1000

        # Build typesense query metadata
        typesense_query = {
            "original_query": query,
            "approach": "rag",
            "nl_search_enabled": True,  # LLM Call 1: Query translation
            "rag_classification_enabled": True,  # LLM Call 2: Category classification
            "retrieval_count": retrieval_count,
            "max_categories": max_categories,
            "samples_per_category": samples_per_category,
            "detected_category": classification.category,
            "category_confidence": classification.confidence,
            "category_applied": category_applied,
            "confidence_threshold": confidence_threshold,
            "llm_reasoning": classification.reasoning,
            "llm_response_time_ms": classification.llm_response_time_ms,
            "top_categories": [cat["category"] for cat in classification.top_categories],
            "max_results": max_results,
        }

        # Add NL-extracted parameters if available
        if parsed_params:
            typesense_query["nl_extracted_filters"] = parsed_params.get("filter_by", "none")
            typesense_query["nl_extracted_sort"] = parsed_params.get("sort_by", "default")
            typesense_query["nl_extracted_query"] = parsed_params.get("q", query)

        return SearchResponse(
            results=products,
            primary_results=primary_results,
            additional_results=additional_results,
            detected_category=classification.category,
            category_confidence=classification.confidence,
            category_applied=category_applied,
            confidence_threshold=confidence_threshold,
            total=len(products),
            query_time_ms=query_time_ms,
            typesense_query=typesense_query
        )

    def _extract_limit_from_query(self, query: str) -> Optional[int]:
        """
        Extract result limit from query if explicitly mentioned.

        Examples:
        - "5 most expensive" → 5
        - "top 10 reagents" → 10
        - "first 3 gloves" → 3
        """
        import re

        patterns = [
            r'^(\d+)\s+(?:most|least|top|best|worst|cheapest|expensive)',
            r'top\s+(\d+)',
            r'first\s+(\d+)',
            r'^(\d+)\s+\w+',
        ]

        query_lower = query.lower().strip()

        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                limit = int(match.group(1))
                if 1 <= limit <= 100:
                    return limit

        return None

    def _retrieve_semantic_results(
        self,
        query: str,
        retrieval_count: int,
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Step 1: Retrieve top N results via NL search (with filter extraction, NO category filter).

        This provides the context for LLM classification.
        Uses Typesense native NL search to extract filters (price, stock, etc.) from the query.

        Args:
            query: Search query
            retrieval_count: Number of results to retrieve
            debug: Enable debug output

        Returns:
            Typesense search results with parsed_nl_query
        """
        search_params = {
            "q": query,
            "query_by": "name,description,short_description,sku,categories",
            "nl_query": "true",  # LLM Call 1: Extract filters, sorts, etc.
            "nl_model_id": self.nl_model_id,
            "per_page": retrieval_count,
            "sort_by": "_text_match:desc,price:asc",  # Default, can be overridden by NL
        }

        # Enable debug to see NL query parsing
        if debug:
            search_params["nl_query_debug"] = "true"

        try:
            results = self.typesense_client.collections[self.collection_name].documents.search(
                search_params
            )

            if debug:
                print(f"\n=== RAG Step 1: NL Search + Retrieval ===")
                print(f"Retrieved {len(results.get('hits', []))} results for context")

                # Show extracted filters
                if "parsed_nl_query" in results:
                    parsed = results["parsed_nl_query"].get("generated_params", {})
                    print(f"Extracted filters: {parsed.get('filter_by', 'none')}")
                    print(f"Extracted sort: {parsed.get('sort_by', 'default')}")
                    print(f"\nFull parsed_nl_query response:")
                    import json
                    print(json.dumps(results["parsed_nl_query"], indent=2))
                else:
                    print(f"WARNING: No parsed_nl_query in response!")
                    print(f"Available keys: {list(results.keys())}")

            return results

        except Exception as e:
            print(f"Error in retrieval: {e}")

            # Fallback to simple text search if NL fails
            try:
                fallback_params = {
                    "q": query,
                    "query_by": "name,description,short_description,sku,categories",
                    "per_page": retrieval_count,
                }
                results = self.typesense_client.collections[self.collection_name].documents.search(
                    fallback_params
                )
                print("  Fallback: Using text-only search (NL search failed)")
                return results
            except Exception as e2:
                print(f"Error in fallback search: {e2}")
                raise

    def _extract_category_context(
        self,
        products: List[Product],
        max_categories: int,
        samples_per_category: int
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Step 2: Extract category context from retrieved products.

        Groups products by category and samples representative products for each category.

        Args:
            products: List of retrieved products
            max_categories: Maximum number of categories to include
            samples_per_category: Number of sample products per category

        Returns:
            Dictionary mapping category → list of sample products
            Example:
            {
                "Gloves": [
                    {"name": "Nitrile Gloves Blue", "sku": "GLV-123"},
                    {"name": "Latex Gloves Powder-Free", "sku": "GLV-456"}
                ],
                "Pipettes": [...]
            }
        """
        # Group products by category
        category_products = defaultdict(list)

        for product in products:
            if product.categories:
                for category in product.categories:
                    category_products[category].append(product)

        # Sort categories by number of products (most products first)
        sorted_categories = sorted(
            category_products.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        # Build context: top N categories with sample products
        context = {}

        for category, category_prods in sorted_categories[:max_categories]:
            # Sample first N products from this category
            samples = []
            for prod in category_prods[:samples_per_category]:
                samples.append({
                    "name": prod.name,
                    "sku": prod.sku,
                    "price": f"${prod.price:.2f}" if prod.price else "N/A",
                })
            context[category] = samples

        return context

    def _classify_category_with_llm(
        self,
        query: str,
        category_context: Dict[str, List[Dict[str, str]]],
        debug: bool = False
    ) -> RAGCategoryClassification:
        """
        Step 3: LLM classifies the best category based on retrieved context.

        Args:
            query: Original search query
            category_context: Category context from retrieval
            debug: Enable debug output

        Returns:
            RAGCategoryClassification with category, confidence, and reasoning
        """
        start_time = time.time()

        # Build prompt for LLM
        prompt = self._build_classification_prompt(query, category_context)

        try:
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a product categorization expert. Analyze search queries and product context to determine the most relevant category."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,  # Deterministic
                response_format={"type": "json_object"}  # Ensure JSON response
            )

            llm_response_time_ms = (time.time() - start_time) * 1000

            # Parse LLM response
            result = json.loads(response.choices[0].message.content)

            category = result.get("category")
            confidence = float(result.get("confidence", 0.0))
            reasoning = result.get("reasoning", "No reasoning provided")

            # Extract top categories (for debugging)
            top_categories = [
                {"category": cat, "sample_count": len(samples)}
                for cat, samples in category_context.items()
            ]

            if debug:
                print(f"\n=== RAG Step 3: LLM Classification ===")
                print(f"LLM Response Time: {llm_response_time_ms:.2f}ms")
                print(f"Category: {category}")
                print(f"Confidence: {confidence:.2f}")
                print(f"Reasoning: {reasoning}")

            return RAGCategoryClassification(
                category=category,
                confidence=confidence,
                reasoning=reasoning,
                top_categories=top_categories,
                llm_response_time_ms=llm_response_time_ms
            )

        except Exception as e:
            print(f"Error in LLM classification: {e}")

            # Fallback: return no category
            return RAGCategoryClassification(
                category=None,
                confidence=0.0,
                reasoning=f"LLM classification failed: {str(e)}",
                top_categories=[],
                llm_response_time_ms=(time.time() - start_time) * 1000
            )

    def _build_classification_prompt(
        self,
        query: str,
        category_context: Dict[str, List[Dict[str, str]]]
    ) -> str:
        """
        Build the LLM prompt for category classification.

        Args:
            query: Original search query
            category_context: Category context with sample products

        Returns:
            LLM prompt string
        """
        context_str = json.dumps(category_context, indent=2)

        prompt = f"""Given the user search query and the top product categories with sample products, determine the most relevant category.

**User Query**: "{query}"

**Top Categories with Sample Products**:
{context_str}

**Task**:
1. Analyze the query intent
2. Consider the sample products in each category
3. Determine which category best matches the query
4. Assign a confidence score (0.0 to 1.0)

**Decision Criteria**:
- **Exact match** (SKU or exact product name): Very high confidence (0.9-1.0)
- **Clear product type** (e.g., "nitrile gloves" → Gloves): High confidence (0.7-0.9)
- **Product type + attributes** (e.g., "blue nitrile gloves"): High confidence (0.7-0.9)
- **Brand + product type** (e.g., "Thermo Fisher pipettes"): Medium-high confidence (0.6-0.8)
- **Ambiguous or attribute-only**: Low confidence (0.0-0.5) → Return null

**CRITICAL RULES - Return null for category and confidence < 0.5 if**:
1. **Single attribute word without product type**:
   - Examples: "clear", "large", "medium", "blue", "sterile", "disposable"
   - These are attributes (color, size, property), NOT product types
   - Rule: If query is 1-2 words AND doesn't mention a specific product type, return null

2. **Brand name only without product type**:
   - Examples: "Mercedes Scientific", "Ansell", "Yamato", "Thermo Fisher"
   - Brands span many categories, too ambiguous to filter
   - Rule: If query is only a brand name, return null

3. **Generic attribute categories**:
   - Avoid categories like "Brand: X", "Size: X", "Color: X"
   - These are not product categories, they're attributes
   - Rule: If category name starts with "Brand:", "Size:", "Color:", return null

4. **Highly ambiguous product types**:
   - Examples: "filters" (could be water, air, syringe, etc.)
   - Multiple distinct product categories match equally well
   - Rule: If 3+ categories match equally, return null

**Important**:
- Be CONSERVATIVE - when in doubt, return null with low confidence
- Only return a category if you're confident (>= 0.7) it's the right one
- A null response is better than a wrong category filter
- If you see an exact SKU or product name match, prioritize that category

**Response Format** (JSON):
{{
  "category": "CategoryName" or null,
  "confidence": 0.85,
  "reasoning": "Explanation of why this category was chosen (or why null was returned)"
}}

**Examples**:

Query: "clear" → {{"category": null, "confidence": 0.2, "reasoning": "Single attribute word without product type"}}
Query: "Mercedes Scientific" → {{"category": null, "confidence": 0.3, "reasoning": "Brand only, spans many categories"}}
Query: "nitrile gloves" → {{"category": "Products/Gloves & Apparel/Gloves", "confidence": 0.85, "reasoning": "Clear product type match"}}
Query: "Ansell gloves ANS 5789911" → {{"category": "Products/Gloves & Apparel/Gloves", "confidence": 0.95, "reasoning": "Exact SKU match"}}
"""
        return prompt

    def _search_with_category_filter(
        self,
        query: str,
        category: str,
        max_results: int,
        parsed_params: Dict[str, Any],
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Step 4: Execute final search with category filter + NL-extracted filters applied.

        Args:
            query: Search query
            category: Category to filter by
            max_results: Maximum results to return
            parsed_params: NL-extracted parameters (filters, sorts, etc.)
            debug: Enable debug output

        Returns:
            Typesense search results
        """
        # Escape category name for Typesense filter
        escaped_category = category.replace("`", "\\`")

        # Build category filter
        category_filter = f"categories:=`{escaped_category}`"

        # Merge with NL-extracted filters (if any)
        nl_filter = parsed_params.get("filter_by", "")

        # Remove category filter from NL-extracted filters (if present)
        # to avoid duplicates - we'll use the RAG-detected category instead
        if nl_filter and "categories:=" in nl_filter:
            nl_filter = self._remove_category_filter(nl_filter)

        if nl_filter:
            # Combine: RAG category filter AND NL-extracted filters (price, stock, etc.)
            combined_filter = f"{category_filter} && {nl_filter}"
        else:
            combined_filter = category_filter

        # Use NL-extracted sort if available, otherwise default
        sort_by = parsed_params.get("sort_by", "_text_match:desc,price:asc")

        # Use NL-extracted query text if available, otherwise original query
        query_text = parsed_params.get("q", query)

        search_params = {
            "q": query_text,
            "query_by": "name,description,short_description,sku,categories",
            "filter_by": combined_filter,
            "per_page": max_results,
            "sort_by": sort_by,
        }

        try:
            results = self.typesense_client.collections[self.collection_name].documents.search(
                search_params
            )

            if debug:
                print(f"\n=== RAG Step 4: Filtered Search ===")
                print(f"Query text: '{query_text}'")
                print(f"Category filter: '{escaped_category}'")
                print(f"Combined filter: '{combined_filter}'")
                print(f"Sort: {sort_by}")
                print(f"Results: {len(results.get('hits', []))}")

            return results

        except Exception as e:
            print(f"Error in filtered search: {e}")
            raise

    def _remove_category_filter(self, filter_by: str) -> str:
        """
        Remove category filter from filter_by string.

        Args:
            filter_by: Filter string (e.g., "categories:=Gloves && price:<50")

        Returns:
            Filter string without category (e.g., "price:<50")
        """
        # Split by " && " to get individual filter parts
        filters = filter_by.split(' && ')

        # Keep only filters that don't start with "categories"
        remaining_filters = [f for f in filters if not f.strip().startswith('categories')]

        # Rejoin with " && "
        result = ' && '.join(remaining_filters).strip()

        return result if result else ""

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


if __name__ == "__main__":
    # Test the RAG search
    import json

    search_engine = RAGNaturalLanguageSearch()

    test_queries = [
        "Ansell gloves ANS 5789911",  # Exact match example
        "nitrile gloves",  # Generic
        "Ansell",  # Brand only (ambiguous)
        "gloves under $50",  # Category + filter
        "pipettes in stock",  # Category + filter
    ]

    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Query: '{query}'")
        print('='*70)

        # Run with debug mode to see RAG workflow
        response = search_engine.search(query, max_results=5, debug=True)

        print(f"\n--- Final Results ---")
        print(f"Category Applied: {response.category_applied}")
        print(f"Detected Category: {response.detected_category}")
        print(f"Confidence: {response.category_confidence:.2f}")
        print(f"Total Results: {response.total}")
        print(f"Query Time: {response.query_time_ms:.2f}ms")

        print(f"\nTop {len(response.results)} Products:")
        for i, product in enumerate(response.results[:3], 1):
            print(f"\n{i}. {product.name}")
            print(f"   SKU: {product.sku}")
            print(f"   Price: ${product.price:.2f}" if product.price else "   Price: N/A")
            if product.categories:
                print(f"   Categories: {', '.join(product.categories[:2])}")
