#!/usr/bin/env python3
from scrapling import Fetcher

def inspect():
    response = Fetcher.get("https://ironcitybham.com/events/")
    container = response.css(".tw-plugin-upcoming-event-list")[0]
    
    # Get all direct div children
    divs = container.xpath("./div")
    print(f"Direct div children count: {len(divs)}")
    
    # If direct div children count is 1, let's look inside that one
    if len(divs) == 1:
        nested_divs = divs[0].xpath("./div")
        print(f"Nested div children count under the first child: {len(nested_divs)}")
        for idx, nd in enumerate(nested_divs[:3]):
            print(f"  Nested Child {idx} classes: {nd.attrib.get('class')}")
            # Print sample text
            print(f"    Text: {nd.text.strip()[:150]}")
    else:
        for idx, d in enumerate(divs[:3]):
            print(f"  Child {idx} classes: {d.attrib.get('class')}")

if __name__ == "__main__":
    inspect()
