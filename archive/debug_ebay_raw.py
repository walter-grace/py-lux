#!/usr/bin/env python3
"""Check raw eBay API response"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local", override=True)

token = os.getenv("EBAY_OAUTH")
url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
headers = {"Authorization": f"Bearer {token}"}

params = {
    "q": "yugioh PSA 10 1st edition",
    "category_ids": "183454",
    "limit": "3",
    "filter": "sellers:{psa},buyingOptions:{FIXED_PRICE}",
    "aspect_filter": (
        "categoryId:183454,"
        "Game:Yu-Gi-Oh! TCG;"
        "Professional Grader:Professional Sports Authenticator (PSA);"
        "Grade:10;"
        "Edition:1st Edition"
    ),
}

response = requests.get(url, headers=headers, params=params, timeout=30)
if response.status_code == 200:
    data = response.json()
    print("First item full structure:")
    if data.get("itemSummaries"):
        first_item = data["itemSummaries"][0]
        print(json.dumps(first_item, indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)

