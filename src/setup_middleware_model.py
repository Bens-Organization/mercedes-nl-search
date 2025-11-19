"""Setup middleware model in Typesense for RAG-powered NL search.

This script registers the middleware as an NL model with Typesense.
The middleware provides RAG-based category classification + filter extraction.

Must be run before using nl_query=true with middleware integration.

IMPORTANT: Models are registered PER ENVIRONMENT + COLLECTION.
Each environment (dev/staging/prod) should have its own model pointing to its middleware.

Usage:
    # Register model for current environment (uses ENVIRONMENT + TYPESENSE_COLLECTION_NAME from env)
    ENVIRONMENT=staging MIDDLEWARE_URL=https://web-mw-staging.up.railway.app python src/setup_middleware_model.py

    # Or specify environment and collection explicitly
    python src/setup_middleware_model.py mercedes_magento staging

    # Check model status
    python src/setup_middleware_model.py check

Example Setup:
    # Development environment
    ENVIRONMENT=development MIDDLEWARE_URL=https://web-development-middleware.up.railway.app python src/setup_middleware_model.py
    # Creates model: middleware-rag-development-mercedes_magento

    # Staging environment
    ENVIRONMENT=staging MIDDLEWARE_URL=https://web-mw-staging.up.railway.app python src/setup_middleware_model.py
    # Creates model: middleware-rag-staging-mercedes_magento

    # Production environment
    ENVIRONMENT=production MIDDLEWARE_URL=https://web-production-middleware.up.railway.app python src/setup_middleware_model.py
    # Creates model: middleware-rag-production-mercedes_magento

Then set NL_MODEL_ID in each backend environment:
    - Development: NL_MODEL_ID=middleware-rag-development-mercedes_magento
    - Staging: NL_MODEL_ID=middleware-rag-staging-mercedes_magento
    - Production: NL_MODEL_ID=middleware-rag-production-mercedes_magento
"""
import typesense
import requests
from config import Config

# Validate configuration
Config.validate()


def setup_middleware_model(collection_name: str = None, environment: str = None):
    """Register middleware as NL search model with Typesense.

    Models can be registered PER ENVIRONMENT + COLLECTION.
    This allows dev/staging/prod to use different middleware URLs.

    Args:
        collection_name: Typesense collection name (e.g., 'mercedes_products', 'mercedes_magento')
                         If not specified, uses Config.TYPESENSE_COLLECTION_NAME
        environment: Environment name (e.g., 'development', 'staging', 'production')
                     If not specified, uses Config.ENVIRONMENT
    """
    # Build Typesense URL
    base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"

    # Use provided values or fall back to config
    if collection_name is None:
        collection_name = Config.TYPESENSE_COLLECTION_NAME

    if environment is None:
        environment = Config.ENVIRONMENT

    # Build model ID based on environment + collection name
    # This ensures separate models per environment
    model_id = f"middleware-rag-{environment}-{collection_name}"

    # Build API URL with collection parameter
    api_url = f"{Config.MIDDLEWARE_URL}/v1/chat/completions?collection={collection_name}"

    # Model configuration pointing to middleware (using vLLM provider)
    model_config = {
        "id": model_id,
        "model_name": "vllm/gpt-4o-mini",  # Use vLLM provider for custom endpoint
        "api_url": api_url,  # Full endpoint URL with collection param
        "api_key": "dummy-key",  # Not validated by middleware
        "max_bytes": 16000,
        "temperature": 0.0,
    }

    print("=" * 70)
    print("Setting up Middleware Model for Typesense NL Search")
    print("=" * 70)
    print(f"Typesense URL: {base_url}")
    print(f"Middleware URL: {Config.MIDDLEWARE_URL}")
    print(f"Model ID: {model_id}")
    print(f"Model Name: {model_config['model_name']}")
    print(f"Collection: {collection_name}")
    print(f"API URL: {api_url}")
    print("=" * 70)
    print("\nHow this works:")
    print("  1. Typesense sends query to middleware (not OpenAI)")
    print("  2. Middleware retrieves products from specified collection")
    print("  3. Middleware runs RAG classification")
    print("  4. Middleware returns {q, filter_by} with category")
    print("  5. Typesense parses and executes search")
    print("=" * 70)

    headers = {
        "X-TYPESENSE-API-KEY": Config.TYPESENSE_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        # Check if model already exists
        check_url = f"{base_url}/nl_search_models/{model_id}"
        check_response = requests.get(check_url, headers=headers)

        if check_response.status_code == 200:
            print(f"\n⚠ Model '{model_id}' already exists")
            existing = check_response.json()
            print(f"Existing configuration:")
            print(f"  - Model: {existing.get('model_name')}")
            print(f"  - API URL: {existing.get('api_url', 'N/A')}")

            # Ask user if they want to update
            response = input("\nDo you want to delete and recreate it? (y/n): ")
            if response.lower() == 'y':
                delete_response = requests.delete(check_url, headers=headers)
                if delete_response.status_code == 200:
                    print(f"✓ Deleted existing model")
                else:
                    print(f"✗ Error deleting model: {delete_response.text}")
                    return
            else:
                print("✓ Keeping existing model (no changes)")
                return

        # Create the model
        create_url = f"{base_url}/nl_search_models"
        create_response = requests.post(create_url, headers=headers, json=model_config)

        if create_response.status_code in [200, 201]:
            result = create_response.json()
            print(f"\n✓ Successfully created middleware model: {model_id}")
            print(f"✓ Configuration: {result}")
            print("\n" + "=" * 60)
            print("Middleware integration is now enabled!")
            print("=" * 60)
            print("\nNext steps:")
            print("  1. Deploy middleware to staging/production")
            print("  2. Test with: nl_query=true, nl_model_id='middleware-rag-vllm'")
            print("  3. Middleware will handle RAG classification automatically")
        else:
            print(f"\n✗ Error creating model: {create_response.status_code}")
            print(f"Response: {create_response.text}")
            raise Exception(f"Failed to create model: {create_response.text}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Connection error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Typesense server is running")
        print(f"  2. Check Typesense URL: {base_url}")
        print("  3. Verify TYPESENSE_API_KEY in .env")
        raise
    except Exception as e:
        print(f"\n✗ Error setting up middleware model: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your Typesense version (need v29.0+)")
        print("  2. Ensure middleware is deployed and accessible")
        print(f"  3. Test middleware: curl {Config.MIDDLEWARE_URL}/health")
        raise


def check_model_status(collection_name: str = None, environment: str = None):
    """Check if middleware model exists and is configured.

    Args:
        collection_name: Collection name (e.g., 'mercedes_products', 'mercedes_magento')
                         If not specified, uses Config.TYPESENSE_COLLECTION_NAME
        environment: Environment name (e.g., 'development', 'staging', 'production')
                     If not specified, uses Config.ENVIRONMENT
    """
    base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"

    # Use provided values or fall back to config
    if collection_name is None:
        collection_name = Config.TYPESENSE_COLLECTION_NAME

    if environment is None:
        environment = Config.ENVIRONMENT

    # Build model ID based on environment + collection name
    model_id = f"middleware-rag-{environment}-{collection_name}"

    headers = {
        "X-TYPESENSE-API-KEY": Config.TYPESENSE_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        check_url = f"{base_url}/nl_search_models/{model_id}"
        response = requests.get(check_url, headers=headers)

        if response.status_code == 200:
            model = response.json()
            print(f"\n✓ Model '{model_id}' exists")
            print(f"Configuration:")
            print(f"  - Model: {model.get('model_name')}")
            print(f"  - API URL: {model.get('api_url', 'N/A')}")
            print(f"  - Temperature: {model.get('temperature')}")
            # Extract collection from API URL
            api_url = model.get('api_url', '')
            if 'collection=' in api_url:
                collection = api_url.split('collection=')[1].split('&')[0]
                print(f"  - Collection: {collection}")
            return True
        else:
            print(f"\n✗ Model '{model_id}' does not exist")
            print("Run this script to create it: python src/setup_middleware_model.py")
            return False
    except Exception as e:
        print(f"\n✗ Error checking model: {e}")
        print("Run this script to create it: python src/setup_middleware_model.py")
        return False


if __name__ == "__main__":
    import sys

    # Parse command-line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "check":
            # Check model status for collection
            collection_name = sys.argv[2] if len(sys.argv) > 2 else None
            environment = sys.argv[3] if len(sys.argv) > 3 else None
            check_model_status(collection_name, environment)
        else:
            # Setup model for collection and optional environment
            collection_name = sys.argv[1]
            environment = sys.argv[2] if len(sys.argv) > 2 else None
            setup_middleware_model(collection_name, environment)
    else:
        # Default: setup model with config values
        print("\nUsage:")
        print("  python src/setup_middleware_model.py                         # Default (from env)")
        print("  python src/setup_middleware_model.py mercedes_magento        # Specific collection")
        print("  python src/setup_middleware_model.py mercedes_magento staging # Collection + environment")
        print("  python src/setup_middleware_model.py check                   # Check default")
        print("  python src/setup_middleware_model.py check mercedes_magento staging # Check specific")
        print("\nIMPORTANT: Models are per ENVIRONMENT + COLLECTION")
        print("Each environment needs its own model pointing to its middleware URL.")
        print("\nSetting up default model...\n")
        setup_middleware_model()
