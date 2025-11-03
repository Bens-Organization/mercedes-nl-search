"""
Test Middleware Response Format for Typesense NL Integration

This script tests that the middleware returns the correct format when called
by Typesense NL (without context), ensuring only standard fields are returned.

Expected behavior:
- When context=None (Typesense NL mode): Return only {q, filter_by, sort_by}
- When context provided (decoupled mode): Return all fields including metadata
"""

import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Middleware URL (local or production)
MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "http://localhost:8000")

def test_typesense_nl_format():
    """
    Test that middleware returns minimal format when called without context.
    This simulates how Typesense NL would call the middleware.
    """
    print("\n" + "="*80)
    print("TEST: Typesense NL Format (No Context)")
    print("="*80)

    # Simulate Typesense NL call (no context)
    request_body = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "Extract search parameters from natural language queries."
            },
            {
                "role": "user",
                "content": "nitrile gloves under $50"
            }
        ],
        "temperature": 0.0
        # NO context field - this triggers Typesense NL mode
    }

    print(f"\n[REQUEST] Calling {MIDDLEWARE_URL}/v1/chat/completions")
    print(f"[REQUEST] Body: {json.dumps(request_body, indent=2)}")

    response = httpx.post(
        f"{MIDDLEWARE_URL}/v1/chat/completions",
        json=request_body,
        timeout=30.0
    )

    print(f"\n[RESPONSE] Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        params = json.loads(content)

        print(f"[RESPONSE] Content: {json.dumps(params, indent=2)}")

        # Verify format
        print("\n[VALIDATION] Checking response format...")

        # These fields SHOULD be present
        assert "q" in params, "❌ Missing 'q' field"
        print("✅ 'q' field present")

        # These fields SHOULD NOT be present (metadata removed for Typesense)
        metadata_fields = ["detected_category", "category_confidence", "category_reasoning", "per_page"]
        for field in metadata_fields:
            if field in params:
                print(f"❌ FAIL: '{field}' should be removed for Typesense NL mode")
                return False
            else:
                print(f"✅ '{field}' correctly removed")

        # filter_by and sort_by are optional (only if needed)
        if "filter_by" in params:
            print(f"✅ 'filter_by' present: {params['filter_by']}")
        if "sort_by" in params:
            print(f"✅ 'sort_by' present: {params['sort_by']}")

        # Check if category was applied to filter_by
        if "filter_by" in params and "categories:=" in params["filter_by"]:
            print(f"✅ Category filter applied in filter_by!")

        print("\n✅ TEST PASSED: Middleware returns Typesense-compatible format")
        return True
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(response.text)
        return False


def test_decoupled_format():
    """
    Test that middleware returns full format when called with context.
    This simulates how the API calls the middleware in decoupled mode.
    """
    print("\n" + "="*80)
    print("TEST: Decoupled Format (With Context)")
    print("="*80)

    # Simulate decoupled API call (with context)
    request_body = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "Extract search parameters from natural language queries."
            },
            {
                "role": "user",
                "content": "nitrile gloves under $50"
            }
        ],
        "temperature": 0.0,
        "context": []  # Providing context triggers decoupled mode
    }

    print(f"\n[REQUEST] Calling {MIDDLEWARE_URL}/v1/chat/completions")
    print(f"[REQUEST] Body: {json.dumps(request_body, indent=2)}")

    response = httpx.post(
        f"{MIDDLEWARE_URL}/v1/chat/completions",
        json=request_body,
        timeout=30.0
    )

    print(f"\n[RESPONSE] Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        params = json.loads(content)

        print(f"[RESPONSE] Content: {json.dumps(params, indent=2)}")

        # Verify format
        print("\n[VALIDATION] Checking response format...")

        # These fields SHOULD be present in decoupled mode
        expected_fields = ["q", "detected_category", "category_confidence", "category_reasoning"]
        for field in expected_fields:
            if field in params:
                print(f"✅ '{field}' present: {params[field]}")
            else:
                print(f"❌ FAIL: '{field}' missing in decoupled mode")
                return False

        print("\n✅ TEST PASSED: Middleware returns full metadata in decoupled mode")
        return True
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(response.text)
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("MIDDLEWARE FORMAT VALIDATION TESTS")
    print("="*80)
    print(f"Middleware URL: {MIDDLEWARE_URL}")

    # Test both modes
    test1 = test_typesense_nl_format()
    test2 = test_decoupled_format()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Typesense NL Format: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Decoupled Format: {'✅ PASS' if test2 else '❌ FAIL'}")

    if test1 and test2:
        print("\n🎉 ALL TESTS PASSED! Middleware is ready for Typesense NL integration.")
    else:
        print("\n❌ SOME TESTS FAILED! Please review the middleware implementation.")
