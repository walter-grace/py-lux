"""
Configuration and environment variable loading
"""
import os
from dotenv import load_dotenv


def load_env() -> dict[str, str]:
    """Load environment variables from .env and .env.local"""
    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    
    # Watch Database API key - can use separate key or fall back to RAPIDAPI_KEY
    watch_db_key = os.getenv("WATCH_DATABASE_API_KEY", "")
    if not watch_db_key:
        watch_db_key = os.getenv("RAPIDAPI_KEY", "")
    
    return {
        "EBAY_OAUTH": os.getenv("EBAY_OAUTH", ""),
        "EBAY_CLIENT_ID": os.getenv("EBAY_CLIENT_ID", ""),
        "EBAY_CLIENT_SECRET": os.getenv("EBAY_CLIENT_SECRET", ""),
        "PSA_TOKEN": os.getenv("PSA_TOKEN", ""),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
        "RAPIDAPI_KEY": os.getenv("RAPIDAPI_KEY", ""),
        "WATCH_DATABASE_API_KEY": watch_db_key,
        "WATCHCHARTS_API_KEY": os.getenv("WATCHCHARTS_API_KEY", ""),
        "DEFAULT_FB_LOCATION": os.getenv("DEFAULT_FB_LOCATION", "Los Angeles, CA"),
    }

