// Admin Portal State
let adminEvents = [];
let adminVenues = [];
let adminDining = [];
let filters = {
  title: "",
  venue: "",
  date: ""
};

// DOM Elements cache
const elements = {
  body: document.body,
  themeBtns: document.querySelectorAll(".theme-btn"),
  tableBody: document.getElementById("admin-table-body"),
  searchTitle: document.getElementById("admin-search-title"),
  searchVenue: document.getElementById("admin-search-venue"),
  searchDate: document.getElementById("admin-search-date"),
  addTrigger: document.getElementById("add-event-trigger"),
  dialog: document.getElementById("admin-dialog"),
  closeDialogBtn: document.getElementById("close-admin-dialog"),
  cancelDialogBtn: document.getElementById("cancel-admin-dialog"),
  dialogForm: document.getElementById("admin-event-form"),
  dialogTitle: document.getElementById("dialog-mode-title"),
  venueSelect: document.getElementById("venue-select-field"),
  
  // Form fields
  idField: document.getElementById("event-id-field"),
  titleField: document.getElementById("title-field"),
  dateField: document.getElementById("date-field"),
  timeField: document.getElementById("time-field"),
  ticketField: document.getElementById("ticket-field"),
  imageUrlField: document.getElementById("image-url-field"),
  descField: document.getElementById("desc-field")
};

const THEMES = ["luxury", "orbit", "nordic"];

// ==========================================================================
// 1. INITIALIZATION & BINDINGS
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  fetchVenues();
  fetchEvents();
  fetchDining();
  setupEventListeners();
  setupDragAndDrop();
});

function setupEventListeners() {
  // Theme Toggle Buttons
  elements.themeBtns.forEach(btn => {
    btn.addEventListener("click", (e) => {
      const selectedTheme = e.target.getAttribute("data-theme");
      setTheme(selectedTheme);
    });
  });

  // Search input filters
  if (elements.searchTitle) {
    elements.searchTitle.addEventListener("input", (e) => {
      filters.title = e.target.value.toLowerCase().trim();
      renderEventsTable();
    });
  }
  if (elements.searchVenue) {
    elements.searchVenue.addEventListener("input", (e) => {
      filters.venue = e.target.value.toLowerCase().trim();
      renderEventsTable();
    });
  }
  if (elements.searchDate) {
    elements.searchDate.addEventListener("input", (e) => {
      filters.date = e.target.value.toLowerCase().trim();
      renderEventsTable();
    });
  }

  // Add Event Trigger
  if (elements.addTrigger) {
    elements.addTrigger.addEventListener("click", () => {
      openFormForAdd();
    });
  }

  // Close Dialog buttons
  if (elements.closeDialogBtn) elements.closeDialogBtn.addEventListener("click", () => elements.dialog.close());
  if (elements.cancelDialogBtn) elements.cancelDialogBtn.addEventListener("click", () => elements.dialog.close());
}

// Tab switcher handler
window.switchTab = function(tabId, element = null) {
  // Hide all panels
  document.querySelectorAll('.admin-panel').forEach(panel => {
    panel.classList.remove('active');
  });
  
  // Deactivate all tab buttons
  document.querySelectorAll('.admin-tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });

  // Show active tab
  const targetPanel = document.getElementById(tabId);
  if (targetPanel) {
    targetPanel.classList.add('active');
  }
  
  // Highlight clicked button
  const targetBtn = element || (window.event ? window.event.target : null);
  if (targetBtn) {
    targetBtn.classList.add('active');
  }
  
  // Refresh content if switching to tab
  if (tabId === 'venues-tab') fetchVenues();
  if (tabId === 'dining-tab') fetchDining();
};

// ==========================================================================
// 2. THEME CONTROLLER
// ==========================================================================
function initTheme() {
  const savedTheme = localStorage.getItem("venue_orbit_theme") || "luxury";
  setTheme(savedTheme);
}

function setTheme(themeName) {
  if (!THEMES.includes(themeName)) return;
  THEMES.forEach(t => elements.body.classList.remove(`theme-${t}`));
  elements.body.classList.add(`theme-${themeName}`);

  elements.themeBtns.forEach(btn => {
    if (btn.getAttribute("data-theme") === themeName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
  localStorage.setItem("venue_orbit_theme", themeName);
}

// ==========================================================================
// 3. API DATA FETCHERS
// ==========================================================================
async function fetchVenues() {
  try {
    const response = await fetch("/api/venues");
    if (!response.ok) throw new Error("Failed to fetch venues list");
    adminVenues = await response.json();
    
    // Populate form select options
    if (elements.venueSelect) {
      elements.venueSelect.innerHTML = '<option value="">-- Select Target Venue --</option>' + 
        adminVenues.map(v => `<option value="${v.id}">${v.name} (${v.category})</option>`).join("");
    }
    
    // Populate dining venue select options
    const diningVenueSelect = document.getElementById("dining-venue-select");
    if (diningVenueSelect) {
      diningVenueSelect.innerHTML = '<option value="">-- Choose Venue --</option>' + 
        adminVenues.map(v => `<option value="${v.id}">${v.name}</option>`).join("");
    }
    
    renderVenuesTable();
      
  } catch (error) {
    console.error("Venues list fetch failed:", error);
  }
}

async function fetchEvents() {
  try {
    const response = await fetch("/api/events");
    if (!response.ok) throw new Error("Failed to fetch events list");
    adminEvents = await response.json();
    renderEventsTable();
  } catch (error) {
    console.error("Events list fetch failed:", error);
    elements.tableBody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; padding:3rem; color:var(--text-muted);">
          ❌ Could not read events from the database.
        </td>
      </tr>
    `;
  }
}

async function fetchDining() {
  try {
    const diningTableBody = document.getElementById("dining-table-body");
    if (!diningTableBody) return;
    diningTableBody.innerHTML = '<tr><td colspan="5" class="loading-state">Loading dining mappings...</td></tr>';
    
    // Fetch mapped restaurants for all venues
    let allMappings = [];
    for (const venue of adminVenues) {
      const resp = await fetch(`/api/dining?venue_id=${venue.id}`);
      if (resp.ok) {
        const diningRows = await resp.json();
        diningRows.forEach(row => {
          allMappings.push({
            venue_id: venue.id,
            venue_name: venue.name,
            restaurant_name: row.name,
            restaurant_id: row.restaurant_id || null, // Map handles deletes
            distance_miles: row.distance_miles,
            address: row.address || ''
          });
        });
      }
    }
    adminDining = allMappings;
    renderDiningTable();
  } catch (error) {
    console.error("Failed to load dining database mappings:", error);
  }
}

// ==========================================================================
// 4. CRUD FORMS & OPERATIONS
// ==========================================================================
function openFormForAdd() {
  elements.dialogTitle.textContent = "➕ Add Event";
  elements.dialogForm.reset();
  elements.idField.value = "";
  elements.dateField.value = "TBD";
  elements.dialog.showModal();
}

window.openFormForEdit = function(eventId) {
  const event = adminEvents.find(e => e.id === eventId);
  if (!event) return;

  elements.dialogTitle.textContent = "✏️ Edit Event Details";
  elements.idField.value = event.id;
  elements.venueSelect.value = event.venue_id;
  elements.titleField.value = event.title;
  elements.dateField.value = event.date;
  elements.timeField.value = event.time || "";
  elements.ticketField.value = event.ticket_url || "";
  elements.imageUrlField.value = event.image_url || "";
  elements.descField.value = event.description || "";

  elements.dialog.showModal();
};

window.duplicateEvent = function(eventId) {
  const event = adminEvents.find(e => e.id === eventId);
  if (!event) return;

  elements.dialogTitle.textContent = "👯 Duplicate Event (New)";
  elements.idField.value = ""; // Empty ID makes it an INSERT (Add) operation
  elements.venueSelect.value = event.venue_id;
  elements.titleField.value = event.title + " (Copy)";
  elements.dateField.value = event.date;
  elements.timeField.value = event.time || "";
  elements.ticketField.value = event.ticket_url || "";
  elements.imageUrlField.value = event.image_url || "";
  elements.descField.value = event.description || "";

  elements.dialog.showModal();
};

window.handleFormSubmit = async function(e) {
  e.preventDefault();
  
  const payload = {
    venue_id: parseInt(elements.venueSelect.value),
    title: elements.titleField.value.trim(),
    date: elements.dateField.value.trim(),
    time: elements.timeField.value.trim() || null,
    ticket_url: elements.ticketField.value.trim() || null,
    image_url: elements.imageUrlField.value.trim() || null,
    description: elements.descField.value.trim() || null
  };

  const id = elements.idField.value;
  const isEdit = id !== "";
  
  let endpoint = "/api/admin/add";
  if (isEdit) {
    payload.id = parseInt(id);
    endpoint = "/api/admin/edit";
  }

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) throw new Error("Server error during save");
    const result = await response.json();
    
    if (result.success) {
      elements.dialog.close();
      fetchEvents(); // Reload and redraw table
    }
  } catch (error) {
    console.error("Save event failed:", error);
    alert("❌ Error: Failed to save the event to the database.");
  }
};

window.handleImageFileUpload = async function(inputEl) {
  const file = inputEl.files[0];
  if (!file) return;

  const statusEl = document.getElementById("upload-status");
  statusEl.style.display = "block";
  statusEl.textContent = "⏳ Uploading image file...";

  const formData = new FormData();
  formData.append("image", file);

  try {
    const response = await fetch("/api/admin/upload-image", {
      method: "POST",
      body: formData
    });

    if (!response.ok) throw new Error("Image upload failed");
    const result = await response.json();

    if (result.success && result.image_url) {
      elements.imageUrlField.value = result.image_url;
      statusEl.textContent = "✅ Image uploaded successfully!";
      setTimeout(() => { statusEl.style.display = "none"; }, 3000);
    }
  } catch (error) {
    console.error("Upload failed:", error);
    statusEl.textContent = "❌ Image upload failed.";
    alert("❌ Error: Could not save uploaded image to local server.");
  }
};

window.confirmDeleteEvent = async function(eventId) {
  const event = adminEvents.find(e => e.id === eventId);
  if (!event) return;

  const isConfirmed = confirm(`⚠️ Are you sure you want to delete the event:\n"${event.title}"?`);
  if (!isConfirmed) return;

  try {
    const response = await fetch("/api/admin/delete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ id: eventId })
    });

    if (!response.ok) throw new Error("Server error during delete");
    const result = await response.json();
    
    if (result.success) {
      fetchEvents(); // Reload database events
    }
  } catch (error) {
    console.error("Delete failed:", error);
    alert("❌ Error: Failed to delete the event from the database.");
  }
};

// --------------------------------------------------------------------------
// VENUES CRUD HANDLERS
// --------------------------------------------------------------------------
window.openVenueModal = function(venueId = null) {
  const modal = document.getElementById("venue-dialog");
  const form = document.getElementById("admin-venue-form");
  form.reset();
  
  if (venueId) {
    const venue = adminVenues.find(v => v.id === venueId);
    if (venue) {
      document.getElementById("venue-dialog-title").textContent = "✏️ Edit Venue";
      document.getElementById("venue-id-field").value = venue.id;
      document.getElementById("venue-name-field").value = venue.name;
      document.getElementById("venue-category-field").value = venue.category;
      document.getElementById("venue-lat-field").value = venue.lat || "";
      document.getElementById("venue-lng-field").value = venue.lng || "";
    }
  } else {
    document.getElementById("venue-dialog-title").textContent = "🏢 Add Venue";
    document.getElementById("venue-id-field").value = "";
  }
  
  modal.showModal();
};

window.handleVenueFormSubmit = async function(e) {
  e.preventDefault();
  const idVal = document.getElementById("venue-id-field").value;
  const isEdit = idVal !== "";
  
  const payload = {
    name: document.getElementById("venue-name-field").value.trim(),
    category: document.getElementById("venue-category-field").value,
    lat: parseFloat(document.getElementById("venue-lat-field").value) || 0.0,
    lng: parseFloat(document.getElementById("venue-lng-field").value) || 0.0
  };
  
  let url = "/api/admin/venues/add";
  if (isEdit) {
    payload.id = parseInt(idVal);
    url = "/api/admin/venues/edit";
  }
  
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (resp.ok) {
      document.getElementById("venue-dialog").close();
      fetchVenues();
    }
  } catch (err) {
    console.error("Venue save error:", err);
  }
};

window.confirmDeleteVenue = async function(venueId) {
  const venue = adminVenues.find(v => v.id === venueId);
  if (!venue) return;
  
  const ok = confirm(`⚠️ Danger: Deleting venue "${venue.name}" will ALSO delete all associated events and dining maps. Do you want to proceed?`);
  if (!ok) return;
  
  try {
    const resp = await fetch("/api/admin/venues/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: venueId })
    });
    if (resp.ok) {
      fetchVenues();
    }
  } catch (err) {
    console.error("Venue delete failed:", err);
  }
};

// --------------------------------------------------------------------------
// DINING MAPPINGS CRUD HANDLERS
// --------------------------------------------------------------------------
window.openDiningModal = function() {
  const form = document.getElementById("admin-dining-form");
  form.reset();
  document.getElementById("dining-dialog").showModal();
};

window.handleDiningFormSubmit = async function(e) {
  e.preventDefault();
  
  const payload = {
    venue_id: parseInt(document.getElementById("dining-venue-select").value),
    restaurant_name: document.getElementById("dining-name-field").value.trim(),
    distance_miles: parseFloat(document.getElementById("dining-distance-field").value),
    menu_url: document.getElementById("dining-menu-field").value.trim(),
    address: document.getElementById("dining-address-field").value.trim(),
    lat: parseFloat(document.getElementById("dining-lat-field").value) || 0.0,
    lng: parseFloat(document.getElementById("dining-lng-field").value) || 0.0
  };
  
  try {
    const resp = await fetch("/api/admin/dining/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (resp.ok) {
      document.getElementById("dining-dialog").close();
      fetchDining();
    }
  } catch (err) {
    console.error("Dining link save error:", err);
  }
};

window.confirmDeleteDining = async function(venueId, restaurantName) {
  const ok = confirm(`Delete walkable link between this venue and "${restaurantName}"?`);
  if (!ok) return;
  
  // Find mapping to locate restaurant_id
  const mapping = adminDining.find(m => m.venue_id === venueId && m.restaurant_name === restaurantName);
  if (!mapping) return;
  
  try {
    const resp = await fetch("/api/admin/dining/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        venue_id: venueId, 
        restaurant_id: mapping.restaurant_id || 0 // Handled by SQL find
      })
    });
    if (resp.ok) {
      fetchDining();
    }
  } catch (err) {
    console.error("Dining link deletion error:", err);
  }
};

// --------------------------------------------------------------------------
// 5. RENDERERS & LAYOUT CONTROLLERS
// --------------------------------------------------------------------------
function renderEventsTable() {
  const filtered = adminEvents.filter(e => {
    const matchesTitle = e.title.toLowerCase().includes(filters.title);
    const matchesVenue = e.venue_name.toLowerCase().includes(filters.venue);
    const matchesDate = e.date.toLowerCase().includes(filters.date);
    return matchesTitle && matchesVenue && matchesDate;
  });

  if (filtered.length === 0) {
    elements.tableBody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; padding:3rem; color:var(--text-muted);">
          🔍 No matching events found in database.
        </td>
      </tr>
    `;
    return;
  }

  elements.tableBody.innerHTML = filtered.map(e => {
    return `
      <tr>
        <td><strong style="color:var(--accent-color); font-family:monospace;">#${e.id}</strong></td>
        <td><span class="category-tag" style="margin-bottom:0; font-size:0.75rem;">${e.category}</span></td>
        <td><strong style="font-size:0.95rem;">${e.title}</strong></td>
        <td>📍 ${e.venue_name}</td>
        <td><code style="font-family:monospace; font-weight:600;">${e.date}</code></td>
        <td>${e.time || '<span style="color:var(--text-muted); font-style:italic;">None</span>'}</td>
        <td>
          <div style="display:flex; flex-direction:column; gap:0.25rem;">
            <div>
              <span class="action-badge edit-badge" onclick="openFormForEdit(${e.id})">✏️ Edit</span>
              <span class="action-badge delete-badge" onclick="confirmDeleteEvent(${e.id})">🗑️ Delete</span>
            </div>
            <div style="margin-top:0.25rem;">
              <span class="action-badge duplicate-badge" onclick="duplicateEvent(${e.id})">👯 Duplicate</span>
            </div>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function renderVenuesTable() {
  const tableBody = document.getElementById("venues-table-body");
  if (!tableBody) return;
  
  if (adminVenues.length === 0) {
    tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:3rem;">No venues listed.</td></tr>';
    return;
  }
  
  tableBody.innerHTML = adminVenues.map(v => {
    return `
      <tr>
        <td><strong style="color:var(--accent-color); font-family:monospace;">#${v.id}</strong></td>
        <td><strong>${v.name}</strong></td>
        <td><span class="category-tag" style="margin:0;">${v.category}</span></td>
        <td>${v.lat || '0.0'}</td>
        <td>${v.lng || '0.0'}</td>
        <td>
          <span class="action-badge edit-badge" onclick="openVenueModal(${v.id})">✏️ Edit</span>
          <span class="action-badge delete-badge" onclick="confirmDeleteVenue(${v.id})">🗑️ Delete</span>
        </td>
      </tr>
    `;
  }).join("");
}

function renderDiningTable() {
  const tableBody = document.getElementById("dining-table-body");
  if (!tableBody) return;
  
  if (adminDining.length === 0) {
    tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:3rem;">No dining links mapped.</td></tr>';
    return;
  }
  
  tableBody.innerHTML = adminDining.map(m => {
    return `
      <tr>
        <td><strong>${m.venue_name}</strong></td>
        <td>🍔 ${m.restaurant_name}</td>
        <td><code style="font-family:monospace; font-weight:700;">${m.distance_miles.toFixed(2)} miles</code></td>
        <td><span style="font-size:0.85rem; color:var(--text-muted);">${m.address || 'None'}</span></td>
        <td>
          <span class="action-badge delete-badge" onclick="confirmDeleteDining(${m.venue_id}, '${m.restaurant_name.replace(/'/g, "\\'")}')">🗑️ Unlink</span>
        </td>
      </tr>
    `;
  }).join("");
}

// --------------------------------------------------------------------------
// 6. CSV FILE SPREADSHEET PARSING & BULK UPLOAD
// --------------------------------------------------------------------------
function setupDragAndDrop() {
  const dropzone = document.getElementById("csv-dropzone");
  if (!dropzone) return;
  
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, e => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    }, false);
  });
  
  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, e => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    }, false);
  });
  
  dropzone.addEventListener('drop', e => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length) {
      document.getElementById("csv-file-input").files = files;
      handleCSVFileSelected({ target: { files: files } });
    }
  });
}

window.handleCSVFileSelected = function(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  const statusEl = document.getElementById("bulk-upload-status");
  statusEl.innerHTML = `⏳ Reading spreadsheet file: <strong>${file.name}</strong>...`;
  
  const reader = new FileReader();
  reader.onload = function(evt) {
    const text = evt.target.result;
    parseAndUploadCSV(text);
  };
  reader.readAsText(file);
};

async function parseAndUploadCSV(csvText) {
  console.log("parseAndUploadCSV triggered with text length:", csvText.length);
  const statusEl = document.getElementById("bulk-upload-status");
  const importType = document.getElementById("bulk-type-select").value;
  console.log("Import target type selected:", importType);
  
  try {
    const lines = csvText.split(/\r?\n/);
    if (lines.length < 2) throw new Error("File is empty or has no header row.");
    
    // Parse headers
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/^["']|["']$/g, ""));
    const records = [];
    
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      
      // Basic CSV parser handling potential quotes containing commas
      const values = [];
      let match;
      const lexer = /"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)'|([^,\s"']+)|,\s*(?=,|$)|(,\s*)/g;
      
      let rawValues = [];
      let inQuotes = false;
      let currentVal = "";
      for (let charIndex = 0; charIndex < line.length; charIndex++) {
        const c = line[charIndex];
        if (c === '"') {
          inQuotes = !inQuotes;
        } else if (c === ',' && !inQuotes) {
          rawValues.push(currentVal.trim());
          currentVal = "";
        } else {
          currentVal += c;
        }
      }
      rawValues.push(currentVal.trim());
      const record = {};
      headers.forEach((header, index) => {
        let val = rawValues[index] || "";
        // Strip quotes
        val = val.replace(/^["']|["']$/g, "").trim();
        record[header] = val;
      });
      records.push(record);
    }
    
    console.log("Parsed records count:", records.length);
    console.log("First parsed record sample:", records[0]);
    statusEl.innerHTML = `⏳ Sending ${records.length} records to database...`;
    
    const resp = await fetch(`/api/admin/bulk-${importType}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ records: records })
    });
    
    if (!resp.ok) throw new Error("Server bulk insert API failed");
    const result = await resp.json();
    console.log("Bulk upload server response:", result);
    
    if (result.success) {
      statusEl.innerHTML = `✅ Successfully imported <strong>${result.count}</strong> records!`;
      // Reload relevant arrays
      fetchEvents();
      fetchVenues();
      fetchDining();
    } else {
      statusEl.innerHTML = `❌ Upload failed. Verify CSV headers match specifications.`;
    }
    
  } catch (err) {
    console.error("Bulk CSV import error:", err);
    statusEl.innerHTML = `❌ Error: ${err.message}`;
  }
}

