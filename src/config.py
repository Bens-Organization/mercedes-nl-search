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
    TYPESENSE_COLLECTION_NAME = "mercedes_products"

    # Mercedes GraphQL
    MERCEDES_GRAPHQL_URL = os.getenv(
        "MERCEDES_GRAPHQL_URL",
        "https://www.mercedesscientific.com/graphql"
    )

    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5001"))

    # Environment identifier (production, staging, development)
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

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
