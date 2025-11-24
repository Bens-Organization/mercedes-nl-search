"""FastAPI server for natural language search."""
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import Config
from search import Search
from models import SearchQuery, SearchResponse
from restrictions import get_user_permissions, build_restriction_filter
from pydantic import BaseModel, Field
import traceback
from typing import Optional

# Validate configuration
Config.validate()

# Initialize FastAPI app
app = FastAPI(
    title="Mercedes Scientific Natural Language Search API",
    description="Natural language search API powered by Journey AI with RAG-based category classification",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
# Note: Wildcards require allow_origin_regex, not allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local Next.js dev
        "http://localhost:5173",  # Local Vite dev
        "https://mercedes-nl-search.vercel.app",  # Production frontend
        "http://35.232.14.171",  # Magento UI (HTTP)
        "https://35.232.14.171",  # Magento UI (HTTPS)
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",  # All Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize search engine
search_engine = Search()


# Request/Response models
class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Natural language search query")
    max_results: int = Field(20, description="Maximum number of results to return", ge=1, le=100)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    services: dict


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str


@app.get("/")
async def home():
    """API info endpoint."""
    return {
        "status": "ok",
        "message": "Mercedes Scientific Natural Language Search API",
        "version": "3.0.0",
        "architecture": "Journey AI NL + RAG",
        "endpoints": {
            "search": "/api/search",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse)
async def health():
    """Health check for monitoring (supports GET and HEAD for UptimeRobot)."""
    try:
        # Verify search service connection
        collections = search_engine.search_client.collections.retrieve()
        return {
            "status": "healthy",
            "services": {
                "api": "ok",
                "search": "ok"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "services": {
                    "api": "ok",
                    "search": "error"
                },
                "error": "Search service unavailable"
            }
        )


@app.post("/api/search", response_model=SearchResponse)
async def search(search_request: SearchRequest, request: Request):
    """
    Search products using natural language with restriction filtering.

    Uses Journey AI NL integration with RAG-based category classification:
    - API receives natural language query
    - Applies restriction filter based on user permissions
    - AI middleware performs RAG classification
    - Returns search parameters with category filter
    - Results returned to user

    Request body:
    {
        "query": "sterile gloves under $100",
        "max_results": 20
    }

    Request headers (optional):
    - Authorization: Bearer <token>
    - X-Customer-Permissions: comma-separated permissions (e.g., "restricted_access")
    - X-Customer-Group: customer group (e.g., "authorized", "premium")

    Response:
    {
        "results": [...],
        "total": 25,
        "query_time_ms": 150,
        "search_query": {...}
    }
    """
    try:
        # Get user permissions from request headers
        user_permissions = await get_user_permissions(request)

        # Build restriction filter (empty if user has access)
        restriction_filter = build_restriction_filter(user_permissions)

        # Execute search with restriction filter
        response = await search_engine.search(
            query=search_request.query,
            max_results=search_request.max_results,
            restriction_filter=restriction_filter
        )
        return response

    except Exception as e:
        traceback.print_exc()

        error_message = str(e)

        if "unavailable" in error_message.lower() or "cannot connect" in error_message.lower():
            raise HTTPException(
                status_code=503,
                detail={
                    "error": error_message,
                    "message": "Search service is currently unavailable"
                }
            )
        elif "authentication" in error_message.lower():
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Configuration error",
                    "message": "Search service configuration error"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": error_message,
                    "message": "An error occurred while processing your search"
                }
            )


@app.get("/api/search", response_model=SearchResponse)
async def search_get(
    request: Request,
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Max results", ge=1, le=100)
):
    """
    Search products using query parameters with restriction filtering (alternative to POST).

    Query params:
        q: Search query
        limit: Max results (default: 20)

    Request headers (optional):
    - Authorization: Bearer <token>
    - X-Customer-Permissions: comma-separated permissions (e.g., "restricted_access")
    - X-Customer-Group: customer group (e.g., "authorized", "premium")

    Example: /api/search?q=gloves%20under%20$50&limit=10
    """
    try:
        # Get user permissions from request headers
        user_permissions = await get_user_permissions(request)

        # Build restriction filter (empty if user has access)
        restriction_filter = build_restriction_filter(user_permissions)

        # Execute search with restriction filter
        response = await search_engine.search(
            query=q,
            max_results=limit,
            restriction_filter=restriction_filter
        )
        return response

    except Exception as e:
        traceback.print_exc()

        error_message = str(e)

        if "unavailable" in error_message.lower() or "cannot connect" in error_message.lower():
            raise HTTPException(
                status_code=503,
                detail={
                    "error": error_message,
                    "message": "Search service is currently unavailable"
                }
            )
        elif "authentication" in error_message.lower():
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Configuration error",
                    "message": "Search service configuration error"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": error_message,
                    "message": "An error occurred while processing your search"
                }
            )


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Mercedes Scientific Natural Language Search API")
    print("=" * 60)
    print(f"Architecture: Journey AI NL + RAG")
    print(f"Environment: {Config.ENVIRONMENT}")
    print(f"Server: http://localhost:{Config.SERVER_PORT}")
    print("=" * 60)
    print("\nEndpoints:")
    print(f"  GET  /              - API info")
    print(f"  GET  /health        - Health check")
    print(f"  POST /api/search    - Search products (JSON body)")
    print(f"  GET  /api/search    - Search products (query params)")
    print(f"  GET  /docs          - Interactive API documentation (Swagger UI)")
    print(f"  GET  /redoc         - Alternative API documentation (ReDoc)")
    print("\nExample:")
    print(f'  curl -X POST http://localhost:{Config.SERVER_PORT}/api/search \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"query": "sterile gloves under $100"}\'')
    print("=" * 60)
    print()

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=Config.SERVER_PORT,
        reload=Config.ENVIRONMENT == "development"
    )
