"""
Build targeted Facebook Marketplace searches based on eBay items found
This optimizes the search to find the same items on Facebook Marketplace
"""

from typing import List
import re


def extract_key_terms_from_ebay_items(ebay_items: list, item_type: str = "luxury") -> str:
    """
    Extract key search terms from eBay items to build a targeted Facebook Marketplace query.
    
    Args:
        ebay_items: List of eBay items
        item_type: "luxury" or "trading_cards"
        
    Returns:
        Optimized search query string for Facebook Marketplace
    """
    if not ebay_items:
        return ""
    
    if item_type == "trading_cards":
        # For trading cards, extract: card name, year, set, PSA grade
        card_names = set()
        years = set()
        sets = set()
        
        for item in ebay_items:
            card_name = item.get("card_name", "")
            if card_name:
                # Clean up card name (remove special chars, keep main name)
                clean_name = re.sub(r'[^\w\s]', '', card_name).strip()
                if clean_name and len(clean_name) > 2:
                    card_names.add(clean_name.split()[0])  # First word (e.g., "Blue-Eyes")
            
            year = item.get("year", "")
            if year:
                years.add(year)
            
            set_name = item.get("set_name", "")
            if set_name:
                # Extract set abbreviation (e.g., "LOB" from "Legend of Blue Eyes")
                set_abbr = set_name.split()[0] if set_name else ""
                if set_abbr and len(set_abbr) <= 5:  # Likely an abbreviation
                    sets.add(set_abbr)
        
        # Build query: "PSA 10 [card name] [year] [set]"
        query_parts = ["PSA 10"]
        if card_names:
            query_parts.append(list(card_names)[0])  # Use first card name
        if years:
            query_parts.append(list(years)[0])
        if sets:
            query_parts.append(list(sets)[0])
        
        return " ".join(query_parts) if len(query_parts) > 1 else "PSA 10"
    
    else:  # luxury items
        # For luxury items, extract: brand, product type, size, material
        brands = set()
        product_types = set()
        sizes = set()
        materials = set()
        
        for item in ebay_items:
            brand = item.get("brand", "")
            if brand:
                brands.add(brand)
            
            title = item.get("title", "").lower()
            
            # Extract product type from title (boots, shoes, bag, etc.)
            product_keywords = ["boot", "shoe", "bag", "handbag", "wallet", "belt", "jacket", "coat"]
            for keyword in product_keywords:
                if keyword in title:
                    product_types.add(keyword)
                    break
            
            # Extract size
            size_match = re.search(r'\b(size|sz)[\s:]*(\d+(?:\.\d+)?)', title)
            if size_match:
                sizes.add(size_match.group(2))
            
            # Extract material
            material_keywords = ["leather", "suede", "canvas", "fabric"]
            for keyword in material_keywords:
                if keyword in title:
                    materials.add(keyword)
                    break
        
        # Build query: "[brand] [product type] [size] [material]"
        query_parts = []
        
        if brands:
            # Use most common brand or first one
            brand_list = list(brands)
            query_parts.append(brand_list[0])
        
        if product_types:
            query_parts.append(list(product_types)[0])
        
        if sizes:
            query_parts.append(f"size {list(sizes)[0]}")
        
        if materials:
            query_parts.append(list(materials)[0])
        
        return " ".join(query_parts) if query_parts else ""
    
    return ""


def build_targeted_fb_query(ebay_items: list, item_type: str = "luxury", fallback_query: str = "") -> str:
    """
    Build the best Facebook Marketplace query based on eBay items found.
    
    Args:
        ebay_items: List of eBay items
        item_type: "luxury" or "trading_cards"
        fallback_query: Fallback query if extraction fails
        
    Returns:
        Optimized search query for Facebook Marketplace
    """
    targeted_query = extract_key_terms_from_ebay_items(ebay_items, item_type)
    
    # If extraction didn't work well, use fallback
    if not targeted_query or len(targeted_query) < 5:
        return fallback_query
    
    return targeted_query


def get_price_range_from_ebay_items(ebay_items: list) -> tuple[float, float]:
    """
    Calculate min/max price range from eBay items for Facebook Marketplace filtering.
    
    Args:
        ebay_items: List of eBay items with prices
        
    Returns:
        Tuple of (min_price, max_price) for filtering
    """
    if not ebay_items:
        return 50.0, 5000.0  # Default range
    
    prices = []
    for item in ebay_items:
        price = item.get("price", 0) + item.get("shipping", 0)
        if price > 0:
            prices.append(price)
    
    if not prices:
        return 50.0, 5000.0
    
    min_price = min(prices)
    max_price = max(prices)
    
    # Add buffer: 20% below min, 50% above max to catch similar items
    min_price_filter = max(10, min_price * 0.8)
    max_price_filter = max_price * 1.5
    
    # Cap at reasonable limits
    min_price_filter = max(10, min(min_price_filter, 1000))
    max_price_filter = min(max_price_filter, 10000)
    
    return min_price_filter, max_price_filter

