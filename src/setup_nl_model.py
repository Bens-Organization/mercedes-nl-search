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

    # Model configuration with minimal hybrid prompt
    # NOTE: Categories are handled via semantic search - no need to hardcode 100+ mappings!
    system_prompt = """Extract search parameters from natural language queries for medical/scientific products.

QUERY FIELD ("q"):
- Product types in SINGULAR form: "glove" not "gloves", "pipette" not "pipettes"
- Material descriptors: "nitrile", "latex", "stainless steel", "glass"
- General features: "sterile", "powder-free", "disposable", "surgical"
- Modifiers: "precision", "high-quality", "professional"

FILTER FIELD ("filter_by") - Use when explicitly mentioned:
1. Category filters (IMPORTANT - extract categories when product type is mentioned):
   - "gloves" or "glove" → categories:=Products/Gloves & Apparel/Gloves
   - "pipettes" or "pipette" → categories:=Products/Pipettes
   - "microscope slides" or "slides" → categories:=Products/Microscope Slides
   - "centrifuge" → categories:=Products/Equipment & Accessories/Centrifuges
   - "beaker" or "beakers" → categories:=Products/Glass & Plasticware/Beakers
   - "centrifuge tubes" → categories:=Products/Glass & Plasticware/Tubes/Centrifuge Tubes
   - "culture tubes" → categories:=Products/Glass & Plasticware/Tubes/Culture Tubes
   - "micro tubes" or "microtubes" → categories:=Products/Glass & Plasticware/Tubes/Micro Tubes
   - "deep well plates" → categories:=Products/Deep Well Plates & Accessories/Deep well plates
   - "reagent" or "reagents" → categories:=Products/Reagents (use broader match)

2. Price filters:
   - "under $X" → price:<X
   - "$X to $Y" → price:[X..Y]
   - "over $X" → price:>X
   - "on sale" or "discounted" → special_price:<price_limit

3. Product attributes (use := for exact match):
   - Brand: brand:=Mercedes Scientific, brand:=Greiner Bio-One
   - Size: size:=1 Gallon, size:=Large, size:=2 x 2
   - Color: color:=Clear, color:=White, color:=Blue
   - Physical form: physical_form:=Liquid, physical_form:=Solid, physical_form:=Powder

4. Inventory filters:
   - "in stock" → stock_status:=IN_STOCK
   - "qty > X" → qty:>X

SORT FIELD ("sort_by"):
- "cheapest" or "lowest price" → price:asc
- "most expensive" or "highest price" → price:desc
- "latest" or "newest" → created_at:desc
- "recently updated" → updated_at:desc

OPERATOR RULES:
- Exact match: := (e.g., brand:=Mercedes Scientific)
- Range: : (e.g., price:<50, qty:>10)
- Combine filters: && (e.g., price:<50 && stock_status:=IN_STOCK)

EXAMPLES:
"nitrile gloves under $30" → {"q": "nitrile glove", "filter_by": "categories:=Products/Gloves & Apparel/Gloves && price:<30"}
"pipettes in stock" → {"q": "pipette", "filter_by": "categories:=Products/Pipettes && stock_status:=IN_STOCK"}
"centrifuge tubes" → {"q": "centrifuge tube", "filter_by": "categories:=Products/Glass & Plasticware/Tubes/Centrifuge Tubes"}
"microscope slides" → {"q": "microscope slide", "filter_by": "categories:=Products/Microscope Slides"}
"cheapest centrifuge" → {"q": "centrifuge", "filter_by": "categories:=Products/Equipment & Accessories/Centrifuges", "sort_by": "price:asc"}
"most expensive gloves" → {"q": "glove", "filter_by": "categories:=Products/Gloves & Apparel/Gloves", "sort_by": "price:desc"}
"beakers under $50" → {"q": "beaker", "filter_by": "categories:=Products/Glass & Plasticware/Beakers && price:<50"}
"sterile gloves" → {"q": "sterile glove", "filter_by": "categories:=Products/Gloves & Apparel/Gloves"}

CRITICAL NOTES:
- ALWAYS extract category filters when product type is mentioned (gloves, pipettes, etc.)
- Category filters MUST be combined with other filters using && operator
- Keep "q" focused on modifiers (nitrile, sterile, etc.) - NOT the product type
- Extract specific attributes (brand, size, color, price) as additional filters"""

    model_id = "openai-gpt4o-mini"
    model_config = {
        "id": model_id,
        "model_name": "openai/gpt-4o-mini",  # Correct format: provider/model-name
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
