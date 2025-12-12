#!/usr/bin/env python3
"""Simple test to see what URL we get"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from lib.watch_api import get_watchcharts_url

# Test the problematic watch
watch_info = {
    "brand": "Rolex",
    "model": "GMT-Master II",
    "model_number": "126710BLNR"
}

print("Testing: Rolex GMT-Master II 126710BLNR")
url = get_watchcharts_url(watch_info)
print(f"Result URL: {url}")

# Check if it contains the right model
if url and '126710blnr' in url.lower():
    print("✅ URL contains correct model number!")
elif url and '126710' in url.lower():
    print("⚠️  URL contains partial model number (126710)")
    print("   This might be a different variant (BLNR vs GRNR vs other)")
else:
    print("❌ URL does not contain model number")

