#!/usr/bin/env python3
"""Test if Polygon API key is loaded correctly."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
import os

# Load .env
env_path = Path(__file__).parent.parent / "backend" / ".env"
load_dotenv(env_path)

# Get key
polygon_key = os.environ.get('POLYGON_API_KEY')

print("=" * 60)
print("Polygon API Key Test")
print("=" * 60)
print(f".env file path: {env_path}")
print(f".env file exists: {env_path.exists()}")
print(f"POLYGON_API_KEY found: {'YES' if polygon_key else 'NO'}")

if polygon_key:
    print(f"Key length: {len(polygon_key)} characters")
    print(f"Key starts with: {polygon_key[:10]}...")
    print(f"Key ends with: ...{polygon_key[-5:]}")
    
    # Check for common issues
    if polygon_key.startswith('"') or polygon_key.startswith("'"):
        print("⚠️  WARNING: Key has quotes at start - remove them!")
    if polygon_key.endswith('"') or polygon_key.endswith("'"):
        print("⚠️  WARNING: Key has quotes at end - remove them!")
    if ' ' in polygon_key:
        print("⚠️  WARNING: Key contains spaces - remove them!")
    if len(polygon_key) < 10:
        print("⚠️  WARNING: Key seems too short!")
    
    # Test with Polygon API
    print("\nTesting API connection...")
    try:
        from polygon import RESTClient
        client = RESTClient(polygon_key)
        
        # Try a simple API call
        ticker_details = client.get_ticker_details("AAPL")
        print("✅ SUCCESS: API key is valid!")
        print(f"   Tested with: AAPL")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        if "Unknown API Key" in str(e):
            print("\n💡 This means your API key is invalid or expired.")
            print("   Check your Polygon.io dashboard for the correct key.")
        elif "rate limit" in str(e).lower():
            print("\n💡 Rate limit hit - key is valid but you've hit API limits.")
        else:
            print(f"\n💡 Error type: {type(e).__name__}")
else:
    print("\n❌ ERROR: POLYGON_API_KEY not found in environment!")
    print("\nMake sure your backend/.env file has:")
    print("  POLYGON_API_KEY=your_key_here")
    print("\n(No quotes, no spaces around the = sign)")

print("=" * 60)
