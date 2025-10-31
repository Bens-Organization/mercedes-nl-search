"""
Configure Typesense to use the custom OpenAI-compatible middleware service.

This script registers a custom NL search model that points to the middleware
service instead of the real OpenAI API.

Usage:
    # Register middleware endpoint
    python src/setup_middleware_model.py

    # Check if model exists
    python src/setup_middleware_model.py check

    # Delete existing model
    python src/setup_middleware_model.py delete

    # Update existing model
    python src/setup_middleware_model.py update
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import json
from src.config import Config

# Typesense configuration
TYPESENSE_URL = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"
TYPESENSE_API_KEY = Config.TYPESENSE_API_KEY

# Model configuration
MODEL_ID = "custom-rag-middleware-v2"  # Changed to bypass Typesense cache
MIDDLEWARE_URL = "https://web-production-a5d93.up.railway.app"  # Update this for production


def get_system_prompt() -> str:
    """
    System prompt for the middleware model.

    This prompt will be sent to the middleware, which will enrich it with
    product context before calling OpenAI.

    NOTE: This uses the CONSERVATIVE FILTERING approach - same as setup_nl_model.py
    """
    return """Extract search parameters from natural language queries for medical/scientific products.

NOTE: This middleware uses RAG (Retrieval-Augmented Generation). You will receive:
1. The user's natural language query
2. Retrieved product context grouped by categories

QUERY FIELD ("q"):
- Product types in SINGULAR form: "glove" not "gloves", "pipette" not "pipettes"
- Material descriptors: "nitrile", "latex", "stainless steel", "glass"
- General features: "sterile", "powder-free", "disposable", "surgical"
- Product attributes: "blue", "yellow", "large", "medium", "Mercedes Scientific"
- Technical specifications: "10μL capacity", "100mL volume", "0.5mm thickness"
- KEEP all descriptive words in "q" for semantic search

FILTER FIELD ("filter_by") - Extract ONLY these RELIABLE filter types:

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

CATEGORY DETECTION (RAG-based):
- Analyze the retrieved product context to determine the best category match
- Use conservative rules:
  * Return null for single-word attributes: "clear", "large", "sterile"
  * Return null for brand-only queries: "Mercedes Scientific"
  * Return null for highly ambiguous queries: "filters" (water/air/syringe?)
  * Only set category when query clearly indicates a product type AND context confirms it

OPERATOR RULES:
- Exact match: := (e.g., price:=20)
- Range: : (e.g., price:<50)
- Combine filters: && (e.g., price:<50 && stock_status:=IN_STOCK)

**RESPONSE FORMAT** (MANDATORY - EVERY response must use this format):
{{
  "q": "search terms in singular form",
  "filter_by": "filters with && operators (empty string if none)",
  "sort_by": "field:direction (empty string if none)",
  "per_page": 20,
  "detected_category": "full category path or null",
  "category_confidence": 0.0-1.0,
  "category_reasoning": "brief explanation"
}}

CRITICAL: ALWAYS include ALL 7 fields above in EVERY response.
- filter_by should NEVER include category filters - only price, stock, special_price, temporal
- Category detection goes in detected_category field (separate from filter_by)
- Use FULL category path: "Products/Gloves & Apparel/Gloves" not "Gloves"
- category_confidence: 0.0-1.0 based on how confident you are about the category
- category_reasoning: Brief explanation of why you chose this category

EXAMPLES (All examples show ALL 7 required fields):

Query: "nitrile gloves under $30"
Output: {{"q": "nitrile glove", "filter_by": "price:<30", "sort_by": "", "per_page": 20, "detected_category": "Products/Gloves & Apparel/Gloves", "category_confidence": 0.90, "category_reasoning": "Clear glove product type with price filter"}}

Query: "yellow slides"
Output: {{"q": "yellow slide", "filter_by": "", "sort_by": "", "per_page": 20, "detected_category": "Products/Lab Equipment/Microscope Slides", "category_confidence": 0.85, "category_reasoning": "Slides typically refer to microscope slides in lab context"}}

Query: "clear"
Output: {{"q": "clear", "filter_by": "", "sort_by": "", "per_page": 20, "detected_category": null, "category_confidence": 0.0, "category_reasoning": "Ambiguous single-word attribute"}}

Query: "Mercedes Scientific"
Output: {{"q": "Mercedes Scientific", "filter_by": "", "sort_by": "", "per_page": 20, "detected_category": null, "category_confidence": 0.0, "category_reasoning": "Brand-only query without product type"}}

Query: "pipettes in stock"
Output: {{"q": "pipette", "filter_by": "stock_status:=IN_STOCK", "sort_by": "", "per_page": 20, "detected_category": "Products/Pipettes", "category_confidence": 0.88, "category_reasoning": "Clear pipette product type with stock filter"}}

Query: "nitrile gloves that costs $20"
Output: {{"q": "nitrile glove", "filter_by": "price:=20", "sort_by": "", "per_page": 20, "detected_category": "Products/Gloves & Apparel/Gloves", "category_confidence": 0.92, "category_reasoning": "Specific glove type with exact price"}}

Query: "beakers under $50"
Output: {{"q": "beaker", "filter_by": "price:<50", "sort_by": "", "per_page": 20, "detected_category": "Products/Lab Glassware/Beakers", "category_confidence": 0.90, "category_reasoning": "Lab glassware product with price filter"}}

Query: "cheapest centrifuge"
Output: {{"q": "centrifuge", "filter_by": "", "sort_by": "price:asc", "per_page": 20, "detected_category": "Products/Lab Equipment/Centrifuges", "category_confidence": 0.87, "category_reasoning": "Lab equipment with price sorting"}}

Query: "on sale microscopes"
Output: {{"q": "microscope", "filter_by": "special_price:>0", "sort_by": "", "per_page": 20, "detected_category": "Products/Lab Equipment/Microscopes", "category_confidence": 0.89, "category_reasoning": "Lab equipment on sale"}}

CRITICAL RULES:
1. ALWAYS return ALL 7 fields: q, filter_by, sort_by, per_page, detected_category, category_confidence, category_reasoning
2. NEVER include category in filter_by - category goes ONLY in detected_category field
3. DO NOT extract color/size/brand as filters - keep them in "q" for semantic search
   - Data is too shallow for strict attribute filtering
   - Semantic search handles color, size, brand matching naturally
4. ALWAYS keep product type in "q" for semantic search (e.g., "nitrile glove", "pipette")
5. ALWAYS extract price filter when ANY price appears:
   - DEFAULT: "costs $X", "cost $X", "priced $X" → price:=X (EXACT match)
   - RANGE: "under $X" → price:<X, "over $X" → price:>X
   - BETWEEN: "$X to $Y" → price:[X..Y]
6. ALWAYS extract stock filter when stock mentioned (in stock → stock_status:=IN_STOCK)
7. ALWAYS extract special_price filter for "on sale", "discounted" → special_price:>0
8. Technical specs (10μL, 100mL) stay in "q" - NEVER as filters
9. NEVER use sort_by for "popular", "most popular", "best selling" - rely on relevance scoring
10. Use retrieved product context to determine category (RAG), but be conservative
11. Use FULL category path in detected_category: "Products/Gloves & Apparel/Gloves" not "Gloves"

IMPORTANT: "costs", "cost", "priced" without range words = EXACT price (price:=X), NOT under (price:<X)"""


def check_model_exists() -> bool:
    """Check if the middleware model is already registered"""
    try:
        response = requests.get(
            f"{TYPESENSE_URL}/nl_search_models/{MODEL_ID}",
            headers={"X-TYPESENSE-API-KEY": TYPESENSE_API_KEY}
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking model: {e}")
        return False


def delete_model():
    """Delete the existing middleware model"""
    try:
        response = requests.delete(
            f"{TYPESENSE_URL}/nl_search_models/{MODEL_ID}",
            headers={"X-TYPESENSE-API-KEY": TYPESENSE_API_KEY}
        )

        if response.status_code == 200:
            print(f"✓ Successfully deleted model '{MODEL_ID}'")
            return True
        else:
            print(f"✗ Failed to delete model: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Error deleting model: {e}")
        return False


def register_model(middleware_url: str = MIDDLEWARE_URL):
    """Register the middleware endpoint with Typesense"""

    # Validate that OpenAI API key is available
    if not Config.OPENAI_API_KEY:
        print("✗ Error: OPENAI_API_KEY not found in environment")
        print("  Please set OPENAI_API_KEY in your .env file")
        return False

    model_config = {
        "id": MODEL_ID,
        "model_name": "openai/gpt-4o-mini",  # Use OpenAI namespace for OpenAI-compatible endpoint
        "api_key": Config.OPENAI_API_KEY,
        "api_base": middleware_url,  # Base URL without the endpoint path
        "system_prompt": get_system_prompt(),
        "max_bytes": 16000,
        "temperature": 0.0
    }

    print(f"\nRegistering middleware with Typesense...")
    print(f"  Middleware URL: {middleware_url}")
    print(f"  Model ID: {MODEL_ID}")
    print(f"\nNote: Typesense will validate the configuration by making a test call.")
    print(f"      This may take a few seconds...\n")

    try:
        response = requests.post(
            f"{TYPESENSE_URL}/nl_search_models",
            json=model_config,
            headers={
                "X-TYPESENSE-API-KEY": TYPESENSE_API_KEY,
                "Content-Type": "application/json"
            }
        )

        if response.status_code in [200, 201]:
            action = "registered" if response.status_code == 201 else "updated"
            print(f"✓ Successfully {action} middleware model!")
            print(f"\nModel ID: {MODEL_ID}")
            print(f"Middleware URL: {middleware_url}")
            print(f"\nTo use this model in searches:")
            print(f'  "nl_model_id": "{MODEL_ID}"')
            print(f"\nNext steps:")
            print(f'  1. Test: ./venv/bin/python src/test_middleware.py case "nitrile gloves"')
            print(f'  2. Run full test suite: ./venv/bin/python src/test_middleware.py all')
            return True
        else:
            print(f"✗ Failed to register model: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Error registering model: {e}")
        return False


def update_model(middleware_url: str = MIDDLEWARE_URL):
    """Update existing model configuration"""
    if not check_model_exists():
        print(f"Model '{MODEL_ID}' does not exist. Use 'register' instead.")
        return False

    print(f"Updating model '{MODEL_ID}'...")
    if delete_model():
        return register_model(middleware_url)
    else:
        return False


def show_model_info():
    """Display current model configuration"""
    try:
        response = requests.get(
            f"{TYPESENSE_URL}/nl_search_models/{MODEL_ID}",
            headers={"X-TYPESENSE-API-KEY": TYPESENSE_API_KEY}
        )

        if response.status_code == 200:
            model_info = response.json()
            print(f"\nModel Configuration:")
            print(f"  ID: {model_info.get('id')}")
            print(f"  Model: {model_info.get('model_name')}")
            print(f"  API Base: {model_info.get('api_base')}")
            print(f"  Temperature: {model_info.get('temperature')}")
            print(f"  Max Bytes: {model_info.get('max_bytes')}")
            print(f"\nSystem Prompt Preview:")
            prompt = model_info.get('system_prompt', '')
            print(f"  {prompt[:200]}...")
            return True
        else:
            print(f"✗ Model '{MODEL_ID}' not found")
            return False

    except Exception as e:
        print(f"✗ Error fetching model info: {e}")
        return False


def main():
    """Main entry point"""
    command = sys.argv[1] if len(sys.argv) > 1 else "register"

    if command == "check":
        if check_model_exists():
            print(f"✓ Model '{MODEL_ID}' exists")
            show_model_info()
        else:
            print(f"✗ Model '{MODEL_ID}' does not exist")

    elif command == "delete":
        delete_model()

    elif command == "update":
        middleware_url = sys.argv[2] if len(sys.argv) > 2 else MIDDLEWARE_URL
        update_model(middleware_url)

    elif command == "register":
        middleware_url = sys.argv[2] if len(sys.argv) > 2 else MIDDLEWARE_URL

        if check_model_exists():
            print(f"⚠ Model '{MODEL_ID}' already exists.")
            response = input("Do you want to update it? (y/n): ")
            if response.lower() == 'y':
                update_model(middleware_url)
            else:
                print("Skipping registration.")
        else:
            register_model(middleware_url)

    else:
        print(f"Unknown command: {command}")
        print("\nUsage:")
        print("  python src/setup_middleware_model.py [command] [middleware_url]")
        print("\nCommands:")
        print("  register [url]  - Register middleware endpoint (default: http://localhost:8000)")
        print("  check           - Check if model exists")
        print("  delete          - Delete existing model")
        print("  update [url]    - Update existing model")


if __name__ == "__main__":
    main()
