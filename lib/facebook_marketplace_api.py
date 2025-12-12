"""
Facebook Marketplace API integration using RapidAPI
"""
import time
import re
from typing import TypedDict, Optional
import requests

# Import usage tracker
try:
    from lib.rapidapi_usage_tracker import record_request, print_usage_stats
except ImportError:
    # Fallback if tracker not available
    def record_request(*args, **kwargs):
        pass
    def print_usage_stats():
        pass


class FacebookMarketplaceItem(TypedDict):
    item_id: str
    title: str
    url: str
    price: float
    shipping: float
    currency: str
    location: Optional[str]
    seller_name: Optional[str]
    condition: Optional[str]
    image_url: Optional[str]
    description: Optional[str]
    posted_date: Optional[str]
    # Additional fields for matching
    brand: Optional[str]
    product_name: Optional[str]
    size: Optional[str]
    # For trading cards
    cert: Optional[str]
    card_name: Optional[str]
    year: Optional[str]
    set_name: Optional[str]


def extract_city_from_location(location: str) -> str:
    """Extract city name from location string (e.g., 'Los Angeles, CA' -> 'los angeles')"""
    if not location:
        return "los angeles"  # Default
    
    # Split by comma and take first part
    city = location.split(',')[0].strip().lower()
    return city


def normalize_facebook_item(item_data: dict) -> FacebookMarketplaceItem:
    """
    Normalize RapidAPI Facebook Marketplace response to our standard format.
    
    Args:
        item_data: Raw item data from RapidAPI
        
    Returns:
        Normalized FacebookMarketplaceItem
    """
    # Extract item ID - try multiple possible fields
    item_id = (
        item_data.get("id", "") or 
        item_data.get("itemId", "") or 
        item_data.get("item_id", "") or
        item_data.get("listing_id", "") or
        str(item_data.get("marketplace_listing_id", "")) if item_data.get("marketplace_listing_id") else ""
    )
    
    # Extract title - RapidAPI uses marketplace_listing_title
    title = (
        item_data.get("marketplace_listing_title", "") or 
        item_data.get("title", "") or 
        item_data.get("name", "") or
        item_data.get("listing_title", "") or
        item_data.get("product_title", "")
    )
    
    # Extract price - RapidAPI uses listing_price dict
    price = 0.0
    currency = "USD"
    listing_price = item_data.get("listing_price", {})
    if isinstance(listing_price, dict):
        # Try amount first (most reliable)
        if "amount" in listing_price:
            try:
                price = float(listing_price["amount"])
            except (ValueError, TypeError):
                pass
        # Fallback to formatted_amount
        if price == 0.0 and "formatted_amount" in listing_price:
            price_text = listing_price["formatted_amount"]
            price_match = re.search(r'[\d,]+\.?\d*', str(price_text).replace(',', ''))
            if price_match:
                try:
                    price = float(price_match.group().replace(',', ''))
                except ValueError:
                    price = 0.0
    
    # Extract URL - try multiple possible fields first
    url = (
        item_data.get("url", "") or
        item_data.get("item_url", "") or
        item_data.get("listing_url", "") or
        item_data.get("marketplace_listing_url", "") or
        item_data.get("link", "") or
        item_data.get("web_url", "")
    )
    
    # If no URL found, try to construct from item ID
    # Format: https://www.facebook.com/marketplace/item/{item_id}
    if not url and item_id:
        # Only construct URL if item_id looks like a real Facebook ID (numeric or alphanumeric, not our generated format)
        if not item_id.startswith("fb_") and item_id:
            url = f"https://www.facebook.com/marketplace/item/{item_id}"
    
    # Extract location - RapidAPI uses location.reverse_geocode
    location = ""
    location_data = item_data.get("location", {})
    if isinstance(location_data, dict):
        reverse_geocode = location_data.get("reverse_geocode", {})
        if isinstance(reverse_geocode, dict):
            city = reverse_geocode.get("city", "")
            state = reverse_geocode.get("state", "")
            if city and state:
                location = f"{city}, {state}"
            elif city:
                location = city
    
    # Extract seller - RapidAPI uses marketplace_listing_seller
    seller_name = None
    seller_data = item_data.get("marketplace_listing_seller")
    if isinstance(seller_data, dict):
        seller_name = seller_data.get("name", "") or seller_data.get("username", "")
    elif isinstance(seller_data, str):
        seller_name = seller_data
    
    # Extract condition - not directly available in RapidAPI response
    condition = None
    # Could check is_sold, is_live, etc.
    if item_data.get("is_sold"):
        condition = "Sold"
    elif item_data.get("is_live"):
        condition = "Available"
    
    # Extract images - RapidAPI uses primary_listing_photo.image.uri
    image_url = None
    photo_data = item_data.get("primary_listing_photo", {})
    if isinstance(photo_data, dict):
        image_data = photo_data.get("image", {})
        if isinstance(image_data, dict):
            image_url = image_data.get("uri", "")
        elif isinstance(image_data, str):
            image_url = image_data
    
    # Extract description - not directly available in RapidAPI response
    description = item_data.get("description", "") or item_data.get("text", "")
    
    # Extract posted date - not directly available in RapidAPI response
    posted_date = item_data.get("postedDate", "") or item_data.get("date", "")
    
    # Try to extract brand/product info from title/description for luxury items
    brand = None
    product_name = None
    size = None
    
    # Try to extract cert number for trading cards
    cert = None
    card_name = None
    year = None
    set_name = None
    
    # Extract cert from title or description
    cert_pattern = r'(?:cert|certification|psa)[\s#:]*(\d{6,8})'
    cert_match = re.search(cert_pattern, (title + " " + description).lower())
    if cert_match:
        cert = cert_match.group(1)
    
    # Extract PSA grade
    psa_match = re.search(r'psa[\s-]*(\d+)', title.lower())
    
    # Extract year
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', title)
    if year_match:
        year = year_match.group(1)
    
    # For luxury items, try to extract brand from title
    luxury_brands = ["gucci", "ysl", "saint laurent", "louis vuitton", "prada", "chanel", "dior"]
    title_lower = title.lower()
    for brand_name in luxury_brands:
        if brand_name in title_lower:
            brand = brand_name.title()
            break
    
    # Extract size (for shoes/clothing)
    size_match = re.search(r'\b(size|sz)[\s:]*(\d+(?:\.\d+)?)', title_lower)
    if size_match:
        size = size_match.group(2)
    
    return FacebookMarketplaceItem(
        item_id=item_id,
        title=title,
        url=url,
        price=price,
        shipping=0.0,  # Facebook Marketplace typically doesn't show shipping upfront
        currency=currency,
        location=location,
        seller_name=seller_name,
        condition=condition,
        image_url=image_url,
        description=description,
        posted_date=posted_date,
        brand=brand,
        product_name=product_name,
        size=size,
        cert=cert,
        card_name=card_name,
        year=year,
        set_name=set_name,
    )


def search_facebook_marketplace(
    query: str,
    max_items: int,
    env: dict[str, str],
    location: Optional[str] = None,
    sort_by: str = "newest",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    days_since_listed: Optional[int] = None
) -> list[FacebookMarketplaceItem]:
    """
    Search Facebook Marketplace using RapidAPI.
    
    ⚠️  WARNING: Free tier has only 30 requests/month - use sparingly!
    
    Args:
        query: Search query string
        max_items: Maximum number of items to return (keep low to conserve API calls)
        env: Environment variables dict with RAPIDAPI_KEY
        location: Location string (e.g., "Los Angeles, CA") - Optional, defaults to "Los Angeles, CA"
        sort_by: Sort order ("newest", "price_asc", "price_desc", "distance")
        min_price: Minimum price filter (optional)
        max_price: Maximum price filter (optional)
        days_since_listed: Filter by days since listing (optional, e.g., 7 for items listed in last week)
        
    Returns:
        List of normalized FacebookMarketplaceItem dictionaries
    """
    api_key = env.get("RAPIDAPI_KEY")
    
    if not api_key:
        raise ValueError("RAPIDAPI_KEY not found in environment")
    
    url = "https://facebook-marketplace1.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-host": "facebook-marketplace1.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    
    # Extract city from location (use default if not provided)
    if not location:
        location = env.get("DEFAULT_FB_LOCATION", "Los Angeles, CA")
    city = extract_city_from_location(location)
    
    # Map sort_by to RapidAPI format
    sort_map = {
        "relevance": "newest",  # Default to newest if relevance not available
        "newest": "newest",
        "price": "price_asc",
        "price_asc": "price_asc",
        "price_desc": "price_desc",
        "distance": "distance"
    }
    rapidapi_sort = sort_map.get(sort_by, "newest")
    
    # RapidAPI query parameters
    params = {
        "query": query,
        "city": city,
        "sort": rapidapi_sort,
        "limit": str(max_items),
    }
    
    # Add optional filters to get more targeted results
    if min_price is not None:
        params["minPrice"] = str(int(min_price))
    
    if max_price is not None:
        params["maxPrice"] = str(int(max_price))
    
    if days_since_listed is not None:
        params["daysSinceListed"] = str(days_since_listed)
    
    items: list[FacebookMarketplaceItem] = []
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] Facebook Marketplace API Request:")
            print(f"  URL: {url}")
            print(f"  Query: {query}")
            print(f"  City: {city}")
            print(f"  Params: {params}")
            
            # RapidAPI should be faster than Apify
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            print(f"[DEBUG] Facebook Marketplace API Response:")
            print(f"  Status Code: {response.status_code}")
            print(f"  Headers: {dict(response.headers)}")
            
            if response.status_code == 401 or response.status_code == 403:
                error_msg = f"RapidAPI Authentication Error ({response.status_code})"
                print(f"[ERROR] {error_msg}")
                print(f"  Please check your RAPIDAPI_KEY")
                if response.status_code == 403:
                    try:
                        error_data = response.json()
                        print(f"  Error Details: {error_data}")
                    except:
                        print(f"  Response: {response.text[:500]}")
                raise ValueError(error_msg)
            
            if response.status_code == 429:
                error_msg = "RapidAPI Rate Limit Exceeded (429)"
                print(f"[ERROR] {error_msg}")
                print(f"  You've reached the monthly limit (30 requests/month)")
                raise ValueError(error_msg)
            
            response.raise_for_status()
            data = response.json()
            
            print(f"[DEBUG] Facebook Marketplace API response type: {type(data)}")
            
            # Save full response to file for analysis
            import json
            import os
            os.makedirs('data', exist_ok=True)
            debug_file = 'data/rapidapi_fb_response.json'
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[DEBUG] Full response saved to: {debug_file}")
            
            if isinstance(data, dict):
                print(f"[DEBUG] Response keys: {list(data.keys())}")
                # Print first 1000 chars of response for debugging
                print(f"[DEBUG] Response sample: {json.dumps(data, indent=2)[:1000]}")
            elif isinstance(data, list):
                print(f"[DEBUG] Response is list with {len(data)} items")
                if len(data) > 0:
                    print(f"[DEBUG] First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
                    # Save first item structure for analysis
                    if isinstance(data[0], dict):
                        first_item_file = 'data/rapidapi_fb_first_item.json'
                        with open(first_item_file, 'w', encoding='utf-8') as f:
                            json.dump(data[0], f, indent=2, ensure_ascii=False)
                        print(f"[DEBUG] First item structure saved to: {first_item_file}")
            
            # Handle different response formats
            if isinstance(data, list):
                raw_items = data
            elif isinstance(data, dict):
                # Check for common response wrapper fields
                if "data" in data:
                    raw_items = data["data"] if isinstance(data["data"], list) else []
                elif "results" in data:
                    raw_items = data["results"] if isinstance(data["results"], list) else []
                elif "items" in data:
                    raw_items = data["items"] if isinstance(data["items"], list) else []
                elif "marketplace_listings" in data:
                    raw_items = data["marketplace_listings"] if isinstance(data["marketplace_listings"], list) else []
                else:
                    # If it's a dict but no wrapper, might be a single item or different structure
                    raw_items = [data] if data else []
                    print(f"[DEBUG] No recognized wrapper field found, treating as single item or empty")
            else:
                raw_items = []
            
            print(f"[DEBUG] Extracted {len(raw_items)} raw items from response")
            
            # Normalize each item
            normalization_errors = 0
            for idx, raw_item in enumerate(raw_items):
                try:
                    # Debug: show raw item structure for first item and save to file
                    if idx == 0 and isinstance(raw_item, dict):
                        print(f"[DEBUG] First raw item structure:")
                        print(f"  Keys: {list(raw_item.keys())}")
                        print(f"  Sample values: {[(k, str(v)[:50]) for k, v in list(raw_item.items())[:5]]}")
                        # Save first raw item for detailed analysis
                        import json
                        import os
                        os.makedirs('data', exist_ok=True)
                        raw_item_file = 'data/rapidapi_fb_raw_item.json'
                        with open(raw_item_file, 'w', encoding='utf-8') as f:
                            json.dump(raw_item, f, indent=2, ensure_ascii=False)
                        print(f"[DEBUG] First raw item saved to: {raw_item_file}")
                    
                    normalized = normalize_facebook_item(raw_item)
                    
                    # Be more lenient - only require title, item_id can be generated
                    if normalized["title"]:
                        # If no item_id, try to extract from URL first
                        if not normalized["item_id"]:
                            # Try to extract from URL if available
                            url = normalized.get("url", "")
                            if url and "item/" in url:
                                item_id_from_url = url.split("item/")[-1].split("/")[0].split("?")[0]
                                if item_id_from_url:
                                    normalized["item_id"] = item_id_from_url
                        
                        # If still no URL, try to construct from item_id (but only if it's a real ID)
                        if not normalized.get("url") and normalized.get("item_id"):
                            # Only construct URL if item_id looks like a real Facebook ID (not our generated format)
                            if not normalized["item_id"].startswith("fb_"):
                                normalized["url"] = f"https://www.facebook.com/marketplace/item/{normalized['item_id']}"
                        
                        # Fallback: generate item_id only if we still don't have one (for tracking purposes)
                        if not normalized["item_id"]:
                            normalized["item_id"] = f"fb_{idx}_{hash(normalized['title'])}"
                        
                        items.append(normalized)
                    else:
                        print(f"[DEBUG] Item {idx} skipped: missing title")
                        print(f"  Available keys: {list(raw_item.keys()) if isinstance(raw_item, dict) else 'Not a dict'}")
                except Exception as e:
                    normalization_errors += 1
                    print(f"[DEBUG] Failed to normalize Facebook item {idx}: {e}")
                    if idx < 2:  # Show first 2 errors in detail
                        import traceback
                        traceback.print_exc()
                    continue
            
            print(f"[DEBUG] Facebook Marketplace Summary:")
            print(f"  Raw items received: {len(raw_items)}")
            print(f"  Successfully normalized: {len(items)}")
            print(f"  Normalization errors: {normalization_errors}")
            
            # Record API usage
            record_request(query, len(items))
            
            break  # Success, exit retry loop
            
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code in (429, 500, 502, 503, 504):
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    print(f"Rate limit or server error, retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
            raise
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 5
                print(f"Request timeout, retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + (0.1 * attempt)
                time.sleep(wait_time)
                continue
            raise
    
    return items

