#!/usr/bin/env python3
import sys
import os
import time
import math
import sqlite3
import httpx
from database import get_db_connection

# User agent required by Nominatim usage policy
HEADERS = {
    "User-Agent": "VenueOrbit/1.0 (contact@venue-orbit.com)"
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points in miles."""
    R = 3958.8  # Earth's radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Local coordinate lookup dictionary for Birmingham seed venues to bypass/correct API lookups
GEOCIDING_FALLBACKS = {
    "Iron City Bham": (33.5065, -86.7937),
    "Red Mountain Theatre": (33.5077, -86.8076),
    "Virginia Samford Theatre": (33.5033, -86.7870),
    "BJCC": (33.5235, -86.8118),
    "Terrific New Theatre": (33.5186, -86.8085),
    "Theatre Downtown": (33.5190, -86.7950),
    "Dorothy Jemison Day Theater": (33.5226, -86.8122),
    "Encore Bham": (33.5132, -86.8066),
    "Homewood Theatre": (33.4795, -86.7963),
    "Woodlawn Theatre": (33.5396, -86.7527)
}

def geocode_venue(venue_name):
    """Geocode a venue using OpenStreetMap Nominatim API with local fallback lookup."""
    print(f"🌍 Geocoding venue: {venue_name}...")
    
    # Check local fallbacks first to correct errors (e.g. Theatre Downtown to Buffalo) and avoid API limits
    if venue_name in GEOCIDING_FALLBACKS:
        lat, lng = GEOCIDING_FALLBACKS[venue_name]
        print(f"  ✅ Found coordinates for {venue_name} in local fallbacks: ({lat}, {lng})")
        return lat, lng

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{venue_name}, Birmingham, AL",
        "format": "json",
        "limit": 1
    }
    
    try:
        # Nominatim asks for 1 req/sec rate limit
        time.sleep(1.0)
        resp = httpx.get(url, params=params, headers=HEADERS, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                print(f"  ✅ Found coordinates for {venue_name}: ({lat}, {lng})")
                return lat, lng
            else:
                # Try a broader search just in Birmingham AL
                print(f"  ⚠️ Direct search failed, trying fallback search for: {venue_name}...")
                time.sleep(1.0)
                params["q"] = f"{venue_name}, AL"
                resp2 = httpx.get(url, params=params, headers=HEADERS, timeout=10.0)
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    if data2:
                        lat = float(data2[0]["lat"])
                        lng = float(data2[0]["lon"])
                        print(f"  ✅ Found fallback coordinates for {venue_name}: ({lat}, {lng})")
                        return lat, lng
        print(f"  ❌ No coordinates found for {venue_name}.")
    except Exception as e:
        print(f"  ❌ Geocoding exception for {venue_name}: {e}")
        
    return None, None

def fetch_nearby_dining(lat, lng, radius_meters=800):
    """Fetch nearby dining establishments from OSM Overpass API."""
    print(f"🍔 Fetching dining options near ({lat}, {lng}) within {radius_meters}m...")
    url = "https://overpass-api.de/api/interpreter"
    
    # Overpass QL query to find restaurants, bars, cafes, pubs
    query = f"""
    [out:json];
    nwr(around:{radius_meters},{lat},{lng})["amenity"~"^(restaurant|bar|pub|cafe)$"];
    out center;
    """
    
    try:
        resp = httpx.post(url, data=query, headers=HEADERS, timeout=25.0)
        if resp.status_code == 200:
            elements = resp.json().get("elements", [])
            print(f"  ✅ Found {len(elements)} dining options.")
            return elements
        else:
            print(f"  ❌ Overpass API error: {resp.status_code}")
    except Exception as e:
        print(f"  ❌ Overpass API exception: {e}")
        
    return []

def enrich_venues_dining():
    """Geocode venues, fetch nearby dining, and save mapping to SQLite."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Force update coordinates for venues in our GEOCIDING_FALLBACKS to correct errors and handle unindexed venues
    print("📌 Applying geocoding fallbacks...")
    for name, coords in GEOCIDING_FALLBACKS.items():
        lat, lng = coords
        # Detect coordinate changes to clear stale dining maps
        cursor.execute("SELECT id, lat, lng FROM venues WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            old_lat, old_lng = row["lat"], row["lng"]
            if old_lat != lat or old_lng != lng:
                print(f"🔄 Coordinates changed for {name}. Clearing old dining maps.")
                cursor.execute("DELETE FROM venue_dining_map WHERE venue_id = ?", (row["id"],))
                
        cursor.execute(
            "UPDATE venues SET lat = ?, lng = ? WHERE name = ?",
            (lat, lng, name)
        )
    conn.commit()
    
    # Fetch venues missing coordinates
    cursor.execute("SELECT id, name FROM venues WHERE lat IS NULL OR lng IS NULL")
    unmapped_venues = cursor.fetchall()
    
    for v in unmapped_venues:
        venue_id = v["id"]
        venue_name = v["name"]
        
        lat, lng = geocode_venue(venue_name)
        if lat and lng:
            cursor.execute(
                "UPDATE venues SET lat = ?, lng = ? WHERE id = ?",
                (lat, lng, venue_id)
            )
            conn.commit()
            
    # Now run dining integration for all venues that have coordinates
    cursor.execute("SELECT id, name, lat, lng FROM venues WHERE lat IS NOT NULL AND lng IS NOT NULL")
    mapped_venues = cursor.fetchall()
    
    print(f"\n🚀 Running dining enrichment for {len(mapped_venues)} geocoded venues...")
    
    for v in mapped_venues:
        venue_id = v["id"]
        venue_name = v["name"]
        v_lat = v["lat"]
        v_lng = v["lng"]
        
        # Check if we already have dining mappings for this venue
        cursor.execute("SELECT COUNT(*) as cnt FROM venue_dining_map WHERE venue_id = ?", (venue_id,))
        if cursor.fetchone()["cnt"] > 0:
            print(f"⏭️ Skipping dining enrichment for {venue_name} (already has mapped dining spots).")
            continue
            
        elements = fetch_nearby_dining(v_lat, v_lng)
        
        saved_dining_count = 0
        mapped_count = 0
        
        for el in elements:
            tags = el.get("tags", {})
            rest_name = tags.get("name")
            if not rest_name or "sweet tea" in rest_name.lower():
                continue
                
            # Extract coordinates (ways/relations have center, nodes have lat/lon)
            r_lat = el.get("lat") or el.get("center", {}).get("lat")
            r_lng = el.get("lon") or el.get("center", {}).get("lon")
            if not r_lat or not r_lng:
                continue
                
            # Build address
            street = tags.get("addr:street", "")
            number = tags.get("addr:housenumber", "")
            address = f"{number} {street}".strip() or "Birmingham, AL"
            
            menu_url = tags.get("website", "")
            if not menu_url:
                continue
            
            # Save restaurant
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO restaurants (name, lat, lng, menu_url, address)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (rest_name, r_lat, r_lng, menu_url, address)
                )
                
                # Fetch restaurant ID
                cursor.execute("SELECT id FROM restaurants WHERE name = ?", (rest_name,))
                rest_row = cursor.fetchone()
                if rest_row:
                    rest_id = rest_row["id"]
                    
                    # Compute haversine distance
                    dist = haversine_distance(v_lat, v_lng, r_lat, r_lng)
                    
                    # Insert mapping
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO venue_dining_map (venue_id, restaurant_id, distance_miles)
                        VALUES (?, ?, ?)
                        """,
                        (venue_id, rest_id, dist)
                    )
                    mapped_count += 1
                saved_dining_count += 1
            except sqlite3.Error as se:
                # Skip errors
                pass
                
        conn.commit()
        print(f"  💾 Mapped {mapped_count} local dining spots near {venue_name}.")
        
    conn.close()
    print("\n🎉 Dining & Location Integration successfully completed!")

if __name__ == "__main__":
    enrich_venues_dining()
