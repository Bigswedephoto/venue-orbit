#!/usr/bin/env python3
from scrapling import Fetcher

def inspect():
    response = Fetcher.get("https://ironcitybham.com/events/")
    container = response.css(".tw-plugin-upcoming-event-list")[0]
    
    # Try finding sub-elements
    li_matches = container.css("li")
    print(f"Number of `li` tags: {len(li_matches)}")
    
    div_matches = container.css("div")
    print(f"Number of `div` tags: {len(div_matches)}")
    
    # Check if there is an item container
    # Let's inspect the classes of any sub-containers inside tw-plugin-upcoming-event-list
    # Common WordPress plugins use classes like '.tw-event-item' or '.tw-event-list-item'
    for item in container.css("li")[:3]:
        print(f"\n--- LI ITEM SAMPLE ---")
        print(item.text.strip()[:200])
        links = item.css("a")
        for l in links:
            print(f"  Link: {l.text.strip()} | Href: {l.attrib.get('href')}")

if __name__ == "__main__":
    inspect()
