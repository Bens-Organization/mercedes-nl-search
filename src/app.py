"""Flask API server for natural language search."""
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from search import NaturalLanguageSearch
from models import SearchQuery
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
    "https://mercedes-nl-search.vercel.app",
    "https://mercedes-nl-search-git-staging-alvin-jbbgis-projects.vercel.app"
])

# Initialize search engine
search_engine = NaturalLanguageSearch()


@app.route("/")
def home():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "Mercedes Scientific Natural Language Search API",
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
    Search products using natural language.

    Request body:
    {
        "query": "sterile gloves under $100",
        "max_results": 20
    }

    Response:
    {
        "results": [...],
        "total": 25,
        "query_time_ms": 150,
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

        # Execute search
        response = search_engine.search(
            query=search_query.query,
            max_results=search_query.max_results
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

    Example: /api/search?q=gloves%20under%20$50&limit=10
    """
    try:
        query = request.args.get("q", "")
        max_results = int(request.args.get("limit", 20))

        if not query:
            return jsonify({
                "error": "Missing 'q' query parameter"
            }), 400

        # Execute search
        response = search_engine.search(
            query=query,
            max_results=max_results
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
    print("Mercedes Scientific Natural Language Search API")
    print("=" * 60)
    print(f"Environment: {Config.FLASK_ENV}")
    print(f"Server: http://localhost:{Config.FLASK_PORT}")
    print(f"Typesense: {Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}")
    print(f"Collection: {Config.TYPESENSE_COLLECTION_NAME}")
    print(f"OpenAI Model: {Config.OPENAI_MODEL}")
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
    print("=" * 60)
    print()

    app.run(
        host="0.0.0.0",
        port=Config.FLASK_PORT,
        debug=Config.FLASK_ENV == "development"
    )
