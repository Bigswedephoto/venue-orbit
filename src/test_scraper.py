#!/usr/bin/env python3
import sys
import os

# Add local paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapling import Fetcher

def test_fetch():
    print("🕷️ Testing Scrapling connection to example.com...")
    try:
        # Fetcher gets page content and automatically handles headers/stealth
        response = Fetcher.get("https://example.com")
        print(f"✅ Response Status: {response.status}")
        
        # Verify page title using scrapling's select/CSS parsing
        title_element = response.css("h1")
        if title_element:
            print(f"✅ Extracted Title: {title_element[0].text.strip()}")
        else:
            print("⚠️ Warning: No h1 title element found.")
            
        print("\n🎉 Scrapling installation and fetch verification: SUCCESSFUL!")
    except Exception as e:
        print(f"❌ Scrapling test failed: {e}")

if __name__ == "__main__":
    test_fetch()
