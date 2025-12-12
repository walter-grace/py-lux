#!/usr/bin/env python3
"""
Amazon API Explorer - Dedicated app to explore Amazon API v3 capabilities
"""
from flask import Flask, render_template, jsonify, request
import os
from dotenv import load_dotenv
from lib.config import load_env
from lib.amazon_api import search_amazon_products, normalize_amazon_item
from lib.amazon_best_sellers import get_amazon_best_sellers, get_available_categories
import requests
import json
import traceback

load_dotenv(".env.local")
app = Flask(__name__, template_folder="templates")

# Store last results for report generation
last_search_results = {}
last_search_query = ""

@app.route('/')
def index():
    """Main page"""
    return render_template('amazon_explorer.html')

@app.route('/api/search', methods=['POST'])
def search():
    """Search Amazon products"""
    global last_search_results, last_search_query
    
    try:
        data = request.json
        query = data.get('query', '').strip()
        max_results = int(data.get('max_results', 20))
        country = data.get('country', 'us')
        sort = data.get('sort', 'Featured')
        page = int(data.get('page', 1))
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        env = load_env()
        items = search_amazon_products(
            query=query,
            max_items=max_results,
            env=env,
            country=country,
            page=page,
            sort=sort
        )
        
        last_search_results = {'search': items}
        last_search_query = query
        
        return jsonify({
            'items': items,
            'count': len(items),
            'query': query
        })
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/product-details', methods=['POST'])
def product_details():
    """Get detailed product information by ASIN"""
    try:
        data = request.json
        asin = data.get('asin', '').strip()
        country = data.get('country', 'us')
        
        if not asin:
            return jsonify({'error': 'ASIN is required'}), 400
        
        env = load_env()
        api_key = env.get("RAPIDAPI_KEY")
        
        if not api_key:
            return jsonify({'error': 'RAPIDAPI_KEY not configured'}), 500
        
        # Try v3 product details endpoint
        url = "https://real-time-amazon-data.p.rapidapi.com/product-details"
        headers = {
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        params = {
            "asin": asin,
            "country": country.upper()
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 404:
            return jsonify({'error': 'Product not found'}), 404
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
        
        product_data = response.json()
        
        # Save for debugging
        os.makedirs('data', exist_ok=True)
        with open(f'data/amazon_product_details_{asin}.json', 'w', encoding='utf-8') as f:
            json.dump(product_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'product': product_data,
            'asin': asin
        })
    except Exception as e:
        print(f"[ERROR] Product details failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/product-reviews', methods=['POST'])
def product_reviews():
    """Get product reviews"""
    try:
        data = request.json
        asin = data.get('asin', '').strip()
        country = data.get('country', 'us')
        page = int(data.get('page', 1))
        
        if not asin:
            return jsonify({'error': 'ASIN is required'}), 400
        
        env = load_env()
        api_key = env.get("RAPIDAPI_KEY")
        
        if not api_key:
            return jsonify({'error': 'RAPIDAPI_KEY not configured'}), 500
        
        url = "https://real-time-amazon-data.p.rapidapi.com/product-reviews"
        headers = {
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        params = {
            "asin": asin,
            "country": country.upper(),
            "page": str(page)
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
        
        reviews_data = response.json()
        
        # Save for debugging
        os.makedirs('data', exist_ok=True)
        with open(f'data/amazon_reviews_{asin}.json', 'w', encoding='utf-8') as f:
            json.dump(reviews_data, f, indent=2, ensure_ascii=False)
        print(f"[DEBUG] Reviews response saved to: data/amazon_reviews_{asin}.json")
        
        return jsonify({
            'reviews': reviews_data,
            'asin': asin,
            'page': page
        })
    except Exception as e:
        print(f"[ERROR] Product reviews failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/product-offers', methods=['POST'])
def product_offers():
    """Get all offers for a product (multiple sellers)"""
    try:
        data = request.json
        asin = data.get('asin', '').strip()
        country = data.get('country', 'us')
        
        if not asin:
            return jsonify({'error': 'ASIN is required'}), 400
        
        env = load_env()
        api_key = env.get("RAPIDAPI_KEY")
        
        if not api_key:
            return jsonify({'error': 'RAPIDAPI_KEY not configured'}), 500
        
        url = "https://real-time-amazon-data.p.rapidapi.com/product-offers"
        headers = {
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        params = {
            "asin": asin,
            "country": country.upper()
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
        
        offers_data = response.json()
        
        return jsonify({
            'offers': offers_data,
            'asin': asin
        })
    except Exception as e:
        print(f"[ERROR] Product offers failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/products-by-category', methods=['POST'])
def products_by_category():
    """Get products by category"""
    try:
        data = request.json
        category = data.get('category', '').strip()
        country = data.get('country', 'us')
        page = int(data.get('page', 1))
        
        if not category:
            return jsonify({'error': 'Category is required'}), 400
        
        env = load_env()
        api_key = env.get("RAPIDAPI_KEY")
        
        if not api_key:
            return jsonify({'error': 'RAPIDAPI_KEY not configured'}), 500
        
        url = "https://real-time-amazon-data.p.rapidapi.com/products-by-category"
        headers = {
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        params = {
            "category": category,
            "country": country.upper(),
            "page": str(page)
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
        
        products_data = response.json()
        
        return jsonify({
            'products': products_data,
            'category': category,
            'page': page
        })
    except Exception as e:
        print(f"[ERROR] Products by category failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/deals', methods=['POST'])
def deals():
    """Get current Amazon deals"""
    try:
        data = request.json
        country = data.get('country', 'us')
        page = int(data.get('page', 1))
        
        env = load_env()
        api_key = env.get("RAPIDAPI_KEY")
        
        if not api_key:
            return jsonify({'error': 'RAPIDAPI_KEY not configured'}), 500
        
        url = "https://real-time-amazon-data.p.rapidapi.com/deals"
        headers = {
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        params = {
            "country": country.upper(),
            "page": str(page)
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
        
        deals_data = response.json()
        
        return jsonify({
            'deals': deals_data,
            'page': page
        })
    except Exception as e:
        print(f"[ERROR] Deals failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/best-sellers', methods=['POST'])
def best_sellers():
    """Get Amazon best sellers by category"""
    try:
        data = request.json
        category = data.get('category', 'electronics')
        country = data.get('country', 'us')
        page = int(data.get('page', 1))
        max_items = int(data.get('max_items', 50))
        
        env = load_env()
        items = get_amazon_best_sellers(
            category=category,
            env=env,
            country=country,
            page=page,
            max_items=max_items
        )
        
        return jsonify({
            'items': items,
            'count': len(items),
            'category': category
        })
    except Exception as e:
        print(f"[ERROR] Best sellers failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
def categories():
    """Get available categories"""
    try:
        return jsonify({
            'categories': get_available_categories()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/seller-products', methods=['POST'])
def seller_products():
    """Get products from a specific seller"""
    try:
        data = request.json
        seller_id = data.get('seller_id', '').strip()
        country = data.get('country', 'us')
        page = int(data.get('page', 1))
        
        if not seller_id:
            return jsonify({'error': 'Seller ID is required'}), 400
        
        env = load_env()
        api_key = env.get("RAPIDAPI_KEY")
        
        if not api_key:
            return jsonify({'error': 'RAPIDAPI_KEY not configured'}), 500
        
        url = "https://real-time-amazon-data.p.rapidapi.com/seller-products"
        headers = {
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        params = {
            "seller_id": seller_id,
            "country": country.upper(),
            "page": str(page)
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
        
        seller_data = response.json()
        
        return jsonify({
            'products': seller_data,
            'seller_id': seller_id,
            'page': page
        })
    except Exception as e:
        print(f"[ERROR] Seller products failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/influencer-profile', methods=['POST'])
def influencer_profile():
    """Get influencer profile information"""
    try:
        data = request.json
        influencer_id = data.get('influencer_id', '').strip()
        country = data.get('country', 'us')
        
        if not influencer_id:
            return jsonify({'error': 'Influencer ID is required'}), 400
        
        env = load_env()
        api_key = env.get("RAPIDAPI_KEY")
        
        if not api_key:
            return jsonify({'error': 'RAPIDAPI_KEY not configured'}), 500
        
        url = "https://real-time-amazon-data.p.rapidapi.com/influencer-profile"
        headers = {
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        params = {
            "influencer_id": influencer_id,
            "country": country.upper()
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
        
        profile_data = response.json()
        
        # Save for debugging
        os.makedirs('data', exist_ok=True)
        with open(f'data/amazon_influencer_profile_{influencer_id}.json', 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        print(f"[DEBUG] Influencer profile saved to: data/amazon_influencer_profile_{influencer_id}.json")
        
        return jsonify({
            'profile': profile_data,
            'influencer_id': influencer_id
        })
    except Exception as e:
        print(f"[ERROR] Influencer profile failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/influencer-posts', methods=['POST'])
def influencer_posts():
    """Get posts from an influencer"""
    try:
        data = request.json
        influencer_id = data.get('influencer_id', '').strip()
        country = data.get('country', 'us')
        page = int(data.get('page', 1))
        
        if not influencer_id:
            return jsonify({'error': 'Influencer ID is required'}), 400
        
        env = load_env()
        api_key = env.get("RAPIDAPI_KEY")
        
        if not api_key:
            return jsonify({'error': 'RAPIDAPI_KEY not configured'}), 500
        
        url = "https://real-time-amazon-data.p.rapidapi.com/influencer-posts"
        headers = {
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        params = {
            "influencer_id": influencer_id,
            "country": country.upper(),
            "page": str(page)
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
        
        posts_data = response.json()
        
        # Save for debugging
        os.makedirs('data', exist_ok=True)
        with open(f'data/amazon_influencer_posts_{influencer_id}.json', 'w', encoding='utf-8') as f:
            json.dump(posts_data, f, indent=2, ensure_ascii=False)
        print(f"[DEBUG] Influencer posts saved to: data/amazon_influencer_posts_{influencer_id}.json")
        
        return jsonify({
            'posts': posts_data,
            'influencer_id': influencer_id,
            'page': page
        })
    except Exception as e:
        print(f"[ERROR] Influencer posts failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/influencer-post-products', methods=['POST'])
def influencer_post_products():
    """Get products featured in an influencer post"""
    try:
        data = request.json
        post_id = data.get('post_id', '').strip()
        country = data.get('country', 'us')
        
        if not post_id:
            return jsonify({'error': 'Post ID is required'}), 400
        
        env = load_env()
        api_key = env.get("RAPIDAPI_KEY")
        
        if not api_key:
            return jsonify({'error': 'RAPIDAPI_KEY not configured'}), 500
        
        url = "https://real-time-amazon-data.p.rapidapi.com/influencer-post-products"
        headers = {
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        params = {
            "post_id": post_id,
            "country": country.upper()
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
        
        products_data = response.json()
        
        # Save for debugging
        os.makedirs('data', exist_ok=True)
        with open(f'data/amazon_influencer_post_products_{post_id}.json', 'w', encoding='utf-8') as f:
            json.dump(products_data, f, indent=2, ensure_ascii=False)
        print(f"[DEBUG] Influencer post products saved to: data/amazon_influencer_post_products_{post_id}.json")
        
        return jsonify({
            'products': products_data,
            'post_id': post_id
        })
    except Exception as e:
        print(f"[ERROR] Influencer post products failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("Amazon API Explorer")
    print("=" * 70)
    print("Starting server on http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    app.run(debug=True, port=5001)

