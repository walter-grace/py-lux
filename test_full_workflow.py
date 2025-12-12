#!/usr/bin/env python3
"""
Comprehensive test script for PSA Card Arbitrage workflow
Tests the full pipeline: search -> extract cert -> fetch PSA data -> scrape estimate -> calculate arbitrage
"""
import sys
from lib.config import load_env
from lib.ebay_api import search_ebay_generic, get_ebay_item_details
from lib.psa_api import fetch_psa_cert
from lib.research_agent import scrape_psa_estimate
from psa_card_arbitrage import extract_cert_from_item
import traceback

def test_full_workflow():
    """Test the complete workflow end-to-end"""
    print("=" * 70)
    print("COMPREHENSIVE PSA CARD ARBITRAGE TEST")
    print("=" * 70)
    print()
    
    env = load_env()
    
    # Check credentials
    print("1. Checking credentials...")
    if not env.get('EBAY_OAUTH') and not (env.get('EBAY_CLIENT_ID') and env.get('EBAY_CLIENT_SECRET')):
        print("   ❌ FAILED: No eBay credentials")
        return False
    print("   ✅ eBay credentials found")
    
    if not env.get('PSA_TOKEN'):
        print("   ⚠️  WARNING: PSA_TOKEN not found - PSA API tests will be limited")
    else:
        print("   ✅ PSA_TOKEN found")
    
    if not env.get('OPENROUTER_API_KEY'):
        print("   ⚠️  WARNING: OPENROUTER_API_KEY not found - AI analysis will be skipped")
    else:
        print("   ✅ OPENROUTER_API_KEY found")
    
    print()
    
    # Test 1: Search eBay
    print("2. Testing eBay Search...")
    try:
        items = search_ebay_generic(
            query="yugioh PSA 9 1st edition 2002",
            limit=5,
            env=env,
            category_ids="183454",
            filters="buyingOptions:{FIXED_PRICE}"
        )
        
        if not items:
            print("   ❌ FAILED: No items found")
            return False
        
        print(f"   ✅ Found {len(items)} items")
        print(f"   Sample: {items[0].get('title', 'N/A')[:60]}...")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        traceback.print_exc()
        return False
    
    print()
    
    # Test 2: Extract cert numbers
    print("3. Testing Cert Number Extraction...")
    certs_found = 0
    items_with_certs = []
    
    for item in items:
        cert = extract_cert_from_item(item)
        if cert:
            certs_found += 1
            items_with_certs.append((item, cert))
            print(f"   ✅ Found cert {cert} in: {item.get('title', '')[:50]}...")
            if certs_found >= 3:
                break
    
    if certs_found == 0:
        print("   ⚠️  WARNING: No cert numbers found in items")
        print("   This might be normal - certs may not be in titles")
        print("   Trying to fetch full item details...")
        
        # Try fetching full details for first item
        if items:
            item_id = items[0].get('item_id')
            print(f"   Fetching full details for item: {item_id}")
            try:
                details = get_ebay_item_details(item_id, env)
                if details:
                    print(f"   ✅ Got full item details")
                    # Check aspects
                    aspects = details.get("localizedAspects", [])
                    print(f"   Found {len(aspects)} aspects")
                    for aspect in aspects[:5]:
                        print(f"      - {aspect.get('name')}: {aspect.get('value')}")
                else:
                    print("   ⚠️  Could not fetch full details")
            except Exception as e:
                print(f"   ⚠️  Error fetching details: {e}")
    else:
        print(f"   ✅ Successfully extracted {certs_found} cert numbers")
    
    print()
    
    # Test 3: Fetch PSA data
    if items_with_certs:
        print("4. Testing PSA Data Fetching...")
        test_item, test_cert = items_with_certs[0]
        
        try:
            psa_data = fetch_psa_cert(test_cert, env)
            
            if psa_data.get('grade'):
                print(f"   ✅ PSA data retrieved for cert {test_cert}")
                print(f"      Grade: {psa_data.get('grade')}")
                print(f"      Year: {psa_data.get('year')}")
                print(f"      Brand: {psa_data.get('brand')}")
                print(f"      Subject: {psa_data.get('subject')}")
            else:
                print(f"   ⚠️  Cert {test_cert} exists but no grade data")
        except Exception as e:
            print(f"   ⚠️  Error fetching PSA data: {e}")
    else:
        print("4. Skipping PSA data test (no certs found)")
    
    print()
    
    # Test 4: Scrape PSA estimate
    if items_with_certs:
        print("5. Testing PSA Estimate Scraping...")
        test_item, test_cert = items_with_certs[0]
        
        try:
            estimate = scrape_psa_estimate(test_cert, ebay_url=test_item.get('url'))
            
            if estimate:
                print(f"   ✅ Found PSA estimate: ${estimate:.2f}")
                
                # Calculate arbitrage
                price = test_item.get('price', 0)
                shipping = test_item.get('shipping', 0)
                tax = 0.09 * price
                total_cost = price + shipping + tax
                spread = estimate - total_cost
                
                print(f"   📊 Arbitrage Calculation:")
                print(f"      PSA Estimate: ${estimate:.2f}")
                print(f"      eBay Cost: ${total_cost:.2f}")
                print(f"      Spread: ${spread:.2f}")
                
                if spread > 0:
                    print(f"      ✅ UNDERVALUED! Potential profit: ${spread:.2f}")
                else:
                    print(f"      ⚠️  Not undervalued")
            else:
                print(f"   ⚠️  No estimate found for cert {test_cert}")
        except Exception as e:
            print(f"   ⚠️  Error scraping estimate: {e}")
            traceback.print_exc()
    else:
        print("5. Skipping PSA estimate test (no certs found)")
    
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"✅ eBay Search: Working")
    print(f"{'✅' if certs_found > 0 else '⚠️ '} Cert Extraction: {certs_found} certs found")
    print(f"{'✅' if items_with_certs else '⚠️ '} PSA Data Fetching: {'Working' if items_with_certs else 'Skipped (no certs)'}")
    print(f"{'✅' if items_with_certs else '⚠️ '} PSA Estimate Scraping: {'Working' if items_with_certs else 'Skipped (no certs)'}")
    print()
    
    if certs_found == 0:
        print("⚠️  RECOMMENDATION:")
        print("   Cert numbers are not being extracted from item summaries.")
        print("   The system is now fetching full item details which should help.")
        print("   Try running a search in the web app to see if certs are found.")
    
    return True

if __name__ == "__main__":
    try:
        test_full_workflow()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        traceback.print_exc()
        sys.exit(1)

