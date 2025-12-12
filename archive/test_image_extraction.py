#!/usr/bin/env python3
"""
Test script for image-based cert extraction
Can test with either a local image file or an image URL from eBay
"""

import os
import sys
import requests
from dotenv import load_dotenv
from research_agent import extract_cert_from_image

# Load environment
load_dotenv(".env")
load_dotenv(".env.local", override=True)

openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    print("Error: OPENROUTER_API_KEY not found in .env.local or .env")
    sys.exit(1)

def download_image_from_url(url: str, output_path: str) -> bool:
    """Download an image from a URL"""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False

if len(sys.argv) < 2:
    print("=" * 70)
    print("PSA Certification Number Extractor - Test")
    print("=" * 70)
    print("\nUsage:")
    print("  python test_image_extraction.py <image_path_or_url>")
    print("\nExamples:")
    print("  python test_image_extraction.py card_image.png")
    print("  python test_image_extraction.py https://i.ebayimg.com/images/g/.../s-l1600.jpg")
    print("\nIf you provide a URL, the image will be downloaded first.")
    sys.exit(1)

input_path = sys.argv[1]
model = sys.argv[2] if len(sys.argv) > 2 else "anthropic/claude-opus-4.5"

# Check if it's a URL
if input_path.startswith('http://') or input_path.startswith('https://'):
    print(f"Downloading image from URL: {input_path}")
    temp_image = "temp_test_image.jpg"
    if download_image_from_url(input_path, temp_image):
        print(f"Image downloaded to {temp_image}")
        image_path = temp_image
    else:
        print("Failed to download image")
        sys.exit(1)
else:
    image_path = input_path
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)

print("\n" + "=" * 70)
print("PSA Certification Number Extractor")
print("=" * 70)
print(f"Image: {image_path}")
print(f"Model: {model}")
print()

cert_number = extract_cert_from_image(
    image_path=image_path,
    openrouter_api_key=openrouter_key,
    model=model
)

if cert_number:
    print("\n" + "=" * 70)
    print(f"SUCCESS: Found certification number: {cert_number}")
    print("=" * 70)
    print(f"\nYou can now use this cert number to:")
    print(f"  - Check PSA estimate: python test_psa_api.py {cert_number}")
    print(f"  - Search for arbitrage opportunities")
else:
    print("\n" + "=" * 70)
    print("FAILED: Could not extract certification number")
    print("=" * 70)
    print("\nPossible reasons:")
    print("  - Image quality is too low")
    print("  - Certification number is not visible")
    print("  - Try a different model (e.g., openai/gpt-4o)")
    print("  - Ensure the image shows the PSA label clearly")

# Clean up temp file if we downloaded it
if input_path.startswith('http://') or input_path.startswith('https://'):
    try:
        os.remove(temp_image)
        print(f"\nCleaned up temporary file: {temp_image}")
    except:
        pass

