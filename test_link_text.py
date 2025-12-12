#!/usr/bin/env python3
"""Check link text for model numbers"""
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

brand = "Rolex"
model_number = "126710BLNR"
search_query = f"{brand} {model_number}"
encoded = quote_plus(search_query)
search_url = f"https://watchcharts.com/watches?search={encoded}"

scraper = cloudscraper.create_scraper()
scraper.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

response = scraper.get(search_url, timeout=15)
if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all watch cards/links
    links = soup.find_all('a', href=True)
    
    print(f"Searching for: {brand} {model_number}\n")
    print("=" * 80)
    
    for link in links:
        href = link.get('href', '')
        if '/watch_model/' in href:
            # Get all text from the link and its parent container
            link_text = link.get_text(strip=True)
            
            # Also check parent elements for more context
            parent = link.parent
            parent_text = ""
            if parent:
                parent_text = parent.get_text(strip=True)
            
            # Check if model number appears anywhere
            href_lower = href.lower()
            all_text = (link_text + " " + parent_text).lower()
            
            if '126710' in href_lower or '126710' in all_text or 'gmt' in href_lower:
                print(f"\nLink: {href}")
                print(f"Link text: {link_text[:200]}")
                print(f"Parent text: {parent_text[:200]}")
                print(f"  Contains '126710': {'126710' in href_lower or '126710' in all_text}")
                print(f"  Contains 'blnr': {'blnr' in href_lower or 'blnr' in all_text}")
                print(f"  Contains 'gmt-master': {'gmt-master' in href_lower}")

