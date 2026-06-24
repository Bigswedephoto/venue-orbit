import csv
from collections import defaultdict
import os

def main():
    csv_file = "bham_restaurants_import.csv"
    if not os.path.exists(csv_file):
        print(f"❌ File {csv_file} does not exist!")
        return
        
    records = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
            
    # Check for duplicate restaurant names (case-insensitive)
    name_counts = defaultdict(list)
    for idx, row in enumerate(records):
        name = row['restaurant_name'].strip()
        # Normalise case and spaces
        norm_name = " ".join(name.lower().split())
        name_counts[norm_name].append((idx + 2, name)) # idx + 2 is the CSV row number (1-based + header)
        
    duplicates = {k: v for k, v in name_counts.items() if len(v) > 1}
    
    if not duplicates:
        print("✅ No duplicate restaurant names found in bham_restaurants_import.csv!")
        return
        
    print(f"⚠️ Found {len(duplicates)} duplicate entries in the CSV:")
    for norm_name, occurrences in duplicates.items():
        print(f"\nRestaurant: '{occurrences[0][1]}'")
        for row_num, name in occurrences:
            print(f"  - Row {row_num}: '{name}'")
            
    # Let's clean them up by keeping only the first occurrence
    seen = set()
    cleaned_records = []
    removed_count = 0
    for row in records:
        norm_name = " ".join(row['restaurant_name'].lower().split())
        if norm_name in seen:
            print(f"  Removing duplicate: '{row['restaurant_name']}'")
            removed_count += 1
            continue
        seen.add(norm_name)
        cleaned_records.append(row)
        
    # Write back clean records
    headers = ['restaurant_name', 'lat', 'lng', 'menu_url', 'address', 'venue_name', 'distance_miles']
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in cleaned_records:
            writer.writerow(row)
            
    print(f"\n✅ Cleaned CSV! Removed {removed_count} duplicates. Current unique record count: {len(cleaned_records)}")

if __name__ == "__main__":
    main()
