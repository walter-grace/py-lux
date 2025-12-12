"""
Shared eBay API functions for trading cards and luxury items
"""
import time
import os
import re
from typing import TypedDict, Optional
import requests
from lib.ebay_oauth import get_oauth_token


class EbayItem(TypedDict):
    item_id: str
    title: str
    url: str
    price: float
    shipping: float
    currency: str
    aspects: dict
    cert: Optional[str]
    card_name: Optional[str]
    year: Optional[str]
    set_name: Optional[str]
    seller_username: Optional[str]
    item_condition: Optional[str]
    image_url: Optional[str]


def search_trading_cards(
    limit: int,
    env: dict[str, str],
    year: Optional[str] = None,
    game: str = "yugioh"
) -> list[EbayItem]:
    """
    Search eBay for PSA 10 trading cards (Yu-Gi-Oh! or Pokemon).
    
    Args:
        limit: Maximum number of items to return
        env: Environment variables dict with EBAY_OAUTH
        year: Optional year filter
        game: "yugioh" or "pokemon"
    
    Returns:
        List of EbayItem dictionaries
    """
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {"Authorization": f"Bearer {env['EBAY_OAUTH']}"}

    # Build query
    query_base = f"{game} PSA 10 1st edition"
    query = f"{query_base} {year}" if year else query_base

    if game == "pokemon" and not year:
        query = "pokemon PSA 10 1st edition 1999"

    params = {
        "q": query,
        "category_ids": "183454",
        "limit": str(limit),
        "filter": "sellers:{psa},buyingOptions:{FIXED_PRICE}",
        "aspect_filter": (
            f"categoryId:183454,"
            f"Game:{'Yu-Gi-Oh! TCG' if game == 'yugioh' else 'Pokémon TCG (Wizards of the Coast)'};"
            f"Professional Grader:Professional Sports Authenticator (PSA);"
            f"Grade:10;"
            f"Edition:1st Edition"
        ),
    }

    items: list[EbayItem] = []
    seen_ids: set[str] = set()

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 401:
                print(f"eBay API Authentication Error (401):")
                print(f"  Please regenerate your eBay User Access Token at:")
                print(f"  https://developer.ebay.com/my/keys")
                response.raise_for_status()

            response.raise_for_status()
            data = response.json()

            for summary in data.get("itemSummaries", []):
                item_id = summary.get("itemId", "")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                price_obj = summary.get("price", {})
                price = float(price_obj.get("value", 0))
                currency = price_obj.get("currency", "")

                if currency != "USD":
                    continue

                shipping = 0.0
                shipping_options = summary.get("shippingOptions", [])
                if shipping_options:
                    first_option = shipping_options[0]
                    shipping_cost = first_option.get("shippingCost", {})
                    shipping = float(shipping_cost.get("value", 0))

                # Check for 1st Edition in summary
                title_lower = summary.get("title", "").lower()
                is_1st_edition = "1st" in title_lower or "first edition" in title_lower

                if not is_1st_edition:
                    continue

                # Fetch full item details
                cert_number = None
                card_name = None
                year_extracted = None
                set_name = None
                seller_username = None
                item_condition = None
                image_url = None

                try:
                    item_url = summary.get("itemHref", "")
                    if item_url:
                        item_response = requests.get(item_url, headers=headers, timeout=30)
                        if item_response.status_code == 200:
                            item_data = item_response.json()

                            image_url = item_data.get("image", {}).get("imageUrl")

                            # Extract metadata
                            for aspect in item_data.get("localizedAspects", []):
                                name = aspect.get("name", "")
                                value = aspect.get("value", "")
                                if "card name" in name.lower():
                                    card_name = value if isinstance(value, str) else (value[0] if isinstance(value, list) and value else None)
                                elif "year" in name.lower():
                                    year_extracted = value if isinstance(value, str) else (value[0] if isinstance(value, list) and value else None)
                                elif "set" in name.lower():
                                    set_name = value if isinstance(value, str) else (value[0] if isinstance(value, list) and value else None)

                            # Get cert number
                            for descriptor in item_data.get("conditionDescriptors", []):
                                name = descriptor.get("name", "")
                                values = descriptor.get("values", [])
                                if "certification" in name.lower() or "cert" in name.lower():
                                    if values:
                                        cert_value = values[0].get("content", "") if isinstance(values[0], dict) else str(values[0])
                                        if cert_value:
                                            cert_number = cert_value

                            seller = item_data.get("seller", {})
                            seller_username = seller.get("username")
                            item_condition = item_data.get("condition", "")

                except Exception:
                    pass

                item: EbayItem = {
                    "item_id": item_id,
                    "title": summary.get("title", ""),
                    "url": summary.get("itemWebUrl", ""),
                    "price": price,
                    "shipping": shipping,
                    "currency": currency,
                    "aspects": {},
                    "cert": cert_number,
                    "card_name": card_name,
                    "year": year_extracted,
                    "set_name": set_name,
                    "seller_username": seller_username,
                    "item_condition": item_condition,
                    "image_url": image_url,
                }
                items.append(item)

            break

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

    return items


def _save_token_to_env_local(token: str) -> None:
    """
    Automatically save eBay OAuth token to .env.local file.
    
    Args:
        token: The OAuth token to save
    """
    env_path = ".env.local"
    
    # Ensure the file exists
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write("")
    
    # Read existing content
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
    except Exception:
        lines = []
    
    # Update or add token
    updated_lines = []
    token_found = False
    
    for line in lines:
        if line.startswith("EBAY_OAUTH="):
            updated_lines.append(f"EBAY_OAUTH={token}\n")
            token_found = True
        else:
            updated_lines.append(line)
    
    if not token_found:
        updated_lines.append(f"\nEBAY_OAUTH={token}\n")
    
    # Write back to file
    try:
        with open(env_path, "w") as f:
            f.writelines(updated_lines)
    except Exception as e:
        print(f"[WARNING] Could not save token to .env.local: {e}")
        print(f"[WARNING] Token will work for this session but may need to be regenerated next time")


def get_ebay_item_details(item_id: str, env: dict[str, str]) -> Optional[dict]:
    """
    Get full item details from eBay API to extract cert numbers and other metadata.
    
    Args:
        item_id: eBay item ID
        env: Environment variables dict with EBAY_OAUTH
        
    Returns:
        Dictionary with item details or None if failed
    """
    oauth_token = env.get('EBAY_OAUTH', '')
    
    if not oauth_token:
        if env.get('EBAY_CLIENT_ID') and env.get('EBAY_CLIENT_SECRET'):
            oauth_token = get_oauth_token(
                client_id=env.get('EBAY_CLIENT_ID'),
                client_secret=env.get('EBAY_CLIENT_SECRET'),
                environment='production'
            )
            if oauth_token:
                env['EBAY_OAUTH'] = oauth_token
        else:
            return None
    
    url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"
    headers = {"Authorization": f"Bearer {oauth_token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def search_ebay_generic(
    query: str,
    limit: int,
    env: dict[str, str],
    category_ids: Optional[str] = None,
    filters: Optional[str] = None
) -> list[EbayItem]:
    """
    Generic eBay search function for any product.
    
    Automatically refreshes OAuth token if expired or missing.
    
    Args:
        query: Search query string
        limit: Maximum number of items to return
        env: Environment variables dict with EBAY_OAUTH (or EBAY_CLIENT_ID/SECRET for auto-refresh)
        category_ids: Optional category ID filter (comma-separated)
        filters: Optional filter string (e.g., "buyingOptions:{FIXED_PRICE}")
    
    Returns:
        List of EbayItem dictionaries
    """
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    
    # Get or automatically generate token
    oauth_token = env.get('EBAY_OAUTH', '')
    
    # If we have Client ID and Secret, always generate a fresh token (no expiration issues!)
    if env.get('EBAY_CLIENT_ID') and env.get('EBAY_CLIENT_SECRET'):
        # Always generate a fresh token - no expiration worries!
        new_token = get_oauth_token(
            client_id=env.get('EBAY_CLIENT_ID'),
            client_secret=env.get('EBAY_CLIENT_SECRET'),
            environment='production'
        )
        if new_token:
            oauth_token = new_token
            # Update env dict so it's used for this session
            env['EBAY_OAUTH'] = new_token
            # Automatically save to .env.local
            _save_token_to_env_local(new_token)
            print(f"[INFO] ✅ Auto-generated and saved fresh eBay OAuth token (expires in ~2 hours)")
        elif not oauth_token:
            raise ValueError("Unable to generate eBay OAuth token. Please check EBAY_CLIENT_ID and EBAY_CLIENT_SECRET")
    elif not oauth_token:
        raise ValueError("EBAY_OAUTH not found. Please set EBAY_OAUTH or add EBAY_CLIENT_ID/SECRET for automatic token generation")
    
    headers = {"Authorization": f"Bearer {oauth_token}"}

    params = {
        "q": query,
        "limit": str(limit),
    }
    
    if category_ids:
        params["category_ids"] = category_ids
    
    if filters:
        params["filter"] = filters
    else:
        params["filter"] = "buyingOptions:{FIXED_PRICE}"  # Default to Buy It Now

    items: list[EbayItem] = []
    seen_ids: set[str] = set()

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
                        env['EBAY_OAUTH'] = new_token  # Update for future calls
                        _save_token_to_env_local(new_token)  # Save to file
                        # Retry the request with new token
                        response = requests.get(url, headers=headers, params=params, timeout=30)
                        if response.status_code == 200:
                            print(f"[INFO] ✅ Token auto-refreshed and saved successfully")
                        elif response.status_code == 401:
                            print(f"eBay API Authentication Error (401) even after refresh:")
                            print(f"  Please check your credentials")
                            response.raise_for_status()
                    else:
                        print(f"eBay API Authentication Error (401):")
                        print(f"  Auto-refresh failed. Please check EBAY_CLIENT_ID and EBAY_CLIENT_SECRET")
                        response.raise_for_status()
                else:
                    print(f"eBay API Authentication Error (401):")
                    if not (env.get('EBAY_CLIENT_ID') and env.get('EBAY_CLIENT_SECRET')):
                        print(f"  Token expired. Add EBAY_CLIENT_ID and EBAY_CLIENT_SECRET to .env.local")
                        print(f"  for automatic token refresh")
                    response.raise_for_status()

            response.raise_for_status()
            data = response.json()

            for summary in data.get("itemSummaries", []):
                item_id = summary.get("itemId", "")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                price_obj = summary.get("price", {})
                price = float(price_obj.get("value", 0))
                currency = price_obj.get("currency", "")

                if currency != "USD":
                    continue

                shipping = 0.0
                shipping_options = summary.get("shippingOptions", [])
                if shipping_options:
                    first_option = shipping_options[0]
                    shipping_cost = first_option.get("shippingCost", {})
                    shipping = float(shipping_cost.get("value", 0))

                image_url = None
                item_condition = None
                
                # Try to get image from summary
                image = summary.get("image", {})
                if image:
                    image_url = image.get("imageUrl")
                
                # Get condition from summary
                item_condition = summary.get("condition", "")
                
                # Fetch full item details to get cert number and aspects
                aspects_dict = {}
                cert_number = None
                card_name = None
                year_extracted = None
                set_name = None
                seller_username = None
                
                try:
                    item_details = get_ebay_item_details(item_id, env)
                    if item_details:
                        # Extract aspects
                        for aspect in item_details.get("localizedAspects", []):
                            aspect_name = aspect.get("name", "")
                            aspect_value = aspect.get("value", "")
                            aspects_dict[aspect_name] = aspect_value
                            
                            # Look for cert number in aspects
                            if any(keyword in aspect_name.lower() for keyword in ['cert', 'certification', 'psa']):
                                if isinstance(aspect_value, str) and re.match(r'^\d{6,9}$', aspect_value.strip()):
                                    cert_number = aspect_value.strip()
                                elif isinstance(aspect_value, list) and aspect_value:
                                    cert_val = str(aspect_value[0]).strip()
                                    if re.match(r'^\d{6,9}$', cert_val):
                                        cert_number = cert_val
                            
                            # Extract card metadata
                            if "card name" in aspect_name.lower():
                                card_name = aspect_value if isinstance(aspect_value, str) else (aspect_value[0] if isinstance(aspect_value, list) and aspect_value else None)
                            elif "year" in aspect_name.lower():
                                year_extracted = aspect_value if isinstance(aspect_value, str) else (aspect_value[0] if isinstance(aspect_value, list) and aspect_value else None)
                            elif "set" in aspect_name.lower() or "set name" in aspect_name.lower():
                                set_name = aspect_value if isinstance(aspect_value, str) else (aspect_value[0] if isinstance(aspect_value, list) and aspect_value else None)
                        
                        # Also check condition descriptors for cert
                        if not cert_number:
                            for descriptor in item_details.get("conditionDescriptors", []):
                                desc_name = descriptor.get("name", "")
                                desc_values = descriptor.get("values", [])
                                if any(keyword in desc_name.lower() for keyword in ['cert', 'certification']):
                                    if desc_values:
                                        cert_val = desc_values[0].get("content", "") if isinstance(desc_values[0], dict) else str(desc_values[0])
                                        if cert_val and re.match(r'^\d{6,9}$', str(cert_val).strip()):
                                            cert_number = str(cert_val).strip()
                        
                        # Get seller info
                        seller = item_details.get("seller", {})
                        seller_username = seller.get("username")
                        
                        # Update image if available in details
                        detail_image = item_details.get("image", {}).get("imageUrl")
                        if detail_image:
                            image_url = detail_image
                except Exception as e:
                    # Silently fail - we'll use summary data only
                    pass

                item: EbayItem = {
                    "item_id": item_id,
                    "title": summary.get("title", ""),
                    "url": summary.get("itemWebUrl", ""),
                    "price": price,
                    "shipping": shipping,
                    "currency": currency,
                    "aspects": aspects_dict,
                    "cert": cert_number,
                    "card_name": card_name,
                    "year": year_extracted,
                    "set_name": set_name,
                    "seller_username": seller_username,
                    "item_condition": item_condition,
                    "image_url": image_url,
                }
                items.append(item)

            break

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

    return items

