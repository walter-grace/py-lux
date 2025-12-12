#!/usr/bin/env python3
"""Test if eBay image URLs are accessible"""
import requests
import json

# Sample image URLs from the JSON you showed
test_urls = [
    "https://i.ebayimg.com/images/g/6BQAAeSwqF1ownP/s-l1600.jpg",
    "https://i.ebayimg.com/images/g/bu0AAeSw7SponjLt/s-l1600.jpg",
    "https://i.ebayimg.com/images/g/FKsAAOSw7hxnu20D/s-l1600.jpg",
]

print("Testing eBay image URLs...\n")

for url in test_urls:
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        print(f"✅ {url}")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        print(f"   Size: {len(response.content)} bytes\n")
    except Exception as e:
        print(f"❌ {url}")
        print(f"   Error: {str(e)}\n")

