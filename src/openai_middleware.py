"""
OpenAI-Compatible Middleware Service for Typesense NL Search

This service acts as a middleware between Typesense and OpenAI, encapsulating
the RAG (Retrieval-Augmented Generation) logic:

1. Receives OpenAI-format requests from Typesense
2. Extracts the user query
3. Runs retrieval search against Typesense (without category filter)
4. Injects product context into the prompt
5. Calls real OpenAI API with enriched context
6. Returns response in OpenAI format

Architecture:
    Typesense NL Search → [This Service] → Real OpenAI API
                              ↓
                         Typesense Search API
                         (for product retrieval)

Usage:
    # Start the service
    uvicorn src.openai_middleware:app --host 0.0.0.0 --port 8000

    # Configure in Typesense
    {
        "model_name": "openai/gpt-4o-mini",
        "api_base": "http://your-service:8000",
        "api_key": "any-value"  # Not validated
    }
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
import httpx
import json
import re
from datetime import datetime

from src.config import Config
import typesense
from src.cache_layer import get_cache
import warnings

# Suppress Typesense deprecation warnings (we're on v29, not using deprecated APIs)
warnings.filterwarnings('ignore', message='.*AnalyticsRulesV1 is deprecated.*')
warnings.filterwarnings('ignore', message='.*Overrides is deprecated.*')
warnings.filterwarnings('ignore', message='.*synonyms API.*is deprecated.*')

# Initialize FastAPI app
app = FastAPI(
    title="OpenAI-Compatible Middleware for Typesense",
    description="RAG middleware that enriches queries with product context",
    version="1.0.0"
)

# Initialize Typesense client
typesense_client = typesense.Client({
    'api_key': Config.TYPESENSE_API_KEY,
    'nodes': [{
        'host': Config.TYPESENSE_HOST,
        'port': Config.TYPESENSE_PORT,
        'protocol': Config.TYPESENSE_PROTOCOL
    }],
    'connection_timeout_seconds': 10
})


# ============================================================================
# Pydantic Models (OpenAI-compatible request/response)
# ============================================================================

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    # Accept pre-retrieved product context (decoupled architecture)
    context: Optional[List[Dict[str, Any]]] = Field(default=None, description="Pre-retrieved product context for RAG")


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


# ============================================================================
# Helper Functions
# ============================================================================

def extract_query_from_messages(messages: List[ChatMessage]) -> str:
    """
    Extract the user query from OpenAI-format messages.

    Typesense sends messages in format:
    [
        {"role": "system", "content": "System prompt with schema..."},
        {"role": "user", "content": "User's natural language query"}
    ]
    """
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content.strip()

    raise ValueError("No user message found in request")


def extract_schema_info(messages: List[ChatMessage]) -> Dict[str, Any]:
    """
    Extract schema information from the system message.
    Typesense includes the collection schema in the system prompt.
    """
    for msg in messages:
        if msg.role == "system":
            # Parse schema information from system message
            # This is a simplified extraction - adjust based on actual format
            return {
                "system_prompt": msg.content,
                "has_schema": "fields" in msg.content.lower()
            }

    return {"system_prompt": "", "has_schema": False}


async def retrieve_products(query: str, limit: int = 20, collection_name: str = None) -> List[Dict[str, Any]]:
    """
    Run retrieval search against Typesense to get relevant products.
    This search does NOT include category filters yet.

    For validation/test queries, returns empty list to avoid circular dependency.

    Args:
        query: Search query
        limit: Max number of products to retrieve
        collection_name: Typesense collection to search (defaults to env var or 'mercedes_products')
    """
    # Use provided collection or fall back to env var or default
    if collection_name is None:
        collection_name = Config.TYPESENSE_COLLECTION_NAME

    # Detect validation queries (Typesense uses these during model registration)
    validation_patterns = ['test', 'validation', 'ping', 'hello', 'check']
    query_lower = query.lower().strip()

    if query_lower in validation_patterns or len(query_lower) < 3:
        print(f"[VALIDATION] Detected validation query: '{query}' - skipping Typesense retrieval")
        return []

    try:
        search_params = {
            "q": query,
            "query_by": "name,sku,name_normalized,sku_normalized,description,short_description,categories",
            "query_by_weights": "100,100,4,4,3,3,500",  # Boosted category weight to overcome combined name+category boost in storage products
            "text_match_type": "max_weight",  # Use highest weighted field's score (not just tie-breaker)
            "per_page": limit,
            "prefix": "true,true,true,true,false,false,false",
            "num_typos": 2,
            "typo_tokens_threshold": 1,
            "drop_tokens_threshold": 2,
            "sort_by": "_text_match:desc",
            "nl_query": False  # CRITICAL: Prevent circular dependency (boolean, not string)
        }

        print(f"[COLLECTION] Using collection: {collection_name}")
        result = typesense_client.collections[collection_name].documents.search(search_params)

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

    except Exception as e:
        print(f"Error retrieving products: {e}")
        return []


def build_enriched_prompt(
    user_query: str,
    products: List[Dict[str, Any]],
    original_system_prompt: str
) -> List[ChatMessage]:
    """
    Build enriched prompt with product context injected (RAG approach).

    This creates a new message list with:
    1. Original system prompt (from Typesense) - includes conservative filtering rules
    2. Enriched user message with RAG context (categories + sample products)

    Matches the format from search_rag.py for consistency.
    """

    # Group products by category
    category_groups = {}
    for product in products:
        for category in product.get('categories', []):
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(product)

    # Sort categories by product count (most products first)
    sorted_categories = sorted(
        category_groups.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    # Build category context (same format as search_rag.py)
    category_context = {}
    for category, items in sorted_categories[:5]:  # Top 5 categories
        samples = []
        for product in items[:3]:  # Top 3 products per category
            samples.append({
                "name": product.get('name', ''),
                "sku": product.get('sku', ''),
                "price": f"${product['price']:.2f}" if product.get('price') else "N/A",
                "brand": product.get('brand', ''),
                "size": product.get('size', ''),
                "color": product.get('color', '')
            })
        category_context[category] = samples

    # DEBUG: Log the context being sent to LLM
    print(f"\n[DEBUG] ===== CONTEXT SENT TO LLM =====")
    print(f"[DEBUG] Total products: {len(products)}")
    print(f"[DEBUG] Total categories: {len(category_context)}")
    print(f"[DEBUG] Categories: {list(category_context.keys())}")
    for cat, samples in list(category_context.items())[:3]:  # Show first 3 categories
        print(f"[DEBUG] Category '{cat}': {len(samples)} products")
        for sample in samples[:2]:  # Show first 2 products
            print(f"[DEBUG]   - {sample['name']} @ {sample['price']}")
    print(f"[DEBUG] ================================\n")

    # Build enriched prompt (matches RAG classification prompt structure)
    import json
    context_str = json.dumps(category_context, indent=2)

    enriched_content = f"""Given the user search query and retrieved product categories, extract search parameters AND classify the most relevant product category.

**User Query**: "{user_query}"

**Retrieved Product Categories with Sample Products**:
{context_str}

**Your Task**:
1. **First, check if query is a SKU/Model Number** (if yes, skip category classification)
2. Extract clean search query (keep measurements, materials, descriptors)
3. Extract filters (price, stock, special_price, temporal only)
4. **Select the BEST MATCHING category from the retrieved products above** (ONLY if not a SKU)

**SKU/Model Number Detection** (CRITICAL - Check First):
- **SKU patterns**: Code + space + number (e.g., "MER 1200", "TNR 700S", "INN 187100")
- **Model number patterns**: Alphanumeric codes (e.g., "TNR700S", "K83-913", "BluTouch")
- **When detected**:
  - Prepend "sku:" to the query to search ONLY in SKU fields (e.g., "sku:MER 1200")
  - This restricts search to sku and sku_normalized fields only
  - Set detected_category to null (SKIP category classification)
  - Set category_confidence to 0.0
  - Set category_reasoning to "SKU/model number search - category filter skipped"
  - ONLY extract price/stock/temporal filters if present
- **Why**: SKU searches need field-specific matching to avoid matching across all product descriptions

**Category Classification (RAG Approach)** - SKIP if SKU detected:
- Look at the categories in the retrieved products above
- Pick the category that BEST matches the user's query intent
- **PREFER MORE SPECIFIC CATEGORIES**: If multiple category paths exist, choose the LONGEST/MOST SPECIFIC one
  - Example: For "cassettes", prefer "Cryotomy & Grossing / Cassettes" over "Products / Embedding"
  - Example: For "test tubes", prefer "Glass & Plasticware / Tubes / Test Tubes" over "Glass & Plasticware"
- ONLY choose categories that start with "Products/" OR contain specific product types (e.g., "Cassettes", "Gloves")
- SKIP categories that start with "Brand:", "Size:", "Color:" (these are attributes, not categories)
- SKIP broad parent categories if more specific subcategories exist
- If no good match exists, return null

**Specificity Rules** (CRITICAL for avoiding accessory contamination):
- **Most Specific Match**: Look for the deepest category path that matches the product type
  - "cassettes" → "Cryotomy & Grossing / Cassettes" NOT "Products / Embedding"
  - "pipettes" → "Pipettes" NOT "Products / Lab Equipment"
  - "gloves" → "Gloves & Apparel / Gloves" NOT "Gloves & Apparel"
- **Avoid Accessory Categories**: Don't select categories for accessories/consumables
  - "cassettes" → NOT "Biopsy Bags" (these are cassette papers, not cassettes)
  - "pipettes" → NOT "Pipette Tips" (these are tips, not pipettes)
  - "gloves" → NOT "Glove Dispensers" (these are dispensers, not gloves)

**Confidence Guidelines**:
- **0.9-1.0**: Exact product type match with specific subcategory (e.g., "test tubes" → "Products/.../Test Tubes")
- **0.8-0.9**: Clear product type match with specific category (e.g., "gloves" → "Products/.../Gloves")
- **0.75-0.85**: Product type with material/property (e.g., "nitrile gloves" → "Products/.../Gloves")
- **< 0.75**: Too ambiguous, return null

**When to Return null**:
- Query is only an attribute (e.g., "clear", "blue", "large") without product type
- Query is only a brand name (e.g., "Mercedes Scientific") without product type
- No "Products/..." category in retrieved results matches the query
- Multiple categories match equally well (ambiguous)
- Only broad parent categories exist without specific subcategories

**Query Extraction Rules** (Match Typesense NL behavior):

**KEEP These Terms** (Enhance search relevance):
- **Descriptive nouns**: capacity, volume, size, weight, length, diameter, thickness, width
- **Measurements with units**: 50ml, 1L, 100mg, 5cm, 10x10, 29.5mm (keep exact format)
- **Material/composition**: nitrile, latex, plastic, glass, steel, polypropylene, PP, HDPE
- **Properties/adjectives**: sterile, disposable, reusable, autoclavable, graduated, conical
- **Colors when specific**: blue, clear, white, amber (not just "colored")
- **Brands with products**: "Thermo Fisher pipettes" → keep both
- **Compound product names**: "centrifuge tube", "petri dish", "test tube"

**REMOVE These Words** (Noise):
- **Conversational fluff**: "I need", "I want", "looking for", "can you find", "show me"
- **Articles**: "a", "an", "the" (unless part of product name)
- **Conjunctions in context**: "and", "or", "with" between descriptors (keep meaningful ones)
- **Filler words**: "some", "any", "please", "thanks"
- **Question words**: "what", "where", "how" (unless meaningful like "how to")

**TRANSFORM**:
- **Plurals to singular** for product types: "gloves" → "glove", "tubes" → "tube"
- **Keep plurals** for measurements: "50ml" stays "50ml", "100mg" stays "100mg"
- **Normalize spacing** in measurements: "50 ml" → "50ml" OR keep as-is if that's more searchable

**Response Format** (JSON ONLY - no markdown, no code fences):
{{
    "q": "descriptive search query (keep measurements, materials, important descriptors)",
    "filter_by": "",
    "sort_by": "",
    "per_page": 20,
    "detected_category": null,
    "category_confidence": 0.0,
    "category_reasoning": ""
}}

**Field Rules**:
- `q`: Cleaned query with descriptive terms (required)
- `filter_by`: Use "" for no filters, OR "price:<50" OR "price:<50 && stock_status:=IN_STOCK" (string)
- `sort_by`: Use "" for default relevance, OR "price:asc" for cheapest, OR "price:desc" for most expensive, OR "created_at:desc" for newest (string)
- `per_page`: Always 20 (number)
- `detected_category`: Use null for no category, OR "Products/Full/Path" (string or null)
- `category_confidence`: 0.0 to 1.0 (number)
- `category_reasoning`: Explanation why category was/wasn't chosen (string)

IMPORTANT:
- Return ONLY the JSON object above. Do NOT wrap it in markdown code fences or any other formatting.
- Keep `sort_by` simple: "" (default), "price:asc" (cheapest), "price:desc" (expensive), "created_at:desc" (newest)
- Use null not "null" string for detected_category when no category
- If detected_category is not null AND category_confidence >= 0.75, it will be applied to filter_by automatically
- Be CONSERVATIVE with category detection - null is better than wrong category

**Conservative Filter Rules**:
- DO NOT extract color/size/brand as filters (keep in "q" for semantic search)
- ALWAYS extract price when mentioned (exact: price:=X, range: price:<X or price:>X)
- ALWAYS extract stock when mentioned (stock_status:=IN_STOCK)
- ALWAYS extract special_price for "on sale" (special_price:>0)

**Examples** (RAG-based category selection from retrieved products):

Example 1 - SKU Search (field-specific, NO category filter):
Query: "MER 1200"
Retrieved categories: ["Products/Chemicals & Stains/Naphthol Yellow", "Brand: Mercedes Scientific"]
→ {{"q": "sku:MER 1200", "filter_by": "", "sort_by": "", "per_page": 20, "detected_category": null, "category_confidence": 0.0, "category_reasoning": "SKU/model number search - category filter skipped"}}

Example 2 - SKU Search with filter (field-specific):
Query: "TNR700S under $100"
Retrieved categories: ["Products/Lab Equipment/Centrifuges", "Brand: Tanner Scientific"]
→ {{"q": "sku:TNR700S", "filter_by": "price:<100", "sort_by": "", "per_page": 20, "detected_category": null, "category_confidence": 0.0, "category_reasoning": "SKU/model number search - category filter skipped"}}

Example 3 - Specific Category Over Broad Parent (CRITICAL for avoiding accessories):
Query: "cassettes under $200"
Retrieved categories: ["Products / Embedding", "Cryotomy & Grossing / Cassettes", "Cryotomy & Grossing / Biopsy Bags, Paper & Sponges", "Brand: Cancer Diagnostics"]
→ {{"q": "cassette", "filter_by": "price:<200", "sort_by": "", "per_page": 20, "detected_category": "Cryotomy & Grossing / Cassettes", "category_confidence": 0.9, "category_reasoning": "Chose specific 'Cassettes' category over broad 'Embedding' parent to avoid cassette papers/accessories in 'Biopsy Bags' category"}}

Example 4:
Query: "test tubes glass"
Retrieved categories: ["Products/Glass & Plasticware/Tubes/Test Tubes", "Brand: Fisher Scientific", "Size: 16mm"]
→ {{"q": "test tube glass", "filter_by": "", "sort_by": "", "per_page": 20, "detected_category": "Products/Glass & Plasticware/Tubes/Test Tubes", "category_confidence": 0.9, "category_reasoning": "Exact match - 'test tubes' maps to Test Tubes category in retrieved products"}}

Example 5:
Query: "nitrile gloves under $50"
Retrieved categories: ["Products/Gloves & Apparel/Gloves", "Brand: Ansell", "Size: Large"]
→ {{"q": "nitrile glove", "filter_by": "price:<50", "sort_by": "", "per_page": 20, "detected_category": "Products/Gloves & Apparel/Gloves", "category_confidence": 0.85, "category_reasoning": "Clear product type matches Gloves category in retrieved results"}}

Example 6:
Query: "clear"
Retrieved categories: ["Products/Glass & Plasticware/Beakers", "Products/Lab Plasticware/Containers", "Brand: Corning"]
→ {{"q": "clear", "filter_by": "", "sort_by": "", "per_page": 20, "detected_category": null, "category_confidence": 0.2, "category_reasoning": "Query is only an attribute without product type - too ambiguous"}}

Example 7:
Query: "Mercedes Scientific"
Retrieved categories: ["Brand: Mercedes Scientific", "Products/Gloves & Apparel/Gloves", "Products/Pipettes"]
→ {{"q": "Mercedes Scientific", "filter_by": "", "sort_by": "", "per_page": 20, "detected_category": null, "category_confidence": 0.3, "category_reasoning": "Query is only a brand name - multiple product categories exist"}}

Example 8:
Query: "centrifuge tubes 50ml capacity"
Retrieved categories: ["Products/Glass & Plasticware/Tubes/Centrifuge Tubes", "Brand": Celltreat"]
→ {{"q": "centrifuge tube 50ml capacity", "filter_by": "", "sort_by": "", "per_page": 20, "detected_category": "Products/Glass & Plasticware/Tubes/Centrifuge Tubes", "category_confidence": 0.9, "category_reasoning": "Specific product type with capacity - exact category match in results"}}

Example 9:
Query: "pipettes on sale sorted by price"
Retrieved categories: ["Products/Pipettes", "Brand: Thermo Fisher"]
→ {{"q": "pipette", "filter_by": "special_price:>0", "sort_by": "price:asc", "per_page": 20, "detected_category": "Products/Pipettes", "category_confidence": 0.85, "category_reasoning": "Clear product type with sale filter and price sort"}}

Note: Middleware will automatically prepend "in_stock_priority:desc,brand_priority:desc" to all sort_by values!
"""

    # Return messages: system prompt + enriched user content
    return [
        ChatMessage(role="system", content=original_system_prompt),
        ChatMessage(role="user", content=enriched_content)
    ]


async def call_openai(messages: List[ChatMessage], model: str = "gpt-4o-mini", use_cache: bool = True, cache_key: str = None) -> Dict[str, Any]:
    """
    Call the real OpenAI API with enriched messages.

    Args:
        messages: Chat messages to send to OpenAI
        model: Model to use
        use_cache: Whether to use caching (default: True)
        cache_key: Optional explicit cache key (original user query). If not provided, extracts from messages.

    Returns:
        OpenAI API response (from cache or fresh API call)
    """
    # Strip "openai/" prefix if present (Typesense sends "openai/gpt-4o-mini")
    if model.startswith("openai/"):
        model = model.replace("openai/", "")

    # Try cache first (if enabled)
    if use_cache:
        try:
            cache = get_cache()

            # Use explicit cache key if provided, otherwise extract from messages
            if not cache_key:
                # Fallback: extract from user message content (last user message)
                # NOTE: This may include RAG context if called after enrichment
                for msg in reversed(messages):
                    if msg.role == "user":
                        cache_key = msg.content
                        break

            if cache_key:
                # Try to get from cache
                cached_response = await cache.get_cached_response(cache_key)
                if cached_response:
                    print(f"[CACHE] ✅ Cache hit for OpenAI call")
                    return cached_response

                print(f"[CACHE] ❌ Cache miss - calling OpenAI API")
        except Exception as e:
            print(f"[CACHE] Cache check error (proceeding without cache): {e}")

    # Cache miss or caching disabled - call OpenAI
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}  # Force JSON output (no markdown)
            }
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"OpenAI API error: {response.text}"
            )

        openai_response = response.json()

    # Cache the response (if caching enabled)
    if use_cache and cache_key:
        try:
            cache = get_cache()
            await cache.cache_response(cache_key, openai_response)
            print(f"[CACHE] Response cached for future queries")
        except Exception as e:
            print(f"[CACHE] Caching error (response still returned): {e}")

    return openai_response


def apply_category_filter(openai_response: Dict[str, Any], confidence_threshold: float = 0.75, for_typesense_nl: bool = True, retrieved_products: List[Dict[str, Any]] = None, user_query: str = None) -> Dict[str, Any]:
    """
    Apply category filter to search parameters if LLM is confident.

    This function:
    1. Parses the LLM response content (JSON with search parameters)
    2. Extracts detected_category and category_confidence
    3. If confident (>= threshold), injects category filter into filter_by
    4. Detects broad queries that span multiple subcategories and uses partial matching
    5. Returns modified response

    Args:
        openai_response: Raw OpenAI API response
        confidence_threshold: Minimum confidence to apply filter (default: 0.75)
        for_typesense_nl: If True, removes custom metadata fields and applies category to filter_by
                          If False, keeps metadata for decoupled architecture (default: True)
        retrieved_products: Optional list of retrieved products for multi-subcategory detection
        user_query: Optional user query for context-aware pattern matching

    Returns:
        Modified OpenAI response with category filter applied (if confident)
    """
    try:
        # Extract LLM message content
        message_content = openai_response["choices"][0]["message"]["content"]

        # DEBUG: Show raw LLM response
        print(f"\n[DEBUG] ===== RAW LLM RESPONSE =====")
        print(f"[DEBUG] {message_content}")
        print(f"[DEBUG] ==============================\n")

        # Parse JSON content
        params = json.loads(message_content)

        # Extract category classification results
        detected_category = params.get("detected_category")
        category_confidence = params.get("category_confidence", 0.0)
        category_reasoning = params.get("category_reasoning", "")

        print(f"[RAG] Category detected: {detected_category or 'None'}")
        print(f"[RAG] Confidence: {category_confidence:.2f} (threshold: {confidence_threshold})")
        print(f"[RAG] Reasoning: {category_reasoning}")

        if for_typesense_nl:
            # Option A: Typesense NL Integration (Single LLM Call)
            # Apply category filter directly to filter_by and remove custom metadata
            print(f"[MODE] Typesense NL integration mode - applying category to filter_by")

            if detected_category and category_confidence >= confidence_threshold:
                # Remove backticks from category (if present)
                normalized_category = detected_category.replace("`", "")

                # CRITICAL: LLM may normalize categories (remove spaces)
                # Match the LLM's category back to ACTUAL category from retrieved products
                # Example: LLM returns "Products/Gloves & Apparel/Gloves"
                #          But actual is "Products / Gloves & Apparel / Gloves" (with spaces)
                escaped_category = normalized_category

                if retrieved_products:
                    # Find exact match from retrieved categories (case-insensitive, space-insensitive)
                    # Support both exact match and suffix match (for categories with prefixes like "Root Catalog")
                    normalized_lower = normalized_category.lower().replace(" ", "").replace("/", "")
                    for product in retrieved_products:
                        for cat in product.get('categories', []):
                            cat_normalized = cat.lower().replace(" ", "").replace("/", "")

                            # Try exact match first (e.g., "Products/Gloves" == "Products/Gloves")
                            if cat_normalized == normalized_lower:
                                escaped_category = cat
                                print(f"[RAG] ✅ Exact match: '{normalized_category}' → '{cat}'")
                                break

                            # Try suffix match (e.g., "Cryotomy&Grossing/Cassettes" matches "RootCatalog/Cryotomy&Grossing/Cassettes")
                            elif cat_normalized.endswith(normalized_lower):
                                # Verify this is a real product category (not Brand, Size, Color)
                                if cat.startswith('Products') or cat.startswith('Root Catalog'):
                                    escaped_category = cat
                                    print(f"[RAG] ✅ Suffix match: '{normalized_category}' → '{cat}'")
                                    break

                # Detect if this is a broad query spanning multiple subcategories
                # Example: "alcohol" query retrieves both "Ethyl Alcohol" and "Isopropyl Alcohol"
                use_partial_match = False
                category_suffix = None

                if retrieved_products:
                    # Collect all "Products/" categories from retrieved products
                    # Note: Categories use "Products / " format (with spaces)
                    retrieved_categories = set()
                    for product in retrieved_products:
                        for cat in product.get('categories', []):
                            # Check for both "Products/" and "Products / " formats
                            if cat.startswith('Products/') or cat.startswith('Products /'):
                                retrieved_categories.add(cat)

                    # Check if we have multiple subcategories with a common suffix
                    # E.g., "Products / Chemicals & Stains / Ethyl Alcohol" and
                    #       "Products / Chemicals & Stains / Isopropyl Alcohol"
                    # Both end with "Alcohol" and share the same parent

                    # Extract the suffix from detected category (last word of last segment)
                    # "Products / Chemicals & Stains / Ethyl Alcohol" → "Alcohol"
                    # "Products / Gloves" → "Gloves"
                    # "Products / Storage / Slide Boxes" → check both "Slide" and "Boxes"
                    parts = escaped_category.split('/')
                    if len(parts) >= 2:
                        last_segment = parts[-1].strip()
                        last_words = last_segment.split()
                        detected_parent = '/'.join(parts[:-1]).strip()

                        # Check for compound category names (e.g., "Slide Boxes", "Test Tubes")
                        # Try both first word (for "Slide *" pattern) and last word (for "* Alcohol" pattern)
                        compound_suffix = None
                        single_suffix = None

                        if len(last_words) >= 2:
                            # Compound name: try first word pattern (e.g., "Slide *")
                            first_word = last_words[0]
                            compound_matching = [
                                cat for cat in retrieved_categories
                                if cat.startswith(detected_parent) and cat.split('/')[-1].strip().startswith(first_word)
                            ]
                            if len(compound_matching) >= 2:
                                compound_suffix = first_word
                                print(f"[RAG] 🔍 Compound category detected: '{first_word} *' pattern")
                                print(f"[RAG]    Found {len(compound_matching)} categories:")
                                for cat in compound_matching[:5]:
                                    print(f"[RAG]      - {cat}")

                        # Also try last word pattern (e.g., "* Alcohol", "* Boxes")
                        last_word = last_words[-1] if last_words else last_segment
                        single_matching = [
                            cat for cat in retrieved_categories
                            if cat.startswith(detected_parent) and last_word.lower() in cat.lower()
                        ]

                        # Check if detected category is under Storage parent
                        # For Storage categories, require explicit storage keywords to avoid false matches
                        # For non-Storage categories (e.g., Chemicals), allow partial matching freely
                        is_storage_category = '/storage/' in detected_parent.lower() or detected_parent.lower().endswith('storage')

                        if is_storage_category:
                            # Storage categories: require storage keywords in query
                            storage_keywords = ['storage', 'box', 'cabinet', 'holder', 'mailer', 'organizer', 'container', 'rack', 'drawer']
                            is_storage_query = False

                            if user_query:
                                query_lower = user_query.lower()
                                is_storage_query = any(keyword in query_lower for keyword in storage_keywords)
                                print(f"[RAG] 🔍 Storage category detected - checking query for storage keywords: {is_storage_query} (query='{user_query}')")

                            # Apply compound pattern ONLY if query mentions storage
                            if compound_suffix and len(compound_matching) >= 2:
                                if is_storage_query:
                                    use_partial_match = True
                                    category_suffix = compound_suffix
                                    print(f"[RAG] ⚠️  Storage query confirmed - using compound pattern '{compound_suffix} *'")
                                else:
                                    print(f"[RAG] ℹ️  Storage category but query NOT storage-related - using exact match (prevents 'microscope slide' → all Slide* storage)")
                            elif len(single_matching) >= 2:
                                if is_storage_query:
                                    use_partial_match = True
                                    category_suffix = last_word
                                    print(f"[RAG] ⚠️  Storage query confirmed - using partial pattern '*{last_word}*'")
                                else:
                                    print(f"[RAG] ℹ️  Storage category but query NOT storage-related - using exact match")
                        else:
                            # Non-Storage categories: allow partial matching freely
                            # This keeps "alcohol" → "*Alcohol*" working for Ethyl/Isopropyl Alcohol
                            if compound_suffix and len(compound_matching) >= 2:
                                use_partial_match = True
                                category_suffix = compound_suffix
                                print(f"[RAG] ⚠️  Non-storage broad query - using compound pattern '{compound_suffix} *'")
                            elif len(single_matching) >= 2:
                                use_partial_match = True
                                category_suffix = last_word
                                print(f"[RAG] ⚠️  Non-storage broad query - using partial pattern '*{last_word}*'")

                # Create appropriate filter based on detection
                if use_partial_match and category_suffix:
                    # Use partial match to include all subcategories
                    # This allows "alcohol" to match "Ethyl Alcohol", "Isopropyl Alcohol", etc.
                    category_filter = f"categories:*{category_suffix}*"
                    print(f"[RAG] ✅ Partial match filter applied: '*{category_suffix}*'")
                else:
                    # Use exact match for specific queries
                    # Backticks required to escape special characters like & in category names
                    category_filter = f"categories:=`{escaped_category}`"
                    print(f"[RAG] ✅ Exact match filter applied: '{escaped_category}'")

                # Get existing filters
                existing_filter = params.get("filter_by", "").strip()

                # Remove any existing category filters to avoid duplicates
                filter_parts = [part.strip() for part in existing_filter.split('&&') if part.strip()]
                filter_parts = [part for part in filter_parts if not part.startswith('categories:')]

                # Add category filter at the beginning
                if filter_parts:
                    params["filter_by"] = f"{category_filter} && {' && '.join(filter_parts)}"
                else:
                    params["filter_by"] = category_filter
            else:
                print(f"[RAG] ❌ Category filter NOT applied (low confidence or null)")

            # Remove custom metadata fields (Typesense can't parse them)
            params.pop("detected_category", None)
            params.pop("category_confidence", None)
            params.pop("category_reasoning", None)
            params.pop("per_page", None)  # Also remove per_page (Typesense sets this)

            print(f"[RAG] Removed custom metadata fields for Typesense compatibility")
        else:
            # Option B: Decoupled Architecture (2 Searches)
            # Keep metadata for API layer, don't apply category here
            print(f"[MODE] Decoupled architecture mode - keeping metadata for API layer")
            print(f"[RAG] NOTE: Category filter will be applied by API layer based on confidence")

        # Always prepend in_stock_priority and brand_priority to sort_by
        # This ensures in-stock products and in-house brands appear first
        # LLM only needs to specify user's sorting preference (price, temporal, etc.)
        llm_sort = params.get("sort_by", "").strip()

        if llm_sort and llm_sort not in ["", "in_stock_priority:desc,brand_priority:desc"]:
            # User has specific sorting preference (price, temporal, etc.)
            # Take only the FIRST sort field to avoid exceeding 3-field limit
            sort_fields = [f.strip() for f in llm_sort.split(",") if f.strip()]
            first_sort = sort_fields[0] if sort_fields else ""

            # Skip if it's already a priority field or _text_match (Typesense handles automatically)
            if first_sort and first_sort not in ["in_stock_priority:desc", "brand_priority:desc",
                                                 "_text_match:desc"]:
                params["sort_by"] = f"in_stock_priority:desc,brand_priority:desc,{first_sort}"
                print(f"[SORT] Prepended stock+brand priority to user sort: {params['sort_by']}")
            else:
                params["sort_by"] = "in_stock_priority:desc,brand_priority:desc"
                print(f"[SORT] Applied default stock-aware brand priority sorting")
        else:
            # Default: in-stock priority, brand priority (Typesense handles relevance automatically)
            params["sort_by"] = "in_stock_priority:desc,brand_priority:desc"
            print(f"[SORT] Applied default stock-aware brand priority sorting")

        # Remove empty string fields (Typesense prefers omitted fields over empty strings)
        if params.get("sort_by") == "":
            params.pop("sort_by", None)
        if params.get("filter_by") == "":
            params.pop("filter_by", None)

        # Update the response with modified parameters
        # CRITICAL: Use single-line JSON (no indent) for Typesense's regex parser
        openai_response["choices"][0]["message"]["content"] = json.dumps(params)

        print(f"[RESPONSE] Final params: {json.dumps(params)}")

        return openai_response

    except Exception as e:
        print(f"Error applying category filter: {e}")
        # Return original response if processing fails
        return openai_response


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check and service info"""
    return {
        "service": "OpenAI-Compatible Middleware for Typesense",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "/v1/chat/completions": "OpenAI-compatible chat completions (for Typesense)",
            "/health": "Health check",
            "/stats": "Service statistics"
        }
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    """Health check endpoint (supports GET and HEAD for UptimeRobot)"""
    try:
        # Test Typesense connection using default collection
        typesense_client.collections[Config.TYPESENSE_COLLECTION_NAME].retrieve()
        typesense_status = "connected"
    except Exception as e:
        typesense_status = f"error: {str(e)}"

    # Check cache status
    cache_status = "unknown"
    try:
        cache = get_cache()
        if not cache._initialized:
            await cache.initialize()
        cache_status = cache.mode
    except Exception as e:
        cache_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "typesense": typesense_status,
        "collection": Config.TYPESENSE_COLLECTION_NAME,
        "cache": cache_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, http_request: Request):
    """
    OpenAI-compatible chat completions endpoint.

    This is the main endpoint that Typesense will call.
    It encapsulates the entire RAG workflow:
    1. Check cache first (early exit if HIT)
    2. Retrieve relevant products (RAG context) - only on cache MISS
    3. Enrich prompt with product context
    4. Call OpenAI for filter extraction + category classification
    5. Apply category filter if confident (>= 0.75)
    6. Cache the response
    7. Return search parameters to Typesense

    Query Parameters:
        collection (optional): Typesense collection name to search
                               Defaults to TYPESENSE_COLLECTION_NAME env var
    """
    try:
        # Extract collection from query params (defaults to env var)
        collection_name = http_request.query_params.get('collection', Config.TYPESENSE_COLLECTION_NAME)

        # ENTRY POINT LOGGING: Prove Typesense is calling us
        import sys
        timestamp = datetime.now().isoformat()
        print(f"\n{'='*80}", flush=True)
        print(f"[{timestamp}] INCOMING REQUEST FROM TYPESENSE", flush=True)
        print(f"{'='*80}", flush=True)
        print(f"[REQUEST] Collection: {collection_name}", flush=True)
        print(f"[REQUEST] Model: {request.model}", flush=True)
        print(f"[REQUEST] Messages: {len(request.messages)} messages", flush=True)
        for i, msg in enumerate(request.messages):
            preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            print(f"  [{i}] {msg.role}: {preview}", flush=True)
        sys.stdout.flush()

        # 1. Extract user query from messages
        user_query = extract_query_from_messages(request.messages)

        # 2. CHECK CACHE FIRST (before RAG retrieval)
        try:
            cache = get_cache()
            cached_response = await cache.get_cached_response(user_query)

            if cached_response:
                # CACHE HIT - return immediately without RAG/OpenAI
                print(f"[CACHE] ✅ HIT - returning cached response (skipped RAG retrieval)", flush=True)

                # Log cached response content for visibility
                if cached_response.get("choices"):
                    cached_content = cached_response["choices"][0]["message"]["content"]
                    content_preview = cached_content[:200] if len(cached_content) > 200 else cached_content
                    print(f"[CACHE] Cached response: {content_preview}...", flush=True)

                # Apply category filter to cached response (for consistent formatting)
                for_typesense_nl = request.context is None
                cached_response = apply_category_filter(cached_response, for_typesense_nl=for_typesense_nl, user_query=user_query)

                # EXIT LOGGING
                response_body = json.dumps(cached_response)
                print(f"\n[RESPONSE] Status: 200 OK (from cache)", flush=True)
                print(f"[RESPONSE] Content length: {len(response_body)} bytes", flush=True)
                print(f"{'='*80}\n", flush=True)
                sys.stdout.flush()

                return cached_response

            # CACHE MISS - proceed with RAG
            print(f"[CACHE] ❌ MISS - proceeding with RAG retrieval + OpenAI", flush=True)

        except Exception as e:
            print(f"[CACHE] Cache check error (proceeding without cache): {e}", flush=True)

        # 3. Extract schema info from system message
        schema_info = extract_schema_info(request.messages)

        # 4. Get product context (RAG) - only executed on cache MISS
        # Decoupled Architecture: Accept context from request (no Typesense calls in middleware)
        if request.context is not None:
            # Context provided by caller (e.g., staging API) - use it directly
            products = request.context
            print(f"[RAG] Using provided context: {len(products)} products", flush=True)
        else:
            # Fallback: retrieve products (for direct middleware testing only)
            # WARNING: This creates circular dependency when called by Typesense
            products = await retrieve_products(user_query, limit=20, collection_name=collection_name)
            print(f"[RAG] Retrieved products from Typesense collection '{collection_name}': {len(products)} products", flush=True)

        # 5. Build enriched prompt with product context
        enriched_messages = build_enriched_prompt(
            user_query,
            products,
            schema_info.get("system_prompt", "")
        )

        # 6. Call real OpenAI API (filter extraction + category classification)
        # Disable caching in call_openai since we handle it here
        openai_response = await call_openai(enriched_messages, model=request.model, use_cache=False)

        # 7. Cache the response for future queries
        try:
            cache = get_cache()
            await cache.cache_response(user_query, openai_response)
            print(f"[CACHE] Response cached for future queries", flush=True)
        except Exception as e:
            print(f"[CACHE] Caching error (response still returned): {e}", flush=True)

        # 8. Apply category filter if LLM is confident
        # Determine mode based on whether context was provided:
        # - context provided (decoupled) → keep metadata for API layer
        # - no context (Typesense NL) → remove metadata for compatibility
        for_typesense_nl = request.context is None
        print(f"[MODE] {'Typesense NL integration' if for_typesense_nl else 'Decoupled architecture'} (context={'not provided' if for_typesense_nl else 'provided'})")
        openai_response = apply_category_filter(openai_response, for_typesense_nl=for_typesense_nl, retrieved_products=products, user_query=user_query)

        # 9. EXIT LOGGING: Show exact response being sent to Typesense
        response_body = json.dumps(openai_response)
        content_preview = openai_response["choices"][0]["message"]["content"][:200] if openai_response.get("choices") else "N/A"
        print(f"\n[RESPONSE] Status: 200 OK", flush=True)
        print(f"[RESPONSE] Content length: {len(response_body)} bytes", flush=True)
        print(f"[RESPONSE] Message content preview: {content_preview}...", flush=True)
        print(f"{'='*80}\n", flush=True)
        sys.stdout.flush()

        # 10. Return in OpenAI format (Typesense expects this)
        return openai_response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in chat_completions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/stats")
async def stats():
    """Service statistics including cache performance"""
    try:
        # Get collection stats using default collection
        collection_info = typesense_client.collections[Config.TYPESENSE_COLLECTION_NAME].retrieve()

        # Get cache stats
        cache_stats = {}
        try:
            cache = get_cache()
            cache_stats = cache.metrics.get_stats()
        except Exception as e:
            cache_stats = {"error": str(e)}

        return {
            "collection": {
                "name": collection_info.get("name"),
                "num_documents": collection_info.get("num_documents"),
                "created_at": collection_info.get("created_at")
            },
            "service": {
                "version": "1.0.0",
                "model": "gpt-4o-mini",
                "retrieval_limit": 20,
                "default_collection": Config.TYPESENSE_COLLECTION_NAME
            },
            "cache": cache_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@app.post("/generate")
async def generate_vllm_format(request: Request):
    """
    vLLM-compatible /generate endpoint for Typesense integration.

    This endpoint provides the same RAG-powered search parameter extraction
    as the OpenAI-compatible endpoint, but returns results in vLLM's format:
    {"text": ["generated text"]}

    Typesense's vllm/ namespace expects this format.

    Query Parameters:
        collection (optional): Typesense collection name to search
                               Defaults to TYPESENSE_COLLECTION_NAME env var
    """
    try:
        # Extract collection from query params (defaults to env var)
        collection_name = request.query_params.get('collection', Config.TYPESENSE_COLLECTION_NAME)

        # Parse request body
        data = await request.json()

        print("\n" + "=" * 80)
        print(f"[{datetime.now().isoformat()}] INCOMING REQUEST FROM TYPESENSE")
        print("=" * 80)
        print(f"[COLLECTION] Using collection: {collection_name}")
        print(f"[DEBUG] Request keys: {list(data.keys())}")

        # Handle both formats:
        # 1. OpenAI chat format: {"messages": [...], "model": "..."}
        # 2. vLLM format: {"prompt": "...", ...}

        user_query = None

        if "messages" in data:
            # OpenAI chat format - extract user query from messages
            print(f"[FORMAT] OpenAI chat format detected")
            messages = data.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    user_query = msg.get("content", "").strip()
                    break
            print(f"[EXTRACTED] User query from messages: '{user_query[:100] if user_query else 'NONE'}...'")
        elif "prompt" in data:
            # vLLM format with prompt field
            prompt = data.get("prompt", "")
            print(f"[FORMAT] vLLM prompt format detected")
            print(f"[REQUEST] Prompt length: {len(prompt)} chars")
            if prompt and len(prompt) > 200:
                print(f"[REQUEST] Prompt preview: {prompt[:200]}...")
            elif prompt:
                print(f"[REQUEST] Prompt: {prompt}")
            user_query = prompt
        else:
            print(f"[WARNING] No messages or prompt found in request!")
            user_query = ""

        # Validation queries (hello, test, etc.) - skip RAG processing
        if user_query and user_query.strip().lower() in ["hello", "hi", "test", "ping"]:
            print(f"[VALIDATION] Detected validation query: '{user_query}' - skipping Typesense retrieval")
            params = {
                "q": user_query.strip().lower(),
                "filter_by": "",
                "sort_by": "",
                "per_page": 20
            }
            print(f"\n[RESPONSE] Status: 200 OK")
            print(f"[RESPONSE] vLLM format: {{\"text\": [...]}}")
            print("=" * 80 + "\n")
            return {"text": [json.dumps(params)]}

        # Handle empty/invalid queries
        if not user_query or user_query.lower() in ["", "test", "hello"]:
            print(f"[VALIDATION] Empty/test query detected - returning default params")
            params = {
                "q": "test",
                "filter_by": "",
                "sort_by": "",
                "per_page": 20
            }
            print(f"\n[RESPONSE] Status: 200 OK")
            print(f"[RESPONSE] vLLM format: {{\"text\": [...]}}")
            print("=" * 80 + "\n")
            return {"text": [json.dumps(params)]}

        # RAG Approach: Retrieve products for context
        print(f"[RAG] Retrieving products for context from collection '{collection_name}'...")
        products = await retrieve_products(user_query, limit=20, collection_name=collection_name)
        print(f"[RAG] Retrieved {len(products)} products")

        # Build enriched prompt with RAG context
        system_prompt = """Extract search parameters from natural language queries for medical/scientific products."""
        enriched_messages = build_enriched_prompt(user_query, products, system_prompt)

        # Call OpenAI with RAG context and enforce JSON format
        openai_client = httpx.AsyncClient(timeout=30.0)
        try:
            openai_response = await openai_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": msg.role, "content": msg.content} for msg in enriched_messages],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}  # Force JSON output
                }
            )
            openai_data = openai_response.json()

            # Extract parameters from OpenAI response
            content = openai_data["choices"][0]["message"]["content"]
            print(f"[OPENAI] Response content: {content[:200]}...")
            params = json.loads(content)

        finally:
            await openai_client.aclose()

        # Apply RAG-based category detection (reuse existing logic from chat_completions)
        detected_category = params.get("detected_category")
        category_confidence = params.get("category_confidence", 0.0)
        confidence_threshold = 0.75

        if detected_category and category_confidence >= confidence_threshold:
            # Remove backticks from category (if present), then re-wrap in backticks for Typesense
            # Backticks are required to escape special characters like & in category names
            escaped_category = detected_category.replace("`", "")
            category_filter = f"categories:=`{escaped_category}`"

            # Remove existing category filters
            existing_filter = params.get("filter_by", "").strip()
            filter_parts = [part.strip() for part in existing_filter.split('&&')]
            filter_parts = [part for part in filter_parts if not part.startswith('categories:=')]
            existing_filter = ' && '.join(filter_parts) if filter_parts else ''

            # Add category filter
            if existing_filter:
                params["filter_by"] = f"{category_filter} && {existing_filter}"
            else:
                params["filter_by"] = category_filter

            print(f"[RAG] Category filter applied: '{escaped_category}' (confidence: {category_confidence:.2f})")
        else:
            print(f"[RAG] Category filter NOT applied (confidence: {category_confidence:.2f})")

        # Keep category metadata for API response (decoupled architecture)
        # The API layer will extract and use these fields
        # NOTE: Don't remove these - API needs them for debugging and response metadata

        # Return in vLLM format: {"text": ["json string"]}
        result = {"text": [json.dumps(params)]}

        print(f"\n[RESPONSE] Status: 200 OK")
        print(f"[RESPONSE] Content: {json.dumps(params)[:200]}...")
        print("=" * 80 + "\n")

        return result

    except Exception as e:
        print(f"Error in generate_vllm_format: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
