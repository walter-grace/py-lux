#!/usr/bin/env python3
"""
Test to find watch_model links in WatchCharts search results
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

def find_watch_model_links(brand, model):
    """Find watch_model links on WatchCharts"""
    search_query = f"{brand} {model}"
    encoded = quote_plus(search_query)
    search_url = f"https://watchcharts.com/watches?search={encoded}"
    
    print(f"Search URL: {search_url}\n")
    
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    
    try:
        response = scraper.get(search_url, timeout=15)
        print(f"Status: {response.status_code}\n")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all watch_model links
            all_links = soup.find_all('a', href=True)
            watch_model_links = []
            
            print("Found watch_model links:\n")
            for link in all_links:
                href = link.get('href', '')
                if '/watch_model/' in href:
                    link_text = link.get_text().strip()
                    
                    # Construct full URL
                    if href.startswith('/'):
                        full_url = f"https://watchcharts.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # Ensure /overview
                    if '/overview' not in full_url:
                        full_url = f"{full_url.rstrip('/')}/overview"
                    
                    watch_model_links.append((full_url, link_text, href))
                    print(f"  {link_text[:60]}")
                    print(f"    URL: {full_url}")
                    print(f"    Href: {href}\n")
            
            print(f"\nTotal watch_model links found: {len(watch_model_links)}")
            
            # Try to find the best match
            brand_lower = brand.lower()
            model_lower = model.lower() if model else ""
            
            print(f"\nLooking for best match (brand: {brand}, model: {model})...\n")
            
            best_matches = []
            for url, text, href in watch_model_links:
                score = 0
                url_lower = url.lower()
                text_lower = text.lower()
                
                if brand_lower in url_lower:
                    score += 2
                if brand_lower in text_lower:
                    score += 1
                
                if model:
                    if model_lower in url_lower or model in url:
                        score += 5
                    if model_lower in text_lower or model in text:
                        score += 3
                
                if score > 0:
                    best_matches.append((score, url, text))
            
            if best_matches:
                best_matches.sort(reverse=True, key=lambda x: x[0])
                print("Best matches:\n")
                for score, url, text in best_matches[:5]:
                    print(f"  Score: {score}")
                    print(f"  {text[:60]}")
                    print(f"  {url}\n")
                
                return best_matches[0][1]  # Return best URL
            else:
                print("No matches found")
                return None
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    brand = "Rolex"
    model = "126720"  # GMT Master II Sprite
    
    if len(sys.argv) > 1:
        brand = sys.argv[1]
    if len(sys.argv) > 2:
        model = sys.argv[2]
    
    print("="*70)
    print("Finding WatchCharts watch_model Links")
    print("="*70)
    
    url = find_watch_model_links(brand, model)
    
    if url:
        print(f"\n✅ Best URL: {url}")
    else:
        print(f"\n❌ Could not find matching watch_model URL")

