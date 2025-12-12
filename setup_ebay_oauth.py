#!/usr/bin/env python3
"""
Setup script to add eBay OAuth credentials and generate token automatically
"""
import os
from lib.ebay_oauth import get_oauth_token
from dotenv import load_dotenv

load_dotenv(".env.local")

print("=" * 70)
print("eBay OAuth Token Setup")
print("=" * 70)
print()

# Get credentials
client_id = os.getenv("EBAY_CLIENT_ID", "")
client_secret = os.getenv("EBAY_CLIENT_SECRET", "")

if not client_id:
    print("❌ EBAY_CLIENT_ID not found in .env.local")
    print()
    print("Please add your eBay Client ID to .env.local:")
    print("EBAY_CLIENT_ID=NicoZahn-YugiohPr-PRD-23cd82f4c-632193b1")
    print()
    print("You also need your Client Secret (Cert ID) from:")
    print("https://developer.ebay.com/my/keys")
    print()
    exit(1)

if not client_secret:
    print("❌ EBAY_CLIENT_SECRET not found in .env.local")
    print()
    print("Please add your eBay Client Secret (Cert ID) to .env.local:")
    print("EBAY_CLIENT_SECRET=your_cert_id_here")
    print()
    print("Get it from: https://developer.ebay.com/my/keys")
    print("Look for 'Cert ID (Client Secret)' next to your App ID")
    print()
    exit(1)

print(f"✅ Client ID found: {client_id[:20]}...")
print(f"✅ Client Secret found: {client_secret[:10]}...")
print()
print("Requesting OAuth token from eBay...")
print()

# Get token
token = get_oauth_token(client_id=client_id, client_secret=client_secret, environment="production")

if token:
    print()
    print("=" * 70)
    print("✅ SUCCESS! Token Generated")
    print("=" * 70)
    print()
    print("Your eBay OAuth Token:")
    print("-" * 70)
    print(token)
    print("-" * 70)
    print()
    print("Add this to your .env.local file:")
    print()
    print(f"EBAY_OAUTH={token}")
    print()
    print("Or use the web app's 'Get eBay OAuth Token' button to generate it automatically!")
    print("=" * 70)
else:
    print()
    print("=" * 70)
    print("❌ FAILED to generate token")
    print("=" * 70)
    print()
    print("Please check:")
    print("1. Your Client ID and Client Secret are correct")
    print("2. Your app has the correct OAuth scopes")
    print("3. Your app is approved for Production use (if using production)")
    print()

