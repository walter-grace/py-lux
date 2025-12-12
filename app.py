#!/usr/bin/env python3
"""
Arbitrage Finder Web App
A simple web interface to search eBay, Facebook Marketplace, and Amazon
and compare prices across all three platforms.
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from lib.config import load_env
from lib.ebay_api import search_ebay_generic
from lib.facebook_marketplace_api import search_facebook_marketplace
from lib.amazon_api import search_amazon_products
from lib.arbitrage_comparison import compare_all_platforms
from lib.amazon_best_sellers import get_amazon_best_sellers, get_available_categories
from reports.generate_luxury_html_report import generate_luxury_html_report

app = Flask(__name__)
app.config['SECRET_KEY'] = 'arbitrage-finder-secret-key'

# Global variable to store last search results
last_search_results = None
last_search_query = None


@app.route('/')
def index():
    """Main search page"""
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def search():
    """Search all three platforms"""
    global last_search_results, last_search_query
    
    data = request.json
    query = data.get('query', '').strip()
    max_results = int(data.get('max_results', 20))
    location = data.get('location', 'Los Angeles, CA')
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    env = load_env()
    results = {
        'query': query,
        'timestamp': datetime.now().isoformat(),
        'ebay': [],
        'facebook': [],
        'amazon': [],
        'errors': []
    }
    
    # Search eBay
    try:
        print(f"[DEBUG] Searching eBay for: {query}")
        ebay_items = search_ebay_generic(
            query=query,
            limit=min(max_results, 50),
            env=env
        )
        results['ebay'] = [{
            'item_id': item.get('item_id', ''),
            'title': item.get('title', ''),
            'price': item.get('price', 0),
            'shipping': item.get('shipping', 0),
            'all_in_cost': item.get('price', 0) + item.get('shipping', 0),
            'url': item.get('url', ''),
            'image_url': item.get('image_url', ''),
            'condition': item.get('item_condition', ''),
            'platform': 'eBay'
        } for item in ebay_items]
        print(f"Found {len(results['ebay'])} eBay items")
    except Exception as e:
        error_msg = f"eBay search error: {str(e)}"
        print(error_msg)
        results['errors'].append(error_msg)
    
    # Search Facebook Marketplace
    try:
        if env.get('RAPIDAPI_KEY'):
            print(f"[DEBUG] Searching Facebook Marketplace for: {query}")
            fb_items = search_facebook_marketplace(
                query=query,
                max_items=min(max_results, 10),  # Limit to conserve API calls
                env=env,
                location=location if location else None  # Optional location
            )
            results['facebook'] = [{
                'item_id': item.get('item_id', ''),
                'title': item.get('title', ''),
                'price': item.get('price', 0),
                'shipping': item.get('shipping', 0),
                'all_in_cost': item.get('price', 0) + item.get('shipping', 0),
                'url': item.get('url', ''),
                'image_url': item.get('image_url', ''),
                'condition': item.get('condition', ''),
                'platform': 'Facebook'
            } for item in fb_items]
            print(f"[DEBUG] Found {len(results['facebook'])} Facebook items")
            if len(results['facebook']) == 0:
                print(f"[DEBUG] WARNING: Facebook search returned 0 items for query: {query}")
                print(f"[DEBUG] This could mean:")
                print(f"  - No items found matching the query")
                print(f"  - API response format changed")
                print(f"  - Location filter too restrictive")
        else:
            error_msg = "Facebook Marketplace API key not configured"
            print(f"[ERROR] {error_msg}")
            results['errors'].append(error_msg)
    except Exception as e:
        error_msg = f"Facebook Marketplace search error: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        results['errors'].append(error_msg)
    
    # Search Amazon
    try:
        if env.get('RAPIDAPI_KEY'):
            print(f"[DEBUG] Searching Amazon for: {query}")
            amazon_items = search_amazon_products(
                query=query,
                max_items=min(max_results, 20),
                env=env
            )
            results['amazon'] = [{
                'item_id': item.get('item_id', ''),
                'title': item.get('title', ''),
                'price': item.get('price', 0),
                'shipping': item.get('shipping', 0),
                'all_in_cost': item.get('price', 0) + item.get('shipping', 0),
                'url': item.get('url', ''),
                'image_url': item.get('image_url', ''),
                'condition': item.get('condition', ''),
                'platform': 'Amazon'
            } for item in amazon_items]
            print(f"Found {len(results['amazon'])} Amazon items")
        else:
            results['errors'].append("Amazon API key not configured")
    except Exception as e:
        error_msg = f"Amazon search error: {str(e)}"
        print(error_msg)
        results['errors'].append(error_msg)
    
    # Perform cross-platform matching
    try:
        print(f"[DEBUG] Performing cross-platform matching...")
        print(f"[DEBUG] eBay items: {len(results['ebay'])}, Facebook items: {len(results['facebook'])}, Amazon items: {len(results['amazon'])}")
        
        # Convert results to format expected by comparison functions
        ebay_items = [{
            'item_id': item['item_id'],
            'title': item['title'],
            'price': item['price'],
            'shipping': item.get('shipping', 0),
            'url': item.get('url', ''),
            'condition': item.get('condition', ''),
        } for item in results['ebay']]
        
        fb_items = [{
            'item_id': item['item_id'],
            'title': item['title'],
            'price': item['price'],
            'shipping': item.get('shipping', 0),
            'url': item.get('url', ''),
            'condition': item.get('condition', ''),
        } for item in results['facebook']]
        
        amazon_items = [{
            'item_id': item['item_id'],
            'title': item['title'],
            'price': item['price'],
            'shipping': item.get('shipping', 0),
            'url': item.get('url', ''),
            'condition': item.get('condition', ''),
        } for item in results['amazon']]
        
        matches = compare_all_platforms(
            ebay_items=ebay_items,
            fb_items=fb_items,
            amazon_items=amazon_items,
            item_type="luxury"  # Default to luxury for web app
        )
        print(f"[DEBUG] Found {len(matches)} cross-platform matches")
        
        # Create lookup dictionaries for quick matching
        ebay_match_dict = {}
        fb_match_dict = {}
        amazon_match_dict = {}
        
        for match in matches:
            ebay_id = match['ebay_item']['item_id']
            ebay_match_dict[ebay_id] = match
            
            if match.get('facebook_item'):
                fb_id = match['facebook_item']['item_id']
                fb_match_dict[fb_id] = match
            
            if match.get('amazon_item'):
                amazon_id = match['amazon_item']['item_id']
                amazon_match_dict[amazon_id] = match
        
        # Add match info to eBay items
        for item in results['ebay']:
            if item['item_id'] in ebay_match_dict:
                match = ebay_match_dict[item['item_id']]
                # Build cross-platform match URLs
                match_urls = []
                if match.get('facebook_item', {}).get('url'):
                    match_urls.append(f"FB: {match['facebook_item']['url']}")
                if match.get('amazon_item', {}).get('url'):
                    match_urls.append(f"Amazon: {match['amazon_item']['url']}")
                item['cross_platform_match'] = ' | '.join(match_urls) if match_urls else ''
                item['price_difference'] = match.get('price_difference', 0)
                item['best_platform'] = match.get('best_platform', 'eBay')
        
        # Add match info to Facebook items
        for item in results['facebook']:
            if item['item_id'] in fb_match_dict:
                match = fb_match_dict[item['item_id']]
                match_urls = []
                if match.get('ebay_item', {}).get('url'):
                    match_urls.append(f"eBay: {match['ebay_item']['url']}")
                if match.get('amazon_item', {}).get('url'):
                    match_urls.append(f"Amazon: {match['amazon_item']['url']}")
                item['cross_platform_match'] = ' | '.join(match_urls) if match_urls else ''
                item['price_difference'] = match.get('price_difference', 0)
                item['best_platform'] = match.get('best_platform', 'Facebook')
        
        # Add match info to Amazon items
        for item in results['amazon']:
            if item['item_id'] in amazon_match_dict:
                match = amazon_match_dict[item['item_id']]
                match_urls = []
                if match.get('ebay_item', {}).get('url'):
                    match_urls.append(f"eBay: {match['ebay_item']['url']}")
                if match.get('facebook_item', {}).get('url'):
                    match_urls.append(f"FB: {match['facebook_item']['url']}")
                item['cross_platform_match'] = ' | '.join(match_urls) if match_urls else ''
                item['price_difference'] = match.get('price_difference', 0)
                item['best_platform'] = match.get('best_platform', 'Amazon')
                    
    except Exception as e:
        error_msg = f"Cross-platform matching error: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        results['errors'].append(error_msg)
    
    # Data quality checks
    data_quality_issues = []
    
    # Check for missing URLs
    fb_missing_urls = sum(1 for item in results['facebook'] if not item.get('url', '').strip())
    if fb_missing_urls > 0:
        data_quality_issues.append(f"⚠️ {fb_missing_urls} Facebook items missing URLs")
    
    ebay_missing_urls = sum(1 for item in results['ebay'] if not item.get('url', '').strip())
    if ebay_missing_urls > 0:
        data_quality_issues.append(f"⚠️ {ebay_missing_urls} eBay items missing URLs")
    
    amazon_missing_urls = sum(1 for item in results['amazon'] if not item.get('url', '').strip())
    if amazon_missing_urls > 0:
        data_quality_issues.append(f"⚠️ {amazon_missing_urls} Amazon items missing URLs")
    
    # Check for missing images
    missing_images = sum(1 for item in results['ebay'] + results['facebook'] + results['amazon'] if not item.get('image_url', '').strip())
    if missing_images > 0:
        data_quality_issues.append(f"⚠️ {missing_images} items missing images")
    
    # Check for missing prices
    missing_prices = sum(1 for item in results['ebay'] + results['facebook'] + results['amazon'] if not item.get('price', 0) or item.get('price', 0) == 0)
    if missing_prices > 0:
        data_quality_issues.append(f"⚠️ {missing_prices} items missing prices")
    
    if data_quality_issues:
        print(f"[WARNING] Data Quality Issues:")
        for issue in data_quality_issues:
            print(f"  {issue}")
        results['data_quality_warnings'] = data_quality_issues
    
    # Store results for HTML generation
    last_search_results = results
    last_search_query = query
    
    return jsonify(results)


@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    """Generate HTML report from search results"""
    global last_search_results, last_search_query
    
    if not last_search_results:
        return jsonify({'error': 'No search results available. Please search first.'}), 400
    
    # Convert results to CSV format for the HTML generator
    os.makedirs('data', exist_ok=True)
    csv_file = 'data/search_results.csv'
    
    import csv
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'item_id', 'title', 'brand', 'condition', 'is_new',
            'ebay_price', 'shipping', 'est_tax', 'all_in_cost',
            'retail_price', 'spread', 'spread_pct', 'is_arbitrage',
            'url', 'image_url', 'platform', 'cross_platform_match',
            'price_difference', 'best_platform'
        ])
        
        # Combine all items
        all_items = []
        for item in last_search_results['ebay']:
            all_items.append({
                'item_id': item['item_id'],
                'title': item['title'],
                'brand': '',
                'condition': item['condition'],
                'is_new': 'false',
                'ebay_price': item['price'],
                'shipping': item['shipping'],
                'est_tax': 0,
                'all_in_cost': item['all_in_cost'],
                'retail_price': '',
                'spread': '',
                'spread_pct': '',
                'is_arbitrage': 'false',
                'url': item['url'],
                'image_url': item['image_url'],
                'platform': 'eBay',
                'cross_platform_match': '',
                'price_difference': '',
                'best_platform': ''
            })
        
        for item in last_search_results['facebook']:
            all_items.append({
                'item_id': item['item_id'],
                'title': item['title'],
                'brand': '',
                'condition': item['condition'],
                'is_new': 'false',
                'ebay_price': item['price'],
                'shipping': item['shipping'],
                'est_tax': 0,
                'all_in_cost': item['all_in_cost'],
                'retail_price': '',
                'spread': '',
                'spread_pct': '',
                'is_arbitrage': 'false',
                'url': item['url'],
                'image_url': item['image_url'],
                'platform': 'Facebook',
                'cross_platform_match': '',
                'price_difference': '',
                'best_platform': ''
            })
        
        for item in last_search_results['amazon']:
            all_items.append({
                'item_id': item['item_id'],
                'title': item['title'],
                'brand': '',
                'condition': item.get('condition', 'New'),
                'is_new': 'true',  # Amazon items are typically new
                'ebay_price': item['price'],
                'shipping': item['shipping'],
                'est_tax': 0,
                'all_in_cost': item['all_in_cost'],
                'retail_price': str(item['price']),  # Amazon price is often retail
                'spread': '',
                'spread_pct': '',
                'is_arbitrage': 'false',
                'url': item['url'],
                'image_url': item.get('image_url', ''),
                'platform': 'Amazon',
                'cross_platform_match': '',
                'price_difference': '',
                'best_platform': ''
            })
        
        # Write to CSV
        for item in all_items:
            writer.writerow([
                item['item_id'],
                item['title'],
                item['brand'],
                item['condition'],
                item['is_new'],
                item['ebay_price'],
                item['shipping'],
                item['est_tax'],
                item['all_in_cost'],
                item['retail_price'],
                item['spread'],
                item['spread_pct'],
                item['is_arbitrage'],
                item['url'],
                item['image_url'],
                item['platform'],
                item['cross_platform_match'],
                item['price_difference'],
                item['best_platform']
            ])
    
    # Generate HTML report
    output_file = f'data/search_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    generate_luxury_html_report(csv_file=csv_file, output_file=output_file)
    
    return jsonify({
        'success': True,
        'report_file': output_file,
        'message': 'Report generated successfully'
    })


@app.route('/api/trending', methods=['GET'])
def get_trending():
    """Get Amazon trending items (best sellers)"""
    category = request.args.get('category', 'shoes')
    max_items = int(request.args.get('max_items', 20))
    
    env = load_env()
    
    try:
        trending_items = get_amazon_best_sellers(
            category=category,
            env=env,
            max_items=max_items
        )
        
        # Format for frontend
        formatted_items = [{
            'title': item['title'],
            'price': float(item.get('price', 0)),  # Ensure price is a float
            'url': item.get('url', ''),
            'image_url': item.get('image_url', ''),
            'rank': item.get('rank', ''),
            'asin': item.get('asin', '')
        } for item in trending_items]
        
        return jsonify({
            'success': True,
            'category': category,
            'items': formatted_items
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get available Amazon categories"""
    return jsonify({
        'categories': get_available_categories()
    })


@app.route('/report/<filename>')
def view_report(filename):
    """View generated report"""
    filepath = os.path.join('data', filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    return "Report not found", 404


if __name__ == '__main__':
    print("=" * 70)
    print("Arbitrage Finder Web App")
    print("=" * 70)
    print("Starting server...")
    print("Open your browser and go to: http://localhost:5000")
    print("=" * 70)
    app.run(debug=True, host='0.0.0.0', port=5000)

