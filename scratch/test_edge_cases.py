#!/usr/bin/env python3
"""Test edge cases for middleware response format"""

import requests
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.config import Config

MIDDLEWARE_URL = "http://localhost:8000"

test_cases = [
    ("clear", "Should NOT apply category (single attribute)"),
    ("Mercedes Scientific", "Should NOT apply category (brand only)"),
    ("pipettes in stock", "SHOULD apply category (clear product type)"),
    ("gloves under $30", "SHOULD apply category (product + filter)"),
]

def test_query(query, description):
    print(f"\nQuery: '{query}'")
    print(f"Expected: {description}")
    print("-" * 80)

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Search parameter extraction."},
            {"role": "user", "content": query}
        ],
        "temperature": 0.0
    }

    response = requests.post(
        f"{MIDDLEWARE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.OPENAI_API_KEY}"
        },
        json=payload,
        timeout=30
    )

    if response.status_code == 200:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        params = json.loads(content)

        has_category = "categories:=" in params.get("filter_by", "")
        has_metadata = any(k in params for k in ["detected_category", "category_confidence", "category_reasoning"])

        print(f"  q: {params.get('q', 'N/A')}")
        print(f"  filter_by: {params.get('filter_by', 'None')}")
        print(f"  Category applied: {'✅ Yes' if has_category else '❌ No'}")
        print(f"  Metadata removed: {'✅ Yes' if not has_metadata else '❌ No (FAIL)'}")

        return not has_metadata
    else:
        print(f"  ❌ Error: {response.status_code}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("TESTING EDGE CASES")
    print("=" * 80)

    all_passed = True
    for query, description in test_cases:
        passed = test_query(query, description)
        all_passed = all_passed and passed

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED: Metadata removed in all cases")
    else:
        print("❌ SOME TESTS FAILED: Metadata still present")

    sys.exit(0 if all_passed else 1)
