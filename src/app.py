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
# Allow all origins for now (Vercel wildcard doesn't work with flask-cors)
# For production, you can restrict this to specific domains
CORS(app,
     origins="*",  # Allow all origins
     supports_credentials=False,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"]
)

# ============================================================================
# DECOUPLED MIDDLEWARE ARCHITECTURE (Active)
# ============================================================================
# Architecture: API handles all orchestration to avoid circular dependency
# Flow:
# 1. API → Typesense (retrieval for context)
# 2. API → Middleware (with context) → OpenAI
# 3. API → Typesense (final search with middleware params)
#
# This avoids circular dependency by NOT using Typesense's nl_search_models
from src.search_middleware import MiddlewareSearch

# Initialize Typesense client for health checks
typesense_client = typesense.Client(Config.get_typesense_config())

# Initialize middleware search engine
search_engine = MiddlewareSearch()


@app.route("/")
def home():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "Mercedes Scientific Natural Language Search API",
        "version": "3.1",
        "environment": Config.ENVIRONMENT,
        "search_engine": "Decoupled Middleware RAG (fast + accurate)",
        "architecture": "Decoupled (API orchestration, no circular dependency)",
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
                "search_approach": "decoupled_middleware"
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
        # Auto-enable debug for non-production environments
        debug = data.get("debug", Config.ENVIRONMENT != "production")
        confidence_threshold = data.get("confidence_threshold", 0.75)

        # ============================================================================
        # DECOUPLED MIDDLEWARE SEARCH
        # ============================================================================
        # This is an async function, so we need to await it
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(
            search_engine.search(
                query=search_query.query,
                max_results=search_query.max_results,
                debug=debug,
                confidence_threshold=confidence_threshold
            )
        )
        return jsonify(response)

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
        # Auto-enable debug for non-production environments
        debug = request.args.get("debug", str(Config.ENVIRONMENT != "production")).lower() == "true"

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
