"""
Generate targeted Amazon search queries based on eBay item details
"""
from typing import Optional, Dict, Any
import re


def generate_targeted_amazon_query(ebay_item: Dict[str, Any], item_type: str) -> Optional[str]:
    """
    Generates a targeted Amazon search query based on an eBay item's details.
    
    Args:
        ebay_item: eBay item dictionary
        item_type: "luxury" or "trading_cards"
        
    Returns:
        Search query string or None if insufficient data
    """
    query_parts = []

    if item_type == "luxury":
        brand = ebay_item.get("brand")
        title = ebay_item.get("title", "").lower()
        condition = ebay_item.get("condition", "").lower()

        if brand:
            query_parts.append(brand)
        
        # Extract key product terms from title
        if "boot" in title:
            query_parts.append("boot")
        if "shoe" in title:
            query_parts.append("shoe")
        if "bag" in title:
            query_parts.append("bag")
        if "handbag" in title:
            query_parts.append("handbag")
        if "sneaker" in title:
            query_parts.append("sneaker")
        
        # Add size if available
        size_match = next((s for s in ["7.5", "7", "8", "9", "10", "11"] if s in title), None)
        if size_match:
            query_parts.append(f"size {size_match}")
        
        # Add material if available
        if "leather" in title:
            query_parts.append("leather")
        if "suede" in title:
            query_parts.append("suede")
        
        # Add style keywords
        if "western" in title:
            query_parts.append("western")
        if "lug" in title:
            query_parts.append("lug")
        if "ankle" in title:
            query_parts.append("ankle")
        if "knee" in title or "knee-high" in title:
            query_parts.append("knee high")

    elif item_type == "trading_cards":
        card_name = ebay_item.get("card_name")
        year = ebay_item.get("year")
        cert = ebay_item.get("cert")
        set_name = ebay_item.get("set_name", "")
        
        if card_name:
            # Clean up card name (remove common prefixes/suffixes)
            card_clean = card_name.replace("Yu-Gi-Oh!", "").replace("Pokemon", "").strip()
            query_parts.append(card_clean)
        
        if year:
            query_parts.append(year)
        
        if set_name:
            query_parts.append(set_name)
        
        # Always add PSA 10 and 1st edition for cards
        query_parts.append("PSA 10")
        query_parts.append("1st edition")

    if not query_parts:
        return None
    
    return " ".join(query_parts)

