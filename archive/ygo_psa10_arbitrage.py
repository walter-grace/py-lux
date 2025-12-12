#!/usr/bin/env python3
"""
YGO PSA10 Arbitrage Scanner (PSA shop · BIN only)

Scans PSA's official eBay store for Yu-Gi-Oh! TCG 1st Edition cards graded PSA 10,
Buy-It-Now only. For listings with a certification number, fetches PSA Estimated Value
and surfaces only positive-spread opportunities after shipping and estimated tax.

Requirements:
- Python 3.11+
- Dependencies: requests, python-dotenv, tabulate

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

Usage:
    python ygo_psa10_arbitrage.py --zip 90001 --limit 100 --min-spread 50 --min-spread-pct 0.2

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
    """Load environment variables from .env.local or .env file."""
    # Load .env first, then .env.local (which overrides .env)
    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    ebay_oauth = os.getenv("EBAY_OAUTH")
    psa_token = os.getenv("PSA_TOKEN")
    default_zip = os.getenv("DEFAULT_SHIP_ZIP", "90001")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")  # Optional

    if not ebay_oauth:
        raise ValueError("EBAY_OAUTH not found in environment")
    if not psa_token:
        raise ValueError("PSA_TOKEN not found in environment")

    return {
        "EBAY_OAUTH": ebay_oauth,
        "PSA_TOKEN": psa_token,
        "DEFAULT_SHIP_ZIP": default_zip,
        "OPENROUTER_API_KEY": openrouter_key,  # Optional
    }


def get_mock_ebay_items() -> list[EbayItem]:
    """Return mock eBay items for dry-run testing."""
    return [
        {
            "item_id": "123456789012",
            "title": "Yu-Gi-Oh! Blue-Eyes White Dragon 1st Edition PSA 10 Cert 12345678",
            "url": "https://www.ebay.com/itm/123456789012",
            "price": 450.00,
            "shipping": 15.00,
            "currency": "USD",
            "aspects": {
                "Game": ["Yu-Gi-Oh! TCG"],
                "Professional Grader": ["Professional Sports Authenticator (PSA)"],
                "Grade": ["10"],
                "Edition": ["1st Edition"],
                "Certification Number": ["12345678"],
            },
            "cert": "12345678",
            "card_name": "Blue-Eyes White Dragon",
            "year": "2002",
            "set_name": "LOB",
            "seller_username": "psa",
            "item_condition": "New",
        },
        {
            "item_id": "987654321098",
            "title": "Yu-Gi-Oh! Dark Magician 1st Edition PSA 10 #87654321",
            "url": "https://www.ebay.com/itm/987654321098",
            "price": 320.00,
            "shipping": 12.50,
            "currency": "USD",
            "aspects": {
                "Game": ["Yu-Gi-Oh! TCG"],
                "Professional Grader": ["Professional Sports Authenticator (PSA)"],
                "Grade": ["10"],
                "Edition": ["1st Edition"],
            },
            "cert": "87654321",
            "card_name": "Dark Magician",
            "year": "2002",
            "set_name": "LOB",
            "seller_username": "psa",
            "item_condition": "New",
        },
    ]


def get_mock_psa_value(cert: str) -> PsaCert:
    """Return mock PSA certificate data for dry-run testing."""
    # Mock data: cert 12345678 has good value, 87654321 has lower value
    if cert == "12345678":
        return {
            "cert": cert,
            "estimated_value": 550.00,
            "year": "2002",
            "brand": "Yu-Gi-Oh!",
            "set_name": "Legend of Blue Eyes White Dragon",
            "player": "Blue-Eyes White Dragon",
            "card_no": "001",
            "grade": "10",
        }
    elif cert == "87654321":
        return {
            "cert": cert,
            "estimated_value": 280.00,  # Lower than eBay price - negative spread
            "year": "2002",
            "brand": "Yu-Gi-Oh!",
            "set_name": "Legend of Blue Eyes White Dragon",
            "player": "Dark Magician",
            "card_no": "005",
            "grade": "10",
        }
    else:
        return {
            "cert": cert,
            "estimated_value": None,
            "year": None,
            "brand": None,
            "set_name": None,
            "player": None,
            "card_no": None,
            "grade": None,
        }


def search_ebay(limit: int, env: dict[str, str], year: Optional[str] = None) -> list[EbayItem]:
    """
    Search eBay Browse API for PSA 10 Yu-Gi-Oh! cards from PSA's official store.

    Args:
        limit: Maximum number of items to return
        env: Environment variables dict with EBAY_OAUTH
        year: Optional year filter (e.g., "2002")

    Returns:
        List of EbayItem dictionaries
    """
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {"Authorization": f"Bearer {env['EBAY_OAUTH']}"}

    # Build query with year if specified
    query = "yugioh PSA 10 1st edition"
    if year:
        query = f"yugioh PSA 10 1st edition {year}"

    params = {
        "q": query,
        "category_ids": "183454",
        "limit": str(limit),
        "filter": "sellers:{psa},buyingOptions:{FIXED_PRICE}",
        "aspect_filter": (
            "categoryId:183454,"
            "Game:Yu-Gi-Oh! TCG;"
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
                # Create a proper HTTPError with response
                response.raise_for_status()  # This will raise with proper response object
            
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
                # Cert number is in conditionDescriptors, not localizedAspects
                card_name = None
                year_extracted = None  # Year extracted from item data
                set_name = None
                seller_username = None
                item_condition = None
                cert_number = None
                
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
                            if year:  # year parameter was passed to function
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
                            image_url = None
                            images = item_data.get("image", {})
                            if isinstance(images, dict):
                                image_url = images.get("imageUrl") or images.get("url")
                            elif isinstance(images, list) and images:
                                image_url = images[0].get("imageUrl") if isinstance(images[0], dict) else images[0]
                            
                            # Also check thumbnailImages
                            if not image_url:
                                thumbnails = item_data.get("thumbnailImages", [])
                                if thumbnails and isinstance(thumbnails, list):
                                    # Get the largest image (usually last or has size indicator)
                                    for thumb in thumbnails:
                                        if isinstance(thumb, dict):
                                            thumb_url = thumb.get("imageUrl") or thumb.get("url")
                                            if thumb_url:
                                                # Prefer larger images (s-l1600, s-l1200, etc.)
                                                if "s-l1600" in thumb_url or "s-l1200" in thumb_url:
                                                    image_url = thumb_url
                                                    break
                                    # If no large image found, use first
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
                    wait_time = (2 ** attempt) + (0.1 * attempt)  # Exponential backoff
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
        "Certification",  # Sometimes just "Certification"
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
        # Verify grader and grade in aspects
        grader_psa = False
        grade_10 = False

        for aspect_name, aspect_values in item["aspects"].items():
            aspect_str = " ".join(str(v).lower() for v in aspect_values)
            if "psa" in aspect_str.lower() or "professional sports authenticator" in aspect_str.lower():
                grader_psa = True
            if "10" in aspect_str:
                grade_10 = True

        if grader_psa and grade_10:
            cert = cert_match.group(0)
            return cert

    return None


def fetch_psa_value(cert: str, env: dict[str, str]) -> PsaCert:
    """
    Fetch PSA certificate data from PSA API.

    Args:
        cert: Certification number
        env: Environment variables dict with PSA_TOKEN

    Returns:
        PsaCert dictionary
    """
    url = f"https://api.psacard.com/publicapi/cert/GetByCertNumber/{cert}"
    headers = {
        "Authorization": f"Bearer {env['PSA_TOKEN']}",  # Note: Capital "Bearer" as per Swagger docs
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    # Add jitter between calls
    import random
    jitter_ms = random.randint(100, 250) / 1000.0
    time.sleep(jitter_ms)

    # Use cloudscraper to bypass Cloudflare protection
    scraper = cloudscraper.create_scraper()
    scraper.headers.update(headers)

    max_retries = 2
    for attempt in range(max_retries):
        try:
            # cloudscraper handles SSL and Cloudflare challenges automatically
            response = scraper.get(url, timeout=30)
            
            # Handle PSA API specific response codes
            if response.status_code == 204:
                # Empty request data (missing cert number)
                return {
                    "cert": cert,
                    "estimated_value": None,
                    "year": None,
                    "brand": None,
                    "set_name": None,
                    "player": None,
                    "card_no": None,
                    "grade": None,
                }
            
            # Check for 4xx errors (invalid path/request)
            if 400 <= response.status_code < 500:
                # Try to parse error message
                try:
                    data = response.json()
                    if not data.get("IsValidRequest", True):
                        # Invalid cert number format
                        return {
                            "cert": cert,
                            "estimated_value": None,
                            "year": None,
                            "brand": None,
                            "set_name": None,
                            "player": None,
                            "card_no": None,
                            "grade": None,
                        }
                except:
                    pass
                return {
                    "cert": cert,
                    "estimated_value": None,
                    "year": None,
                    "brand": None,
                    "set_name": None,
                    "player": None,
                    "card_no": None,
                    "grade": None,
                }
            
            # Check for 500 (invalid credentials or server error)
            if response.status_code == 500:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    time.sleep(wait_time)
                    continue
                # After retries, return empty
                return {
                    "cert": cert,
                    "estimated_value": None,
                    "year": None,
                    "brand": None,
                    "set_name": None,
                    "player": None,
                    "card_no": None,
                    "grade": None,
                }
            
            response.raise_for_status()
            data = response.json()

            # Check PSA API response format
            is_valid = data.get("IsValidRequest", False)
            server_message = data.get("ServerMessage", "")
            
            if not is_valid:
                # Invalid request format
                return {
                    "cert": cert,
                    "estimated_value": None,
                    "year": None,
                    "brand": None,
                    "set_name": None,
                    "player": None,
                    "card_no": None,
                    "grade": None,
                }
            
            if server_message == "No data found":
                # Valid request but no data found
                return {
                    "cert": cert,
                    "estimated_value": None,
                    "year": None,
                    "brand": None,
                    "set_name": None,
                    "player": None,
                    "card_no": None,
                    "grade": None,
                }

            # PSA API returns data in PublicCertificationModel format:
            # { "PSACert": { ... }, "DNACert": { ... } }
            psa_cert_data = data.get("PSACert", {})
            
            # IMPORTANT: EstimatedValue is NOT in the PSA Public API response
            # We'll get it from scraping the PSA cert page or deep research
            estimated_value = None
            
            # Check if EstimatedValue exists in response (unlikely, but checking defensively)
            if "EstimatedValue" in data:
                try:
                    estimated_value = float(data["EstimatedValue"])
                except (ValueError, TypeError):
                    pass
            elif "EstimatedValue" in psa_cert_data:
                try:
                    estimated_value = float(psa_cert_data["EstimatedValue"])
                except (ValueError, TypeError):
                    pass
            
            # If not found in API response, we'll try scraping/research in the calling function

            # Extract fields from PSACert object
            psa_cert: PsaCert = {
                "cert": cert,
                "estimated_value": estimated_value,
                "year": psa_cert_data.get("Year"),
                "brand": psa_cert_data.get("Brand"),
                "set_name": psa_cert_data.get("SetName"),  # May not exist, use Subject or Category
                "player": psa_cert_data.get("Subject"),  # Subject is the player/card name
                "card_no": psa_cert_data.get("CardNumber"),
                "grade": psa_cert_data.get("CardGrade"),  # CardGrade is the grade
            }
            return psa_cert

        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (429, 502, 503, 504):
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    time.sleep(wait_time)
                    continue
            # For other HTTP errors, return empty cert
            return {
                "cert": cert,
                "estimated_value": None,
                "year": None,
                "brand": None,
                "set_name": None,
                "player": None,
                "card_no": None,
                "grade": None,
            }
        except Exception:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + (0.1 * attempt)
                time.sleep(wait_time)
                continue
            return {
                "cert": cert,
                "estimated_value": None,
                "year": None,
                "brand": None,
                "set_name": None,
                "player": None,
                "card_no": None,
                "grade": None,
            }

    return {
        "cert": cert,
        "estimated_value": None,
        "year": None,
        "brand": None,
        "set_name": None,
        "player": None,
        "card_no": None,
        "grade": None,
    }


def score_item(
    item: EbayItem, psa: PsaCert, tax_rate: float = 0.09
) -> Optional[ScoredDeal]:
    """
    Calculate costs, spread, and return ScoredDeal if valid.

    Args:
        item: EbayItem dictionary
        psa: PsaCert dictionary
        tax_rate: Tax rate as fraction (default 0.09 = 9%)

    Returns:
        ScoredDeal dictionary or None if invalid
    """
    # Skip if no PSA value
    if psa["estimated_value"] is None or psa["estimated_value"] <= 0:
        return None

    # Skip if not USD
    if item["currency"] != "USD":
        return None

    price = item["price"]
    shipping = item["shipping"]
    est_tax = round(tax_rate * price, 2)
    all_in = price + shipping + est_tax
    psa_est_value = psa["estimated_value"]
    spread = psa_est_value - all_in

    # Guard divide by zero
    if psa_est_value > 0:
        spread_pct = spread / psa_est_value
    else:
        spread_pct = 0.0

    cert = item["cert"]
    if not cert:
        return None

    deal: ScoredDeal = {
        "item_id": item["item_id"],
        "title": item["title"],
        "url": item["url"],
        "price": price,
        "shipping": shipping,
        "est_tax": est_tax,
        "all_in": all_in,
        "psa_est_value": psa_est_value,
        "spread": spread,
        "spread_pct": spread_pct,
        "cert": cert,
    }

    return deal


def render_table(deals: list[ScoredDeal]) -> None:
    """Render deals as a pretty table to console."""
    if not deals:
        print("No positive-spread matches.")
        return

    table_data = []
    for deal in deals:
        title = deal["title"][:60] if len(deal["title"]) > 60 else deal["title"]
        table_data.append([
            title,
            f"${deal['price']:.2f}",
            f"${deal['shipping']:.2f}",
            f"${deal['est_tax']:.2f}",
            f"${deal['all_in']:.2f}",
            f"${deal['psa_est_value']:.2f}",
            f"${deal['spread']:.2f}",
            f"{deal['spread_pct']*100:.1f}%",
            deal["cert"],
            deal["url"],
        ])

    headers = [
        "Title",
        "Price",
        "Ship",
        "Tax",
        "All In",
        "PSA Est",
        "Spread",
        "Spread%",
        "Cert",
        "Link",
    ]

    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def write_csv(deals: list[ScoredDeal], path: str = "deals.csv") -> None:
    """Write deals to CSV file."""
    if not deals:
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "title",
            "url",
            "price",
            "shipping",
            "est_tax",
            "all_in",
            "psa_est_value",
            "spread",
            "spread_pct",
            "cert",
            "ebay_item_id",
        ])

        for deal in deals:
            writer.writerow([
                deal["title"],
                deal["url"],
                deal["price"],
                deal["shipping"],
                deal["est_tax"],
                deal["all_in"],
                deal["psa_est_value"],
                deal["spread"],
                deal["spread_pct"],
                deal["cert"],
                deal["item_id"],
            ])

    print(f"\nWrote {len(deals)} deals to {path}")


def main(args: argparse.Namespace) -> None:
    """Main CLI entry point."""
    # Dry-run mode: use mock data
    if args.dry_run_sample:
        print("🧪 DRY-RUN MODE: Using mock data for testing")
        items = get_mock_ebay_items()
        env = {"DEFAULT_SHIP_ZIP": args.zip or "90001"}
        zip_code = args.zip or "90001"
        limit = 2
        min_spread = args.min_spread
        min_spread_pct = args.min_spread_pct
        min_psa_value = args.min_psa_value
        tax_rate = args.tax_rate
        print(f"Found {len(items)} mock PSA shop candidates")
    else:
        try:
            env = load_env()
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        zip_code = args.zip or env["DEFAULT_SHIP_ZIP"]
        limit = args.limit
        min_spread = args.min_spread
        min_spread_pct = args.min_spread_pct
        min_psa_value = args.min_psa_value
        tax_rate = args.tax_rate

        print(f"Searching eBay for PSA 10 Yu-Gi-Oh! 1st Edition cards (limit={limit})...")
        items = search_ebay(limit, env)
        print(f"Found {len(items)} PSA shop candidates")

    # Extract certs
    items_with_cert = 0
    for item in items:
        cert = extract_cert(item)
        item["cert"] = cert
        if cert:
            items_with_cert += 1

    print(f"Found {items_with_cert} items with certification numbers")

    # Fetch PSA values and score
    scored_deals: list[ScoredDeal] = []
    for item in items:
        if not item["cert"]:
            continue

        if args.dry_run_sample:
            psa = get_mock_psa_value(item["cert"])
        else:
            psa = fetch_psa_value(item["cert"], env)
            
            # If EstimatedValue not found in API response, try scraping/research
            if psa["estimated_value"] is None:
                print(f"  Fetching pricing for cert {item['cert']} via research agent...")
                card_info = {
                    "year": psa.get("year"),
                    "brand": psa.get("brand"),
                    "player": psa.get("player"),
                    "card_no": psa.get("card_no"),
                    "grade": psa.get("grade"),
                }
                estimated_value = get_card_pricing(
                    item["cert"],
                    card_info,
                    env.get("OPENROUTER_API_KEY"),
                    env.get("EBAY_OAUTH")  # Pass eBay OAuth for eBay search in research
                )
                if estimated_value:
                    psa["estimated_value"] = estimated_value
                    print(f"    Found PSA Estimate: ${estimated_value:,.2f}")
                else:
                    print(f"    Could not find PSA Estimate for cert {item['cert']}")
        
        deal = score_item(item, psa, tax_rate)

        if deal is None:
            continue

        # Apply filters
        if deal["psa_est_value"] < min_psa_value:
            continue
        if deal["spread"] < min_spread:
            continue
        if deal["spread_pct"] < min_spread_pct:
            continue

        scored_deals.append(deal)

    print(f"Scored {len(scored_deals)} positive-spread items")

    # Filter to positive spread only
    positive_deals = [d for d in scored_deals if d["spread"] > 0]

    if not positive_deals:
        print("No positive-spread matches.")
        sys.exit(0)

    # Output
    render_table(positive_deals)
    write_csv(positive_deals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan PSA eBay store for YGO PSA10 arbitrage opportunities"
    )
    parser.add_argument(
        "--zip",
        type=str,
        help="Shipping zip code (default: from DEFAULT_SHIP_ZIP env var)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of items to search (default: 50)",
    )
    parser.add_argument(
        "--min-spread",
        type=float,
        default=0.0,
        help="Minimum absolute spread in USD (default: 0.0)",
    )
    parser.add_argument(
        "--min-spread-pct",
        type=float,
        default=0.0,
        help="Minimum spread percentage as fraction (default: 0.0)",
    )
    parser.add_argument(
        "--min-psa-value",
        type=float,
        default=0.0,
        help="Minimum PSA estimated value to consider (default: 0.0)",
    )
    parser.add_argument(
        "--tax-rate",
        type=float,
        default=0.09,
        help="Tax rate as fraction (default: 0.09 = 9%%)",
    )
    parser.add_argument(
        "--dry-run-sample",
        action="store_true",
        help="Run with 2 mocked eBay items to validate parsing & math (no API calls)",
    )

    args = parser.parse_args()
    main(args)

