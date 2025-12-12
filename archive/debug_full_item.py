#!/usr/bin/env python3
"""Check full item details for cert number"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local", override=True)

token = os.getenv("EBAY_OAUTH")
headers = {"Authorization": f"Bearer {token}"}

# Get one item ID from search
search_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
params = {
    "q": "yugioh PSA 10 1st edition",
    "category_ids": "183454",
    "limit": "1",
    "filter": "sellers:{psa},buyingOptions:{FIXED_PRICE}",
}

response = requests.get(search_url, headers=headers, params=params, timeout=30)
if response.status_code == 200:
    data = response.json()
    if data.get("itemSummaries"):
        item = data["itemSummaries"][0]
        item_href = item.get("itemHref", "")
        print(f"Fetching full item: {item_href}")
        
        # Get full item details
        item_response = requests.get(item_href, headers=headers, timeout=30)
        if item_response.status_code == 200:
            full_item = item_response.json()
            print("\nFull item structure (all fields):")
            print(json.dumps(full_item, indent=2))
        else:
            print(f"Error fetching item: {item_response.status_code}")
            print(item_response.text)

