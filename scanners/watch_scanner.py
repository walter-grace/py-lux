#!/usr/bin/env python3
"""
Watch eBay Arbitrage Scanner
Scans eBay for watches and identifies arbitrage opportunities
by comparing eBay prices to market reference values from sold listings and price guides.
"""

import os
import sys
import csv
import time
import re
from typing import TypedDict, Optional
from dotenv import load_dotenv
from tabulate import tabulate
import requests

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.config import load_env
from lib.ebay_api import search_ebay_generic
from lib.watch_api import (
    extract_watch_metadata,
    enrich_watch_metadata_with_watch_db,
    get_watch_reference_price,
    get_watch_retail_price,
    get_watchcharts_url
)


class WatchItem(TypedDict):
    item_id: str
    title: str
    url: str
    price: float
    shipping: float
    currency: str
    brand: Optional[str]
    model: Optional[str]
    model_number: Optional[str]
    condition: Optional[str]
    image_url: Optional[str]
    watch_info: Optional[dict]  # Full WatchInfo dict


def search_watches(
    search_query: str,
    limit: int,
    env: dict[str, str],
    brand_filter: Optional[str] = None
) -> list[WatchItem]:
    """
    Search eBay for watches.
    
    Args:
        search_query: Search query (e.g., "Rolex Submariner", "Omega Speedmaster")
        limit: Maximum number of items to return
        env: Environment variables dict with EBAY_OAUTH
        brand_filter: Optional brand to filter by
        
    Returns:
        List of WatchItem dictionaries
    """
    # Use generic eBay search with watches category
    ebay_items = search_ebay_generic(
        query=search_query,
        limit=limit,
        env=env,
        category_ids="260324",  # Watches category
        filters="buyingOptions:{FIXED_PRICE}"
    )
    
    watches: list[WatchItem] = []
    openrouter_key = env.get("OPENROUTER_API_KEY", "")
    watch_db_key = env.get("WATCH_DATABASE_API_KEY") or env.get("RAPIDAPI_KEY", "")
    use_watch_db = bool(watch_db_key)
    
    if use_watch_db:
        print(f"[DEBUG] Watch Database API enabled - will enrich metadata")
    else:
        print(f"[DEBUG] Watch Database API not available - using basic extraction only")
    
    for item in ebay_items:
        # Extract aspects from item
        aspects = item.get("aspects", {})
        
        # Extract watch metadata
        watch_info = extract_watch_metadata(
            title=item.get("title", ""),
            aspects=aspects,
            openrouter_api_key=openrouter_key if openrouter_key else None
        )
        
        # Enrich metadata using Watch Database API if available
        if use_watch_db and (watch_info.get("brand") or watch_info.get("model") or watch_info.get("model_number")):
            try:
                watch_info = enrich_watch_metadata_with_watch_db(
                    watch_info=watch_info,
                    api_key=watch_db_key,
                    env=env
                )
            except Exception as e:
                print(f"  ⚠️  Watch Database enrichment failed for item {item.get('item_id', 'unknown')}: {e}")
                # Continue with original metadata
        
        # Apply brand filter if specified
        if brand_filter:
            item_brand = watch_info.get("brand", "").lower()
            filter_brand = brand_filter.lower()
            if filter_brand not in item_brand and item_brand not in filter_brand:
                continue
        
        watch: WatchItem = {
            "item_id": item.get("item_id", ""),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "price": item.get("price", 0),
            "shipping": item.get("shipping", 0),
            "currency": item.get("currency", "USD"),
            "brand": watch_info.get("brand"),
            "model": watch_info.get("model"),
            "model_number": watch_info.get("model_number"),
            "condition": watch_info.get("condition") or item.get("item_condition"),
            "image_url": item.get("image_url"),
            "watch_info": watch_info,
        }
        watches.append(watch)
    
    return watches


def analyze_watch_arbitrage(
    items: list[WatchItem],
    tax_rate: float = 0.09,
    env: dict[str, str] = None,
    min_spread_pct: float = 10.0
) -> list[dict]:
    """
    Analyze watches for arbitrage opportunities.
    
    Args:
        items: List of watch items
        tax_rate: Tax rate as fraction
        env: Environment variables dict
        min_spread_pct: Minimum spread percentage to consider as arbitrage
        
    Returns:
        List of arbitrage opportunities
    """
    if env is None:
        env = load_env()
    
    opportunities = []
    openrouter_key = env.get("OPENROUTER_API_KEY", "")
    use_watchcharts = bool(env.get("WATCHCHARTS_API_KEY", ""))
    
    for item in items:
        price = item["price"]
        shipping = item["shipping"]
        est_tax = round(tax_rate * price, 2)
        all_in_cost = price + shipping + est_tax
        
        # Get watch info
        watch_info = item.get("watch_info", {})
        if not watch_info:
            watch_info = {
                "brand": item.get("brand"),
                "model": item.get("model"),
                "model_number": item.get("model_number"),
                "title": item.get("title"),
            }
        
        # Get reference prices (market and retail)
        title_safe = item['title'][:60].encode('ascii', 'ignore').decode('ascii')
        print(f"  Looking up prices for: {title_safe}...")
        
        # Get market price (current market value)
        reference_price = get_watch_reference_price(
            watch_info=watch_info,
            env=env,
            use_watchcharts=use_watchcharts
        )
        
        if reference_price:
            print(f"    Found market price: ${reference_price:.2f}")
        else:
            print(f"    Could not find market price")
        
        # Get retail price (MSRP)
        retail_price = get_watch_retail_price(
            watch_info=watch_info,
            env=env,
            use_watchcharts=use_watchcharts
        )
        
        if retail_price:
            print(f"    Found retail price: ${retail_price:.2f}")
        else:
            print(f"    Could not find retail price")
        
        # Calculate spread vs market price
        if reference_price:
            spread = reference_price - all_in_cost
            spread_pct = (spread / reference_price * 100) if reference_price > 0 else 0
            is_arbitrage = spread > 0 and spread_pct >= min_spread_pct
        else:
            reference_price = None
            spread = None
            spread_pct = None
            is_arbitrage = False
        
        # Calculate discount from retail (if available)
        retail_discount = None
        retail_discount_pct = None
        if retail_price and all_in_cost:
            retail_discount = retail_price - all_in_cost
            retail_discount_pct = (retail_discount / retail_price * 100) if retail_price > 0 else 0
        
        # Get WatchCharts URL for verification
        watchcharts_url = None
        if watch_info:
            watchcharts_url = get_watchcharts_url(watch_info)
        
        opportunity = {
            "item_id": item["item_id"],
            "title": item["title"],
            "brand": item.get("brand", ""),
            "model": item.get("model", ""),
            "model_number": item.get("model_number", ""),
            "condition": item.get("condition", ""),
            "ebay_price": price,
            "shipping": shipping,
            "est_tax": est_tax,
            "all_in_cost": all_in_cost,
            "retail_price": retail_price,
            "retail_discount": retail_discount,
            "retail_discount_pct": retail_discount_pct,
            "market_price": reference_price,
            "spread": spread,
            "spread_pct": spread_pct,
            "is_arbitrage": is_arbitrage,
            "url": item["url"],
            "image_url": item.get("image_url", ""),
            "watchcharts_url": watchcharts_url,
        }
        opportunities.append(opportunity)
    
    return opportunities


def main():
    """Main entry point for watch scanner."""
    # Load environment
    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    
    try:
        env = load_env()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    ebay_oauth = env.get("EBAY_OAUTH")
    openrouter_key = env.get("OPENROUTER_API_KEY", "")
    watchcharts_key = env.get("WATCHCHARTS_API_KEY", "")
    
    if not ebay_oauth:
        print("Error: EBAY_OAUTH not found in .env.local")
        sys.exit(1)
    
    if not openrouter_key:
        print("Warning: OPENROUTER_API_KEY not found. AI metadata extraction will be disabled.")
        print("  Add OPENROUTER_API_KEY to .env.local to enable AI extraction.")
    
    if not watchcharts_key:
        print("Info: WATCHCHARTS_API_KEY not found. WatchCharts API will be skipped.")
        print("  WatchCharts web scraping will be used instead (free).")
        print("  Add WATCHCHARTS_API_KEY to .env.local to enable WatchCharts API (paid).")
    
    # Get parameters
    search_query = "Rolex Submariner"
    brand_filter = None
    limit = 20
    tax_rate = 0.09
    min_spread_pct = 10.0
    
    if len(sys.argv) > 1:
        search_query = sys.argv[1]
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    if len(sys.argv) > 3:
        brand_filter = sys.argv[3]
    if len(sys.argv) > 4:
        min_spread_pct = float(sys.argv[4])
    
    print("=" * 70)
    print("Watch eBay Arbitrage Scanner")
    print("=" * 70)
    print(f"Search Query: {search_query}")
    if brand_filter:
        print(f"Brand Filter: {brand_filter}")
    print(f"Limit: {limit} listings")
    print(f"Minimum Spread: {min_spread_pct}%")
    print()
    
    # Step 1: Search eBay
    print("Step 1: Searching eBay for watches...")
    items = search_watches(
        search_query=search_query,
        limit=limit,
        env=env,
        brand_filter=brand_filter
    )
    print(f"Found {len(items)} watch listings")
    print()
    
    # Step 2: Analyze for arbitrage
    print("Step 2: Analyzing listings and looking up market prices...")
    print()
    
    # Use WatchCharts API if key available, otherwise use scraping (free)
    use_watchcharts_api = bool(watchcharts_key)
    
    opportunities = analyze_watch_arbitrage(
        items,
        tax_rate=tax_rate,
        env=env,
        min_spread_pct=min_spread_pct
    )
    
    # Step 3: Display results
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    # Save to CSV
    csv_filename = "data/watches.csv"
    os.makedirs("data", exist_ok=True)
    
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item_id", "title", "brand", "model", "model_number", "condition",
            "ebay_price", "shipping", "est_tax", "all_in_cost",
            "market_price", "spread", "spread_pct", "is_arbitrage",
            "url", "image_url"
        ])
        for opp in opportunities:
            writer.writerow([
                opp.get("item_id", ""),
                opp.get("title", ""),
                opp.get("brand", ""),
                opp.get("model", ""),
                opp.get("model_number", ""),
                opp.get("condition", ""),
                opp.get("ebay_price", 0),
                opp.get("shipping", 0),
                opp.get("est_tax", 0),
                opp.get("all_in_cost", 0),
                opp.get("market_price") or "",
                opp.get("spread") or "",
                opp.get("spread_pct") or "",
                opp.get("is_arbitrage", False),
                opp.get("url", ""),
                opp.get("image_url", ""),
            ])
    
    print(f"Saved {len(opportunities)} items to {csv_filename}")
    
    # Filter arbitrage opportunities
    arbitrage_deals = [o for o in opportunities if o.get("is_arbitrage")]
    
    # Sort by spread percentage (highest first)
    all_opportunities = sorted(
        opportunities,
        key=lambda x: x.get("spread_pct") if x.get("spread_pct") is not None else float('-inf'),
        reverse=True
    )
    
    # Display table
    table_data = []
    for opp in all_opportunities[:20]:  # Show first 20
        title = opp["title"][:50] if len(opp["title"]) > 50 else opp["title"]
        market = f"${opp['market_price']:.2f}" if opp.get("market_price") else "N/A"
        spread = f"${opp['spread']:.2f}" if opp.get("spread") is not None else "N/A"
        spread_pct = f"{opp['spread_pct']:.1f}%" if opp.get("spread_pct") is not None else "N/A"
        
        table_data.append([
            title,
            opp.get("brand", "N/A"),
            opp.get("model", "N/A"),
            f"${opp['ebay_price']:.2f}",
            f"${opp['all_in_cost']:.2f}",
            market,
            spread,
            spread_pct,
            "ARBITRAGE" if opp.get("is_arbitrage") else "No",
        ])
    
    headers = ["Title", "Brand", "Model", "Price", "All-In Cost", "Market Price", "Spread", "Spread %", "Arbitrage"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    if arbitrage_deals:
        print(f"\n[SUCCESS] Found {len(arbitrage_deals)} arbitrage opportunities!")
        if arbitrage_deals:
            best_spread = max([o['spread_pct'] for o in arbitrage_deals if o.get('spread_pct')])
            print(f"  Best spread: {best_spread:.1f}%")
    else:
        print(f"\nNo arbitrage opportunities found (minimum spread: {min_spread_pct}%)")
        print(f"Note: Market prices are based on eBay sold listings and may vary.")


if __name__ == "__main__":
    main()

