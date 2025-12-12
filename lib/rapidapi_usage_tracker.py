"""
Track RapidAPI usage to help manage the 30 requests/month free tier limit
"""
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

USAGE_FILE = "data/rapidapi_usage.json"


def get_usage_stats() -> dict:
    """Get current usage statistics"""
    if not os.path.exists(USAGE_FILE):
        return {
            "total_requests": 0,
            "requests_this_month": 0,
            "month_start": datetime.now().strftime("%Y-%m-%d"),
            "requests": []
        }
    
    with open(USAGE_FILE, "r") as f:
        return json.load(f)


def record_request(query: str, items_returned: int):
    """Record an API request"""
    os.makedirs("data", exist_ok=True)
    
    stats = get_usage_stats()
    
    # Check if we need to reset monthly count
    month_start = datetime.strptime(stats.get("month_start", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
    now = datetime.now()
    
    # If new month, reset counter
    if (now - month_start).days > 31:
        stats["requests_this_month"] = 0
        stats["month_start"] = now.strftime("%Y-%m-%d")
    
    # Record request
    stats["total_requests"] += 1
    stats["requests_this_month"] += 1
    stats["requests"].append({
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "items_returned": items_returned
    })
    
    # Keep only last 50 requests
    if len(stats["requests"]) > 50:
        stats["requests"] = stats["requests"][-50:]
    
    with open(USAGE_FILE, "w") as f:
        json.dump(stats, f, indent=2)
    
    # Warn if approaching limit
    remaining = 30 - stats["requests_this_month"]
    if remaining <= 5:
        print(f"⚠️  WARNING: Only {remaining} RapidAPI requests remaining this month!")


def print_usage_stats():
    """Print current usage statistics"""
    stats = get_usage_stats()
    
    print("\n" + "=" * 70)
    print("RapidAPI Usage Statistics")
    print("=" * 70)
    print(f"Total requests (all time): {stats['total_requests']}")
    print(f"Requests this month: {stats['requests_this_month']}/30")
    print(f"Remaining this month: {30 - stats['requests_this_month']}")
    print(f"Month started: {stats.get('month_start', 'N/A')}")
    
    if stats['requests_this_month'] >= 30:
        print("\n⚠️  MONTHLY LIMIT REACHED - No more requests until next month!")
    elif stats['requests_this_month'] >= 25:
        print("\n⚠️  WARNING: Approaching monthly limit!")
    
    print("=" * 70 + "\n")

