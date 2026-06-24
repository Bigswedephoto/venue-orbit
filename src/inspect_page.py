#!/usr/bin/env python3
from scrapling import Fetcher

def inspect(url, tag):
    print(f"\n🔍 Inspecting elements for: {url}...")
    response = Fetcher.get(url)
    
    # Try finding some common container classes
    possible_selectors = [
        "div.event", "article", ".events-list", "div.entry", "a.event-link", 
        "div.event-card", "div.wp-block-columns", "div.wp-block-column"
    ]
    
    for sel in possible_selectors:
        matches = response.css(sel)
        if matches:
            print(f"  Found {len(matches)} matches for CSS selector: '{sel}'")
            # Print text of first match
            print(f"  First Match Sample: {matches[0].text.strip()[:100]}...")
            
    # Also dump all text on the page to search for event clues
    body_text = response.text
    print(f"  Raw Body Text Length: {len(body_text)} characters.")
    
    # Check if JSON-LD exists on either page
    json_ld = response.css("script[type='application/ld+json']")
    if json_ld:
        print(f"  ✅ Found {len(json_ld)} JSON-LD blocks on this page!")
        for idx, block in enumerate(json_ld[:3]):
            print(f"  [JSON-LD Block {idx+1}]: {block.text.strip()[:200]}...")

if __name__ == "__main__":
    inspect("https://alabamatheatre.com/events/", "alabama")
    inspect("https://www.ironcitybham.com/events", "ironcity")
