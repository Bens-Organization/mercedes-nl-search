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

    # Typesense
    TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "localhost")
    TYPESENSE_PORT = int(os.getenv("TYPESENSE_PORT", "8108"))
    TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
    TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY")
    TYPESENSE_COLLECTION_NAME = os.getenv("TYPESENSE_COLLECTION_NAME", "mercedes_products")
    # NL Search Model ID (collection-based, not environment-based)
    # Format: middleware-rag-{collection_name}
    # Examples: "middleware-rag-mercedes_products", "middleware-rag-mercedes_magento"
    # Multiple environments can share the same model if they use the same collection
    NL_MODEL_ID = os.getenv("NL_MODEL_ID", f"middleware-rag-{os.getenv('TYPESENSE_COLLECTION_NAME', 'mercedes_products')}")

    # Middleware URL for RAG processing
    MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "https://web-production-a5d93.up.railway.app")

    # Mercedes GraphQL
    MERCEDES_GRAPHQL_URL = os.getenv(
        "MERCEDES_GRAPHQL_URL",
        "https://www.mercedesscientific.com/graphql"
    )

    # Server Configuration (with backward compatibility)
    ENVIRONMENT = os.getenv("ENVIRONMENT") or os.getenv("FLASK_ENV", "development")
    SERVER_PORT = int(os.getenv("SERVER_PORT") or os.getenv("FLASK_PORT", "5001"))

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
            ("TYPESENSE_API_KEY", cls.TYPESENSE_API_KEY),
        ]

        missing = [name for name, value in required if not value]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    @classmethod
    def get_typesense_config(cls):
        """Get Typesense client configuration."""
        return {
            "nodes": [{
                "host": cls.TYPESENSE_HOST,
                "port": cls.TYPESENSE_PORT,
                "protocol": cls.TYPESENSE_PROTOCOL
            }],
            "api_key": cls.TYPESENSE_API_KEY,
            "connection_timeout_seconds": 300  # 5 minutes for embedding generation
        }
