#!/usr/bin/env python3
"""Test chatbot tool calling"""
import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from chatbot_mcp import MCPChatbot

load_dotenv(".env")
load_dotenv(".env.local", override=True)


async def test_ebay_search():
    """Test eBay search tool calling"""
    print("=" * 70)
    print("Testing eBay Search Tool Calling")
    print("=" * 70)
    
    chatbot = MCPChatbot()
    
    # Test query that should trigger search_ebay
    test_query = "Search eBay for Rolex Submariner watches under 10000"
    
    print(f"\nQuery: {test_query}")
    print("\nProcessing...")
    
    try:
        response = await chatbot.process_query(test_query)
        print(f"\nResponse:\n{response}")
        
        # Check if response contains actual eBay data
        if "item" in response.lower() or "price" in response.lower() or "ebay.com" in response.lower():
            print("\n✅ SUCCESS: Response appears to contain eBay search results")
        else:
            print("\n⚠️  WARNING: Response may not contain eBay search results")
            print("   The tool may not have been called")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await chatbot.cleanup()


if __name__ == "__main__":
    asyncio.run(test_ebay_search())

