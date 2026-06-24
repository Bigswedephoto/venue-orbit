#!/usr/bin/env python3
from scrapling import Fetcher

def inspect_ironcity():
    url = "https://ironcitybham.com/events/"
    print(f"🕷️ Fetching {url}...")
    response = Fetcher.get(url)
    
    # Try finding divs that could contain events
    classes_to_try = [
        "div", "section", "li", "a"
    ]
    
    # Let's check classes of divs
    print("Checking CSS selectors...")
    selectors = [
        "a[href*='/event/']", "a[href*='/events/']", ".tribe-events-calendar",
        ".tribe-events-list", "[class*='event']", "[id*='event']"
    ]
    for sel in selectors:
        matches = response.css(sel)
        print(f"  Matches for '{sel}': {len(matches)}")
        if matches:
            # print sample
            for m in matches[:3]:
                print(f"    - Text: {m.text.strip()[:60]} | Href: {m.attrib.get('href', 'None')}")

if __name__ == "__main__":
    inspect_ironcity()
