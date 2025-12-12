"""
eBay OAuth 2.0 Token Management
Automatically generate and refresh eBay OAuth tokens
"""
import os
import base64
import requests
import time
from typing import Optional, Dict
from dotenv import load_dotenv


def get_oauth_token(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    environment: str = "production"
) -> Optional[str]:
    """
    Get eBay OAuth access token using Client Credentials Grant Flow.
    
    This is for applications that only need access to public data (like Browse API).
    No user authorization required!
    
    Args:
        client_id: eBay App ID (Client ID). If None, reads from EBAY_CLIENT_ID env var
        client_secret: eBay Cert ID (Client Secret). If None, reads from EBAY_CLIENT_SECRET env var
        environment: "production" or "sandbox"
        
    Returns:
        Access token string, or None if failed
    """
    # Load from env if not provided
    if not client_id:
        load_dotenv(".env.local")
        client_id = os.getenv("EBAY_CLIENT_ID", "")
    
    if not client_secret:
        load_dotenv(".env.local")
        client_secret = os.getenv("EBAY_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        print("[ERROR] EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required")
        print("Get them from: https://developer.ebay.com/my/keys")
        return None
    
    # Choose endpoint based on environment
    if environment.lower() == "sandbox":
        token_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    else:
        token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    
    # Create Basic Auth header (base64 encoded client_id:client_secret)
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    # OAuth 2.0 Client Credentials Grant
    # Try different scope formats
    scope_options = [
        "https://api.ebay.com/oauth/api_scope/buy.browse",  # Full scope URL
        "buy.browse",  # Short format
        "https://api.ebay.com/oauth/api_scope",  # Base scope
    ]
    
    # Try each scope format
    for scope in scope_options:
        data = {
            "grant_type": "client_credentials",
            "scope": scope
        }
        
        try:
            print(f"[DEBUG] Trying scope: {scope}")
            response = requests.post(token_url, headers=headers, data=data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 7200)
                
                print(f"[SUCCESS] OAuth token obtained with scope: {scope}")
                print(f"[SUCCESS] Token expires in {expires_in} seconds")
                return access_token
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("error_description", "")
                if "scope" in error_msg.lower():
                    print(f"[DEBUG] Scope '{scope}' rejected: {error_msg}")
                    continue  # Try next scope
                else:
                    print(f"[ERROR] Failed: {error_msg}")
                    return None
            else:
                print(f"[ERROR] Status {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"[ERROR] Exception: {e}")
            continue
    
    # If all scopes failed, return None
    print("[ERROR] All scope formats failed. Your app may need to be configured with OAuth scopes in eBay Developer Portal.")
    return None
    
    try:
        print(f"[DEBUG] Requesting OAuth token from {token_url}...")
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 7200)  # Default 2 hours
            
            print(f"[SUCCESS] OAuth token obtained! Expires in {expires_in} seconds")
            return access_token
        else:
            print(f"[ERROR] Failed to get OAuth token: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Exception getting OAuth token: {e}")
        return None


def refresh_oauth_token(
    refresh_token: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    environment: str = "production"
) -> Optional[str]:
    """
    Refresh an eBay OAuth access token using a refresh token.
    
    Args:
        refresh_token: The refresh token from previous authorization
        client_id: eBay App ID. If None, reads from EBAY_CLIENT_ID env var
        client_secret: eBay Cert ID. If None, reads from EBAY_CLIENT_SECRET env var
        environment: "production" or "sandbox"
        
    Returns:
        New access token string, or None if failed
    """
    # Load from env if not provided
    if not client_id:
        load_dotenv(".env.local")
        client_id = os.getenv("EBAY_CLIENT_ID", "")
    
    if not client_secret:
        load_dotenv(".env.local")
        client_secret = os.getenv("EBAY_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        print("[ERROR] EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required")
        return None
    
    # Choose endpoint
    if environment.lower() == "sandbox":
        token_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    else:
        token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    
    # Create Basic Auth header
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "https://api.ebay.com/oauth/api_scope/buy.browse"
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"[ERROR] Failed to refresh token: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Exception refreshing token: {e}")
        return None


def get_authorization_url(
    client_id: Optional[str] = None,
    redirect_uri: str = "http://localhost:5002/oauth/callback",
    environment: str = "production"
) -> str:
    """
    Generate eBay OAuth authorization URL for Authorization Code Grant Flow.
    
    This requires user interaction - user must authorize the app.
    
    Args:
        client_id: eBay App ID. If None, reads from EBAY_CLIENT_ID env var
        redirect_uri: Where to redirect after authorization (must match app settings)
        environment: "production" or "sandbox"
        
    Returns:
        Authorization URL
    """
    if not client_id:
        load_dotenv(".env.local")
        client_id = os.getenv("EBAY_CLIENT_ID", "")
    
    if not client_id:
        raise ValueError("EBAY_CLIENT_ID is required")
    
    # Choose endpoint
    if environment.lower() == "sandbox":
        auth_url = "https://auth.sandbox.ebay.com/oauth2/authorize"
    else:
        auth_url = "https://auth.ebay.com/oauth2/authorize"
    
    scope = "https://api.ebay.com/oauth/api_scope/buy.browse"
    
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{auth_url}?{query_string}"


def exchange_code_for_token(
    authorization_code: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    redirect_uri: str = "http://localhost:5002/oauth/callback",
    environment: str = "production"
) -> Optional[Dict[str, str]]:
    """
    Exchange authorization code for access token (Authorization Code Grant Flow).
    
    Args:
        authorization_code: Code received from authorization callback
        client_id: eBay App ID. If None, reads from EBAY_CLIENT_ID env var
        client_secret: eBay Cert ID. If None, reads from EBAY_CLIENT_SECRET env var
        redirect_uri: Must match the redirect_uri used in authorization
        environment: "production" or "sandbox"
        
    Returns:
        Dict with 'access_token' and 'refresh_token', or None if failed
    """
    if not client_id:
        load_dotenv(".env.local")
        client_id = os.getenv("EBAY_CLIENT_ID", "")
    
    if not client_secret:
        load_dotenv(".env.local")
        client_secret = os.getenv("EBAY_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        print("[ERROR] EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required")
        return None
    
    # Choose endpoint
    if environment.lower() == "sandbox":
        token_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    else:
        token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    
    # Create Basic Auth header
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": redirect_uri
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in", 7200)
            }
        else:
            print(f"[ERROR] Failed to exchange code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Exception exchanging code: {e}")
        return None

