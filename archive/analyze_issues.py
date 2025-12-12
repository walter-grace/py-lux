#!/usr/bin/env python3
"""Analyze where issues are - eBay cert extraction vs PSA estimates"""

import csv

# Read CSV
with open('all_cards.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print("=" * 70)
print("ISSUE ANALYSIS: eBay vs PSA")
print("=" * 70)

total = len(rows)
cards_with_cert = [r for r in rows if r.get('cert_number')]
cards_without_cert = [r for r in rows if not r.get('cert_number')]
cards_with_psa = [r for r in rows if r.get('psa_estimate')]
cards_without_psa = [r for r in rows if not r.get('psa_estimate')]

print(f"\nTotal cards found: {total}")
print(f"\n1. CERT NUMBER EXTRACTION (eBay API issue?):")
print(f"   [OK] Cards WITH cert number: {len(cards_with_cert)} ({len(cards_with_cert)/total*100:.1f}%)")
print(f"   [MISSING] Cards WITHOUT cert number: {len(cards_without_cert)} ({len(cards_without_cert)/total*100:.1f}%)")

if cards_without_cert:
    print(f"\n   Cards missing cert numbers:")
    for card in cards_without_cert[:5]:
        print(f"     - {card.get('title', 'N/A')[:60]}")

print(f"\n2. PSA ESTIMATE AVAILABILITY (PSA website issue?):")
print(f"   [OK] Cards WITH PSA estimate: {len(cards_with_psa)} ({len(cards_with_psa)/total*100:.1f}%)")
print(f"   [MISSING] Cards WITHOUT PSA estimate: {len(cards_without_psa)} ({len(cards_without_psa)/total*100:.1f}%)")

# Cards that have cert but no PSA estimate
cards_with_cert_no_psa = [r for r in cards_with_cert if not r.get('psa_estimate')]
print(f"\n3. CARDS WITH CERT BUT NO PSA ESTIMATE:")
print(f"   Count: {len(cards_with_cert_no_psa)}")
if cards_with_cert_no_psa:
    print(f"\n   These cards have cert numbers but PSA doesn't have estimates:")
    for card in cards_with_cert_no_psa[:10]:
        print(f"     - Cert {card.get('cert_number')}: {card.get('title', 'N/A')[:50]}")

# Cards that have both
cards_with_both = [r for r in rows if r.get('cert_number') and r.get('psa_estimate')]
print(f"\n4. CARDS WITH BOTH CERT AND PSA ESTIMATE:")
print(f"   Count: {len(cards_with_both)} ({len(cards_with_both)/total*100:.1f}%)")

print("\n" + "=" * 70)
print("CONCLUSION:")
print("=" * 70)

if len(cards_without_cert) > len(cards_without_cert) * 0.2:
    print("[WARNING] eBay API Issue: Many cards missing cert numbers in metadata")
    print("   -> Solution: Use image extraction as fallback (already implemented)")
else:
    print("[OK] eBay API: Most cards have cert numbers")

if len(cards_without_psa) > len(cards_with_psa):
    print("[WARNING] PSA Website Issue: Many cards don't have PSA estimates available")
    print("   → Possible reasons:")
    print("     - Cards are too new (not enough sales data)")
    print("     - PSA hasn't calculated estimates yet")
    print("     - Cards are rare/uncommon")
else:
    print("[OK] PSA Website: Most cards with certs have estimates")

