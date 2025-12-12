#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test other RapidAPI endpoints: /search/url, /seller, /seller/url
"""

import os
import sys
import json
from dotenv import load_dotenv
import requests

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

base_url = "https://facebook-marketplace1.p.rapidapi.com"
headers = {
    "x-rapidapi-host": "facebook-marketplace1.p.rapidapi.com",
    "x-rapidapi-key": api_key
}

print("Testing Additional RapidAPI Endpoints")
print("=" * 70)
print("⚠️  Using 3 API calls")
print("=" * 70)

# Test 1: Search By URL
print("\nTEST 1: GET /search/url")
print("-" * 70)
test_url = "https://www.facebook.com/marketplace/search/?query=boots&city=los%20angeles"
params = {"url": test_url}

try:
    response = requests.get(f"{base_url}/search/url", headers=headers, params=params, timeout=30)
    print(f"Status: {response.status_code}")
    remaining = response.headers.get('X-RateLimit-Requests-Remaining', 'N/A')
    print(f"Remaining: {remaining}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ /search/url works! Returned {len(data) if isinstance(data, list) else 'data'}")
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Search Seller Listings
print("\nTEST 2: GET /seller")
print("-" * 70)
# We'd need a seller ID - let's try to get one from a search first
try:
    search_response = requests.get(f"{base_url}/search", headers=headers, 
                                   params={"query": "boots", "city": "los angeles", "limit": "1"}, 
                                   timeout=30)
    if search_response.status_code == 200:
        search_data = search_response.json()
        if isinstance(search_data, list) and len(search_data) > 0:
            seller_data = search_data[0].get("marketplace_listing_seller")
            if seller_data and isinstance(seller_data, dict):
                seller_id = seller_data.get("id")
                if seller_id:
                    print(f"Found seller ID: {seller_id}")
                    seller_params = {"sellerId": seller_id, "city": "los angeles"}
                    seller_response = requests.get(f"{base_url}/seller", headers=headers, params=seller_params, timeout=30)
                    print(f"Status: {seller_response.status_code}")
                    remaining = seller_response.headers.get('X-RateLimit-Requests-Remaining', 'N/A')
                    print(f"Remaining: {remaining}")
                    
                    if seller_response.status_code == 200:
                        seller_data = seller_response.json()
                        print(f"✅ /seller works! Returned {len(seller_data) if isinstance(seller_data, list) else 'data'}")
                    else:
                        print(f"Response: {seller_response.text[:200]}")
                else:
                    print("No seller ID found in item data")
            else:
                print("No seller data in response (seller field is null)")
        else:
            print("No items in search response")
    else:
        print(f"Search failed: {search_response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Search Seller By URL
print("\nTEST 3: GET /seller/url")
print("-" * 70)
# Would need a seller profile URL
seller_url = "https://www.facebook.com/marketplace/profile/123456789"  # Example
params = {"url": seller_url}

try:
    response = requests.get(f"{base_url}/seller/url", headers=headers, params=params, timeout=30)
    print(f"Status: {response.status_code}")
    remaining = response.headers.get('X-RateLimit-Requests-Remaining', 'N/A')
    print(f"Remaining: {remaining}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ /seller/url works! Returned {len(data) if isinstance(data, list) else 'data'}")
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
print("Test Complete!")
print("=" * 70)

