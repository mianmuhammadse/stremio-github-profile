#!/usr/bin/env python3
"""
Test the fixed Trakt integration locally
"""
import sys
sys.path.append('.')

from api.view import get_trakt_media_info
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_offline_behavior():
    print("=== Testing Trakt Offline Behavior ===")
    
    uid = "mianmuhammad"
    
    # Test with show_offline=True
    print(f"\nTest 1: show_offline=True for {uid}")
    item, is_playing, progress_ms, duration_ms = get_trakt_media_info(uid, show_offline=True)
    print(f"Result: item={item is not None}, is_playing={is_playing}")
    if item:
        print(f"Item type: {item.get('currently_playing_type')}")
        print(f"Item name: {item.get('name')}")
    
    # Test with show_offline=False
    print(f"\nTest 2: show_offline=False for {uid}")
    item, is_playing, progress_ms, duration_ms = get_trakt_media_info(uid, show_offline=False)
    print(f"Result: item={item is not None}, is_playing={is_playing}")

if __name__ == "__main__":
    test_offline_behavior()
