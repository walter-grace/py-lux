#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test for RapidAPI Facebook Marketplace - single query
"""

import os
import sys
import json
from dotenv import load_dotenv
import requests

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.config import load_env

load_dotenv(".env")
load_dotenv(".env.local", override=True)

env = load_env()
api_key = env.get("RAPIDAPI_KEY")

if not api_key:
    print("Error: RAPIDAPI_KEY not found")
    sys.exit(1)

url = "https://facebook-marketplace1.p.rapidapi.com/search"
headers = {
    "x-rapidapi-host": "facebook-marketplace1.p.rapidapi.com",
    "x-rapidapi-key": api_key
}

# Minimal test query - only 1 item to conserve API calls
# IMPORTANT: Free tier has only 30 requests/month
params = {
    "query": "YSL boots",
    "city": "los angeles",
    "sort": "newest",
    "limit": "1"  # Only 1 item for testing
}

print("Testing RapidAPI Facebook Marketplace API")
print("=" * 70)
print(f"URL: {url}")
print(f"Params: {json.dumps(params, indent=2)}")
print("\nSending request...")

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n[SUCCESS] Response received!")
        print(f"Response Type: {type(data)}")
        
        if isinstance(data, list):
            print(f"Number of items: {len(data)}")
            if len(data) > 0:
                print(f"\nFirst item structure:")
                print(json.dumps(data[0], indent=2, ensure_ascii=False))
        elif isinstance(data, dict):
            print(f"Response structure:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"Response: {data}")
    else:
        print(f"\n[ERROR] Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 403:
            print("\n⚠️  You need to subscribe to the Facebook Marketplace API on RapidAPI:")
            print("   1. Go to https://rapidapi.com/")
            print("   2. Search for 'Facebook Marketplace'")
            print("   3. Subscribe to the API")
            print("   4. Make sure your API key is associated with the subscription")
        elif response.status_code == 429:
            print("\n⚠️  Rate limit exceeded. Wait a moment and try again.")
            
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

