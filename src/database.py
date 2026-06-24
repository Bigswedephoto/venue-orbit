import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venue_orbit.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create the SQLite tables if they do not exist."""
    print("🗄️ Initializing SQLite Database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Venues Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        lat REAL,
        lng REAL
    )
    """)
    
    # 2. Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venue_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT,
        ticket_url TEXT,
        description TEXT,
        image_url TEXT,
        FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE CASCADE
    )
    """)
    
    # 3. Restaurants Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        lat REAL,
        lng REAL,
        menu_url TEXT,
        reservation_url TEXT,
        address TEXT
    )
    """)
    
    # 4. Event Dining Map Table (hyper-local bounds mapping)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venue_dining_map (
        venue_id INTEGER NOT NULL,
        restaurant_id INTEGER NOT NULL,
        distance_miles REAL,
        PRIMARY KEY (venue_id, restaurant_id),
        FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE CASCADE,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database tables created successfully.")

if __name__ == "__main__":
    init_db()
