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


async def retrieve_products(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Run retrieval search against Typesense to get relevant products.
    This search does NOT include category filters yet.
    """
    try:
        search_params = {
            "q": query,
            "query_by": "name,description,short_description,sku,categories,brand,size,color",
            "per_page": limit,
            "prefix": "true,true,true,false,false,false,false,false",
            "num_typos": 2,
            "typo_tokens_threshold": 1,
            "drop_tokens_threshold": 2,
            "sort_by": "_text_match:desc"  # Removed stock_status:desc (not sortable)
        }

        result = typesense_client.collections['mercedes_products'].documents.search(search_params)

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

    # Build enriched prompt (matches RAG classification prompt structure)
    import json
    context_str = json.dumps(category_context, indent=2)

    enriched_content = f"""Given the user search query and the top product categories with sample products, extract search parameters.

**User Query**: "{user_query}"

**Top Categories with Sample Products**:
{context_str}

**Task**:
1. Extract filters (price, stock, special_price only - follow conservative rules)
2. Build search query (q field with product type, attributes, descriptors)
3. Determine sort order (if applicable)
4. Detect category based on context (be conservative - return null if ambiguous)

**Response Format** (JSON ONLY - no markdown, no code fences):
{{
    "q": "search terms in singular form",
    "filter_by": "price/stock/special_price filters with &&",
    "sort_by": "field:direction",
    "per_page": 20
}}

IMPORTANT: Return ONLY the JSON object above. Do NOT wrap it in markdown code fences or any other formatting.

**Conservative Rules** (from system prompt):
- DO NOT extract color/size/brand as filters (keep in "q" for semantic search)
- Return null category for single-word attributes ("clear", "large")
- Return null category for brand-only queries ("Mercedes Scientific")
- Return null category for highly ambiguous queries
- ALWAYS extract price when mentioned (exact: price:=X, range: price:<X or price:>X)
- ALWAYS extract stock when mentioned (stock_status:=IN_STOCK)
- ALWAYS extract special_price for "on sale" (special_price:>0)
"""

    # Return messages: system prompt + enriched user content
    return [
        ChatMessage(role="system", content=original_system_prompt),
        ChatMessage(role="user", content=enriched_content)
    ]


async def call_openai(messages: List[ChatMessage], model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Call the real OpenAI API with enriched messages.
    """
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

        return response.json()


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


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Test Typesense connection
        typesense_client.collections['mercedes_products'].retrieve()
        typesense_status = "connected"
    except Exception as e:
        typesense_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "typesense": typesense_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.

    This is the main endpoint that Typesense will call.
    It encapsulates the entire RAG workflow.
    """
    try:
        # 1. Extract user query from messages
        user_query = extract_query_from_messages(request.messages)

        # 2. Extract schema info from system message
        schema_info = extract_schema_info(request.messages)

        # 3. Run retrieval search
        products = await retrieve_products(user_query, limit=20)

        # 4. Build enriched prompt with product context
        enriched_messages = build_enriched_prompt(
            user_query,
            products,
            schema_info.get("system_prompt", "")
        )

        # 5. Call real OpenAI API
        openai_response = await call_openai(enriched_messages, model=request.model)

        # 6. Return in OpenAI format (Typesense expects this)
        return openai_response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in chat_completions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/stats")
async def stats():
    """Service statistics"""
    try:
        # Get collection stats
        collection_info = typesense_client.collections['mercedes_products'].retrieve()

        return {
            "collection": {
                "name": collection_info.get("name"),
                "num_documents": collection_info.get("num_documents"),
                "created_at": collection_info.get("created_at")
            },
            "service": {
                "version": "1.0.0",
                "model": "gpt-4o-mini",
                "retrieval_limit": 20
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


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
