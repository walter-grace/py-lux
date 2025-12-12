#!/usr/bin/env python3
"""
Deep Research Agent for PSA Card Pricing
- Scrapes PSA cert pages for EstimatedValue
- Uses OpenRouter AI for deep research
- Finds arbitrage opportunities
- Searches eBay and analyzes listings
"""

import re
import json
import time
import base64
import os
from typing import Optional, Dict, Any, List
import requests
import cloudscraper
from bs4 import BeautifulSoup


def scrape_psa_estimate_from_ebay(ebay_url: str) -> Optional[float]:
    """
    Scrape PSA Estimated Value from eBay listing's "See all" PSA data section.
    eBay loads this data dynamically, so we need to look for it in the page's JavaScript/JSON.
    
    Args:
        ebay_url: eBay listing URL
        
    Returns:
        Estimated value as float, or None if not found
    """
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    
    try:
        response = scraper.get(ebay_url, timeout=30)
        if response.status_code != 200:
            return None
        
        html_content = response.text
        
        # Method 1: Look for PSA data in embedded JSON/JavaScript
        # eBay often embeds data in window.__INITIAL_STATE__ or similar
        json_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
            r'var\s+__INITIAL_STATE__\s*=\s*({.+?});',
            r'"psaData"[:\s]*({.+?})',
            r'"psa"[:\s]*({.+?})',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    data = json.loads(match)
                    # Recursively search for estimated value
                    estimate = find_estimated_value_in_dict(data)
                    if estimate:
                        return estimate
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # Method 2: Look for PSA data in script tags with specific patterns
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup.find_all('script'):
            if not script.string:
                continue
                
            script_text = script.string
            
            # Look for PSA-related JSON objects
            if 'psa' in script_text.lower():
                # Try to find estimated value patterns
                estimate_patterns = [
                    r'"estimatedValue"[:\s]*([\d,]+\.?\d*)',
                    r'"estimated_value"[:\s]*([\d,]+\.?\d*)',
                    r'"estimate"[:\s]*([\d,]+\.?\d*)',
                    r'"psaEstimate"[:\s]*([\d,]+\.?\d*)',
                    r'estimatedValue["\']?\s*[:=]\s*["\']?([\d,]+\.?\d*)',
                ]
                
                for pattern in estimate_patterns:
                    matches = re.findall(pattern, script_text, re.IGNORECASE)
                    for match in matches:
                        try:
                            value_str = match.replace(',', '')
                            value = float(value_str)
                            if value > 0:
                                return value
                        except (ValueError, AttributeError):
                            continue
                
                # Try to extract full JSON objects
                json_matches = re.findall(r'\{[^{}]*"estimatedValue"[^{}]*\}', script_text, re.IGNORECASE | re.DOTALL)
                for json_str in json_matches:
                    try:
                        data = json.loads(json_str)
                        if 'estimatedValue' in data:
                            value = float(str(data['estimatedValue']).replace(',', ''))
                            if value > 0:
                                return value
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
        
        # Method 3: Look for text patterns in the HTML (might be in hidden divs)
        text = soup.get_text()
        estimate_patterns = [
            r'PSA\s+Estimate[:\s]*\$?([\d,]+\.?\d*)',
            r'Estimated\s+Value[:\s]*\$?([\d,]+\.?\d*)',
            r'Est\.\s+Value[:\s]*\$?([\d,]+\.?\d*)',
            r'\$([\d,]+\.?\d*)\s*\(PSA\s+Estimate\)',
            r'Estimated\s+Market\s+Value[:\s]*\$?([\d,]+\.?\d*)',
        ]
        
        for pattern in estimate_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value_str = match.group(1).replace(',', '')
                    value = float(value_str)
                    if value > 0:
                        return value
                except (ValueError, AttributeError):
                    continue
        
        # Method 4: Look for data attributes in HTML elements
        for elem in soup.find_all(['div', 'span', 'td', 'th', 'p'], attrs={'data-psa-estimate': True}):
            try:
                value = float(elem.get('data-psa-estimate', '').replace(',', ''))
                if value > 0:
                    return value
            except (ValueError, AttributeError):
                continue
        
        return None
        
    except Exception as e:
        # Silently fail - we'll fall back to PSA website scraping
        return None


def find_estimated_value_in_dict(data: dict, depth: int = 0) -> Optional[float]:
    """
    Recursively search a dictionary for estimated value fields.
    
    Args:
        data: Dictionary to search
        depth: Current recursion depth (max 5 to avoid infinite loops)
        
    Returns:
        Estimated value as float, or None if not found
    """
    if depth > 5:  # Prevent infinite recursion
        return None
    
    if not isinstance(data, dict):
        return None
    
    # Check common keys
    for key in ['estimatedValue', 'estimated_value', 'estimate', 'psaEstimate', 'psa_estimate', 'estimatedMarketValue']:
        if key in data:
            try:
                value = data[key]
                if isinstance(value, (int, float)):
                    if value > 0:
                        return float(value)
                elif isinstance(value, str):
                    value_str = value.replace(',', '').replace('$', '')
                    value_float = float(value_str)
                    if value_float > 0:
                        return value_float
            except (ValueError, TypeError):
                continue
    
    # Recursively search nested dictionaries
    for value in data.values():
        if isinstance(value, dict):
            result = find_estimated_value_in_dict(value, depth + 1)
            if result:
                return result
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    result = find_estimated_value_in_dict(item, depth + 1)
                    if result:
                        return result
    
    return None


def scrape_psa_estimate(cert_number: str, ebay_url: Optional[str] = None) -> Optional[float]:
    """
    Scrape PSA cert page to find EstimatedValue.
    Tries eBay first (if URL provided), then falls back to PSA website.
    
    Args:
        cert_number: PSA certification number
        ebay_url: Optional eBay listing URL to try first
        
    Returns:
        Estimated value as float, or None if not found
    """
    # Method 1: Try eBay listing first (more reliable)
    if ebay_url:
        estimate = scrape_psa_estimate_from_ebay(ebay_url)
        if estimate:
            return estimate
    
    # Method 2: Fall back to PSA website
    url = f"https://www.psacard.com/cert/{cert_number}/psa"
    
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    
    try:
        response = scraper.get(url, timeout=30)
        if response.status_code != 200:
            return None
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for PSA Estimate in various formats
        # Common patterns: "$1,205.93", "PSA Estimate: $1,205.93", etc.
        text = soup.get_text()
        
        # Pattern 1: Look for "PSA Estimate" followed by price
        estimate_patterns = [
            r'PSA\s+Estimate[:\s]*\$?([\d,]+\.?\d*)',
            r'Estimated\s+Value[:\s]*\$?([\d,]+\.?\d*)',
            r'Est\.\s+Value[:\s]*\$?([\d,]+\.?\d*)',
            r'\$([\d,]+\.?\d*)\s*\(PSA\s+Estimate\)',
        ]
        
        for pattern in estimate_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value_str = match.group(1).replace(',', '')
                    return float(value_str)
                except (ValueError, AttributeError):
                    continue
        
        # Pattern 2: Look for price in specific HTML elements
        # Check for data attributes or specific classes
        for elem in soup.find_all(['span', 'div', 'td', 'th']):
            text_elem = elem.get_text()
            if 'estimate' in text_elem.lower() or 'est. value' in text_elem.lower():
                # Look for price in nearby elements
                price_match = re.search(r'\$([\d,]+\.?\d*)', text_elem)
                if price_match:
                    try:
                        value_str = price_match.group(1).replace(',', '')
                        return float(value_str)
                    except ValueError:
                        continue
        
        # Pattern 3: Look for JSON data in script tags
        for script in soup.find_all('script'):
            if script.string and 'estimate' in script.string.lower():
                # Try to extract JSON
                json_match = re.search(r'\{[^}]*estimate[^}]*\}', script.string, re.IGNORECASE)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                        if 'estimate' in data or 'estimatedValue' in data:
                            value = data.get('estimate') or data.get('estimatedValue')
                            if value:
                                return float(str(value).replace(',', ''))
                    except (json.JSONDecodeError, ValueError, AttributeError):
                        continue
        
        return None
        
    except Exception as e:
        print(f"Error scraping PSA estimate for cert {cert_number}: {e}")
        return None


def search_ebay_listings(
    card_name: str,
    year: Optional[str] = None,
    grade: str = "10",
    edition: str = "1st Edition",
    ebay_oauth: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search eBay for similar cards to find pricing data.
    
    Args:
        card_name: Name of the card (e.g., "GATE GUARDIAN")
        year: Year of the card
        grade: PSA grade (default: "10")
        edition: Edition (default: "1st Edition")
        ebay_oauth: Optional eBay OAuth token for API access
        
    Returns:
        Dictionary with eBay search results
    """
    results = {
        "active_listings": [],
        "sold_listings": [],
        "average_price": None,
        "min_price": None,
        "max_price": None,
    }
    
    if not ebay_oauth:
        return results
    
    # Build search query
    query_parts = [card_name, f"PSA {grade}"]
    if edition:
        query_parts.append(edition)
    if year:
        query_parts.append(year)
    
    query = " ".join(query_parts)
    
    try:
        import requests
        
        # Search for active listings (Buy It Now)
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
        headers = {"Authorization": f"Bearer {ebay_oauth}"}
        
        params = {
            "q": query,
            "category_ids": "183454",  # CCG individual cards
            "limit": "20",
            "filter": "buyingOptions:{FIXED_PRICE}",
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("itemSummaries", []):
                price_obj = item.get("price", {})
                if price_obj.get("currency") == "USD":
                    price = float(price_obj.get("value", 0))
                    results["active_listings"].append({
                        "title": item.get("title", ""),
                        "price": price,
                        "url": item.get("itemWebUrl", ""),
                        "shipping": float(item.get("shippingOptions", [{}])[0].get("shippingCost", {}).get("value", 0)),
                    })
        
        # Note: Sold listings require a different endpoint or web scraping
        # For now, we'll use active listings as a proxy
        
        if results["active_listings"]:
            prices = [item["price"] for item in results["active_listings"]]
            results["average_price"] = sum(prices) / len(prices)
            results["min_price"] = min(prices)
            results["max_price"] = max(prices)
            
    except Exception as e:
        print(f"Error searching eBay: {e}")
    
    return results


def deep_research_pricing(
    cert_number: str,
    card_info: Dict[str, Any],
    openrouter_api_key: str,
    ebay_oauth: Optional[str] = None,
    site_url: Optional[str] = None,
    site_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Use OpenRouter deep research model to find card pricing and arbitrage opportunities.
    
    Args:
        cert_number: PSA certification number
        card_info: Dictionary with card details (year, brand, subject, grade, etc.)
        openrouter_api_key: OpenRouter API key
        site_url: Optional site URL for OpenRouter rankings
        site_name: Optional site name for OpenRouter rankings
        
    Returns:
        Dictionary with research results including pricing and arbitrage opportunities
    """
    if not openrouter_api_key:
        return None
    
    # Build research prompt
    card_description = f"""
    PSA Certification: {cert_number}
    Year: {card_info.get('year', 'N/A')}
    Brand: {card_info.get('brand', 'N/A')}
    Card: {card_info.get('player', 'N/A')} ({card_info.get('card_no', 'N/A')})
    Grade: {card_info.get('grade', 'N/A')}
    """
    
    # First, search eBay programmatically
    ebay_results = search_ebay_listings(
        card_name=card_info.get("player", ""),
        year=card_info.get("year"),
        grade=card_info.get("grade", "10"),
        edition="1st Edition",
        ebay_oauth=ebay_oauth
    )
    
    ebay_summary = ""
    if ebay_results["active_listings"]:
        ebay_summary = f"""
eBay Active Listings Found: {len(ebay_results['active_listings'])}
- Average Price: ${ebay_results.get('average_price', 0):,.2f}
- Price Range: ${ebay_results.get('min_price', 0):,.2f} - ${ebay_results.get('max_price', 0):,.2f}
"""
    
    prompt = f"""Research the current market value and pricing for this PSA-graded card:

{card_description}

eBay Search Results:
{ebay_summary if ebay_summary else "No eBay listings found programmatically"}

Please find:
1. Current PSA Estimated Value (check PSA website: https://www.psacard.com/cert/{cert_number}/psa)
2. Recent eBay sold listings for similar cards (same card, same grade) - use the eBay search results above
3. Current eBay active listings (Buy It Now prices) - use the eBay search results above
4. Market trends and arbitrage opportunities
5. Compare PSA Estimate vs eBay prices to identify arbitrage

Provide a detailed analysis with specific prices and sources."""

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }
    
    if site_url:
        headers["HTTP-Referer"] = site_url
    if site_name:
        headers["X-Title"] = site_name
    
    data = {
        "model": "openai/o4-mini-deep-research",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=120  # Deep research may take longer
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Try to extract pricing information from the response
            pricing_info = {
                "research_summary": content,
                "psa_estimate": None,
                "ebay_sold_prices": [],
                "ebay_active_listings": [],
                "arbitrage_opportunities": [],
            }
            
            # Extract PSA Estimate from research
            psa_match = re.search(r'PSA\s+Estimate[:\s]*\$?([\d,]+\.?\d*)', content, re.IGNORECASE)
            if psa_match:
                try:
                    pricing_info["psa_estimate"] = float(psa_match.group(1).replace(',', ''))
                except ValueError:
                    pass
            
            # Extract eBay prices from AI response
            ebay_matches = re.findall(r'eBay[:\s]*\$?([\d,]+\.?\d*)', content, re.IGNORECASE)
            for match in ebay_matches:
                try:
                    pricing_info["ebay_sold_prices"].append(float(match.replace(',', '')))
                except ValueError:
                    continue
            
            # Add programmatic eBay search results
            pricing_info["ebay_search_results"] = ebay_results
            if ebay_results.get("average_price"):
                pricing_info["ebay_average_price"] = ebay_results["average_price"]
                pricing_info["ebay_price_range"] = {
                    "min": ebay_results.get("min_price"),
                    "max": ebay_results.get("max_price"),
                }
            
            return pricing_info
        else:
            print(f"OpenRouter API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error in deep research: {e}")
        return None


def ai_search_ebay_listings(
    openrouter_api_key: str,
    search_query: str = "yugioh psa 10 1st edition buy it now",
    limit: int = 50,
    site_url: Optional[str] = None,
    site_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Use AI to search eBay and extract card listings with cert numbers.
    
    Args:
        openrouter_api_key: OpenRouter API key
        search_query: Search query for eBay
        limit: Maximum number of listings to find
        site_url: Optional site URL for OpenRouter
        site_name: Optional site name for OpenRouter
        
    Returns:
        List of card listings with cert numbers, titles, prices, etc.
    """
    if not openrouter_api_key:
        return []
    
    prompt = f"""Find {limit} eBay listings for "{search_query}". Extract PSA cert numbers (7-9 digits) and prices.

Return JSON:
{{
  "listings": [
    {{"cert_number": "12345678", "price": 500, "title": "Card title"}}
  ]
}}

Only PSA 10, 1st Edition, Buy It Now. Return JSON only."""

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }
    
    if site_url:
        headers["HTTP-Referer"] = site_url
    if site_name:
        headers["X-Title"] = site_name
    
    # Try a model better suited for structured output
    # o4-mini-deep-research may not output content properly, try gpt-4o-mini instead
    data = {
        "model": "openai/gpt-4o-mini",  # Better for structured JSON output
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 500,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=180  # Deep research may take longer
        )
        
        if response.status_code == 200:
            result = response.json()
            message = result.get("choices", [{}])[0].get("message", {})
            content = message.get("content", "")
            reasoning = message.get("reasoning", "")
            
            # o4-mini-deep-research may put output in reasoning field
            if not content and reasoning:
                content = reasoning
            
            # Try to parse JSON response
            try:
                # Clean up content - remove markdown code blocks, whitespace
                content = re.sub(r'```json\s*', '', content)
                content = re.sub(r'```\s*$', '', content)
                content = re.sub(r'^```\s*', '', content)
                content = content.strip()
                
                # Try to extract JSON object if wrapped in text
                json_match = re.search(r'\{[^{}]*"listings"[^{}]*\[.*?\]\s*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                
                parsed = json.loads(content)
                
                # Handle different response formats
                if isinstance(parsed, dict):
                    # Might be {"listings": [...]} or {"results": [...]}
                    listings = parsed.get("listings", parsed.get("results", parsed.get("items", [])))
                elif isinstance(parsed, list):
                    listings = parsed
                else:
                    listings = []
                
                # Validate and clean listings
                cleaned_listings = []
                for listing in listings:
                    if isinstance(listing, dict) and listing.get("cert_number"):
                        # Ensure cert_number is string and clean
                        cert = str(listing.get("cert_number", "")).strip()
                        if cert and re.match(r'^\d{7,9}$', cert):
                            cleaned_listings.append({
                                "title": listing.get("title", ""),
                                "cert_number": cert,
                                "price": float(listing.get("price", 0)) if listing.get("price") else 0,
                                "shipping": float(listing.get("shipping", 0)) if listing.get("shipping") else 0,
                                "url": listing.get("url", ""),
                                "card_name": listing.get("card_name", ""),
                                "year": listing.get("year"),
                                "set": listing.get("set"),
                            })
                
                return cleaned_listings
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to extract listings from text
                print(f"Warning: Could not parse AI response as JSON: {e}")
                print(f"Content length: {len(content)} chars")
                print(f"First 1000 chars of response:")
                print(content[:1000])
                print()
                print(f"Attempting to extract information from text...")
                
                # Try to extract structured information from text
                listings = []
                
                # Pattern 1: Look for any 7-9 digit numbers (potential cert numbers)
                all_numbers = re.findall(r'\b(\d{7,9})\b', content)
                print(f"Found {len(all_numbers)} potential cert numbers: {all_numbers[:20]}")
                
                # Pattern 2: Look for cert numbers with context
                # Try to find patterns like "cert 12345678" or "PSA #12345678" or "certification number: 12345678"
                cert_patterns = [
                    r'(?:cert|certification|PSA\s*#?|cert\s*#?)[:\s]*(\d{7,9})',
                    r'(\d{7,9})(?:\s*PSA|\s*cert)',
                ]
                
                cert_matches = []
                for pattern in cert_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    cert_matches.extend(matches)
                
                # Also try all 7-9 digit numbers as potential certs
                if not cert_matches and all_numbers:
                    cert_matches = all_numbers[:limit]
                
                # Remove duplicates while preserving order
                seen = set()
                unique_certs = []
                for cert in cert_matches:
                    if cert not in seen:
                        seen.add(cert)
                        unique_certs.append(cert)
                
                print(f"Using {len(unique_certs)} cert numbers: {unique_certs[:10]}")
                
                # For each cert, try to extract price and other info from nearby text
                for cert in unique_certs[:limit]:
                    # Find context around this cert number
                    cert_index = content.find(cert)
                    if cert_index == -1:
                        continue
                    
                    # Extract 500 chars before and after
                    start = max(0, cert_index - 500)
                    end = min(len(content), cert_index + len(cert) + 500)
                    context = content[start:end]
                    
                    # Try to extract price
                    price_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', context)
                    price = 0
                    if price_match:
                        try:
                            price_str = price_match.group(1).replace(',', '')
                            price = float(price_str)
                        except ValueError:
                            pass
                    
                    # Try to extract title/card name
                    title_match = re.search(r'([A-Z][A-Z\s\-!]+(?:DRAGON|MAGICIAN|GUARDIAN|BEAST|WARRIOR|SPELLCASTER))', context, re.IGNORECASE)
                    card_name = title_match.group(1).strip() if title_match else ""
                    
                    listings.append({
                        "cert_number": cert,
                        "title": f"Yu-Gi-Oh! PSA 10 1st Edition - Cert {cert}",
                        "price": price,
                        "shipping": 5.99,  # Default estimate
                        "url": f"https://www.ebay.com/sch/i.html?_nkw=yugioh+psa+10+{cert}",
                        "card_name": card_name,
                        "year": None,
                        "set": None,
                    })
                
                return listings
        else:
            print(f"OpenRouter API error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"Error in AI eBay search: {e}")
        return []


def analyze_arbitrage_opportunities(
    listings: List[Dict[str, Any]],
    openrouter_api_key: str,
    tax_rate: float = 0.09,
    site_url: Optional[str] = None,
    site_name: Optional[str] = None,
    model: str = "moonshotai/kimi-k2-thinking"
) -> List[Dict[str, Any]]:
    """
    Analyze listings for arbitrage opportunities with LLM insights.
    
    For each listing:
    1. Scrape PSA cert page for EstimatedValue
    2. Calculate all-in cost (price + shipping + tax)
    3. Calculate spread (PSA Estimate - all-in cost)
    4. Use LLM to analyze and provide insights on opportunities
    
    Args:
        listings: List of card listings from AI search
        openrouter_api_key: OpenRouter API key for additional analysis
        tax_rate: Tax rate as fraction
        site_url: Optional site URL for OpenRouter
        site_name: Optional site name for OpenRouter
        model: LLM model to use (default: moonshotai/kimi-k2-thinking)
        
    Returns:
        List of arbitrage opportunities with spread calculations and LLM insights
    """
    opportunities = []
    
    for listing in listings:
        cert_number = listing.get("cert_number")
        if not cert_number:
            continue
        
        print(f"Analyzing cert {cert_number}...")
        
        # Step 1: Scrape PSA estimate (try eBay first if URL available)
        ebay_url = listing.get("url", "")
        psa_estimate = scrape_psa_estimate(cert_number, ebay_url=ebay_url if ebay_url else None)
        
        # Step 2: Calculate costs
        price = listing.get("price", 0)
        shipping = listing.get("shipping", 0)
        est_tax = round(tax_rate * price, 2)
        all_in_cost = price + shipping + est_tax
        
        # Step 3: Calculate spread (if PSA estimate available)
        if psa_estimate:
            spread = psa_estimate - all_in_cost
            spread_pct = (spread / psa_estimate * 100) if psa_estimate > 0 else 0
            is_arbitrage = spread > 0
        else:
            spread = None
            spread_pct = None
            is_arbitrage = False
            print(f"  Could not find PSA estimate for cert {cert_number}")
        
        # Step 4: Create opportunity record (always include, even without PSA estimate)
        opportunity = {
            "cert_number": cert_number,
            "title": listing.get("title", ""),
            "card_name": listing.get("card_name", ""),
            "year": listing.get("year"),
            "set": listing.get("set"),
            "ebay_price": price,
            "shipping": shipping,
            "est_tax": est_tax,
            "all_in_cost": all_in_cost,
            "psa_estimate": psa_estimate,
            "spread": spread,
            "spread_pct": spread_pct,
            "url": listing.get("url", ""),
            "is_arbitrage": is_arbitrage,
            "ai_insights": None,
        }
        
        # Step 5: Use LLM for deeper analysis if this is an arbitrage opportunity
        if is_arbitrage and openrouter_api_key and psa_estimate:
            try:
                print(f"  🤖 Getting AI insights for cert {cert_number}...")
                ai_insights = get_llm_arbitrage_insights(
                    listing=listing,
                    psa_estimate=psa_estimate,
                    spread=spread,
                    spread_pct=spread_pct,
                    openrouter_api_key=openrouter_api_key,
                    model=model,
                    site_url=site_url,
                    site_name=site_name
                )
                opportunity["ai_insights"] = ai_insights
            except Exception as e:
                print(f"  ⚠️ LLM analysis failed: {e}")
        
        opportunities.append(opportunity)
        
        if psa_estimate:
            if spread > 0:
                print(f"  [ARBITRAGE FOUND] Spread = ${spread:.2f} ({spread_pct:.1f}%)")
                print(f"    PSA Est: ${psa_estimate:.2f} | eBay Cost: ${all_in_cost:.2f}")
            else:
                print(f"  [No arbitrage] Spread = ${spread:.2f} (PSA Est: ${psa_estimate:.2f} < Cost: ${all_in_cost:.2f})")
    
    return opportunities


def get_llm_arbitrage_insights(
    listing: Dict[str, Any],
    psa_estimate: float,
    spread: float,
    spread_pct: float,
    openrouter_api_key: str,
    model: str = "moonshotai/kimi-k2-thinking",
    site_url: Optional[str] = None,
    site_name: Optional[str] = None
) -> Optional[str]:
    """
    Get LLM insights on an arbitrage opportunity.
    
    Args:
        listing: Card listing dictionary
        psa_estimate: PSA estimated value
        spread: Profit spread
        spread_pct: Profit percentage
        openrouter_api_key: OpenRouter API key
        model: LLM model to use
        site_url: Optional site URL for OpenRouter
        site_name: Optional site name for OpenRouter
        
    Returns:
        AI insights string or None
    """
    prompt = f"""Analyze this PSA card arbitrage opportunity:

Card: {listing.get('title', 'Unknown')}
PSA Cert: {listing.get('cert_number', 'N/A')}
eBay Price: ${listing.get('price', 0):.2f}
Shipping: ${listing.get('shipping', 0):.2f}
Total Cost: ${listing.get('price', 0) + listing.get('shipping', 0):.2f}
PSA Estimate: ${psa_estimate:.2f}
Potential Profit: ${spread:.2f} ({spread_pct:.1f}%)

Provide a brief analysis (2-3 sentences) on:
1. Whether this is a good arbitrage opportunity
2. Market factors to consider
3. Risk assessment

Be concise and actionable."""

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }
    
    if site_url:
        headers["HTTP-Referer"] = site_url
    if site_name:
        headers["X-Title"] = site_name
    
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 300,
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
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip() if content else None
        else:
            print(f"  OpenRouter API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"  Error calling LLM: {e}")
        return None


def get_card_pricing(
    cert_number: str,
    card_info: Dict[str, Any],
    openrouter_api_key: Optional[str] = None,
    ebay_oauth: Optional[str] = None
) -> Optional[float]:
    """
    Get PSA Estimated Value using multiple methods.
    
    Priority:
    1. Scrape PSA cert page (fastest, most reliable)
    2. Deep research agent (if API key provided)
    
    Args:
        cert_number: PSA certification number
        card_info: Dictionary with card details
        openrouter_api_key: Optional OpenRouter API key for deep research
        
    Returns:
        Estimated value as float, or None if not found
    """
    # Method 1: Scrape PSA cert page
    estimate = scrape_psa_estimate(cert_number)
    if estimate:
        return estimate
    
    # Method 2: Deep research (if API key provided and scraping failed)
    if openrouter_api_key:
        research = deep_research_pricing(
            cert_number, 
            card_info, 
            openrouter_api_key,
            ebay_oauth=ebay_oauth
        )
        if research and research.get("psa_estimate"):
            return research["psa_estimate"]
    
    return None


def extract_cert_from_image(
    image_path: str,
    openrouter_api_key: str,
    model: str = "anthropic/claude-opus-4.5",  # Claude Opus 4.5
    site_url: Optional[str] = None,
    site_name: Optional[str] = None
) -> Optional[str]:
    """
    Extract PSA certification number from a card image using OpenRouter vision models.
    
    Args:
        image_path: Path to the image file (PNG, JPG, etc.)
        openrouter_api_key: OpenRouter API key
        model: Vision model to use (default: claude-opus-4.5, alternatives: gpt-4o, gpt-4o-mini)
        site_url: Optional site URL for OpenRouter
        site_name: Optional site name for OpenRouter
        
    Returns:
        PSA certification number as string, or None if not found
    """
    if not openrouter_api_key:
        print("Error: OPENROUTER_API_KEY not provided")
        return None
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return None
    
    # Read and encode image as base64
    try:
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"Error reading image file: {e}")
        return None
    
    # Determine image MIME type from file extension
    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    mime_type = mime_types.get(ext, 'image/png')
    
    # Create prompt
    prompt = """Look at this PSA-graded trading card image and extract the PSA certification number.

The certification number is typically:
- A 7-9 digit number
- Located on the PSA label/slab
- Usually near the top or bottom of the label
- May be labeled as "Cert #", "Certification Number", or just shown as a number

Please extract ONLY the certification number (digits only, no spaces or dashes).
If you cannot find a certification number, respond with "NOT_FOUND".

Format your response as a JSON object:
{
  "cert_number": "12345678" or "NOT_FOUND"
}"""
    
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }
    
    if site_url:
        headers["HTTP-Referer"] = site_url
    if site_name:
        headers["X-Title"] = site_name
    
    # Prepare message with image
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 200,
        "response_format": {"type": "json_object"}  # Request JSON format
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
            
            # Try to parse JSON response
            try:
                # Clean up content
                content = re.sub(r'```json\s*', '', content)
                content = re.sub(r'```\s*$', '', content)
                content = re.sub(r'^```\s*', '', content)
                content = content.strip()
                
                parsed = json.loads(content)
                cert_number = parsed.get("cert_number", "")
                
                if cert_number and cert_number != "NOT_FOUND":
                    # Validate it's a 7-9 digit number
                    if re.match(r'^\d{7,9}$', cert_number):
                        return cert_number
                    else:
                        print(f"Warning: Extracted cert number doesn't match expected format: {cert_number}")
                        return None
                else:
                    print("Model could not find certification number in image")
                    return None
                    
            except json.JSONDecodeError:
                # Try to extract cert number from plain text
                cert_match = re.search(r'\b(\d{7,9})\b', content)
                if cert_match:
                    return cert_match.group(1)
                print(f"Could not parse response as JSON: {content[:200]}")
                return None
        else:
            print(f"OpenRouter API error: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        return None

