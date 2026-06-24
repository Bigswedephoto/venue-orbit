const express = require('express');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const multer = require('multer');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 8000;

// Setup database path
const DB_PATH = path.join(__dirname, 'venue_orbit.db');
const STATIC_DIR = path.join(__dirname, 'src', 'static');
const IMAGES_DIR = path.join(STATIC_DIR, 'images');

// Ensure image uploads folder exists
if (!fs.existsSync(IMAGES_DIR)) {
  fs.mkdirSync(IMAGES_DIR, { recursive: true });
}

// Middleware
app.use(express.json());
app.use(express.static(STATIC_DIR));

// Setup multer storage for custom manual image uploads
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, IMAGES_DIR);
  },
  filename: function (req, file, cb) {
    const ext = path.extname(file.originalname) || '.jpg';
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, 'event_' + uniqueSuffix + ext);
  }
});
const upload = multer({ storage: storage });

// Database helper
function getDbConnection() {
  return new sqlite3.Database(DB_PATH);
}

// ==========================================================================
// API ENDPOINTS
// ==========================================================================

// 1. Get all events (Join query matching app.py)
app.get('/api/events', (req, res) => {
  const db = getDbConnection();
  const query = `
    SELECT e.id, e.title, e.date, e.time, e.ticket_url, e.description, e.image_url,
           v.id as venue_id, v.name as venue_name, v.category, v.lat as venue_lat, v.lng as venue_lng
    FROM events e
    JOIN venues v ON e.venue_id = v.id
    ORDER BY e.date ASC
  `;
  db.all(query, [], (err, rows) => {
    db.close();
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.json(rows);
  });
});

// 2. Get all venues (for dropdown lists in admin)
app.get('/api/venues', (req, res) => {
  const db = getDbConnection();
  db.all("SELECT id, name, category FROM venues ORDER BY name ASC", [], (err, rows) => {
    db.close();
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.json(rows);
  });
});

// 3. Get dining mapping for a specific venue (excludes Sweet Tea & restaurants without website links)
app.get('/api/dining', (req, res) => {
  const venueId = req.query.venue_id;
  if (!venueId) {
    return res.status(400).json({ error: 'Missing venue_id parameter' });
  }

  const db = getDbConnection();
  const query = `
    SELECT r.name, r.lat, r.lng, r.menu_url, r.address, m.distance_miles
    FROM venue_dining_map m
    JOIN restaurants r ON m.restaurant_id = r.id
    WHERE m.venue_id = ? AND r.name NOT LIKE '%Sweet Tea%' AND r.menu_url IS NOT NULL AND r.menu_url != ''
    ORDER BY m.distance_miles ASC
  `;
  db.all(query, [venueId], (err, rows) => {
    db.close();
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.json(rows);
  });
});

// ==========================================================================
// ADMIN CRUD ENDPOINTS
// ==========================================================================

// Add manual event
app.post('/api/admin/add', (req, res) => {
  const { venue_id, title, date, time, ticket_url, description, image_url } = req.body;
  if (!venue_id || !title) {
    return res.status(400).json({ error: 'Missing venue_id or title' });
  }

  const db = getDbConnection();
  const query = `
    INSERT INTO events (venue_id, title, date, time, ticket_url, description, image_url)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `;
  db.run(query, [venue_id, title, date || 'TBD', time, ticket_url, description, image_url], function(err) {
    db.close();
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.json({ success: true, id: this.lastID });
  });
});

// Edit event
app.post('/api/admin/edit', (req, res) => {
  const { id, venue_id, title, date, time, ticket_url, description, image_url } = req.body;
  if (!id || !venue_id || !title) {
    return res.status(400).json({ error: 'Missing event id, venue_id, or title' });
  }

  const db = getDbConnection();
  const query = `
    UPDATE events 
    SET venue_id = ?, title = ?, date = ?, time = ?, ticket_url = ?, description = ?, image_url = ?
    WHERE id = ?
  `;
  db.run(query, [venue_id, title, date || 'TBD', time, ticket_url, description, image_url, id], function(err) {
    db.close();
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.json({ success: true });
  });
});

// Delete event
app.post('/api/admin/delete', (req, res) => {
  const { id } = req.body;
  if (!id) {
    return res.status(400).json({ error: 'Missing event id' });
  }

  const db = getDbConnection();
  db.run("DELETE FROM events WHERE id = ?", [id], function(err) {
    db.close();
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.json({ success: true });
  });
});

// Upload image file
app.post('/api/admin/upload-image', upload.single('image'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No image file found in request' });
  }
  // Return the relative folder path to save in SQLite
  res.json({ success: true, image_url: 'images/' + req.file.filename });
});

// Catch-all to serve index.html for root path requests
app.get('*', (req, res) => {
  res.sendFile(path.join(STATIC_DIR, 'index.html'));
});

// Start Server
app.listen(PORT, () => {
  console.log(`📡 Node.js wrapper server running on port ${PORT}`);
  console.log(`📂 Static assets served from: ${STATIC_DIR}`);
  console.log(`🗄️ SQLite database loaded from: ${DB_PATH}`);
});
