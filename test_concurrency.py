#!/usr/bin/env python
"""
Concurrency Test Script - 5 Simultaneous Booking Requests

This script tests the pessimistic locking implementation by sending
5 concurrent requests to book the SAME seat at the SAME time.

Expected Result: Only 1 request succeeds, 4 fail with conflict error.

Usage: python test_concurrency.py
"""

import requests
import concurrent.futures
import time
import json

API_BASE = "http://localhost:8000/api"
SEAT_ID = 10  # Use seat 10 for testing (change if needed)
SHOW_ID = 1

def reset_seat():
    """Reset the seat by releasing any existing lock/booking via API."""
    print(f"Resetting seat {SEAT_ID} for show {SHOW_ID}...")
    try:
        # Try to release any lock
        response = requests.post(
            f"{API_BASE}/release-lock/",
            json={"seat_id": SEAT_ID, "show_id": SHOW_ID},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"  Release lock: {response.json().get('message', 'done')}")
    except:
        pass
    
    # Also try to delete via a direct call (if seat is BOOKED, we need Django shell)
    # For simplicity, we'll use a different seat each time or reset via shell

def make_booking_request(request_id):
    """Make a single booking request and return the result."""
    start_time = time.time()
    try:
        response = requests.post(
            f"{API_BASE}/book-seat/",
            json={"seat_id": SEAT_ID, "show_id": SHOW_ID},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        elapsed = time.time() - start_time
        return {
            "request_id": request_id,
            "status_code": response.status_code,
            "response": response.json(),
            "elapsed_ms": round(elapsed * 1000, 2)
        }
    except Exception as e:
        return {
            "request_id": request_id,
            "error": str(e)
        }

def run_concurrent_test():
    print("=" * 60)
    print("CONCURRENCY TEST: 5 Simultaneous Booking Requests")
    print("=" * 60)
    print(f"\nTarget: POST {API_BASE}/book-seat/")
    print(f"Payload: seat_id={SEAT_ID}, show_id={SHOW_ID}")
    print(f"\nSending 5 requests simultaneously...\n")
    
    # Use ThreadPoolExecutor to send 5 requests at the same time
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all 5 requests at once
        futures = [executor.submit(make_booking_request, i+1) for i in range(5)]
        
        # Wait for all to complete
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # Sort by request_id for consistent output
    results.sort(key=lambda x: x.get("request_id", 0))
    
    # Analyze results
    success_count = 0
    conflict_count = 0
    
    print("-" * 60)
    print("RESULTS:")
    print("-" * 60)
    
    for result in results:
        req_id = result.get("request_id", "?")
        status = result.get("status_code", "ERROR")
        elapsed = result.get("elapsed_ms", "N/A")
        
        if status == 200:
            success_count += 1
            status_text = "✅ SUCCESS"
            message = result.get("response", {}).get("message", "")
        elif status == 409:
            conflict_count += 1
            status_text = "❌ CONFLICT"
            message = result.get("response", {}).get("message", "")
        else:
            status_text = f"⚠️  {status}"
            message = str(result.get("response") or result.get("error", ""))
        
        print(f"  Request #{req_id}: {status_text} ({elapsed}ms) - {message}")
    
    print("-" * 60)
    print(f"\nSUMMARY:")
    print(f"  ✅ Successful bookings: {success_count}")
    print(f"  ❌ Rejected (conflict): {conflict_count}")
    print(f"  Total requests: {len(results)}")
    print()
    
    if success_count == 1 and conflict_count == 4:
        print("🎉 TEST PASSED! Pessimistic locking is working correctly.")
        print("   Only 1 request succeeded, 4 were properly rejected.")
    elif success_count == 0:
        print("⚠️  No requests succeeded. The seat is already booked.")
        print(f"\n   To reset seat {SEAT_ID}, run:")
        print(f'   python manage.py shell -c "from booking.models import Booking; Booking.objects.filter(seat_id={SEAT_ID}, show_id={SHOW_ID}).delete(); print(\'Seat reset\')"')
        print(f"\n   Or change SEAT_ID at top of test_concurrency.py to an unused seat.")
    else:
        print(f"⚠️  Unexpected result: {success_count} successes")
    
    print("=" * 60)

if __name__ == "__main__":
    run_concurrent_test()
