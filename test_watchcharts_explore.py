#!/usr/bin/env python3
"""
Explore WatchCharts website structure to find correct URL patterns
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import cloudscraper
from bs4 import BeautifulSoup
import re

def explore_watchcharts(brand, model):
    """Explore WatchCharts to find correct URL structure"""
    print(f"\n{'='*70}")
    print(f"Exploring WatchCharts for: {brand} {model}")
    print(f"{'='*70}\n")
    
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    
    # Try the main watches page
    print("1. Exploring main watches page...")
    try:
        response = scraper.get("https://watchcharts.com/watches", timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for links that might lead to specific watches
            all_links = soup.find_all('a', href=True)
            watch_links = []
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text().strip()
                
                # Look for links that might be watch pages
                if any(pattern in href.lower() for pattern in ['/watch', '/model', brand.lower(), model.lower()]):
                    if href.startswith('/'):
                        full_url = f"https://watchcharts.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # Check if it mentions our brand/model
                    if brand.lower() in text.lower() or model.lower() in text.lower() or model in href:
                        watch_links.append((full_url, text[:50]))
            
            print(f"   Found {len(watch_links)} potentially relevant links")
            if watch_links:
                print("   Sample links:")
                for url, text in watch_links[:5]:
                    print(f"     - {text}: {url}")
            
            # Look for search functionality
            search_inputs = soup.find_all(['input', 'form'], {'type': 'search'}) + soup.find_all('input', {'name': re.compile('search|q', re.I)})
            if search_inputs:
                print(f"\n   Found search inputs on page")
            
            # Look for any forms
            forms = soup.find_all('form')
            if forms:
                print(f"   Found {len(forms)} forms on page")
                for form in forms:
                    action = form.get('action', '')
                    method = form.get('method', 'GET')
                    if action:
                        print(f"     Form action: {action} (method: {method})")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Try searching on the site
    print(f"\n2. Trying to search for '{brand} {model}'...")
    try:
        # Try different search endpoints
        search_urls = [
            f"https://watchcharts.com/watches?search={brand}+{model}",
            f"https://watchcharts.com/watches?q={brand}+{model}",
            f"https://watchcharts.com/watches?filter={brand}",
        ]
        
        for search_url in search_urls:
            try:
                response = scraper.get(search_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    print(f"   ✅ {search_url} - Status 200")
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text()
                    
                    # Check if results contain our watch
                    if brand.lower() in text.lower() and model.lower() in text.lower():
                        print(f"      ✅ Page contains {brand} {model}!")
                        
                        # Look for price data
                        price_matches = re.findall(r'\$([\d,]+\.?\d*)', text)
                        if price_matches:
                            print(f"      💰 Found {len(price_matches)} price mentions")
                        
                        # Look for watch card links
                        cards = soup.find_all(['div', 'article', 'section'], class_=re.compile('watch|card|item', re.I))
                        print(f"      📊 Found {len(cards)} potential watch cards")
                        
                        # Try to find a specific watch link
                        for link in soup.find_all('a', href=True):
                            href = link.get('href', '')
                            link_text = link.get_text()
                            if model in href or (brand.lower() in link_text.lower() and model in link_text):
                                if href.startswith('/'):
                                    full_url = f"https://watchcharts.com{href}"
                                elif href.startswith('http'):
                                    full_url = href
                                else:
                                    continue
                                print(f"      🔗 Potential watch link: {full_url}")
                                print(f"         Text: {link_text[:60]}")
                                break
                        
                        print(f"\n   💡 Working search URL: {search_url}")
                        break
                    else:
                        print(f"      ⚠️  Page doesn't contain specific watch")
            except Exception as e:
                print(f"   ❌ {search_url} - Error: {str(e)[:50]}")
    
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    brand = "Rolex"
    model = "126300"
    
    if len(sys.argv) > 1:
        brand = sys.argv[1]
    if len(sys.argv) > 2:
        model = sys.argv[2]
    
    explore_watchcharts(brand, model)

