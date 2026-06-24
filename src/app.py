#!/usr/bin/env python3
import http.server
import socketserver
import urllib.parse
import json
import os
import sqlite3
import re

PORT = 8000
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "venue_orbit.db")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

class VenueOrbitHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Override to serve static assets from the src/static directory
        parsed = urllib.parse.urlparse(path)
        rel_path = parsed.path.lstrip('/')
        
        # Default index
        if not rel_path:
            rel_path = "index.html"
            
        return os.path.join(STATIC_DIR, rel_path)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. API Endpoint: Get all events
        if path == "/api/events":
            self.handle_api_events()
            
        # 2. API Endpoint: Get all venues (for dropdown lists in admin)
        elif path == "/api/venues":
            self.handle_api_venues()
            
        # 3. API Endpoint: Get dining mapping for a specific venue
        elif path == "/api/dining":
            venue_id = query.get("venue_id", [None])[0]
            self.handle_api_dining(venue_id)
            
        # Default: Serve static files
        else:
            super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Read post payload body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        if path == "/api/admin/upload-image":
            self.handle_admin_image_upload(post_data)
            return

        try:
            data = json.loads(post_data.decode('utf-8'))
        except Exception:
            self.send_error_response("Invalid JSON payload", 400)
            return

        # Handle Admin CRUD actions
        if path == "/api/admin/add":
            self.handle_admin_add(data)
        elif path == "/api/admin/edit":
            self.handle_admin_edit(data)
        elif path == "/api/admin/delete":
            self.handle_admin_delete(data)
        elif path == "/api/admin/upload-image":
            self.handle_admin_image_upload(post_data)
        elif path == "/api/admin/bulk-venues":
            self.handle_admin_bulk_venues(data)
        elif path == "/api/admin/bulk-events":
            self.handle_admin_bulk_events(data)
        elif path == "/api/admin/bulk-dining":
            self.handle_admin_bulk_dining(data)
        else:
            self.send_error_response("Not Found", 404)

    def handle_api_events(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.id, e.title, e.date, e.time, e.ticket_url, e.description, e.image_url,
                       v.id as venue_id, v.name as venue_name, v.category, v.lat as venue_lat, v.lng as venue_lng
                FROM events e
                JOIN venues v ON e.venue_id = v.id
                ORDER BY e.date ASC
            """)
            rows = cursor.fetchall()
            
            events = []
            for r in rows:
                events.append({
                    "id": r["id"],
                    "title": r["title"],
                    "date": r["date"],
                    "time": r["time"],
                    "ticket_url": r["ticket_url"],
                    "description": r["description"],
                    "image_url": r.keys() and "image_url" in r.keys() and r["image_url"] or None,
                    "venue_id": r["venue_id"],
                    "venue_name": r["venue_name"],
                    "category": r["category"],
                    "venue_lat": r["venue_lat"],
                    "venue_lng": r["venue_lng"]
                })
            
            conn.close()
            self.send_json_response(events)
            
        except Exception as e:
            self.send_error_response(str(e))

    def handle_api_venues(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, category FROM venues ORDER BY name ASC")
            rows = cursor.fetchall()
            
            venues = []
            for r in rows:
                venues.append({
                    "id": r["id"],
                    "name": r["name"],
                    "category": r["category"]
                })
                
            conn.close()
            self.send_json_response(venues)
        except Exception as e:
            self.send_error_response(str(e))

    def handle_api_dining(self, venue_id):
        if not venue_id:
            self.send_error_response("Missing venue_id parameter", 400)
            return
            
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r.name, r.lat, r.lng, r.menu_url, r.address, m.distance_miles
                FROM venue_dining_map m
                JOIN restaurants r ON m.restaurant_id = r.id
                WHERE m.venue_id = ? AND r.name NOT LIKE '%Sweet Tea%' AND r.menu_url IS NOT NULL AND r.menu_url != ''
                ORDER BY m.distance_miles ASC
            """, (venue_id,))
            rows = cursor.fetchall()
            
            dining = []
            for r in rows:
                dining.append({
                    "name": r["name"],
                    "lat": r["lat"],
                    "lng": r["lng"],
                    "menu_url": r["menu_url"],
                    "address": r["address"],
                    "distance_miles": r["distance_miles"]
                })
                
            conn.close()
            self.send_json_response(dining)
            
        except Exception as e:
            self.send_error_response(str(e))

    def handle_admin_add(self, data):
        venue_id = data.get("venue_id")
        title = data.get("title")
        date = data.get("date", "TBD")
        time_val = data.get("time")
        ticket_url = data.get("ticket_url")
        description = data.get("description")
        image_url = data.get("image_url")
        
        if not venue_id or not title:
            self.send_error_response("Missing venue_id or title", 400)
            return
            
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (venue_id, title, date, time, ticket_url, description, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (venue_id, title, date, time_val, ticket_url, description, image_url))
            conn.commit()
            conn.close()
            self.send_json_response({"success": True})
        except Exception as e:
            self.send_error_response(str(e))

    def handle_admin_edit(self, data):
        event_id = data.get("id")
        venue_id = data.get("venue_id")
        title = data.get("title")
        date = data.get("date", "TBD")
        time_val = data.get("time")
        ticket_url = data.get("ticket_url")
        description = data.get("description")
        image_url = data.get("image_url")
        
        if not event_id or not venue_id or not title:
            self.send_error_response("Missing event id, venue_id, or title", 400)
            return
            
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE events 
                SET venue_id = ?, title = ?, date = ?, time = ?, ticket_url = ?, description = ?, image_url = ?
                WHERE id = ?
            """, (venue_id, title, date, time_val, ticket_url, description, image_url, event_id))
            conn.commit()
            conn.close()
            self.send_json_response({"success": True})
        except Exception as e:
            self.send_error_response(str(e))

    def handle_admin_delete(self, data):
        event_id = data.get("id")
        if not event_id:
            self.send_error_response("Missing event id", 400)
            return
            
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            conn.close()
            self.send_json_response({"success": True})
        except Exception as e:
            self.send_error_response(str(e))

    def handle_admin_image_upload(self, raw_data):
        try:
            # Parse multipart/form-data payload manually to remain dependency-free
            content_type = self.headers.get('Content-Type', '')
            if 'boundary=' not in content_type:
                self.send_error_response("Invalid boundary in Content-Type", 400)
                return
            
            boundary = content_type.split('boundary=')[1].strip().encode('utf-8')
            parts = raw_data.split(b'--' + boundary)
            
            file_data = None
            filename = "uploaded_image.jpg"
            
            for part in parts:
                if b'Content-Disposition:' in part and b'filename=' in part:
                    # Extract headers and body separation
                    headers_part, body_part = part.split(b'\r\n\r\n', 1)
                    # Discard trailing \r\n
                    if body_part.endswith(b'\r\n'):
                        body_part = body_part[:-2]
                    
                    # Resolve filename
                    fn_match = re.search(r'filename="([^"]+)"', headers_part.decode('utf-8', errors='ignore'))
                    if fn_match:
                        filename = fn_match.group(1)
                    
                    file_data = body_part
                    break
            
            if file_data is None:
                self.send_error_response("No image file found in request", 400)
                return
            
            # Determine extension
            ext = ".jpg"
            if filename.lower().endswith(".png"):
                ext = ".png"
            elif filename.lower().endswith(".jpeg"):
                ext = ".jpeg"
            elif filename.lower().endswith(".webp"):
                ext = ".webp"
                
            import uuid
            new_filename = f"event_{uuid.uuid4().hex}{ext}"
            images_dir = os.path.join(STATIC_DIR, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            filepath = os.path.join(images_dir, new_filename)
            with open(filepath, "wb") as f:
                f.write(file_data)
                
            self.send_json_response({"success": True, "image_url": f"images/{new_filename}"})
            
        except Exception as e:
            self.send_error_response(str(e))

    def handle_admin_bulk_venues(self, data):
        records = data.get("records", [])
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            count = 0
            for r in records:
                name = r.get("name")
                category = r.get("category")
                if name and category:
                    lat = float(r.get("lat") or 0.0)
                    lng = float(r.get("lng") or 0.0)
                    cursor.execute(
                        "INSERT INTO venues (name, category, lat, lng) VALUES (?, ?, ?, ?)",
                        (name, category, lat, lng)
                    )
                    count += 1
            conn.commit()
            conn.close()
            self.send_json_response({"success": True, "count": count})
        except Exception as e:
            self.send_error_response(str(e))

    def handle_admin_bulk_events(self, data):
        records = data.get("records", [])
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Map names to IDs
            cursor.execute("SELECT id, name FROM venues")
            venues = {row["name"].lower().strip(): row["id"] for row in cursor.fetchall()}
            
            count = 0
            for r in records:
                title = r.get("title")
                v_name = r.get("venue_name")
                if not title or not v_name:
                    continue
                v_key = v_name.lower().strip()
                if v_key in venues:
                    venue_id = venues[v_key]
                    date = r.get("date") or "TBD"
                    time_val = r.get("time")
                    ticket_url = r.get("ticket_url")
                    description = r.get("description")
                    image_url = r.get("image_url")
                    
                    cursor.execute(
                        "INSERT INTO events (venue_id, title, date, time, ticket_url, description, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (venue_id, title, date, time_val, ticket_url, description, image_url)
                    )
                    count += 1
            conn.commit()
            conn.close()
            self.send_json_response({"success": True, "count": count})
        except Exception as e:
            self.send_error_response(str(e))

    def handle_admin_bulk_dining(self, data):
        records = data.get("records", [])
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Map names to IDs
            cursor.execute("SELECT id, name FROM venues")
            venues = {row["name"].lower().strip(): row["id"] for row in cursor.fetchall()}
            
            count = 0
            for r in records:
                rest_name = r.get("restaurant_name")
                v_name = r.get("venue_name")
                
                # If venue name or distance is empty, we can just insert the restaurant profile if it doesn't exist
                if not rest_name:
                    continue
                    
                # 1. Insert or find restaurant
                cursor.execute("SELECT id FROM restaurants WHERE name = ? LIMIT 1", (rest_name,))
                row = cursor.fetchone()
                if row:
                    rest_id = row["id"]
                else:
                    lat = float(r.get("lat") or 0.0)
                    lng = float(r.get("lng") or 0.0)
                    menu_url = r.get("menu_url") or ""
                    address = r.get("address") or ""
                    cursor.execute(
                        "INSERT INTO restaurants (name, lat, lng, menu_url, address) VALUES (?, ?, ?, ?, ?)",
                        (rest_name, lat, lng, menu_url, address)
                    )
                    rest_id = cursor.lastrowid
                
                # 2. Map venue dining link if venue is specified
                if v_name and r.get("distance_miles"):
                    v_key = v_name.lower().strip()
                    if v_key in venues:
                        venue_id = venues[v_key]
                        dist = float(r.get("distance_miles"))
                        cursor.execute(
                            "INSERT OR IGNORE INTO venue_dining_map (venue_id, restaurant_id, distance_miles) VALUES (?, ?, ?)",
                            (venue_id, rest_id, dist)
                        )
                count += 1
                
            conn.commit()
            conn.close()
            self.send_json_response({"success": True, "count": count})
        except Exception as e:
            self.send_error_response(str(e))

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        # Enable CORS for development ease
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def send_error_response(self, message, status=500):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode("utf-8"))

def main():
    # Make sure static directory exists
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    # Run server
    handler = VenueOrbitHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"📡 Venue Orbit server running on http://localhost:{PORT}")
        print(f"📂 Serving static assets from: {STATIC_DIR}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server shutting down.")

if __name__ == "__main__":
    main()
