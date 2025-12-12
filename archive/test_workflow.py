#!/usr/bin/env python3
"""Test the workflow with a known cert number"""

from research_agent import scrape_psa_estimate, analyze_arbitrage_opportunities

# Test with cert 67118020 (GATE GUARDIAN - we know this works)
test_listing = {
    "cert_number": "67118020",
    "title": "2002 YU-GI-OH! MRD-METAL RAIDERS 1ST EDITION #000 GATE GUARDIAN PSA 10",
    "price": 500.00,  # Example eBay price
    "shipping": 5.99,
    "url": "https://www.ebay.com/itm/example",
    "card_name": "GATE GUARDIAN",
    "year": "2002",
    "set": "METAL RAIDERS"
}

print("Testing workflow with cert 67118020...")
print("=" * 70)

# Step 1: Scrape PSA estimate
print("Step 1: Scraping PSA cert page...")
psa_estimate = scrape_psa_estimate(test_listing["cert_number"])

if psa_estimate:
    print(f"Found PSA Estimate: ${psa_estimate:,.2f}")
    
    # Step 2: Analyze arbitrage
    print("\nStep 2: Analyzing arbitrage opportunity...")
    opportunities = analyze_arbitrage_opportunities(
        listings=[test_listing],
        openrouter_api_key=None,  # Not needed for this test
        tax_rate=0.09
    )
    
    if opportunities:
        opp = opportunities[0]
        print(f"\nResults:")
        print(f"  eBay Price: ${opp['ebay_price']:.2f}")
        print(f"  Shipping: ${opp['shipping']:.2f}")
        print(f"  Tax (9%): ${opp['est_tax']:.2f}")
        print(f"  All-In Cost: ${opp['all_in_cost']:.2f}")
        print(f"  PSA Estimate: ${opp['psa_estimate']:.2f}")
        print(f"  Spread: ${opp['spread']:.2f}")
        print(f"  Spread %: {opp['spread_pct']:.1f}%")
        
        if opp['is_arbitrage']:
            print(f"\n[ARBITRAGE OPPORTUNITY FOUND!]")
        else:
            print(f"\n[No arbitrage] (PSA estimate is lower than cost)")
    else:
        print("Could not analyze opportunity")
else:
    print("Could not find PSA estimate")

