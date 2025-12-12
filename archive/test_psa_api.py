#!/usr/bin/env python3
"""
Simple test script for PSA API
Tests the /cert/GetByCertNumber endpoint

Usage:
    python test_psa_api.py [cert_number]
    
Example:
    python test_psa_api.py 12345678
"""

import os
import sys
import json
from dotenv import load_dotenv
import cloudscraper

# Load environment variables
load_dotenv(".env")
load_dotenv(".env.local", override=True)

psa_token = os.getenv("PSA_TOKEN")

if not psa_token:
    print("Error: PSA_TOKEN not found in .env.local")
    print("Please add your PSA token to .env.local:")
    print("PSA_TOKEN=your_token_here")
    sys.exit(1)

# Get cert number from command line or use default
if len(sys.argv) > 1:
    test_cert = sys.argv[1]
else:
    test_cert = "12345678"  # Default test cert

url = f"https://api.psacard.com/publicapi/cert/GetByCertNumber/{test_cert}"
headers = {
    "Authorization": f"Bearer {psa_token}",  # Note: Capital "Bearer" as per Swagger docs
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

print(f"\nTesting PSA API...")
print(f"URL: {url}")
print(f"Cert Number: {test_cert}")
print(f"Token (first 20 chars): {psa_token[:20]}...")
print("\n" + "="*60)

try:
    # Use cloudscraper to bypass Cloudflare protection
    scraper = cloudscraper.create_scraper()
    scraper.headers.update(headers)
    
    # cloudscraper handles SSL and Cloudflare challenges automatically
    response = scraper.get(url, timeout=30)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print("\n" + "="*60)
    
    if response.status_code == 204:
        print("Response: 204 No Content (empty request data)")
    elif response.status_code == 200:
        try:
            data = response.json()
            print("Response JSON:")
            print("-" * 60)
            
            # Pretty print the response
            import json
            print(json.dumps(data, indent=2))
            
            print("\n" + "="*60)
            print("Key Fields:")
            # Check if response has IsValidRequest (old format) or PSACert (new format)
            if "IsValidRequest" in data:
                print(f"  IsValidRequest: {data.get('IsValidRequest', 'N/A')}")
                print(f"  ServerMessage: {data.get('ServerMessage', 'N/A')}")
            
            # PSA API returns { "PSACert": {...}, "DNACert": {...} }
            if "PSACert" in data:
                psa_cert = data["PSACert"]
                print("\nPSACert Data:")
                print(f"  CertNumber: {psa_cert.get('CertNumber', 'N/A')}")
                print(f"  Year: {psa_cert.get('Year', 'N/A')}")
                print(f"  Brand: {psa_cert.get('Brand', 'N/A')}")
                print(f"  Category: {psa_cert.get('Category', 'N/A')}")
                print(f"  Subject: {psa_cert.get('Subject', 'N/A')}")
                print(f"  CardNumber: {psa_cert.get('CardNumber', 'N/A')}")
                print(f"  CardGrade: {psa_cert.get('CardGrade', 'N/A')}")
                print(f"  GradeDescription: {psa_cert.get('GradeDescription', 'N/A')}")
                print(f"  TotalPopulation: {psa_cert.get('TotalPopulation', 'N/A')}")
                print(f"  PopulationHigher: {psa_cert.get('PopulationHigher', 'N/A')}")
            
            if "DNACert" in data:
                print("\nDNACert Data:")
                dna_cert = data["DNACert"]
                print(f"  CertNumber: {dna_cert.get('CertNumber', 'N/A')}")
                print(f"  ItemDescription: {dna_cert.get('ItemDescription', 'N/A')}")
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            print(f"Raw response: {response.text[:500]}")
    elif 400 <= response.status_code < 500:
        print(f"Client Error ({response.status_code})")
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
        except:
            print(f"Response: {response.text[:500]}")
    elif response.status_code == 500:
        print("Server Error (500)")
        print("This might indicate invalid credentials or server error")
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
        except:
            print(f"Response: {response.text[:500]}")
    else:
        print(f"Unexpected status code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("Test complete!")

