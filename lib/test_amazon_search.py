"""
Quick test of Amazon product search endpoint
"""
import http.client
import json
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

conn = http.client.HTTPSConnection("realtime-amazon-data.p.rapidapi.com")

headers = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': "realtime-amazon-data.p.rapidapi.com"
}

# Test product search
print("Testing /product-search endpoint...")
conn.request("GET", "/product-search?keyword=coffee%20machine&country=us&page=1&sort=Featured", headers=headers)

res = conn.getresponse()
data = res.read()

print(f"\nStatus Code: {res.status}")
if res.status == 200:
    response_data = json.loads(data.decode("utf-8"))
    print(f"\n✅ SUCCESS!")
    print(f"Response keys: {list(response_data.keys())}")
    
    if "details" in response_data:
        print(f"\nFound {len(response_data['details'])} products in 'details' array")
        if len(response_data['details']) > 0:
            print(f"\nFirst product structure:")
            print(json.dumps(response_data['details'][0], indent=2))
    elif "products" in response_data:
        print(f"\nFound {len(response_data['products'])} products in 'products' array")
        if len(response_data['products']) > 0:
            print(f"\nFirst product structure:")
            print(json.dumps(response_data['products'][0], indent=2))
else:
    print(f"\n❌ Error: {data.decode('utf-8')[:500]}")

conn.close()

