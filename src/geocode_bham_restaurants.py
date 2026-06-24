import csv
import time
import httpx
import sys
import os

HEADERS = {
    "User-Agent": "VenueOrbitScraper/1.0 (contact@venue-orbit.com)"
}

# Local coordinate lookup dictionary for Birmingham restaurants to guarantee matches or override failures
RESTAURANT_FALLBACKS = {
    "Bellini's Ristorante & Bar": (33.4079, -86.7454),
    "Billy's Sports Grill - Overton": (33.5186, -86.7118),
    "Bistro V": (33.4290, -86.7909),
    "FoodBar": (33.4475, -86.7876),
    "Troup's Pizza": (33.4475, -86.7876),
}

def geocode_address(name, address):
    """Geocode address using fallbacks first, then OpenStreetMap Nominatim API."""
    if name in RESTAURANT_FALLBACKS:
        lat, lng = RESTAURANT_FALLBACKS[name]
        print(f"  ✅ Found coords for '{name}' in local fallbacks: ({lat}, {lng})")
        return lat, lng

    if not address or address.strip() == "":
        return None, None
        
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }
    
    try:
        time.sleep(1.0)
        resp = httpx.get(url, params=params, headers=HEADERS, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                print(f"  ✅ Geocoded '{address}': ({lat}, {lng})")
                return lat, lng
            else:
                simplified = address.replace("Suite", "").replace("Ste.", "").replace("Heights Center", "").replace("Heights Village", "")
                simplified = " ".join(simplified.split())
                if simplified != address:
                    print(f"  ⚠️ Direct search failed, trying simplified address: '{simplified}'...")
                    time.sleep(1.0)
                    params["q"] = simplified
                    resp2 = httpx.get(url, params=params, headers=HEADERS, timeout=10.0)
                    if resp2.status_code == 200:
                        data2 = resp2.json()
                        if data2:
                            lat = float(data2[0]["lat"])
                            lng = float(data2[0]["lon"])
                            print(f"    ✅ Geocoded simplified address: ({lat}, {lng})")
                            return lat, lng
        print(f"  ❌ No coordinates found for: {address}")
    except Exception as e:
        print(f"  ❌ Geocoding exception for '{address}': {e}")
        
    return None, None

def main():
    csv_file = "bham_restaurants_import.csv"
    if not os.path.exists(csv_file):
        print(f"❌ File {csv_file} does not exist!")
        sys.exit(1)
        
    records = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
            
    print(f"🌍 Running geocoder updates (applying manual fallbacks)...")
    
    for idx, row in enumerate(records):
        name = row['restaurant_name']
        address = row['address']
        
        # Only query if coordinates are currently empty or we have a manual fallback for it
        if not row.get('lat') or not row.get('lng') or name in RESTAURANT_FALLBACKS:
            lat, lng = geocode_address(name, address)
            if lat and lng:
                row['lat'] = str(lat)
                row['lng'] = str(lng)
            
    headers = ['restaurant_name', 'lat', 'lng', 'menu_url', 'address', 'venue_name', 'distance_miles']
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in records:
            writer.writerow(row)
            
    print(f"✅ Finished! Geocoded records saved back to {csv_file}")

if __name__ == "__main__":
    main()
