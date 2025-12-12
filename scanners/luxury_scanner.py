#!/usr/bin/env python3
"""
Luxury Items eBay Arbitrage Scanner
Scans eBay for luxury items (YSL boots, Saint Laurent, etc.) and identifies arbitrage opportunities
by comparing eBay prices to retail/MSRP values.
"""

import os
import sys
import csv
import time
import re
import json
from typing import TypedDict, Optional
from dotenv import load_dotenv
from tabulate import tabulate
import requests
import cloudscraper
from bs4 import BeautifulSoup


class LuxuryItem(TypedDict):
    item_id: str
    title: str
    url: str
    price: float
    shipping: float
    currency: str
    brand: Optional[str]
    product_name: Optional[str]
    condition: Optional[str]
    image_url: Optional[str]


import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.config import load_env
from lib.facebook_marketplace_api import search_facebook_marketplace
from lib.arbitrage_comparison import compare_ebay_facebook, calculate_cross_platform_spread
from lib.targeted_fb_search import build_targeted_fb_query, get_price_range_from_ebay_items


def search_luxury_items(
    search_query: str,
    limit: int,
    env: dict[str, str],
    brand_filter: Optional[str] = None
) -> list[LuxuryItem]:
    """
    Search eBay for luxury items.
    
    Args:
        search_query: Search query (e.g., "YSL boots", "Saint Laurent boots")
        limit: Maximum number of items to return
        env: Environment variables dict with EBAY_OAUTH
        brand_filter: Optional brand to filter by
        
    Returns:
        List of LuxuryItem dictionaries
    """
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {"Authorization": f"Bearer {env['EBAY_OAUTH']}"}

    params = {
        "q": search_query,
        "category_ids": "11450",  # Clothing, Shoes & Accessories
        "limit": str(limit),
        "filter": "buyingOptions:{FIXED_PRICE}",
    }
    
    # Add brand filter if specified
    if brand_filter:
        params["aspect_filter"] = f"Brand:{brand_filter}"

    items: list[LuxuryItem] = []
    seen_ids: set[str] = set()

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 401:
                error_data = response.text
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

                # Extract price
                price_obj = summary.get("price", {})
                price = float(price_obj.get("value", 0))
                currency = price_obj.get("currency", "")

                # Skip non-USD
                if currency != "USD":
                    continue

                # Extract shipping cost
                shipping = 0.0
                shipping_options = summary.get("shippingOptions", [])
                if shipping_options:
                    first_option = shipping_options[0]
                    shipping_cost = first_option.get("shippingCost", {})
                    shipping = float(shipping_cost.get("value", 0))

                # Extract brand and product info from title/aspects
                title = summary.get("title", "")
                brand = None
                product_name = None
                condition = None
                
                # Try to extract brand from aspects
                aspects = {}
                for aspect in summary.get("localizedAspects", []):
                    name = aspect.get("name", "")
                    value = aspect.get("value", "")
                    if name and value:
                        aspects[name] = value if isinstance(value, str) else (value[0] if isinstance(value, list) else value)
                        
                        if "brand" in name.lower():
                            brand = value if isinstance(value, str) else (value[0] if isinstance(value, list) else value)
                        if "condition" in name.lower():
                            condition = value if isinstance(value, str) else (value[0] if isinstance(value, list) else value)
                
                # Fetch full item details to get condition and more metadata
                try:
                    item_url = summary.get("itemHref", "")
                    if item_url:
                        item_response = requests.get(item_url, headers=headers, timeout=30)
                        if item_response.status_code == 200:
                            item_data = item_response.json()
                            
                            # Get condition from full item data
                            if not condition:
                                condition = item_data.get("condition", "")
                            
                            # Get brand from itemSpecifics if not found
                            if not brand:
                                item_specifics = item_data.get("itemSpecifics", {})
                                for spec in item_specifics.get("nameValuePairs", []):
                                    spec_name = spec.get("name", "").lower()
                                    spec_value = spec.get("value", [])
                                    if "brand" in spec_name and spec_value:
                                        brand = spec_value[0] if isinstance(spec_value[0], str) else str(spec_value[0])
                            
                            # Get aspects from localizedAspects
                            for aspect in item_data.get("localizedAspects", []):
                                name = aspect.get("name", "")
                                value = aspect.get("value", "")
                                if name and value:
                                    aspects[name] = value if isinstance(value, str) else (value[0] if isinstance(value, list) else value)
                                    
                                    if "brand" in name.lower() and not brand:
                                        brand = value if isinstance(value, str) else (value[0] if isinstance(value, list) else value)
                                    if "condition" in name.lower() and not condition:
                                        condition = value if isinstance(value, str) else (value[0] if isinstance(value, list) else value)
                except Exception:
                    pass  # Continue without additional metadata if fetch fails
                
                # Extract image URL
                image_url = None
                images = summary.get("image", {})
                if isinstance(images, dict):
                    image_url = images.get("imageUrl") or images.get("url")
                elif isinstance(images, list) and images:
                    image_url = images[0].get("imageUrl") if isinstance(images[0], dict) else images[0]

                item: LuxuryItem = {
                    "item_id": item_id,
                    "title": title,
                    "url": summary.get("itemWebUrl", ""),
                    "price": price,
                    "shipping": shipping,
                    "currency": currency,
                    "brand": brand,
                    "product_name": product_name,
                    "condition": condition,
                    "image_url": image_url,
                }
                items.append(item)

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

    return items


def get_retail_price_ai(
    brand: str,
    title: str,
    openrouter_api_key: Optional[str] = None
) -> Optional[float]:
    """
    Get retail/MSRP price for a luxury item using AI search.
    
    Args:
        brand: Brand name (e.g., "Yves Saint Laurent", "Saint Laurent")
        title: Full eBay listing title
        openrouter_api_key: OpenRouter API key for AI search
        
    Returns:
        Retail price as float, or None if not found
    """
    if not openrouter_api_key:
        return None
    
    # Extract product name from title
    # Remove common eBay terms and extract product name
    product_name = title
    for term in ["YSL", "Saint Laurent", "Yves Saint Laurent", "Genuine", "Authentic", "New", "Used", "Pre-owned"]:
        product_name = product_name.replace(term, "").strip()
    
    prompt = f"""Find the retail/MSRP price for this luxury item:

Brand: {brand}
Product: {product_name}
Full Title: {title}

Search official brand websites (like ysl.com, saintlaurent.com) or authorized retailers to find the current retail price.

Return ONLY a JSON object with this format:
{{
  "retail_price": 1295.00,
  "currency": "USD",
  "source": "ysl.com"
}}

If you cannot find the retail price, return:
{{
  "retail_price": null,
  "currency": null,
  "source": null
}}

Return ONLY the JSON, nothing else."""
    
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "anthropic/claude-opus-4.5",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 200,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            message = result.get("choices", [{}])[0].get("message", {})
            content = message.get("content", "")
            
            try:
                # Clean up content
                content = re.sub(r'```json\s*', '', content)
                content = re.sub(r'```\s*$', '', content)
                content = content.strip()
                
                parsed = json.loads(content)
                retail_price = parsed.get("retail_price")
                
                if retail_price:
                    return float(retail_price)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        return None
    except Exception:
        return None


def get_retail_price(brand: str, product_name: str, title: str, openrouter_api_key: Optional[str] = None) -> Optional[float]:
    """
    Get retail/MSRP price for a luxury item.
    
    Args:
        brand: Brand name (e.g., "Yves Saint Laurent", "Saint Laurent")
        product_name: Product name
        title: Full eBay listing title
        openrouter_api_key: Optional OpenRouter API key for AI search
        
    Returns:
        Retail price as float, or None if not found
    """
    # Try AI search if API key available
    if openrouter_api_key:
        return get_retail_price_ai(brand, title, openrouter_api_key)
    
    return None


def analyze_luxury_arbitrage(
    items: list[LuxuryItem],
    tax_rate: float = 0.09,
    openrouter_api_key: Optional[str] = None,
    filter_size: Optional[str] = None,
    filter_material: Optional[str] = None,
    filter_new_with_box: bool = False
) -> list[dict]:
    """
    Analyze luxury items for arbitrage opportunities.
    
    Args:
        items: List of luxury items
        tax_rate: Tax rate as fraction
        
    Returns:
        List of arbitrage opportunities
    """
    opportunities = []
    
    for item in items:
        # Apply filters
        if filter_new_with_box:
            condition_str = item.get("condition", "") or ""
            condition = condition_str.lower()
            title_lower = item.get("title", "").lower()
            is_new_with_box = (
                ("new with box" in condition or "nib" in condition or "nwt" in condition) and
                ("new" in title_lower or "nib" in title_lower or "nwt" in title_lower)
            )
            if not is_new_with_box:
                continue
        
        if filter_size:
            title_lower = item.get("title", "").lower()
            # Check if size matches (e.g., "7.5", "US 7.5", "EU 37.5", "37.5")
            size_found = False
            if filter_size in title_lower:
                size_found = True
            # Also check for EU size equivalents (7.5 US = 37.5 EU)
            if filter_size == "7.5":
                if "37.5" in title_lower or "37.5eu" in title_lower or "eu 37.5" in title_lower:
                    size_found = True
            if not size_found:
                continue
        
        if filter_material:
            title_lower = item.get("title", "").lower()
            if filter_material.lower() not in title_lower:
                continue
        price = item["price"]
        shipping = item["shipping"]
        est_tax = round(tax_rate * price, 2)
        all_in_cost = price + shipping + est_tax
        
        # Get retail price
        title_safe = item['title'][:60].encode('ascii', 'ignore').decode('ascii')
        print(f"  Looking up retail price for: {title_safe}...")
        retail_price = get_retail_price(
            item.get("brand", ""),
            item.get("product_name", ""),
            item["title"],
            openrouter_api_key=openrouter_api_key
        )
        
        if retail_price:
            print(f"    Found retail price: ${retail_price:.2f}")
        else:
            print(f"    Could not find retail price")
        
        if retail_price:
            spread = retail_price - all_in_cost
            spread_pct = (spread / retail_price * 100) if retail_price > 0 else 0
            is_arbitrage = spread > 0
        else:
            retail_price = None
            spread = None
            spread_pct = None
            is_arbitrage = False
        
        # Check if item is new (for accurate arbitrage comparison)
        condition_str = item.get("condition", "") or ""
        condition = condition_str.lower()
        title_lower = item.get("title", "").lower()
        
        # Check condition field and title for "new" keywords
        is_new = (
            "new" in condition or 
            "new with tags" in condition or 
            "nwt" in condition or
            "new" in title_lower or
            "nwt" in title_lower or
            "new with tags" in title_lower
        )
        
        opportunity = {
            "item_id": item["item_id"],
            "title": item["title"],
            "brand": item.get("brand", ""),
            "condition": item.get("condition", ""),
            "is_new": is_new,
            "ebay_price": price,
            "shipping": shipping,
            "est_tax": est_tax,
            "all_in_cost": all_in_cost,
            "retail_price": retail_price,
            "spread": spread,
            "spread_pct": spread_pct,
            "is_arbitrage": is_arbitrage and is_new,  # Only arbitrage if new item
            "url": item["url"],
        }
        opportunities.append(opportunity)
    
    return opportunities


def main():
    """Main entry point for luxury items scanner."""
    # Load environment
    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    
    try:
        env = load_env()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    ebay_oauth = env.get("EBAY_OAUTH")
    openrouter_key = env.get("OPENROUTER_API_KEY", "")
    
    if not ebay_oauth:
        print("Error: EBAY_OAUTH not found in .env.local")
        sys.exit(1)
    
    if not openrouter_key:
        print("Warning: OPENROUTER_API_KEY not found. Retail price lookup will be disabled.")
        print("  Add OPENROUTER_API_KEY to .env.local to enable retail price lookup.")
    
    # Get parameters
    search_query = "YSL boots"
    brand_filter = "Yves Saint Laurent"
    limit = 20
    tax_rate = 0.09
    
    if len(sys.argv) > 1:
        search_query = sys.argv[1]
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    if len(sys.argv) > 3:
        brand_filter = sys.argv[3]
    
    print("=" * 70)
    print("Luxury Items eBay Arbitrage Scanner")
    print("=" * 70)
    print(f"Search Query: {search_query}")
    if brand_filter:
        print(f"Brand Filter: {brand_filter}")
    print(f"Limit: {limit} listings")
    print()
    
    # Step 1: Search eBay
    print("Step 1: Searching eBay...")
    items = search_luxury_items(
        search_query=search_query,
        limit=limit,
        env=env,
        brand_filter=brand_filter
    )
    print(f"Found {len(items)} eBay listings")
    print()
    
    # Step 1.5: Search Facebook Marketplace
    rapidapi_key = env.get("RAPIDAPI_KEY")
    fb_location = env.get("DEFAULT_FB_LOCATION", "Los Angeles, CA")
    
    fb_items = []
    if rapidapi_key and items:  # Only search if we found eBay items
        print("Step 1.5: Searching Facebook Marketplace for matching items...")
        print("  ⚠️  Note: Free tier has 30 requests/month - limiting to 10 items")
        try:
            # Build targeted query based on eBay items found
            targeted_query = build_targeted_fb_query(items, item_type="luxury", fallback_query=search_query)
            
            if not targeted_query:
                targeted_query = search_query
            
            print(f"  Using targeted query: '{targeted_query}' (based on {len(items)} eBay items)")
            
            # Limit to 10 items max to conserve API calls
            fb_limit = min(limit, 10)
            
            # Use price range from eBay items to filter Facebook results
            min_price, max_price = get_price_range_from_ebay_items(items)
            days_since_listed = 30  # Items listed in last 30 days
            
            print(f"  Price range filter: ${min_price:.0f} - ${max_price:.0f} (based on eBay prices)")
            
            fb_items = search_facebook_marketplace(
                query=targeted_query,
                max_items=fb_limit,
                env=env,
                location=fb_location,
                min_price=min_price,
                max_price=max_price,
                days_since_listed=days_since_listed
            )
            print(f"Found {len(fb_items)} Facebook Marketplace listings")
        except Exception as e:
            print(f"Warning: Facebook Marketplace search failed: {e}")
            print("  Continuing with eBay results only...")
        print()
    else:
        print("Step 1.5: Skipping Facebook Marketplace (RAPIDAPI_KEY not found)")
        print()
    
    # Step 1.6: Search Amazon
    amazon_items = []
    if rapidapi_key and items:  # Only search if we found eBay items
        print("Step 1.6: Searching Amazon for matching items...")
        try:
            from lib.amazon_api import search_amazon_products
            from lib.targeted_amazon_search import generate_targeted_amazon_query
            
            # Generate targeted Amazon queries for each eBay item
            for ebay_item in items[:5]:  # Limit to first 5 to conserve API calls
                targeted_query = generate_targeted_amazon_query(ebay_item, item_type="luxury")
                if not targeted_query:
                    continue
                
                try:
                    print(f"  Searching Amazon for: '{targeted_query}'")
                    current_amazon_results = search_amazon_products(
                        query=targeted_query,
                        max_items=5,  # Limit per query
                        env=env,
                        country="us"
                    )
                    amazon_items.extend(current_amazon_results)
                    print(f"    Found {len(current_amazon_results)} Amazon listings")
                except Exception as e:
                    print(f"  Warning: Amazon search for '{targeted_query}' failed: {e}")
            
            print(f"Found a total of {len(amazon_items)} Amazon listings")
        except ImportError as e:
            print(f"  Warning: Amazon API module not available: {e}")
        except Exception as e:
            print(f"Warning: Amazon search failed: {e}")
            print("  Continuing with eBay and Facebook results only...")
        print()
    else:
        print("Step 1.6: Skipping Amazon (RAPIDAPI_KEY not found)")
        print()
    
    # Step 2: Cross-platform comparison
    cross_platform_matches = []
    amazon_matches = []
    if fb_items:
        print("Step 2: Comparing eBay and Facebook Marketplace listings...")
        cross_platform_matches = compare_ebay_facebook(items, fb_items, item_type="luxury")
        print(f"Found {len(cross_platform_matches)} eBay-Facebook matches")
    
    if amazon_items:
        print("Step 2.5: Comparing eBay and Amazon listings...")
        from lib.arbitrage_comparison import compare_ebay_amazon
        amazon_matches = compare_ebay_amazon(items, amazon_items, item_type="luxury")
        print(f"Found {len(amazon_matches)} eBay-Amazon matches")
    
    if cross_platform_matches or amazon_matches:
        print()
    
    # Step 3: Analyze for arbitrage
    print("Step 3: Analyzing listings and looking up retail prices...")
    print()
    
    # Extract filters from search query or use defaults
    filter_size = "7.5" if "7.5" in search_query else None
    filter_material = "leather" if "leather" in search_query.lower() else None
    filter_new_with_box = "new" in search_query.lower() and "box" in search_query.lower()
    
    opportunities = analyze_luxury_arbitrage(
        items, 
        tax_rate=tax_rate, 
        openrouter_api_key=openrouter_key,
        filter_size=filter_size,
        filter_material=filter_material,
        filter_new_with_box=filter_new_with_box
    )
    
    # Add Facebook Marketplace items to opportunities (with platform marker)
    for fb_item in fb_items:
        # Calculate all-in cost (no tax typically on Facebook Marketplace, but add shipping if any)
        price = fb_item.get("price", 0)
        shipping = fb_item.get("shipping", 0)
        all_in_cost = price + shipping
        
        # Try to get retail price
        retail_price = None
        if openrouter_key and fb_item.get("brand"):
            retail_price = get_retail_price(
                brand=fb_item.get("brand", ""),
                product_name=fb_item.get("product_name", ""),
                title=fb_item.get("title", ""),
                openrouter_api_key=openrouter_key
            )
        
        # Check if new
        condition_str = fb_item.get("condition", "") or ""
        condition = condition_str.lower()
        title_lower = fb_item.get("title", "").lower()
        is_new = (
            "new" in condition or 
            "new with tags" in condition or 
            "nwt" in condition or
            "new" in title_lower or
            "nwt" in title_lower
        )
        
        # Calculate spread if retail price available
        spread = None
        spread_pct = None
        if retail_price and is_new:
            spread = retail_price - all_in_cost
            spread_pct = (spread / retail_price * 100) if retail_price > 0 else 0
        
        # Find matching eBay item if exists
        cross_match = None
        for match in cross_platform_matches:
            if match["facebook_item"]["item_id"] == fb_item["item_id"]:
                cross_match = match
                break
        
        opportunity = {
            "item_id": fb_item["item_id"],
            "title": fb_item["title"],
            "brand": fb_item.get("brand", ""),
            "condition": fb_item.get("condition", ""),
            "is_new": is_new,
            "ebay_price": price,
            "shipping": shipping,
            "est_tax": 0.0,  # Facebook Marketplace typically no tax
            "all_in_cost": all_in_cost,
            "retail_price": retail_price,
            "spread": spread,
            "spread_pct": spread_pct,
            "is_arbitrage": spread is not None and spread > 0 and is_new,
            "url": fb_item["url"],
            "platform": "Facebook",
            "cross_platform_match": cross_match["ebay_item"]["url"] if cross_match else "",
            "price_difference": cross_match["price_difference"] if cross_match else None,
            "best_platform": cross_match["best_platform"] if cross_match else "Facebook",
        }
        opportunities.append(opportunity)
    
    # Add Amazon items to opportunities (with platform marker)
    for amazon_item in amazon_items:
        # Calculate all-in cost (Amazon typically has free shipping for Prime, but add if any)
        price = amazon_item.get("price", 0)
        shipping = amazon_item.get("shipping", 0)
        all_in_cost = price + shipping
        
        # Try to get retail price (Amazon price is often the retail price)
        retail_price = price  # Amazon prices are typically retail/MSRP
        if openrouter_key and amazon_item.get("brand"):
            # Try to get actual retail price from AI if available
            ai_retail = get_retail_price(
                brand=amazon_item.get("brand", ""),
                product_name=amazon_item.get("product_name", ""),
                title=amazon_item.get("title", ""),
                openrouter_api_key=openrouter_key
            )
            if ai_retail:
                retail_price = ai_retail
        
        # Check if new (Amazon items are typically new)
        condition_str = amazon_item.get("condition", "") or ""
        condition = condition_str.lower()
        title_lower = amazon_item.get("title", "").lower()
        is_new = (
            "new" in condition or 
            "new with tags" in condition or 
            "nwt" in condition or
            "new" in title_lower or
            amazon_item.get("prime_eligible", False)  # Prime items are typically new
        )
        
        # Calculate spread if retail price available
        spread = None
        spread_pct = None
        if retail_price and is_new:
            spread = retail_price - all_in_cost
            spread_pct = (spread / retail_price * 100) if retail_price > 0 else 0
        
        # Find matching eBay item if exists
        amazon_match = None
        for match in amazon_matches:
            if match["amazon_item"]["item_id"] == amazon_item["item_id"]:
                amazon_match = match
                break
        
        opportunity = {
            "item_id": amazon_item["item_id"],
            "title": amazon_item["title"],
            "brand": amazon_item.get("brand", ""),
            "condition": amazon_item.get("condition", ""),
            "is_new": is_new,
            "ebay_price": price,
            "shipping": shipping,
            "est_tax": 0.0,  # Amazon tax varies by location
            "all_in_cost": all_in_cost,
            "retail_price": retail_price,
            "spread": spread,
            "spread_pct": spread_pct,
            "is_arbitrage": spread is not None and spread > 0 and is_new,
            "url": amazon_item["url"],
            "platform": "Amazon",
            "cross_platform_match": amazon_match["ebay_item"]["url"] if amazon_match else "",
            "price_difference": amazon_match["price_difference"] if amazon_match else None,
            "best_platform": amazon_match["best_platform"] if amazon_match else "Amazon",
        }
        opportunities.append(opportunity)
    
    # Add platform marker to eBay items
    for opp in opportunities:
        if "platform" not in opp:
            opp["platform"] = "eBay"
            # Find cross-platform matches (Facebook and Amazon)
            for match in cross_platform_matches:
                if match["ebay_item"]["item_id"] == opp["item_id"]:
                    opp["cross_platform_match"] = match["facebook_item"]["url"]
                    opp["price_difference"] = match["price_difference"]
                    opp["best_platform"] = match["best_platform"]
                    break
            
            # Also check Amazon matches
            for match in amazon_matches:
                if match["ebay_item"]["item_id"] == opp["item_id"]:
                    # If we already have a Facebook match, append Amazon match info
                    if opp.get("cross_platform_match"):
                        opp["cross_platform_match"] += f" | Amazon: {match['amazon_item']['url']}"
                    else:
                        opp["cross_platform_match"] = match["amazon_item"]["url"]
                    # Update best platform if Amazon is better
                    if match["best_platform"] == "Amazon":
                        opp["best_platform"] = "Amazon"
                    if not opp.get("price_difference") or match["price_difference"] > opp.get("price_difference", 0):
                        opp["price_difference"] = match["price_difference"]
                    break
            
            if "cross_platform_match" not in opp:
                opp["cross_platform_match"] = ""
                opp["price_difference"] = None
                opp["best_platform"] = "eBay"
    
    # Step 3: Display results
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    # Save to CSV
    csv_filename = "data/luxury_items.csv"
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item_id", "title", "brand", "condition", "is_new",
            "ebay_price", "shipping", "est_tax", "all_in_cost",
            "retail_price", "spread", "spread_pct", "is_arbitrage", 
            "url", "image_url", "platform", "cross_platform_match", 
            "price_difference", "best_platform"
        ])
        for opp in opportunities:
            # Find corresponding item to get image_url (check eBay, FB, and Amazon items)
            item = next((i for i in items if i.get("item_id") == opp.get("item_id")), None)
            if not item:
                # Try to find in FB items
                fb_item = next((i for i in fb_items if i.get("item_id") == opp.get("item_id")), None)
                if fb_item:
                    image_url = fb_item.get("image_url", "")
                else:
                    # Try to find in Amazon items
                    amazon_item = next((i for i in amazon_items if i.get("item_id") == opp.get("item_id")), None)
                    image_url = amazon_item.get("image_url", "") if amazon_item else ""
            else:
                image_url = item.get("image_url", "")
            
            writer.writerow([
                opp.get("item_id", ""),
                opp.get("title", ""),
                opp.get("brand", ""),
                opp.get("condition", ""),
                opp.get("is_new", False),
                opp.get("ebay_price", 0),
                opp.get("shipping", 0),
                opp.get("est_tax", 0),
                opp.get("all_in_cost", 0),
                opp.get("retail_price") or "",
                opp.get("spread") or "",
                opp.get("spread_pct") or "",
                opp.get("is_arbitrage", False),
                opp.get("url", ""),
                image_url,
                opp.get("platform", "eBay"),
                opp.get("cross_platform_match", ""),
                opp.get("price_difference") or "",
                opp.get("best_platform", ""),
            ])
    
    print(f"Saved {len(opportunities)} items to {csv_filename}")
    
    # Filter arbitrage opportunities
    arbitrage_deals = [o for o in opportunities if o.get("is_arbitrage")]
    
    # Sort by spread (highest first)
    all_opportunities = sorted(
        opportunities,
        key=lambda x: x.get("spread") if x.get("spread") is not None else float('-inf'),
        reverse=True
    )
    
    # Display table
    table_data = []
    for opp in all_opportunities[:20]:  # Show first 20
        title = opp["title"][:50] if len(opp["title"]) > 50 else opp["title"]
        retail = f"${opp['retail_price']:.2f}" if opp.get("retail_price") else "N/A"
        spread = f"${opp['spread']:.2f}" if opp.get("spread") is not None else "N/A"
        condition_display = opp.get("condition", "N/A")
        if opp.get("is_new"):
            condition_display += " (NEW)"
        
        table_data.append([
            title,
            opp.get("brand", "N/A"),
            condition_display,
            f"${opp['ebay_price']:.2f}",
            f"${opp['all_in_cost']:.2f}",
            retail,
            spread,
            opp.get("platform", "eBay"),
            "ARBITRAGE" if opp.get("is_arbitrage") else "No",
        ])
    
    headers = ["Title", "Brand", "Condition", "Price", "All-In Cost", "Retail Price", "Spread", "Platform", "Arbitrage"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Display cross-platform matches
    if cross_platform_matches:
        print(f"\n{'='*70}")
        print("CROSS-PLATFORM MATCHES")
        print(f"{'='*70}")
        print(f"Found {len(cross_platform_matches)} items listed on both platforms:")
        for i, match in enumerate(cross_platform_matches[:10], 1):  # Show top 10
            ebay_item = match["ebay_item"]
            fb_item = match["facebook_item"]
            ebay_price = ebay_item.get("price", 0) + ebay_item.get("shipping", 0)
            fb_price = fb_item.get("price", 0) + fb_item.get("shipping", 0)
            print(f"\n{i}. {ebay_item.get('title', '')[:60]}")
            print(f"   eBay: ${ebay_price:.2f} | Facebook: ${fb_price:.2f} | Difference: ${abs(ebay_price - fb_price):.2f}")
            print(f"   Best: {match['best_platform']} (saves ${abs(ebay_price - fb_price):.2f})")
            print(f"   Confidence: {match['match_confidence']:.2%}")
    
    if arbitrage_deals:
        print(f"\n[SUCCESS] Found {len(arbitrage_deals)} arbitrage opportunities!")
        print(f"  Best spread: ${max([o['spread'] for o in arbitrage_deals]):.2f}")
    else:
        print(f"\nNo arbitrage opportunities found (items may be used/pre-owned).")
        print(f"Note: Arbitrage is only calculated for NEW items.")


if __name__ == "__main__":
    main()

