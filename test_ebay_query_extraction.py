#!/usr/bin/env python3
"""Test query extraction for eBay searches"""
import re

test_queries = [
    "Search eBay for Rolex Submariner watches under $10,000",
    "Find Rolex watches on eBay under 10000",
    "Search eBay for Omega Speedmaster",
    "Find watches on eBay",
]

for query in test_queries:
    query_lower = query.lower()
    print(f"\nQuery: {query}")
    
    # Check if eBay query
    ebay_keywords = ["search ebay", "find on ebay", "ebay", "search for", "find", "look for", "show me", "get me"]
    is_ebay_query = "ebay" in query_lower and any(keyword in query_lower for keyword in ebay_keywords)
    print(f"  Is eBay query: {is_ebay_query}")
    
    if is_ebay_query:
        # Extract search query
        search_query = query
        for prefix in ["search ebay for", "find on ebay", "search for", "find", "look for", "show me", "get me"]:
            if prefix in query_lower:
                search_query = query[query_lower.find(prefix) + len(prefix):].strip()
                # Remove price filters
                search_query = re.sub(r'\s*(under|below|less than|max|maximum)\s*\$?\d+[,\d]*', '', search_query, flags=re.IGNORECASE).strip()
                break
        
        # If we didn't find a prefix, try to extract after "ebay"
        if search_query == query and "ebay" in query_lower:
            ebay_pos = query_lower.find("ebay")
            search_query = query[ebay_pos + 4:].strip()
            for word in ["for", "watches", "watch", "items", "listings"]:
                if search_query.lower().startswith(word + " "):
                    search_query = search_query[len(word):].strip()
            search_query = re.sub(r'\s*(under|below|less than|max|maximum)\s*\$?\d+[,\d]*', '', search_query, flags=re.IGNORECASE).strip()
        
        # Extract price limit
        price_limit = None
        if "under" in query_lower or "$" in query:
            price_matches = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', query)
            if price_matches:
                price_limit = int(price_matches[0].replace(',', ''))
        
        print(f"  Extracted search query: '{search_query}'")
        print(f"  Price limit: {price_limit}")

