"""
PSA API integration for fetching certification data
"""
import time
import random
from typing import TypedDict, Optional
import cloudscraper
import requests


class PsaCert(TypedDict):
    cert: str
    estimated_value: Optional[float]
    year: Optional[str]
    brand: Optional[str]
    set_name: Optional[str]
    player: Optional[str]
    card_no: Optional[str]
    grade: Optional[str]
    subject: Optional[str]
    category: Optional[str]
    total_population: Optional[int]
    population_higher: Optional[int]


def fetch_psa_cert(cert_number: str, env: dict[str, str]) -> PsaCert:
    """
    Fetch PSA certificate data from PSA API.
    
    Args:
        cert_number: PSA certification number
        env: Environment variables dict with PSA_TOKEN
        
    Returns:
        PsaCert dictionary with card information
    """
    psa_token = env.get("PSA_TOKEN", "")
    
    if not psa_token:
        return {
            "cert": cert_number,
            "estimated_value": None,
            "year": None,
            "brand": None,
            "set_name": None,
            "player": None,
            "card_no": None,
            "grade": None,
            "subject": None,
            "category": None,
            "total_population": None,
            "population_higher": None,
        }
    
    url = f"https://api.psacard.com/publicapi/cert/GetByCertNumber/{cert_number}"
    headers = {
        "Authorization": f"Bearer {psa_token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    # Add small jitter between calls
    jitter_ms = random.randint(50, 150) / 1000.0
    time.sleep(jitter_ms)
    
    # Use cloudscraper to bypass Cloudflare protection
    scraper = cloudscraper.create_scraper()
    scraper.headers.update(headers)
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = scraper.get(url, timeout=30)
            
            if response.status_code == 401:
                print(f"[PSA API] Authentication Error (401) - Check your PSA_TOKEN")
                return {
                    "cert": cert_number,
                    "estimated_value": None,
                    "year": None,
                    "brand": None,
                    "set_name": None,
                    "player": None,
                    "card_no": None,
                    "grade": None,
                    "subject": None,
                    "category": None,
                    "total_population": None,
                    "population_higher": None,
                }
            
            if response.status_code == 500:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    time.sleep(wait_time)
                    continue
                return {
                    "cert": cert_number,
                    "estimated_value": None,
                    "year": None,
                    "brand": None,
                    "set_name": None,
                    "player": None,
                    "card_no": None,
                    "grade": None,
                    "subject": None,
                    "category": None,
                    "total_population": None,
                    "population_higher": None,
                }
            
            if response.status_code == 204:
                # No content
                return {
                    "cert": cert_number,
                    "estimated_value": None,
                    "year": None,
                    "brand": None,
                    "set_name": None,
                    "player": None,
                    "card_no": None,
                    "grade": None,
                    "subject": None,
                    "category": None,
                    "total_population": None,
                    "population_higher": None,
                }
            
            response.raise_for_status()
            data = response.json()
            
            # Check if response has IsValidRequest (old format)
            if "IsValidRequest" in data:
                is_valid = data.get("IsValidRequest", False)
                server_message = data.get("ServerMessage", "")
                
                if not is_valid or server_message == "No data found":
                    return {
                        "cert": cert_number,
                        "estimated_value": None,
                        "year": None,
                        "brand": None,
                        "set_name": None,
                        "player": None,
                        "card_no": None,
                        "grade": None,
                        "subject": None,
                        "category": None,
                        "total_population": None,
                        "population_higher": None,
                    }
            
            # PSA API returns { "PSACert": {...}, "DNACert": {...} }
            psa_cert_data = data.get("PSACert", {})
            
            # Extract card information
            return {
                "cert": cert_number,
                "estimated_value": None,  # Not available in Public API
                "year": psa_cert_data.get("Year"),
                "brand": psa_cert_data.get("Brand"),
                "set_name": psa_cert_data.get("SetName") or psa_cert_data.get("Category"),
                "player": psa_cert_data.get("Subject"),
                "card_no": psa_cert_data.get("CardNumber"),
                "grade": psa_cert_data.get("CardGrade"),
                "subject": psa_cert_data.get("Subject"),
                "category": psa_cert_data.get("Category"),
                "total_population": psa_cert_data.get("TotalPopulation"),
                "population_higher": psa_cert_data.get("PopulationHigher"),
            }
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + (0.1 * attempt)
                time.sleep(wait_time)
                continue
            print(f"[PSA API] Error fetching cert {cert_number}: {e}")
            return {
                "cert": cert_number,
                "estimated_value": None,
                "year": None,
                "brand": None,
                "set_name": None,
                "player": None,
                "card_no": None,
                "grade": None,
                "subject": None,
                "category": None,
                "total_population": None,
                "population_higher": None,
            }
    
    return {
        "cert": cert_number,
        "estimated_value": None,
        "year": None,
        "brand": None,
        "set_name": None,
        "player": None,
        "card_no": None,
        "grade": None,
        "subject": None,
        "category": None,
        "total_population": None,
        "population_higher": None,
    }

