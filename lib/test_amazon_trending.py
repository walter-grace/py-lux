"""
Test script to check if Amazon has a trending items endpoint via RapidAPI
"""
import http.client
import json
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

def test_amazon_endpoints():
    """Test various Amazon endpoints to find trending items"""
    conn = http.client.HTTPSConnection("realtime-amazon-data.p.rapidapi.com")
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': "realtime-amazon-data.p.rapidapi.com"
    }
    
    # Test different endpoint variations for trending items
    endpoints_to_try = [
        "/trending?country=us",
        "/trending-items?country=us",
        "/trending-products?country=us",
        "/popular?country=us",
        "/popular-items?country=us",
        "/hot-items?country=us",
        "/hot-products?country=us",
        "/best-sellers?category=all&country=us&page=1",  # We know this works
    ]
    
    print("=" * 70)
    print("Testing Amazon Trending/Popular Items Endpoints")
    print("=" * 70)
    
    for endpoint in endpoints_to_try:
        print(f"\nTesting: {endpoint}")
        try:
            conn.request("GET", endpoint, headers=headers)
            res = conn.getresponse()
            data = res.read()
            
            print(f"Status Code: {res.status}")
            
            if res.status == 200:
                response_data = json.loads(data.decode("utf-8"))
                print(f"✅ SUCCESS!")
                print(f"Response keys: {list(response_data.keys())}")
                
                # Check for products/items/data
                if "products" in response_data:
                    print(f"Found 'products' array with {len(response_data['products'])} items")
                    if len(response_data['products']) > 0:
                        print(f"First item: {json.dumps(response_data['products'][0], indent=2)[:500]}")
                elif "items" in response_data:
                    print(f"Found 'items' array with {len(response_data['items'])} items")
                elif "data" in response_data:
                    print(f"Found 'data' array with {len(response_data['data'])} items")
                elif "trending" in response_data:
                    print(f"Found 'trending' data: {json.dumps(response_data['trending'], indent=2)[:500]}")
                
                break  # Found working endpoint
            elif res.status == 404:
                print(f"❌ Not found")
            else:
                print(f"Response: {data.decode('utf-8')[:200]}")
        except Exception as e:
            print(f"Error: {e}")
    
    conn.close()

if __name__ == "__main__":
    if not RAPIDAPI_KEY:
        print("ERROR: RAPIDAPI_KEY not found in environment")
        exit(1)
    
    test_amazon_endpoints()

