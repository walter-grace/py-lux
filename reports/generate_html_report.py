#!/usr/bin/env python3
"""
Generate a beautiful HTML report from the all_cards.csv file
"""

import csv
import sys
import os
from datetime import datetime

# Add parent directory to path for data files
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def generate_html_report(csv_file='data/all_cards.csv', output_file='data/cards_report.html', title_suffix=''):
    """Generate an HTML report from CSV data"""
    
    # Read CSV data
    cards = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cards.append(row)
    
    # Calculate statistics
    total_cards = len(cards)
    cards_with_psa = [c for c in cards if c.get('psa_estimate')]
    cards_without_psa = [c for c in cards if not c.get('psa_estimate')]
    arbitrage_cards = [c for c in cards_with_psa if c.get('is_arbitrage') == 'True']
    
    # Platform statistics
    ebay_cards = [c for c in cards if c.get('platform', 'eBay') == 'eBay']
    facebook_cards = [c for c in cards if c.get('platform') == 'Facebook']
    cross_platform_matches = [c for c in cards if c.get('cross_platform_match')]
    
    # Calculate spread statistics
    spreads = []
    for card in cards_with_psa:
        try:
            spread = float(card.get('spread', 0))
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
    <title>PSA 10 Trading Card Arbitrage Scanner{title_suffix} - Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            color: #667eea;
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
            border-color: #667eea;
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
            background: #667eea;
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
        
        tbody tr.no-psa {{
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
        
        .badge.no-psa {{
            background: #f59e0b;
            color: white;
        }}
        
        .price {{
            font-weight: 600;
            color: #667eea;
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
        
        .card-link {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        
        .card-link:hover {{
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
            <h1>PSA 10 Trading Card Arbitrage Scanner{title_suffix}</h1>
            <p>Report Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{total_cards}</div>
                <div class="stat-label">Total Cards</div>
            </div>
            <div class="stat-card positive">
                <div class="stat-value">{len(cards_with_psa)}</div>
                <div class="stat-label">With PSA Estimates</div>
            </div>
            <div class="stat-card negative">
                <div class="stat-value">{len(cards_without_psa)}</div>
                <div class="stat-label">No PSA Estimate</div>
            </div>
            <div class="stat-card {'positive' if len(arbitrage_cards) > 0 else 'negative'}">
                <div class="stat-value">{len(arbitrage_cards)}</div>
                <div class="stat-label">Arbitrage Opportunities</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(ebay_cards)}</div>
                <div class="stat-label">eBay Listings</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(facebook_cards)}</div>
                <div class="stat-label">Facebook Listings</div>
            </div>
            <div class="stat-card positive">
                <div class="stat-value">{len(cross_platform_matches)}</div>
                <div class="stat-label">Cross-Platform Matches</div>
            </div>
            {f'''
            <div class="stat-card">
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
                    <option value="all">All Cards</option>
                    <option value="arbitrage">Arbitrage Opportunities</option>
                    <option value="with-psa">With PSA Estimates</option>
                    <option value="no-psa">No PSA Estimate</option>
                    <option value="ebay">eBay Only</option>
                    <option value="facebook">Facebook Only</option>
                    <option value="cross-platform">Cross-Platform Matches</option>
                </select>
            </div>
            <div class="control-group">
                <label for="sort">Sort by:</label>
                <select id="sort" onchange="sortTable()">
                    <option value="spread-desc">Spread (High to Low)</option>
                    <option value="spread-asc">Spread (Low to High)</option>
                    <option value="price-desc">Price (High to Low)</option>
                    <option value="price-asc">Price (Low to High)</option>
                    <option value="psa-desc">PSA Estimate (High to Low)</option>
                    <option value="psa-asc">PSA Estimate (Low to High)</option>
                </select>
            </div>
            <div class="control-group">
                <label for="search">Search:</label>
                <input type="text" id="search" placeholder="Card name, cert number..." onkeyup="searchTable()">
            </div>
        </div>
        
        <div class="table-container">
            <table id="cardsTable">
                <thead>
                    <tr>
                        <th>Image</th>
                        <th>Cert #</th>
                        <th>Card Name</th>
                        <th>Set</th>
                        <th>eBay Price</th>
                        <th>Shipping</th>
                        <th>Tax</th>
                        <th>All-In Cost</th>
                        <th>PSA Estimate</th>
                        <th>Spread</th>
                        <th>Spread %</th>
                        <th>Platform</th>
                        <th>Cross-Platform</th>
                        <th>Status</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add table rows
    for card in cards:
        cert = card.get('cert_number', '')
        card_name = card.get('card_name', 'N/A')
        set_name = card.get('set', 'N/A')
        price = float(card.get('ebay_price', 0))
        shipping = float(card.get('shipping', 0))
        tax = float(card.get('est_tax', 0))
        all_in = float(card.get('all_in_cost', 0))
        psa_est = card.get('psa_estimate', '')
        spread = card.get('spread', '')
        spread_pct = card.get('spread_pct', '')
        is_arbitrage = card.get('is_arbitrage', 'False') == 'True'
        url = card.get('url', '#')
        image_url = card.get('image_url', '').strip()
        platform = card.get('platform', 'eBay')
        cross_platform_match = card.get('cross_platform_match', '')
        price_difference = card.get('price_difference', '')
        best_platform = card.get('best_platform', '')
        
        # Determine row class
        row_class = ''
        if not psa_est:
            row_class = 'no-psa'
            status_badge = '<span class="badge no-psa">No PSA Est</span>'
        elif is_arbitrage:
            row_class = 'arbitrage'
            status_badge = '<span class="badge arbitrage">ARBITRAGE</span>'
        else:
            status_badge = '<span class="badge no-arbitrage">No Arbitrage</span>'
        
        # Format spread
        if spread:
            spread_val = float(spread)
            spread_class = 'spread-positive' if spread_val > 0 else 'spread-negative'
            spread_display = f'<span class="{spread_class}">${spread_val:,.2f}</span>'
        else:
            spread_display = 'N/A'
        
        if spread_pct:
            try:
                spread_pct_val = float(spread_pct)
                spread_pct_class = 'spread-positive' if spread_pct_val > 0 else 'spread-negative'
                spread_pct_display = f'<span class="{spread_pct_class}">{spread_pct_val:.1f}%</span>'
            except:
                spread_pct_display = 'N/A'
        else:
            spread_pct_display = 'N/A'
        
        # Image display
        if image_url:
            image_html = f'<img src="{image_url}" alt="{card_name}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 8px; cursor: pointer;" onclick="window.open(this.src, \'_blank\')" title="Click to view full size">'
        else:
            image_html = '<div style="width: 80px; height: 80px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #999; font-size: 10px; text-align: center;">No Image</div>'
        
        # Platform badge
        platform_badge = f'<span class="badge" style="background: {"#3b82f6" if platform == "eBay" else "#1877f2"}; color: white;">{platform}</span>'
        
        # Cross-platform match display
        if cross_platform_match:
            price_diff_display = f'${float(price_difference):,.2f}' if price_difference else 'N/A'
            cross_platform_html = f'<a href="{cross_platform_match}" target="_blank" class="card-link" title="View on {"eBay" if platform == "Facebook" else "Facebook"}">Match →</a><br><small style="color: #666;">Diff: {price_diff_display}</small><br><small style="color: #10b981;">Best: {best_platform}</small>'
        else:
            cross_platform_html = '<span style="color: #999;">—</span>'
        
        html += f"""
                    <tr class="{row_class}" data-cert="{cert}" data-card-name="{card_name.lower()}" data-has-psa="{'true' if psa_est else 'false'}" data-is-arbitrage="{'true' if is_arbitrage else 'false'}" data-spread="{spread or '0'}" data-price="{price}" data-psa-est="{psa_est or '0'}" data-platform="{platform.lower()}">
                        <td>{image_html}</td>
                        <td><strong>{cert}</strong></td>
                        <td>{card_name}</td>
                        <td>{set_name[:40] if len(set_name) > 40 else set_name}</td>
                        <td class="price">${price:,.2f}</td>
                        <td>${shipping:.2f}</td>
                        <td>${tax:.2f}</td>
                        <td class="price">${all_in:,.2f}</td>
                        <td class="price">{f'${float(psa_est):,.2f}' if psa_est else 'N/A'}</td>
                        <td>{spread_display}</td>
                        <td>{spread_pct_display}</td>
                        <td>{platform_badge}</td>
                        <td>{cross_platform_html}</td>
                        <td>{status_badge}</td>
                        <td><a href="{url}" target="_blank" class="card-link">View →</a></td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated by PSA 10 Yu-Gi-Oh! Arbitrage Scanner | Data from all_cards.csv</p>
        </div>
    </div>
    
    <script>
        let allRows = Array.from(document.querySelectorAll('#cardsTable tbody tr'));
        let currentFilter = 'all';
        let currentSort = 'spread-desc';
        
        function filterTable() {
            const filter = document.getElementById('filter').value;
            currentFilter = filter;
            
            allRows.forEach(row => {
                let show = true;
                
                if (filter === 'arbitrage') {
                    show = row.dataset.isArbitrage === 'true';
                } else if (filter === 'with-psa') {
                    show = row.dataset.hasPsa === 'true';
                } else if (filter === 'no-psa') {
                    show = row.dataset.hasPsa === 'false';
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
            
            const tbody = document.querySelector('#cardsTable tbody');
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
                } else if (sort === 'psa-desc') {
                    return parseFloat(b.dataset.psaEst || 0) - parseFloat(a.dataset.psaEst || 0);
                } else if (sort === 'psa-asc') {
                    return parseFloat(a.dataset.psaEst || 0) - parseFloat(b.dataset.psaEst || 0);
                }
                return 0;
            });
            
            visibleRows.forEach(row => tbody.appendChild(row));
        }
        
        function searchTable() {
            const search = document.getElementById('search').value.toLowerCase();
            
            allRows.forEach(row => {
                const cert = row.dataset.cert || '';
                const cardName = row.dataset.cardName || '';
                const matches = cert.includes(search) || cardName.includes(search);
                
                // Also check if it matches current filter
                let filterMatch = true;
                if (currentFilter === 'arbitrage') {
                    filterMatch = row.dataset.isArbitrage === 'true';
                } else if (currentFilter === 'with-psa') {
                    filterMatch = row.dataset.hasPsa === 'true';
                } else if (currentFilter === 'no-psa') {
                    filterMatch = row.dataset.hasPsa === 'false';
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
    print(f"   Total cards: {total_cards}")
    print(f"   Cards with PSA estimates: {len(cards_with_psa)}")
    print(f"   Arbitrage opportunities: {len(arbitrage_cards)}")

if __name__ == '__main__':
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'data/all_cards.csv'
    
    # Auto-detect output filename and title based on input CSV
    if 'pokemon' in csv_file.lower():
        output_file = 'data/pokemon_cards_report.html'
        title_suffix = ' - Pokemon Base Set 1999'
    elif 'yugioh' in csv_file.lower() or 'all_cards' in csv_file.lower():
        output_file = 'data/cards_report.html'
        title_suffix = ' - Yu-Gi-Oh! 2002'
    else:
        output_file = csv_file.replace('.csv', '_report.html')
        if not output_file.startswith('data/'):
            output_file = 'data/' + output_file
        title_suffix = ''
    
    generate_html_report(csv_file=csv_file, output_file=output_file, title_suffix=title_suffix)

