#!/usr/bin/env python3
"""Test script to find PSA estimated value in eBay listings"""

import requests
import cloudscraper
import re
import json
from bs4 import BeautifulSoup

def test_ebay_psa_extraction(ebay_url: str):
    """Test different methods to extract PSA data from eBay"""
    
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    
    print(f"Testing URL: {ebay_url}\n")
    
    try:
        response = scraper.get(ebay_url, timeout=30)
        print(f"Status Code: {response.status_code}\n")
        
        html = response.text
        
        # Method 1: Look for window.__INITIAL_STATE__ or similar
        print("=" * 70)
        print("Method 1: Looking for window.__INITIAL_STATE__")
        print("=" * 70)
        initial_state_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
            r'var\s+__INITIAL_STATE__\s*=\s*({.+?});',
        ]
        
        for pattern in initial_state_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            if matches:
                print(f"Found {len(matches)} matches")
                try:
                    data = json.loads(matches[0][:5000])  # First 5000 chars
                    print(f"Sample keys: {list(data.keys())[:10]}")
                    # Search for PSA-related keys
                    psa_keys = [k for k in str(data).lower() if 'psa' in k.lower() or 'estimate' in k.lower()]
                    if psa_keys:
                        print(f"Found PSA-related keys: {psa_keys[:5]}")
                except:
                    print("Could not parse as JSON")
        
        # Method 2: Look for API endpoints in script tags
        print("\n" + "=" * 70)
        print("Method 2: Looking for API endpoints")
        print("=" * 70)
        api_patterns = [
            r'["\']([^"\']*psa[^"\']*api[^"\']*)["\']',
            r'["\']([^"\']*api[^"\']*psa[^"\']*)["\']',
            r'https?://[^"\']*psa[^"\']*',
            r'https?://[^"\']*ebay[^"\']*psa[^"\']*',
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                print(f"Found potential API endpoints:")
                for match in matches[:5]:
                    print(f"  {match}")
        
        # Method 3: Look for PSA data in script tags
        print("\n" + "=" * 70)
        print("Method 3: Looking for PSA data in script tags")
        print("=" * 70)
        soup = BeautifulSoup(html, 'html.parser')
        psa_scripts = []
        for script in soup.find_all('script'):
            if script.string and ('psa' in script.string.lower() or 'estimate' in script.string.lower()):
                psa_scripts.append(script.string[:500])  # First 500 chars
        
        if psa_scripts:
            print(f"Found {len(psa_scripts)} script tags with PSA/estimate content")
            for i, script in enumerate(psa_scripts[:3]):
                print(f"\nScript {i+1} (first 500 chars):")
                print(script)
        
        # Method 4: Look for data attributes
        print("\n" + "=" * 70)
        print("Method 4: Looking for data attributes")
        print("=" * 70)
        for elem in soup.find_all(attrs={'data-psa': True}):
            print(f"Found element with data-psa: {elem.get('data-psa')}")
        for elem in soup.find_all(attrs={'data-estimate': True}):
            print(f"Found element with data-estimate: {elem.get('data-estimate')}")
        
        # Method 5: Look for "See all" button and its data attributes
        print("\n" + "=" * 70)
        print("Method 5: Looking for 'See all' button")
        print("=" * 70)
        see_all_buttons = soup.find_all(string=re.compile('See all', re.I))
        for button in see_all_buttons:
            parent = button.parent
            if parent:
                print(f"Found 'See all' button")
                print(f"  Parent tag: {parent.name}")
                print(f"  Attributes: {parent.attrs}")
                # Look for onclick or data attributes
                if 'onclick' in parent.attrs:
                    print(f"  onclick: {parent.attrs['onclick'][:200]}")
                if 'data-click' in parent.attrs:
                    print(f"  data-click: {parent.attrs['data-click'][:200]}")
        
        # Method 6: Search for estimated value patterns in text
        print("\n" + "=" * 70)
        print("Method 6: Searching for estimated value patterns")
        print("=" * 70)
        text = soup.get_text()
        patterns = [
            r'PSA\s+Estimate[:\s]*\$?([\d,]+\.?\d*)',
            r'Estimated\s+Value[:\s]*\$?([\d,]+\.?\d*)',
            r'Est\.\s+Value[:\s]*\$?([\d,]+\.?\d*)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                print(f"Pattern '{pattern}' found: {matches[:5]}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Test with the GRAVEROBBER listing
    test_ebay_psa_extraction('https://www.ebay.com/itm/306050014852')

