#!/usr/bin/env python3
"""Debug eBay API response to see what data we're getting"""

from ygo_psa10_arbitrage import search_ebay, extract_cert, load_env
import json

env = load_env()
items = search_ebay(5, env)  # Get 5 items

print(f"Found {len(items)} items\n")
print("=" * 70)

for i, item in enumerate(items[:3], 1):  # Show first 3
    print(f"\nItem {i}:")
    print(f"  Title: {item['title']}")
    print(f"  Price: ${item['price']:.2f}")
    print(f"  URL: {item['url']}")
    print(f"  Aspects: {json.dumps(item['aspects'], indent=4)}")
    
    cert = extract_cert(item)
    print(f"  Extracted Cert: {cert if cert else 'NONE'}")
    print()

