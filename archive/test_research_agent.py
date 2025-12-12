#!/usr/bin/env python3
"""Test the research agent scraping function"""

from research_agent import scrape_psa_estimate

# Test with the cert number we know works
cert = "67118020"
print(f"Testing PSA estimate scraping for cert {cert}...")
estimate = scrape_psa_estimate(cert)

if estimate:
    print(f"Found PSA Estimate: ${estimate:,.2f}")
else:
    print("Could not find PSA Estimate")

