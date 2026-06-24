#!/usr/bin/env python3
from scrapling import Fetcher

def inspect():
    response = Fetcher.get("https://ironcitybham.com/events/")
    sections = response.css("div.tw-section")
    print(f"Total tw-section elements: {len(sections)}")
    
    if len(sections) > 0:
        sec = sections[0]
        print("\n--- SAMPLE tw-section TEXT ---")
        print(sec.text.strip()[:400])
        
        # Check sub-elements and class names
        sub_elements = sec.css("div, a, span")
        print(f"Sub-elements count: {len(sub_elements)}")
        for idx, el in enumerate(sub_elements):
            cls = el.attrib.get('class', 'None')
            txt = el.text.strip()[:60]
            print(f"  [{idx}]: Class={cls}, Text='{txt}'")

if __name__ == "__main__":
    inspect()
