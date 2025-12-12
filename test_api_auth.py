#!/usr/bin/env python3
"""Test API authentication and base URL"""
import os
import sys
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lib.config import load_env

load_dotenv(".env")
load_dotenv(".env.local", override=True)

env = load_env()
api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY")

if not api_key:
    print("❌ No API key found!")
    print("Please set WATCH_DATABASE_API_KEY or RAPIDAPI_KEY in .env.local")
    sys.exit(1)

print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
print()

# Test different base URLs
base_urls = [
    "https://watch-database1.p.rapidapi.com",
    "https://watch-database.p.rapidapi.com",
    "https://api.watch-database.com",
]

headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": "watch-database1.p.rapidapi.com",
    "Content-Type": "application/json"
}

for base_url in base_urls:
    print(f"Testing base URL: {base_url}")
    
    # Try root endpoint
    try:
        response = requests.get(base_url, headers=headers, timeout=10)
        print(f"  Root: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"  Root: Error - {e}")
    
    # Try common paths
    test_paths = ["/", "/health", "/status", "/api", "/v1", "/v2"]
    for path in test_paths:
        try:
            url = f"{base_url}{path}"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 404:
                print(f"  {path}: {response.status_code} - {response.text[:100]}")
        except:
            pass
    
    print()

# Check RapidAPI dashboard info
print("\n" + "="*70)
print("To find the correct endpoints:")
print("1. Go to https://rapidapi.com/makingdatameaningful-com-makingdatameaningful-com-default/api/watch-database1")
print("2. Check the 'Endpoints' section for the actual endpoint paths")
print("3. The MCP server might use different paths than direct API calls")
print("="*70)

