<?php
// Simple single-file router for Venue Orbit
$request_uri = explode('?', $_SERVER['REQUEST_URI'], 2)[0];

// Serve static assets manually if they exist, else route APIs
$static_path = __DIR__ . '/src/static' . $request_uri;
if (file_exists($static_path) && !is_dir($static_path)) {
    // Determine Content-Type
    $ext = pathinfo($static_path, PATHINFO_EXTENSION);
    $mimes = [
        'css'  => 'text/css',
        'js'   => 'application/javascript',
        'png'  => 'image/png',
        'jpg'  => 'image/jpeg',
        'jpeg' => 'image/jpeg',
        'gif'  => 'image/gif',
        'ico'  => 'image/x-icon',
        'svg'  => 'image/svg+xml'
    ];
    if (isset($mimes[$ext])) {
        header("Content-Type: " . $mimes[$ext]);
    }
    readfile($static_path);
    exit;
}

// Database helper connection
function get_db() {
    // 1. Try persistent path outside deployment folder (e.g. at user domains/venue-orbit.com/ level)
    $db_path = dirname(__DIR__) . '/venue_orbit.db';
    
    // 2. Fallback to standard paths
    if (!file_exists($db_path)) {
        $db_path = __DIR__ . '/venue_orbit.db';
    }
    if (!file_exists($db_path) && file_exists(__DIR__ . '/10_Venue_Orbit/venue_orbit.db')) {
        $db_path = __DIR__ . '/10_Venue_Orbit/venue_orbit.db';
    }
    if (!file_exists($db_path) && file_exists(__DIR__ . '/10_Venue_Orbit/10_Venue_Orbit/venue_orbit.db')) {
        $db_path = __DIR__ . '/10_Venue_Orbit/10_Venue_Orbit/venue_orbit.db';
    }
    try {
        $db = new PDO("sqlite:" . $db_path);
        $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        return $db;
    } catch (PDOException $e) {
        header('HTTP/1.1 500 Internal Server Error');
        echo json_encode(['error' => $e->getMessage()]);
        exit;
    }
}

// Route API Calls
if ($request_uri === '/api/events') {
    header('Content-Type: application/json');
    $db = get_db();
    $stmt = $db->query("
        SELECT e.id, e.title, e.date, e.time, e.ticket_url, e.description, e.image_url,
               v.id as venue_id, v.name as venue_name, v.category, v.lat as venue_lat, v.lng as venue_lng
        FROM events e
        JOIN venues v ON e.venue_id = v.id
        ORDER BY e.date ASC
    ");
    echo json_encode($stmt->fetchAll());
    exit;
}

if ($request_uri === '/api/venues') {
    header('Content-Type: application/json');
    $db = get_db();
    $stmt = $db->query("SELECT id, name, category FROM venues ORDER BY name ASC");
    echo json_encode($stmt->fetchAll());
    exit;
}

if ($request_uri === '/api/dining') {
    header('Content-Type: application/json');
    $venue_id = $_GET['venue_id'] ?? null;
    if (!$venue_id) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing venue_id parameter']);
        exit;
    }
    $db = get_db();
    $stmt = $db->prepare("
        SELECT r.name, r.lat, r.lng, r.menu_url, r.address, m.distance_miles
        FROM venue_dining_map m
        JOIN restaurants r ON m.restaurant_id = r.id
        WHERE m.venue_id = ? AND r.name NOT LIKE '%Sweet Tea%' AND r.menu_url IS NOT NULL AND r.menu_url != ''
        ORDER BY m.distance_miles ASC
    ");
    $stmt->execute([$venue_id]);
    echo json_encode($stmt->fetchAll());
    exit;
}

// Admin API Operations
if ($request_uri === '/api/admin/add') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['venue_id']) || !isset($data['title'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing venue_id or title']);
        exit;
    }
    $db = get_db();
    $stmt = $db->prepare("
        INSERT INTO events (venue_id, title, date, time, ticket_url, description, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->execute([
        $data['venue_id'],
        $data['title'],
        $data['date'] ?: 'TBD',
        $data['time'] ?? null,
        $data['ticket_url'] ?? null,
        $data['description'] ?? null,
        $data['image_url'] ?? null
    ]);
    echo json_encode(['success' => true, 'id' => $db->lastInsertId()]);
    exit;
}

if ($request_uri === '/api/admin/edit') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['id']) || !isset($data['venue_id']) || !isset($data['title'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing event id, venue_id, or title']);
        exit;
    }
    $db = get_db();
    $stmt = $db->prepare("
        UPDATE events 
        SET venue_id = ?, title = ?, date = ?, time = ?, ticket_url = ?, description = ?, image_url = ?
        WHERE id = ?
    ");
    $stmt->execute([
        $data['venue_id'],
        $data['title'],
        $data['date'] ?: 'TBD',
        $data['time'] ?? null,
        $data['ticket_url'] ?? null,
        $data['description'] ?? null,
        $data['image_url'] ?? null,
        $data['id']
    ]);
    echo json_encode(['success' => true]);
    exit;
}

if ($request_uri === '/api/admin/delete') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['id'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing event id']);
        exit;
    }
    $db = get_db();
    $stmt = $db->prepare("DELETE FROM events WHERE id = ?");
    $stmt->execute([$data['id']]);
    echo json_encode(['success' => true]);
    exit;
}

if ($request_uri === '/api/admin/upload-image') {
    header('Content-Type: application/json');
    if (!isset($_FILES['image'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'No image file found in request']);
        exit;
    }
    $target_dir = __DIR__ . '/src/static/images/';
    if (!file_exists($target_dir)) {
        mkdir($target_dir, 0755, true);
    }
    $ext = pathinfo($_FILES['image']['name'], PATHINFO_EXTENSION) ?: 'jpg';
    $filename = 'event_' . time() . '_' . rand(1000, 9999) . '.' . $ext;
    $target_file = $target_dir . $filename;
    
    if (move_uploaded_file($_FILES['image']['tmp_name'], $target_file)) {
        echo json_encode(['success' => true, 'image_url' => 'images/' . $filename]);
    } else {
        header('HTTP/1.1 500 Internal Server Error');
        echo json_encode(['error' => 'Could not save uploaded image to local server']);
    }
    exit;
}

// --------------------------------------------------------------------------
// DEDICATED VENUES CRUD
// --------------------------------------------------------------------------

// Add Venue
if ($request_uri === '/api/admin/venues/add') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['name']) || !isset($data['category'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing venue name or category']);
        exit;
    }
    $db = get_db();
    $stmt = $db->prepare("INSERT INTO venues (name, category, lat, lng) VALUES (?, ?, ?, ?)");
    $stmt->execute([
        $data['name'],
        $data['category'],
        $data['lat'] ?? 0.0,
        $data['lng'] ?? 0.0
    ]);
    echo json_encode(['success' => true, 'id' => $db->lastInsertId()]);
    exit;
}

// Edit Venue
if ($request_uri === '/api/admin/venues/edit') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['id']) || !isset($data['name']) || !isset($data['category'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing venue ID, name, or category']);
        exit;
    }
    $db = get_db();
    $stmt = $db->prepare("UPDATE venues SET name = ?, category = ?, lat = ?, lng = ? WHERE id = ?");
    $stmt->execute([
        $data['name'],
        $data['category'],
        $data['lat'] ?? 0.0,
        $data['lng'] ?? 0.0,
        $data['id']
    ]);
    echo json_encode(['success' => true]);
    exit;
}

// Delete Venue
if ($request_uri === '/api/admin/venues/delete') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['id'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing venue ID']);
        exit;
    }
    $db = get_db();
    
    // Delete venue records and cascade delete associated event rows
    $db->beginTransaction();
    $stmt1 = $db->prepare("DELETE FROM events WHERE venue_id = ?");
    $stmt1->execute([$data['id']]);
    $stmt2 = $db->prepare("DELETE FROM venue_dining_map WHERE venue_id = ?");
    $stmt2->execute([$data['id']]);
    $stmt3 = $db->prepare("DELETE FROM venues WHERE id = ?");
    $stmt3->execute([$data['id']]);
    $db->commit();
    
    echo json_encode(['success' => true]);
    exit;
}

// --------------------------------------------------------------------------
// DEDICATED DINING MAPPINGS CRUD
// --------------------------------------------------------------------------

// Add Restaurant & Map to Venue
if ($request_uri === '/api/admin/dining/add') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['restaurant_name']) || !isset($data['venue_id']) || !isset($data['distance_miles'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing restaurant_name, venue_id, or distance_miles']);
        exit;
    }
    $db = get_db();
    $db->beginTransaction();
    
    // 1. Insert or find restaurant
    $stmt = $db->prepare("SELECT id FROM restaurants WHERE name = ? LIMIT 1");
    $stmt->execute([$data['restaurant_name']]);
    $row = $stmt->fetch();
    $restaurant_id = null;
    if ($row) {
        $restaurant_id = $row['id'];
    } else {
        $stmt_ins = $db->prepare("INSERT INTO restaurants (name, lat, lng, menu_url, address) VALUES (?, ?, ?, ?, ?)");
        $stmt_ins->execute([
            $data['restaurant_name'],
            $data['lat'] ?? 0.0,
            $data['lng'] ?? 0.0,
            $data['menu_url'] ?? '',
            $data['address'] ?? ''
        ]);
        $restaurant_id = $db->lastInsertId();
    }
    
    // 2. Insert dining map record
    $stmt_map = $db->prepare("INSERT INTO venue_dining_map (venue_id, restaurant_id, distance_miles) VALUES (?, ?, ?)");
    $stmt_map->execute([
        $data['venue_id'],
        $restaurant_id,
        $data['distance_miles']
    ]);
    
    $db->commit();
    echo json_encode(['success' => true]);
    exit;
}

// Delete Dining Map Link
if ($request_uri === '/api/admin/dining/delete') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['venue_id']) || !isset($data['restaurant_id'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing venue_id or restaurant_id']);
        exit;
    }
    $db = get_db();
    $stmt = $db->prepare("DELETE FROM venue_dining_map WHERE venue_id = ? AND restaurant_id = ?");
    $stmt->execute([$data['venue_id'], $data['restaurant_id']]);
    echo json_encode(['success' => true]);
    exit;
}

// --------------------------------------------------------------------------
// CSV SPREADSHEET BULK IMPORTERS
// --------------------------------------------------------------------------

// 1. Bulk Venues
if ($request_uri === '/api/admin/bulk-venues') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['records']) || !is_array($data['records'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing records array']);
        exit;
    }
    $db = get_db();
    $db->beginTransaction();
    $stmt = $db->prepare("INSERT INTO venues (name, category, lat, lng) VALUES (?, ?, ?, ?)");
    $count = 0;
    foreach ($data['records'] as $r) {
        if (!empty($r['name']) && !empty($r['category'])) {
            $stmt->execute([
                $r['name'],
                $r['category'],
                floatval($r['lat'] ?? 0.0),
                floatval($r['lng'] ?? 0.0)
            ]);
            $count++;
        }
    }
    $db->commit();
    echo json_encode(['success' => true, 'count' => $count]);
    exit;
}

// 2. Bulk Events
if ($request_uri === '/api/admin/bulk-events') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['records']) || !is_array($data['records'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing records array']);
        exit;
    }
    $db = get_db();
    $db->beginTransaction();
    
    // Select venues lookup mapper to match names to IDs
    $venues_stmt = $db->query("SELECT id, name FROM venues");
    $venues = [];
    foreach ($venues_stmt->fetchAll() as $row) {
        $venues[strtolower(trim($row['name']))] = $row['id'];
    }
    
    $stmt = $db->prepare("INSERT INTO events (venue_id, title, date, time, ticket_url, description, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)");
    $count = 0;
    foreach ($data['records'] as $r) {
        if (empty($r['title']) || empty($r['venue_name'])) continue;
        $venue_key = strtolower(trim($r['venue_name']));
        if (isset($venues[$venue_key])) {
            $stmt->execute([
                $venues[$venue_key],
                $r['title'],
                $r['date'] ?: 'TBD',
                $r['time'] ?? null,
                $r['ticket_url'] ?? null,
                $r['description'] ?? null,
                $r['image_url'] ?? null
            ]);
            $count++;
        }
    }
    $db->commit();
    echo json_encode(['success' => true, 'count' => $count]);
    exit;
}

// 3. Bulk Dining Mapping
if ($request_uri === '/api/admin/bulk-dining') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    if (!isset($data['records']) || !is_array($data['records'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['error' => 'Missing records array']);
        exit;
    }
    $db = get_db();
    $db->beginTransaction();
    
    // Select venues lookup mapper to match names to IDs
    $venues_stmt = $db->query("SELECT id, name FROM venues");
    $venues = [];
    foreach ($venues_stmt->fetchAll() as $row) {
        $venues[strtolower(trim($row['name']))] = $row['id'];
    }
    
    $count = 0;
    try {
        error_log("INFO: bulk-dining endpoint triggered. Records count: " . count($data['records']));
        if (count($data['records']) > 0) {
            error_log("INFO: First record structure: " . json_encode($data['records'][0]));
        }
        foreach ($data['records'] as $r) {
            // Trim and normalize keys to be extra safe against spacing issues
            $rest_name = isset($r['restaurant_name']) ? trim($r['restaurant_name']) : '';
            if (empty($rest_name)) {
                error_log("WARNING: Skipping record due to empty restaurant_name. Record: " . json_encode($r));
                continue;
            }
            
            // 1. Insert or find restaurant
            $stmt_find = $db->prepare("SELECT id FROM restaurants WHERE name = ? LIMIT 1");
            $stmt_find->execute([$rest_name]);
            $row = $stmt_find->fetch();
            $restaurant_id = null;
            if ($row) {
                $restaurant_id = $row['id'];
                error_log("INFO: Found existing restaurant '{$rest_name}' with ID: " . $restaurant_id);
            } else {
                $stmt_ins = $db->prepare("INSERT INTO restaurants (name, lat, lng, menu_url, address) VALUES (?, ?, ?, ?, ?)");
                $stmt_ins->execute([
                    $rest_name,
                    floatval($r['lat'] ?? 0.0),
                    floatval($r['lng'] ?? 0.0),
                    $r['menu_url'] ?? '',
                    $r['address'] ?? ''
                ]);
                $restaurant_id = $db->lastInsertId();
                error_log("INFO: Inserted new restaurant '{$rest_name}' with ID: " . $restaurant_id);
            }
            
            // 2. Map venue dining link (only if venue details are provided)
            if (!empty($r['venue_name']) && !empty($r['distance_miles'])) {
                $venue_key = strtolower(trim($r['venue_name']));
                if (isset($venues[$venue_key])) {
                    $venue_id = $venues[$venue_key];
                    $stmt_map = $db->prepare("INSERT OR IGNORE INTO venue_dining_map (venue_id, restaurant_id, distance_miles) VALUES (?, ?, ?)");
                    $stmt_map->execute([
                        $venue_id,
                        $restaurant_id,
                        floatval($r['distance_miles'])
                    ]);
                }
            }
            $count++;
        }
        $db->commit();
        echo json_encode(['success' => true, 'count' => $count]);
    } catch (Exception $e) {
        $db->rollBack();
        header('HTTP/1.1 500 Internal Server Error');
        echo json_encode(['success' => false, 'error' => $e->getMessage()]);
    }
    exit;
}

// Serve standard index.html fallback for home routing
if ($request_uri === '/' || $request_uri === '/admin' || $request_uri === '/admin.html') {
    if ($request_uri === '/admin' || $request_uri === '/admin.html') {
        readfile(__DIR__ . '/src/static/admin.html');
    } else {
        readfile(__DIR__ . '/src/static/index.html');
    }
    exit;
}

header('HTTP/1.1 404 Not Found');
echo "404 Not Found";
