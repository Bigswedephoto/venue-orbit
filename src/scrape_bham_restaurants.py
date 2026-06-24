import httpx
from lxml import html
import re
import csv
import sys
import os

def main():
    print("🚀 Starting Birmingham Restaurants Scraper...")
    url = "https://www.birminghamrestaurants.com/Listings/Restaurants/All"
    
    try:
        resp = httpx.get(url, timeout=15.0)
        if resp.status_code != 200:
            print(f"❌ Failed to fetch restaurant list: {resp.status_code}")
            sys.exit(1)
            
        tree = html.fromstring(resp.content)
        
        # Extract landing page profile links
        items = tree.xpath('//span[contains(@class, "landing-page-item")]')
        print(f"Found {len(items)} restaurant listings on birminghamrestaurants.com.")
        
        scraped_records = []
        
        for idx, item in enumerate(items):
            link = item.xpath('.//a')
            if not link:
                continue
            
            relative_path = link[0].get('href')
            restaurant_name = " ".join([t.strip() for t in link[0].itertext() if t.strip()])
            
            print(f"({idx+1}/{len(items)}) Scraping {restaurant_name}...")
            
            full_url = f"https://www.birminghamrestaurants.com{relative_path}"
            try:
                r = httpx.get(full_url, timeout=15.0)
                if r.status_code != 200:
                    print(f"  ⚠️ Failed to fetch profile page for {restaurant_name}: {r.status_code}")
                    continue
                    
                t = html.fromstring(r.content)
                
                # Double check / get canonical name from h1
                h1s = t.xpath('//h1')
                for h1 in h1s:
                    txt = h1.text_content().strip()
                    if txt and txt != "Birmingham Restaurants":
                        restaurant_name = txt
                        break
                        
                # Extract address
                address = ""
                addrs = t.xpath('//address')
                if addrs:
                    address = " ".join([txt.strip() for txt in addrs[0].itertext() if txt.strip()])
                    address = " ".join(address.split()) # normalize spaces
                
                # Extract menu or website URL
                # In our bulk csv upload format: we need `menu_url`. 
                # Let's see if there is any menu link or social/booking link or we just use the birminghamrestaurants profile url
                # The birminghamrestaurants site profile itself contains the menu text under PanelOverview and menus tab.
                # Since the site's own redirect postback is tricky, we can use the birminghamrestaurants profile URL as menu_url 
                # or look for an OpenTable/Resy/reservations link, or default to the profile URL.
                menu_url = full_url
                
                # Check for OpenTable booking link
                ot_links = t.xpath('//a[contains(@href, "opentable.com")]/@href')
                if ot_links:
                    # Let's save this as reservation_url or use it as website/menu fallback
                    pass
                
                # We also need coordinates (lat, lng)
                # We can geocode the address using OpenStreetMap Nominatim or leave it empty/None
                # Since Nominatim asks for 1 req/sec rate limit, let's geocode with 1s sleep.
                lat, lng = "", ""
                
                scraped_records.append({
                    'restaurant_name': restaurant_name,
                    'lat': lat,
                    'lng': lng,
                    'menu_url': menu_url,
                    'address': address,
                    'venue_name': '',  # To be associated inside the admin dashboard
                    'distance_miles': ''  # To be calculated/associated
                })
                
            except Exception as pe:
                print(f"  ❌ Error parsing profile for {restaurant_name}: {pe}")
                
        # Write to CSV in workspace root
        csv_file = "bham_restaurants_import.csv"
        csv_path = os.path.join(PROJECT_ROOT, csv_file) if 'PROJECT_ROOT' in locals() else csv_file
        
        headers = ['restaurant_name', 'lat', 'lng', 'menu_url', 'address', 'venue_name', 'distance_miles']
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for rec in scraped_records:
                writer.writerow(rec)
                
        print(f"✅ Success! Scraped {len(scraped_records)} restaurants and saved to {csv_file}")
        
    except Exception as e:
        print(f"❌ General exception: {e}")

if __name__ == "__main__":
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main()
