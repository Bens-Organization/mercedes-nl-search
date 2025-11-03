#!/usr/bin/env python3
"""
Quick test of local middleware response format
"""

import requests
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.config import Config

MIDDLEWARE_URL = "http://localhost:8000"

def test_middleware():
    print("Testing local middleware response format...")
    print(f"URL: {MIDDLEWARE_URL}")
    print("-" * 80)

    # Test query
    query = "nitrile gloves under $50"
    print(f"\nTest Query: '{query}'")

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a search parameter extraction assistant."},
            {"role": "user", "content": query}
        ],
        "temperature": 0.0
    }

    # Call middleware
    response = requests.post(
        f"{MIDDLEWARE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.OPENAI_API_KEY}"
        },
        json=payload,
        timeout=30
    )

    print(f"Status: {response.status_code}")

    if response.status_code != 200:
        print(f"ERROR: {response.text}")
        return False

    # Parse response
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    params = json.loads(content)

    print("\nExtracted Parameters:")
    print(json.dumps(params, indent=2))

    # Check fields
    print("\n" + "-" * 80)
    print("Field Analysis:")

    standard = ["q", "filter_by", "sort_by", "per_page"]
    custom = ["detected_category", "category_confidence", "category_reasoning"]

    for field in standard:
        if field in params:
            print(f"  ✅ {field}: {params[field]}")

    for field in custom:
        if field in params:
            print(f"  ❌ {field}: PRESENT (should be removed!)")
        else:
            print(f"  ✅ {field}: removed (good)")

    # Final check
    has_custom = any(f in params for f in custom)
    has_category_filter = "categories:=" in params.get("filter_by", "")

    print("\n" + "=" * 80)
    if has_custom:
        print("❌ FAIL: Custom metadata still present")
        print("   Typesense cannot parse this response!")
        return False
    else:
        print("✅ PASS: Response format is Typesense-compatible")
        if has_category_filter:
            print("✅ PASS: Category filter applied to filter_by")
        else:
            print("⚠️  WARN: No category filter (might be low confidence)")
        return True

if __name__ == "__main__":
    success = test_middleware()
    sys.exit(0 if success else 1)
