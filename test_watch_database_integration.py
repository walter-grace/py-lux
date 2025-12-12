#!/usr/bin/env python3
"""
Test script for Watch Database API integration
Tests the watch metadata enrichment functionality
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lib.config import load_env
from lib.watch_api import extract_watch_metadata, enrich_watch_metadata_with_watch_db
from lib.watch_database_api import (
    get_all_makes,
    search_watches_by_name,
    search_reference,
    normalize_brand_name
)


def test_brand_normalization():
    """Test brand name normalization"""
    print("\n" + "=" * 70)
    print("Test 1: Brand Name Normalization")
    print("=" * 70)
    
    env = load_env()
    api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY")
    
    if not api_key:
        print("⚠️  Skipping test - No API key found")
        return
    
    makes = get_all_makes(api_key, use_cache=True)
    print(f"Loaded {len(makes)} makes from API/cache")
    
    test_brands = ["tag heuer", "TAG", "rolex", "Rolex", "omega", "AP"]
    for brand in test_brands:
        normalized = normalize_brand_name(brand, makes=makes)
        print(f"  '{brand}' -> '{normalized}'")


def test_watch_search():
    """Test watch search by name"""
    print("\n" + "=" * 70)
    print("Test 2: Watch Search by Name")
    print("=" * 70)
    
    env = load_env()
    api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY")
    
    if not api_key:
        print("⚠️  Skipping test - No API key found")
        return
    
    test_queries = ["Rolex Submariner", "Omega Speedmaster", "TAG Heuer Carrera"]
    
    for query in test_queries:
        print(f"\nSearching for: {query}")
        results = search_watches_by_name(query, api_key, limit=3)
        
        if results:
            watches = []
            if isinstance(results, list):
                watches = results
            elif isinstance(results, dict):
                watches = results.get("data", results.get("results", results.get("watches", [])))
                if not isinstance(watches, list):
                    watches = [results]
            
            print(f"  Found {len(watches)} results")
            for i, watch in enumerate(watches[:3], 1):
                brand = watch.get("make") or watch.get("brand", "N/A")
                model = watch.get("model", "N/A")
                ref = watch.get("reference", "N/A")
                print(f"  {i}. {brand} {model} (Ref: {ref})")
        else:
            print(f"  No results found")


def test_reference_search():
    """Test watch search by reference number"""
    print("\n" + "=" * 70)
    print("Test 3: Watch Search by Reference")
    print("=" * 70)
    
    env = load_env()
    api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY")
    
    if not api_key:
        print("⚠️  Skipping test - No API key found")
        return
    
    test_references = ["116610LN", "311.30.42.30.01.005", "126710BLNR"]
    
    for ref in test_references:
        print(f"\nSearching for reference: {ref}")
        results = search_reference(ref, api_key)
        
        if results:
            watches = []
            if isinstance(results, list):
                watches = results
            elif isinstance(results, dict):
                watches = results.get("data", results.get("results", results.get("watches", [])))
                if not isinstance(watches, list):
                    watches = [results]
            
            if watches:
                watch = watches[0]
                brand = watch.get("make") or watch.get("brand", "N/A")
                model = watch.get("model", "N/A")
                print(f"  Found: {brand} {model}")
            else:
                print(f"  No results found")
        else:
            print(f"  No results found")


def test_metadata_enrichment():
    """Test metadata enrichment with sample eBay listing data"""
    print("\n" + "=" * 70)
    print("Test 4: Metadata Enrichment")
    print("=" * 70)
    
    env = load_env()
    api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY")
    
    if not api_key:
        print("⚠️  Skipping test - No API key found")
        return
    
    # Simulate eBay listing data
    test_cases = [
        {
            "title": "Rolex Submariner Date 116610LN Black Dial Men's Watch",
            "aspects": {"Brand": "Rolex", "Model": "Submariner"},
            "expected_brand": "Rolex",
            "expected_model": "Submariner"
        },
        {
            "title": "Omega Speedmaster Professional Moonwatch 311.30.42.30.01.005",
            "aspects": {"Brand": "Omega"},
            "expected_brand": "Omega",
            "expected_model": "Speedmaster"
        },
        {
            "title": "TAG Heuer Carrera Calibre 16 Chronograph Watch",
            "aspects": {"Brand": "Tag Heuer"},
            "expected_brand": "TAG Heuer",
            "expected_model": "Carrera"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['title']}")
        
        # Extract initial metadata
        watch_info = extract_watch_metadata(
            title=test_case["title"],
            aspects=test_case["aspects"],
            openrouter_api_key=None
        )
        
        print(f"  Initial extraction:")
        print(f"    Brand: {watch_info.get('brand')}")
        print(f"    Model: {watch_info.get('model')}")
        print(f"    Model Number: {watch_info.get('model_number')}")
        
        # Enrich with Watch Database API
        enriched_info = enrich_watch_metadata_with_watch_db(
            watch_info=watch_info,
            api_key=api_key,
            env=env
        )
        
        print(f"  After enrichment:")
        print(f"    Brand: {enriched_info.get('brand')}")
        print(f"    Model: {enriched_info.get('model')}")
        print(f"    Model Number: {enriched_info.get('model_number')}")
        
        # Check if enrichment improved the data
        if enriched_info.get('brand') != watch_info.get('brand'):
            print(f"    ✓ Brand normalized/updated")
        if enriched_info.get('model_number') and not watch_info.get('model_number'):
            print(f"    ✓ Model number found")
        if enriched_info.get('model') and not watch_info.get('model'):
            print(f"    ✓ Model found")


def main():
    """Run all tests"""
    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    
    print("=" * 70)
    print("Watch Database API Integration Tests")
    print("=" * 70)
    
    env = load_env()
    api_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY")
    
    if not api_key:
        print("\n⚠️  WARNING: No API key found!")
        print("   Set WATCH_DATABASE_API_KEY or RAPIDAPI_KEY in .env.local")
        print("   Some tests will be skipped.")
    
    try:
        test_brand_normalization()
        test_watch_search()
        test_reference_search()
        test_metadata_enrichment()
        
        print("\n" + "=" * 70)
        print("Tests Complete")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

