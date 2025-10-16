#!/usr/bin/env python3
"""Test configuration and connections."""

import sys
import requests

# Add src to path
sys.path.insert(0, 'src')

from config import Config

print("=" * 60)
print("Testing Configuration")
print("=" * 60)

# Test 1: Check environment variables
print("\n1. Checking environment variables...")
try:
    Config.validate()
    print("   ✓ OpenAI API Key: Set")
    print("   ✓ Typesense API Key: Set")
except ValueError as e:
    print(f"   ✗ Error: {e}")
    print("\n   Please edit .env and add your API keys")
    sys.exit(1)

# Test 2: Check Typesense connection
print("\n2. Testing Typesense connection...")
try:
    url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}/health"
    response = requests.get(url, timeout=5)
    if response.ok:
        print(f"   ✓ Typesense is running at {url}")
    else:
        print(f"   ✗ Typesense returned status {response.status_code}")
except Exception as e:
    print(f"   ✗ Cannot connect to Typesense: {e}")
    print("\n   Make sure Typesense Docker container is running:")
    print("   docker run -p 8108:8108 -v$(pwd)/typesense-data:/data typesense/typesense:29.0 \\")
    print("     --data-dir /data --api-key=xyz --enable-cors")
    sys.exit(1)

# Test 3: Test Typesense authentication
print("\n3. Testing Typesense authentication...")
try:
    import typesense
    client = typesense.Client(Config.get_typesense_config())
    # Try to list collections (will work even if empty)
    collections = client.collections.retrieve()
    print(f"   ✓ Successfully authenticated (Found {len(collections)} collections)")
except Exception as e:
    print(f"   ✗ Authentication failed: {e}")
    print(f"\n   Check that TYPESENSE_API_KEY in .env matches your Docker command")
    sys.exit(1)

# Test 4: Test Mercedes GraphQL API
print("\n4. Testing Mercedes GraphQL API...")
try:
    response = requests.post(
        Config.MERCEDES_GRAPHQL_URL,
        json={"query": "{ __typename }"},
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    if response.ok:
        print(f"   ✓ Mercedes GraphQL API is accessible")
    else:
        print(f"   ✗ Mercedes API returned status {response.status_code}")
except Exception as e:
    print(f"   ✗ Cannot connect to Mercedes API: {e}")

# Test 5: Test OpenAI API
print("\n5. Testing OpenAI API...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=Config.OPENAI_API_KEY)
    # Make a minimal test call
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=5
    )
    print(f"   ✓ OpenAI API is working (Model: {response.model})")
except Exception as e:
    print(f"   ✗ OpenAI API error: {e}")
    print("\n   Check your OPENAI_API_KEY in .env")
    print("   Get a key from: https://platform.openai.com/api-keys")

print("\n" + "=" * 60)
print("✓ Configuration test complete!")
print("=" * 60)
print("\nYou're ready to:")
print("  1. Index products: python src/indexer.py")
print("  2. Start API: python src/app.py")
print()
