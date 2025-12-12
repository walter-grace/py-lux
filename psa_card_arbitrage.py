#!/usr/bin/env python3
"""
PSA Card Arbitrage Web App - eBay + PSA Integration
Specialized tool for finding arbitrage opportunities in PSA-graded trading cards
"""
from flask import Flask, render_template, jsonify, request
import os
from dotenv import load_dotenv
from lib.config import load_env
from lib.ebay_api import search_ebay_generic, EbayItem
from lib.psa_api import fetch_psa_cert
from lib.research_agent import scrape_psa_estimate, analyze_arbitrage_opportunities
from lib.ebay_oauth import get_oauth_token
from lib.watch_api import extract_watch_metadata, get_watch_reference_price
from scanners.watch_scanner import search_watches, analyze_watch_arbitrage
from typing import Optional, List, Dict, Any
import re
import traceback

load_dotenv(".env.local")
app = Flask(__name__, template_folder="templates")

@app.route('/')
def index():
    """Main page"""
    return render_template('psa_card_arbitrage.html')

@app.route('/watches')
def watches():
    """Watches page"""
    return render_template('psa_card_arbitrage.html', active_tab='watches')

@app.route('/api/get-ebay-token', methods=['POST'])
def get_ebay_token():
    """Automatically get eBay OAuth token using Client Credentials"""
    try:
        data = request.json or {}
        environment = data.get('environment', 'production')
        
        # Try to get token automatically
        token = get_oauth_token(environment=environment)
        
        if token:
            return jsonify({
                'success': True,
                'token': token,
                'message': 'Token obtained successfully! Add this to your .env.local as EBAY_OAUTH'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to get token. Make sure EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are set in .env.local'
            }), 400
            
    except Exception as e:
        print(f"[ERROR] Get token failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search():
    """Search eBay for PSA cards and check PSA data"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        max_results = int(data.get('max_results', 20))
        game = data.get('game', '').strip().lower()  # yugioh or pokemon
        year = data.get('year', '').strip() or None
        check_psa = data.get('check_psa', True)  # Whether to check PSA data
        enable_ai = data.get('enable_ai', True)  # Whether to enable AI analysis
        
        env = load_env()
        
        # Build the search query using filters
        query_parts = []
        
        # Add game filter if specified
        if game:
            if game == 'yugioh':
                query_parts.append('yugioh')
            elif game == 'pokemon':
                query_parts.append('pokemon')
        
        # Add user's query text
        if query:
            query_parts.append(query)
        else:
            # Default query if nothing entered
            query_parts.append('PSA')
        
        # Add year filter if specified
        if year:
            query_parts.append(year)
        
        # Build final query
        final_query = ' '.join(query_parts)
        
        # Search eBay
        print(f"[DEBUG] Searching eBay for: {final_query} (game={game}, year={year})")
        ebay_items = search_ebay_generic(
            query=final_query,
            limit=max_results * 2,  # Get more results to filter
            env=env,
            category_ids="183454",  # Trading Cards category
            filters="buyingOptions:{FIXED_PRICE}"
        )
        
        print(f"[DEBUG] Found {len(ebay_items)} eBay items before filtering")
        
        # Filter results by game type if specified
        if game:
            filtered_items = []
            for item in ebay_items:
                title_lower = item.get('title', '').lower()
                # Check if title matches game type
                if game == 'yugioh':
                    # Must contain yugioh-related terms and NOT pokemon
                    if any(term in title_lower for term in ['yugioh', 'yu-gi-oh', 'yugio', 'blue-eyes', 'dark magician', 'exodia']) and 'pokemon' not in title_lower:
                        filtered_items.append(item)
                elif game == 'pokemon':
                    # Must contain pokemon-related terms and NOT yugioh
                    if 'pokemon' in title_lower and not any(term in title_lower for term in ['yugioh', 'yu-gi-oh', 'yugio']):
                        filtered_items.append(item)
            ebay_items = filtered_items[:max_results]  # Limit to max_results
            print(f"[DEBUG] Filtered to {len(ebay_items)} items matching game type '{game}'")
        
        # Extract cert numbers, check PSA data, scrape estimates, and calculate arbitrage
        results = []
        psa_checked = 0
        tax_rate = 0.09  # 9% estimated tax rate
        
        for item in ebay_items:
            # Try to extract cert number from title or aspects
            cert_number = extract_cert_from_item(item)
            
            psa_data = None
            psa_estimate = None
            spread = None
            spread_pct = None
            is_undervalued = False
            
            if check_psa and cert_number:
                print(f"[DEBUG] Checking PSA cert: {cert_number}")
                psa_data = fetch_psa_cert(cert_number, env)
                psa_checked += 1
                
                # Scrape PSA estimated value (not available in API, need to scrape)
                if cert_number:
                    print(f"[DEBUG] Scraping PSA estimate for cert: {cert_number}")
                    try:
                        psa_estimate = scrape_psa_estimate(cert_number, ebay_url=item.get('url'))
                        if psa_estimate:
                            print(f"[DEBUG] ✅ Found PSA estimate: ${psa_estimate:.2f}")
                        else:
                            print(f"[DEBUG] ⚠️ No PSA estimate found for cert {cert_number}")
                    except Exception as e:
                        print(f"[WARNING] Error scraping PSA estimate: {e}")
            
            # Calculate total cost (price + shipping + estimated tax)
            est_tax = round(tax_rate * item['price'], 2)
            total_cost = item['price'] + item['shipping'] + est_tax
            
            # Calculate arbitrage if we have PSA estimate
            if psa_estimate and psa_estimate > 0:
                spread = round(psa_estimate - total_cost, 2)
                spread_pct = round((spread / psa_estimate * 100) if psa_estimate > 0 else 0, 2)
                is_undervalued = spread > 0  # Positive spread = undervalued
            
            result = {
                'item_id': item['item_id'],
                'title': item['title'],
                'url': item['url'],
                'price': item['price'],
                'shipping': item['shipping'],
                'est_tax': est_tax,
                'total_cost': total_cost,
                'image_url': item.get('image_url', ''),
                'cert_number': cert_number,
                'psa_data': psa_data,
                'psa_estimate': psa_estimate,
                'spread': spread,
                'spread_pct': spread_pct,
                'is_undervalued': is_undervalued,
                'seller': item.get('seller_username', ''),
                'condition': item.get('item_condition', ''),
            }
            
            results.append(result)
        
        # Use LLM to analyze and identify best undervalued opportunities (if enabled)
        undervalued_cards = [r for r in results if r.get('is_undervalued')]
        if enable_ai and undervalued_cards and env.get('OPENROUTER_API_KEY'):
            print(f"[DEBUG] 🤖 Analyzing {len(undervalued_cards)} undervalued cards with LLM...")
            try:
                # Prepare data for LLM analysis
                llm_listings = []
                for card in undervalued_cards:
                    llm_listings.append({
                        'cert_number': card.get('cert_number'),
                        'title': card.get('title'),
                        'price': card.get('price'),
                        'shipping': card.get('shipping'),
                        'url': card.get('url'),
                        'psa_estimate': card.get('psa_estimate'),
                        'spread': card.get('spread'),
                        'spread_pct': card.get('spread_pct'),
                    })
                
                # Analyze with LLM (this will enhance the opportunities)
                analyzed = analyze_arbitrage_opportunities(
                    llm_listings,
                    env.get('OPENROUTER_API_KEY'),
                    tax_rate=tax_rate,
                    model="moonshotai/kimi-k2-thinking"
                )
                
                # Update results with LLM insights
                analyzed_dict = {a['cert_number']: a for a in analyzed if a.get('cert_number')}
                for result in results:
                    if result.get('cert_number') in analyzed_dict:
                        analyzed_data = analyzed_dict[result['cert_number']]
                        # Add any additional insights from LLM analysis
                        result['llm_analyzed'] = True
                        result['llm_spread'] = analyzed_data.get('spread')
                        result['llm_spread_pct'] = analyzed_data.get('spread_pct')
                        result['ai_insights'] = analyzed_data.get('ai_insights')  # Add AI insights
            except Exception as e:
                print(f"[WARNING] LLM analysis failed: {e}")
                traceback.print_exc()
        
        # Sort results: undervalued cards first, then by spread percentage (highest first)
        results.sort(key=lambda x: (
            not x.get('is_undervalued', False),  # Undervalued first
            -(x.get('spread_pct') or 0)  # Then by spread % (highest first)
        ))
        
        # Calculate statistics
        undervalued_count = len([r for r in results if r.get('is_undervalued')])
        cards_with_estimate = len([r for r in results if r.get('psa_estimate')])
        total_potential_profit = sum([r.get('spread', 0) for r in results if r.get('is_undervalued')])
        
        return jsonify({
            'items': results,
            'count': len(results),
            'psa_checked': psa_checked,
            'undervalued_count': undervalued_count,
            'cards_with_estimate': cards_with_estimate,
            'total_potential_profit': total_potential_profit,
            'query': final_query,
            'filters_applied': {
                'game': game if game else None,
                'year': year
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-psa', methods=['POST'])
def check_psa():
    """Check PSA data for a specific cert number"""
    try:
        data = request.json
        cert_number = data.get('cert_number', '').strip()
        
        if not cert_number:
            return jsonify({'error': 'Cert number is required'}), 400
        
        env = load_env()
        psa_data = fetch_psa_cert(cert_number, env)
        
        return jsonify({
            'cert_number': cert_number,
            'psa_data': psa_data
        })
        
    except Exception as e:
        print(f"[ERROR] PSA check failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-analyze', methods=['POST'])
def ai_analyze():
    """AI analysis endpoint for analyzing undervalued cards"""
    try:
        data = request.json
        items = data.get('items', [])
        
        if not items:
            return jsonify({'error': 'No items provided'}), 400
        
        env = load_env()
        api_key = env.get('OPENROUTER_API_KEY')
        
        if not api_key:
            return jsonify({'error': 'OPENROUTER_API_KEY not configured'}), 400
        
        # Filter to undervalued cards
        undervalued = [item for item in items if item.get('is_undervalued')]
        
        if not undervalued:
            return jsonify({
                'insights': 'No undervalued cards found to analyze.',
                'top_opportunities': []
            })
        
        # Prepare data for LLM analysis
        llm_listings = []
        for card in undervalued:
            llm_listings.append({
                'cert_number': card.get('cert_number'),
                'title': card.get('title'),
                'price': card.get('price'),
                'shipping': card.get('shipping'),
                'url': card.get('url'),
                'psa_estimate': card.get('psa_estimate'),
                'spread': card.get('spread'),
                'spread_pct': card.get('spread_pct'),
            })
        
        # Analyze with LLM using moonshotai/kimi-k2-thinking
        analyzed = analyze_arbitrage_opportunities(
            llm_listings,
            api_key,
            tax_rate=0.09,
            model="moonshotai/kimi-k2-thinking"
        )
        
        # Generate insights
        top_opportunities = []
        for opp in sorted(analyzed, key=lambda x: x.get('spread', 0), reverse=True)[:5]:
            title = opp.get('title', 'Unknown')[:50]
            spread = opp.get('spread', 0)
            spread_pct = opp.get('spread_pct', 0)
            top_opportunities.append(f"{title}: ${spread:.2f} profit ({spread_pct:.1f}%)")
        
        insights = f"AI analyzed {len(undervalued)} undervalued cards. Found {len(analyzed)} opportunities with total potential profit of ${sum([o.get('spread', 0) for o in analyzed]):.2f}."
        
        return jsonify({
            'insights': insights,
            'top_opportunities': top_opportunities,
            'analyzed_count': len(analyzed),
            'total_profit': sum([o.get('spread', 0) for o in analyzed])
        })
        
    except Exception as e:
        print(f"[ERROR] AI analysis failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/discover-card-types', methods=['POST'])
def discover_card_types():
    """Search eBay for various PSA card types and aggregate PSA data to discover available card types"""
    try:
        data = request.json
        max_per_category = int(data.get('max_per_category', 10))  # How many cards to check per search
        
        env = load_env()
        
        # Define various search queries to discover different card types
        search_queries = [
            # Trading Card Games
            "PSA 10 yugioh",
            "PSA 10 pokemon",
            "PSA 10 magic the gathering",
            "PSA 10 sports cards",
            "PSA 10 baseball",
            "PSA 10 basketball",
            "PSA 10 football",
            "PSA 10 hockey",
            "PSA 10 soccer",
            # Specific brands/sets
            "PSA 10 charizard",
            "PSA 10 blue eyes",
            "PSA 10 michael jordan",
            "PSA 10 topps",
            "PSA 10 panini",
            # Other collectibles
            "PSA 10 autograph",
            "PSA 10 rookie card",
        ]
        
        discovered_types = {
            'brands': set(),
            'categories': set(),
            'years': set(),
            'games': set(),
            'subjects': set(),
            'total_cards_checked': 0,
            'cards_with_psa_data': 0,
        }
        
        all_cards = []
        
        print(f"[DEBUG] Starting card type discovery with {len(search_queries)} search queries...")
        
        for query in search_queries:
            print(f"[DEBUG] Searching: {query}")
            
            try:
                # Search eBay
                ebay_items = search_ebay_generic(
                    query=query,
                    limit=max_per_category,
                    env=env,
                    category_ids="183454",
                    filters="buyingOptions:{FIXED_PRICE}"
                )
                
                # Check PSA data for each item
                for item in ebay_items:
                    cert_number = extract_cert_from_item(item)
                    
                    if cert_number:
                        print(f"[DEBUG] Checking PSA cert: {cert_number}")
                        psa_data = fetch_psa_cert(cert_number, env)
                        discovered_types['total_cards_checked'] += 1
                        
                        if psa_data.get('grade'):
                            discovered_types['cards_with_psa_data'] += 1
                            
                            # Aggregate data
                            if psa_data.get('brand'):
                                discovered_types['brands'].add(psa_data['brand'])
                            if psa_data.get('category'):
                                discovered_types['categories'].add(psa_data['category'])
                            if psa_data.get('year'):
                                discovered_types['years'].add(str(psa_data['year']))
                            if psa_data.get('subject'):
                                discovered_types['subjects'].add(psa_data['subject'])
                            
                            # Determine game type
                            brand = psa_data.get('brand', '').lower()
                            category = psa_data.get('category', '').lower()
                            if 'yugioh' in brand or 'yugioh' in category:
                                discovered_types['games'].add('Yu-Gi-Oh!')
                            elif 'pokemon' in brand or 'pokemon' in category:
                                discovered_types['games'].add('Pokemon')
                            elif 'magic' in brand or 'magic' in category:
                                discovered_types['games'].add('Magic: The Gathering')
                            elif any(sport in brand or sport in category for sport in ['baseball', 'basketball', 'football', 'hockey', 'soccer']):
                                discovered_types['games'].add('Sports Cards')
                            
                            # Store card data
                            all_cards.append({
                                'title': item['title'],
                                'cert_number': cert_number,
                                'psa_data': psa_data,
                                'ebay_url': item['url'],
                                'price': item['price'],
                            })
                
            except Exception as e:
                print(f"[ERROR] Error processing query '{query}': {e}")
                continue
        
        # Convert sets to sorted lists
        result = {
            'brands': sorted(list(discovered_types['brands'])),
            'categories': sorted(list(discovered_types['categories'])),
            'years': sorted(list(discovered_types['years']), key=lambda x: int(x) if x.isdigit() else 0),
            'games': sorted(list(discovered_types['games'])),
            'subjects': sorted(list(discovered_types['subjects']))[:50],  # Limit subjects
            'stats': {
                'total_cards_checked': discovered_types['total_cards_checked'],
                'cards_with_psa_data': discovered_types['cards_with_psa_data'],
                'unique_brands': len(discovered_types['brands']),
                'unique_categories': len(discovered_types['categories']),
                'unique_years': len(discovered_types['years']),
                'unique_games': len(discovered_types['games']),
            },
            'sample_cards': all_cards[:20],  # Return first 20 cards as samples
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[ERROR] Card type discovery failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def extract_cert_from_item(item: EbayItem) -> Optional[str]:
    """
    Extract PSA cert number from eBay item.
    Tries multiple methods: cert field, aspects, title, condition descriptors.
    """
    # Method 1: Check if cert is already extracted in item data
    if item.get('cert'):
        cert = str(item.get('cert')).strip()
        if re.match(r'^\d{6,9}$', cert):
            return cert
    
    # Method 2: Check aspects dictionary
    aspects = item.get('aspects', {})
    if isinstance(aspects, dict):
        for key, value in aspects.items():
            if any(keyword in key.lower() for keyword in ['cert', 'certification', 'psa']):
                if isinstance(value, str):
                    cert_str = value.strip()
                    if re.match(r'^\d{6,9}$', cert_str):
                        return cert_str
                elif isinstance(value, list) and value:
                    cert_str = str(value[0]).strip()
                    if re.match(r'^\d{6,9}$', cert_str):
                        return cert_str
    
    # Method 3: Extract from title using regex
    title = item.get('title', '')
    # Look for patterns like "PSA 12345678", "Cert #12345678", "S#4376", etc.
    patterns = [
        r'PSA\s*#?\s*(\d{6,9})',  # PSA 12345678 or PSA #12345678
        r'Cert\s*#?\s*(\d{6,9})',  # Cert #12345678
        r'Certification\s*#?\s*(\d{6,9})',  # Certification #12345678
        r'PSA\s+(\d{6,9})',  # PSA 12345678 (with space)
        r'S#(\d{4,9})',  # S#4376 (serial number format)
        r'Serial\s*#?\s*(\d{6,9})',  # Serial #12345678
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            cert = match.group(1).strip()
            if re.match(r'^\d{6,9}$', cert):  # Validate it's 6-9 digits
                return cert
    
    return None

@app.route('/api/search-watches', methods=['POST'])
def search_watches_api():
    """Search eBay for watches and check market prices"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        max_results = int(data.get('max_results', 20))
        brand_filter = data.get('brand_filter')
        if brand_filter:
            brand_filter = str(brand_filter).strip() or None
        else:
            brand_filter = None
        min_spread_pct = float(data.get('min_spread_pct', 10.0))
        
        env = load_env()
        
        # Search eBay for watches
        print(f"[DEBUG] Searching eBay for watches: {query}")
        items = search_watches(
            search_query=query,
            limit=max_results,
            env=env,
            brand_filter=brand_filter
        )
        
        print(f"[DEBUG] Found {len(items)} watch listings")
        
        # Analyze for arbitrage
        opportunities = analyze_watch_arbitrage(
            items,
            tax_rate=0.09,
            env=env,
            min_spread_pct=min_spread_pct
        )
        
        # Sort by spread percentage (highest first)
        opportunities.sort(key=lambda x: (
            not x.get('is_arbitrage', False),  # Arbitrage first
            -(x.get('spread_pct') or 0)  # Then by spread % (highest first)
        ))
        
        # Calculate statistics
        arbitrage_count = len([o for o in opportunities if o.get('is_arbitrage')])
        watches_with_price = len([o for o in opportunities if o.get('market_price')])
        watches_with_retail = len([o for o in opportunities if o.get('retail_price')])
        total_potential_profit = sum([o.get('spread', 0) for o in opportunities if o.get('is_arbitrage')])
        
        return jsonify({
            'items': opportunities,
            'count': len(opportunities),
            'arbitrage_count': arbitrage_count,
            'watches_with_price': watches_with_price,
            'watches_with_retail': watches_with_retail,
            'total_potential_profit': total_potential_profit,
            'query': query,
            'filters_applied': {
                'brand': brand_filter,
                'min_spread_pct': min_spread_pct
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Watch search failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("PSA Card Arbitrage Web App")
    print("=" * 70)
    print("Starting server on http://localhost:5002")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    app.run(debug=True, port=5002)

