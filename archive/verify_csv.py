#!/usr/bin/env python3
"""Verify CSV data accuracy"""

import csv

# Read CSV
with open('all_cards.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total cards in CSV: {len(rows)}\n")
print("=" * 70)
print("VERIFICATION RESULTS")
print("=" * 70)

# Check a few key entries
test_certs = [
    ("85347418", "JINZO"),
    ("44977357", "WHIPTAIL CROW"),
    ("67118020", "GATE GUARDIAN"),
]

for cert_num, card_name in test_certs:
    row = next((r for r in rows if r['cert_number'] == cert_num), None)
    if not row:
        print(f"\n❌ Cert {cert_num} ({card_name}) NOT FOUND")
        continue
    
    print(f"\n✅ Cert {cert_num} - {card_name}:")
    print(f"   Title: {row['title'][:60]}...")
    print(f"   Card Name: {row['card_name']}")
    print(f"   Set: {row['set']}")
    print(f"   eBay Price: ${float(row['ebay_price']):.2f}")
    print(f"   Shipping: ${float(row['shipping']):.2f}")
    print(f"   Tax (9%): ${float(row['est_tax']):.2f}")
    
    # Verify calculation
    calculated_all_in = float(row['ebay_price']) + float(row['shipping']) + float(row['est_tax'])
    csv_all_in = float(row['all_in_cost']) if row['all_in_cost'] else 0
    
    if abs(calculated_all_in - csv_all_in) < 0.01:
        print(f"   ✅ All-in Cost: ${csv_all_in:.2f} (calculation correct)")
    else:
        print(f"   ❌ All-in Cost mismatch: CSV=${csv_all_in:.2f}, Calculated=${calculated_all_in:.2f}")
    
    if row['psa_estimate']:
        psa_est = float(row['psa_estimate'])
        spread = float(row['spread'])
        print(f"   PSA Estimate: ${psa_est:.2f}")
        print(f"   Spread: ${spread:.2f}")
        
        # Verify spread calculation
        expected_spread = psa_est - csv_all_in
        if abs(spread - expected_spread) < 0.01:
            print(f"   ✅ Spread calculation correct")
        else:
            print(f"   ❌ Spread mismatch: CSV=${spread:.2f}, Calculated=${expected_spread:.2f}")
    else:
        print(f"   ⚠️  No PSA estimate available")

# Summary statistics
print("\n" + "=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)

cards_with_psa = [r for r in rows if r['psa_estimate']]
cards_without_psa = [r for r in rows if not r['psa_estimate']]

print(f"Total cards: {len(rows)}")
print(f"Cards with PSA estimates: {len(cards_with_psa)}")
print(f"Cards without PSA estimates: {len(cards_without_psa)}")

if cards_with_psa:
    spreads = [float(r['spread']) for r in cards_with_psa]
    print(f"\nSpread Statistics (for cards with PSA estimates):")
    print(f"  Best spread: ${max(spreads):.2f}")
    print(f"  Worst spread: ${min(spreads):.2f}")
    print(f"  Average spread: ${sum(spreads)/len(spreads):.2f}")
    
    positive_spreads = [s for s in spreads if s > 0]
    if positive_spreads:
        print(f"  ✅ {len(positive_spreads)} cards with positive spread (arbitrage opportunities)")
    else:
        print(f"  ❌ No arbitrage opportunities found")

# Check for calculation errors
print("\n" + "=" * 70)
print("CALCULATION VERIFICATION")
print("=" * 70)

errors = []
for i, row in enumerate(rows, start=2):  # Start at 2 because row 1 is header
    try:
        price = float(row['ebay_price'])
        shipping = float(row['shipping'])
        tax = float(row['est_tax'])
        all_in = float(row['all_in_cost']) if row['all_in_cost'] else 0
        
        calculated = price + shipping + tax
        if abs(calculated - all_in) > 0.01:
            errors.append(f"Row {i} (Cert {row['cert_number']}): All-in cost mismatch")
        
        if row['psa_estimate']:
            psa_est = float(row['psa_estimate'])
            spread = float(row['spread'])
            expected_spread = psa_est - all_in
            if abs(spread - expected_spread) > 0.01:
                errors.append(f"Row {i} (Cert {row['cert_number']}): Spread mismatch")
    except (ValueError, KeyError) as e:
        errors.append(f"Row {i} (Cert {row.get('cert_number', 'unknown')}): Error - {e}")

if errors:
    print(f"❌ Found {len(errors)} calculation errors:")
    for error in errors[:10]:  # Show first 10
        print(f"  {error}")
    if len(errors) > 10:
        print(f"  ... and {len(errors) - 10} more")
else:
    print("✅ All calculations are correct!")

