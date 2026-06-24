import json
import os
import sys
import re
import urllib.request
import uuid
from datetime import datetime
from scrapling import Fetcher
from database import get_db_connection

# Load configurations
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
STATIC_IMAGES_DIR = os.path.join(PROJECT_ROOT, "src", "static", "images")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def download_image_locally(url: str) -> str:
    """Download image from url and save it inside static/images directory, returning the relative path."""
    if not url:
        return ""
    try:
        os.makedirs(STATIC_IMAGES_DIR, exist_ok=True)
        # Determine file extension
        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        elif ".jpeg" in url.lower():
            ext = ".jpeg"
        elif ".webp" in url.lower():
            ext = ".webp"
        
        filename = f"event_{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(STATIC_IMAGES_DIR, filename)
        
        # Download image with a user-agent to bypass basic scrape protection
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
        )
        # Bypassing SSL certificate verification issues locally
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response, open(filepath, 'wb') as out_file:
            out_file.write(response.read())
            
        return f"images/{filename}"
    except Exception as e:
        print(f"⚠️ Warning: Failed to download image {url} locally: {e}")
        return url  # Fallback to absolute url if download fails

def normalize_date(date_raw: str) -> str:
    """Standardizes date strings to YYYY-MM-DD format."""
    if not date_raw or not str(date_raw).strip():
        return "TBD"
        
    date_clean = str(date_raw).strip()
    
    # 1. Check if it matches ISO format (e.g. 2026-06-19T19:00:00+00:00)
    iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_clean)
    if iso_match:
        return iso_match.group(0)
        
    # Remove day name prefixes like "Friday, Jun 19" or "Fri, Jun 19" or "Thursday, "
    date_clean = re.sub(
        r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+",
        "",
        date_clean,
        flags=re.IGNORECASE
    )
    
    # Try to find year if explicitly present
    year = None
    year_match = re.search(r"\b(20\d{2})\b", date_clean)
    if year_match:
        year = int(year_match.group(1))
        # Remove the year from the string to avoid interference
        date_clean = date_clean.replace(year_match.group(0), "").strip()
        # Remove commas left over
        date_clean = date_clean.replace(",", "").strip()

    # 2. Check for numeric month/day formats like "6 / 19" or "06/19"
    slash_match = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", date_clean)
    if slash_match:
        month_num = int(slash_match.group(1))
        day_val = int(slash_match.group(2))
        if year is None:
            now = datetime.now()
            year = now.year
            if month_num < now.month:
                year += 1
        return f"{year:04d}-{month_num:02d}-{day_val:02d}"

    # 3. Try parsing short format (e.g. "Jun 19" or "June 19")
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    match = re.search(r"([a-zA-Z]{3,9})\s+(\d{1,2})", date_clean, re.IGNORECASE)
    if not match:
        match = re.search(r"(\d{1,2})\s+([a-zA-Z]{3,9})", date_clean, re.IGNORECASE)
        if match:
            day_str, month_str = match.group(1), match.group(2)
        else:
            day_str, month_str = None, None
    else:
        month_str, day_str = match.group(1), match.group(2)
        
    if month_str and day_str:
        month_num = months.get(month_str.lower())
        if month_num:
            if year is None:
                now = datetime.now()
                year = now.year
                if month_num < now.month:
                    year += 1
            return f"{year:04d}-{month_num:02d}-{int(day_str):02d}"
            
    return "TBD"

class EventScraper:
    def __init__(self, venue_config):
        self.config = venue_config
        self.name = venue_config.get("name")
        self.url = venue_config.get("schedule_url")
        self.parser_type = venue_config.get("parser_type")
        self.selectors = venue_config.get("selectors", {})

    def scrape(self):
        print(f"🕷️ Scraper starting for: {self.name} ({self.url})...")
        try:
            # Fetch content using Scrapling's built-in stealth fetcher
            response = Fetcher.get(self.url)
            if response.status != 200:
                print(f"❌ Error: Received status {response.status} from {self.url}")
                return []

            if self.parser_type == "json_ld":
                events = self._parse_json_ld(response)
            else:
                events = self._parse_standard_html(response)

            for ev in events:
                ev["date"] = normalize_date(ev.get("date"))

            return events

        except Exception as e:
            print(f"❌ Scraping exception for {self.name}: {e}")
            return []

    def _parse_standard_html(self, response):
        events = []
        container_sel = self.selectors.get("event_container")
        title_sel = self.selectors.get("title")
        date_sel = self.selectors.get("date")
        time_sel = self.selectors.get("time")

        # Find event element wrappers
        containers = response.css(container_sel)
        print(f"🔍 Found {len(containers)} raw containers on page.")

        for container in containers:
            try:
                # Scrapling css matches allow contextual selections
                title_el = [container] if title_sel == "self" else container.css(title_sel)
                date_el = [container] if date_sel == "self" else container.css(date_sel)
                time_el = None
                if time_sel:
                    time_el = [container] if time_sel == "self" else container.css(time_sel)
                
                title = ""
                if title_el:
                    if title_el[0].tag == "img" and "alt" in title_el[0].attrib:
                        title = title_el[0].attrib["alt"].strip()
                    elif title_el[0].css("img"):
                        img_el = title_el[0].css("img")[0]
                        if "alt" in img_el.attrib:
                            title = img_el.attrib["alt"].strip()
                            
                    if not title:
                        title = title_el[0].get_all_text().strip()
                else:
                    title = "Unknown Event"
                
                if date_el:
                    if date_el[0].tag == "time" and "datetime" in date_el[0].attrib:
                        date_val = date_el[0].attrib["datetime"]
                    elif date_el[0].tag == "img" and "alt" in date_el[0].attrib:
                        date_val = date_el[0].attrib["alt"].strip()
                    elif date_el[0].css("img"):
                        img_el = date_el[0].css("img")[0]
                        if "alt" in img_el.attrib:
                            date_val = img_el.attrib["alt"].strip()
                        else:
                            date_val = date_el[0].get_all_text().strip()
                    else:
                        date_val = date_el[0].get_all_text().strip()
                else:
                    date_val = "TBD"
                    
                if time_el:
                    if time_el[0].tag == "time" and "datetime" in time_el[0].attrib:
                        time_val = time_el[0].attrib["datetime"]
                        if "T" in time_val:
                            time_val = time_val.split("T")[1]
                    elif time_el[0].tag == "img" and "alt" in time_el[0].attrib:
                        time_val = time_el[0].attrib["alt"].strip()
                    elif time_el[0].css("img"):
                        img_el = time_el[0].css("img")[0]
                        if "alt" in img_el.attrib:
                            time_val = img_el.attrib["alt"].strip()
                        else:
                            time_val = time_el[0].get_all_text().strip()
                    else:
                        time_val = time_el[0].get_all_text().strip()
                else:
                    time_val = "TBD"
                
                # Check for links inside container
                tix_sel = self.selectors.get("ticket_url")
                ticket_url = ""
                if tix_sel:
                    if tix_sel == "self" or container.tag == "a":
                        ticket_url = container.attrib.get("href", "")
                    else:
                        tix_el = container.css(tix_sel)
                        if not tix_el:
                            continue # Skip container since the required ticket link is missing
                        ticket_url = tix_el[0].attrib.get("href", "")
                else:
                    link_el = container.css("a")
                    ticket_url = link_el[0].attrib.get("href", "") if link_el else ""
                
                if ticket_url and ticket_url.startswith("/"):
                    from urllib.parse import urljoin
                    ticket_url = urljoin(self.url, ticket_url)
                
                # Scrape Image URL if selector exists
                image_url = ""
                img_sel = self.selectors.get("image")
                if img_sel:
                    img_el = container.css(img_sel)
                    if img_el:
                        # 1. If element is img tag, extract src
                        if img_el[0].tag == "img" and "src" in img_el[0].attrib:
                            image_url = img_el[0].attrib["src"]
                        # 2. Support data-src attributes for lazy loading
                        elif "data-src" in img_el[0].attrib:
                            image_url = img_el[0].attrib["data-src"]
                        # 3. Fallback to style background-image if style is present
                        elif "style" in img_el[0].attrib:
                            style_str = img_el[0].attrib["style"]
                            bg_match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_str)
                            if bg_match:
                                image_url = bg_match.group(1)

                if image_url and image_url.startswith("/"):
                    from urllib.parse import urljoin
                    image_url = urljoin(self.url, image_url)
                
                events.append({
                    "title": title,
                    "date": date_val,
                    "time": time_val,
                    "ticket_url": ticket_url,
                    "image_url": image_url
                })
            except Exception as inner_e:
                print(f"⚠️ Warning: Skipped container due to parsing error: {inner_e}")
                
        return events

    def _parse_json_ld(self, response):
        events = []
        script_sel = self.selectors.get("event_container", "script[type='application/ld+json']")
        scripts = response.css(script_sel)
        
        for script in scripts:
            try:
                # Load script content
                data = json.loads(script.text.strip())
                
                # JSON-LD can be a single dict or a list
                if isinstance(data, dict):
                    entries = data.get("@graph", [data]) if "@graph" in data else [data]
                elif isinstance(data, list):
                    entries = data
                else:
                    continue
 
                for item in entries:
                    if item.get("@type") == "Event" or "startDate" in item:
                        title = item.get("name", "Unknown Event")
                        date_val = item.get("startDate", "TBD")
                        # Format ticket offers
                        offers = item.get("offers", {})
                        ticket_url = ""
                        if isinstance(offers, dict):
                            ticket_url = offers.get("url", "")
                        elif isinstance(offers, list) and len(offers) > 0:
                            ticket_url = offers[0].get("url", "")
                            
                        # Image URL from JSON-LD
                        image_val = item.get("image", "")
                        image_url = ""
                        if isinstance(image_val, str):
                            image_url = image_val
                        elif isinstance(image_val, list) and len(image_val) > 0:
                            if isinstance(image_val[0], str):
                                image_url = image_val[0]
                            elif isinstance(image_val[0], dict):
                                image_url = image_val[0].get("url", "")
                        elif isinstance(image_val, dict):
                            image_url = image_val.get("url", "")

                        if image_url and image_url.startswith("/"):
                            from urllib.parse import urljoin
                            image_url = urljoin(self.url, image_url)

                        events.append({
                            "title": title,
                            "date": date_val,
                            "time": date_val.split("T")[1] if "T" in date_val else "TBD",
                            "ticket_url": ticket_url,
                            "image_url": image_url
                        })
            except Exception as e:
                print(f"⚠️ Warning: Failed to parse JSON-LD script block: {e}")
 
        return events
 
def save_events_to_db(venue_name, venue_category, events):
    """Upsert venue, download images locally, and save crawled events to database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure Venue exists
    cursor.execute(
        "INSERT OR IGNORE INTO venues (name, category) VALUES (?, ?)", 
        (venue_name, venue_category)
    )
    cursor.execute("SELECT id FROM venues WHERE name = ?", (venue_name,))
    venue_id = cursor.fetchone()["id"]
    
    # Clear existing events for this venue to prevent duplicates
    cursor.execute("DELETE FROM events WHERE venue_id = ?", (venue_id,))
    
    # Save events
    saved_count = 0
    for ev in events:
        raw_img_url = ev.get("image_url", "")
        local_img_path = ""
        if raw_img_url:
            print(f"📥 Downloading image for event '{ev['title']}'...")
            local_img_path = download_image_locally(raw_img_url)
            
        cursor.execute(
            """
            INSERT INTO events (venue_id, title, date, time, ticket_url, image_url) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (venue_id, ev["title"], ev["date"], ev["time"], ev["ticket_url"], local_img_path)
        )
        saved_count += 1
        
    conn.commit()
    conn.close()
    print(f"💾 Saved {saved_count} events to database for {venue_name}.")

def main():
    config = load_config()
    print(f"🗺️ Loaded config for {config.get('city_name')}...")
    
    for venue_cfg in config.get("venues", []):
        scraper = EventScraper(venue_cfg)
        events = scraper.scrape()
        if events:
            save_events_to_db(venue_cfg["name"], venue_cfg["category"], events)
        else:
            print(f"⚠️ No events found for {venue_cfg['name']}")

if __name__ == "__main__":
    main()
