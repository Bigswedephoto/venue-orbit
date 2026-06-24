// Global Application State
let eventsData = [];
let activeFilters = {
  search: "",
  time: "all",
  category: "all",
  calendarDate: null // Stores selected calendar date (e.g. "2026-06-19")
};

let currentCalendarMonth = new Date(); // Tracks the displayed month

// Theme Config mappings
const THEMES = ["luxury", "orbit", "nordic"];

// DOM elements cache
const elements = {
  body: document.body,
  themeBtns: document.querySelectorAll(".theme-btn"),
  eventsGrid: document.getElementById("events-grid"),
  searchInput: document.getElementById("event-search"),
  timeTabs: document.querySelectorAll(".filter-tab"),
  catPills: document.querySelectorAll(".cat-pill"),
  dialog: document.getElementById("event-dialog"),
  closeDialogBtn: document.getElementById("close-dialog"),
  mapRadar: document.getElementById("map-radar"),
  quickCoords: document.getElementById("quick-coords"),
  
  // Calendar elements
  prevMonth: document.getElementById("prev-month"),
  nextMonth: document.getElementById("next-month"),
  monthYear: document.getElementById("calendar-month-year"),
  calendarDays: document.getElementById("calendar-days")
};

// ==========================================================================
// 1. INITIALIZATION & LISTENERS
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initMaps();
  fetchEvents();
  setupEventListeners();
  renderCalendar();
});

function setupEventListeners() {
  // Theme Toggle Buttons
  elements.themeBtns.forEach(btn => {
    btn.addEventListener("click", (e) => {
      const selectedTheme = e.target.getAttribute("data-theme");
      setTheme(selectedTheme);
    });
  });

  // Search input
  elements.searchInput.addEventListener("input", (e) => {
    activeFilters.search = e.target.value.toLowerCase().trim();
    renderFilteredEvents();
  });

  // Time tabs
  elements.timeTabs.forEach(tab => {
    tab.addEventListener("click", (e) => {
      elements.timeTabs.forEach(t => t.classList.remove("active"));
      e.target.classList.add("active");
      activeFilters.time = e.target.getAttribute("data-time");
      activeFilters.calendarDate = null; // Clear calendar selection when tab is selected
      renderCalendar(); // Rerender calendar to clear active state
      renderFilteredEvents();
    });
  });

  // Category pills
  elements.catPills.forEach(pill => {
    pill.addEventListener("click", (e) => {
      elements.catPills.forEach(p => p.classList.remove("active"));
      e.target.classList.add("active");
      activeFilters.category = e.target.getAttribute("data-cat");
      renderFilteredEvents();
    });
  });

  // Close Dialog interactions
  elements.closeDialogBtn.addEventListener("click", () => {
    elements.dialog.close();
  });

  // Click outside dialog to close (Light dismiss helper)
  elements.dialog.addEventListener("click", (e) => {
    const rect = elements.dialog.getBoundingClientRect();
    const isInDialog = (rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX && e.clientX <= rect.left + rect.width);
    if (!isInDialog) {
      elements.dialog.close();
    }
  });

  // Calendar Navigation
  elements.prevMonth.addEventListener("click", () => {
    currentCalendarMonth.setMonth(currentCalendarMonth.getMonth() - 1);
    renderCalendar();
  });

  elements.nextMonth.addEventListener("click", () => {
    currentCalendarMonth.setMonth(currentCalendarMonth.getMonth() + 1);
    renderCalendar();
  });
}

// ==========================================================================
// 2. THEME CONTROLLER
// ==========================================================================
function initTheme() {
  const savedTheme = localStorage.getItem("venue_orbit_theme") || "luxury";
  setTheme(savedTheme);
}

function setTheme(themeName) {
  if (!THEMES.includes(themeName)) return;
  
  // Update classes
  THEMES.forEach(t => elements.body.classList.remove(`theme-${t}`));
  elements.body.classList.add(`theme-${themeName}`);

  // Update button active state
  elements.themeBtns.forEach(btn => {
    if (btn.getAttribute("data-theme") === themeName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Persist choice
  localStorage.setItem("venue_orbit_theme", themeName);
}

// ==========================================================================
// 3. API DATA FETCHERS
// ==========================================================================
async function fetchEvents() {
  try {
    const response = await fetch("/api/events");
    if (!response.ok) throw new Error("Failed to fetch events data.");
    eventsData = await response.json();
    renderFilteredEvents();
    renderCalendar(); // Highlight days with events
  } catch (error) {
    console.error("API error:", error);
    elements.eventsGrid.innerHTML = `
      <div class="empty-state">
        <h3>🪐 Lost Connection</h3>
        <p>Could not retrieve events database. Please verify the aggregator database status.</p>
      </div>
    `;
  }
}

async function fetchNearbyDining(venueId) {
  const diningList = document.getElementById("dining-list");
  diningList.innerHTML = `<div class="loading-state"><span class="spinner"></span> Querying nearby walkable dining...</div>`;
  
  const venue = eventsData.find(e => e.venue_id === venueId);
  
  try {
    const response = await fetch(`/api/dining?venue_id=${venueId}`);
    if (!response.ok) throw new Error("Failed to fetch dining options.");
    const diningData = await response.json();
    
    // Update live dialog map if coordinates exist
    if (venue && venue.venue_lat && venue.venue_lng) {
      updateDialogMap(venue.venue_lat, venue.venue_lng, venue.venue_name, diningData);
    }
    
    if (diningData.length === 0) {
      diningList.innerHTML = `<p class="empty-state">🍔 No restaurants found within walking distance (0.5 miles) in the database.</p>`;
      return;
    }
    
    diningList.innerHTML = diningData.map(item => {
      const walkTime = Math.round(item.distance_miles * 20); // Estimation: 20 mins per mile
      const menuBtn = item.menu_url ? `<a href="${item.menu_url}" class="menu-btn" target="_blank">Menu</a>` : "";
      
      return `
        <div class="dining-item">
          <div class="dining-info">
            <span class="dining-name">${item.name}</span>
            <span class="dining-distance">📍 ${item.distance_miles.toFixed(2)} mi (~${walkTime} min walk)</span>
            <span class="dining-address">${item.address}</span>
          </div>
          ${menuBtn}
        </div>
      `;
    }).join("");
    
  } catch (error) {
    console.error("Dining API error:", error);
    diningList.innerHTML = `<p class="empty-state">❌ Failed to query hyper-local food database.</p>`;
  }
}

// ==========================================================================
// 4. RENDERERS & EVENT HANDLERS
// ==========================================================================
function renderFilteredEvents() {
  const filtered = eventsData.filter(event => {
    // 1. Search filter
    const matchesSearch = event.title.toLowerCase().includes(activeFilters.search) ||
                          event.venue_name.toLowerCase().includes(activeFilters.search);

    // 2. Category filter
    const matchesCat = activeFilters.category === "all" || event.category === activeFilters.category;

    // 3. Time filter
    let matchesTime = true;
    if (activeFilters.calendarDate) {
      matchesTime = event.date === activeFilters.calendarDate;
    } else if (activeFilters.time !== "all") {
      const todayStr = new Date().toISOString().split('T')[0];
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const tomorrowStr = tomorrow.toISOString().split('T')[0];
      
      // Determine weekend range (Friday to Sunday)
      const now = new Date();
      const dayOfWeek = now.getDay(); // 0 is Sunday, 5 is Friday, 6 is Saturday
      const daysToFriday = dayOfWeek <= 5 ? (5 - dayOfWeek) : (5 + 7 - dayOfWeek);
      const fri = new Date(now);
      fri.setDate(now.getDate() + daysToFriday);
      const sun = new Date(fri);
      sun.setDate(fri.getDate() + 2);
      
      const friStr = fri.toISOString().split('T')[0];
      const sunStr = sun.toISOString().split('T')[0];

      if (activeFilters.time === "tonight") {
        matchesTime = event.date === todayStr;
      } else if (activeFilters.time === "weekend") {
        matchesTime = event.date >= friStr && event.date <= sunStr;
      }
    }

    // Exclude TBD dates because they often represent past/unresolvable schedules
    if (event.date === "TBD") return false;

    return matchesSearch && matchesCat && matchesTime;
  });

  if (filtered.length === 0) {
    elements.eventsGrid.innerHTML = `
      <div class="empty-state">
        <h3>🔍 No Matches Found</h3>
        <p>Try resetting filters or adjusting search queries.</p>
      </div>
    `;
    return;
  }

  // Group events by matching title and venue_id to deduplicate multi-date schedules
  const groupedEvents = [];
  const groups = {};

  filtered.forEach(event => {
    const key = `${event.title.toLowerCase()}_${event.venue_id}`;
    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(event);
  });

  for (const key in groups) {
    const list = groups[key];
    // Sort runs chronologically
    list.sort((a, b) => {
      if (a.date === "TBD") return 1;
      if (b.date === "TBD") return -1;
      return a.date.localeCompare(b.date);
    });
    
    // Primary event represents the earliest date
    const primary = list[0];
    groupedEvents.push({
      primary: primary,
      runs: list
    });
  }

  // Sort groups chronologically based on their earliest run
  groupedEvents.sort((a, b) => {
    if (a.primary.date === "TBD") return 1;
    if (b.primary.date === "TBD") return -1;
    return a.primary.date.localeCompare(b.primary.date);
  });

  elements.eventsGrid.innerHTML = groupedEvents.map(group => {
    const primary = group.primary;
    const isMultiDate = group.runs.length > 1;
    
    // Human friendly date helper
    const getHumanDate = (dateStr) => {
      if (!dateStr || dateStr === "TBD") return "TBD";
      const dateObj = new Date(dateStr + "T00:00:00");
      if (isNaN(dateObj.getTime())) return dateStr;
      return dateObj.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        weekday: 'short'
      });
    };

    const imgTag = primary.image_url ? `<img class="event-thumbnail" src="${primary.image_url}" alt="${primary.title}">` : "";
    const badge = isMultiDate ? `<span class="multi-date-badge">${group.runs.length} Dates</span>` : "";

    let dateSectionHTML = "";
    if (isMultiDate) {
      const optionsHTML = group.runs.map(run => {
        return `<option value="${run.id}">${getHumanDate(run.date)}</option>`;
      }).join("");
      dateSectionHTML = `
        <select class="dedup-date-select" onclick="event.stopPropagation()" onchange="updateCardTarget(this, ${primary.id})">
          ${optionsHTML}
        </select>
      `;
    } else {
      dateSectionHTML = `<span class="date-tag">${getHumanDate(primary.date)}</span>`;
    }

    return `
      <div class="event-card" id="card-group-${primary.id}" data-selected-id="${primary.id}" onclick="openEventDetails(parseInt(this.getAttribute('data-selected-id')))">
        <div class="card-top">
          ${imgTag}
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: 0.5rem;">
            <span class="category-tag" style="margin-bottom:0;">${primary.category}</span>
            ${badge}
          </div>
          <h3 class="event-title">${primary.title}</h3>
          <span class="venue-tag">📍 ${primary.venue_name}</span>
        </div>
        <div class="card-bottom">
          ${dateSectionHTML}
          <span class="arrow-icon">→</span>
        </div>
      </div>
    `;
  }).join("");
}

// Global helper to switch event details target when selecting different run dates
window.updateCardTarget = function(selectEl, primaryId) {
  const selectedEventId = selectEl.value;
  const card = document.getElementById(`card-group-${primaryId}`);
  if (card) {
    card.setAttribute("data-selected-id", selectedEventId);
  }
};

// Open modal drawer
window.openEventDetails = function(eventId) {
  const event = eventsData.find(e => e.id === eventId);
  if (!event) return;

  // Set hero image if it exists
  const diagImg = document.getElementById("diag-image");
  if (event.image_url) {
    diagImg.src = event.image_url;
    diagImg.style.display = "block";
  } else {
    diagImg.style.display = "none";
    diagImg.src = "";
  }

  // Set event card detail info
  document.getElementById("diag-category").textContent = event.category;
  document.getElementById("diag-title").textContent = event.title;
  document.getElementById("diag-venue").textContent = event.venue_name;
  
  let formattedDiagDate = "TBD";
  if (event.date && event.date !== "TBD") {
    const dateObj = new Date(event.date + "T00:00:00");
    if (!isNaN(dateObj.getTime())) {
      formattedDiagDate = dateObj.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
      });
    }
  }
  document.getElementById("diag-date").textContent = formattedDiagDate;
  document.getElementById("diag-time").textContent = event.time || "See ticket site for details";
  document.getElementById("diag-desc").textContent = event.description || "Join us for this upcoming run. Explore walking-distance restaurant recommendations to complete your night out in Birmingham.";
  
  // Set ticket link
  const ticketBtn = document.getElementById("diag-ticket-link");
  if (event.ticket_url) {
    ticketBtn.href = event.ticket_url;
    ticketBtn.style.display = "inline-block";
  } else {
    ticketBtn.style.display = "none";
  }

  // Query and render nearby dining options
  fetchNearbyDining(event.venue_id);

  // Open native dialog modal
  elements.dialog.showModal();

  // Desktop Map update
  if (event.venue_lat && event.venue_lng) {
    updateSidebarMap(event.venue_lat, event.venue_lng, event.venue_name);
  }
};

// Global map objects
let sidebarMap = null;
let sidebarMarker = null;
let dialogMap = null;
let dialogMarkers = [];

// Initialize maps
function initMaps() {
  const defaultLat = 33.5186;
  const defaultLng = -86.8104;
  
  // Initialize Sidebar map
  sidebarMap = L.map('sidebar-map', {
    zoomControl: true,
    scrollWheelZoom: false
  }).setView([defaultLat, defaultLng], 13);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; CartoDB'
  }).addTo(sidebarMap);
}

// Update Sidebar Map Marker
function updateSidebarMap(lat, lng, name) {
  if (!sidebarMap) return;
  
  if (sidebarMarker) {
    sidebarMarker.setLatLng([lat, lng]);
  } else {
    const customIcon = L.divIcon({
      className: 'custom-venue-pin',
      html: '<div style="width:14px; height:14px; border-radius:50%; background:#d4a359; box-shadow: 0 0 15px #d4a359;"></div>',
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });
    sidebarMarker = L.marker([lat, lng], {icon: customIcon}).addTo(sidebarMap);
  }
  sidebarMarker.bindPopup(`<b>${name}</b>`).openPopup();
  sidebarMap.setView([lat, lng], 15);
  
  // Force recalculating map size inside container
  setTimeout(() => { sidebarMap.invalidateSize(); }, 200);
}

// Update dialog details map with venue and dining option markers
function updateDialogMap(venueLat, venueLng, venueName, diningData) {
  const mapContainer = document.getElementById('dialog-map');
  if (!mapContainer) return;
  
  // Initialize Dialog Map if it doesn't exist
  if (!dialogMap) {
    dialogMap = L.map('dialog-map', {
      zoomControl: true,
      scrollWheelZoom: true
    }).setView([venueLat, venueLng], 15);
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; CartoDB'
    }).addTo(dialogMap);
  } else {
    // Clear old markers
    dialogMarkers.forEach(m => dialogMap.removeLayer(m));
    dialogMarkers = [];
    dialogMap.setView([venueLat, venueLng], 15);
  }
  
  // Force map to redraw size properly inside open dialog container
  setTimeout(() => { dialogMap.invalidateSize(); }, 150);

  // Add Venue Pin (Gold Color)
  const venueIcon = L.divIcon({
    className: 'dialog-venue-icon',
    html: '<div style="width:16px; height:16px; border-radius:50%; background:#d4a359; border: 2px solid #fff; box-shadow: 0 0 15px #d4a359;"></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  });
  const venueMarker = L.marker([venueLat, venueLng], {icon: venueIcon})
    .addTo(dialogMap)
    .bindPopup(`<b>📍 Venue: ${venueName}</b>`);
  
  dialogMarkers.push(venueMarker);
  
  // Add Restaurant Pins (Cyan Color)
  diningData.forEach(restaurant => {
    if (restaurant.lat && restaurant.lng) {
      const restIcon = L.divIcon({
        className: 'dialog-restaurant-icon',
        html: '<div style="width:12px; height:12px; border-radius:50%; background:#00f0c8; border: 1px solid #fff; box-shadow: 0 0 10px #00f0c8;"></div>',
        iconSize: [12, 12],
        iconAnchor: [6, 6]
      });
      const walkTime = Math.round(restaurant.distance_miles * 20);
      const marker = L.marker([restaurant.lat, restaurant.lng], {icon: restIcon})
        .addTo(dialogMap)
        .bindPopup(`<b>🍔 ${restaurant.name}</b><br>${restaurant.distance_miles.toFixed(2)} miles (~${walkTime} min walk)<br><a href="${restaurant.menu_url || '#'}" target="_blank">View Menu</a>`);
      
      dialogMarkers.push(marker);
    }
  });
}


// ==========================================================================
// 5. CALENDAR RENDERER & INTERACTIVE FILTER
// ==========================================================================
function renderCalendar() {
  if (!elements.calendarDays) return; // Guard for script context
  
  const month = currentCalendarMonth.getMonth();
  const year = currentCalendarMonth.getFullYear();
  
  // Set month/year header text
  const monthNames = ["January", "February", "March", "April", "May", "June", 
                      "July", "August", "September", "October", "November", "December"];
  elements.monthYear.textContent = `${monthNames[month]} ${year}`;
  
  // Calculate first day and total days
  const firstDayIndex = new Date(year, month, 1).getDay();
  const totalDays = new Date(year, month + 1, 0).getDate();
  
  let daysHTML = "";
  
  // Empty slots for previous month's weekday overflow
  for (let i = 0; i < firstDayIndex; i++) {
    daysHTML += `<div class="calendar-day empty"></div>`;
  }
  
  // Render days
  for (let day = 1; day <= totalDays; day++) {
    // Format YYYY-MM-DD
    const mm = String(month + 1).padStart(2, '0');
    const dd = String(day).padStart(2, '0');
    const dateStr = `${year}-${mm}-${dd}`;
    
    // Check if this date has events in the dataset
    const hasEvents = eventsData.some(e => e.date === dateStr);
    const hasEventsClass = hasEvents ? "has-events" : "";
    
    // Check if this day is currently selected
    const isActive = activeFilters.calendarDate === dateStr ? "active" : "";
    
    daysHTML += `
      <div class="calendar-day ${hasEventsClass} ${isActive}" 
           onclick="toggleCalendarDate('${dateStr}')" 
           title="${hasEvents ? 'Events scheduled' : ''}">
        ${day}
      </div>
    `;
  }
  
  elements.calendarDays.innerHTML = daysHTML;
}

window.toggleCalendarDate = function(dateStr) {
  // Toggle selection
  if (activeFilters.calendarDate === dateStr) {
    activeFilters.calendarDate = null; // Deselect
    // Re-highlight the active tab filter visually
    elements.timeTabs.forEach(t => {
      if (t.getAttribute("data-time") === activeFilters.time) {
        t.classList.add("active");
      }
    });
  } else {
    activeFilters.calendarDate = dateStr; // Select
    
    // Deactivate standard time tabs visually
    elements.timeTabs.forEach(t => t.classList.remove("active"));
  }
  
  renderCalendar();
  renderFilteredEvents();
};
