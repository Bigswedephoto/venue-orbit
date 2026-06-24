#!/usr/bin/env python3
import json
from scrapling import Fetcher

def dump(url):
    print(f"\n--- JSON-LD for {url} ---")
    response = Fetcher.get(url)
    json_ld = response.css("script[type='application/ld+json']")
    for idx, block in enumerate(json_ld):
        text = block.text.strip()
        try:
            data = json.loads(text)
            # Dump keys
            if isinstance(data, dict):
                print(f"Block {idx}: Keys: {list(data.keys())}")
                if "@graph" in data:
                    print(f"  @graph contains {len(data['@graph'])} items")
                    for i, item in enumerate(data["@graph"]):
                        print(f"    Item {i}: @type = {item.get('@type')}, name = {item.get('name', 'N/A')[:40]}")
            elif isinstance(data, list):
                print(f"Block {idx}: List of length {len(data)}")
                for i, item in enumerate(data[:3]):
                    print(f"    Item {i}: @type = {item.get('@type')}, name = {item.get('name', 'N/A')[:40]}")
        except Exception as e:
            print(f"Block {idx}: Failed to parse JSON: {e}")

if __name__ == "__main__":
    dump("https://alabamatheatre.com/events/")
    dump("https://ironcitybham.com/events/")
