"""
Amazon Best Sellers API integration
Gets best-selling products from Amazon and searches for them on other platforms
"""
import requests
import time
from typing import Optional
from lib.rapidapi_usage_tracker import record_request


def get_amazon_best_sellers(
    category: str,
    env: dict[str, str],
    country: str = "us",
    page: int = 1,
    max_items: int = 50
) -> list[dict]:
    """
    Get Amazon best sellers for a given category.
    
    Args:
        category: Category name (e.g., "shoes", "electronics", "fashion", "mobile-apps")
        env: Environment variables dict with RAPIDAPI_KEY
        country: Country code (default: "us")
        page: Page number (default: 1)
        max_items: Maximum number of items to return
        
    Returns:
        List of best seller product dictionaries
    """
    api_key = env.get("RAPIDAPI_KEY")
    
    if not api_key:
        raise ValueError("RAPIDAPI_KEY not found in environment")
    
    # Real-Time Amazon Data API v3 - Best Sellers endpoint
    url = "https://real-time-amazon-data.p.rapidapi.com/best-sellers"
    headers = {
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    
    params = {
        "category": category,
        "country": country.upper(),  # v3 expects uppercase country codes
        "page": str(page),
    }
    
    items = []
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] Amazon Best Sellers v3 Request:")
            print(f"  URL: {url}")
            print(f"  Category: {category}")
            print(f"  Params: {params}")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            print(f"[DEBUG] Amazon Best Sellers v3 Response:")
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 401 or response.status_code == 403:
                error_msg = f"RapidAPI Authentication Error ({response.status_code})"
                print(f"[ERROR] {error_msg}")
                response.raise_for_status()
            
            if response.status_code == 429:
                error_msg = "RapidAPI Rate Limit Exceeded (429)"
                print(f"[ERROR] {error_msg}")
                raise ValueError(error_msg)
            
            response.raise_for_status()
            data = response.json()
            
            # Save response for debugging
            import json
            import os
            os.makedirs('data', exist_ok=True)
            debug_file = f'data/amazon_best_sellers_v3_{category}.json'
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[DEBUG] Response saved to: {debug_file}")
            
            # v3 API structure: {"status": "OK", "data": {"best_sellers": [...]}}
            raw_items = []
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], dict):
                    # v3 uses "best_sellers" array inside "data"
                    if "best_sellers" in data["data"]:
                        raw_items = data["data"]["best_sellers"] if isinstance(data["data"]["best_sellers"], list) else []
                    elif "products" in data["data"]:
                        raw_items = data["data"]["products"] if isinstance(data["data"]["products"], list) else []
                elif "products" in data:
                    raw_items = data["products"] if isinstance(data["products"], list) else []
                elif "best_sellers" in data:
                    raw_items = data["best_sellers"] if isinstance(data["best_sellers"], list) else []
            
            print(f"[DEBUG] Extracted {len(raw_items)} best seller items")
            
            # Normalize best-sellers format to match our product structure
            # v3 uses snake_case: product_title, product_price, product_photo, product_url
            for raw_item in raw_items[:max_items]:
                normalized = {
                    "asin": raw_item.get("asin", ""),
                    "title": (
                        raw_item.get("product_title", "") or 
                        raw_item.get("title", "") or
                        raw_item.get("ProductTitle", "")
                    ),
                    "price": _parse_price(
                        raw_item.get("product_price", "") or 
                        raw_item.get("price", "")
                    ),
                    "url": (
                        raw_item.get("product_url", "") or 
                        raw_item.get("productUrl", "") or 
                        raw_item.get("link", "") or 
                        f"https://www.amazon.com/dp/{raw_item.get('asin', '')}"
                    ),
                    "image_url": (
                        raw_item.get("product_photo", "") or 
                        raw_item.get("product_photo", "") or
                        raw_item.get("imageUrl", "") or
                        raw_item.get("image", "")
                    ),
                    "rating": _parse_rating(
                        raw_item.get("product_star_rating", "") or 
                        raw_item.get("rating", "") or
                        raw_item.get("star_rating", "")
                    ),
                    "rank": raw_item.get("rank", ""),
                    "category": category,
                }
                if normalized["asin"] and normalized["title"]:
                    items.append(normalized)
            
            print(f"[DEBUG] Normalized {len(items)} best seller items")
            
            # Record API usage
            record_request(f"amazon_best_sellers:{category}", len(items))
            
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
                print(f"Timeout, retrying...")
                time.sleep(2)
                continue
            raise
        except Exception as e:
            print(f"Error getting Amazon best sellers: {e}")
            raise
    
    return items


def _parse_price(price_str: str) -> float:
    """Parse price string to float (e.g., "$99.95" -> 99.95)"""
    if not price_str:
        return 0.0
    
    import re
    price_match = re.search(r'[\d,]+\.?\d*', str(price_str).replace(',', ''))
    if price_match:
        try:
            return float(price_match.group().replace(',', ''))
        except ValueError:
            pass
    return 0.0


def _parse_rating(rating_str: str) -> Optional[float]:
    """Parse rating string to float (e.g., "4.5" -> 4.5)"""
    if not rating_str or "No rating" in str(rating_str):
        return None
    
    try:
        return float(str(rating_str))
    except (ValueError, TypeError):
        return None


def get_available_categories() -> list[str]:
    """
    Get list of available Amazon best-seller categories.
    These are categories that have been tested and confirmed to work with the API.
    
    Note: Some categories like "toys-games", "sports-outdoors", "computers", etc.
    return empty results and have been removed from this list.
    """
    return [
        "electronics",
        "fashion",
        "mobile-apps",
        "books",
        "home-garden",
        "beauty",
        "automotive",
        "kitchen",
        "pet-supplies",
        "musical-instruments",
        "office-products",
    ]

