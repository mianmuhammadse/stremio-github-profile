#!/usr/bin/env python3
"""
Debug script to test Trakt API calls directly
"""
import sys
sys.path.append('.')

from util.firestore import get_firestore_db
from util import trakt
import logging
import json

logging.basicConfig(level=logging.DEBUG)

def main():
    # Check if user provided a uid
    if len(sys.argv) < 2:
        print("Usage: python debug_trakt.py <uid>")
        print("Example: python debug_trakt.py mianmuhammad")
        return
    
    uid = sys.argv[1]
    print(f"=== Debugging Trakt for user: {uid} ===")
    
    # Check Firestore
    print("\n1. Checking Firestore...")
    db = get_firestore_db()
    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()
    
    if not doc.exists:
        print(f"❌ No document found for uid: {uid}")
        return
    
    token_info = doc.to_dict()
    print(f"✓ Document found with keys: {list(token_info.keys())}")
    
    access_token = token_info.get("access_token")
    if not access_token:
        print("❌ No access_token in document")
        return
    
    print(f"✓ Access token found: {access_token[:10]}...")
    
    # Check token expiry
    import time
    current_ts = int(time.time())
    expired_ts = token_info.get("expired_ts")
    if expired_ts:
        print(f"Token expires at: {expired_ts}, current: {current_ts}")
        if current_ts >= expired_ts:
            print("⚠️ Token is expired")
        else:
            print("✓ Token is still valid")
    else:
        print("⚠️ No expiry timestamp found")
    
    # Test Trakt API calls
    print("\n2. Testing Trakt API calls...")
    
    # Test user profile
    try:
        print("Testing get_user_profile...")
        user_profile = trakt.get_user_profile(access_token)
        print(f"✓ User profile: {json.dumps(user_profile, indent=2)}")
    except Exception as e:
        print(f"❌ get_user_profile failed: {e}")
    
    # Test current playback
    try:
        print("\nTesting get_current_playback...")
        playback = trakt.get_current_playback(access_token)
        print(f"✓ Current playback: {json.dumps(playback, indent=2)}")
        
        if not playback:
            print("ℹ️ User is not currently watching anything")
        else:
            print(f"ℹ️ User is watching: {playback.get('type', 'unknown')} - {playback}")
    except Exception as e:
        print(f"❌ get_current_playback failed: {e}")
    
    # Test watch history
    try:
        print("\nTesting get_watch_history...")
        history = trakt.get_watch_history(access_token, limit=3)
        print(f"✓ Watch history ({len(history)} items):")
        for item in history[:3]:
            print(f"  - {item}")
    except Exception as e:
        print(f"❌ get_watch_history failed: {e}")

if __name__ == "__main__":
    main()
