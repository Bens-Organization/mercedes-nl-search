"""Export the NL model's system prompt from Typesense.

This script retrieves the registered NL model configuration from Typesense
and exports its system prompt to a text file.
"""
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import json
from src.config import Config

# Validate configuration
Config.validate()


def export_system_prompt(output_file: str = None):
    """
    Export the NL model's system prompt from Typesense.

    Args:
        output_file: Path to output file (default: database/typesense/nl_model_system_prompt.txt)
    """
    # Default output file
    if output_file is None:
        output_file = "database/typesense/nl_model_system_prompt.txt"

    # Build Typesense URL
    base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"

    # The model ID (UUID assigned by Typesense)
    model_id = "openai-gpt4o-mini"

    print("=" * 70)
    print("NL Model System Prompt Exporter")
    print("=" * 70)
    print(f"Typesense URL: {base_url}")
    print(f"Model ID: {model_id}")
    print("=" * 70)

    headers = {
        "X-TYPESENSE-API-KEY": Config.TYPESENSE_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        # Get the model configuration
        model_url = f"{base_url}/nl_search_models/{model_id}"
        response = requests.get(model_url, headers=headers)

        if response.status_code == 200:
            model_config = response.json()

            print(f"\n✓ Model found: {model_id}")
            print(f"  Model Name: {model_config.get('model_name', 'N/A')}")
            print(f"  Temperature: {model_config.get('temperature', 'N/A')}")
            print(f"  Max Bytes: {model_config.get('max_bytes', 'N/A')}")

            # Extract system prompt
            system_prompt = model_config.get('system_prompt', '')

            if system_prompt:
                # Save to file
                output_path = Path(output_file)
                output_path.write_text(system_prompt, encoding='utf-8')

                print(f"\n✓ System prompt exported to: {output_path.absolute()}")
                print(f"  Prompt length: {len(system_prompt)} characters")
                print(f"  Prompt lines: {len(system_prompt.splitlines())} lines")

                # Show first few lines
                lines = system_prompt.splitlines()
                print(f"\n--- First 10 lines ---")
                for i, line in enumerate(lines[:10], 1):
                    print(f"{i:3d}: {line[:100]}")

                if len(lines) > 10:
                    print(f"... ({len(lines) - 10} more lines)")

                # Also save as JSON for complete config
                json_output = output_path.with_suffix('.json')
                json_output.write_text(json.dumps(model_config, indent=2), encoding='utf-8')
                print(f"\n✓ Full model config saved to: {json_output.absolute()}")

            else:
                print(f"\n✗ No system prompt found in model configuration")
                print(f"  Available keys: {list(model_config.keys())}")

        elif response.status_code == 404:
            print(f"\n✗ Model '{model_id}' not found")
            print(f"\nTip: Run 'python src/setup_nl_model.py' to register the model")

            # Try to list all available models
            list_url = f"{base_url}/nl_search_models"
            list_response = requests.get(list_url, headers=headers)
            if list_response.status_code == 200:
                models = list_response.json()
                if models:
                    print(f"\nAvailable models:")
                    for model in models:
                        print(f"  - {model.get('id', 'N/A')} ({model.get('model_name', 'N/A')})")
                else:
                    print(f"\nNo models found. Register one with: python src/setup_nl_model.py")
        else:
            print(f"\n✗ Error: {response.status_code}")
            print(f"  Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Connection error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Typesense server is running")
        print(f"  2. Check Typesense URL: {base_url}")
        print("  3. Verify TYPESENSE_API_KEY in .env")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def compare_with_file_version():
    """Compare the exported prompt with the one in setup_nl_model.py."""
    print("\n" + "=" * 70)
    print("Comparing with setup_nl_model.py")
    print("=" * 70)

    try:
        # Read the setup file
        setup_file = Path(__file__).parent / "setup_nl_model.py"
        setup_content = setup_file.read_text(encoding='utf-8')

        # Extract the system_prompt variable from the file
        # This is a simple extraction - looks for the system_prompt = """ ... """ block
        import re
        pattern = r'system_prompt\s*=\s*"""(.*?)"""'
        match = re.search(pattern, setup_content, re.DOTALL)

        if match:
            file_prompt = match.group(1).strip()
            exported_prompt = Path("database/typesense/nl_model_system_prompt.txt").read_text(encoding='utf-8').strip()

            if file_prompt == exported_prompt:
                print("\n✓ System prompts match!")
                print("  The deployed model uses the same prompt as in setup_nl_model.py")
            else:
                print("\n⚠ System prompts differ!")
                print(f"  File version: {len(file_prompt)} chars")
                print(f"  Deployed version: {len(exported_prompt)} chars")
                print("\n  This might mean:")
                print("  1. The model was updated manually via Typesense API")
                print("  2. The setup_nl_model.py file was changed but model not re-registered")
                print("\n  To sync: Run 'python src/setup_nl_model.py' and choose to recreate")
        else:
            print("\n✗ Could not extract system_prompt from setup_nl_model.py")

    except Exception as e:
        print(f"\n✗ Error comparing: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Export NL model system prompt from Typesense"
    )
    parser.add_argument(
        "-o", "--output",
        default="database/typesense/nl_model_system_prompt.txt",
        help="Output file path (default: database/typesense/nl_model_system_prompt.txt)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare exported prompt with setup_nl_model.py version"
    )

    args = parser.parse_args()

    # Export the system prompt
    export_system_prompt(args.output)

    # Compare if requested
    if args.compare:
        compare_with_file_version()

    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70)
