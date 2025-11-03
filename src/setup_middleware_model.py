"""Setup middleware model in Typesense for RAG-powered NL search.

This script registers the middleware as an NL model with Typesense.
The middleware provides RAG-based category classification + filter extraction.

Must be run before using nl_query=true with middleware integration.
"""
import typesense
import requests
from config import Config

# Validate configuration
Config.validate()

# Middleware URL (production)
MIDDLEWARE_URL = "https://web-production-a5d93.up.railway.app"


def setup_middleware_model():
    """Register middleware as NL search model with Typesense."""

    # Build Typesense URL
    base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"

    # Model configuration pointing to middleware
    model_id = "middleware-rag-gpt4o-mini"
    model_config = {
        "id": model_id,
        "model_name": "openai/gpt-4o-mini-2024-07-18",  # OpenAI-compatible format
        "api_base": MIDDLEWARE_URL,  # Point to middleware instead of OpenAI
        "api_key": "dummy-key-not-validated",  # Middleware doesn't validate this
        "max_bytes": 16000,
        "temperature": 0.0,
    }

    print("=" * 60)
    print("Setting up Middleware Model for Typesense NL Search")
    print("=" * 60)
    print(f"Typesense URL: {base_url}")
    print(f"Middleware URL: {MIDDLEWARE_URL}")
    print(f"Model ID: {model_id}")
    print(f"Model Name: {model_config['model_name']}")
    print("=" * 60)
    print("\nHow this works:")
    print("  1. Typesense sends query to middleware (not OpenAI)")
    print("  2. Middleware runs RAG classification")
    print("  3. Middleware returns {q, filter_by} with category")
    print("  4. Typesense parses and executes search")
    print("=" * 60)

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
            print(f"  - API Base: {existing.get('api_base', 'N/A')}")

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
            print("  2. Test with: nl_query=true, nl_model_id='middleware-rag-gpt4o-mini'")
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
        print(f"  3. Test middleware: curl {MIDDLEWARE_URL}/health")
        raise


def check_model_status():
    """Check if middleware model exists and is configured."""
    base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"
    model_id = "middleware-rag-gpt4o-mini"

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
            print(f"  - API Base: {model.get('api_base', 'N/A')}")
            print(f"  - Temperature: {model.get('temperature')}")
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

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Check if model exists
        check_model_status()
    else:
        # Setup the model
        setup_middleware_model()
