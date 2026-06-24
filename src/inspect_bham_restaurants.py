import httpx
from lxml import html
import re

url = "https://www.birminghamrestaurants.com/Restaurants/Profile/Bistro-V"
resp = httpx.get(url)
tree = html.fromstring(resp.content)

# We notice that if we simulate postback or click on buttons, the server redirects us to /Listings/Restaurants/All/
# Let's inspect what happens if we look at other profile links. E.g., Bottega Cafe or Vino.
# Let's see if we can find if there are social media links (Instagram, Facebook) or OpenTable links.
# E.g., Bistro V has: `https://www.opentable.com/bistro-v-vestavia-hills` and Facebook/Instagram links.
# Are they directly in the HTML or do they redirect too?
# Bistro V:
# - Instagram: https://www.instagram.com/bistro_v/
# - OpenTable: https://www.opentable.com/bistro-v-vestavia-hills
# Let's write a script that loads ALL 25 restaurant profile pages, extracts:
# 1. Restaurant Name
# 2. Address (from the <address> element)
# 3. Phone (from the strong: Phone block)
# 4. Social Links (Facebook, Instagram, OpenTable, etc.) if any.
# Let's run this for all 25 restaurants and print the results!

url_list = [
    "/Restaurants/Profile/Bellinis-Ristorante-Bar",
    "/Restaurants/Profile/Billys-Sports-Grill-Overton",
    "/Restaurants/Profile/Birmingham-Breadworks",
    "/Restaurants/Profile/Bistro-Two-Eighteen",
    "/Restaurants/Profile/Bistro-V",
    "/Restaurants/Profile/Blueprint-on-3rd",
    "/Restaurants/Profile/Bocca-Ristorante",
    "/Restaurants/Profile/Bottega-Cafe",
    "/Restaurants/Profile/Bottega-Restaurant",
    "/Restaurants/Profile/Cafe-Dupont",
    "/Restaurants/Profile/Chez-Fonfon",
    "/Restaurants/Profile/Dreamland-Bar-B-Que",
    "/Restaurants/Profile/Dyrons-Lowcountry",
    "/Restaurants/Profile/Elis-Jerusalem-Grill",
    "/Restaurants/Profile/FoodBar",
    "/Restaurants/Profile/Galley-and-Garden",
    "/Restaurants/Profile/Highlands-Bar-and-Grill",
    "/Restaurants/Profile/Piggly-Wiggly-Delis",
    "/Restaurants/Profile/Sloans",
    "/Restaurants/Profile/Taco-Mama",
    "/Restaurants/Profile/Teds-Restaurant",
    "/Restaurants/Profile/The-Gardens-Cafe",
    "/Restaurants/Profile/The-Red-Cat",
    "/Restaurants/Profile/Troups-Pizza",
    "/Restaurants/Profile/Vino--Gallery-Bar"
]

for relative_path in url_list:
    full_url = f"https://www.birminghamrestaurants.com{relative_path}"
    try:
        r = httpx.get(full_url, timeout=10.0)
        t = html.fromstring(r.content)
        
        # Name
        h1_text = ""
        h1s = t.xpath('//h1')
        for h1 in h1s:
            # Let's find the h1 that has non-empty text and is part of main content
            txt = h1.text_content().strip()
            if txt and txt != "Birmingham Restaurants":
                h1_text = txt
                break
        
        # Address
        address_text = ""
        addrs = t.xpath('//address')
        if addrs:
            address_text = " ".join([txt.strip() for txt in addrs[0].itertext() if txt.strip()])
            address_text = " ".join(address_text.split()) # normalise spaces
            
        # Phone
        phone_text = ""
        phone_match = re.search(r'Phone:[\s\S]*?(\d[\d\.\-\s]+)', t.text_content())
        if phone_match:
            phone_text = phone_match.group(1).strip()
            
        # Reserv/OpenTable
        opentable_url = ""
        ot_links = t.xpath('//a[contains(@href, "opentable.com")]/@href')
        if ot_links:
            opentable_url = ot_links[0]
            
        # Facebook/Instagram
        fb_url = ""
        fb_links = t.xpath('//a[contains(@href, "facebook.com")]/@href')
        if fb_links:
            fb_url = fb_links[0]
            
        insta_url = ""
        insta_links = t.xpath('//a[contains(@href, "instagram.com")]/@href')
        if insta_links:
            insta_url = insta_links[0]
            
        print(f"Name: {h1_text}")
        print(f"  Addr: {address_text}")
        print(f"  Phone: {phone_text}")
        print(f"  OpenTable: {opentable_url}")
        print(f"  FB: {fb_url}")
        print(f"  Insta: {insta_url}")
        print("-" * 30)
    except Exception as e:
        print(f"Error scraping {relative_path}: {e}")
