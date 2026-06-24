#!/usr/bin/env python3
from scrapling import Fetcher

def inspect():
    response = Fetcher.get("https://ironcitybham.com/events/")
    # Find event containers
    containers = response.css(".tw-plugin-upcoming-event-list")
    print(f"Containers found: {len(containers)}")
    
    if len(containers) > 0:
        container = containers[0]
        # Print child tags and text
        print("First Container Children & Text:")
        print(container.text.strip()[:300])
        # Find links
        links = container.css("a")
        for l in links:
            print(f"  Link Text: {l.text.strip()} | Href: {l.attrib.get('href')}")
            
if __name__ == "__main__":
    inspect()
