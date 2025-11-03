#!/usr/bin/env python3
"""Test if Railway middleware has the updated RAG prompt"""

import requests
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.config import Config

RAILWAY_URL = "https://web-production-a5d93.up.railway.app"

def test_gloves_query():
    """Test that 'gloves' now gets proper category classification"""

    print("=" * 80)
    print("Testing Railway Middleware - 'Gloves' Category Classification")
    print("=" * 80)

    query = "gloves in stock under $50"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Search parameter extraction."},
            {"role": "user", "content": query}
        ],
        "temperature": 0.0
    }

    print(f"\nQuery: '{query}'")
    print(f"Testing: {RAILWAY_URL}")

    try:
        response = requests.post(
            f"{RAILWAY_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}"
            },
            json=payload,
            timeout=30
        )

        print(f"\nStatus: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ ERROR: {response.text}")
            return False

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        params = json.loads(content)

        print("\n" + "-" * 80)
        print("Middleware Response:")
        print(json.dumps(params, indent=2))

        # Check if category detection worked
        has_category = "categories:=" in params.get("filter_by", "")
        detected_category = params.get("detected_category")
        confidence = params.get("category_confidence", 0.0)

        print("\n" + "-" * 80)
        print("Analysis:")
        print(f"  Detected category: {detected_category or 'None'}")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Category in filter_by: {'✅ Yes' if has_category else '❌ No'}")

        # Validation
        if confidence >= 0.75 and has_category:
            print("\n✅ SUCCESS: Category classification is working!")
            print("   Railway middleware has been updated with the fix.")
            return True
        else:
            print("\n❌ STILL BROKEN: Category classification not working")
            print("   Railway might not have deployed yet, or deployment failed")
            print("\n   Expected:")
            print("     - Confidence >= 0.75")
            print("     - Category in filter_by")
            print("\n   Actual:")
            print(f"     - Confidence: {confidence:.2f}")
            print(f"     - Category in filter_by: {has_category}")
            return False

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🧪 TESTING RAILWAY MIDDLEWARE UPDATE\n")
    success = test_gloves_query()

    if success:
        print("\n🎉 READY TO USE!")
        print("   The RAG category classification fix is deployed and working.")
    else:
        print("\n⏳ DEPLOYMENT PENDING")
        print("   Wait for Railway to finish deploying, then test again.")
        print("\n   Check deployment status:")
        print("   https://railway.app/project/5b7b2ee5-6273-4627-96b9-2a310547d63b")

    sys.exit(0 if success else 1)
