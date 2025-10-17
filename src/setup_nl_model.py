"""Setup natural language search model in Typesense.

This script registers an OpenAI model with Typesense for native NL search.
Must be run before using nl_query=true in search requests.
"""
import typesense
import requests
from config import Config

# Validate configuration
Config.validate()


def setup_nl_model():
    """Register OpenAI model with Typesense for natural language search."""

    # Build Typesense URL
    base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"

    # Balanced system prompt - extracts filters when clearly mentioned
    system_prompt = """Extract search parameters from natural language queries for medical/scientific products.

QUERY FIELD ("q"):
- Product types in SINGULAR form: "glove" not "gloves", "pipette" not "pipettes"
- Material descriptors: "nitrile", "latex", "stainless steel", "glass"
- General features: "sterile", "powder-free", "disposable", "surgical"
- Technical specifications: "10μL capacity", "100mL volume", "0.5mm thickness"

FILTER FIELD ("filter_by") - Extract when clearly mentioned:
1. Category filters (extract when product type is clearly mentioned):
   - "gloves" or "glove" → categories:=Products/Gloves & Apparel/Gloves
   - "pipettes" or "pipette" → categories:=Products/Pipettes
   - "microscope slides" or "slides" → categories:=Products/Microscope Slides
   - "centrifuge" → categories:=Products/Equipment & Accessories/Centrifuges
   - "beaker" or "beakers" → categories:=Products/Glass & Plasticware/Beakers
   - "centrifuge tubes" → categories:=Products/Glass & Plasticware/Tubes/Centrifuge Tubes
   - "culture tubes" → categories:=Products/Glass & Plasticware/Tubes/Culture Tubes
   - "micro tubes" or "microtubes" → categories:=Products/Glass & Plasticware/Tubes/Micro Tubes
   - "deep well plates" → categories:=Products/Deep Well Plates & Accessories/Deep well plates
   - "reagent" or "reagents" → categories:=Products/Reagents

2. Price filters (ALWAYS extract when ANY price is mentioned):
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

3. Stock filters (extract when stock mentioned):
   - "in stock" or "available" → stock_status:=IN_STOCK

4. Product attributes (exact match only when EXPLICITLY stated):
   - Brand: "Mercedes Scientific brand" → brand:=Mercedes Scientific
   - Size: "size large" or "large size" → size:=Large
   - Color: "blue color" or "color blue" → color:=Blue

SORT FIELD ("sort_by"):
- "cheapest" or "lowest price" → price:asc
- "most expensive" or "highest price" → price:desc
- "latest" or "newest" → created_at:desc
- "popular" or "most popular" or "best selling" → DO NOT use sort_by (rely on relevance scoring)

OPERATOR RULES:
- Exact match: := (e.g., brand:=Mercedes Scientific)
- Range: : (e.g., price:<50)
- Combine filters: && (e.g., price:<50 && stock_status:=IN_STOCK)

EXAMPLES:
"nitrile gloves under $30" → {"q": "nitrile glove", "filter_by": "categories:=Products/Gloves & Apparel/Gloves && price:<30"}
"pipettes in stock" → {"q": "pipette", "filter_by": "categories:=Products/Pipettes && stock_status:=IN_STOCK"}
"nitrile gloves that costs $20" → {"q": "nitrile glove", "filter_by": "categories:=Products/Gloves & Apparel/Gloves && price:=20"}
"nitrile gloves priced $20" → {"q": "nitrile glove", "filter_by": "categories:=Products/Gloves & Apparel/Gloves && price:=20"}
"pipettes with at least 10μL capacity under $500" → {"q": "pipette 10μL capacity", "filter_by": "categories:=Products/Pipettes && price:<500"}
"nitrile gloves powder-free in stock under $30" → {"q": "nitrile glove powder-free", "filter_by": "categories:=Products/Gloves & Apparel/Gloves && stock_status:=IN_STOCK && price:<30"}
"beakers under $50" → {"q": "beaker", "filter_by": "categories:=Products/Glass & Plasticware/Beakers && price:<50"}
"cheapest centrifuge" → {"q": "centrifuge", "filter_by": "categories:=Products/Equipment & Accessories/Centrifuges", "sort_by": "price:asc"}
"most popular lab equipment" → {"q": "lab equipment"}

CRITICAL RULES:
1. ALWAYS extract category filter when product type is mentioned (if mapping exists)
2. ALWAYS extract price filter when ANY price appears:
   - DEFAULT: "costs $X", "cost $X", "priced $X" → price:=X (EXACT match)
   - RANGE: "under $X" → price:<X, "over $X" → price:>X
   - BETWEEN: "$X to $Y" → price:[X..Y]
3. ALWAYS extract stock filter when stock mentioned (in stock → stock_status:=IN_STOCK)
4. Technical specs (10μL, 100mL) stay in "q" - NEVER as filters
5. Only extract size/color/brand as filters when EXPLICITLY stated as attributes
6. Remove price phrases from "q" after extracting as filter
7. NEVER use sort_by for "popular", "most popular", "best selling" - rely on relevance scoring

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
            print("Natural Language Search is now enabled!")
            print("=" * 60)
            print("\nNext steps:")
            print("  1. Your search.py will now work with nl_query=true")
            print("  2. Test with: python src/search.py")
            print("  3. Or start API: python src/app.py")
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
