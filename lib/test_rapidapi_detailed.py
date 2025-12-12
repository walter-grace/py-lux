#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed test for RapidAPI Facebook Marketplace - test different queries to see response structure
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

# Test with a broader query that's more likely to have results
test_queries = [
    ("boots", "los angeles"),  # Very broad
    ("shoes", "los angeles"),   # Even broader
]

print("Testing RapidAPI Facebook Marketplace - Response Structure Analysis")
print("=" * 70)
print(f"⚠️  Using 2 requests (28 remaining this month)")
print("=" * 70)

for query, city in test_queries:
    params = {
        "query": query,
        "city": city,
        "sort": "newest",
        "limit": "3"  # Get a few items to see structure
    }
    
    print(f"\n{'='*70}")
    print(f"Query: '{query}' in {city}")
    print(f"{'='*70}")
    print(f"Params: {json.dumps(params, indent=2)}")
    print("\nSending request...")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        # Check rate limit headers
        remaining = response.headers.get('X-RateLimit-Requests-Remaining', 'N/A')
        print(f"Remaining requests this month: {remaining}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n[SUCCESS] Response received!")
            print(f"Response Type: {type(data)}")
            
            if isinstance(data, list):
                print(f"Number of items: {len(data)}")
                if len(data) > 0:
                    print(f"\n{'='*70}")
                    print("FIRST ITEM STRUCTURE (Full):")
                    print(f"{'='*70}")
                    print(json.dumps(data[0], indent=2, ensure_ascii=False))
                    
                    print(f"\n{'='*70}")
                    print("FIELD ANALYSIS:")
                    print(f"{'='*70}")
                    for key, value in data[0].items():
                        value_type = type(value).__name__
                        if isinstance(value, str):
                            preview = value[:80] + "..." if len(value) > 80 else value
                        elif isinstance(value, (list, dict)):
                            preview = f"{value_type} with {len(value)} items" if hasattr(value, '__len__') else value_type
                        else:
                            preview = str(value)
                        print(f"  {key:20s} : {value_type:10s} = {preview}")
                    
                    # Save to file
                    output_file = f"data/rapidapi_response_{query.replace(' ', '_')}.json"
                    os.makedirs("data", exist_ok=True)
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"\n✅ Full response saved to: {output_file}")
                else:
                    print("\n⚠️  No items returned for this query")
            elif isinstance(data, dict):
                print(f"\nResponse is a dictionary:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
            else:
                print(f"\nUnexpected response type: {data}")
        else:
            print(f"\n[ERROR] Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    # Only test first query that returns results
    if response.status_code == 200 and isinstance(response.json(), list) and len(response.json()) > 0:
        print(f"\n✅ Found results! Stopping tests to conserve API calls.")
        break
    
    print("\n" + "-" * 70)

print(f"\n{'='*70}")
print("Test Complete!")
print(f"{'='*70}")

