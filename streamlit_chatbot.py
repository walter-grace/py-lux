#!/usr/bin/env python3
"""
Streamlit Chatbot Application
Interactive web interface for Watch & eBay Arbitrage Chatbot
"""
import streamlit as st
import asyncio
import json
import os
import sys
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Load environment
load_dotenv(".env")
load_dotenv(".env.local", override=True)

# Import chatbot
from chatbot_mcp import MCPChatbot

# Page configuration
st.set_page_config(
    page_title="Watch & eBay Arbitrage Chatbot",
    page_icon="⌚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
    }
    .sample-prompt {
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-left: 3px solid #1f77b4;
        background-color: #f0f2f6;
        cursor: pointer;
        border-radius: 5px;
    }
    .sample-prompt:hover {
        background-color: #e0e2e6;
    }
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Sample prompts
SAMPLE_PROMPTS = [
    {
        "category": "eBay Search",
        "prompts": [
            "Search eBay for Rolex Submariner watches under $10,000",
            "Find Omega Speedmaster watches on eBay",
            "Search eBay for PSA 10 Charizard cards",
            "Find Rolex GMT-Master watches on eBay",
            "Search for TAG Heuer Carrera watches under $3000"
        ]
    },
    {
        "category": "Watch Analysis",
        "prompts": [
            "Analyze this watch listing: Rolex Submariner Date 116610LN - $8,500",
            "Is this a good deal? Rolex GMT-Master II 126710BLNR for $12,000",
            "Analyze: Omega Speedmaster Professional 311.30.42.30.01.005 - $5,200",
            "Check this watch: TAG Heuer Carrera Calibre 16 - $2,800"
        ]
    },
    {
        "category": "Watch Database",
        "prompts": [
            "Search the watch database for reference 116610LN",
            "What watch brands are available in the database?",
            "Find information about Rolex Submariner in the watch database",
            "Search for Omega Speedmaster reference 311.30.42.30.01.005"
        ]
    },
    {
        "category": "Combined Queries",
        "prompts": [
            "Find Rolex watches on eBay under $10,000 and analyze if they're good deals",
            "Search for Omega Speedmaster on eBay and check the watch database for details",
            "Find cheap Rolex Submariner watches and analyze them for arbitrage opportunities"
        ]
    }
]


@st.cache_resource
def initialize_chatbot():
    """Initialize chatbot (cached to avoid re-initialization)"""
    try:
        chatbot = MCPChatbot()
        return chatbot
    except Exception as e:
        st.error(f"Failed to initialize chatbot: {e}")
        return None


async def process_message_async(chatbot: MCPChatbot, message: str) -> str:
    """Process message asynchronously"""
    return await chatbot.process_query(message)


def process_message(chatbot: MCPChatbot, message: str) -> str:
    """Wrapper to run async function in Streamlit"""
    try:
        # Use asyncio.run which handles event loop creation/cleanup
        # This works better with Streamlit
        return asyncio.run(process_message_async(chatbot, message))
    except RuntimeError:
        # If event loop already exists, create a new one
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(process_message_async(chatbot, message))
                return result
            finally:
                loop.close()
        except Exception as e:
            import traceback
            return f"Error: {str(e)}\n\n{traceback.format_exc()}"
    except Exception as e:
        import traceback
        return f"Error: {str(e)}\n\n{traceback.format_exc()}"


def display_response_with_images(response: str):
    """Parse response and display eBay results with images and links"""
    try:
        import re
        
        # First, try to extract structured data from HTML comments (our custom format)
        ebay_items = None
        if "<!-- EBAY_RESULTS_START -->" in response:
            start_idx = response.find("<!-- EBAY_RESULTS_START -->") + len("<!-- EBAY_RESULTS_START -->")
            end_idx = response.find("<!-- EBAY_RESULTS_END -->")
            if end_idx > start_idx:
                json_str = response[start_idx:end_idx].strip()
                # Remove any leading/trailing whitespace and newlines
                json_str = json_str.strip()
                try:
                    data = json.loads(json_str)
                    if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:
                        ebay_items = data["items"]
                        # Debug output
                        st.success(f"✅ Parsed {len(ebay_items)} eBay items from search results")
                except json.JSONDecodeError as e:
                    # Show error in UI for debugging
                    st.error(f"❌ Failed to parse JSON: {str(e)[:100]}")
                    st.code(json_str[:500], language="json")
                    pass
        
        # Fallback: Try to extract JSON from the response
        if not ebay_items:
            # Try to find JSON objects in the response
            json_pattern = r'\{[^{}]*"items"[^{}]*\[.*?\].*?\}'
            matches = re.findall(json_pattern, response, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    if "items" in data and isinstance(data["items"], list):
                        # Check if it looks like eBay results
                        if data["items"] and isinstance(data["items"][0], dict) and "url" in data["items"][0]:
                            ebay_items = data["items"]
                            break
                except json.JSONDecodeError:
                    continue
        
        # Also try to parse the entire response as JSON (if it's a tool result)
        if not ebay_items:
            try:
                data = json.loads(response)
                if "items" in data and isinstance(data["items"], list):
                    ebay_items = data["items"]
            except (json.JSONDecodeError, TypeError):
                pass
        
        # If we found eBay items, display them nicely
        if ebay_items and len(ebay_items) > 0:
            st.markdown("---")
            st.markdown("### 📦 eBay Search Results")
            st.markdown(f"**Found {len(ebay_items)} items**\n")
            
            # Debug: Show first item's image URL
            if st.session_state.get("debug_mode", False):
                with st.expander("🔍 Debug: First Item Data"):
                    st.json(ebay_items[0] if ebay_items else {})
            
            # Display items in a grid
            cols_per_row = 2
            for i in range(0, len(ebay_items), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(ebay_items):
                        item = ebay_items[i + j]
                        with col:
                            # Create a card-like container with border
                            st.markdown('<div class="ebay-item-card">', unsafe_allow_html=True)
                            
                            # Display image if available - use HTML directly for better compatibility
                            image_url = item.get("image_url") or item.get("imageUrl")
                            if image_url:
                                # Use HTML img tag directly - more reliable for external URLs
                                st.markdown(
                                    f'<div style="text-align: center; margin-bottom: 10px;">'
                                    f'<img src="{image_url}" '
                                    f'style="width: 100%; max-height: 300px; object-fit: contain; border-radius: 8px; border: 1px solid #e0e0e0; cursor: pointer;" '
                                    f'alt="{item.get("title", "")[:50]}" '
                                    f'onclick="window.open(\'{image_url}\', \'_blank\')" '
                                    f'onerror="this.onerror=null; this.style.display=\'none\';" />'
                                    f'</div>',
                                    unsafe_allow_html=True
                                )
                                # Also add caption
                                caption = item.get("title", "")[:60] + "..." if len(item.get("title", "")) > 60 else item.get("title", "")
                                if caption:
                                    st.caption(caption)
                            else:
                                st.markdown("*[No image available]*")
                                
                                # Display item info
                                title = item.get("title", "No title")
                                price = item.get("price_usd") or item.get("price")
                                shipping = item.get("shipping_usd") or item.get("shipping", 0)
                                total = item.get("total_cost_usd") or (price + shipping if price else None)
                                url = item.get("url") or item.get("itemWebUrl")
                                
                                # Title
                                st.markdown(f"**{title[:70]}{'...' if len(title) > 70 else ''}**")
                                
                                # Price
                                if price:
                                    if total and total != price and shipping > 0:
                                        st.markdown(f"💰 **${price:,.2f}** + ${shipping:.2f} = **${total:,.2f}**")
                                    else:
                                        st.markdown(f"💰 **${price:,.2f}**")
                                
                                # Condition
                                condition = item.get("condition") or item.get("item_condition")
                                if condition:
                                    st.markdown(f"📦 {condition}")
                                
                                # Brand/Model if available
                                brand = item.get("brand")
                                model = item.get("model")
                                if brand or model:
                                    model_info = f"{brand} {model}".strip()
                                    if model_info:
                                        st.markdown(f"⌚ {model_info}")
                                
                                # Display link
                                if url:
                                    st.markdown(f"[🔗 View on eBay →]({url})")
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                                st.markdown("<br>", unsafe_allow_html=True)
            
            # Clean up response text (remove HTML comments and JSON)
            clean_response = response
            if "<!-- EBAY_RESULTS_START -->" in clean_response:
                start_idx = clean_response.find("<!-- EBAY_RESULTS_START -->")
                end_idx = clean_response.find("<!-- EBAY_RESULTS_END -->") + len("<!-- EBAY_RESULTS_END -->")
                clean_response = clean_response[:start_idx] + clean_response[end_idx:].strip()
            
            # Also show the text response below (if there's meaningful content)
            if clean_response.strip() and len(clean_response.strip()) > 50:
                st.markdown("---")
                st.markdown("**Response:**")
                st.markdown(clean_response)
        else:
            # No eBay items found, just display the response normally
            # But clean up HTML comments if present
            clean_response = response
            if "<!-- EBAY_RESULTS_START -->" in clean_response:
                start_idx = clean_response.find("<!-- EBAY_RESULTS_START -->")
                end_idx = clean_response.find("<!-- EBAY_RESULTS_END -->") + len("<!-- EBAY_RESULTS_END -->")
                clean_response = clean_response[:start_idx] + clean_response[end_idx:].strip()
            st.markdown(clean_response)
            
    except Exception as e:
        # If parsing fails, show error and display the response normally
        st.warning(f"⚠️ Error parsing eBay results: {str(e)[:200]}")
        import traceback
        st.code(traceback.format_exc()[:500])
        st.markdown(response)


def main():
    """Main Streamlit app"""
    # Header
    st.title("⌚ Watch & eBay Arbitrage Chatbot")
    st.markdown("**Powered by OpenRouter (Claude) with MCP servers for eBay and Watch Database**")
    
    # Sidebar
    with st.sidebar:
        st.header("📋 Sample Prompts")
        st.markdown("Click any prompt to use it:")
        
        for category in SAMPLE_PROMPTS:
            with st.expander(category["category"], expanded=False):
                for prompt in category["prompts"]:
                    # Use a shorter display text but store full prompt
                    display_text = prompt[:55] + "..." if len(prompt) > 55 else prompt
                    if st.button(
                        f"💬 {display_text}",
                        key=f"prompt_{hash(prompt)}",
                        use_container_width=True,
                        help=prompt  # Show full prompt on hover
                    ):
                        # Set the prompt and trigger processing
                        st.session_state.pending_prompt = prompt
                        st.rerun()
        
        st.divider()
        
        st.header("⚙️ Configuration")
        
        # Check API keys
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        watch_db_key = os.getenv("WATCH_DATABASE_API_KEY") or os.getenv("RAPIDAPI_KEY", "")
        ebay_oauth = os.getenv("EBAY_OAUTH", "")
        ebay_client_id = os.getenv("EBAY_CLIENT_ID", "")
        
        if openrouter_key:
            st.success("✅ OpenRouter API Key")
        else:
            st.error("❌ OpenRouter API Key Missing")
        
        if watch_db_key:
            st.success("✅ Watch Database API Key")
        else:
            st.warning("⚠️ Watch Database API Key Missing")
        
        if ebay_oauth or ebay_client_id:
            st.success("✅ eBay Credentials")
        else:
            st.warning("⚠️ eBay Credentials Missing")
        
        st.divider()
        
        st.markdown("### 💡 Tips")
        st.markdown("""
        - Ask about watches, trading cards, or arbitrage opportunities
        - The chatbot can search eBay and analyze listings
        - Watch Database integration provides detailed watch information
        - All searches use real-time data from APIs
        """)
    
    # Initialize chatbot
    if "chatbot" not in st.session_state:
        with st.spinner("🔌 Connecting to MCP servers and initializing chatbot..."):
            chatbot = initialize_chatbot()
            if chatbot:
                # Connect to MCP server
                try:
                    connected = asyncio.run(chatbot.connect_to_watch_db_server())
                    if connected:
                        st.session_state.mcp_connected = True
                    else:
                        st.session_state.mcp_connected = False
                except RuntimeError:
                    # If event loop exists, create new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        connected = loop.run_until_complete(chatbot.connect_to_watch_db_server())
                        if connected:
                            st.session_state.mcp_connected = True
                        else:
                            st.session_state.mcp_connected = False
                    finally:
                        loop.close()
                except Exception as e:
                    st.session_state.mcp_connected = False
                    st.warning(f"MCP server connection failed: {e}")
                
                st.session_state.chatbot = chatbot
                st.session_state.messages = []
                st.success("✅ Chatbot initialized!")
            else:
                st.error("Failed to initialize chatbot. Check your API keys.")
                st.stop()
    
    chatbot = st.session_state.chatbot
    
    # Display connection status
    if st.session_state.get("mcp_connected"):
        st.success("✅ Connected to Watch Database MCP server")
    else:
        st.info("ℹ️ Watch Database MCP server not connected (using direct API calls)")
    
    # Chat interface
    st.divider()
    st.header("💬 Chat")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I can help you:\n\n• Search eBay for watches and items\n• Analyze watch listings for arbitrage opportunities\n• Search the Watch Database for watch information\n• Get watch brands and models\n\nWhat would you like to know?"
            }
        ]
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Handle sidebar prompt clicks
    if "pending_prompt" in st.session_state and st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        del st.session_state.pending_prompt  # Clear it
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Processing..."):
                try:
                    # Create a container for debug info
                    debug_container = st.empty()
                    
                    # Check if this is an eBay search query
                    query_lower = prompt.lower()
                    is_ebay_query = "ebay" in query_lower and any(kw in query_lower for kw in ["search", "find", "look"])
                    
                    if is_ebay_query:
                        debug_container.info("🔍 Detected eBay search query - calling search_ebay tool...")
                    
                    response = process_message(chatbot, prompt)
                    
                    # Clear debug info
                    debug_container.empty()
                    
                    # Try to parse and display eBay results with images
                    display_response_with_images(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    import traceback
                    st.code(traceback.format_exc())
        st.rerun()
    
    # User input from chat
    if prompt := st.chat_input("Ask me about watches, eBay listings, or arbitrage opportunities..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    # Create a container for debug info
                    debug_container = st.empty()
                    
                    # Check if this is an eBay search query
                    query_lower = prompt.lower()
                    is_ebay_query = "ebay" in query_lower and any(kw in query_lower for kw in ["search", "find", "look"])
                    
                    if is_ebay_query:
                        debug_container.info("🔍 Detected eBay search query - calling search_ebay tool...")
                    
                    response = process_message(chatbot, prompt)
                    
                    # Clear debug info
                    debug_container.empty()
                    
                    # Try to parse and display eBay results with images
                    display_response_with_images(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    import traceback
                    st.code(traceback.format_exc())
    
    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Chat cleared! How can I help you?"
            }
        ]
        st.rerun()


if __name__ == "__main__":
    main()

