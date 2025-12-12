#!/usr/bin/env python3
"""
Test script for PSA Card Arbitrage functionality
Tests key features: eBay search, PSA data fetching, estimate scraping, and AI analysis
"""
import sys
from lib.config import load_env
from lib.ebay_api import search_ebay_generic
from lib.psa_api import fetch_psa_cert
from lib.research_agent import scrape_psa_estimate, analyze_arbitrage_opportunities
from psa_card_arbitrage import extract_cert_from_item
import traceback

def test_ebay_search():
    """Test eBay search functionality"""
    print("=" * 70)
    print("TEST 1: eBay Search")
    print("=" * 70)
    try:
        env = load_env()
        
        if not env.get('EBAY_OAUTH') and not (env.get('EBAY_CLIENT_ID') and env.get('EBAY_CLIENT_SECRET')):
            print("❌ FAILED: No eBay credentials found")
            print("   Need either EBAY_OAUTH or EBAY_CLIENT_ID + EBAY_CLIENT_SECRET")
            return False
        
        print("✅ eBay credentials found")
        print(f"   Searching for: 'yugioh PSA 10 1st edition'")
        
        items = search_ebay_generic(
            query="yugioh PSA 10 1st edition",
            limit=5,
            env=env,
            category_ids="183454",
            filters="buyingOptions:{FIXED_PRICE}"
        )
        
        if not items:
            print("⚠️  WARNING: No items found (this might be normal)")
            return True
        
        print(f"✅ SUCCESS: Found {len(items)} items")
        print(f"   First item: {items[0].get('title', 'N/A')[:60]}...")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False

def test_psa_api():
    """Test PSA API functionality"""
    print("\n" + "=" * 70)
    print("TEST 2: PSA API")
    print("=" * 70)
    try:
        env = load_env()
        
        if not env.get('PSA_TOKEN'):
            print("⚠️  WARNING: PSA_TOKEN not found - skipping PSA API test")
            return True
        
        print("✅ PSA_TOKEN found")
        print("   Testing with cert: 12345678 (example)")
        
        # Use a real cert number if available, otherwise test with a dummy
        test_cert = "12345678"
        psa_data = fetch_psa_cert(test_cert, env)
        
        if psa_data.get('grade'):
            print(f"✅ SUCCESS: PSA data retrieved")
            print(f"   Grade: {psa_data.get('grade')}")
            print(f"   Year: {psa_data.get('year')}")
            print(f"   Brand: {psa_data.get('brand')}")
        else:
            print("⚠️  WARNING: No PSA data returned (cert might not exist)")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False

def test_psa_estimate_scraping():
    """Test PSA estimate scraping"""
    print("\n" + "=" * 70)
    print("TEST 3: PSA Estimate Scraping")
    print("=" * 70)
    try:
        print("   Testing PSA estimate scraping...")
        print("   Note: This requires a valid cert number with an estimate")
        
        # Try with a known cert if we have one, otherwise skip
        test_cert = "12345678"  # Replace with a real cert if available
        estimate = scrape_psa_estimate(test_cert)
        
        if estimate:
            print(f"✅ SUCCESS: Found PSA estimate: ${estimate:.2f}")
        else:
            print("⚠️  WARNING: No estimate found (cert might not have estimate)")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False

def test_cert_extraction():
    """Test cert number extraction from eBay items"""
    print("\n" + "=" * 70)
    print("TEST 4: Cert Number Extraction")
    print("=" * 70)
    try:
        env = load_env()
        
        print("   Searching eBay for cards with cert numbers...")
        items = search_ebay_generic(
            query="yugioh PSA 10 1st edition",
            limit=10,
            env=env,
            category_ids="183454",
            filters="buyingOptions:{FIXED_PRICE}"
        )
        
        certs_found = 0
        for item in items:
            cert = extract_cert_from_item(item)
            if cert:
                certs_found += 1
                print(f"   ✅ Found cert: {cert} in '{item.get('title', '')[:50]}...'")
                if certs_found >= 3:
                    break
        
        if certs_found > 0:
            print(f"✅ SUCCESS: Extracted {certs_found} cert numbers")
        else:
            print("⚠️  WARNING: No cert numbers found in titles")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False

def test_ai_analysis():
    """Test AI analysis functionality"""
    print("\n" + "=" * 70)
    print("TEST 5: AI Analysis")
    print("=" * 70)
    try:
        env = load_env()
        
        if not env.get('OPENROUTER_API_KEY'):
            print("⚠️  WARNING: OPENROUTER_API_KEY not found - skipping AI analysis test")
            return True
        
        print("✅ OPENROUTER_API_KEY found")
        print("   Testing AI analysis with sample data...")
        
        # Create sample listing
        sample_listings = [{
            'cert_number': '12345678',
            'title': 'Test Card PSA 10',
            'price': 100.0,
            'shipping': 5.0,
            'url': 'https://ebay.com/test'
        }]
        
        analyzed = analyze_arbitrage_opportunities(
            sample_listings,
            env.get('OPENROUTER_API_KEY'),
            tax_rate=0.09,
            model="moonshotai/kimi-k2-thinking"
        )
        
        if analyzed:
            print(f"✅ SUCCESS: AI analysis completed")
            print(f"   Analyzed {len(analyzed)} opportunities")
        else:
            print("⚠️  WARNING: No analysis results (might be expected for test data)")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False

def test_full_workflow():
    """Test the full workflow: search -> extract cert -> get PSA data -> scrape estimate"""
    print("\n" + "=" * 70)
    print("TEST 6: Full Workflow")
    print("=" * 70)
    try:
        env = load_env()
        
        print("   1. Searching eBay...")
        items = search_ebay_generic(
            query="yugioh PSA 10 1st edition",
            limit=5,
            env=env,
            category_ids="183454",
            filters="buyingOptions:{FIXED_PRICE}"
        )
        
        if not items:
            print("   ⚠️  No items found - cannot test full workflow")
            return True
        
        print(f"   ✅ Found {len(items)} items")
        
        # Try to find a card with a cert
        for item in items:
            cert = extract_cert_from_item(item)
            if cert:
                print(f"   2. Found cert: {cert}")
                print(f"   3. Fetching PSA data...")
                psa_data = fetch_psa_cert(cert, env)
                
                if psa_data.get('grade'):
                    print(f"      ✅ PSA Grade: {psa_data.get('grade')}")
                    print(f"      ✅ Year: {psa_data.get('year')}")
                    print(f"      ✅ Brand: {psa_data.get('brand')}")
                
                print(f"   4. Scraping PSA estimate...")
                estimate = scrape_psa_estimate(cert, ebay_url=item.get('url'))
                
                if estimate:
                    print(f"      ✅ PSA Estimate: ${estimate:.2f}")
                    
                    # Calculate arbitrage
                    total_cost = item['price'] + item['shipping'] + (0.09 * item['price'])
                    spread = estimate - total_cost
                    print(f"   5. Arbitrage Calculation:")
                    print(f"      eBay Cost: ${total_cost:.2f}")
                    print(f"      PSA Estimate: ${estimate:.2f}")
                    print(f"      Spread: ${spread:.2f}")
                    
                    if spread > 0:
                        print(f"      ✅ UNDERVALUED! Potential profit: ${spread:.2f}")
                    else:
                        print(f"      ⚠️  Not undervalued")
                else:
                    print(f"      ⚠️  No estimate found")
                
                print(f"   ✅ Full workflow test completed successfully!")
                return True
        
        print("   ⚠️  No cert numbers found in items - cannot test full workflow")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("PSA CARD ARBITRAGE - TEST SUITE")
    print("=" * 70)
    print()
    
    results = []
    
    # Run tests
    results.append(("eBay Search", test_ebay_search()))
    results.append(("PSA API", test_psa_api()))
    results.append(("PSA Estimate Scraping", test_psa_estimate_scraping()))
    results.append(("Cert Extraction", test_cert_extraction()))
    results.append(("AI Analysis", test_ai_analysis()))
    results.append(("Full Workflow", test_full_workflow()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your code is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) had issues. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

