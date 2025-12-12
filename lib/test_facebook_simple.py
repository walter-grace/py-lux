"""
Simple test to check Facebook Marketplace API
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from lib.config import load_env
from lib.facebook_marketplace_api import search_facebook_marketplace

env = load_env()

print("Testing Facebook Marketplace API...")
print("=" * 70)

try:
    results = search_facebook_marketplace(
        query="water bottle",
        max_items=5,
        env=env,
        location="Los Angeles, CA"
    )
    
    print(f"\n✅ SUCCESS! Found {len(results)} items\n")
    
    for i, item in enumerate(results[:3], 1):
        print(f"{i}. {item['title'][:60]}...")
        print(f"   Price: ${item['price']:.2f}")
        print(f"   URL: {item['url']}")
        print(f"   Image: {item.get('image_url', 'No image')[:60]}...")
        print()
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

