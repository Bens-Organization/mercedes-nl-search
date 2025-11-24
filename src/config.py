"""Configuration module for the application."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # Search Engine Configuration
    # Supports both SEARCH_* (preferred) and TYPESENSE_* (legacy) environment variables
    SEARCH_HOST = os.getenv("SEARCH_HOST") or os.getenv("TYPESENSE_HOST", "localhost")
    SEARCH_PORT = int(os.getenv("SEARCH_PORT") or os.getenv("TYPESENSE_PORT", "8108"))
    SEARCH_PROTOCOL = os.getenv("SEARCH_PROTOCOL") or os.getenv("TYPESENSE_PROTOCOL", "http")
    SEARCH_API_KEY = os.getenv("SEARCH_API_KEY") or os.getenv("TYPESENSE_API_KEY")
    SEARCH_COLLECTION_NAME = os.getenv("SEARCH_COLLECTION_NAME") or os.getenv("TYPESENSE_COLLECTION_NAME", "mercedes_products")

    # Server Configuration (with backward compatibility)
    ENVIRONMENT = os.getenv("ENVIRONMENT") or os.getenv("FLASK_ENV", "development")
    SERVER_PORT = int(os.getenv("SERVER_PORT") or os.getenv("FLASK_PORT", "5001"))

    # NL Search Model ID (environment + collection based)
    # Format: middleware-rag-{environment}-{collection_name}
    # Examples: "middleware-rag-development-mercedes_magento", "middleware-rag-staging-mercedes_magento"
    # Each environment should have its own model pointing to its middleware URL
    _default_collection = os.getenv('SEARCH_COLLECTION_NAME') or os.getenv('TYPESENSE_COLLECTION_NAME', 'mercedes_products')
    _default_env = os.getenv("ENVIRONMENT") or os.getenv("FLASK_ENV", "development")
    NL_MODEL_ID = os.getenv("NL_MODEL_ID", f"middleware-rag-{_default_env}-{_default_collection}")

    # Middleware URL for RAG processing
    MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "https://web-production-a5d93.up.railway.app")

    # Mercedes GraphQL
    MERCEDES_GRAPHQL_URL = os.getenv(
        "MERCEDES_GRAPHQL_URL",
        "https://www.mercedesscientific.com/graphql"
    )

    # Restricted Items Configuration
    RESTRICTED_BRANDS = os.getenv("RESTRICTED_BRANDS", "Beckman Coulter,Olympus").split(",")
    RESTRICTED_SKU_PREFIXES = os.getenv("RESTRICTED_SKU_PREFIXES", "BEY,OSR").split(",")

    # Authentication (for future use)
    AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "")

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        required = [
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
            ("SEARCH_API_KEY", cls.SEARCH_API_KEY),
        ]

        missing = [name for name, value in required if not value]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    @classmethod
    def get_search_config(cls):
        """Get search engine client configuration."""
        return {
            "nodes": [{
                "host": cls.SEARCH_HOST,
                "port": cls.SEARCH_PORT,
                "protocol": cls.SEARCH_PROTOCOL
            }],
            "api_key": cls.SEARCH_API_KEY,
            "connection_timeout_seconds": 300  # 5 minutes for embedding generation
        }
