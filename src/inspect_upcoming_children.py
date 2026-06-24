#!/usr/bin/env python3
from scrapling import Fetcher

def inspect():
    response = Fetcher.get("https://ironcitybham.com/events/")
    # Let's inspect the tags of the children of the list
    container = response.css(".tw-plugin-upcoming-event-list")[0]
    # Check immediate children tags and classes
    print("Children elements of the event list:")
    # We can fetch direct children elements using CSS select
    children = container.xpath("./*")
    print(f"Direct children count: {len(children)}")
    if children:
        for idx, child in enumerate(children[:5]):
            print(f"Child {idx}: Tag = {child.tag_name}, Class = {child.attrib.get('class')}")
            # Print title
            title_el = child.css("a[href*='/event/']")
            title_text = title_el[1].text.strip() if len(title_el) > 1 else title_el[0].text.strip() if title_el else "None"
            print(f"  Event Title Text: {title_text}")

if __name__ == "__main__":
    inspect()
