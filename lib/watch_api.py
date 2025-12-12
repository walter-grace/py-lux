"""
Watch API - Extract watch metadata and get reference prices from multiple sources
"""
import re
import json
import time
from typing import TypedDict, Optional, Dict, Any
import requests
import cloudscraper
from bs4 import BeautifulSoup
from lib.ebay_sold_listings import get_market_price_from_sold_listings
from lib.watch_database_api import (
    search_watches_by_name,
    search_reference,
    get_watch_details,
    normalize_brand_name,
    get_all_makes
)


class WatchInfo(TypedDict):
    brand: Optional[str]
    model: Optional[str]
    model_number: Optional[str]
    year: Optional[str]
    condition: Optional[str]
    movement_type: Optional[str]
    case_material: Optional[str]
    dial_color: Optional[str]
    title: Optional[str]


def get_watchcharts_url(watch_info: WatchInfo) -> Optional[str]:
    """
    Generate WatchCharts URL for a watch based on brand and model.
    Tries to find the actual watch page URL by searching, otherwise returns search URL.
    
    WatchCharts URL format: https://watchcharts.com/watch_model/{id}-{brand}-{model}/overview
    
    Args:
        watch_info: WatchInfo dictionary with watch metadata
    
    Returns:
        WatchCharts URL string (preferably direct watch page, otherwise search URL), or None if insufficient data
    """
    brand = watch_info.get("brand")
    model = watch_info.get("model_number") or watch_info.get("model")
    
    if not brand:
        return None
    
    from urllib.parse import quote_plus
    
    # First, try to find the actual watch page URL by searching
    if model:
        search_query = f"{brand} {model}"
    else:
        search_query = brand
    
    encoded_query = quote_plus(search_query)
    search_url = f"https://watchcharts.com/watches?search={encoded_query}"
    
    # Try to scrape the search results to find the actual watch page URL
    # WatchCharts URL format: /watch_model/{id}-{brand}-{model}/overview
    try:
        scraper = cloudscraper.create_scraper()
        scraper.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        
        response = scraper.get(search_url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for watch_model links
            # Format: /watch_model/{id}-{brand}-{model}/overview
            brand_lower = brand.lower().replace(' ', '-')
            model_number = watch_info.get("model_number")  # Use model_number if available (more specific)
            model_name = watch_info.get("model")  # Model name (e.g., "GMT-Master II")
            
            # Find all links
            links = soup.find_all('a', href=True)
            
            best_match = None
            best_score = 0
            
            for link in links:
                href = link.get('href', '')
                
                # Look for watch_model URLs
                if '/watch_model/' in href:
                    href_lower = href.lower()
                    link_text = link.get_text().strip().lower()
                    
                    # Brand must match
                    if brand_lower not in href_lower and brand.lower() not in href_lower:
                        continue  # Skip if brand doesn't match
                    
                    score = 0
                    score += 10  # Base score for brand match
                    
                    # Model number matching (highest priority)
                    if model_number:
                        model_num_lower = model_number.lower()
                        model_num_clean = model_number.replace(' ', '').replace('-', '').replace('_', '').lower()
                        href_clean = href_lower.replace('-', '').replace('_', '').replace('/', '')
                        link_text_clean = link_text.replace('-', '').replace(' ', '').replace('_', '')
                        
                        # Check for exact model number match
                        exact_in_url = model_num_lower in href_lower or model_num_clean in href_clean
                        exact_in_text = model_num_lower in link_text or model_num_clean in link_text_clean
                        
                        if exact_in_url and exact_in_text:
                            score += 50  # Perfect match!
                        elif exact_in_url or exact_in_text:
                            score += 25  # Partial match
                        else:
                            # Check for partial model number (e.g., "126710" in "126710BLNR")
                            # Only count if it's a significant portion
                            if len(model_number) >= 6:  # For model numbers like "126710BLNR"
                                base_num = model_number[:6]  # First 6 digits
                                if base_num in href_lower or base_num in link_text:
                                    score += 5  # Partial number match
                                else:
                                    # No model number match at all - skip this link
                                    continue
                    
                    # Model name matching (secondary priority)
                    if model_name:
                        model_name_lower = model_name.lower()
                        model_words = [w for w in model_name_lower.split() if len(w) > 2]
                        
                        # Check if key model words appear
                        words_in_url = sum(1 for word in model_words if word in href_lower)
                        words_in_text = sum(1 for word in model_words if word in link_text)
                        
                        if words_in_url >= 2:  # At least 2 key words match
                            score += 10
                        elif words_in_url >= 1:
                            score += 5
                        
                        if words_in_text >= 2:
                            score += 5
                    
                    if score > best_score:
                        best_score = score
                        # Construct full URL
                        if href.startswith('/'):
                            best_match = f"https://watchcharts.com{href}"
                        elif href.startswith('http'):
                            best_match = href
                        else:
                            continue
                        
                        # Ensure it has /overview
                        if '/overview' not in best_match:
                            if best_match.endswith('/'):
                                best_match = f"{best_match}overview"
                            else:
                                best_match = f"{best_match}/overview"
            
            # Only return direct link if we have a very strong match
            # For model numbers: require at least 25 points (brand + exact/partial model match)
            # For model names only: require at least 20 points (brand + model name words)
            if model_number:
                min_score = 25  # Brand (10) + model number match (15+)
            elif model_name:
                min_score = 20  # Brand (10) + model name words (10+)
            else:
                min_score = 15  # Just brand match
            
            if best_match and best_score >= min_score:
                return best_match
            
    except Exception:
        # If scraping fails, fall back to search URL
        pass
    
    # Fallback: return search URL if we couldn't find the exact watch page
    return search_url


def extract_watch_metadata(
    title: str,
    aspects: dict,
    openrouter_api_key: Optional[str] = None
) -> WatchInfo:
    """
    Extract structured watch metadata from eBay listing title and aspects.
    
    Args:
        title: eBay listing title
        aspects: Dictionary of aspect name-value pairs from eBay API
        openrouter_api_key: Optional OpenRouter API key for AI extraction
    
    Returns:
        WatchInfo dictionary with extracted metadata
    """
    watch_info: WatchInfo = {
        "brand": None,
        "model": None,
        "model_number": None,
        "year": None,
        "condition": None,
        "movement_type": None,
        "case_material": None,
        "dial_color": None,
        "title": title,
    }
    
    # Extract from aspects first (most reliable)
    for aspect_name, aspect_value in aspects.items():
        name_lower = aspect_name.lower()
        value = aspect_value if isinstance(aspect_value, str) else (aspect_value[0] if isinstance(aspect_value, list) and aspect_value else "")
        
        if "brand" in name_lower:
            watch_info["brand"] = value
        elif "condition" in name_lower:
            watch_info["condition"] = value
        elif "movement" in name_lower or "movement type" in name_lower:
            watch_info["movement_type"] = value
        elif "case material" in name_lower or "material" in name_lower:
            watch_info["case_material"] = value
        elif "dial" in name_lower and "color" in name_lower:
            watch_info["dial_color"] = value
        elif "year" in name_lower:
            watch_info["year"] = value
    
    # Try AI extraction if OpenRouter key available and we're missing key fields
    if openrouter_api_key and (not watch_info["brand"] or not watch_info["model"]):
        ai_info = _extract_watch_metadata_ai(title, openrouter_api_key)
        if ai_info:
            # Merge AI results, preferring existing values
            for key in ["brand", "model", "model_number", "year", "condition", "movement_type"]:
                if not watch_info.get(key) and ai_info.get(key):
                    watch_info[key] = ai_info[key]
    
    # Fallback: Basic regex extraction from title if still missing brand
    if not watch_info["brand"]:
        watch_info["brand"] = _extract_brand_from_title(title)
    
    if not watch_info["model"] and not watch_info["model_number"]:
        watch_info["model"] = _extract_model_from_title(title, watch_info.get("brand"))
    
    return watch_info


def enrich_watch_metadata_with_watch_db(
    watch_info: WatchInfo,
    api_key: Optional[str] = None,
    env: Optional[Dict[str, str]] = None
) -> WatchInfo:
    """
    Enrich watch metadata using Watch Database API.
    This function searches the Watch Database API to validate and enhance
    extracted watch metadata from eBay listings.
    
    Args:
        watch_info: Initial WatchInfo dictionary with extracted metadata
        api_key: Optional Watch Database API key (if None, will try to get from env)
        env: Optional environment variables dict (if None and api_key is None, will load)
        
    Returns:
        Enriched WatchInfo dictionary with validated/enhanced metadata
    """
    # Get API key
    if not api_key:
        if env is None:
            from lib.config import load_env
            env = load_env()
        api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY")
    
    if not api_key:
        # No API key available, return original metadata
        return watch_info
    
    # Only enrich if we have at least a brand or model to search with
    brand = watch_info.get("brand")
    model = watch_info.get("model")
    model_number = watch_info.get("model_number")
    title = watch_info.get("title", "")
    
    if not brand and not model and not model_number:
        # No useful metadata to search with
        return watch_info
    
    enriched_info = watch_info.copy()
    
    try:
        # Step 1: Normalize brand name using makes list
        if brand:
            makes = get_all_makes(api_key, use_cache=True)
            normalized_brand = normalize_brand_name(brand, makes=makes, api_key=api_key)
            if normalized_brand and normalized_brand != brand:
                print(f"    Normalized brand: {brand} -> {normalized_brand}")
                enriched_info["brand"] = normalized_brand
                brand = normalized_brand
        
        # Step 2: Search by reference number if available (most accurate)
        if model_number:
            ref_results = search_reference(model_number, api_key)
            if ref_results:
                # Extract watch data from results
                watches = []
                if isinstance(ref_results, list):
                    watches = ref_results
                elif isinstance(ref_results, dict):
                    watches = ref_results.get("data", ref_results.get("results", ref_results.get("watches", [])))
                    if not isinstance(watches, list) and isinstance(ref_results, dict):
                        watches = [ref_results]  # Single watch result
                
                if watches and len(watches) > 0:
                    watch_data = watches[0]  # Use first match
                    print(f"    Found watch in database by reference: {model_number}")
                    
                    # Enrich metadata from API response
                    if not enriched_info.get("brand") and watch_data.get("make") or watch_data.get("brand"):
                        enriched_info["brand"] = watch_data.get("make") or watch_data.get("brand")
                    
                    if not enriched_info.get("model") and watch_data.get("model"):
                        enriched_info["model"] = watch_data.get("model")
                    
                    if not enriched_info.get("model_number") and watch_data.get("reference"):
                        enriched_info["model_number"] = watch_data.get("reference")
                    
                    # Add additional fields if available
                    if watch_data.get("year") and not enriched_info.get("year"):
                        enriched_info["year"] = str(watch_data.get("year"))
                    
                    if watch_data.get("movement") and not enriched_info.get("movement_type"):
                        enriched_info["movement_type"] = watch_data.get("movement")
                    
                    if watch_data.get("case_material") and not enriched_info.get("case_material"):
                        enriched_info["case_material"] = watch_data.get("case_material")
                    
                    if watch_data.get("dial_color") and not enriched_info.get("dial_color"):
                        enriched_info["dial_color"] = watch_data.get("dial_color")
                    
                    return enriched_info
        
        # Step 3: Search by name if we have brand and/or model
        search_query_parts = []
        if brand:
            search_query_parts.append(brand)
        if model:
            search_query_parts.append(model)
        elif model_number:
            search_query_parts.append(model_number)
        
        if search_query_parts:
            search_query = " ".join(search_query_parts)
            # Also try with title if it's different
            if title and search_query.lower() not in title.lower():
                # Try searching with title as well
                search_results = search_watches_by_name(title, api_key, limit=5)
            else:
                search_results = search_watches_by_name(search_query, api_key, limit=5)
            
            if search_results:
                # Extract watches from results
                watches = []
                if isinstance(search_results, list):
                    watches = search_results
                elif isinstance(search_results, dict):
                    watches = search_results.get("data", search_results.get("results", search_results.get("watches", [])))
                    if not isinstance(watches, list) and isinstance(search_results, dict):
                        watches = [search_results]
                
                if watches and len(watches) > 0:
                    # Find best match
                    best_match = None
                    best_score = 0
                    
                    for watch_data in watches[:5]:  # Check top 5 results
                        score = 0
                        watch_brand = (watch_data.get("make") or watch_data.get("brand") or "").lower()
                        watch_model = (watch_data.get("model") or "").lower()
                        watch_ref = (watch_data.get("reference") or "").lower()
                        
                        # Score based on matches
                        if brand and brand.lower() in watch_brand:
                            score += 10
                        if model and model.lower() in watch_model:
                            score += 10
                        if model_number and model_number.lower() in watch_ref:
                            score += 20  # Reference match is most important
                        
                        if score > best_score:
                            best_score = score
                            best_match = watch_data
                    
                    if best_match and best_score >= 10:  # Require at least brand or model match
                        print(f"    Found watch in database by name search (score: {best_score})")
                        
                        # Enrich metadata from best match
                        if not enriched_info.get("brand") and best_match.get("make"):
                            enriched_info["brand"] = best_match.get("make")
                        
                        if not enriched_info.get("model") and best_match.get("model"):
                            enriched_info["model"] = best_match.get("model")
                        
                        if not enriched_info.get("model_number") and best_match.get("reference"):
                            enriched_info["model_number"] = best_match.get("reference")
                        
                        # Add additional fields if available
                        if best_match.get("year") and not enriched_info.get("year"):
                            enriched_info["year"] = str(best_match.get("year"))
                        
                        if best_match.get("movement") and not enriched_info.get("movement_type"):
                            enriched_info["movement_type"] = best_match.get("movement")
                        
                        if best_match.get("case_material") and not enriched_info.get("case_material"):
                            enriched_info["case_material"] = best_match.get("case_material")
                        
                        if best_match.get("dial_color") and not enriched_info.get("dial_color"):
                            enriched_info["dial_color"] = best_match.get("dial_color")
    
    except Exception as e:
        # If API enrichment fails, return original metadata
        print(f"    ⚠️  Watch Database API enrichment failed: {e}")
        return watch_info
    
    return enriched_info


def _extract_brand_from_title(title: str) -> Optional[str]:
    """Extract watch brand from title using common patterns."""
    # Common watch brands
    brands = [
        "Rolex", "Omega", "Seiko", "Citizen", "Casio", "Timex", "Bulova",
        "Tissot", "Tag Heuer", "Breitling", "Patek Philippe", "Audemars Piguet",
        "Vacheron Constantin", "IWC", "Panerai", "Cartier", "Jaeger-LeCoultre",
        "Blancpain", "Breguet", "Zenith", "Tudor", "Longines", "Hamilton",
        "Movado", "Fossil", "Michael Kors", "Invicta", "Orient", "Swatch"
    ]
    
    title_upper = title.upper()
    for brand in brands:
        if brand.upper() in title_upper:
            return brand
    
    return None


def _extract_model_from_title(title: str, brand: Optional[str] = None) -> Optional[str]:
    """Extract watch model from title using basic patterns."""
    # Remove common words
    title_clean = title
    for word in ["watch", "mens", "womens", "vintage", "pre-owned", "authentic", "genuine"]:
        title_clean = re.sub(rf'\b{word}\b', '', title_clean, flags=re.IGNORECASE)
    
    # Look for model numbers (e.g., "Submariner 116610", "Speedmaster 311.30.42.30.01.005")
    model_patterns = [
        r'\b([A-Z]{2,}\d{3,}[A-Z]?\d*)\b',  # Alphanumeric model numbers
        r'\b(\d{3,}[A-Z]?\d*\.\d+\.\d+\.\d+\.\d+\.\d+)\b',  # Omega-style numbers
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # Model names like "Submariner Date"
    ]
    
    for pattern in model_patterns:
        match = re.search(pattern, title_clean)
        if match:
            model = match.group(1).strip()
            if len(model) > 2:  # Filter out very short matches
                return model
    
    return None


def _extract_watch_metadata_ai(
    title: str,
    openrouter_api_key: str
) -> Optional[Dict[str, Any]]:
    """
    Use AI to extract watch metadata from title.
    
    Args:
        title: eBay listing title
        openrouter_api_key: OpenRouter API key
    
    Returns:
        Dictionary with extracted metadata, or None if failed
    """
    prompt = f"""Extract watch information from this eBay listing title:

Title: {title}

Return ONLY a JSON object with this format:
{{
  "brand": "Rolex",
  "model": "Submariner",
  "model_number": "116610LN",
  "year": "2020",
  "condition": "Pre-owned",
  "movement_type": "Automatic"
}}

If a field cannot be determined, use null. Return ONLY the JSON, nothing else."""

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "anthropic/claude-3-haiku",
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
            timeout=30
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
                return parsed
            except (json.JSONDecodeError, ValueError, TypeError):
                return None
        
        return None
    except Exception:
        return None


def get_watch_retail_price(
    watch_info: WatchInfo,
    env: dict[str, str],
    use_watchcharts: bool = False
) -> Optional[float]:
    """
    Get retail price (MSRP) for a watch from the best available source.
    
    Priority order:
    1. WatchCharts API (if available and enabled)
    2. WatchCharts scraping (free alternative)
    3. AI price lookup (fallback)
    
    Args:
        watch_info: WatchInfo dictionary with watch metadata
        env: Environment variables dict
        use_watchcharts: Whether to try WatchCharts API if available
    
    Returns:
        Retail price as float, or None if not found
    """
    # Method 1: WatchCharts API (optional, if API key available)
    if use_watchcharts:
        watchcharts_key = env.get("WATCHCHARTS_API_KEY")
        if watchcharts_key:
            try:
                retail_price = get_watchcharts_retail_price(watch_info, watchcharts_key)
                if retail_price:
                    return retail_price
            except Exception as e:
                print(f"  Warning: WatchCharts retail price API lookup failed: {e}")
    
    # Method 2: WatchCharts web scraping (free, always try)
    try:
        scraped_retail = scrape_watchcharts_retail_price(watch_info)
        if scraped_retail:
            return scraped_retail
    except Exception as e:
        print(f"  Warning: WatchCharts retail price scraping failed: {e}")
    
    # Method 3: AI price lookup (fallback)
    openrouter_key = env.get("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            ai_retail = get_watch_retail_price_ai(watch_info, openrouter_key)
            if ai_retail:
                return ai_retail
        except Exception as e:
            print(f"  Warning: AI retail price lookup failed: {e}")
    
    return None


def get_watchcharts_retail_price(
    watch_info: WatchInfo,
    api_key: str,
    currency: str = "USD"
) -> Optional[float]:
    """
    Get watch retail price (MSRP) from WatchCharts API.
    
    Note: Requires WatchCharts API subscription (Level 2 access for retail endpoint).
    API documentation: https://watchcharts.com/api
    
    Args:
        watch_info: WatchInfo dictionary with watch metadata
        api_key: WatchCharts API key (sent as X-Api-Key header)
        currency: Currency code (default: USD)
    
    Returns:
        Retail price as float, or None if not found
    """
    base_url = "https://api.watchcharts.com/v3"
    headers = {
        "X-Api-Key": api_key,
    }
    
    # Step 1: Search for watch by brand and reference number
    brand_name = watch_info.get("brand")
    reference = watch_info.get("model_number") or watch_info.get("model")
    
    if not brand_name or not reference:
        return None
    
    # Search for the watch
    search_url = f"{base_url}/search/watch"
    search_params = {
        "brand_name": brand_name,
        "reference": reference,
        "exact_match": "false"
    }
    
    try:
        # Search for watch UUID
        search_response = requests.get(
            search_url,
            headers=headers,
            params=search_params,
            timeout=30
        )
        
        if search_response.status_code != 200:
            return None
        
        search_data = search_response.json()
        
        if not search_data.get("success") or not search_data.get("results"):
            return None
        
        results = search_data.get("results", [])
        if not results:
            return None
        
        watch_uuid = results[0].get("uuid")
        if not watch_uuid:
            return None
        
        # Step 2: Get retail price
        retail_url = f"{base_url}/watch/retail"
        retail_params = {
            "uuid": watch_uuid,
            "currency": currency
        }
        
        retail_response = requests.get(
            retail_url,
            headers=headers,
            params=retail_params,
            timeout=30
        )
        
        if retail_response.status_code != 200:
            return None
        
        retail_data = retail_response.json()
        
        # Extract retail price from PriceRetail response
        retail_price = retail_data.get("value")
        if retail_price is not None:
            return float(retail_price)
        
        return None
        
    except Exception as e:
        print(f"  WatchCharts retail API error: {e}")
        return None


def scrape_watchcharts_retail_price(
    watch_info: WatchInfo
) -> Optional[float]:
    """
    Scrape watch retail price (MSRP) from WatchCharts website.
    
    Args:
        watch_info: WatchInfo dictionary with watch metadata
    
    Returns:
        Retail price as float, or None if not found
    """
    # First, get the watch page URL
    watch_url = get_watchcharts_url(watch_info)
    if not watch_url or '/watch_model/' not in watch_url:
        # If we don't have a direct watch page, try to find it
        brand = watch_info.get("brand")
        model = watch_info.get("model_number") or watch_info.get("model")
        
        if not brand or not model:
            return None
        
        # Try to search and find the watch page
        from urllib.parse import quote_plus
        search_query = f"{brand} {model}"
        encoded = quote_plus(search_query)
        search_url = f"https://watchcharts.com/watches?search={encoded}"
        
        scraper = cloudscraper.create_scraper()
        scraper.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        
        try:
            response = scraper.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=True)
                
                # Use same strict matching logic as get_watchcharts_url
                model_number = watch_info.get("model_number")
                model_name = watch_info.get("model")
                model = model_number or model_name
                
                if model:
                    model_num_clean = model_number.replace(' ', '').replace('-', '').lower() if model_number else None
                    
                    for link in links:
                        href = link.get('href', '')
                        if '/watch_model/' in href:
                            link_text = link.get_text().strip().lower()
                            href_lower = href.lower()
                            
                            # Strict matching: require exact model number if available
                            if model_number:
                                href_clean = href_lower.replace('-', '').replace('_', '')
                                if model_num_clean not in href_clean and model_number.lower() not in href_lower:
                                    continue  # Must match model number
                                if model_number.lower() not in link_text and model_num_clean not in link_text.replace('-', '').replace(' ', ''):
                                    continue  # Must also be in link text
                            
                            brand_match = brand.lower() in href_lower
                            model_match = model.lower() in href_lower or model in href
                            
                            if brand_match and model_match:
                                if href.startswith('/'):
                                    watch_url = f"https://watchcharts.com{href}/overview"
                                elif href.startswith('http'):
                                    watch_url = f"{href}/overview" if '/overview' not in href else href
                                break
        except Exception:
            pass
    
    if not watch_url or '/watch_model/' not in watch_url:
        return None
    
    # Scrape the watch page for retail price
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    
    try:
        response = scraper.get(watch_url, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            
            # Look for retail price patterns
            retail_patterns = [
                r'Retail\s+Price[:\s]*\$?([\d,]+\.?\d*)',
                r'MSRP[:\s]*\$?([\d,]+\.?\d*)',
                r'Retail[:\s]*\$?([\d,]+\.?\d*)',
                r'List\s+Price[:\s]*\$?([\d,]+\.?\d*)',
                r'Suggested\s+Retail[:\s]*\$?([\d,]+\.?\d*)',
            ]
            
            for pattern in retail_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        value_str = match.group(1).replace(',', '')
                        price = float(value_str)
                        if 100 <= price <= 1000000:  # Reasonable range
                            return price
                    except (ValueError, AttributeError):
                        continue
            
            # Also check for JSON data
            for script in soup.find_all('script'):
                if script.string:
                    script_text = script.string
                    json_patterns = [
                        r'"retail_price"\s*:\s*([\d,]+\.?\d*)',
                        r'"retailPrice"\s*:\s*([\d,]+\.?\d*)',
                        r'"msrp"\s*:\s*([\d,]+\.?\d*)',
                        r'"list_price"\s*:\s*([\d,]+\.?\d*)',
                    ]
                    
                    for pattern in json_patterns:
                        match = re.search(pattern, script_text, re.IGNORECASE)
                        if match:
                            try:
                                value_str = match.group(1).replace(',', '')
                                price = float(value_str)
                                if 100 <= price <= 1000000:
                                    return price
                            except (ValueError, AttributeError):
                                continue
        
        return None
    except Exception:
        return None


def get_watch_retail_price_ai(
    watch_info: WatchInfo,
    openrouter_api_key: str
) -> Optional[float]:
    """
    Use AI to search for watch retail/MSRP price.
    
    Args:
        watch_info: WatchInfo dictionary with watch metadata
        openrouter_api_key: OpenRouter API key
    
    Returns:
        Retail price as float, or None if not found
    """
    # Build description from watch info
    desc_parts = []
    if watch_info.get("brand"):
        desc_parts.append(f"Brand: {watch_info['brand']}")
    if watch_info.get("model"):
        desc_parts.append(f"Model: {watch_info['model']}")
    if watch_info.get("model_number"):
        desc_parts.append(f"Model Number: {watch_info['model_number']}")
    
    watch_description = "\n".join(desc_parts) if desc_parts else watch_info.get("title", "")
    
    prompt = f"""Find the retail price (MSRP) for this watch:

{watch_description}

Search official brand websites (like rolex.com, omega.com) or authorized dealers to find the current retail/MSRP price for this watch.

Return ONLY a JSON object with this format:
{{
  "retail_price": 10800.00,
  "currency": "USD",
  "source": "rolex.com"
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
        "model": "anthropic/claude-3-haiku",
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


def get_watch_reference_price(
    watch_info: WatchInfo,
    env: dict[str, str],
    use_watchcharts: bool = False
) -> Optional[float]:
    """
    Get reference price for a watch from the best available source.
    
    Priority order:
    1. eBay sold listings (primary)
    2. WatchCharts scraping (free alternative to API)
    3. WatchCharts API (if available and enabled)
    4. AI price lookup (fallback)
    
    Args:
        watch_info: WatchInfo dictionary with watch metadata
        env: Environment variables dict
        use_watchcharts: Whether to try WatchCharts API if available (scraping is always tried)
    
    Returns:
        Reference price as float, or None if not found
    """
    # Method 1: eBay sold listings (primary)
    try:
        market_price = get_market_price_from_sold_listings(watch_info, env)
        if market_price:
            return market_price
    except Exception as e:
        print(f"  Warning: eBay sold listings search failed: {e}")
    
    # Method 2: WatchCharts web scraping (free, always try)
    try:
        scraped_price = scrape_watchcharts_price(watch_info)
        if scraped_price:
            return scraped_price
    except Exception as e:
        print(f"  Warning: WatchCharts scraping failed: {e}")
    
    # Method 3: WatchCharts API (optional, if API key available)
    if use_watchcharts:
        watchcharts_key = env.get("WATCHCHARTS_API_KEY")
        if watchcharts_key:
            try:
                watchcharts_price = get_watchcharts_price(watch_info, watchcharts_key)
                if watchcharts_price:
                    return watchcharts_price
            except Exception as e:
                print(f"  Warning: WatchCharts API lookup failed: {e}")
    
    # Method 4: AI price lookup (fallback)
    openrouter_key = env.get("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            ai_price = get_watch_price_ai(watch_info, openrouter_key)
            if ai_price:
                return ai_price
        except Exception as e:
            print(f"  Warning: AI price lookup failed: {e}")
    
    return None


def scrape_watchcharts_price(
    watch_info: WatchInfo
) -> Optional[float]:
    """
    Scrape watch market price from WatchCharts website (free alternative to API).
    
    Args:
        watch_info: WatchInfo dictionary with watch metadata
    
    Returns:
        Market price as float, or None if not found
    """
    brand = watch_info.get("brand")
    model = watch_info.get("model_number") or watch_info.get("model")
    
    if not brand or not model:
        return None
    
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://watchcharts.com/",
    })
    
    # Method 1: Try to search for the watch first
    search_url = "https://watchcharts.com/search"
    search_params = {
        "q": f"{brand} {model}",
    }
    
    try:
        # Try search first
        search_response = scraper.get(search_url, params=search_params, timeout=30)
        if search_response.status_code == 200:
            soup = BeautifulSoup(search_response.text, 'html.parser')
            
            # Look for watch links in search results
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if '/watch/' in href or '/model/' in href:
                    # Found a watch page link
                    if href.startswith('/'):
                        watch_url = f"https://watchcharts.com{href}"
                    elif href.startswith('http'):
                        watch_url = href
                    else:
                        continue
                    
                    price = _scrape_price_from_watch_page(scraper, watch_url)
                    if price:
                        return price
    except Exception:
        pass  # Continue to direct URL attempts
    
    # Method 2: Try direct URL patterns
    # WatchCharts URL patterns
    brand_slug = brand.lower().replace(' ', '-').replace("'", "")
    model_slug = model.lower().replace(' ', '-').replace("'", "")
    
    base_urls = [
        f"https://watchcharts.com/watch/{brand_slug}/{model_slug}",
        f"https://www.watchcharts.com/watch/{brand_slug}/{model_slug}",
        f"https://watchcharts.com/{brand_slug}/{model_slug}",
        f"https://watchcharts.com/model/{brand_slug}/{model_slug}",
    ]
    
    for url in base_urls:
        price = _scrape_price_from_watch_page(scraper, url)
        if price:
            return price
    
    return None


def _scrape_price_from_watch_page(
    scraper: cloudscraper.CloudScraper,
    url: str
) -> Optional[float]:
    """
    Scrape price from a specific WatchCharts watch page.
    
    Args:
        scraper: CloudScraper instance
        url: URL of the watch page
    
    Returns:
        Market price as float, or None if not found
    """
    try:
        response = scraper.get(url, timeout=30)
        if response.status_code != 200:
            return None
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Method 1: Look for market price in text patterns
        text = soup.get_text()
        
        # Common patterns for market price
        price_patterns = [
            r'Market\s+Price[:\s]*\$?([\d,]+\.?\d*)',
            r'Market\s+Value[:\s]*\$?([\d,]+\.?\d*)',
            r'Current\s+Price[:\s]*\$?([\d,]+\.?\d*)',
            r'Average\s+Price[:\s]*\$?([\d,]+\.?\d*)',
            r'Price\s+Index[:\s]*\$?([\d,]+\.?\d*)',
            r'\$([\d,]+\.?\d*)\s*\(Market\)',
            r'\$([\d,]+\.?\d*)\s*Market',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value_str = match.group(1).replace(',', '')
                    price = float(value_str)
                    if 100 <= price <= 1000000:  # Reasonable price range
                        return price
                except (ValueError, AttributeError):
                    continue
        
        # Method 2: Look for price in data attributes or JSON
        # Check for script tags with JSON data
        for script in soup.find_all('script'):
            if script.string:
                script_text = script.string
                
                # Look for market_price or price in JSON
                json_patterns = [
                    r'"market_price"\s*:\s*([\d,]+\.?\d*)',
                    r'"marketPrice"\s*:\s*([\d,]+\.?\d*)',
                    r'"price"\s*:\s*([\d,]+\.?\d*)',
                    r'"currentPrice"\s*:\s*([\d,]+\.?\d*)',
                    r'"averagePrice"\s*:\s*([\d,]+\.?\d*)',
                ]
                
                for pattern in json_patterns:
                    match = re.search(pattern, script_text, re.IGNORECASE)
                    if match:
                        try:
                            value_str = match.group(1).replace(',', '')
                            price = float(value_str)
                            if 100 <= price <= 1000000:  # Reasonable price range
                                return price
                        except (ValueError, AttributeError):
                            continue
        
        # Method 3: Look for price in specific HTML elements
        # Common class names that might contain price
        price_selectors = [
            '[class*="price"]',
            '[class*="market"]',
            '[data-price]',
            '[data-market-price]',
            '[id*="price"]',
        ]
        
        for selector in price_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text_elem = elem.get_text()
                    # Look for dollar amount
                    price_match = re.search(r'\$([\d,]+\.?\d*)', text_elem)
                    if price_match:
                        try:
                            value_str = price_match.group(1).replace(',', '')
                            price = float(value_str)
                            if 100 <= price <= 1000000:  # Reasonable price range
                                # Check if it's likely a market price (not retail)
                                elem_text_lower = text_elem.lower()
                                if any(keyword in elem_text_lower for keyword in ['market', 'current', 'average', 'index']):
                                    return price
                        except ValueError:
                            continue
            except Exception:
                continue
        
        # Method 4: Search page for large dollar amounts (likely market price)
        # Find all dollar amounts and take the one that's most likely the market price
        all_prices = re.findall(r'\$([\d,]+\.?\d*)', text)
        if all_prices:
            # Filter reasonable prices and take the middle/higher range (market price is usually higher than retail)
            prices = []
            for price_str in all_prices:
                try:
                    price = float(price_str.replace(',', ''))
                    if 100 <= price <= 1000000:
                        prices.append(price)
                except ValueError:
                    continue
            
            if prices:
                # If multiple prices, market price is often the highest or second highest
                prices_sorted = sorted(prices, reverse=True)
                # Return the highest price (likely market price)
                return prices_sorted[0]
        
        return None
        
    except Exception:
        return None
    
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://watchcharts.com/",
    })
    
    for url in base_urls:
        try:
            response = scraper.get(url, timeout=30)
            if response.status_code != 200:
                continue
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: Look for market price in text patterns
            text = soup.get_text()
            
            # Common patterns for market price
            price_patterns = [
                r'Market\s+Price[:\s]*\$?([\d,]+\.?\d*)',
                r'Market\s+Value[:\s]*\$?([\d,]+\.?\d*)',
                r'Current\s+Price[:\s]*\$?([\d,]+\.?\d*)',
                r'Average\s+Price[:\s]*\$?([\d,]+\.?\d*)',
                r'\$([\d,]+\.?\d*)\s*\(Market\)',
                r'\$([\d,]+\.?\d*)\s*Market',
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        value_str = match.group(1).replace(',', '')
                        price = float(value_str)
                        if 100 <= price <= 1000000:  # Reasonable price range
                            return price
                    except (ValueError, AttributeError):
                        continue
            
            # Method 2: Look for price in data attributes or JSON
            # Check for script tags with JSON data
            for script in soup.find_all('script'):
                if script.string:
                    script_text = script.string
                    
                    # Look for market_price or price in JSON
                    json_patterns = [
                        r'"market_price"\s*:\s*([\d,]+\.?\d*)',
                        r'"marketPrice"\s*:\s*([\d,]+\.?\d*)',
                        r'"price"\s*:\s*([\d,]+\.?\d*)',
                        r'"currentPrice"\s*:\s*([\d,]+\.?\d*)',
                    ]
                    
                    for pattern in json_patterns:
                        match = re.search(pattern, script_text, re.IGNORECASE)
                        if match:
                            try:
                                value_str = match.group(1).replace(',', '')
                                price = float(value_str)
                                if 100 <= price <= 1000000:  # Reasonable price range
                                    return price
                            except (ValueError, AttributeError):
                                continue
            
            # Method 3: Look for price in specific HTML elements
            # Common class names that might contain price
            price_selectors = [
                '[class*="price"]',
                '[class*="market"]',
                '[data-price]',
                '[data-market-price]',
            ]
            
            for selector in price_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text_elem = elem.get_text()
                    # Look for dollar amount
                    price_match = re.search(r'\$([\d,]+\.?\d*)', text_elem)
                    if price_match:
                        try:
                            value_str = price_match.group(1).replace(',', '')
                            price = float(value_str)
                            if 100 <= price <= 1000000:  # Reasonable price range
                                # Check if it's likely a market price (not retail)
                                if 'market' in text_elem.lower() or 'current' in text_elem.lower():
                                    return price
                        except ValueError:
                            continue
            
            # Method 4: Search page for large dollar amounts (likely market price)
            # Find all dollar amounts and take the one that's most likely the market price
            all_prices = re.findall(r'\$([\d,]+\.?\d*)', text)
            if all_prices:
                # Filter reasonable prices and take the middle/higher range (market price is usually higher than retail)
                prices = []
                for price_str in all_prices:
                    try:
                        price = float(price_str.replace(',', ''))
                        if 100 <= price <= 1000000:
                            prices.append(price)
                    except ValueError:
                        continue
                
                if prices:
                    # If multiple prices, market price is often the highest or second highest
                    prices_sorted = sorted(prices, reverse=True)
                    # Return the highest price (likely market price)
                    return prices_sorted[0]
            
            # If we found the page but no price, try next URL format
            continue
            
        except Exception as e:
            # Try next URL format
            continue
    
    return None


def get_watchcharts_price(
    watch_info: WatchInfo,
    api_key: str,
    currency: str = "USD"
) -> Optional[float]:
    """
    Get watch market price from WatchCharts API.
    
    Note: Requires WatchCharts API subscription (Level 1 or higher).
    API documentation: https://watchcharts.com/api
    
    Args:
        watch_info: WatchInfo dictionary with watch metadata
        api_key: WatchCharts API key (sent as X-Api-Key header)
        currency: Currency code (default: USD)
    
    Returns:
        Market price as float, or None if not found
    """
    base_url = "https://api.watchcharts.com/v3"
    headers = {
        "X-Api-Key": api_key,
    }
    
    # Step 1: Search for watch by brand and reference number
    brand_name = watch_info.get("brand")
    reference = watch_info.get("model_number") or watch_info.get("model")
    
    if not brand_name or not reference:
        return None
    
    # Search for the watch
    search_url = f"{base_url}/search/watch"
    search_params = {
        "brand_name": brand_name,
        "reference": reference,
        "exact_match": "false"  # Allow partial matches
    }
    
    try:
        # Search for watch UUID
        search_response = requests.get(
            search_url,
            headers=headers,
            params=search_params,
            timeout=30
        )
        
        if search_response.status_code != 200:
            return None
        
        search_data = search_response.json()
        
        # Check if search was successful and has results
        if not search_data.get("success") or not search_data.get("results"):
            return None
        
        # Get the first result's UUID
        results = search_data.get("results", [])
        if not results:
            return None
        
        watch_uuid = results[0].get("uuid")
        if not watch_uuid:
            return None
        
        # Step 2: Get watch info with market price
        info_url = f"{base_url}/watch/info"
        info_params = {
            "uuid": watch_uuid,
            "currency": currency
        }
        
        info_response = requests.get(
            info_url,
            headers=headers,
            params=info_params,
            timeout=30
        )
        
        if info_response.status_code != 200:
            return None
        
        info_data = info_response.json()
        
        # Extract market price from WatchInfo response
        market_price = info_data.get("market_price")
        if market_price is not None:
            return float(market_price)
        
        return None
        
    except Exception as e:
        print(f"  WatchCharts API error: {e}")
        return None


def get_watch_price_ai(
    watch_info: WatchInfo,
    openrouter_api_key: str
) -> Optional[float]:
    """
    Use AI to search for watch market price.
    
    Args:
        watch_info: WatchInfo dictionary with watch metadata
        openrouter_api_key: OpenRouter API key
    
    Returns:
        Market price as float, or None if not found
    """
    # Build description from watch info
    desc_parts = []
    if watch_info.get("brand"):
        desc_parts.append(f"Brand: {watch_info['brand']}")
    if watch_info.get("model"):
        desc_parts.append(f"Model: {watch_info['model']}")
    if watch_info.get("model_number"):
        desc_parts.append(f"Model Number: {watch_info['model_number']}")
    if watch_info.get("year"):
        desc_parts.append(f"Year: {watch_info['year']}")
    if watch_info.get("condition"):
        desc_parts.append(f"Condition: {watch_info['condition']}")
    
    watch_description = "\n".join(desc_parts) if desc_parts else watch_info.get("title", "")
    
    prompt = f"""Find the current market price for this watch:

{watch_description}

Search eBay sold listings, Chrono24, and other watch marketplaces to find the average selling price for this watch in similar condition.

Return ONLY a JSON object with this format:
{{
  "market_price": 8500.00,
  "currency": "USD",
  "source": "eBay sold listings average"
}}

If you cannot find the market price, return:
{{
  "market_price": null,
  "currency": null,
  "source": null
}}

Return ONLY the JSON, nothing else."""

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "anthropic/claude-3-haiku",
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
                market_price = parsed.get("market_price")
                
                if market_price:
                    return float(market_price)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        return None
    except Exception:
        return None

