#!/usr/bin/env python3
"""
Best Sellers Arbitrage Scanner
Finds Amazon best sellers and searches for them on eBay and Facebook Marketplace
to identify arbitrage opportunities.
"""

import os
import sys
import csv
from typing import Optional
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.config import load_env
from lib.amazon_best_sellers import get_amazon_best_sellers, get_available_categories
from lib.ebay_api import search_ebay_generic
from lib.facebook_marketplace_api import search_facebook_marketplace
from lib.arbitrage_comparison import compare_ebay_facebook, compare_ebay_amazon, compare_all_platforms
from lib.targeted_fb_search import build_targeted_fb_query
from lib.targeted_amazon_search import generate_targeted_amazon_query


def search_ebay_for_product(product: dict, env: dict[str, str], limit: int = 10) -> list[dict]:
    """
    Search eBay for a product from Amazon best sellers using generic search.
    """
    title = product.get("title", "")
    
    if not title:
        return []
    
    try:
        # Use generic eBay search
        items = search_ebay_generic(
            query=title,
            limit=limit,
            env=env,
            filters="buyingOptions:{FIXED_PRICE}"  # Buy It Now only
        )
        return items
    except Exception as e:
        print(f"    Error searching eBay: {e}")
        return []


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Find arbitrage opportunities from Amazon best sellers")
    parser.add_argument("category", nargs="?", help="Amazon category (e.g., 'shoes', 'electronics', 'fashion')")
    parser.add_argument("--limit", type=int, default=20, help="Number of best sellers to check (default: 20)")
    parser.add_argument("--max-ebay", type=int, default=10, help="Max eBay results per product (default: 10)")
    parser.add_argument("--max-fb", type=int, default=5, help="Max Facebook results per product (default: 5)")
    parser.add_argument("--list-categories", action="store_true", help="List available categories and exit")
    
    args = parser.parse_args()
    
    if args.list_categories:
        print("Available Amazon Best Seller Categories:")
        print("=" * 70)
        for cat in get_available_categories():
            print(f"  - {cat}")
        return
    
    if not args.category:
        parser.print_help()
        return
    
    env = load_env()
    
    print("=" * 70)
    print("AMAZON BEST SELLERS ARBITRAGE SCANNER")
    print("=" * 70)
    print(f"Category: {args.category}")
    print(f"Checking top {args.limit} best sellers")
    print()
    
    # Step 1: Get Amazon best sellers
    print("Step 1: Getting Amazon best sellers...")
    try:
        amazon_products = get_amazon_best_sellers(
            category=args.category,
            env=env,
            max_items=args.limit
        )
        print(f"Found {len(amazon_products)} Amazon best sellers")
        
        if not amazon_products:
            print("No best sellers found. Exiting.")
            return
        
        # Display top 5
        print("\nTop 5 Best Sellers:")
        for i, product in enumerate(amazon_products[:5], 1):
            print(f"  {i}. {product['title'][:60]}... - ${product['price']:.2f}")
        print()
        
    except Exception as e:
        print(f"Error getting Amazon best sellers: {e}")
        return
    
    # Step 2: Search eBay for each best seller
    print("Step 2: Searching eBay for best sellers...")
    ebay_results = {}
    for i, product in enumerate(amazon_products, 1):
        print(f"  [{i}/{len(amazon_products)}] Searching eBay for: {product['title'][:50]}...")
        try:
            ebay_items = search_ebay_for_product(product, env, limit=args.max_ebay)
            if ebay_items:
                ebay_results[product['asin']] = ebay_items
                print(f"    Found {len(ebay_items)} eBay listings")
            else:
                print(f"    No eBay listings found")
        except Exception as e:
            print(f"    Error: {e}")
    print()
    
    # Step 3: Search Facebook Marketplace for each best seller
    print("Step 3: Searching Facebook Marketplace for best sellers...")
    fb_results = {}
    rapidapi_key = env.get("RAPIDAPI_KEY")
    fb_location = env.get("DEFAULT_FB_LOCATION", "Los Angeles, CA")
    
    if rapidapi_key:
        for i, product in enumerate(amazon_products, 1):
            print(f"  [{i}/{len(amazon_products)}] Searching FB for: {product['title'][:50]}...")
            try:
                # Generate targeted query
                # Convert Amazon product to eBay-like format for query generation
                ebay_like_product = {
                    "title": product["title"],
                    "brand": None,  # Try to extract from title
                    "price": product["price"],
                }
                
                # Try luxury items query format
                query = build_targeted_fb_query([ebay_like_product], item_type="luxury", fallback_query=product["title"])
                if not query:
                    query = product["title"][:50]  # Fallback to title
                
                fb_items = search_facebook_marketplace(
                    query=query,
                    max_items=args.max_fb,
                    env=env,
                    location=fb_location
                )
                if fb_items:
                    fb_results[product['asin']] = fb_items
                    print(f"    Found {len(fb_items)} Facebook listings")
                else:
                    print(f"    No Facebook listings found")
            except Exception as e:
                print(f"    Error: {e}")
    else:
        print("  Skipping Facebook Marketplace (RAPIDAPI_KEY not found)")
    print()
    
    # Step 4: Compare prices and find arbitrage opportunities
    print("Step 4: Analyzing arbitrage opportunities...")
    opportunities = []
    
    for product in amazon_products:
        asin = product["asin"]
        amazon_price = product["price"]
        
        # Get eBay matches
        ebay_items = ebay_results.get(asin, [])
        fb_items = fb_results.get(asin, [])
        
        # Compare with eBay
        for ebay_item in ebay_items:
            ebay_price = ebay_item.get("price", 0) + ebay_item.get("shipping", 0)
            price_diff = amazon_price - ebay_price
            
            opportunity = {
                "amazon_title": product["title"],
                "amazon_price": amazon_price,
                "amazon_url": product["url"],
                "amazon_rank": product.get("rank", ""),
                "platform": "eBay",
                "platform_price": ebay_price,
                "platform_url": ebay_item.get("url", ""),
                "price_difference": price_diff,
                "arbitrage_opportunity": price_diff > 0,  # Amazon cheaper = buy on Amazon, sell on eBay
                "item_type": "best_seller",
            }
            opportunities.append(opportunity)
        
        # Compare with Facebook
        for fb_item in fb_items:
            fb_price = fb_item.get("price", 0) + fb_item.get("shipping", 0)
            price_diff = amazon_price - fb_price
            
            opportunity = {
                "amazon_title": product["title"],
                "amazon_price": amazon_price,
                "amazon_url": product["url"],
                "amazon_rank": product.get("rank", ""),
                "platform": "Facebook",
                "platform_price": fb_price,
                "platform_url": fb_item.get("url", ""),
                "price_difference": price_diff,
                "arbitrage_opportunity": price_diff > 0,
                "item_type": "best_seller",
            }
            opportunities.append(opportunity)
    
    # Sort by price difference (highest first)
    opportunities.sort(key=lambda x: x["price_difference"], reverse=True)
    
    print(f"Found {len(opportunities)} cross-platform opportunities")
    print()
    
    # Step 5: Save to CSV
    csv_filename = f"data/best_sellers_arbitrage_{args.category}.csv"
    os.makedirs("data", exist_ok=True)
    
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "amazon_title", "amazon_price", "amazon_url", "amazon_rank",
            "platform", "platform_price", "platform_url",
            "price_difference", "arbitrage_opportunity"
        ])
        for opp in opportunities:
            writer.writerow([
                opp.get("amazon_title", ""),
                opp.get("amazon_price", 0),
                opp.get("amazon_url", ""),
                opp.get("amazon_rank", ""),
                opp.get("platform", ""),
                opp.get("platform_price", 0),
                opp.get("platform_url", ""),
                opp.get("price_difference", 0),
                opp.get("arbitrage_opportunity", False),
            ])
    
    print(f"Saved results to {csv_filename}")
    print()
    
    # Display top opportunities
    print("=" * 70)
    print("TOP ARBITRAGE OPPORTUNITIES")
    print("=" * 70)
    
    arbitrage_opps = [o for o in opportunities if o.get("arbitrage_opportunity")]
    
    if arbitrage_opps:
        print(f"\nFound {len(arbitrage_opps)} arbitrage opportunities:\n")
        for i, opp in enumerate(arbitrage_opps[:10], 1):
            print(f"{i}. {opp['amazon_title'][:50]}...")
            print(f"   Amazon: ${opp['amazon_price']:.2f}")
            print(f"   {opp['platform']}: ${opp['platform_price']:.2f}")
            print(f"   Profit: ${opp['price_difference']:.2f}")
            print()
    else:
        print("\nNo arbitrage opportunities found (Amazon prices are higher than other platforms)")
        print("This could mean:")
        print("  - Items are cheaper on eBay/Facebook (good for buyers)")
        print("  - Items are in high demand (Amazon best sellers)")
        print("  - Price differences are minimal")


if __name__ == "__main__":
    main()

