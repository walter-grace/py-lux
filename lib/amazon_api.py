"""
Amazon API integration using RapidAPI Real-Time Amazon Data API v3
More robust API with better endpoints and data structure
"""
import time
import re
from typing import TypedDict, Optional
import requests
import urllib.parse
import json

# Import usage tracker
try:
    from lib.rapidapi_usage_tracker import record_request, print_usage_stats
except ImportError:
    def record_request(*args, **kwargs):
        pass
    def print_usage_stats():
        pass


class AmazonItem(TypedDict):
    item_id: str  # ASIN
    title: str
    url: str
    price: float
    shipping: float
    currency: str
    condition: Optional[str]
    image_url: Optional[str]
    description: Optional[str]
    # Additional fields for matching
    brand: Optional[str]
    product_name: Optional[str]
    size: Optional[str]
    # For trading cards
    cert: Optional[str]
    card_name: Optional[str]
    year: Optional[str]
    set_name: Optional[str]
    # Amazon-specific
    asin: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    prime_eligible: Optional[bool]


def normalize_amazon_item(item_data: dict) -> AmazonItem:
    """
    Normalize RapidAPI Amazon response to our standard format.
    
    Args:
        item_data: Raw item data from RapidAPI (from "details" array)
        
    Returns:
        Normalized AmazonItem
    """
    # Extract ASIN (Amazon Standard Identification Number)
    asin = item_data.get("asin", "") or item_data.get("ASIN", "") or item_data.get("id", "")
    item_id = asin  # Use ASIN as item_id
    
    # Extract title - v3 API uses "product_title" (snake_case)
    title = (
        item_data.get("product_title", "") or 
        item_data.get("ProductTitle", "") or 
        item_data.get("title", "") or 
        item_data.get("productTitle", "") or 
        item_data.get("name", "")
    )
    
    # Extract price - v3 API uses "product_price" as string like "$99.95"
    price = 0.0
    currency = item_data.get("currency", "USD") or "USD"
    
    # Try different price fields (v3 uses "product_price" in snake_case)
    price_fields = [
        "product_price",  # v3 primary field
        "product_minimum_offer_price",  # v3 alternative
        "price", 
        "currentPrice", 
        "priceAmount", 
        "listPrice", 
        "salePrice"
    ]
    for field in price_fields:
        price_val = item_data.get(field)
        if price_val:
            if isinstance(price_val, (int, float)):
                price = float(price_val)
                break
            elif isinstance(price_val, dict):
                # Price might be in a dict like {"amount": 99.99, "currency": "USD"}
                if "amount" in price_val:
                    try:
                        price = float(price_val["amount"])
                        currency = price_val.get("currency", currency)
                        break
                    except (ValueError, TypeError):
                        pass
            elif isinstance(price_val, str):
                # Extract number from string like "$99.95" or "$1,234.56"
                price_match = re.search(r'[\d,]+\.?\d*', price_val.replace(',', ''))
                if price_match:
                    try:
                        price = float(price_match.group().replace(',', ''))
                        break
                    except ValueError:
                        pass
    
    # Construct URL - v3 API might use "product_url" or "url"
    url = (
        item_data.get("product_url", "") or 
        item_data.get("productUrl", "") or 
        item_data.get("url", "") or 
        (f"https://www.amazon.com/dp/{asin}" if asin else "")
    )
    
    # Extract condition - Amazon items are typically "New" unless specified
    condition = item_data.get("condition", "") or item_data.get("itemCondition", "") or "New"
    
    # Extract images - v3 API uses "product_photo" (snake_case)
    image_url = (
        item_data.get("product_photo", "") or 
        item_data.get("product_image", "") or 
        item_data.get("productImage", "") or 
        item_data.get("image", "") or 
        item_data.get("mainImage", "") or
        item_data.get("main_image", "")
    )
    
    # Fallback to other image fields if productImage not found
    if not image_url:
        image_fields = ["thumbnail", "images"]
        for field in image_fields:
            img_val = item_data.get(field)
            if img_val:
                if isinstance(img_val, str):
                    image_url = img_val
                    break
                elif isinstance(img_val, dict):
                    image_url = img_val.get("url", "") or img_val.get("uri", "")
                    if image_url:
                        break
                elif isinstance(img_val, list) and len(img_val) > 0:
                    if isinstance(img_val[0], str):
                        image_url = img_val[0]
                        break
                    elif isinstance(img_val[0], dict):
                        image_url = img_val[0].get("url", "") or img_val[0].get("uri", "")
                        if image_url:
                            break
    
    # Extract description
    description = item_data.get("description", "") or item_data.get("productDescription", "")
    
    # Extract brand
    brand = item_data.get("brand", "") or item_data.get("manufacturer", "")
    
    # Extract rating - v3 API uses "product_star_rating" as string like "4.7"
    rating = None
    rating_val = (
        item_data.get("product_star_rating", "") or 
        item_data.get("rating", "") or 
        item_data.get("averageRating", "") or
        item_data.get("star_rating", "")
    )
    if rating_val:
        try:
            rating = float(str(rating_val))
        except (ValueError, TypeError):
            pass
    
    # Extract review count - v3 API uses "product_num_ratings"
    review_count = None
    review_count_val = (
        item_data.get("product_num_ratings", "") or 
        item_data.get("totalRatings", "") or 
        item_data.get("reviewCount", "") or 
        item_data.get("reviewsCount", "") or 
        item_data.get("numberOfReviews", "") or
        item_data.get("num_ratings", "")
    )
    if review_count_val:
        try:
            review_count = int(review_count_val)
        except (ValueError, TypeError):
            pass
    
    # Prime eligible - v3 API uses "is_prime" as boolean
    prime_eligible = False
    prime_val = (
        item_data.get("is_prime") or 
        item_data.get("isPrime") or 
        item_data.get("prime")
    )
    if isinstance(prime_val, bool):
        prime_eligible = prime_val
    elif isinstance(prime_val, str):
        prime_eligible = prime_val.lower() in ("true", "yes", "1")
    
    # Try to extract size, product name, etc. from title/description for luxury items
    size = None
    product_name = None
    
    # Try to extract cert number for trading cards
    cert = None
    card_name = None
    year = None
    set_name = None
    
    # Extract size from title (e.g., "Size 7.5", "7.5", "Size 8")
    size_pattern = r'\b(size|sz)[\s:]*(\d+(?:\.\d+)?)|\b(\d+(?:\.\d+)?)\s*(?:us|eu|uk)?\s*(?:size|sz)'
    size_match = re.search(size_pattern, title.lower(), re.IGNORECASE)
    if size_match:
        size = size_match.group(2) or size_match.group(3)
    
    # Extract cert number (PSA cert format)
    cert_pattern = r'\b(?:psa|cert)[\s#:]*(\d{6,8})\b'
    cert_match = re.search(cert_pattern, title.lower() + " " + (description or "").lower(), re.IGNORECASE)
    if cert_match:
        cert = cert_match.group(1)
    
    return AmazonItem(
        item_id=item_id or "",
        title=title or "",
        url=url,
        price=price,
        shipping=0.0,  # Amazon Prime items typically have free shipping
        currency=currency,
        condition=condition,
        image_url=image_url,
        description=description,
        brand=brand,
        product_name=product_name,
        size=size,
        cert=cert,
        card_name=card_name,
        year=year,
        set_name=set_name,
        asin=asin,
        rating=rating,
        review_count=review_count,
        prime_eligible=prime_eligible
    )


def search_amazon_products(
    query: str,
    max_items: int,
    env: dict[str, str],
    country: str = "us",
    page: int = 1,
    sort: str = "Featured"
) -> list[AmazonItem]:
    """
    Search Amazon products using RapidAPI.
    
    ⚠️  NOTE: The exact search endpoint may vary - this is a template that can be updated
    once we confirm the correct endpoint path from RapidAPI documentation.
    
    Args:
        query: Search query string
        max_items: Maximum number of items to return
        env: Environment variables dict with RAPIDAPI_KEY
        country: Country code (default: "us")
        page: Page number (default: 1)
        
    Returns:
        List of normalized AmazonItem dictionaries
    """
    api_key = env.get("RAPIDAPI_KEY")
    
    if not api_key:
        raise ValueError("RAPIDAPI_KEY not found in environment")
    
    # Real-Time Amazon Data API v3 - Search endpoint
    # Working endpoint: /search (not /product-search)
    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    
    # Map sort options to v3 format
    sort_map = {
        "Featured": "RELEVANCE",
        "Price: Low to High": "PRICE_LOW_TO_HIGH",
        "Price: High to Low": "PRICE_HIGH_TO_LOW",
        "Newest": "NEWEST",
        "Customer Rating": "CUSTOMER_RATING",
    }
    v3_sort = sort_map.get(sort, "RELEVANCE")
    
    params = {
        "query": query,  # v3 uses "query" parameter
        "country": country.upper(),  # v3 expects uppercase country codes (US, UK, etc.)
        "page": str(page),
        "sort_by": v3_sort,  # v3 uses "sort_by" with specific values
    }
    
    items = []
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] Amazon API v3 Request:")
            print(f"  URL: {url}")
            print(f"  Query: {query}")
            print(f"  Params: {params}")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            print(f"[DEBUG] Amazon API v3 Response:")
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 401 or response.status_code == 403:
                error_msg = f"RapidAPI Authentication Error ({response.status_code})"
                print(f"[ERROR] {error_msg}")
                print(f"  Please check your RAPIDAPI_KEY")
                response.raise_for_status()
            
            if response.status_code == 429:
                error_msg = "RapidAPI Rate Limit Exceeded (429)"
                print(f"[ERROR] {error_msg}")
                raise ValueError(error_msg)
            
            response.raise_for_status()
            data = response.json()
            
            # Save full response for debugging
            import os
            os.makedirs('data', exist_ok=True)
            debug_file = 'data/amazon_v3_response.json'
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[DEBUG] Full response saved to: {debug_file}")
            
            print(f"[DEBUG] Amazon API v3 response type: {type(data)}")
            if isinstance(data, dict):
                print(f"[DEBUG] Response keys: {list(data.keys())}")
                print(f"[DEBUG] Response sample: {json.dumps(data, indent=2)[:1000]}")
            elif isinstance(data, list):
                print(f"[DEBUG] Response is list with {len(data)} items")
                if len(data) > 0 and isinstance(data[0], dict):
                    print(f"[DEBUG] First item keys: {list(data[0].keys())}")
            
            # Handle Amazon API v3 response format
            # v3 response structure: {"status": "OK", "data": {"products": [...]}}
            if isinstance(data, list):
                raw_items = data
            elif isinstance(data, dict):
                # v3 API structure: data.data.products
                if "data" in data and isinstance(data["data"], dict):
                    if "products" in data["data"]:
                        raw_items = data["data"]["products"] if isinstance(data["data"]["products"], list) else []
                    else:
                        raw_items = []
                elif "products" in data:
                    raw_items = data["products"] if isinstance(data["products"], list) else []
                elif "data" in data:
                    raw_items = data["data"] if isinstance(data["data"], list) else []
                elif "results" in data:
                    raw_items = data["results"] if isinstance(data["results"], list) else []
                elif "items" in data:
                    raw_items = data["items"] if isinstance(data["items"], list) else []
                elif "details" in data:
                    raw_items = data["details"] if isinstance(data["details"], list) else []
                else:
                    # If it's a dict but no wrapper, might be a single item or different structure
                    raw_items = [data] if data else []
                    print(f"[DEBUG] No recognized wrapper field found, treating as single item or empty")
            else:
                raw_items = []
            
            print(f"[DEBUG] Extracted {len(raw_items)} raw items from response")
            
            # Normalize each item
            normalization_errors = 0
            for idx, raw_item in enumerate(raw_items[:max_items]):
                try:
                    # Debug first item structure
                    if idx == 0 and isinstance(raw_item, dict):
                        print(f"[DEBUG] First raw item structure:")
                        print(f"  Keys: {list(raw_item.keys())}")
                        # Save first item for analysis
                        first_item_file = 'data/amazon_v3_first_item.json'
                        with open(first_item_file, 'w', encoding='utf-8') as f:
                            json.dump(raw_item, f, indent=2, ensure_ascii=False)
                        print(f"[DEBUG] First item saved to: {first_item_file}")
                    
                    normalized = normalize_amazon_item(raw_item)
                    if normalized["item_id"] and normalized["title"]:
                        items.append(normalized)
                    else:
                        print(f"[DEBUG] Item {idx} skipped: missing item_id or title")
                except Exception as e:
                    normalization_errors += 1
                    print(f"[DEBUG] Failed to normalize Amazon item {idx}: {e}")
                    if idx < 2:  # Show first 2 errors in detail
                        import traceback
                        traceback.print_exc()
                    continue
            
            print(f"[DEBUG] Amazon v3 Summary:")
            print(f"  Raw items received: {len(raw_items)}")
            print(f"  Successfully normalized: {len(items)}")
            print(f"  Normalization errors: {normalization_errors}")
            
            # Record API usage
            record_request(f"amazon_search:{query}", len(items))
            
            break  # Success, exit retry loop
            
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code in (429, 500, 502, 503, 504):
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    print(f"Rate limit or server error, retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
            # If it's a 404, the endpoint might not exist
            if e.response and e.response.status_code == 404:
                print(f"⚠️  Warning: Amazon search endpoint returned 404. The endpoint path may need to be updated.")
                print(f"   Response: {e.response.text[:200]}")
            raise
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"Timeout, retrying...")
                time.sleep(2)
                continue
            raise
        except Exception as e:
            print(f"Error searching Amazon: {e}")
            raise
    
    return items


def get_amazon_product_by_asin(
    asin: str,
    env: dict[str, str],
    country: str = "us"
) -> Optional[AmazonItem]:
    """
    Get Amazon product details by ASIN.
    
    Args:
        asin: Amazon ASIN
        env: Environment variables dict with RAPIDAPI_KEY
        country: Country code (default: "us")
        
    Returns:
        Normalized AmazonItem or None if not found
    """
    api_key = env.get("RAPIDAPI_KEY")
    
    if not api_key:
        raise ValueError("RAPIDAPI_KEY not found in environment")
    
    # Real-Time Amazon Data API v3 - Product Details endpoint
    # Try different endpoint variations for v3
    endpoints_to_try = [
        f"/product-details?asin={asin}&country={country.upper()}",
        f"/product?asin={asin}&country={country.upper()}",
        f"/products/{asin}?country={country.upper()}",
    ]
    
    headers = {
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    
    for endpoint in endpoints_to_try:
        url = f"https://real-time-amazon-data.p.rapidapi.com{endpoint}"
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                normalized = normalize_amazon_item(data)
                record_request(f"amazon_product:{asin}", 1)
                return normalized
            elif response.status_code == 404:
                continue  # Try next endpoint
        except Exception as e:
            continue  # Try next endpoint
    
    return None

