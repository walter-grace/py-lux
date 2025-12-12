#!/usr/bin/env python3
"""Test OpenRouter API to see actual response format"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv(".env")
load_dotenv(".env.local", override=True)

openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    print("Error: OPENROUTER_API_KEY not found")
    exit(1)

# Simple test prompt
test_prompt = """Search eBay for "yugioh psa 10 1st edition buy it now" and find 3 listings with PSA certification numbers.

Return a JSON object with this exact format:
{
  "listings": [
    {
      "title": "listing title",
      "cert_number": "12345678",
      "price": 500.00,
      "shipping": 5.99,
      "url": "https://www.ebay.com/itm/...",
      "card_name": "Card Name",
      "year": "2002",
      "set": "Set Name"
    }
  ]
}

Return ONLY the JSON, nothing else."""

print("Testing OpenRouter API...")
print(f"Model: openai/o4-mini-deep-research")
print(f"Prompt length: {len(test_prompt)} chars")
print()

headers = {
    "Authorization": f"Bearer {openrouter_key}",
    "Content-Type": "application/json",
}

data = {
    "model": "openai/o4-mini-deep-research",
    "messages": [
        {
            "role": "user",
            "content": test_prompt
        }
    ],
    "max_tokens": 8000,  # Increased for deep research
}

try:
    print("Sending request...")
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=120
    )
    
    print(f"Status Code: {response.status_code}")
    print()
    
    if response.status_code == 200:
        result = response.json()
        print("Full Response Structure:")
        print(json.dumps(result, indent=2)[:1000])  # First 1000 chars
        print()
        print("=" * 70)
        print("Content from response:")
        print("=" * 70)
        
        message = result.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "")
        reasoning = message.get("reasoning")
        finish_reason = result.get("choices", [{}])[0].get("finish_reason", "")
        
        print(f"Finish reason: {finish_reason}")
        print(f"Content length: {len(content)} chars")
        if reasoning:
            print(f"Reasoning length: {len(reasoning)} chars")
        print()
        
        if content:
            print("Content:")
            print(content[:2000])
            if len(content) > 2000:
                print(f"... (truncated, total {len(content)} chars)")
        else:
            print("No content in response!")
            if reasoning:
                print("\nReasoning (first 1000 chars):")
                print(reasoning[:1000])
        
    else:
        print(f"Error Response:")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

