#!/usr/bin/env python3
"""
Test script to verify MCP server configuration and test Watch Database API
This script helps verify the API key and provides guidance for MCP testing
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lib.config import load_env

load_dotenv(".env")
load_dotenv(".env.local", override=True)

env = load_env()
api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY")

print("=" * 70)
print("Watch Database MCP Server Test")
print("=" * 70)
print()

if not api_key:
    print("❌ No API key found!")
    print("   Please set WATCH_DATABASE_API_KEY or RAPIDAPI_KEY in .env.local")
    print()
    sys.exit(1)

print(f"✅ API Key found: {api_key[:20]}...{api_key[-10:]}")
print()

# Check MCP configuration
print("MCP Server Configuration:")
print("-" * 70)
print("To test the MCP server in Cursor:")
print()
print("1. Ensure MCP is configured in Cursor settings (see MCP_CONFIG.md)")
print("2. Restart Cursor after configuration")
print("3. In Cursor chat, try asking:")
print("   - 'Search for Rolex Submariner watches in the database'")
print("   - 'What watch makes are available?'")
print("   - 'Get details for watch reference 116610LN'")
print()

# Note about endpoint paths
print("=" * 70)
print("Note: Direct API Endpoint Testing")
print("=" * 70)
print("The Python client code uses direct HTTP calls to the API.")
print("The endpoint paths may need to be verified from the RapidAPI dashboard.")
print()
print("To find correct endpoints:")
print("1. Visit: https://rapidapi.com/makingdatameaningful-com-makingdatameaningful-com-default/api/watch-database1")
print("2. Check the 'Endpoints' tab for actual paths")
print("3. The MCP server may use different paths than direct API calls")
print()
print("Common RapidAPI endpoint patterns:")
print("  - /v1/makes")
print("  - /v1/search")
print("  - /v2/makes")
print("  - /v2/search")
print()

# Test if we can at least connect
print("=" * 70)
print("Testing API Connection")
print("=" * 70)

import requests

BASE_URL = "https://watch-database1.p.rapidapi.com"
headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": "watch-database1.p.rapidapi.com",
}

try:
    # Try to get any response to verify connection
    response = requests.get(BASE_URL, headers=headers, timeout=10)
    print(f"Connection test: Status {response.status_code}")
    if response.status_code == 404:
        print("✅ API is reachable (404 means endpoint doesn't exist, but API is working)")
        print("   We need to find the correct endpoint paths")
    elif response.status_code == 401 or response.status_code == 403:
        print("❌ Authentication failed - check your API key")
    else:
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ Connection failed: {e}")

print()
print("=" * 70)
print("Next Steps:")
print("=" * 70)
print("1. Test MCP server in Cursor (ask AI assistant to search watches)")
print("2. Check RapidAPI dashboard for correct endpoint paths")
print("3. Update lib/watch_database_api.py with correct paths if needed")
print("=" * 70)

