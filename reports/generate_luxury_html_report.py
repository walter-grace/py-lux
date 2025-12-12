#!/usr/bin/env python3
"""
Generate a beautiful HTML report from the luxury_items.csv file
"""

import csv
import sys
import os
from datetime import datetime

# Add parent directory to path for data files
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def generate_luxury_html_report(csv_file='data/luxury_items.csv', output_file='data/luxury_items_report.html'):
    """Generate an HTML report from luxury items CSV data"""
    
    # Read CSV data
    items = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(row)
    
    # Calculate statistics
    total_items = len(items)
    items_with_retail = [i for i in items if i.get('retail_price') and i.get('retail_price').strip()]
    items_without_retail = [i for i in items if not i.get('retail_price') or not i.get('retail_price').strip()]
    arbitrage_items = [i for i in items if i.get('is_arbitrage', '').lower() == 'true']
    new_items = [i for i in items if i.get('is_new', '').lower() == 'true']
    
    # Platform statistics
    ebay_items = [i for i in items if i.get('platform', 'eBay') == 'eBay']
    facebook_items = [i for i in items if i.get('platform') == 'Facebook']
    amazon_items = [i for i in items if i.get('platform') == 'Amazon']
    cross_platform_matches = [i for i in items if i.get('cross_platform_match')]
    
    # Group items by title to show all platforms together
    items_by_title = {}
    for item in items:
        title = item.get('title', '').lower().strip()
        # Use first 50 chars as key for grouping similar items
        title_key = title[:50] if len(title) > 50 else title
        if title_key not in items_by_title:
            items_by_title[title_key] = {
                'ebay': None,
                'facebook': None,
                'amazon': None,
                'title': item.get('title', ''),
                'brand': item.get('brand', ''),
            }
        
        platform = item.get('platform', 'eBay').lower()
        if platform == 'ebay':
            items_by_title[title_key]['ebay'] = item
        elif platform == 'facebook':
            items_by_title[title_key]['facebook'] = item
        elif platform == 'amazon':
            items_by_title[title_key]['amazon'] = item
    
    # Calculate spread statistics
    spreads = []
    for item in items_with_retail:
        try:
            spread = float(item.get('spread', 0) or 0)
            if spread > 0:
                spreads.append(spread)
        except (ValueError, TypeError):
            pass
    
    best_spread = max(spreads) if spreads else 0
    worst_spread = min(spreads) if spreads else 0
    avg_spread = sum(spreads) / len(spreads) if spreads else 0
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Luxury Items Arbitrage Scanner - Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #f5576c;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card.positive .stat-value {{
            color: #10b981;
        }}
        
        .stat-card.negative .stat-value {{
            color: #ef4444;
        }}
        
        .controls {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .control-group label {{
            font-weight: 600;
            color: #555;
        }}
        
        .control-group select,
        .control-group input {{
            padding: 8px 12px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s;
        }}
        
        .control-group select:focus,
        .control-group input:focus {{
            outline: none;
            border-color: #f5576c;
        }}
        
        .table-container {{
            overflow-x: auto;
            padding: 20px 30px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        
        thead {{
            background: #f5576c;
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        tbody tr {{
            transition: background-color 0.2s;
        }}
        
        tbody tr:hover {{
            background-color: #f8f9fa;
        }}
        
        tbody tr.arbitrage {{
            background-color: #d1fae5;
        }}
        
        tbody tr.arbitrage:hover {{
            background-color: #a7f3d0;
        }}
        
        tbody tr.no-retail {{
            background-color: #fef3c7;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .badge.arbitrage {{
            background: #10b981;
            color: white;
        }}
        
        .badge.no-arbitrage {{
            background: #ef4444;
            color: white;
        }}
        
        .badge.no-retail {{
            background: #f59e0b;
            color: white;
        }}
        
        .badge.new {{
            background: #3b82f6;
            color: white;
        }}
        
        .price {{
            font-weight: 600;
            color: #f5576c;
        }}
        
        .spread-positive {{
            color: #10b981;
            font-weight: 600;
        }}
        
        .spread-negative {{
            color: #ef4444;
            font-weight: 600;
        }}
        
        .footer {{
            padding: 20px 30px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
            background: #f8f9fa;
        }}
        
        .item-link {{
            color: #f5576c;
            text-decoration: none;
            font-weight: 500;
        }}
        
        .item-link:hover {{
            text-decoration: underline;
        }}
        
        img {{
            transition: transform 0.2s;
        }}
        
        img:hover {{
            transform: scale(1.1);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .stats {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .table-container {{
                padding: 10px;
            }}
            
            table {{
                font-size: 12px;
            }}
            
            th, td {{
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Luxury Items Arbitrage Scanner</h1>
            <p>Report Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{total_items}</div>
                <div class="stat-label">Total Items</div>
            </div>
            <div class="stat-card positive">
                <div class="stat-value">{len(items_with_retail)}</div>
                <div class="stat-label">With Retail Prices</div>
            </div>
            <div class="stat-card negative">
                <div class="stat-value">{len(items_without_retail)}</div>
                <div class="stat-label">No Retail Price</div>
            </div>
            <div class="stat-card {'positive' if len(arbitrage_items) > 0 else 'negative'}">
                <div class="stat-value">{len(arbitrage_items)}</div>
                <div class="stat-label">Arbitrage Opportunities</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(new_items)}</div>
                <div class="stat-label">New Items</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(ebay_items)}</div>
                <div class="stat-label">eBay Listings</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(facebook_items)}</div>
                <div class="stat-label">Facebook Listings</div>
            </div>
            <div class="stat-card positive">
                <div class="stat-value">{len(cross_platform_matches)}</div>
                <div class="stat-label">Cross-Platform Matches</div>
            </div>
            {f'''
            <div class="stat-card positive">
                <div class="stat-value">${best_spread:,.2f}</div>
                <div class="stat-label">Best Spread</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${avg_spread:,.2f}</div>
                <div class="stat-label">Average Spread</div>
            </div>
            ''' if spreads else ''}
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label for="filter">Filter:</label>
                <select id="filter" onchange="filterTable()">
                    <option value="all">All Items</option>
                    <option value="arbitrage">Arbitrage Opportunities</option>
                    <option value="new">New Items Only</option>
                    <option value="with-retail">With Retail Prices</option>
                    <option value="no-retail">No Retail Price</option>
                    <option value="ebay">eBay Only</option>
                    <option value="facebook">Facebook Only</option>
                    <option value="amazon">Amazon Only</option>
                    <option value="cross-platform">Cross-Platform Matches</option>
                </select>
            </div>
            <div class="control-group">
                <label for="sort">Sort by:</label>
                <select id="sort" onchange="sortTable()">
                    <option value="spread-desc">Spread (High to Low)</option>
                    <option value="spread-asc">Spread (Low to High)</option>
                    <option value="price-desc">eBay Price (High to Low)</option>
                    <option value="price-asc">eBay Price (Low to High)</option>
                    <option value="retail-desc">Retail Price (High to Low)</option>
                    <option value="retail-asc">Retail Price (Low to High)</option>
                </select>
            </div>
            <div class="control-group">
                <label for="search">Search:</label>
                <input type="text" id="search" placeholder="Title, brand..." onkeyup="searchTable()">
            </div>
        </div>
        
        <div class="table-container">
            <table id="itemsTable">
                <thead>
                    <tr>
                        <th>Image</th>
                        <th>Title</th>
                        <th>Brand</th>
                        <th>Condition</th>
                        <th>eBay Price</th>
                        <th>Facebook Price</th>
                        <th>Amazon Price</th>
                        <th>Best Price</th>
                        <th>Retail Price</th>
                        <th>Spread</th>
                        <th>Spread %</th>
                        <th>Status</th>
                        <th>Links</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add table rows - grouped by title to show all platforms
    for title_key, grouped in items_by_title.items():
        ebay_item = grouped['ebay']
        fb_item = grouped['facebook']
        amazon_item = grouped['amazon']
        title = grouped['title']
        brand = grouped['brand']
        
        # Get prices from all platforms
        ebay_price = float(ebay_item.get('all_in_cost', 0) or 0) if ebay_item else None
        fb_price = float(fb_item.get('all_in_cost', 0) or 0) if fb_item else None
        amazon_price = float(amazon_item.get('all_in_cost', 0) or 0) if amazon_item else None
        
        # Determine best price
        prices = {}
        if ebay_price: prices['eBay'] = ebay_price
        if fb_price: prices['Facebook'] = fb_price
        if amazon_price: prices['Amazon'] = amazon_price
        
        best_platform = min(prices, key=prices.get) if prices else None
        best_price = min(prices.values()) if prices else None
        
        # Get retail price (prefer from any platform)
        retail_price = None
        for item in [ebay_item, fb_item, amazon_item]:
            if item and item.get('retail_price'):
                try:
                    retail_price = float(item.get('retail_price'))
                    break
                except:
                    pass
        
        # Calculate spread if retail price available
        spread = None
        spread_pct = None
        if retail_price and best_price:
            spread = retail_price - best_price
            spread_pct = (spread / retail_price * 100) if retail_price > 0 else 0
        
        is_arbitrage = spread is not None and spread > 0
        
        # Get condition (prefer from eBay, then others)
        condition = 'N/A'
        for item in [ebay_item, fb_item, amazon_item]:
            if item and item.get('condition'):
                condition = item.get('condition')
                break
        
        # Get image (prefer from eBay, then others)
        image_url = ''
        for item in [ebay_item, fb_item, amazon_item]:
            if item and item.get('image_url'):
                image_url = item.get('image_url')
                break
        
        # Determine row class
        row_class = ''
        if not retail_price:
            row_class = 'no-retail'
            status_badge = '<span class="badge no-retail">No Retail Price</span>'
        elif is_arbitrage:
            row_class = 'arbitrage'
            status_badge = '<span class="badge arbitrage">ARBITRAGE</span>'
        else:
            status_badge = '<span class="badge no-arbitrage">No Arbitrage</span>'
        
        # Format prices
        ebay_display = f'<span class="price">${ebay_price:,.2f}</span>' if ebay_price else '<span style="color: #999;">—</span>'
        fb_display = f'<span class="price">${fb_price:,.2f}</span>' if fb_price else '<span style="color: #999;">—</span>'
        amazon_display = f'<span class="price">${amazon_price:,.2f}</span>' if amazon_price else '<span style="color: #999;">—</span>'
        best_display = f'<span class="price" style="color: #10b981; font-weight: bold;">${best_price:,.2f}</span><br><small style="color: #666;">({best_platform})</small>' if best_price else '<span style="color: #999;">—</span>'
        
        # Format spread
        if spread is not None:
            spread_class = 'spread-positive' if spread > 0 else 'spread-negative'
            spread_display = f'<span class="{spread_class}">${spread:,.2f}</span>'
            spread_pct_display = f'<span class="{spread_class}">{spread_pct:.1f}%</span>'
        else:
            spread_display = 'N/A'
            spread_pct_display = 'N/A'
        
        # Truncate title
        title_display = title[:60] + '...' if len(title) > 60 else title
        
        # Image display
        if image_url:
            image_html = f'<img src="{image_url}" alt="{title_display}" style="width: 100px; height: 100px; object-fit: cover; border-radius: 8px; cursor: pointer;" onclick="window.open(this.src, \'_blank\')" title="Click to view full size">'
        else:
            image_html = '<div style="width: 100px; height: 100px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #999; font-size: 12px;">No Image</div>'
        
        # Build links
        links = []
        if ebay_item and ebay_item.get('url'):
            links.append(f'<a href="{ebay_item["url"]}" target="_blank" class="item-link" style="margin-right: 8px;">eBay →</a>')
        if fb_item and fb_item.get('url'):
            links.append(f'<a href="{fb_item["url"]}" target="_blank" class="item-link" style="margin-right: 8px;">FB →</a>')
        if amazon_item and amazon_item.get('url'):
            links.append(f'<a href="{amazon_item["url"]}" target="_blank" class="item-link">Amazon →</a>')
        links_html = ' '.join(links) if links else '<span style="color: #999;">—</span>'
        
        html += f"""
                    <tr class="{row_class}" data-title="{title.lower()}" data-brand="{brand.lower()}" data-has-retail="{'true' if retail_price else 'false'}" data-is-arbitrage="{'true' if is_arbitrage else 'false'}" data-spread="{spread or '0'}" data-price="{best_price or '0'}" data-retail="{retail_price or '0'}">
                        <td>{image_html}</td>
                        <td><strong>{title_display}</strong></td>
                        <td>{brand}</td>
                        <td>{condition}</td>
                        <td>{ebay_display}</td>
                        <td>{fb_display}</td>
                        <td>{amazon_display}</td>
                        <td>{best_display}</td>
                        <td class="price">{f'${retail_price:,.2f}' if retail_price else 'N/A'}</td>
                        <td>{spread_display}</td>
                        <td>{spread_pct_display}</td>
                        <td>{status_badge}</td>
                        <td>{links_html}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated by Luxury Items Arbitrage Scanner | Data from luxury_items.csv</p>
        </div>
    </div>
    
    <script>
        let allRows = Array.from(document.querySelectorAll('#itemsTable tbody tr'));
        let currentFilter = 'all';
        let currentSort = 'spread-desc';
        
        function filterTable() {
            const filter = document.getElementById('filter').value;
            currentFilter = filter;
            
            allRows.forEach(row => {
                let show = true;
                
                if (filter === 'arbitrage') {
                    show = row.dataset.isArbitrage === 'true';
                } else if (filter === 'new') {
                    show = row.dataset.isNew === 'true';
                } else if (filter === 'with-retail') {
                    show = row.dataset.hasRetail === 'true';
                } else if (filter === 'no-retail') {
                    show = row.dataset.hasRetail === 'false';
                } else if (filter === 'ebay') {
                    show = row.dataset.platform === 'ebay';
                } else if (filter === 'facebook') {
                    show = row.dataset.platform === 'facebook';
                } else if (filter === 'cross-platform') {
                    const crossPlatformCell = row.querySelector('td:nth-child(13)');
                    show = crossPlatformCell && !crossPlatformCell.textContent.includes('—');
                }
                
                row.style.display = show ? '' : 'none';
            });
            
            sortTable();
        }
        
        function sortTable() {
            const sort = document.getElementById('sort').value;
            currentSort = sort;
            
            const tbody = document.querySelector('#itemsTable tbody');
            const visibleRows = allRows.filter(row => row.style.display !== 'none');
            
            visibleRows.sort((a, b) => {
                if (sort === 'spread-desc') {
                    return parseFloat(b.dataset.spread || 0) - parseFloat(a.dataset.spread || 0);
                } else if (sort === 'spread-asc') {
                    return parseFloat(a.dataset.spread || 0) - parseFloat(b.dataset.spread || 0);
                } else if (sort === 'price-desc') {
                    return parseFloat(b.dataset.price || 0) - parseFloat(a.dataset.price || 0);
                } else if (sort === 'price-asc') {
                    return parseFloat(a.dataset.price || 0) - parseFloat(b.dataset.price || 0);
                } else if (sort === 'retail-desc') {
                    return parseFloat(b.dataset.retail || 0) - parseFloat(a.dataset.retail || 0);
                } else if (sort === 'retail-asc') {
                    return parseFloat(a.dataset.retail || 0) - parseFloat(b.dataset.retail || 0);
                }
                return 0;
            });
            
            visibleRows.forEach(row => tbody.appendChild(row));
        }
        
        function searchTable() {
            const search = document.getElementById('search').value.toLowerCase();
            
            allRows.forEach(row => {
                const title = row.dataset.title || '';
                const brand = row.dataset.brand || '';
                const matches = title.includes(search) || brand.includes(search);
                
                // Also check if it matches current filter
                let filterMatch = true;
                if (currentFilter === 'arbitrage') {
                    filterMatch = row.dataset.isArbitrage === 'true';
                } else if (currentFilter === 'new') {
                    filterMatch = row.dataset.isNew === 'true';
                } else if (currentFilter === 'with-retail') {
                    filterMatch = row.dataset.hasRetail === 'true';
                } else if (currentFilter === 'no-retail') {
                    filterMatch = row.dataset.hasRetail === 'false';
                }
                
                row.style.display = (matches && filterMatch) ? '' : 'none';
            });
            
            sortTable();
        }
        
        // Initialize
        sortTable();
    </script>
</body>
</html>
"""
    
    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"[SUCCESS] HTML report generated: {output_file}")
    print(f"   Total items: {total_items}")
    print(f"   Items with retail prices: {len(items_with_retail)}")
    print(f"   Arbitrage opportunities: {len(arbitrage_items)}")
    print(f"   New items: {len(new_items)}")
    if spreads:
        print(f"   Best spread: ${best_spread:,.2f}")

if __name__ == '__main__':
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'data/luxury_items.csv'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'data/luxury_items_report.html'
    
    generate_luxury_html_report(csv_file=csv_file, output_file=output_file)

