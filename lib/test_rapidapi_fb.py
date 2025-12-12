#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to explore RapidAPI Facebook Marketplace API
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


def extract_city_from_location(location: str) -> str:
    """Extract city name from location string (e.g., 'Los Angeles, CA' -> 'los angeles')"""
    if not location:
        return "los angeles"  # Default
    
    # Split by comma and take first part
    city = location.split(',')[0].strip().lower()
    return city


def test_rapidapi_search(query: str, location: str = "Los Angeles, CA", max_items: int = 1):
    """
    Test RapidAPI's Facebook Marketplace search endpoint.
    
    Uses: GET https://facebook-marketplace1.p.rapidapi.com/search
    """
    env = load_env()
    api_key = env.get("RAPIDAPI_KEY")
    
    if not api_key:
        print("Error: RAPIDAPI_KEY not found in environment")
        print("Please add it to .env.local")
        return None
    
    url = "https://facebook-marketplace1.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-host": "facebook-marketplace1.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    
    # Extract city from location
    city = extract_city_from_location(location)
    
    # RapidAPI parameters
    params = {
        "query": query,
        "city": city,
        "sort": "newest",  # Options: newest, price_asc, price_desc, distance
        "limit": str(max_items),
    }
    
    print(f"\n{'='*70}")
    print(f"Testing RapidAPI Facebook Marketplace API")
    print(f"{'='*70}")
    print(f"Query: {query}")
    print(f"Location: {location} (city: {city})")
    print(f"Max Items: {max_items}")
    print(f"\nSending request to RapidAPI...")
    print(f"URL: {url}")
    print(f"Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
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
                output_file = f"data/rapidapi_test_response_{int(time.time())}.json"
                os.makedirs("data", exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"\nFull response saved to: {output_file}")
            else:
                print("\nNo items returned in response")
        elif isinstance(data, dict):
            # Check if response has a data/results field
            if "data" in data:
                items = data["data"]
                print(f"Response has 'data' field with {len(items) if isinstance(items, list) else 'non-list'} items")
                print(f"\nFull response structure:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
            elif "results" in data:
                items = data["results"]
                print(f"Response has 'results' field with {len(items) if isinstance(items, list) else 'non-list'} items")
                print(f"\nFull response structure:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
            else:
                print(f"\nResponse structure:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"\nUnexpected response format:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
        
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


def main():
    """Run test queries"""
    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    
    # IMPORTANT: Free tier has only 30 requests/month - use sparingly!
    # Only test ONE query to conserve API calls
    test_queries = [
        ("YSL boots", "Los Angeles, CA"),  # Single test query
    ]
    
    print("Starting RapidAPI Facebook Marketplace API Tests")
    print("=" * 70)
    print("⚠️  WARNING: Free tier has only 30 requests/month - testing with minimal queries")
    print("=" * 70)
    
    for query, location in test_queries:
        print(f"\n\nTesting query: {query}")
        result = test_rapidapi_search(query, location, max_items=5)
        
        if result:
            if isinstance(result, list):
                print(f"\n[SUCCESS] Successfully retrieved {len(result)} items for: {query}")
            else:
                print(f"\n[SUCCESS] Successfully retrieved data for: {query}")
        else:
            print(f"\n[FAILED] Failed to retrieve data for: {query}")
        
        # Wait between requests to avoid rate limiting
        time.sleep(2)
    
    print(f"\n\n{'='*70}")
    print("Test Complete!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

