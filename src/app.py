"""Flask API server for natural language search."""
from flask import Flask, request, jsonify
from flask_cors import CORS
from src.config import Config
from src.search_rag import RAGNaturalLanguageSearch
from src.models import SearchQuery
import traceback

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
    # Add your production domain here:
    "https://mercedes-nl-search.vercel.app"
])

# Initialize RAG search engine (improved category classification)
search_engine = RAGNaturalLanguageSearch()


@app.route("/")
def home():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "Mercedes Scientific Natural Language Search API (RAG-powered)",
        "version": "2.0",
        "search_engine": "RAG-based category classification",
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
        collections = search_engine.typesense_client.collections.retrieve()
        return jsonify({
            "status": "healthy",
            "services": {
                "api": "ok",
                "typesense": "ok"
            }
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "services": {
                "api": "ok",
                "typesense": "error"
            },
            "error": str(e)
        }), 503


@app.route("/api/search", methods=["POST"])
def search():
    """
    Search products using natural language with RAG-based category classification.

    Request body:
    {
        "query": "sterile gloves under $100",
        "max_results": 20,
        "debug": false,
        "confidence_threshold": 0.75
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

        # Optional parameters for RAG search
        debug = data.get("debug", False)
        confidence_threshold = data.get("confidence_threshold", 0.75)

        # Execute RAG search
        response = search_engine.search(
            query=search_query.query,
            max_results=search_query.max_results,
            debug=debug,
            confidence_threshold=confidence_threshold
        )

        # Return results
        return jsonify(response.model_dump())

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
        confidence_threshold: Min confidence for category filter (default: 0.75)

    Example: /api/search?q=gloves%20under%20$50&limit=10&debug=true
    """
    try:
        query = request.args.get("q", "")
        max_results = int(request.args.get("limit", 20))
        debug = request.args.get("debug", "false").lower() == "true"
        confidence_threshold = float(request.args.get("confidence_threshold", 0.75))

        if not query:
            return jsonify({
                "error": "Missing 'q' query parameter"
            }), 400

        # Execute RAG search
        response = search_engine.search(
            query=query,
            max_results=max_results,
            debug=debug,
            confidence_threshold=confidence_threshold
        )

        return jsonify(response.model_dump())

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
    print("Mercedes Scientific Natural Language Search API v2.0")
    print("RAG-Powered Category Classification")
    print("=" * 60)
    print(f"Environment: {Config.FLASK_ENV}")
    print(f"Server: http://localhost:{Config.FLASK_PORT}")
    print(f"Typesense: {Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}")
    print(f"Collection: {Config.TYPESENSE_COLLECTION_NAME}")
    print(f"OpenAI Model: {Config.OPENAI_MODEL}")
    print(f"Search Engine: RAG-based (improved)")
    print(f"Default Confidence: 0.75")
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
    print("\nRAG Features:")
    print("  ✓ Smart category detection with LLM reasoning")
    print("  ✓ Conservative handling of ambiguous queries")
    print("  ✓ 84.6% accuracy on test dataset")
    print("  ✓ Transparent confidence scoring")
    print("=" * 60)
    print()

    app.run(
        host="0.0.0.0",
        port=Config.FLASK_PORT,
        debug=Config.FLASK_ENV == "development"
    )
