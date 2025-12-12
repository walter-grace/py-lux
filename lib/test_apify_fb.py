#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to explore Apify Facebook Marketplace scraper API
Tests various queries and documents response structure
"""

import os
import sys
import json
import time
from dotenv import load_dotenv
import requests

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.config import load_env


def test_apify_sync_search(query: str, location: str = "Los Angeles, CA", max_items: int = 10):
    """
    Test Apify's synchronous Facebook Marketplace search endpoint.
    
    Uses: POST /v2/acts/apify~facebook-marketplace-scraper/run-sync-get-dataset-items
    """
    env = load_env()
    api_token = env.get("APIFY_API_TOKEN")
    
    if not api_token:
        print("Error: APIFY_API_TOKEN not found in environment")
        print("Please add it to .env.local")
        return None
    
    url = f"https://api.apify.com/v2/acts/apify~facebook-marketplace-scraper/run-sync-get-dataset-items"
    params = {"token": api_token}
    
    # Facebook Marketplace search URL format
    # Format: https://www.facebook.com/marketplace/search/?query=QUERY&latitude=LAT&longitude=LNG
    # For now, we'll use a simpler format with just query
    # Note: We may need to geocode the location first
    
    # Construct Facebook Marketplace search URL
    # Facebook Marketplace URLs typically look like:
    # https://www.facebook.com/marketplace/search/?query=QUERY
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    marketplace_url = f"https://www.facebook.com/marketplace/search/?query={encoded_query}"
    
    # Apify input payload - requires startUrls
    payload = {
        "startUrls": [
            {
                "url": marketplace_url
            }
        ],
        "maxItems": max_items,
    }
    
    print(f"\n{'='*70}")
    print(f"Testing Apify Facebook Marketplace API")
    print(f"{'='*70}")
    print(f"Query: {query}")
    print(f"Location: {location}")
    print(f"Max Items: {max_items}")
    print(f"\nSending request to Apify...")
    
    try:
        print(f"Request URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print(f"\nNote: Facebook Marketplace scraping can take 2-5 minutes...")
        response = requests.post(url, params=params, json=payload, timeout=300)  # 5 minute timeout
        
        # Print response details before raising
        if response.status_code != 200:
            print(f"\nError Response Status: {response.status_code}")
            print(f"Error Response Headers: {dict(response.headers)}")
            print(f"Error Response Body: {response.text}")
        
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Type: {type(data)}")
        
        if isinstance(data, list):
            print(f"Number of items returned: {len(data)}")
            
            if len(data) > 0:
                print(f"\n{'='*70}")
                print("Sample Item Structure:")
                print(f"{'='*70}")
                sample = data[0]
                print(json.dumps(sample, indent=2, ensure_ascii=False))
                
                print(f"\n{'='*70}")
                print("Available Fields in Response:")
                print(f"{'='*70}")
                for key in sample.keys():
                    value = sample[key]
                    value_type = type(value).__name__
                    if isinstance(value, str) and len(value) > 50:
                        value_preview = value[:50] + "..."
                    else:
                        value_preview = value
                    print(f"  {key}: {value_type} = {value_preview}")
                
                # Save full response to file for analysis
                output_file = f"data/apify_test_response_{int(time.time())}.json"
                os.makedirs("data", exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"\nFull response saved to: {output_file}")
            else:
                print("\nNo items returned in response")
        else:
            print(f"\nUnexpected response format:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        
        return data
        
    except requests.exceptions.HTTPError as e:
        print(f"\nHTTP Error: {e}")
        if e.response:
            print(f"Status Code: {e.response.status_code}")
            print(f"Response: {e.response.text}")
            try:
                error_json = e.response.json()
                print(f"Error Details: {json.dumps(error_json, indent=2)}")
            except:
                pass
        return None
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_async_search(query: str, location: str = "Los Angeles, CA", max_items: int = 10):
    """
    Test Apify's asynchronous Facebook Marketplace search endpoint.
    
    Uses: POST /v2/acts/apify~facebook-marketplace-scraper/runs
    """
    env = load_env()
    api_token = env.get("APIFY_API_TOKEN")
    
    if not api_token:
        print("Error: APIFY_API_TOKEN not found in environment")
        return None
    
    url = f"https://api.apify.com/v2/acts/apify~facebook-marketplace-scraper/runs"
    params = {"token": api_token}
    
    payload = {
        "query": query,
        "location": location,
        "maxItems": max_items,
    }
    
    print(f"\n{'='*70}")
    print(f"Testing Async Apify Facebook Marketplace API")
    print(f"{'='*70}")
    print(f"Query: {query}")
    print(f"Location: {location}")
    print(f"\nSending async request...")
    
    try:
        response = requests.post(url, params=params, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\nRun created successfully!")
        print(f"Run ID: {data.get('data', {}).get('id')}")
        print(f"Status: {data.get('data', {}).get('status')}")
        print(f"\nFull response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        return data
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run test queries"""
    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    
    # Test queries
    test_queries = [
        ("PSA 10 yugioh 1st edition", "Los Angeles, CA"),
        ("PSA 10 pokemon base set", "Los Angeles, CA"),
        ("Gucci western boot 7.5", "Los Angeles, CA"),
        ("YSL boots", "Los Angeles, CA"),
    ]
    
    print("Starting Apify Facebook Marketplace API Tests")
    print("=" * 70)
    
    for query, location in test_queries:
        print(f"\n\nTesting query: {query}")
        result = test_apify_sync_search(query, location, max_items=5)
        
        if result:
            print(f"\n[SUCCESS] Successfully retrieved {len(result) if isinstance(result, list) else 'data'} for: {query}")
        else:
            print(f"\n[FAILED] Failed to retrieve data for: {query}")
        
        # Wait between requests to avoid rate limiting
        time.sleep(2)
    
    print(f"\n\n{'='*70}")
    print("Test Complete!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

