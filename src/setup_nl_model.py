"""Setup natural language search model in Typesense.

This script registers an OpenAI model with Typesense for native NL search.
Must be run before using nl_query=true in search requests.

For RAG approach: This NL model extracts filters (price, stock, etc.) but NOT categories.
RAG handles category detection via a second LLM call.
"""
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import typesense
import requests
from src.config import Config

# Validate configuration
Config.validate()


def setup_nl_model():
    """Register OpenAI model with Typesense for natural language search."""

    # Build Typesense URL
    base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"

    # RAG-optimized system prompt - extracts filters but NOT categories (RAG handles categories)
    # Conservative approach: Only filter by reliable fields (price, stock, special_price, temporal)
    # Attributes (color, size, brand) go in "q" for semantic search (data too shallow for strict filtering)
    system_prompt = """Extract search parameters from natural language queries for medical/scientific products.

NOTE: This search uses RAG (Retrieval-Augmented Generation) for category detection.
DO NOT extract category filters - only extract price, stock, and special_price filters.

QUERY FIELD ("q"):
- Product types in SINGULAR form: "glove" not "gloves", "pipette" not "pipettes"
- Material descriptors: "nitrile", "latex", "stainless steel", "glass"
- General features: "sterile", "powder-free", "disposable", "surgical"
- Product attributes: "blue", "yellow", "large", "medium", "Mercedes Scientific"
- Technical specifications: "10μL capacity", "100mL volume", "0.5mm thickness"
- KEEP all descriptive words in "q" for semantic search

FILTER FIELD ("filter_by") - Extract ONLY these filter types:

1. Price filters (ALWAYS extract when ANY price is mentioned):
   - EXACT PRICE (default for bare amounts):
     * "costs $X" or "cost $X" → price:=X
     * "priced $X" or "priced at $X" → price:=X
     * "that costs $X" or "that cost $X" → price:=X
   - RANGE FILTERS:
     * "under $X" or "less than $X" → price:<X
     * "over $X" or "more than $X" → price:>X
     * "$X to $Y" or "between $X and $Y" → price:[X..Y]
   - SPECIAL:
     * "on sale" or "discounted" → special_price:>0

2. Stock filters (extract when stock mentioned):
   - "in stock" or "available" → stock_status:=IN_STOCK

SORT FIELD ("sort_by"):
- "cheapest" or "lowest price" → price:asc
- "most expensive" or "highest price" → price:desc
- "latest" or "newest" → created_at:desc
- "popular" or "most popular" or "best selling" → DO NOT use sort_by (rely on relevance scoring)

OPERATOR RULES:
- Exact match: := (e.g., price:=20)
- Range: : (e.g., price:<50)
- Combine filters: && (e.g., price:<50 && stock_status:=IN_STOCK)

EXAMPLES (NO category filters - RAG handles categories):
"nitrile gloves under $30" → {"q": "nitrile glove", "filter_by": "price:<30"}
"yellow slides" → {"q": "yellow slide"}
"yellow slides under $220" → {"q": "yellow slide", "filter_by": "price:<220"}
"blue gloves powder-free" → {"q": "blue glove powder-free"}
"pipettes in stock" → {"q": "pipette", "filter_by": "stock_status:=IN_STOCK"}
"clear test tubes" → {"q": "clear test tube"}
"nitrile gloves that costs $20" → {"q": "nitrile glove", "filter_by": "price:=20"}
"pipettes with at least 10μL capacity under $500" → {"q": "pipette 10μL capacity", "filter_by": "price:<500"}
"nitrile gloves powder-free in stock under $30" → {"q": "nitrile glove powder-free", "filter_by": "stock_status:=IN_STOCK && price:<30"}
"beakers under $50" → {"q": "beaker", "filter_by": "price:<50"}
"cheapest centrifuge" → {"q": "centrifuge", "sort_by": "price:asc"}
"white lab coats size large" → {"q": "white lab coat large"}
"Mercedes Scientific nitrile gloves size medium" → {"q": "Mercedes Scientific nitrile glove medium"}
"on sale microscopes" → {"q": "microscope", "filter_by": "special_price:>0"}

CRITICAL RULES:
1. DO NOT extract category filters - RAG handles category detection
2. DO NOT extract color/size/brand as filters - keep them in "q" for semantic search
   - Data is too shallow for strict attribute filtering
   - Semantic search handles color, size, brand matching naturally
3. ALWAYS keep product type in "q" for semantic search (e.g., "nitrile glove", "pipette")
4. ALWAYS extract price filter when ANY price appears:
   - DEFAULT: "costs $X", "cost $X", "priced $X" → price:=X (EXACT match)
   - RANGE: "under $X" → price:<X, "over $X" → price:>X
   - BETWEEN: "$X to $Y" → price:[X..Y]
5. ALWAYS extract stock filter when stock mentioned (in stock → stock_status:=IN_STOCK)
6. ALWAYS extract special_price filter for "on sale", "discounted" → special_price:>0
7. Technical specs (10μL, 100mL) stay in "q" - NEVER as filters
8. NEVER use sort_by for "popular", "most popular", "best selling" - rely on relevance scoring

IMPORTANT: "costs", "cost", "priced" without range words = EXACT price (price:=X), NOT under (price:<X)"""

    model_id = "openai-gpt4o-mini"
    model_config = {
        "id": model_id,
        "model_name": "openai/gpt-4o-mini-2024-07-18",  # Correct format: provider/model-name
        "api_key": Config.OPENAI_API_KEY,
        "max_bytes": 16000,  # Maximum bytes to send to LLM
        "temperature": 0.0,  # Deterministic results
        "system_prompt": system_prompt,  # Add custom system prompt
    }

    print("=" * 60)
    print("Setting up Natural Language Search Model")
    print("=" * 60)
    print(f"Typesense URL: {base_url}")
    print(f"Model ID: {model_id}")
    print(f"Model Name: {model_config['model_name']}")
    print(f"Temperature: {model_config['temperature']}")
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
            print(f"Existing configuration: {existing}")

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
            print(f"\n✓ Successfully created NL search model: {model_id}")
            print(f"✓ Configuration: {result}")
            print("\n" + "=" * 60)
            print("RAG Natural Language Search is now enabled!")
            print("=" * 60)
            print("\nHow it works (Dual LLM approach):")
            print("  1. LLM Call 1 (NL Model): Extracts filters (price, stock, etc.)")
            print("  2. LLM Call 2 (RAG): Detects category based on retrieved products")
            print("\nNext steps:")
            print("  1. Test RAG search: python src/search_rag.py")
            print("  2. Start API: python src/app.py")
            print("  3. Query example: 'nitrile gloves powder-free in stock under $30'")
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
        print(f"\n✗ Error setting up NL model: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your Typesense version (need v29.0+)")
        print("  2. Verify OPENAI_API_KEY in .env")
        print("  3. Ensure Typesense server is running")
        raise


def check_model_status():
    """Check if NL search model exists and is configured."""
    base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"
    model_id = "openai-gpt4o-mini"

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
            print(f"Configuration: {model}")
            return True
        else:
            print(f"\n✗ Model '{model_id}' does not exist")
            print("Run this script to create it: python src/setup_nl_model.py")
            return False
    except Exception as e:
        print(f"\n✗ Error checking model: {e}")
        print("Run this script to create it: python src/setup_nl_model.py")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Check if model exists
        check_model_status()
    else:
        # Setup the model
        setup_nl_model()
