#!/usr/bin/env python3
"""
Pokemon Base Set 1999 PSA10 Arbitrage Scanner (PSA shop · BIN only)

Scans PSA's official eBay store for Pokemon Base Set 1999 1st Edition cards graded PSA 10,
Buy-It-Now only. For listings with a certification number, fetches PSA Estimated Value
and surfaces only positive-spread opportunities after shipping and estimated tax.

Requirements:
- Python 3.11+
- Dependencies: requests, python-dotenv, tabulate, cloudscraper, beautifulsoup4

Setup:
1. Create eBay OAuth token:
   - Go to https://developer.ebay.com/
   - Create an app and get OAuth token
   - Set EBAY_OAUTH in .env

2. Create PSA API token:
   - Go to https://www.psacard.com/publicapi/documentation
   - Log in and generate access token
   - Set PSA_TOKEN in .env.local
   - Test in Swagger UI: https://api.psacard.com/publicapi/swagger

3. Create .env file:
   EBAY_OAUTH=your_ebay_token_here
   PSA_TOKEN=your_psa_token_here
   DEFAULT_SHIP_ZIP=90001
   OPENROUTER_API_KEY=your_openrouter_key_here (optional, for image extraction)

Usage:
    python pokemon_ebay_scanner.py --zip 90001 --limit 100 --min-spread 50 --min-spread-pct 0.2

Limitations:
- BIN (FIXED_PRICE) only; auctions and best offers excluded
- Tax rate is a flat 9% placeholder (TODO: zip-based calculation)
- Only USD currency supported
"""

import argparse
import csv
import os
import re
import sys
import time
from typing import TypedDict, Optional

import requests
import cloudscraper
from dotenv import load_dotenv
from tabulate import tabulate

# Import research agent
try:
    from research_agent import get_card_pricing, scrape_psa_estimate
except ImportError:
    # Fallback if research_agent not available
    def get_card_pricing(*args, **kwargs):
        return None
    def scrape_psa_estimate(*args, **kwargs):
        return None


# Type definitions
class EbayItem(TypedDict):
    item_id: str
    title: str
    url: str
    price: float
    shipping: float
    currency: str
    aspects: dict[str, list[str]]
    cert: Optional[str]
    card_name: Optional[str]  # Extracted card name
    year: Optional[str]  # Extracted year
    set_name: Optional[str]  # Extracted set name
    seller_username: Optional[str]  # Seller info
    item_condition: Optional[str]  # Item condition
    image_url: Optional[str]  # Primary image URL from eBay


class PsaCert(TypedDict):
    cert: str
    estimated_value: Optional[float]
    year: Optional[str]
    brand: Optional[str]
    set_name: Optional[str]
    player: Optional[str]
    card_no: Optional[str]
    grade: Optional[str]


class ScoredDeal(TypedDict):
    item_id: str
    title: str
    url: str
    price: float
    shipping: float
    est_tax: float
    all_in: float
    psa_est_value: float
    spread: float
    spread_pct: float
    cert: str


def load_env() -> dict[str, str]:
    """Load environment variables from .env and .env.local"""
    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    
    default_zip = os.getenv("DEFAULT_SHIP_ZIP", "90001")
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    
    return {
        "EBAY_OAUTH": os.getenv("EBAY_OAUTH", ""),
        "PSA_TOKEN": os.getenv("PSA_TOKEN", ""),
        "DEFAULT_SHIP_ZIP": default_zip,
        "OPENROUTER_API_KEY": openrouter_key,  # Optional
    }


def search_ebay(limit: int, env: dict[str, str], year: Optional[str] = None) -> list[EbayItem]:
    """
    Search eBay Browse API for PSA 10 Pokemon Base Set 1999 cards from PSA's official store.

    Args:
        limit: Maximum number of items to return
        env: Environment variables dict with EBAY_OAUTH
        year: Optional year filter (default: 1999 for Pokemon Base Set)

    Returns:
        List of EbayItem dictionaries
    """
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {"Authorization": f"Bearer {env['EBAY_OAUTH']}"}

    # Build query - Pokemon Base Set 1999
    query = "pokemon PSA 10 1st edition base set"
    if year:
        query = f"pokemon PSA 10 1st edition base set {year}"
    else:
        query = "pokemon PSA 10 1st edition base set 1999"  # Default to 1999 Base Set

    params = {
        "q": query,
        "category_ids": "183454",  # Trading Cards category
        "limit": str(limit),
        "filter": "sellers:{psa},buyingOptions:{FIXED_PRICE}",
        "aspect_filter": (
            "categoryId:183454,"
            "Game:Pokemon;"
            "Professional Grader:Professional Sports Authenticator (PSA);"
            "Grade:10;"
            "Edition:1st Edition"
        ),
    }

    items: list[EbayItem] = []
    seen_ids: set[str] = set()

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Better error handling for 401
            if response.status_code == 401:
                error_data = response.text
                print(f"eBay API Authentication Error (401):")
                print(f"  This usually means your token is expired or invalid.")
                print(f"  Please regenerate your eBay User Access Token at:")
                print(f"  https://developer.ebay.com/my/keys")
                print(f"  Error details: {error_data[:200]}")
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

                # Extract aspects (may not be in summary, try to get from full item)
                aspects: dict[str, list[str]] = {}
                is_1st_edition_summary = False
                for aspect in summary.get("localizedAspects", []):
                    name = aspect.get("name", "")
                    values = aspect.get("value", [])
                    if name and values:
                        aspects[name] = values
                        # Check for 1st Edition in summary
                        name_lower = name.lower()
                        if "edition" in name_lower:
                            value_str = (values[0] if isinstance(values, list) and values else str(values)).lower()
                            if "1st" in value_str or "first" in value_str:
                                is_1st_edition_summary = True
                
                # Also check title for 1st Edition
                title_lower = summary.get("title", "").lower()
                if "1st" in title_lower or "first edition" in title_lower:
                    is_1st_edition_summary = True
                
                # Skip if not 1st Edition (early filter to avoid unnecessary API calls)
                if not is_1st_edition_summary:
                    continue
                
                # Always fetch full item details to get cert number and more metadata
                card_name = None
                year_extracted = None
                set_name = None
                seller_username = None
                item_condition = None
                cert_number = None
                image_url = None
                
                try:
                    item_url = summary.get("itemHref", "")
                    if item_url:
                        item_response = requests.get(item_url, headers=headers, timeout=30)
                        if item_response.status_code == 200:
                            item_data = item_response.json()
                            
                            # Get aspects from localizedAspects
                            is_1st_edition = False
                            for aspect in item_data.get("localizedAspects", []):
                                name = aspect.get("name", "")
                                value = aspect.get("value", "")
                                if name and value:
                                    aspects[name] = [value] if isinstance(value, str) else value
                                    
                                    # Check for 1st Edition
                                    name_lower = name.lower()
                                    value_str = (value if isinstance(value, str) else (value[0] if isinstance(value, list) and value else "")).lower()
                                    if "edition" in name_lower and ("1st" in value_str or "first" in value_str):
                                        is_1st_edition = True
                                    
                                    # Extract structured metadata
                                    if "card name" in name_lower or "player" in name_lower or "subject" in name_lower:
                                        card_name = value if isinstance(value, str) else (value[0] if isinstance(value, list) and value else None)
                                    elif "year" in name_lower:
                                        year_extracted = value if isinstance(value, str) else (value[0] if isinstance(value, list) and value else None)
                                    elif "set" in name_lower or "set name" in name_lower:
                                        set_name = value if isinstance(value, str) else (value[0] if isinstance(value, list) and value else None)
                            
                            # Also check title for 1st Edition
                            title_lower = item_data.get("title", "").lower()
                            if "1st" in title_lower or "first edition" in title_lower:
                                is_1st_edition = True
                            
                            # Skip if not 1st Edition
                            if not is_1st_edition:
                                continue
                            
                            # Filter by year if specified (check both extracted year and title)
                            if year:
                                year_found = False
                                if year_extracted and str(year_extracted) == str(year):
                                    year_found = True
                                elif str(year) in title_lower:
                                    year_found = True
                                if not year_found:
                                    continue
                            
                            # Get cert number from conditionDescriptors
                            for descriptor in item_data.get("conditionDescriptors", []):
                                name = descriptor.get("name", "")
                                values = descriptor.get("values", [])
                                
                                if "certification" in name.lower() or "cert" in name.lower():
                                    if values:
                                        cert_value = values[0].get("content", "") if isinstance(values[0], dict) else str(values[0])
                                        if cert_value:
                                            cert_number = cert_value
                                            aspects[name] = [cert_value]
                                
                                # Also extract condition
                                if "condition" in name.lower() and not item_condition:
                                    if values:
                                        item_condition = values[0].get("content", "") if isinstance(values[0], dict) else str(values[0])
                            
                            # Try to get cert from itemSpecifics if available
                            if not cert_number:
                                item_specifics = item_data.get("itemSpecifics", {})
                                for spec in item_specifics.get("nameValuePairs", []):
                                    spec_name = spec.get("name", "").lower()
                                    spec_value = spec.get("value", [])
                                    if "cert" in spec_name or "certification" in spec_name:
                                        if spec_value:
                                            cert_number = spec_value[0] if isinstance(spec_value[0], str) else str(spec_value[0])
                            
                            # Extract seller info
                            seller = item_data.get("seller", {})
                            seller_username = seller.get("username")
                            
                            # Extract item condition if not already found
                            if not item_condition:
                                item_condition = item_data.get("condition", "")
                            
                            # Extract image URL (primary image)
                            images = item_data.get("image", {})
                            if isinstance(images, dict):
                                image_url = images.get("imageUrl") or images.get("url")
                            elif isinstance(images, list) and images:
                                image_url = images[0].get("imageUrl") if isinstance(images[0], dict) else images[0]
                            
                            # Also check thumbnailImages
                            if not image_url:
                                thumbnails = item_data.get("thumbnailImages", [])
                                if thumbnails and isinstance(thumbnails, list):
                                    for thumb in thumbnails:
                                        if isinstance(thumb, dict):
                                            thumb_url = thumb.get("imageUrl") or thumb.get("url")
                                            if thumb_url:
                                                if "s-l1600" in thumb_url or "s-l1200" in thumb_url:
                                                    image_url = thumb_url
                                                    break
                                    if not image_url and thumbnails[0]:
                                        if isinstance(thumbnails[0], dict):
                                            image_url = thumbnails[0].get("imageUrl") or thumbnails[0].get("url")
                                
                except Exception:
                    pass  # Continue without additional metadata if fetch fails

                item: EbayItem = {
                    "item_id": item_id,
                    "title": summary.get("title", ""),
                    "url": summary.get("itemWebUrl", ""),
                    "price": price,
                    "shipping": shipping,
                    "currency": currency,
                    "aspects": aspects,
                    "cert": cert_number,
                    "card_name": card_name,
                    "year": year_extracted,
                    "set_name": set_name,
                    "seller_username": seller_username,
                    "item_condition": item_condition,
                    "image_url": image_url,
                }
                items.append(item)

            break  # Success, exit retry loop

        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (429, 500, 502, 503, 504):
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


def extract_cert(item: EbayItem) -> Optional[str]:
    """
    Extract PSA certification number from item aspects or title.

    Args:
        item: EbayItem dictionary

    Returns:
        Certification number as string, or None if not found
    """
    # Try aspects first (including conditionDescriptors)
    cert_names = [
        "Certification Number",
        "Certification #",
        "Cert Number",
        "PSA Cert",
        "Cert #",
        "Certification",
    ]

    for name in cert_names:
        if name in item["aspects"]:
            values = item["aspects"][name]
            if values:
                cert = re.sub(r"\D", "", str(values[0]))  # Digits only
                if 7 <= len(cert) <= 9:
                    return cert

    # Fallback: regex in title
    title = item["title"]
    cert_match = re.search(r"\b\d{7,9}\b", title)
    if cert_match:
        cert = cert_match.group(0)
        return cert

    return None

