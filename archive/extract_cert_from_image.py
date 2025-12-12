#!/usr/bin/env python3
"""
Test script to extract PSA certification number from card images using OpenRouter vision models
"""

import os
import sys
from dotenv import load_dotenv
from research_agent import extract_cert_from_image

# Load environment
load_dotenv(".env")
load_dotenv(".env.local", override=True)

openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    print("Error: OPENROUTER_API_KEY not found in .env.local or .env")
    print("Please add your OpenRouter API key to .env.local")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python extract_cert_from_image.py <image_path> [model]")
    print("\nExample:")
    print("  python extract_cert_from_image.py card_image.png")
    print("  python extract_cert_from_image.py card_image.png openai/gpt-4o")
    print("\nAvailable vision models:")
    print("  - anthropic/claude-opus-4.5 (default, Claude Opus 4.5 - most accurate)")
    print("  - openai/gpt-4o (alternative)")
    print("  - openai/gpt-4o-mini (cheaper)")
    sys.exit(1)

image_path = sys.argv[1]
model = sys.argv[2] if len(sys.argv) > 2 else "anthropic/claude-opus-4.5"

if not os.path.exists(image_path):
    print(f"Error: Image file not found: {image_path}")
    sys.exit(1)

print("=" * 70)
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
    print("=" * 70)
    print(f"SUCCESS: Found certification number: {cert_number}")
    print("=" * 70)
else:
    print("=" * 70)
    print("FAILED: Could not extract certification number")
    print("=" * 70)
    print("\nPossible reasons:")
    print("  - Image quality is too low")
    print("  - Certification number is not visible")
    print("  - Try a different model (e.g., openai/gpt-4o)")
    print("  - Ensure the image shows the PSA label clearly")

