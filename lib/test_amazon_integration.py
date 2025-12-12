"""
Test the full Amazon API integration
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.amazon_api import search_amazon_products, normalize_amazon_item
from lib.config import load_env

env = load_env()

print("Testing Amazon product search...")
print("=" * 70)

# Test search
results = search_amazon_products("Gucci boot", max_items=3, env=env, country="us")

print(f"\n✅ Found {len(results)} items\n")

for i, item in enumerate(results, 1):
    print(f"{i}. {item['title'][:60]}...")
    print(f"   Price: ${item['price']:.2f}")
    print(f"   ASIN: {item['asin']}")
    print(f"   URL: {item['url']}")
    print(f"   Prime: {item.get('prime_eligible', False)}")
    print(f"   Rating: {item.get('rating', 'N/A')}")
    print()

