#!/usr/bin/env python3
"""
Test script to debug WatchCharts URL matching
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from lib.watch_api import get_watchcharts_url
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

def test_watch_url(watch_info):
    """Test getting WatchCharts URL for a watch"""
    print(f"\n{'='*70}")
    print(f"Testing WatchCharts URL for:")
    print(f"  Brand: {watch_info.get('brand')}")
    print(f"  Model: {watch_info.get('model')}")
    print(f"  Model Number: {watch_info.get('model_number')}")
    print(f"{'='*70}\n")
    
    url = get_watchcharts_url(watch_info)
    print(f"Generated URL: {url}\n")
    
    # Also manually check what the search returns
    brand = watch_info.get("brand")
    model = watch_info.get("model_number") or watch_info.get("model")
    
    if brand and model:
        search_query = f"{brand} {model}"
        encoded_query = quote_plus(search_query)
        search_url = f"https://watchcharts.com/watches?search={encoded_query}"
        
        print(f"Search URL: {search_url}\n")
        print("Checking search results...")
        
        try:
            scraper = cloudscraper.create_scraper()
            scraper.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            
            response = scraper.get(search_url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=True)
                
                print(f"\nFound {len(links)} links total")
                print("\nWatch model links found:")
                print("-" * 70)
                
                watch_model_links = []
                for link in links:
                    href = link.get('href', '')
                    if '/watch_model/' in href:
                        link_text = link.get_text().strip()
                        watch_model_links.append((href, link_text))
                        print(f"  URL: {href}")
                        print(f"  Text: {link_text}")
                        print()
                
                if not watch_model_links:
                    print("  No watch_model links found!")
                else:
                    print(f"\nTotal watch_model links: {len(watch_model_links)}")
                    
                    # Check which one should match
                    model_number = watch_info.get("model_number")
                    if model_number:
                        print(f"\nLooking for model number: {model_number}")
                        for href, text in watch_model_links:
                            href_lower = href.lower()
                            text_lower = text.lower()
                            model_lower = model_number.lower()
                            
                            in_href = model_lower in href_lower or model_number.replace('-', '').replace(' ', '').lower() in href_lower.replace('-', '').replace('_', '')
                            in_text = model_lower in text_lower or model_number.replace('-', '').replace(' ', '').lower() in text_lower.replace('-', '').replace(' ', '')
                            
                            print(f"\n  Link: {href}")
                            print(f"    Model in URL: {in_href}")
                            print(f"    Model in text: {in_text}")
                            if in_href and in_text:
                                print(f"    ✅ SHOULD MATCH THIS ONE!")
            else:
                print(f"Error: Status code {response.status_code}")
        except Exception as e:
            print(f"Error checking search results: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Test with the problematic watch
    test_watch = {
        "brand": "Rolex",
        "model": "GMT-Master II",
        "model_number": "126710BLNR"
    }
    
    test_watch_url(test_watch)
    
    # Test with another watch
    print("\n\n" + "="*70)
    print("Testing another watch...")
    test_watch2 = {
        "brand": "Rolex",
        "model": "Datejust 41",
        "model_number": "126334"
    }
    
    test_watch_url(test_watch2)
