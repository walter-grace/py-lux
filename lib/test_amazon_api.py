"""
Test script to explore RapidAPI Amazon Data API endpoints and response structure
"""
import http.client
import json
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

def test_amazon_product_search(query: str = "Gucci boot"):
    """Test the Product Search endpoint"""
    print(f"\n{'='*70}")
    print(f"Testing Amazon Product Search: '{query}'")
    print(f"{'='*70}")
    
    conn = http.client.HTTPSConnection("realtime-amazon-data.p.rapidapi.com")
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': "realtime-amazon-data.p.rapidapi.com"
    }
    
    # Try different endpoint variations based on RapidAPI documentation
    # The /product-search endpoint exists but uses "keyword" instead of "query"
    query_encoded = query.replace(' ', '%20')
    endpoints_to_try = [
        f"/product-search?keyword={query_encoded}&country=us&page=1",
        f"/product-search?query={query_encoded}&country=us&page=1",
        f"/search?query={query_encoded}&country=us&page=1",
        f"/product/search?query={query_encoded}&country=us&page=1",
        f"/products/search?query={query_encoded}&country=us&page=1",
    ]
    
    for endpoint in endpoints_to_try:
        print(f"\nTrying endpoint: {endpoint}")
        try:
            conn.request("GET", endpoint, headers=headers)
            res = conn.getresponse()
            data = res.read()
            
            print(f"Status Code: {res.status}")
            
            if res.status == 200:
                response_data = json.loads(data.decode("utf-8"))
                print(f"✅ SUCCESS! Response structure:")
                print(json.dumps(response_data, indent=2)[:2000])
                
                # Analyze structure
                if isinstance(response_data, dict):
                    print(f"\nTop-level keys: {list(response_data.keys())}")
                    if "data" in response_data:
                        print(f"Data type: {type(response_data['data'])}")
                        if isinstance(response_data["data"], list) and len(response_data["data"]) > 0:
                            print(f"\nFirst item keys: {list(response_data['data'][0].keys())}")
                            print(f"\nFirst item sample:")
                            print(json.dumps(response_data["data"][0], indent=2)[:1000])
                break
            elif res.status == 404:
                print(f"❌ Not found, trying next endpoint...")
                continue
            else:
                print(f"Error Response: {data.decode('utf-8')[:500]}")
                break
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    # If all failed, try the best-sellers endpoint to see the API structure
    print(f"\n{'='*70}")
    print("Testing Best Sellers endpoint to understand API structure:")
    print(f"{'='*70}")
    try:
        endpoint = "/best-sellers?category=shoes&country=us&page=1"
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            response_data = json.loads(data.decode("utf-8"))
            print(f"\nBest Sellers Response Structure:")
            print(json.dumps(response_data, indent=2)[:2000])
            
            # Check if products array has items
            if "products" in response_data and isinstance(response_data["products"], list) and len(response_data["products"]) > 0:
                print(f"\n✅ Found products! First product structure:")
                print(json.dumps(response_data["products"][0], indent=2)[:1500])
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()


def test_amazon_product_details(asin: str = "B08XYZ123"):
    """Test the Product Details endpoint (if we have an ASIN)"""
    print(f"\n{'='*70}")
    print(f"Testing Amazon Product Details: ASIN '{asin}'")
    print(f"{'='*70}")
    
    conn = http.client.HTTPSConnection("realtime-amazon-data.p.rapidapi.com")
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': "realtime-amazon-data.p.rapidapi.com"
    }
    
    # Try different endpoint variations for product details
    endpoints_to_try = [
        f"/product?asin={asin}&country=us",
        f"/product/details?asin={asin}&country=us",
        f"/products/{asin}?country=us",
    ]
    
    try:
        for endpoint in endpoints_to_try:
            print(f"\nTrying endpoint: {endpoint}")
            try:
                conn.request("GET", endpoint, headers=headers)
                res = conn.getresponse()
                data = res.read()
                
                print(f"Status Code: {res.status}")
                
                if res.status == 200:
                    response_data = json.loads(data.decode("utf-8"))
                    print(f"✅ SUCCESS! Response structure:")
                    print(json.dumps(response_data, indent=2)[:2000])
                    break
                elif res.status == 404:
                    print(f"❌ Not found")
                    continue
                else:
                    print(f"Error Response: {data.decode('utf-8')[:500]}")
                    break
            except Exception as e:
                print(f"Error: {e}")
                continue
    finally:
        conn.close()


if __name__ == "__main__":
    if not RAPIDAPI_KEY:
        print("ERROR: RAPIDAPI_KEY not found in environment")
        exit(1)
    
    # Test product search (most relevant for our use case)
    test_amazon_product_search("Gucci western boot 7.5")
    
    # Test with trading card query
    # test_amazon_product_search("PSA 10 yugioh")  # Skip to save API calls
    
    # Test product details with a real ASIN (if we can find one)
    # test_amazon_product_details("B08XYZ123")  # Skip for now

