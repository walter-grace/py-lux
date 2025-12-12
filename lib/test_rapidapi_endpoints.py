#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test all available RapidAPI Facebook Marketplace endpoints to see what we can use
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

base_url = "https://facebook-marketplace1.p.rapidapi.com"
headers = {
    "x-rapidapi-host": "facebook-marketplace1.p.rapidapi.com",
    "x-rapidapi-key": api_key
}

print("Testing RapidAPI Facebook Marketplace Endpoints")
print("=" * 70)
print("⚠️  This will use multiple API calls - testing strategically")
print("=" * 70)

# Test 1: Search with additional filters
print("\n" + "=" * 70)
print("TEST 1: Search Results with Filters (minPrice, maxPrice, daysSinceListed)")
print("=" * 70)

params = {
    "query": "boots",
    "city": "los angeles",
    "sort": "newest",
    "limit": "2",
    "minPrice": "50",  # Test price filter
    "maxPrice": "500",  # Test price filter
    "daysSinceListed": "7"  # Test date filter
}

print(f"Testing with filters: {json.dumps(params, indent=2)}")

try:
    response = requests.get(f"{base_url}/search", headers=headers, params=params, timeout=30)
    print(f"Status: {response.status_code}")
    remaining = response.headers.get('X-RateLimit-Requests-Remaining', 'N/A')
    print(f"Remaining requests: {remaining}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Filters work! Returned {len(data) if isinstance(data, list) else 'data'} items")
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Get Product By ID (if we have an ID from previous search)
print("\n" + "=" * 70)
print("TEST 2: Get Product Information By ID")
print("=" * 70)

# First get an item ID from a search
test_params = {
    "query": "boots",
    "city": "los angeles",
    "limit": "1"
}

try:
    search_response = requests.get(f"{base_url}/search", headers=headers, params=test_params, timeout=30)
    if search_response.status_code == 200:
        search_data = search_response.json()
        if isinstance(search_data, list) and len(search_data) > 0:
            item_id = search_data[0].get("id")
            print(f"Found item ID: {item_id}")
            
            # Now try to get detailed info
            detail_params = {"id": item_id}
            detail_response = requests.get(f"{base_url}/product", headers=headers, params=detail_params, timeout=30)
            print(f"Get Product By ID Status: {detail_response.status_code}")
            remaining = detail_response.headers.get('X-RateLimit-Requests-Remaining', 'N/A')
            print(f"Remaining requests: {remaining}")
            
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                print(f"✅ Get Product By ID works!")
                print(f"Response type: {type(detail_data)}")
                if isinstance(detail_data, dict):
                    print(f"Keys in response: {list(detail_data.keys())[:10]}")
            else:
                print(f"Response: {detail_response.text[:200]}")
        else:
            print("No items found to test Get Product By ID")
    else:
        print(f"Search failed: {search_response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Get Product By URL
print("\n" + "=" * 70)
print("TEST 3: Get Product By URL")
print("=" * 70)

# Use a known Facebook Marketplace URL format
test_url = "https://www.facebook.com/marketplace/item/1480717813586756"  # From our previous test
url_params = {"url": test_url}

try:
    url_response = requests.get(f"{base_url}/product/url", headers=headers, params=url_params, timeout=30)
    print(f"Get Product By URL Status: {url_response.status_code}")
    remaining = url_response.headers.get('X-RateLimit-Requests-Remaining', 'N/A')
    print(f"Remaining requests: {remaining}")
    
    if url_response.status_code == 200:
        url_data = url_response.json()
        print(f"✅ Get Product By URL works!")
        print(f"Response type: {type(url_data)}")
    else:
        print(f"Response: {url_response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: Check what other endpoints exist
print("\n" + "=" * 70)
print("TEST 4: Available Endpoints Summary")
print("=" * 70)
print("""
Based on RapidAPI documentation, available endpoints:
1. GET /search - Search Results (✅ We're using this)
2. GET /search/url - Search Results By URL (❓ Not tested)
3. GET /seller - Search Seller Listings (❓ Not tested)
4. GET /seller/url - Search Seller By URL (❓ Not tested)
5. GET /product - Get Product Information By ID (✅ Tested above)
6. GET /product/url - Get Product By URL (✅ Tested above)

Additional filters available:
- minPrice, maxPrice (✅ Tested)
- daysSinceListed (✅ Tested)
- category (❓ Not tested)
- condition (❓ Not tested)
""")

print("\n" + "=" * 70)
print("Test Complete!")
print("=" * 70)

