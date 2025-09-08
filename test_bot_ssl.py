#!/usr/bin/env python3
"""
Test bot with different SSL configurations
"""
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_with_different_configs(token):
    """Test bot with various SSL configurations"""
    
    configs = [
        ("Default requests", {}),
        ("No SSL verify", {"verify": False}),
        ("Custom timeout", {"timeout": 30}),
        ("No SSL + timeout", {"verify": False, "timeout": 30}),
    ]
    
    for name, kwargs in configs:
        print(f"\n--- Testing {name} ---")
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, **kwargs)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS with {name}!")
                print(f"Bot username: @{data['result']['username']}")
                return True
            else:
                print(f"❌ Status {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Failed with {name}: {e}")
    
    return False

if __name__ == "__main__":
    token = "8394268785:AAFykCk0r0Y7CPUMK-ZTX2eJ6amZWoVJrE4"
    test_with_different_configs(token)
