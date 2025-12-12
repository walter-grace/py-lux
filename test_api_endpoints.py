#!/usr/bin/env python3
"""Test script to find correct Watch Database API endpoint paths"""
import os
import sys
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lib.config import load_env

load_dotenv(".env")
load_dotenv(".env.local", override=True)

env = load_env()
api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY")

if not api_key:
    print("❌ No API key found!")
    sys.exit(1)

BASE_URL = "https://watch-database1.p.rapidapi.com"
headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": "watch-database1.p.rapidapi.com",
    "Content-Type": "application/json"
}

# Test different endpoint path variations
test_endpoints = [
    "/makes",
    "/v2/makes",
    "/api/makes",
    "/api/v2/makes",
    "/watch/makes",
    "/watches/makes",
]

print("Testing endpoint paths...\n")

for endpoint in test_endpoints:
    url = f"{BASE_URL}{endpoint}"
    print(f"Testing: {endpoint}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✅ SUCCESS! Endpoint works: {endpoint}")
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"  Sample data: {data[0]}")
            elif isinstance(data, dict):
                print(f"  Response keys: {list(data.keys())[:5]}")
            break
        elif response.status_code == 404:
            print(f"  ❌ Not found")
        else:
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
    print()

# Test POST endpoints
print("\nTesting POST endpoints...\n")
post_endpoints = [
    "/search",
    "/v2/search",
    "/api/search",
    "/api/v2/search",
    "/watches/search",
]

for endpoint in post_endpoints:
    url = f"{BASE_URL}{endpoint}"
    print(f"Testing POST: {endpoint}")
    try:
        response = requests.post(
            url,
            headers=headers,
            json={"name": "Rolex"},
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✅ SUCCESS! Endpoint works: {endpoint}")
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"  Sample data: {data[0]}")
            elif isinstance(data, dict):
                print(f"  Response keys: {list(data.keys())[:5]}")
            break
        elif response.status_code == 404:
            print(f"  ❌ Not found")
        else:
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
    print()
