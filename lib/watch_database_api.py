"""
Watch Database API Client
Integrates with RapidAPI Watch Database API for enhanced watch identification
"""
import os
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import requests

# Base URL for Watch Database API
BASE_URL = "https://watch-database1.p.rapidapi.com"
API_HOST = "watch-database1.p.rapidapi.com"

# Cache file for brand list (makes)
CACHE_DIR = Path("data")
CACHE_FILE = CACHE_DIR / "watch_database_makes_cache.json"
CACHE_TTL_HOURS = 24


def _get_headers(api_key: str) -> Dict[str, str]:
    """Get headers for API requests"""
    return {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": API_HOST,
        "Content-Type": "application/json"
    }


def _handle_rate_limit(response: requests.Response, retry_count: int = 0, max_retries: int = 3) -> bool:
    """
    Handle rate limit errors (429) with exponential backoff
    
    Returns:
        True if should retry, False otherwise
    """
    if response.status_code == 429:
        if retry_count >= max_retries:
            print(f"  ⚠️  Rate limit exceeded. Max retries reached.")
            return False
        
        # Exponential backoff: 2^retry_count seconds
        wait_time = 2 ** retry_count
        print(f"  ⚠️  Rate limit exceeded. Waiting {wait_time} seconds before retry {retry_count + 1}/{max_retries}...")
        time.sleep(wait_time)
        return True
    
    return False


def _make_request(
    method: str,
    endpoint: str,
    api_key: str,
    params: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Make HTTP request to Watch Database API with error handling
    
    Args:
        method: HTTP method (GET, POST)
        endpoint: API endpoint path
        api_key: RapidAPI key
        params: Query parameters (for GET)
        json_data: JSON body (for POST)
        max_retries: Maximum retry attempts for rate limits
        
    Returns:
        Response JSON as dict, or None if failed
    """
    url = f"{BASE_URL}{endpoint}"
    headers = _get_headers(api_key)
    
    for attempt in range(max_retries + 1):
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=json_data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Handle rate limiting
            if response.status_code == 429:
                if _handle_rate_limit(response, attempt, max_retries):
                    continue  # Retry
                else:
                    return None
            
            # Handle authentication errors
            if response.status_code in (401, 403):
                print(f"  ⚠️  Authentication error ({response.status_code}). Check your API key.")
                return None
            
            # Handle other errors
            if response.status_code >= 400:
                print(f"  ⚠️  API error ({response.status_code}): {response.text[:200]}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            print(f"  ⚠️  Request timeout. Attempt {attempt + 1}/{max_retries + 1}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Request error: {e}")
            return None
    
    return None


def get_all_makes(api_key: str, use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Get all watch makes (brands) from the API.
    Results are cached for 24 hours to reduce API calls.
    
    Args:
        api_key: RapidAPI key
        use_cache: Whether to use cached data if available
        
    Returns:
        List of make dictionaries, or empty list if failed
    """
    # Check cache first
    if use_cache and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cache_data.get("cached_at", "2000-01-01"))
            if datetime.now() - cache_time < timedelta(hours=CACHE_TTL_HOURS):
                print(f"  Using cached makes list (cached at {cache_time.strftime('%Y-%m-%d %H:%M')})")
                return cache_data.get("makes", [])
        except Exception as e:
            print(f"  ⚠️  Error reading cache: {e}")
    
    # Fetch from API
    print(f"  Fetching makes from Watch Database API...")
    response = _make_request("GET", "/makes", api_key)
    
    if response is None:
        # Try to return cached data even if expired
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    cache_data = json.load(f)
                    print(f"  ⚠️  API failed, using expired cache")
                    return cache_data.get("makes", [])
            except:
                pass
        return []
    
    # Extract makes from response
    makes = []
    if isinstance(response, list):
        makes = response
    elif isinstance(response, dict):
        # Try common response wrapper fields
        makes = response.get("data", response.get("results", response.get("makes", [])))
        if not isinstance(makes, list):
            makes = []
    
    # Save to cache
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "makes": makes
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
        print(f"  Cached {len(makes)} makes for {CACHE_TTL_HOURS} hours")
    except Exception as e:
        print(f"  ⚠️  Error saving cache: {e}")
    
    return makes


def normalize_brand_name(brand: str, makes: Optional[List[Dict[str, Any]]] = None, api_key: Optional[str] = None) -> Optional[str]:
    """
    Normalize brand name using the makes list from Watch Database API.
    
    Args:
        brand: Brand name to normalize
        makes: Optional pre-fetched makes list (if None, will fetch)
        api_key: API key (required if makes is None)
        
    Returns:
        Normalized brand name, or original if not found
    """
    if not brand:
        return None
    
    # Get makes list if not provided
    if makes is None:
        if not api_key:
            return brand  # Can't normalize without API key
        makes = get_all_makes(api_key)
    
    if not makes:
        return brand
    
    brand_lower = brand.lower().strip()
    
    # Try exact match first
    for make in makes:
        make_name = make.get("name") or make.get("make") or make.get("brand")
        if make_name and make_name.lower() == brand_lower:
            return make_name
    
    # Try partial match (brand contains make name or vice versa)
    for make in makes:
        make_name = make.get("name") or make.get("make") or make.get("brand")
        if not make_name:
            continue
        
        make_lower = make_name.lower()
        if brand_lower in make_lower or make_lower in brand_lower:
            return make_name
    
    # Try fuzzy match (common variations)
    brand_variations = {
        "tag heuer": "TAG Heuer",
        "tag": "TAG Heuer",
        "ap": "Audemars Piguet",
        "audemars": "Audemars Piguet",
        "patek": "Patek Philippe",
        "rolex": "Rolex",
        "omega": "Omega",
        "seiko": "Seiko",
        "citizen": "Citizen",
        "casio": "Casio",
    }
    
    normalized = brand_variations.get(brand_lower)
    if normalized:
        return normalized
    
    return brand  # Return original if no match found


def search_watches_by_name(name: str, api_key: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """
    Search watches by name using POST /search endpoint.
    
    Args:
        name: Watch name to search for
        api_key: RapidAPI key
        limit: Maximum number of results (default: 10)
        
    Returns:
        Response dictionary with search results, or None if failed
    """
    endpoint = "/search"
    json_data = {
        "name": name,
        "limit": limit
    }
    
    print(f"  Searching Watch Database for: {name}")
    response = _make_request("POST", endpoint, api_key, json_data=json_data)
    
    if response is None:
        return None
    
    return response


def search_reference(reference: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Search watches by reference number using POST /search/reference endpoint.
    
    Args:
        reference: Reference number to search for (e.g., "116610LN")
        api_key: RapidAPI key
        
    Returns:
        Response dictionary with search results, or None if failed
    """
    endpoint = "/search/reference"
    json_data = {
        "reference": reference
    }
    
    print(f"  Searching Watch Database for reference: {reference}")
    response = _make_request("POST", endpoint, api_key, json_data=json_data)
    
    if response is None:
        return None
    
    return response


def get_watch_details(watch_id: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed watch information by watch ID using GET /watch/{id} endpoint.
    
    Args:
        watch_id: Watch ID from search results
        api_key: RapidAPI key
        
    Returns:
        Watch details dictionary, or None if failed
    """
    endpoint = f"/watch/{watch_id}"
    
    print(f"  Fetching watch details for ID: {watch_id}")
    response = _make_request("GET", endpoint, api_key)
    
    if response is None:
        return None
    
    return response


def get_models_by_make(make_id: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Get all watch models for a specific make using GET /models/{make_id} endpoint.
    
    Args:
        make_id: Make ID from makes list
        api_key: RapidAPI key
        
    Returns:
        List of model dictionaries, or empty list if failed
    """
    endpoint = f"/models/{make_id}"
    
    print(f"  Fetching models for make ID: {make_id}")
    response = _make_request("GET", endpoint, api_key)
    
    if response is None:
        return []
    
    # Extract models from response
    models = []
    if isinstance(response, list):
        models = response
    elif isinstance(response, dict):
        models = response.get("data", response.get("results", response.get("models", [])))
        if not isinstance(models, list):
            models = []
    
    return models


def get_watches_by_make(make_id: str, api_key: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get watches by make ID using GET /watches/{make_id} endpoint.
    
    Args:
        make_id: Make ID from makes list
        api_key: RapidAPI key
        limit: Maximum number of results (default: 50)
        
    Returns:
        List of watch dictionaries, or empty list if failed
    """
    endpoint = f"/watches/{make_id}"
    params = {"limit": limit} if limit else None
    
    print(f"  Fetching watches for make ID: {make_id}")
    response = _make_request("GET", endpoint, api_key, params=params)
    
    if response is None:
        return []
    
    # Extract watches from response
    watches = []
    if isinstance(response, list):
        watches = response
    elif isinstance(response, dict):
        watches = response.get("data", response.get("results", response.get("watches", [])))
        if not isinstance(watches, list):
            watches = []
    
    return watches


def get_watches_by_model(model_id: str, api_key: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get watches by model ID using GET /watches/model/{model_id} endpoint.
    
    Args:
        model_id: Model ID from models list
        api_key: RapidAPI key
        limit: Maximum number of results (default: 50)
        
    Returns:
        List of watch dictionaries, or empty list if failed
    """
    endpoint = f"/watches/model/{model_id}"
    params = {"limit": limit} if limit else None
    
    print(f"  Fetching watches for model ID: {model_id}")
    response = _make_request("GET", endpoint, api_key, params=params)
    
    if response is None:
        return []
    
    # Extract watches from response
    watches = []
    if isinstance(response, list):
        watches = response
    elif isinstance(response, dict):
        watches = response.get("data", response.get("results", response.get("watches", [])))
        if not isinstance(watches, list):
            watches = []
    
    return watches


def get_watches_by_family(family_id: str, api_key: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get watches by family ID using GET /watches/family/{family_id} endpoint.
    
    Args:
        family_id: Family ID
        api_key: RapidAPI key
        limit: Maximum number of results (default: 50)
        
    Returns:
        List of watch dictionaries, or empty list if failed
    """
    endpoint = f"/watches/family/{family_id}"
    params = {"limit": limit} if limit else None
    
    print(f"  Fetching watches for family ID: {family_id}")
    response = _make_request("GET", endpoint, api_key, params=params)
    
    if response is None:
        return []
    
    # Extract watches from response
    watches = []
    if isinstance(response, list):
        watches = response
    elif isinstance(response, dict):
        watches = response.get("data", response.get("results", response.get("watches", [])))
        if not isinstance(watches, list):
            watches = []
    
    return watches


def get_family_by_make_and_model(make_id: str, model_id: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Get watch families by make ID and model ID using GET /family/{make_id}/{model_id} endpoint.
    
    Args:
        make_id: Make ID
        model_id: Model ID
        api_key: RapidAPI key
        
    Returns:
        List of family dictionaries, or empty list if failed
    """
    endpoint = f"/family/{make_id}/{model_id}"
    
    print(f"  Fetching families for make ID: {make_id}, model ID: {model_id}")
    response = _make_request("GET", endpoint, api_key)
    
    if response is None:
        return []
    
    # Extract families from response
    families = []
    if isinstance(response, list):
        families = response
    elif isinstance(response, dict):
        families = response.get("data", response.get("results", response.get("families", [])))
        if not isinstance(families, list):
            families = []
    
    return families

