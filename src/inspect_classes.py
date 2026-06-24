#!/usr/bin/env python3
from scrapling import Fetcher

def print_classes():
    response = Fetcher.get("https://ironcitybham.com/events/")
    # Find all elements with classes containing 'event'
    elements = response.css("[class*='event']")
    seen_classes = set()
    for el in elements:
        cls_str = el.attrib.get("class", "")
        for cls in cls_str.split():
            if "event" in cls:
                seen_classes.add(cls)
                
    print("Class names containing 'event':")
    for cls in sorted(seen_classes):
        print(f"  - {cls}")

if __name__ == "__main__":
    print_classes()
