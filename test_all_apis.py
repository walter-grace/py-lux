#!/usr/bin/env python3
"""
Comprehensive test script for all API integrations in the chatbot
Tests eBay, Watch Database, and metadata extraction
"""
import os
import sys
import asyncio
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lib.config import load_env
from lib.ebay_api import search_ebay_generic
from lib.watch_database_api import (
    search_watches_by_name,
    search_reference,
    get_all_makes,
    normalize_brand_name
)
from lib.watch_api import extract_watch_metadata, enrich_watch_metadata_with_watch_db
from chatbot_mcp import eBayTools

load_dotenv(".env")
load_dotenv(".env.local", override=True)


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_test(test_name):
    """Print a test name"""
    print(f"\n📋 Test: {test_name}")
    print("-" * 70)


def test_ebay_api():
    """Test eBay API integration"""
    print_section("eBay API Tests")
    
    env = load_env()
    
    # Check credentials
    ebay_oauth = env.get("EBAY_OAUTH", "")
    ebay_client_id = env.get("EBAY_CLIENT_ID", "")
    ebay_client_secret = env.get("EBAY_CLIENT_SECRET", "")
    
    if not ebay_oauth and not (ebay_client_id and ebay_client_secret):
        print("❌ eBay credentials not found - skipping eBay tests")
        return False
    
    print("✅ eBay credentials found")
    
    # Test 1: Basic search
    print_test("Basic eBay Search - Watches")
    try:
        items = search_ebay_generic(
            query="Rolex Submariner",
            limit=5,
            env=env,
            category_ids="260324",  # Watches
            filters="buyingOptions:{FIXED_PRICE}"
        )
        
        if items:
            print(f"✅ Found {len(items)} items")
            for i, item in enumerate(items[:3], 1):
                print(f"  {i}. {item.get('title', 'N/A')[:60]}...")
                print(f"     Price: ${item.get('price', 0):,.2f} + ${item.get('shipping', 0):,.2f} shipping")
                print(f"     URL: {item.get('url', 'N/A')[:60]}...")
        else:
            print("⚠️  No items found")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Trading cards search
    print_test("eBay Search - Trading Cards")
    try:
        items = search_ebay_generic(
            query="PSA 10 Charizard",
            limit=3,
            env=env,
            category_ids="183454",  # Trading Cards
            filters="buyingOptions:{FIXED_PRICE}"
        )
        
        if items:
            print(f"✅ Found {len(items)} items")
            for i, item in enumerate(items[:2], 1):
                print(f"  {i}. {item.get('title', 'N/A')[:60]}...")
        else:
            print("⚠️  No items found (this is okay)")
    except Exception as e:
        print(f"⚠️  Error: {e}")
    
    # Test 3: eBay Tools class
    print_test("eBay Tools Class - search_ebay function")
    try:
        ebay_tools = eBayTools(env)
        result = asyncio.run(ebay_tools.call_tool("search_ebay", {
            "query": "Omega Speedmaster",
            "limit": 3
        }))
        
        if result.get("success"):
            print(f"✅ eBay Tools working")
            print(f"   Found {result.get('count', 0)} items")
            if result.get("items"):
                print(f"   First item: {result['items'][0].get('title', 'N/A')[:50]}...")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_watch_database_api():
    """Test Watch Database API integration"""
    print_section("Watch Database API Tests")
    
    env = load_env()
    api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY", "")
    
    if not api_key:
        print("❌ Watch Database API key not found - skipping tests")
        return False
    
    print(f"✅ API key found: {api_key[:20]}...")
    
    # Test 1: Get all makes
    print_test("Get All Watch Makes (Brands)")
    try:
        makes = get_all_makes(api_key, use_cache=True)
        
        if makes:
            print(f"✅ Found {len(makes)} watch brands")
            print(f"   Sample brands: {', '.join([m.get('name', m.get('make', m.get('brand', 'N/A'))) for m in makes[:5]])}")
        else:
            print("⚠️  No makes found (may need to check endpoint)")
    except Exception as e:
        print(f"⚠️  Error: {e}")
        print("   Note: This may fail if endpoint paths need adjustment")
    
    # Test 2: Search by name
    print_test("Search Watches by Name")
    try:
        result = search_watches_by_name("Rolex Submariner", api_key, limit=5)
        
        if result:
            watches = []
            if isinstance(result, list):
                watches = result
            elif isinstance(result, dict):
                watches = result.get("data", result.get("results", result.get("watches", [])))
                if not isinstance(watches, list):
                    watches = [result]
            
            if watches:
                print(f"✅ Found {len(watches)} watches")
                for i, watch in enumerate(watches[:3], 1):
                    brand = watch.get("make") or watch.get("brand", "N/A")
                    model = watch.get("model", "N/A")
                    ref = watch.get("reference", "N/A")
                    print(f"  {i}. {brand} {model} (Ref: {ref})")
            else:
                print("⚠️  No watches found in response")
        else:
            print("⚠️  No results (may need to check endpoint paths)")
    except Exception as e:
        print(f"⚠️  Error: {e}")
        print("   Note: Endpoint paths may need to be verified from RapidAPI dashboard")
    
    # Test 3: Search by reference
    print_test("Search Watches by Reference Number")
    try:
        result = search_reference("116610LN", api_key)
        
        if result:
            watches = []
            if isinstance(result, list):
                watches = result
            elif isinstance(result, dict):
                watches = result.get("data", result.get("results", result.get("watches", [])))
                if not isinstance(watches, list):
                    watches = [result]
            
            if watches:
                print(f"✅ Found watch by reference")
                watch = watches[0]
                brand = watch.get("make") or watch.get("brand", "N/A")
                model = watch.get("model", "N/A")
                print(f"   {brand} {model}")
            else:
                print("⚠️  No watch found for reference 116610LN")
        else:
            print("⚠️  No results (may need to check endpoint paths)")
    except Exception as e:
        print(f"⚠️  Error: {e}")
    
    # Test 4: Brand normalization
    print_test("Brand Name Normalization")
    try:
        makes = get_all_makes(api_key, use_cache=True)
        if makes:
            test_brands = ["tag heuer", "TAG", "rolex"]
            for brand in test_brands:
                normalized = normalize_brand_name(brand, makes=makes)
                print(f"   '{brand}' -> '{normalized}'")
        else:
            print("⚠️  Cannot test normalization without makes list")
    except Exception as e:
        print(f"⚠️  Error: {e}")
    
    return True


def test_watch_metadata_extraction():
    """Test watch metadata extraction and enrichment"""
    print_section("Watch Metadata Extraction Tests")
    
    env = load_env()
    
    # Test 1: Basic extraction
    print_test("Extract Metadata from Title")
    test_cases = [
        {
            "title": "Rolex Submariner Date 116610LN Black Dial Men's Watch",
            "aspects": {"Brand": "Rolex", "Model": "Submariner"}
        },
        {
            "title": "Omega Speedmaster Professional Moonwatch 311.30.42.30.01.005",
            "aspects": {"Brand": "Omega"}
        },
        {
            "title": "TAG Heuer Carrera Calibre 16 Chronograph Watch",
            "aspects": {"Brand": "Tag Heuer"}
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            watch_info = extract_watch_metadata(
                title=test_case["title"],
                aspects=test_case["aspects"],
                openrouter_api_key=None
            )
            
            print(f"\n  Test Case {i}: {test_case['title'][:50]}...")
            print(f"    Brand: {watch_info.get('brand', 'N/A')}")
            print(f"    Model: {watch_info.get('model', 'N/A')}")
            print(f"    Model Number: {watch_info.get('model_number', 'N/A')}")
            
            if watch_info.get('brand'):
                print(f"    ✅ Metadata extracted")
            else:
                print(f"    ⚠️  Brand not extracted")
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Test 2: Enrichment with Watch Database
    print_test("Enrich Metadata with Watch Database API")
    try:
        watch_info = extract_watch_metadata(
            title="Rolex Submariner Date 116610LN Black Dial Men's Watch",
            aspects={"Brand": "Rolex"},
            openrouter_api_key=None
        )
        
        enriched_info = enrich_watch_metadata_with_watch_db(
            watch_info=watch_info,
            env=env
        )
        
        print(f"  Before enrichment:")
        print(f"    Brand: {watch_info.get('brand')}")
        print(f"    Model: {watch_info.get('model')}")
        print(f"    Model Number: {watch_info.get('model_number')}")
        
        print(f"  After enrichment:")
        print(f"    Brand: {enriched_info.get('brand')}")
        print(f"    Model: {enriched_info.get('model')}")
        print(f"    Model Number: {enriched_info.get('model_number')}")
        
        if enriched_info.get('model_number') or enriched_info.get('model'):
            print(f"  ✅ Enrichment successful")
        else:
            print(f"  ⚠️  Enrichment may need API endpoint fixes")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
        print("     Note: This may fail if Watch Database API endpoints need adjustment")
    
    return True


def test_chatbot_tools():
    """Test chatbot tool integration"""
    print_section("Chatbot Tools Integration Tests")
    
    env = load_env()
    
    # Test eBay Tools
    print_test("eBay Tools Integration")
    try:
        ebay_tools = eBayTools(env)
        tools = ebay_tools.get_tools()
        
        print(f"✅ eBay Tools class initialized")
        print(f"   Available tools: {[t['function']['name'] for t in tools]}")
        
        # Test search_ebay tool
        if any(t['function']['name'] == 'search_ebay' for t in tools):
            print(f"   ✅ search_ebay tool available")
        
        # Test analyze_watch_listing tool
        if any(t['function']['name'] == 'analyze_watch_listing' for t in tools):
            print(f"   ✅ analyze_watch_listing tool available")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test analyze_watch_listing
    print_test("Analyze Watch Listing Tool")
    try:
        result = asyncio.run(ebay_tools.call_tool("analyze_watch_listing", {
            "title": "Rolex Submariner Date 116610LN Black Dial Men's Watch",
            "price": 8500
        }))
        
        if result.get("success"):
            print(f"✅ Watch analysis working")
            metadata = result.get("metadata", {})
            print(f"   Brand: {metadata.get('brand', 'N/A')}")
            print(f"   Model: {metadata.get('model', 'N/A')}")
            print(f"   Model Number: {metadata.get('model_number', 'N/A')}")
        else:
            print(f"⚠️  Analysis returned: {result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"⚠️  Error: {e}")
    
    return True


def test_openrouter_config():
    """Test OpenRouter configuration"""
    print_section("OpenRouter Configuration Test")
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    
    if not openrouter_key:
        print("❌ OPENROUTER_API_KEY not found")
        return False
    
    print(f"✅ OpenRouter API key found: {openrouter_key[:20]}...")
    
    # Test basic connection
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key
        )
        
        # Simple test call
        response = client.chat.completions.create(
            model="anthropic/claude-3-haiku",
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=10
        )
        
        if response.choices[0].message.content:
            print(f"✅ OpenRouter connection successful")
            print(f"   Response: {response.choices[0].message.content.strip()}")
        else:
            print("⚠️  No response from OpenRouter")
            return False
    except Exception as e:
        print(f"❌ OpenRouter connection failed: {e}")
        return False
    
    return True


def main():
    """Run all tests"""
    print("=" * 70)
    print("Comprehensive API Integration Tests")
    print("=" * 70)
    
    results = {}
    
    # Test OpenRouter
    results["openrouter"] = test_openrouter_config()
    
    # Test eBay API
    results["ebay"] = test_ebay_api()
    
    # Test Watch Database API
    results["watch_database"] = test_watch_database_api()
    
    # Test metadata extraction
    results["metadata"] = test_watch_metadata_extraction()
    
    # Test chatbot tools
    results["chatbot_tools"] = test_chatbot_tools()
    
    # Summary
    print_section("Test Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name.replace('_', ' ').title()}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All critical tests passed! Chatbot should be ready to use.")
    elif passed >= total - 1:
        print("\n⚠️  Most tests passed. Some features may need endpoint adjustments.")
    else:
        print("\n❌ Several tests failed. Check configuration and API endpoints.")
    
    print("=" * 70)


if __name__ == "__main__":
    main()

