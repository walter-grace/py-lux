#!/usr/bin/env python3
"""Test script to verify chatbot setup"""
import os
import sys
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local", override=True)

print("=" * 70)
print("Chatbot Setup Verification")
print("=" * 70)
print()

# Check dependencies
print("Checking dependencies...")
try:
    import mcp
    print("✅ MCP SDK installed")
except ImportError:
    print("❌ MCP SDK not installed - run: pip install mcp")
    sys.exit(1)

try:
    from openai import OpenAI
    print("✅ OpenAI SDK installed")
except ImportError:
    print("❌ OpenAI SDK not installed - run: pip install openai")
    sys.exit(1)

# Check environment variables
print("\nChecking environment variables...")
openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
if openrouter_key:
    print(f"✅ OPENROUTER_API_KEY found: {openrouter_key[:20]}...")
else:
    print("❌ OPENROUTER_API_KEY not found")

watch_db_key = os.getenv("WATCH_DATABASE_API_KEY") or os.getenv("RAPIDAPI_KEY", "")
if watch_db_key:
    print(f"✅ Watch Database API key found: {watch_db_key[:20]}...")
else:
    print("⚠️  Watch Database API key not found (MCP server won't work)")

ebay_oauth = os.getenv("EBAY_OAUTH", "")
ebay_client_id = os.getenv("EBAY_CLIENT_ID", "")
ebay_client_secret = os.getenv("EBAY_CLIENT_SECRET", "")

if ebay_oauth or (ebay_client_id and ebay_client_secret):
    print("✅ eBay credentials found")
else:
    print("⚠️  eBay credentials not found (eBay search won't work)")

# Check Node.js (needed for MCP)
print("\nChecking Node.js (required for MCP)...")
import subprocess
try:
    result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print(f"✅ Node.js installed: {result.stdout.strip()}")
    else:
        print("⚠️  Node.js not found - MCP server may not work")
except (FileNotFoundError, subprocess.TimeoutExpired):
    print("⚠️  Node.js not found - install Node.js for MCP server support")

print("\n" + "=" * 70)
print("Setup Summary")
print("=" * 70)

if openrouter_key and (watch_db_key or ebay_oauth or (ebay_client_id and ebay_client_secret)):
    print("✅ Ready to run chatbot!")
    print("\nRun: python chatbot_mcp.py")
else:
    print("⚠️  Some configuration missing - chatbot may have limited functionality")
    print("\nRequired:")
    print("  - OPENROUTER_API_KEY (required)")
    print("  - WATCH_DATABASE_API_KEY or RAPIDAPI_KEY (for Watch Database)")
    print("  - EBAY_OAUTH or EBAY_CLIENT_ID + EBAY_CLIENT_SECRET (for eBay)")

print("=" * 70)

