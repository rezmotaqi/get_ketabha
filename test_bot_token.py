#!/usr/bin/env python3
"""
Simple test to verify bot token works
"""
import requests
import sys

def test_bot_token(token):
    """Test if bot token is valid"""
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        print(f"Testing bot token: {token[:20]}...")
        
        response = requests.get(url, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Bot token is valid!")
            print(f"Bot info: {data}")
            return True
        else:
            print("❌ Bot token is invalid or there's an API issue")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

if __name__ == "__main__":
    token = "8394268785:AAFykCk0r0Y7CPUMK-ZTX2eJ6amZWoVJrE4"
    test_bot_token(token)
