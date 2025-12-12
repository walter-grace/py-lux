#!/usr/bin/env python3
"""Check what the search results actually look like"""
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

brand = "Rolex"
model_number = "126710BLNR"
search_query = f"{brand} {model_number}"
encoded = quote_plus(search_query)
search_url = f"https://watchcharts.com/watches?search={encoded}"

print(f"Search URL: {search_url}\n")

scraper = cloudscraper.create_scraper()
scraper.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

response = scraper.get(search_url, timeout=15)
if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)
    
    print(f"Looking for model: {model_number}")
    print(f"Model (lowercase, no dashes): {model_number.lower().replace('-', '').replace(' ', '')}\n")
    
    print("Watch model links found:")
    print("=" * 80)
    
    watch_links = []
    for link in links:
        href = link.get('href', '')
        if '/watch_model/' in href:
            link_text = link.get_text().strip()
            watch_links.append((href, link_text))
    
    # Show first 10 unique links
    seen = set()
    count = 0
    for href, text in watch_links:
        if href not in seen and count < 10:
            seen.add(href)
            count += 1
            href_lower = href.lower()
            model_lower = model_number.lower()
            model_clean = model_number.replace('-', '').replace(' ', '').lower()
            href_clean = href_lower.replace('-', '').replace('_', '')
            
            print(f"\nLink: {href}")
            print(f"Text: {text[:100]}")
            print(f"  Model in URL (exact): {model_lower in href_lower}")
            print(f"  Model in URL (clean): {model_clean in href_clean}")
            print(f"  Model in text: {model_lower in text.lower()}")
            
            # Check for partial matches
            if '126710' in href_lower:
                print(f"  ⚠️  Contains '126710' (partial match)")
            if 'gmt' in href_lower and 'master' in href_lower:
                print(f"  ⚠️  Contains 'gmt-master' (model name match)")
else:
    print(f"Error: Status {response.status_code}")

