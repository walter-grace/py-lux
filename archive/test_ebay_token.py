#!/usr/bin/env python3
"""Test eBay token validity"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local", override=True)

token = os.getenv("EBAY_OAUTH")
if not token:
    print("Error: EBAY_OAUTH not found")
    exit(1)

print(f"Token length: {len(token)}")
print(f"Token preview: {token[:50]}...")
print()

# Test with a simple API call
url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
headers = {"Authorization": f"Bearer {token}"}
params = {
    "q": "test",
    "limit": "1"
}

print("Testing eBay API with your token...")
try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("[SUCCESS] Token is VALID!")
        data = response.json()
        print(f"Found {len(data.get('itemSummaries', []))} items")
    elif response.status_code == 401:
        print("[ERROR] Token is INVALID or EXPIRED")
        print("\nError details:")
        try:
            error_data = response.json()
            print(f"  {error_data}")
        except:
            print(f"  {response.text[:500]}")
        print("\nPlease regenerate your token at:")
        print("https://developer.ebay.com/my/keys")
    else:
        print(f"Unexpected status: {response.status_code}")
        print(response.text[:500])
        
except Exception as e:
    print(f"Error: {e}")

