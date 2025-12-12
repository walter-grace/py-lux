#!/usr/bin/env python3
"""
Final test: Get WatchCharts URL and show stats from the website
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from lib.watch_api import get_watchcharts_url
import cloudscraper
from bs4 import BeautifulSoup
import re

def get_watchcharts_stats(url, brand, model):
    """Get stats from WatchCharts page"""
    print(f"\n{'='*70}")
    print(f"Fetching stats from WatchCharts")
    print(f"{'='*70}\n")
    print(f"URL: {url}\n")
    
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    
    try:
        response = scraper.get(url, timeout=15, allow_redirects=True)
        print(f"Status Code: {response.status_code}")
        print(f"Final URL: {response.url}\n")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            
            # Check if page contains our watch
            has_brand = brand.lower() in text.lower()
            has_model = model.lower() in text.lower()
            
            print(f"Page contains '{brand}': {has_brand}")
            print(f"Page contains '{model}': {has_model}\n")
            
            # Extract prices
            print("💰 Price Data Found:")
            price_patterns = [
                (r'\$([\d,]+\.?\d*)', 'All dollar amounts'),
                (r'Market\s+Price[:\s]*\$?([\d,]+\.?\d*)', 'Market Price'),
                (r'Current\s+Price[:\s]*\$?([\d,]+\.?\d*)', 'Current Price'),
                (r'Average[:\s]*\$?([\d,]+\.?\d*)', 'Average Price'),
            ]
            
            found_prices = []
            for pattern, label in price_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for match in matches[:5]:  # First 5 matches
                        try:
                            price = float(match.replace(',', ''))
                            if 100 <= price <= 1000000:  # Reasonable range
                                found_prices.append((price, label))
                        except:
                            pass
            
            if found_prices:
                # Remove duplicates and sort
                unique_prices = sorted(set([p[0] for p in found_prices]), reverse=True)
                print(f"   Found {len(unique_prices)} unique prices:")
                for price in unique_prices[:10]:  # Top 10
                    print(f"     ${price:,.2f}")
            else:
                print("   No prices found in reasonable range")
            
            # Count watch-related elements
            print(f"\n📊 Page Statistics:")
            watch_cards = soup.find_all(['div', 'article'], class_=re.compile('watch|card|item', re.I))
            print(f"   Watch cards/sections: {len(watch_cards)}")
            
            links = soup.find_all('a', href=True)
            watch_links = [l for l in links if any(x in l.get('href', '').lower() for x in ['/watch', '/model', brand.lower()])]
            print(f"   Watch-related links: {len(watch_links)}")
            
            # Look for specific watch mentions
            brand_mentions = len(re.findall(re.escape(brand), text, re.IGNORECASE))
            model_mentions = len(re.findall(re.escape(model), text, re.IGNORECASE))
            print(f"   '{brand}' mentioned: {brand_mentions} times")
            print(f"   '{model}' mentioned: {model_mentions} times")
            
            # Try to find a direct link to the watch
            print(f"\n🔗 Direct Watch Links Found:")
            direct_links = []
            for link in watch_links[:20]:  # Check first 20
                href = link.get('href', '')
                link_text = link.get_text().strip()
                
                if model in href or (brand.lower() in link_text.lower() and model in link_text):
                    if href.startswith('/'):
                        full_url = f"https://watchcharts.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    direct_links.append((full_url, link_text[:50]))
            
            if direct_links:
                for url, text in direct_links[:5]:
                    print(f"   {text}")
                    print(f"     → {url}")
            else:
                print("   No direct watch links found")
            
            return True
        else:
            print(f"❌ Page returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    brand = "Rolex"
    model = "126300"
    
    if len(sys.argv) > 1:
        brand = sys.argv[1]
    if len(sys.argv) > 2:
        model = sys.argv[2]
    
    print("="*70)
    print("WatchCharts URL & Stats Test")
    print("="*70)
    
    # Generate URL
    watch_info = {
        "brand": brand,
        "model": model,
        "model_number": model,
    }
    
    url = get_watchcharts_url(watch_info)
    print(f"\n✅ Generated URL: {url}")
    
    # Test the URL and get stats
    if url:
        get_watchcharts_stats(url, brand, model)
    else:
        print("\n❌ Could not generate URL")

