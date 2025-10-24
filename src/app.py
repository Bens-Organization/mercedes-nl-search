"""Flask API server for natural language search."""
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, request, jsonify
from flask_cors import CORS
from src.config import Config
from src.models import SearchQuery, SearchResponse, Product
import traceback
import typesense
import time

# Validate configuration
Config.validate()

# Initialize Flask app
app = Flask(__name__)

# CORS Configuration
# For production, update with your actual frontend URL
CORS(app, origins=[
    "http://localhost:3000",  # Local Next.js dev
    "http://localhost:5173",  # Local Vite dev
    "https://*.vercel.app",   # Vercel deployments
    "https://*.netlify.app",  # Netlify deployments
    # Production domain:
    "https://mercedes-nl-search.vercel.app",
    # Staging domain:
    "https://mercedes-nl-search-git-staging-alvin-jbbgis-projects.vercel.app"
])

# ============================================================================
# MIDDLEWARE APPROACH (New - For Staging Testing)
# ============================================================================
# Initialize Typesense client for middleware-based search
typesense_client = typesense.Client(Config.get_typesense_config())

# Middleware model ID (must be registered with Typesense first)
# Run: ./venv/bin/python src/setup_middleware_model.py update YOUR_MIDDLEWARE_URL
MIDDLEWARE_MODEL_ID = "custom-rag-middleware"

# ============================================================================
# OLD APPROACH (Dual LLM RAG - Commented out for rollback)
# ============================================================================
# from src.search_rag import RAGNaturalLanguageSearch
# search_engine = RAGNaturalLanguageSearch()


@app.route("/")
def home():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "Mercedes Scientific Natural Language Search API (Middleware-powered)",
        "version": "3.0",
        "environment": Config.ENVIRONMENT,
        "search_engine": "Middleware-based RAG (faster, cheaper)",
        "middleware_model_id": MIDDLEWARE_MODEL_ID,
        "endpoints": {
            "search": "/api/search",
            "health": "/health"
        }
    })


@app.route("/health")
def health():
    """Health check for monitoring."""
    try:
        # Try to retrieve collections to verify Typesense connection
        collections = typesense_client.collections.retrieve()
        return jsonify({
            "status": "healthy",
            "environment": Config.ENVIRONMENT,
            "services": {
                "api": "ok",
                "typesense": "ok",
                "search_approach": "middleware"
            }
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "environment": Config.ENVIRONMENT,
            "services": {
                "api": "ok",
                "typesense": "error"
            },
            "error": str(e)
        }), 503


@app.route("/api/search", methods=["POST"])
def search():
    """
    Search products using natural language via middleware.

    Request body:
    {
        "query": "sterile gloves under $100",
        "max_results": 20,
        "debug": false
    }

    Response:
    {
        "results": [...],
        "total": 25,
        "query_time_ms": 150,
        "detected_category": "Gloves",
        "category_confidence": 0.85,
        "category_applied": true,
        "typesense_query": {...}
    }
    """
    try:
        # Parse request
        data = request.get_json()

        if not data or "query" not in data:
            return jsonify({
                "error": "Missing 'query' in request body"
            }), 400

        # Validate with Pydantic
        search_query = SearchQuery(
            query=data["query"],
            max_results=data.get("max_results", 20)
        )

        # Optional parameters
        debug = data.get("debug", False)

        # ============================================================================
        # MIDDLEWARE SEARCH IMPLEMENTATION
        # ============================================================================
        start_time = time.time()

        # Build search parameters using middleware
        search_params = {
            "q": search_query.query,
            "query_by": "name,sku,name_normalized,sku_normalized,description,short_description,categories",
            "query_by_weights": "100,100,4,4,3,3,1",  # Prioritize original fields
            "nl_query": "true",  # Enable NL search
            "nl_model_id": MIDDLEWARE_MODEL_ID,  # Use middleware (handles RAG internally)
            "per_page": search_query.max_results,
            "sort_by": "brand_priority:desc,_text_match:desc,price:asc"  # In-house brands first
        }

        # Enable debug mode if requested
        if debug:
            search_params["nl_query_debug"] = "true"

        # Execute search via Typesense (which calls middleware)
        typesense_results = typesense_client.collections[Config.TYPESENSE_COLLECTION_NAME].documents.search(search_params)

        # Transform results to Product models
        products = []
        for hit in typesense_results.get("hits", []):
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

        query_time_ms = (time.time() - start_time) * 1000

        # Extract category info from NL query results (if available)
        detected_category = None
        category_confidence = 0.0
        category_applied = False

        if "parsed_nl_query" in typesense_results:
            parsed = typesense_results["parsed_nl_query"].get("generated_params", {})
            filter_by = parsed.get("filter_by", "")

            # Check if category filter was applied by middleware
            if "categories:=" in filter_by:
                category_applied = True
                # Extract category name from filter
                import re
                match = re.search(r'categories:=`?([^`&]+)`?', filter_by)
                if match:
                    detected_category = match.group(1).strip()
                    # Middleware applies category when confident, so assume high confidence
                    category_confidence = 0.85

        # Build response in same format as RAG approach
        response = SearchResponse(
            results=products,
            primary_results=products,  # All results are primary in middleware approach
            additional_results=None,
            detected_category=detected_category,
            category_confidence=category_confidence,
            category_applied=category_applied,
            confidence_threshold=0.75,  # Middleware uses this internally
            total=typesense_results.get("found", 0),
            query_time_ms=query_time_ms,
            typesense_query={
                "approach": "middleware",
                "nl_model_id": MIDDLEWARE_MODEL_ID,
                "original_query": search_query.query,
                "parsed_nl_query": typesense_results.get("parsed_nl_query", {}),
                "search_time_ms": typesense_results.get("search_time_ms", 0)
            }
        )

        # Return results
        return jsonify(response.model_dump())

        # ============================================================================
        # OLD APPROACH (Dual LLM RAG - Commented out for rollback)
        # ============================================================================
        # response = search_engine.search(
        #     query=search_query.query,
        #     max_results=search_query.max_results,
        #     debug=debug,
        #     confidence_threshold=confidence_threshold
        # )
        # return jsonify(response.model_dump())

    except Exception as e:
        traceback.print_exc()

        # Distinguish between different error types
        error_message = str(e)

        if "unavailable" in error_message.lower() or "cannot connect" in error_message.lower():
            return jsonify({
                "error": error_message,
                "message": "Search service is currently unavailable"
            }), 503  # Service Unavailable
        elif "authentication" in error_message.lower():
            return jsonify({
                "error": "Configuration error",
                "message": "Search service configuration error"
            }), 500
        else:
            return jsonify({
                "error": error_message,
                "message": "An error occurred while processing your search"
            }), 500


@app.route("/api/search", methods=["GET"])
def search_get():
    """
    Search products using query parameters (alternative to POST).

    Query params:
        q: Search query
        limit: Max results (default: 20)
        debug: Enable debug mode (default: false)

    Example: /api/search?q=gloves%20under%20$50&limit=10&debug=true
    """
    try:
        query = request.args.get("q", "")
        max_results = int(request.args.get("limit", 20))
        debug = request.args.get("debug", "false").lower() == "true"

        if not query:
            return jsonify({
                "error": "Missing 'q' query parameter"
            }), 400

        # Call POST search internally with same logic
        data = {
            "query": query,
            "max_results": max_results,
            "debug": debug
        }

        # Use the same search logic as POST endpoint
        with app.test_request_context("/api/search", method="POST", json=data):
            return search()

    except Exception as e:
        traceback.print_exc()

        # Distinguish between different error types
        error_message = str(e)

        if "unavailable" in error_message.lower() or "cannot connect" in error_message.lower():
            return jsonify({
                "error": error_message,
                "message": "Search service is currently unavailable"
            }), 503  # Service Unavailable
        elif "authentication" in error_message.lower():
            return jsonify({
                "error": "Configuration error",
                "message": "Search service configuration error"
            }), 500
        else:
            return jsonify({
                "error": error_message,
                "message": "An error occurred while processing your search"
            }), 500


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        "error": "Not found",
        "message": "The requested endpoint does not exist"
    }), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500


if __name__ == "__main__":
    print("=" * 60)
    print("Mercedes Scientific Natural Language Search API v3.0")
    print("Middleware-Powered RAG (Faster & Cheaper)")
    print("=" * 60)
    print(f"Environment: {Config.ENVIRONMENT}")
    print(f"Flask Mode: {Config.FLASK_ENV}")
    print(f"Server: http://localhost:{Config.FLASK_PORT}")
    print(f"Typesense: {Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}")
    print(f"Collection: {Config.TYPESENSE_COLLECTION_NAME}")
    print(f"OpenAI Model: {Config.OPENAI_MODEL}")
    print(f"Search Approach: Middleware-based RAG")
    print(f"Middleware Model ID: {MIDDLEWARE_MODEL_ID}")
    print("=" * 60)
    print("\nEndpoints:")
    print(f"  GET  /              - API info")
    print(f"  GET  /health        - Health check")
    print(f"  POST /api/search    - Search products (JSON body)")
    print(f"  GET  /api/search    - Search products (query params)")
    print("\nExample requests:")
    print(f'  curl -X POST http://localhost:{Config.FLASK_PORT}/api/search \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"query": "sterile gloves under $100"}\'')
    print(f'\n  curl "http://localhost:{Config.FLASK_PORT}/api/search?q=pipettes%20in%20stock"')
    print(f'\n  # With debug mode:')
    print(f'  curl "http://localhost:{Config.FLASK_PORT}/api/search?q=nitrile%20gloves&debug=true"')
    print("=" * 60)
    print("\nMiddleware Features:")
    print("  ✓ 2x faster than dual LLM RAG (~3-4s vs 6-8s)")
    print("  ✓ 50% cheaper (~$0.01 vs $0.02 per query)")
    print("  ✓ RAG-powered category detection (~80-85% accuracy)")
    print("  ✓ Conservative filtering (price, stock, special_price)")
    print("  ✓ Encapsulated logic (easier to maintain)")
    print("=" * 60)
    print(f"\n⚠️  IMPORTANT: Middleware must be deployed and registered!")
    print(f"   1. Deploy middleware to Render/Railway")
    print(f"   2. Register: ./venv/bin/python src/setup_middleware_model.py update YOUR_URL")
    print(f"   3. Verify: ./venv/bin/python src/setup_middleware_model.py check")
    print("=" * 60)
    print()

    app.run(
        host="0.0.0.0",
        port=Config.FLASK_PORT,
        debug=Config.FLASK_ENV == "development"
    )
