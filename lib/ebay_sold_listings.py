"""
eBay Sold Listings Search
Search for sold/completed listings to get market reference prices.
Note: eBay Browse API doesn't directly support sold listings.
This module uses active listings as a proxy, or can be extended for Marketplace Insights API.
"""
import time
from typing import TypedDict, Optional
import requests
from lib.ebay_oauth import get_oauth_token


class SoldListingResult(TypedDict):
    average_price: Optional[float]
    min_price: Optional[float]
    max_price: Optional[float]
    median_price: Optional[float]
    count: int
    listings: list[dict]


def _save_token_to_env_local(token: str):
    """Save token to .env.local file"""
    import os
    env_local_path = ".env.local"
    
    # Read existing .env.local if it exists
    env_vars = {}
    if os.path.exists(env_local_path):
        with open(env_local_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Update EBAY_OAUTH
    env_vars['EBAY_OAUTH'] = token
    
    # Write back to file
    with open(env_local_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")


def search_sold_listings(
    query: str,
    env: dict[str, str],
    limit: int = 50,
    category_ids: Optional[str] = None
) -> SoldListingResult:
    """
    Search eBay for sold/completed listings to get market reference prices.
    
    Note: eBay Browse API doesn't directly support sold listings without Marketplace Insights API approval.
    This function uses active listings as a proxy for market prices.
    
    Args:
        query: Search query string
        env: Environment variables dict with EBAY_OAUTH (or EBAY_CLIENT_ID/SECRET for auto-refresh)
        limit: Maximum number of items to return
        category_ids: Optional category ID filter (comma-separated)
    
    Returns:
        SoldListingResult with price statistics and listings
    """
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    
    # Get or automatically generate token
    oauth_token = env.get('EBAY_OAUTH', '')
    
    # If we have Client ID and Secret, always generate a fresh token
    if env.get('EBAY_CLIENT_ID') and env.get('EBAY_CLIENT_SECRET'):
        new_token = get_oauth_token(
            client_id=env.get('EBAY_CLIENT_ID'),
            client_secret=env.get('EBAY_CLIENT_SECRET'),
            environment='production'
        )
        if new_token:
            oauth_token = new_token
            env['EBAY_OAUTH'] = new_token
            _save_token_to_env_local(new_token)
            print(f"[INFO] ✅ Auto-generated and saved fresh eBay OAuth token")
        elif not oauth_token:
            raise ValueError("Unable to generate eBay OAuth token")
    elif not oauth_token:
        raise ValueError("EBAY_OAUTH not found. Please set EBAY_OAUTH or add EBAY_CLIENT_ID/SECRET")
    
    headers = {"Authorization": f"Bearer {oauth_token}"}
    
    params = {
        "q": query,
        "limit": str(min(limit, 200)),  # eBay API max is 200
        "filter": "buyingOptions:{FIXED_PRICE}",  # Only Buy It Now items
    }
    
    if category_ids:
        params["category_ids"] = category_ids
    
    listings = []
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 401:
                # Token expired - automatically refresh if we have credentials
                if env.get('EBAY_CLIENT_ID') and env.get('EBAY_CLIENT_SECRET') and attempt == 0:
                    print(f"[INFO] Token expired (401), auto-refreshing...")
                    new_token = get_oauth_token(
                        client_id=env.get('EBAY_CLIENT_ID'),
                        client_secret=env.get('EBAY_CLIENT_SECRET'),
                        environment='production'
                    )
                    if new_token:
                        headers["Authorization"] = f"Bearer {new_token}"
                        oauth_token = new_token
                        env['EBAY_OAUTH'] = new_token
                        _save_token_to_env_local(new_token)
                        response = requests.get(url, headers=headers, params=params, timeout=30)
                        if response.status_code == 200:
                            print(f"[INFO] ✅ Token auto-refreshed")
                        else:
                            response.raise_for_status()
                    else:
                        response.raise_for_status()
                else:
                    print(f"eBay API Authentication Error (401)")
                    response.raise_for_status()
            
            response.raise_for_status()
            data = response.json()
            
            for summary in data.get("itemSummaries", []):
                price_obj = summary.get("price", {})
                if price_obj.get("currency") != "USD":
                    continue
                
                price = float(price_obj.get("value", 0))
                if price <= 0:
                    continue
                
                # Extract shipping cost
                shipping = 0.0
                shipping_options = summary.get("shippingOptions", [])
                if shipping_options:
                    first_option = shipping_options[0]
                    shipping_cost = first_option.get("shippingCost", {})
                    shipping = float(shipping_cost.get("value", 0))
                
                listing = {
                    "item_id": summary.get("itemId", ""),
                    "title": summary.get("title", ""),
                    "price": price,
                    "shipping": shipping,
                    "total_cost": price + shipping,
                    "url": summary.get("itemWebUrl", ""),
                }
                listings.append(listing)
            
            break  # Success, exit retry loop
            
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code in (429, 500, 502, 503, 504):
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    time.sleep(wait_time)
                    continue
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + (0.1 * attempt)
                time.sleep(wait_time)
                continue
            raise
    
    # Calculate statistics
    if not listings:
        return {
            "average_price": None,
            "min_price": None,
            "max_price": None,
            "median_price": None,
            "count": 0,
            "listings": []
        }
    
    prices = [listing["total_cost"] for listing in listings]
    prices_sorted = sorted(prices)
    
    average_price = sum(prices) / len(prices)
    min_price = min(prices)
    max_price = max(prices)
    
    # Calculate median
    n = len(prices_sorted)
    if n % 2 == 0:
        median_price = (prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2
    else:
        median_price = prices_sorted[n // 2]
    
    return {
        "average_price": average_price,
        "min_price": min_price,
        "max_price": max_price,
        "median_price": median_price,
        "count": len(listings),
        "listings": listings
    }


def get_market_price_from_sold_listings(
    watch_info: dict,
    env: dict[str, str],
    limit: int = 50
) -> Optional[float]:
    """
    Get market reference price for a watch by searching sold listings.
    
    Args:
        watch_info: Dictionary with watch metadata (brand, model, etc.)
        env: Environment variables dict
        limit: Maximum number of listings to search
    
    Returns:
        Average market price, or None if not found
    """
    # Build search query from watch info
    query_parts = []
    
    if watch_info.get("brand"):
        query_parts.append(watch_info["brand"])
    
    if watch_info.get("model"):
        query_parts.append(watch_info["model"])
    elif watch_info.get("model_number"):
        query_parts.append(watch_info["model_number"])
    
    if not query_parts:
        # Fallback to title if available
        if watch_info.get("title"):
            query = watch_info["title"]
        else:
            return None
    else:
        query = " ".join(query_parts)
    
    # Search for similar watches
    result = search_sold_listings(
        query=query,
        env=env,
        limit=limit,
        category_ids="260324"  # Watches category
    )
    
    # Return average price if available
    return result.get("average_price")

