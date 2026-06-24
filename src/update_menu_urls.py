import csv
import os

# Dictionary matching official websites (or closest working URLs)
OFFICIAL_WEBSITES = {
    "Bellini's Ristorante & Bar": "https://ourbellinis.com/",
    "Billy's Sports Grill - Overton": "https://billyssportsgrill.com/",
    "Birmingham Breadworks": "https://birminghambreadworks.com/",
    "Bistro Two Eighteen": "https://bistro218.com/",
    "Bistro V": "https://bistro-v.com/",
    "Blueprint on 3rd": "https://blueprinton3rd.com/",
    "Bocca Ristorante": "https://boccabirmingham.com/",
    "Bottega Cafe": "https://bottegarestaurant.com/",
    "Bottega Restaurant": "https://bottegarestaurant.com/",
    "Cafe Dupont": "https://cafedupont.net/",
    "Chez Fonfon": "https://fonfonbham.com/",
    "Dreamland Bar-B-Que": "https://dreamlandbbq.com/",
    "Dyron's Lowcountry": "http://dyronslowcountry.com/",
    "Eli's Jerusalem Grill": "https://elisjerusalemgrill.com/",
    "FoodBar": "https://foodbarbham.com/",
    "Galley & Garden": "https://galleyandgarden.com/",
    "Highlands Bar and Grill": "https://highlandsbarandgrill.com/",
    "Piggly Wiggly Delis": "https://pigbham.com/",
    "Sloan's": "https://sloansbham.com/",
    "Taco Mama": "https://tacomamaonline.com/",
    "Ted's Restaurant": "https://tedsbirmingham.com/",
    "The Gardens Cafe, by Kathy G.": "https://kathyg.com/",
    "The Red Cat": "https://theredcatcoffeehouse.com/",
    "Troup's Pizza": "https://troupspizza.com/",
    "Vino & Gallery Bar": "https://vinobirmingham.com/"
}

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
            
    print(f"🔄 Updating menu_url column with official websites...")
    
    updated_count = 0
    for row in records:
        name = row['restaurant_name']
        if name in OFFICIAL_WEBSITES:
            row['menu_url'] = OFFICIAL_WEBSITES[name]
            updated_count += 1
            
    # Write updated records back to CSV
    headers = ['restaurant_name', 'lat', 'lng', 'menu_url', 'address', 'venue_name', 'distance_miles']
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in records:
            writer.writerow(row)
            
    print(f"✅ Successfully updated {updated_count} restaurant menu URLs to their official websites!")

if __name__ == "__main__":
    main()
