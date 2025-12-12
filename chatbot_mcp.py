#!/usr/bin/env python3
"""
Chatbot using OpenRouter with MCP servers for eBay and Watch Database
"""
import asyncio
import os
import sys
import json
import re
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack
from dotenv import load_dotenv

# MCP imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ MCP SDK not installed. Install with: pip install mcp")
    sys.exit(1)

# OpenRouter/OpenAI client
try:
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI SDK not installed. Install with: pip install openai")
    sys.exit(1)

# Load environment
load_dotenv(".env")
load_dotenv(".env.local", override=True)

# Configuration
MODEL = "anthropic/claude-3-5-sonnet"  # Using Claude via OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# MCP Server Configurations
WATCH_DB_SERVER_CONFIG = {
    "command": "npx",
    "args": [
        "-y",
        "mcp-remote",
        "https://mcp.rapidapi.com",
        "--header",
        "x-api-host: watch-database1.p.rapidapi.com",
        "--header",
        f"x-api-key: {os.getenv('WATCH_DATABASE_API_KEY') or os.getenv('RAPIDAPI_KEY', '')}"
    ],
    "env": None
}

# Import our existing functions for eBay
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from lib.config import load_env
from lib.ebay_api import search_ebay_generic
from lib.watch_database_api import (
    search_watches_by_name,
    search_reference,
    get_all_makes,
    normalize_brand_name
)
from lib.watch_api import extract_watch_metadata, enrich_watch_metadata_with_watch_db


def convert_tool_format(tool):
    """Convert MCP tool definition to OpenAI tool definition"""
    converted_tool = {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": tool.inputSchema.get("properties", {}),
                "required": tool.inputSchema.get("required", [])
            }
        }
    }
    return converted_tool


class eBayTools:
    """eBay API tools that can be called by the chatbot"""
    
    def __init__(self, env: Dict[str, str]):
        self.env = env
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of eBay tools in OpenRouter function calling format"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_ebay",
                    "description": "ALWAYS use this tool when the user asks to search eBay, find items on eBay, or look for watches/cards on eBay. This tool searches eBay using the eBay Browse API and returns real listings with prices, URLs, and details. REQUIRED for any eBay search request.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query string (e.g., 'Rolex Submariner', 'PSA 10 Charizard', 'Omega Speedmaster')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 20, max: 200)",
                                "default": 20,
                                "minimum": 1,
                                "maximum": 200
                            },
                            "category": {
                                "type": "string",
                                "description": "Optional eBay category ID filter. Common categories: '260324' for watches, '183454' for trading cards. Leave empty for all categories.",
                                "default": None
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_watch_listing",
                    "description": "Analyze an eBay watch listing to extract metadata (brand, model, reference number) and check for arbitrage opportunities. Uses Watch Database API to enrich metadata. Provide the eBay listing title and optionally the price.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "eBay listing title (required). Example: 'Rolex Submariner Date 116610LN Black Dial Men's Watch'"
                            },
                            "price": {
                                "type": "number",
                                "description": "Listing price in USD (optional). Used for arbitrage calculations."
                            },
                            "aspects": {
                                "type": "object",
                                "description": "eBay item aspects/attributes as a dictionary (optional). Keys like 'Brand', 'Model', 'Condition', etc."
                            }
                        },
                        "required": ["title"]
                    }
                }
            }
        ]
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute eBay tool calls (synchronous)"""
        if name == "search_ebay":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 20)
            category = arguments.get("category")
            
            try:
                items = search_ebay_generic(
                    query=query,
                    limit=min(limit, 200),
                    env=self.env,
                    category_ids=category,
                    filters="buyingOptions:{FIXED_PRICE}"
                )
                
                results = []
                for item in items[:limit]:
                    total_cost = item.get("price", 0) + item.get("shipping", 0)
                    results.append({
                        "item_id": item.get("item_id", ""),
                        "title": item.get("title", ""),
                        "price_usd": round(item.get("price", 0), 2),
                        "shipping_usd": round(item.get("shipping", 0), 2),
                        "total_cost_usd": round(total_cost, 2),
                        "url": item.get("url", ""),
                        "image_url": item.get("image_url", ""),
                        "condition": item.get("item_condition", "Unknown"),
                        "brand": item.get("aspects", {}).get("Brand", ""),
                        "model": item.get("aspects", {}).get("Model", ""),
                        "currency": item.get("currency", "USD")
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "count": len(results),
                    "total_found": len(items),
                    "items": results,
                    "summary": f"Found {len(results)} items on eBay for '{query}'"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Error searching eBay: {e}"
                }
        
        elif name == "analyze_watch_listing":
            title = arguments.get("title", "")
            price = arguments.get("price")
            aspects = arguments.get("aspects", {})
            
            try:
                # Extract metadata
                watch_info = extract_watch_metadata(
                    title=title,
                    aspects=aspects,
                    openrouter_api_key=None
                )
                
                # Enrich with Watch Database
                watch_info = enrich_watch_metadata_with_watch_db(
                    watch_info=watch_info,
                    env=self.env
                )
                
                result = {
                    "success": True,
                    "title": title,
                    "metadata": {
                        "brand": watch_info.get("brand"),
                        "model": watch_info.get("model"),
                        "model_number": watch_info.get("model_number"),
                        "condition": watch_info.get("condition"),
                        "year": watch_info.get("year"),
                        "movement_type": watch_info.get("movement_type"),
                        "case_material": watch_info.get("case_material"),
                        "dial_color": watch_info.get("dial_color")
                    },
                    "enrichment": "Metadata extracted and enriched with Watch Database API",
                    "message": "Watch listing analyzed successfully"
                }
                
                if price:
                    result["listing_price_usd"] = float(price)
                    result["metadata"]["price"] = float(price)
                
                return result
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Error analyzing watch: {e}"
                }
        
        return {"success": False, "error": f"Unknown tool: {name}"}


class MCPChatbot:
    """Chatbot that uses OpenRouter with MCP servers"""
    
    def __init__(self):
        self.watch_db_session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai = None
        self.messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": """You are a helpful assistant for watch and trading card arbitrage. 
When users ask to search eBay, find items on eBay, or look for watches/cards, you MUST use the search_ebay tool.
When users ask to analyze a watch listing, you MUST use the analyze_watch_listing tool.
Always use the available tools instead of making up information. Be direct and use tools when appropriate."""
            }
        ]
        self.env = load_env()
        self.ebay_tools = eBayTools(self.env)
        
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found in environment")
        
        self.openai = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
    
    async def connect_to_watch_db_server(self):
        """Connect to Watch Database MCP server"""
        try:
            watch_db_key = self.env.get("WATCH_DATABASE_API_KEY") or self.env.get("RAPIDAPI_KEY")
            if not watch_db_key:
                print("⚠️  Watch Database API key not found - MCP server will not be available")
                return False
            
            # Update config with actual key
            WATCH_DB_SERVER_CONFIG["args"][-1] = f"x-api-key: {watch_db_key}"
            
            server_params = StdioServerParameters(**WATCH_DB_SERVER_CONFIG)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.watch_db_stdio, self.watch_db_write = stdio_transport
            self.watch_db_session = await self.exit_stack.enter_async_context(
                ClientSession(self.watch_db_stdio, self.watch_db_write)
            )
            await self.watch_db_session.initialize()
            
            # List available tools
            response = await self.watch_db_session.list_tools()
            print(f"\n✅ Connected to Watch Database MCP server")
            print(f"   Available tools: {[tool.name for tool in response.tools]}")
            return True
        except Exception as e:
            print(f"⚠️  Failed to connect to Watch Database MCP server: {e}")
            print("   Continuing without MCP server (will use direct API calls)")
            return False
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools (MCP + eBay)"""
        tools = []
        
        # Add eBay tools
        tools.extend(self.ebay_tools.get_tools())
        
        # Add Watch Database MCP tools if connected
        if self.watch_db_session:
            try:
                # This is async, so we'll handle it differently
                # For now, we'll add Watch Database tools manually
                tools.extend([
                    {
                        "type": "function",
                        "function": {
                            "name": "search_watch_database",
                            "description": "Search the Watch Database for watches by name or reference number",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Watch name or reference number to search for"
                                    },
                                    "search_type": {
                                        "type": "string",
                                        "enum": ["name", "reference"],
                                        "description": "Type of search: 'name' for watch name, 'reference' for reference number",
                                        "default": "name"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_watch_makes",
                            "description": "Get all available watch brands (makes) from the database",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    }
                ])
            except:
                pass
        
        return tools
    
    async def call_watch_db_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call Watch Database tool via MCP or direct API"""
        if not self.watch_db_session:
            # Fallback to direct API calls
            api_key = self.env.get("WATCH_DATABASE_API_KEY") or self.env.get("RAPIDAPI_KEY")
            if not api_key:
                return {"success": False, "error": "Watch Database API key not available"}
            
            if name == "search_watch_database":
                query = arguments.get("query", "")
                search_type = arguments.get("search_type", "name")
                
                try:
                    if search_type == "reference":
                        result = search_reference(query, api_key)
                    else:
                        result = search_watches_by_name(query, api_key, limit=10)
                    
                    if result:
                        watches = []
                        if isinstance(result, list):
                            watches = result
                        elif isinstance(result, dict):
                            watches = result.get("data", result.get("results", result.get("watches", [])))
                            if not isinstance(watches, list):
                                watches = [result]
                        
                        return {
                            "success": True,
                            "count": len(watches),
                            "watches": watches[:10],
                            "message": f"Found {len(watches)} watches"
                        }
                    return {"success": False, "message": "No results found"}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            elif name == "get_watch_makes":
                try:
                    makes = get_all_makes(api_key, use_cache=True)
                    return {
                        "success": True,
                        "count": len(makes),
                        "makes": makes[:50],  # Limit to first 50
                        "message": f"Found {len(makes)} watch brands"
                    }
                except Exception as e:
                    return {"success": False, "error": str(e)}
        
        else:
            # Use MCP server
            try:
                result = await self.watch_db_session.call_tool(name, arguments)
                return {
                    "success": True,
                    "content": result.content if hasattr(result, 'content') else str(result),
                    "message": "Query executed via MCP server"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    async def process_query(self, query: str) -> str:
        """Process a user query and return response using OpenRouter function calling"""
        self.messages.append({
            "role": "user",
            "content": query
        })
        
        # Get all available tools
        available_tools = self.get_all_tools()
        
        # First call to OpenRouter with function calling enabled
        response = self.openai.chat.completions.create(
            model=MODEL,
            tools=available_tools if available_tools else None,
            messages=self.messages,
            max_tokens=2000,
            temperature=0.7
        )
        
        message = response.choices[0].message
        
        final_text = []
        
        # Handle tool calls (OpenRouter function calling)
        # Check if we should auto-detect eBay searches even if model doesn't call tool
        query_lower = query.lower()
        # More aggressive detection - if "ebay" is mentioned with search terms, it's an eBay query
        ebay_keywords = ["search ebay", "find on ebay", "ebay", "search for", "find", "look for", "show me", "get me"]
        is_ebay_query = "ebay" in query_lower and any(keyword in query_lower for keyword in ebay_keywords)
        
        # Auto-detect and add tool call if needed (BEFORE checking message.tool_calls)
        # Force tool usage for eBay searches - don't rely on model to call it
        if not message.tool_calls and is_ebay_query and available_tools:
            print(f"\n🔧 Auto-detected eBay search query - forcing search_ebay tool usage")
            print(f"   Query: {query}")
            # Extract search query from user input
            search_query = query
            # Try to extract the actual search terms
            for prefix in ["search ebay for", "find on ebay", "search for", "find", "look for", "show me", "get me"]:
                if prefix in query_lower:
                    search_query = query[query_lower.find(prefix) + len(prefix):].strip()
                    # Remove price filters from search query
                    search_query = re.sub(r'\s*(under|below|less than|max|maximum)\s*\$?\d+[,\d]*', '', search_query, flags=re.IGNORECASE).strip()
                    break
            
            # If we didn't find a prefix, try to extract after "ebay"
            if search_query == query and "ebay" in query_lower:
                ebay_pos = query_lower.find("ebay")
                search_query = query[ebay_pos + 4:].strip()
                # Remove "on eBay" if present
                search_query = re.sub(r'\s*on\s+ebay\s*', ' ', search_query, flags=re.IGNORECASE).strip()
                # Remove common words at start
                for word in ["for", "watches", "watch", "items", "listings"]:
                    if search_query.lower().startswith(word + " "):
                        search_query = search_query[len(word):].strip()
                # Remove price filters
                search_query = re.sub(r'\s*(under|below|less than|max|maximum)\s*\$?\d+[,\d]*', '', search_query, flags=re.IGNORECASE).strip()
            
            # Clean up the search query - remove "on eBay" if it's still there
            search_query = re.sub(r'\s*on\s+ebay\s*', ' ', search_query, flags=re.IGNORECASE).strip()
            
            # Extract price limit if mentioned
            price_limit = None
            if "under" in query_lower or "below" in query_lower or "$" in query:
                # Look for price after "under" or "below"
                under_match = re.search(r'(?:under|below|less than|max|maximum)\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', query_lower)
                if under_match:
                    price_limit = int(under_match.group(1).replace(',', ''))
                else:
                    # Fallback: find all prices and take the largest (likely the price limit)
                    price_matches = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', query)
                    if price_matches:
                        # Convert and take the largest number (likely the price limit)
                        prices = [int(p.replace(',', '')) for p in price_matches]
                        price_limit = max(prices) if prices else None
            
            # Create a fake tool call for processing
            class FakeToolCall:
                def __init__(self, name, args):
                    self.id = "manual_call"
                    self.function = type('obj', (object,), {'name': name, 'arguments': json.dumps(args)})()
            
            tool_args = {"query": search_query, "limit": 20}
            if price_limit:
                tool_args["max_price"] = price_limit
            
                message.tool_calls = [FakeToolCall("search_ebay", tool_args)]
                print(f"  → Auto-calling: search_ebay")
                print(f"     Extracted query: '{search_query}'")
                print(f"     Price limit: {price_limit if price_limit else 'None'}")
        
        # Now append the message (with or without tool calls)
        self.messages.append(message.model_dump())
        
        if message.tool_calls:
            print(f"\n🔧 Function calling: {len(message.tool_calls)} tool(s) requested")
            
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                except json.JSONDecodeError:
                    tool_args = {}
                
                print(f"  → Calling: {tool_name}")
                if tool_args:
                    print(f"    Args: {json.dumps(tool_args, indent=2)[:200]}...")
                
                # Execute tool call based on tool name
                try:
                    if tool_name in ["search_ebay", "analyze_watch_listing"]:
                        # eBay API tools - use function calling
                        result = await asyncio.to_thread(self.ebay_tools.call_tool, tool_name, tool_args)
                    elif tool_name in ["search_watch_database", "get_watch_makes"]:
                        # Watch Database tools
                        result = await self.call_watch_db_tool(tool_name, tool_args)
                    else:
                        # Try MCP server for Watch Database tools
                        if self.watch_db_session:
                            try:
                                mcp_result = await self.watch_db_session.call_tool(tool_name, tool_args)
                                result = {
                                    "success": True,
                                    "content": mcp_result.content if hasattr(mcp_result, 'content') else str(mcp_result)
                                }
                            except Exception as mcp_error:
                                result = {"success": False, "error": f"MCP error: {str(mcp_error)}"}
                        else:
                            result = {"success": False, "error": f"Unknown tool: {tool_name}"}
                    
                    # Format result for OpenRouter function calling response
                    # OpenRouter expects JSON string in tool response
                    if isinstance(result, dict):
                        # Ensure result is properly formatted
                        if "success" not in result:
                            result["success"] = True
                        result_content = json.dumps(result, indent=2, default=str)
                    else:
                        result_content = json.dumps({"success": True, "result": str(result)}, default=str)
                    
                    # Add tool response to messages (required for OpenRouter function calling)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": result_content
                    })
                    
                    print(f"  ✅ {tool_name} completed")
                    
                except Exception as e:
                    error_msg = f"Error calling tool {tool_name}: {str(e)}"
                    print(f"  ❌ {error_msg}")
                    import traceback
                    traceback.print_exc()
                    
                    # Send error back to OpenRouter
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps({
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__
                        })
                    })
            
            # Get final response from OpenRouter after tool calls
            # OpenRouter will synthesize the tool results into a natural response
            print("\n🤔 Synthesizing response...")
            response = self.openai.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            assistant_message = response.choices[0].message
            final_text.append(assistant_message.content)
            self.messages.append(assistant_message.model_dump())
            
            # Also append tool results to the response for easier parsing in Streamlit
            # Look for eBay search results in the message history
            for msg in reversed(self.messages):
                if msg.get("role") == "tool" and msg.get("name") == "search_ebay":
                    try:
                        tool_content = json.loads(msg.get("content", "{}"))
                        if tool_content.get("success") and tool_content.get("items"):
                            # Append structured data to response for Streamlit parsing
                            final_text.append("\n\n<!-- EBAY_RESULTS_START -->")
                            final_text.append(json.dumps(tool_content, indent=2))
                            final_text.append("<!-- EBAY_RESULTS_END -->")
                            break
                    except (json.JSONDecodeError, KeyError):
                        pass
        else:
            # No tool calls - log this for debugging
            print(f"\n⚠️  No tool calls detected for query: {query[:50]}...")
            print(f"   Available tools: {[t['function']['name'] for t in available_tools] if available_tools else 'None'}")
            # No tool calls needed, just return the response
            final_text.append(message.content)
        
        return "\n".join(final_text)
    
    async def chat_loop(self):
        """Run interactive chat loop"""
        print("\n" + "=" * 70)
        print("Watch & eBay Arbitrage Chatbot")
        print("=" * 70)
        print("\nI can help you:")
        print("  • Search eBay for watches and items")
        print("  • Analyze watch listings for arbitrage opportunities")
        print("  • Search the Watch Database for watch information")
        print("  • Get watch brands and models")
        print("\nType 'quit' or 'exit' to stop.\n")
        
        while True:
            try:
                query = input("You: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye! 👋")
                    break
                
                if not query:
                    continue
                
                print("\n🤔 Thinking...")
                result = await self.process_query(query)
                print(f"\nAssistant: {result}\n")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.exit_stack.aclose()


async def main():
    """Main entry point"""
    if not OPENROUTER_API_KEY:
        print("❌ Error: OPENROUTER_API_KEY not found in environment")
        print("   Please set OPENROUTER_API_KEY in .env.local")
        return
    
    chatbot = MCPChatbot()
    
    try:
        print("🔌 Connecting to MCP servers...")
        await chatbot.connect_to_watch_db_server()
        
        print("\n✅ Chatbot ready!")
        await chatbot.chat_loop()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await chatbot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

