#!/usr/bin/env python3
"""
AI-Powered eBay Scanner for Pokemon Base Set 1999 PSA Arbitrage
Uses deep research agent to:
1. Search eBay for Pokemon Base Set 1999 PSA 10 1st Edition cards
2. Scrape PSA cert pages for estimates
3. Analyze for arbitrage opportunities
"""

import os
import sys
import json
from dotenv import load_dotenv
from tabulate import tabulate
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.research_agent import (
    analyze_arbitrage_opportunities,
    scrape_psa_estimate
)
from lib.ebay_api import search_trading_cards
from lib.config import load_env
from lib.facebook_marketplace_api import search_facebook_marketplace
from lib.arbitrage_comparison import compare_ebay_facebook
from lib.targeted_fb_search import build_targeted_fb_query, get_price_range_from_ebay_items


def main():
    """Main entry point for Pokemon eBay scanner."""
    # Load environment
    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    
    # Load environment
    try:
        env = load_env()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    openrouter_key = env.get("OPENROUTER_API_KEY")
    ebay_oauth = env.get("EBAY_OAUTH")
    
    if not ebay_oauth:
        print("Error: EBAY_OAUTH not found in .env.local")
        print("We need eBay API to get actual listings")
        sys.exit(1)
    
    # Get parameters
    limit = 20
    year = "1999"  # Default to 1999 Base Set
    tax_rate = 0.09
    min_spread = 0
    min_spread_pct = 0
    
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    if len(sys.argv) > 2:
        year = sys.argv[2]  # Optional year override
    
    print("=" * 70)
    print("AI-Powered eBay Scanner for Pokemon Base Set 1999 PSA Arbitrage")
    print("=" * 70)
    print(f"Searching eBay for PSA 10 Pokemon Base Set 1999 1st Edition cards")
    if year:
        print(f"Year filter: {year}")
    print(f"Limit: {limit} listings")
    print()
    
    # Step 1: Use eBay API to get listings
    print("Step 1: Searching eBay via API...")
    ebay_items = search_trading_cards(limit, env, year=year, game="pokemon")
    print(f"Found {len(ebay_items)} eBay listings")
    
    # Step 1.5: Search Facebook Marketplace
    rapidapi_key = env.get("RAPIDAPI_KEY")
    fb_location = env.get("DEFAULT_FB_LOCATION", "Los Angeles, CA")
    
    fb_items = []
    if rapidapi_key and ebay_items:  # Only search if we found eBay items
        print("\nStep 1.5: Searching Facebook Marketplace for matching items...")
        print("  ⚠️  Note: Free tier has 30 requests/month - limiting to 10 items")
        try:
            # Build targeted query based on eBay items found
            fallback_query = f"PSA 10 pokemon base set {year}" if year else "PSA 10 pokemon base set 1999"
            targeted_query = build_targeted_fb_query(ebay_items, item_type="trading_cards", fallback_query=fallback_query)
            
            if not targeted_query:
                targeted_query = fallback_query
            
            print(f"  Using targeted query: '{targeted_query}' (based on {len(ebay_items)} eBay items)")
            
            # Limit to 10 items max to conserve API calls
            fb_limit = min(limit, 10)
            
            # Use price range from eBay items to filter Facebook results
            min_price, max_price = get_price_range_from_ebay_items(ebay_items)
            days_since_listed = 30  # Recent listings
            
            print(f"  Price range filter: ${min_price:.0f} - ${max_price:.0f} (based on eBay prices)")
            
            fb_items = search_facebook_marketplace(
                query=targeted_query,
                max_items=fb_limit,
                env=env,
                location=fb_location,
                min_price=min_price,
                max_price=max_price,
                days_since_listed=days_since_listed
            )
            print(f"Found {len(fb_items)} Facebook Marketplace listings")
        except Exception as e:
            print(f"Warning: Facebook Marketplace search failed: {e}")
            print("  Continuing with eBay results only...")
    else:
        print("\nStep 1.5: Skipping Facebook Marketplace (RAPIDAPI_KEY not found)")
    
    # Cross-platform comparison
    cross_platform_matches = []
    if fb_items:
        print("\nComparing eBay and Facebook Marketplace listings...")
        cross_platform_matches = compare_ebay_facebook(ebay_items, fb_items, item_type="trading_cards")
        print(f"Found {len(cross_platform_matches)} cross-platform matches")
    
    # Extract cert numbers and use enhanced metadata
    # If cert not found in metadata, try extracting from image using vision
    listings = []
    for item in ebay_items:
        cert = item.get("cert")  # Cert should already be extracted in search_trading_cards
        
        # If no cert found and we have an image URL, try vision extraction
        if not cert and item.get("image_url") and openrouter_key:
            print(f"  No cert in metadata for {item['title'][:50]}... trying image extraction...")
            try:
                from research_agent import extract_cert_from_image
                # Download image temporarily
                import requests
                import tempfile
                import os
                
                image_url = item.get("image_url")
                response = requests.get(image_url, timeout=30)
                if response.status_code == 200:
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                        tmp_file.write(response.content)
                        tmp_path = tmp_file.name
                    
                    # Extract cert from image
                    cert = extract_cert_from_image(
                        image_path=tmp_path,
                        openrouter_api_key=openrouter_key,
                        model="anthropic/claude-opus-4.5"
                    )
                    
                    # Clean up temp file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                    
                    if cert:
                        print(f"  [SUCCESS] Extracted cert {cert} from image!")
            except Exception as e:
                print(f"  [ERROR] Image extraction failed: {e}")
        
        if cert:
            listings.append({
                "cert_number": cert,
                "title": item["title"],
                "price": item["price"],
                "shipping": item["shipping"],
                "url": item["url"],
                "card_name": item.get("card_name", ""),
                "year": item.get("year"),
                "set": item.get("set_name"),
            })
    
    print(f"Found {len(listings)} listings with cert numbers")
    print()
    
    if not listings:
        print("No listings with cert numbers found. Exiting.")
        return
    
    # Step 2: Analyze for arbitrage
    print("Step 2: Analyzing listings for arbitrage opportunities...")
    print()
    
    opportunities = analyze_arbitrage_opportunities(
        listings=listings,
        openrouter_api_key=openrouter_key,
        tax_rate=tax_rate
    )
    
    # Add platform marker to eBay opportunities
    for opp in opportunities:
        opp["platform"] = "eBay"
        # Find cross-platform match
        for match in cross_platform_matches:
            if match["ebay_item"].get("cert") == opp.get("cert_number"):
                opp["cross_platform_match"] = match["facebook_item"]["url"]
                opp["price_difference"] = match["price_difference"]
                opp["best_platform"] = match["best_platform"]
                break
        if "cross_platform_match" not in opp:
            opp["cross_platform_match"] = ""
            opp["price_difference"] = None
            opp["best_platform"] = "eBay"
    
    # Add Facebook Marketplace items to opportunities
    for fb_item in fb_items:
        cert = fb_item.get("cert")
        if not cert:
            continue
        
        # Try to get PSA estimate
        psa_estimate = None
        try:
            psa_estimate = scrape_psa_estimate(cert, env.get("PSA_TOKEN"))
        except:
            pass
        
        price = fb_item.get("price", 0)
        shipping = fb_item.get("shipping", 0)
        all_in_cost = price + shipping
        
        # Calculate spread if PSA estimate available
        spread = None
        spread_pct = None
        if psa_estimate:
            spread = psa_estimate - all_in_cost
            spread_pct = (spread / psa_estimate * 100) if psa_estimate > 0 else 0
        
        # Find matching eBay item if exists
        cross_match = None
        for match in cross_platform_matches:
            if match["facebook_item"]["item_id"] == fb_item["item_id"]:
                cross_match = match
                break
        
        opportunity = {
            "cert_number": cert,
            "title": fb_item["title"],
            "card_name": fb_item.get("card_name", ""),
            "year": fb_item.get("year"),
            "set": fb_item.get("set_name"),
            "ebay_price": price,
            "shipping": shipping,
            "est_tax": 0.0,
            "all_in_cost": all_in_cost,
            "psa_estimate": psa_estimate,
            "spread": spread,
            "spread_pct": spread_pct,
            "is_arbitrage": spread is not None and spread > 0,
            "url": fb_item["url"],
            "platform": "Facebook",
            "cross_platform_match": cross_match["ebay_item"]["url"] if cross_match else "",
            "price_difference": cross_match["price_difference"] if cross_match else None,
            "best_platform": cross_match["best_platform"] if cross_match else "Facebook",
            "image_url": fb_item.get("image_url", ""),
        }
        opportunities.append(opportunity)
    
    # Step 3: Filter and display results
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    # Save ALL cards to CSV (not just arbitrage)
    import csv
    
    # Sort all opportunities by spread (highest first, including negative)
    # Handle None values by treating them as -infinity
    all_opportunities = sorted(
        opportunities, 
        key=lambda x: x.get("spread") if x.get("spread") is not None else float('-inf'), 
        reverse=True
    )
    
    # Save all cards to CSV
    csv_filename = "data/pokemon_cards.csv"
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "cert_number", "title", "card_name", "year", "set",
            "ebay_price", "shipping", "est_tax", "all_in_cost",
            "psa_estimate", "spread", "spread_pct", "is_arbitrage", "url", "image_url",
            "platform", "cross_platform_match", "price_difference", "best_platform"
        ])
        for opp in all_opportunities:
            # Handle None values for spread/psa_estimate
            psa_est = opp.get("psa_estimate") or ""
            spread_val = opp.get("spread") if opp.get("spread") is not None else ""
            spread_pct_val = opp.get("spread_pct") if opp.get("spread_pct") is not None else ""
            
            # Find corresponding item to get image_url
            item = next((i for i in listings if i.get("item_id") == opp.get("item_id")), None)
            image_url = item.get("image_url", "") if item else ""
            
            writer.writerow([
                opp.get("cert_number", ""),
                opp.get("title", ""),
                opp.get("card_name", ""),
                opp.get("year", ""),
                opp.get("set", ""),
                opp.get("ebay_price", 0),
                opp.get("shipping", 0),
                opp.get("est_tax", 0),
                opp.get("all_in_cost", 0),
                psa_est,
                spread_val,
                spread_pct_val,
                opp.get("is_arbitrage", False),
                opp.get("url", ""),
                image_url or opp.get("image_url", ""),
                opp.get("platform", "eBay"),
                opp.get("cross_platform_match", ""),
                opp.get("price_difference") or "",
                opp.get("best_platform", ""),
            ])
    
    print(f"Saved {len(all_opportunities)} cards to {csv_filename}")
    
    # Filter positive arbitrage for display
    arbitrage_deals = [o for o in opportunities if o["is_arbitrage"] and o["spread"] >= min_spread]
    
    if not arbitrage_deals:
        print("No arbitrage opportunities found.")
        print(f"\nAll {len(all_opportunities)} cards saved to {csv_filename}")
        return
    
    # Sort by spread (highest first)
    arbitrage_deals.sort(key=lambda x: x["spread"], reverse=True)
    
    # Display table
    table_data = []
    for deal in arbitrage_deals:
        title = deal["title"][:50] if len(deal["title"]) > 50 else deal["title"]
        table_data.append([
            deal["cert_number"],
            title,
            f"${deal['ebay_price']:.2f}",
            f"${deal['shipping']:.2f}",
            f"${deal['est_tax']:.2f}",
            f"${deal['all_in_cost']:.2f}",
            f"${deal['psa_estimate']:.2f}",
            f"${deal['spread']:.2f}",
            f"{deal['spread_pct']:.1f}%",
        ])
    
    headers = [
        "Cert",
        "Title",
        "Price",
        "Ship",
        "Tax",
        "All In",
        "PSA Est",
        "Spread",
        "Spread%",
    ]
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Also save arbitrage opportunities to separate CSV
    with open("data/pokemon_arbitrage_opportunities.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "cert_number", "title", "card_name", "year", "set",
            "ebay_price", "shipping", "est_tax", "all_in_cost",
            "psa_estimate", "spread", "spread_pct", "url"
        ])
        for deal in arbitrage_deals:
            writer.writerow([
                deal["cert_number"],
                deal["title"],
                deal.get("card_name", ""),
                deal.get("year", ""),
                deal.get("set", ""),
                deal["ebay_price"],
                deal["shipping"],
                deal["est_tax"],
                deal["all_in_cost"],
                deal["psa_estimate"],
                deal["spread"],
                deal["spread_pct"],
                deal["url"],
            ])
    
    print(f"\nSaved {len(arbitrage_deals)} arbitrage opportunities to pokemon_arbitrage_opportunities.csv")
    print(f"All {len(all_opportunities)} cards saved to {csv_filename}")


if __name__ == "__main__":
    main()

