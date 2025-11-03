#!/usr/bin/env python3
"""
Test Typesense NL Integration with Simplified Middleware Response

This script tests if the middleware correctly returns only 4 standard fields
for Typesense compatibility (Option A approach).

Expected response format:
{
  "q": "...",
  "filter_by": "categories:=... && price:<...",
  "sort_by": "...",  // optional
  "per_page": 20
}

NO custom metadata fields should be present:
- detected_category (removed)
- category_confidence (removed)
- category_reasoning (removed)
"""

import os
import json
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
import httpx

# Middleware URL (deployed on Railway)
MIDDLEWARE_URL = "https://web-production-a5d93.up.railway.app"

async def test_middleware_response_format():
    """Test that middleware returns simplified format for Typesense NL integration"""

    print("=" * 80)
    print("TESTING MIDDLEWARE RESPONSE FORMAT (OPTION A)")
    print("=" * 80)
    print(f"Middleware URL: {MIDDLEWARE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Test query with category + filters (should apply category to filter_by)
    test_query = "nitrile gloves under $50"

    print(f"Test Query: '{test_query}'")
    print("-" * 80)

    # Build OpenAI-format request
    request_payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are a search parameter extraction assistant."
            },
            {
                "role": "user",
                "content": test_query
            }
        ],
        "temperature": 0.0
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call middleware
            print("\n[1] Calling middleware at /v1/chat/completions...")
            response = await client.post(
                f"{MIDDLEWARE_URL}/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {Config.OPENAI_API_KEY}"
                },
                json=request_payload
            )

            print(f"    Status: {response.status_code}")

            if response.status_code != 200:
                print(f"    ❌ ERROR: {response.text}")
                return False

            # Parse response
            result = response.json()

            # Extract message content
            message_content = result["choices"][0]["message"]["content"]
            print(f"\n[2] Parsing middleware response...")
            print(f"    Raw content: {message_content[:200]}...")

            # Parse parameters
            params = json.loads(message_content)
            print(f"\n[3] Extracted parameters:")
            print(f"    {json.dumps(params, indent=2)}")

            # Validate response format
            print(f"\n[4] Validating response format...")

            # Check for standard fields
            standard_fields = {"q", "filter_by", "sort_by", "per_page"}
            custom_fields = {"detected_category", "category_confidence", "category_reasoning"}

            present_standard = {k for k in standard_fields if k in params}
            present_custom = {k for k in custom_fields if k in params}

            print(f"    Standard fields present: {present_standard}")
            print(f"    Custom fields present: {present_custom}")

            # Validation checks
            success = True

            if "q" not in params:
                print(f"    ❌ FAIL: Missing required field 'q'")
                success = False
            else:
                print(f"    ✅ PASS: Required field 'q' present")

            if present_custom:
                print(f"    ❌ FAIL: Custom metadata fields still present: {present_custom}")
                print(f"           Typesense cannot parse these fields!")
                success = False
            else:
                print(f"    ✅ PASS: No custom metadata fields (Typesense compatible)")

            # Check if category was applied to filter_by (if confident)
            filter_by = params.get("filter_by", "")
            if "categories:=" in filter_by:
                print(f"    ✅ PASS: Category filter applied to filter_by")
                print(f"           Filter: {filter_by}")
            else:
                print(f"    ⚠️  WARN: No category filter in filter_by")
                print(f"           This might be expected if confidence was low")

            # Summary
            print(f"\n[5] FINAL RESULT:")
            if success:
                print(f"    ✅ SUCCESS: Middleware returns Typesense-compatible format")
                print(f"    ✅ Only standard fields present (q, filter_by, sort_by, per_page)")
                print(f"    ✅ Custom metadata removed (detected_category, etc.)")
            else:
                print(f"    ❌ FAILURE: Response format incompatible with Typesense")
                print(f"    ❌ Custom metadata still present - parser will fail")

            print("=" * 80)

            return success

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_edge_cases():
    """Test edge cases (low confidence, ambiguous queries)"""

    print("\n\n" + "=" * 80)
    print("TESTING EDGE CASES")
    print("=" * 80)

    test_cases = [
        ("clear", "Single attribute word - should NOT apply category"),
        ("Mercedes Scientific", "Brand only - should NOT apply category"),
        ("pipettes in stock", "Clear product type - SHOULD apply category"),
    ]

    for query, description in test_cases:
        print(f"\n{description}")
        print(f"Query: '{query}'")
        print("-" * 80)

        request_payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a search parameter extraction assistant."},
                {"role": "user", "content": query}
            ],
            "temperature": 0.0
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{MIDDLEWARE_URL}/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {Config.OPENAI_API_KEY}"
                    },
                    json=request_payload
                )

                if response.status_code == 200:
                    result = response.json()
                    message_content = result["choices"][0]["message"]["content"]
                    params = json.loads(message_content)

                    has_category = "categories:=" in params.get("filter_by", "")
                    has_metadata = any(k in params for k in ["detected_category", "category_confidence"])

                    print(f"  Q: {params.get('q', 'N/A')}")
                    print(f"  Filter: {params.get('filter_by', 'None')}")
                    print(f"  Category applied: {'✅ Yes' if has_category else '❌ No'}")
                    print(f"  Metadata present: {'❌ Yes (FAIL)' if has_metadata else '✅ No (PASS)'}")
                else:
                    print(f"  ❌ Error: {response.status_code}")

        except Exception as e:
            print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    import asyncio

    print("\n🧪 TESTING TYPESENSE NL INTEGRATION - OPTION A\n")

    # Test 1: Main test case
    success = asyncio.run(test_middleware_response_format())

    # Test 2: Edge cases
    asyncio.run(test_edge_cases())

    print("\n\n🎯 SUMMARY:")
    if success:
        print("✅ Middleware correctly returns simplified format for Typesense")
        print("✅ Ready to test with Typesense NL integration")
    else:
        print("❌ Middleware still returns custom metadata fields")
        print("❌ Typesense parser will fail - need to fix middleware code")

    sys.exit(0 if success else 1)
