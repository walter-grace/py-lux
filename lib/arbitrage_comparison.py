"""
Cross-platform arbitrage comparison logic
Matches items across eBay and Facebook Marketplace
"""
from typing import TypedDict, Optional, Literal
import re
from difflib import SequenceMatcher


class CrossPlatformMatch(TypedDict):
    ebay_item: dict
    facebook_item: Optional[dict]
    amazon_item: Optional[dict]
    match_confidence: float
    price_difference: float
    best_platform: Literal["eBay", "Facebook", "Amazon"]
    match_reason: str


def similarity_score(str1: str, str2: str) -> float:
    """Calculate similarity between two strings (0-1)"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text for matching"""
    if not text:
        return set()
    
    # Remove common words
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "psa", "grade", "edition"}
    
    # Extract words (alphanumeric, at least 3 chars)
    words = re.findall(r'\b[a-z0-9]{3,}\b', text.lower())
    return set(word for word in words if word not in stop_words)


def match_trading_cards(ebay_item: dict, facebook_item: dict) -> Optional[CrossPlatformMatch]:
    """
    Match trading cards across platforms.
    Priority: cert number (exact) > title similarity + price range
    """
    ebay_title = ebay_item.get("title", "")
    fb_title = facebook_item.get("title", "")
    
    # Exact cert match (highest confidence)
    ebay_cert = ebay_item.get("cert", "")
    fb_cert = facebook_item.get("cert", "")
    
    if ebay_cert and fb_cert and ebay_cert == fb_cert:
        ebay_price = ebay_item.get("price", 0) + ebay_item.get("shipping", 0)
        fb_price = facebook_item.get("price", 0) + facebook_item.get("shipping", 0)
        price_diff = abs(ebay_price - fb_price)
        
        return CrossPlatformMatch(
            ebay_item=ebay_item,
            facebook_item=facebook_item,
            amazon_item=None,
            match_confidence=1.0,
            price_difference=price_diff,
            best_platform="Facebook" if fb_price < ebay_price else "eBay",
            match_reason=f"Exact cert match: {ebay_cert}"
        )
    
    # Title similarity + price range match
    title_sim = similarity_score(ebay_title, fb_title)
    
    # Extract key card identifiers
    ebay_keywords = extract_keywords(ebay_title)
    fb_keywords = extract_keywords(fb_title)
    
    # Check for PSA 10, 1st edition, card name matches
    psa_match = "psa" in ebay_title.lower() and "psa" in fb_title.lower()
    grade_match = "10" in ebay_title and "10" in fb_title
    edition_match = ("1st" in ebay_title.lower() or "first" in ebay_title.lower()) and \
                   ("1st" in fb_title.lower() or "first" in fb_title.lower())
    
    # Calculate keyword overlap
    keyword_overlap = len(ebay_keywords & fb_keywords) / max(len(ebay_keywords | fb_keywords), 1)
    
    # Combined confidence score
    confidence = (title_sim * 0.4) + (keyword_overlap * 0.3) + (0.1 if psa_match else 0) + \
                (0.1 if grade_match else 0) + (0.1 if edition_match else 0)
    
    # Price range check (within 30% of each other)
    ebay_price = ebay_item.get("price", 0) + ebay_item.get("shipping", 0)
    fb_price = facebook_item.get("price", 0) + facebook_item.get("shipping", 0)
    
    if ebay_price > 0 and fb_price > 0:
        price_ratio = min(ebay_price, fb_price) / max(ebay_price, fb_price)
        if price_ratio < 0.7:  # Prices differ by more than 30%
            confidence *= 0.5  # Reduce confidence for very different prices
    
    # Only return match if confidence is high enough
    if confidence >= 0.6:
        price_diff = abs(ebay_price - fb_price)
        return CrossPlatformMatch(
            ebay_item=ebay_item,
            facebook_item=facebook_item,
            amazon_item=None,
            match_confidence=confidence,
            price_difference=price_diff,
            best_platform="Facebook" if fb_price < ebay_price else "eBay",
            match_reason=f"Title similarity: {title_sim:.2f}, Keywords: {keyword_overlap:.2f}"
        )
    
    return None


def match_luxury_items(ebay_item: dict, facebook_item: dict) -> Optional[CrossPlatformMatch]:
    """
    Match luxury items across platforms.
    Priority: brand + product keywords + size + condition
    """
    ebay_title = ebay_item.get("title", "")
    fb_title = facebook_item.get("title", "")
    
    # Brand match (required)
    ebay_brand = ebay_item.get("brand", "").lower()
    fb_brand = facebook_item.get("brand", "").lower()
    
    # Extract brand from title if not in metadata
    if not ebay_brand:
        luxury_brands = ["gucci", "ysl", "saint laurent", "louis vuitton", "prada", "chanel", "dior"]
        for brand in luxury_brands:
            if brand in ebay_title.lower():
                ebay_brand = brand
                break
    
    if not fb_brand:
        luxury_brands = ["gucci", "ysl", "saint laurent", "louis vuitton", "prada", "chanel", "dior"]
        for brand in luxury_brands:
            if brand in fb_title.lower():
                fb_brand = brand
                break
    
    # Brand must match
    if ebay_brand and fb_brand and ebay_brand != fb_brand:
        return None
    
    if not ebay_brand or not fb_brand:
        # Try to match by checking if same brand appears in both titles
        ebay_title_lower = ebay_title.lower()
        fb_title_lower = fb_title.lower()
        brand_match = False
        for brand in ["gucci", "ysl", "saint laurent", "louis vuitton", "prada", "chanel", "dior"]:
            if brand in ebay_title_lower and brand in fb_title_lower:
                brand_match = True
                break
        if not brand_match:
            return None
    
    # Size match (if specified)
    ebay_size = ebay_item.get("size", "")
    fb_size = facebook_item.get("size", "")
    
    # Extract size from title if not in metadata
    size_pattern = r'\b(size|sz)[\s:]*(\d+(?:\.\d+)?)'
    if not ebay_size:
        match = re.search(size_pattern, ebay_title.lower())
        if match:
            ebay_size = match.group(2)
    
    if not fb_size:
        match = re.search(size_pattern, fb_title.lower())
        if match:
            fb_size = match.group(2)
    
    # Condition match (new vs used)
    ebay_condition = ebay_item.get("condition", "").lower()
    fb_condition = facebook_item.get("condition", "").lower()
    ebay_is_new = "new" in ebay_condition or "new" in ebay_title.lower()
    fb_is_new = "new" in fb_condition or "new" in fb_title.lower()
    
    # Calculate confidence
    title_sim = similarity_score(ebay_title, fb_title)
    ebay_keywords = extract_keywords(ebay_title)
    fb_keywords = extract_keywords(fb_title)
    keyword_overlap = len(ebay_keywords & fb_keywords) / max(len(ebay_keywords | fb_keywords), 1)
    
    confidence = (title_sim * 0.4) + (keyword_overlap * 0.3)
    
    # Size match bonus
    if ebay_size and fb_size and ebay_size == fb_size:
        confidence += 0.2
    elif ebay_size or fb_size:
        confidence -= 0.1  # Penalty if one has size and other doesn't
    
    # Condition match bonus
    if ebay_is_new == fb_is_new:
        confidence += 0.1
    
    # Only return match if confidence is high enough
    if confidence >= 0.5:
        ebay_price = ebay_item.get("price", 0) + ebay_item.get("shipping", 0)
        fb_price = facebook_item.get("price", 0) + facebook_item.get("shipping", 0)
        price_diff = abs(ebay_price - fb_price)
        
        return CrossPlatformMatch(
            ebay_item=ebay_item,
            facebook_item=facebook_item,
            amazon_item=None,
            match_confidence=confidence,
            price_difference=price_diff,
            best_platform="Facebook" if fb_price < ebay_price else "eBay",
            match_reason=f"Brand match, Title similarity: {title_sim:.2f}"
        )
    
    return None


def compare_ebay_facebook(
    ebay_items: list[dict],
    fb_items: list[dict],
    item_type: Literal["trading_cards", "luxury"]
) -> list[CrossPlatformMatch]:
    """
    Compare items across eBay and Facebook Marketplace.
    
    Args:
        ebay_items: List of eBay items
        fb_items: List of Facebook Marketplace items
        item_type: Type of items ("trading_cards" or "luxury")
        
    Returns:
        List of CrossPlatformMatch objects
    """
    matches = []
    
    match_func = match_trading_cards if item_type == "trading_cards" else match_luxury_items
    
    for ebay_item in ebay_items:
        for fb_item in fb_items:
            match = match_func(ebay_item, fb_item)
            if match:
                matches.append(match)
    
    # Sort by confidence (highest first)
    matches.sort(key=lambda x: x["match_confidence"], reverse=True)
    
    return matches


def compare_ebay_amazon(
    ebay_items: list[dict],
    amazon_items: list[dict],
    item_type: Literal["trading_cards", "luxury"]
) -> list[CrossPlatformMatch]:
    """
    Compare items across eBay and Amazon.
    
    Args:
        ebay_items: List of eBay items
        amazon_items: List of Amazon items
        item_type: Type of items ("trading_cards" or "luxury")
        
    Returns:
        List of CrossPlatformMatch objects
    """
    matches = []
    
    match_func = match_trading_cards_amazon if item_type == "trading_cards" else match_luxury_items_amazon
    
    for ebay_item in ebay_items:
        for amazon_item in amazon_items:
            match = match_func(ebay_item, amazon_item)
            if match:
                matches.append(match)
    
    # Sort by confidence (highest first)
    matches.sort(key=lambda x: x["match_confidence"], reverse=True)
    
    return matches


def compare_all_platforms(
    ebay_items: list[dict],
    fb_items: list[dict],
    amazon_items: list[dict],
    item_type: Literal["trading_cards", "luxury"]
) -> list[dict]:
    """
    Compare items across all three platforms (eBay, Facebook, Amazon).
    Returns matches with all platforms included.
    
    Args:
        ebay_items: List of eBay items
        fb_items: List of Facebook Marketplace items
        amazon_items: List of Amazon items
        item_type: Type of items ("trading_cards" or "luxury")
        
    Returns:
        List of match dictionaries with all platform comparisons
    """
    all_matches = []
    
    # Get eBay-Facebook matches
    ebay_fb_matches = compare_ebay_facebook(ebay_items, fb_items, item_type)
    
    # Get eBay-Amazon matches
    ebay_amazon_matches = compare_ebay_amazon(ebay_items, amazon_items, item_type)
    
    # Combine and find 3-way matches
    for ebay_item in ebay_items:
        fb_match = None
        amazon_match = None
        
        # Find Facebook match
        for match in ebay_fb_matches:
            if match["ebay_item"]["item_id"] == ebay_item["item_id"]:
                fb_match = match
                break
        
        # Find Amazon match
        for match in ebay_amazon_matches:
            if match["ebay_item"]["item_id"] == ebay_item["item_id"]:
                amazon_match = match
                break
        
        # If we have matches on any platform, create a combined match
        if fb_match or amazon_match:
            ebay_price = ebay_item.get("price", 0) + ebay_item.get("shipping", 0)
            fb_price = fb_match["facebook_item"].get("price", 0) + fb_match["facebook_item"].get("shipping", 0) if fb_match else None
            amazon_price = amazon_match["amazon_item"].get("price", 0) + amazon_match["amazon_item"].get("shipping", 0) if amazon_match else None
            
            # Determine best platform
            prices = {"eBay": ebay_price}
            if fb_price is not None:
                prices["Facebook"] = fb_price
            if amazon_price is not None:
                prices["Amazon"] = amazon_price
            
            best_platform = min(prices, key=prices.get) if prices else "eBay"
            
            all_matches.append({
                "ebay_item": ebay_item,
                "facebook_item": fb_match["facebook_item"] if fb_match else None,
                "amazon_item": amazon_match["amazon_item"] if amazon_match else None,
                "ebay_price": ebay_price,
                "facebook_price": fb_price,
                "amazon_price": amazon_price,
                "best_platform": best_platform,
                "price_difference": max(prices.values()) - min(prices.values()) if len(prices) > 1 else 0,
            })
    
    return all_matches


def calculate_cross_platform_spread(
    ebay_item: dict,
    fb_item: dict,
    reference_price: Optional[float] = None
) -> dict:
    """
    Calculate arbitrage spread between eBay and Facebook Marketplace.
    
    Args:
        ebay_item: eBay item dict
        fb_item: Facebook Marketplace item dict
        reference_price: Reference price (e.g., PSA estimate, retail price)
        
    Returns:
        Dict with spread calculations
    """
    ebay_all_in = ebay_item.get("price", 0) + ebay_item.get("shipping", 0)
    fb_all_in = fb_item.get("price", 0) + fb_item.get("shipping", 0)
    
    price_diff = abs(ebay_all_in - fb_all_in)
    cheaper_platform = "Facebook" if fb_all_in < ebay_all_in else "eBay"
    savings = abs(ebay_all_in - fb_all_in)
    
    result = {
        "ebay_price": ebay_all_in,
        "facebook_price": fb_all_in,
        "price_difference": price_diff,
        "cheaper_platform": cheaper_platform,
        "savings": savings,
    }
    
    if reference_price:
        ebay_spread = reference_price - ebay_all_in
        fb_spread = reference_price - fb_all_in
        best_spread = max(ebay_spread, fb_spread)
        best_platform = "eBay" if ebay_spread > fb_spread else "Facebook"
        
        result.update({
            "reference_price": reference_price,
            "ebay_spread": ebay_spread,
            "facebook_spread": fb_spread,
            "best_spread": best_spread,
            "best_platform_for_arbitrage": best_platform,
        })
    
    return result


def find_best_deals(
    ebay_items: list[dict],
    fb_items: list[dict],
    reference_prices: dict[str, float],
    item_type: Literal["trading_cards", "luxury"]
) -> list[dict]:
    """
    Find best arbitrage opportunities across platforms.
    
    Args:
        ebay_items: List of eBay items
        fb_items: List of Facebook Marketplace items
        reference_prices: Dict mapping item IDs to reference prices
        item_type: Type of items
        
    Returns:
        List of best deals with arbitrage calculations
    """
    matches = compare_ebay_facebook(ebay_items, fb_items, item_type)
    
    best_deals = []
    for match in matches:
        ebay_item = match["ebay_item"]
        fb_item = match["facebook_item"]
        
        # Get reference price if available
        ref_price = reference_prices.get(ebay_item.get("item_id")) or \
                   reference_prices.get(fb_item.get("item_id"))
        
        spread_data = calculate_cross_platform_spread(ebay_item, fb_item, ref_price)
        
        deal = {
            "match": match,
            "spread_data": spread_data,
            "ebay_item": ebay_item,
            "facebook_item": fb_item,
        }
        
        best_deals.append(deal)
    
    # Sort by best spread (if reference price available) or savings
    best_deals.sort(
        key=lambda x: x["spread_data"].get("best_spread", x["spread_data"]["savings"]),
        reverse=True
    )
    
    return best_deals

