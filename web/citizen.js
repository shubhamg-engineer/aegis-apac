/**
 * Aegis-APAC Citizen Home (Simple Mode UI)
 * ──────────────────────────────────────────────────────────────────────────
 * Fast, lightweight, offline-resilient presentation layer.
 * Instant 2-second situational comprehension.
 * ──────────────────────────────────────────────────────────────────────────
 */

"use strict";

const API_BASE = window.location.origin;

// State Container
const CitizenApp = {
  currentDistrict: localStorage.getItem("aegis_citizen_district") || "South 24 Parganas",
  currentLang: localStorage.getItem("aegis_citizen_lang") || "en",
  statusData: null,
  mapInstance: null,
  mapInitialized: false,

  // Text translations for UI chrome
  UI_I18N: {
    en: {
      action_btn: "What should I do?",
      map_btn: "See map & details ›",
      for_officials: "For officials & control room ›",
      last_checked_prefix: "Last checked:",
      just_now: "Just now",
      min_ago: "min ago",
      offline_warning: "⚡ Offline mode — Showing last confirmed status",
      shelter_badge: "Nearest Shelter",
      call_1077: "📞 Helpline 1077",
      call_112: "🚨 Emergency 112",
      call_108: "🚑 Ambulance 108",
      advisory_title: "Official Early-Warning Advisory",
      advanced_view: "Open Official Control Room Console ›",
      select_loc_title: "Select Your District",
      use_gps: "📍 Use My Current GPS Location",
      select_lang_title: "Select Language / ভাষা / भाषा / ଭାଷା",
    },
    bn: {
      action_btn: "আমার কী করণীয়?",
      map_btn: "মানচিত্র ও বিস্তারিত দেখুন ›",
      for_officials: "আধিকারিক ও কন্ট্রোল রুমের জন্য ›",
      last_checked_prefix: "সর্বশেষ যাচাই:",
      just_now: "এইমাত্র",
      min_ago: "মিনিট আগে",
      offline_warning: "⚡ অফলাইন মোড — সংরক্ষিত তথ্য প্রদর্শিত হচ্ছে",
      shelter_badge: "নিকটবর্তী আশ্রয়কেন্দ্র",
      call_1077: "📞 হেল্পলাইন ১০৭৭",
      call_112: "🚨 জরুরি ১১২",
      call_108: "🚑 অ্যাম্বুলেন্স ১০৮",
      advisory_title: "সরকারি আগাম সতর্কবার্তা",
      advanced_view: "অফিসিয়াল কন্ট্রোল রুম কনসোল খুলুন ›",
      select_loc_title: "আপনার জেলা নির্বাচন করুন",
      use_gps: "📍 বর্তমান জিপিএস অবস্থান ব্যবহার করুন",
      select_lang_title: "ভাষা নির্বাচন করুন (Select Language)",
    },
    hi: {
      action_btn: "मुझे क्या करना चाहिए?",
      map_btn: "मानचित्र और विवरण देखें ›",
      for_officials: "अधिकारियों और नियंत्रण कक्ष के लिए ›",
      last_checked_prefix: "अंतिम जांच:",
      just_now: "अभी-अभी",
      min_ago: "मिनट पहले",
      offline_warning: "⚡ ऑफलाइन मोड — अंतिम पुष्टि स्थिति दिखाई जा रही है",
      shelter_badge: "निकटतम चक्रवात आश्रय",
      call_1077: "📞 हेल्पलाइन 1077",
      call_112: "🚨 आपातकाल 112",
      call_108: "🚑 एम्बुलेंस 108",
      advisory_title: "आधिकारिक पूर्व-चेतावनी बुलेटिन",
      advanced_view: "नियंत्रण कक्ष कंसोल खोलें ›",
      select_loc_title: "अपना जिला चुनें",
      use_gps: "📍 वर्तमान जीपीएस स्थान का उपयोग करें",
      select_lang_title: "भाषा चुनें (Select Language)",
    },
    or: {
      action_btn: "ମୁଁ କ’ଣ କରିବା ଉଚିତ?",
      map_btn: "ମାନଚିତ୍ର ଏବଂ ବିବରଣୀ ଦେଖନ୍ତୁ ›",
      for_officials: "ଅଧିକାରୀ ଓ ନିୟନ୍ତ୍ରଣ କକ୍ଷ ପାଇଁ ›",
      last_checked_prefix: "ଶେଷ ଯାଞ୍ଚ:",
      just_now: "ଏବେ",
      min_ago: "ମିନିଟ୍ ପୂର୍ବରୁ",
      offline_warning: "⚡ ଅଫଲାଇନ୍ ମୋଡ୍ — ଶେଷ ସ୍ଥିତି ପ୍ରଦର୍ଶିତ ହେଉଛି",
      shelter_badge: "ନିକଟତମ ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳୀ",
      call_1077: "📞 ହେଲ୍ପଲାଇନ୍ ୧୦୭୭",
      call_112: "🚨 ଜରୁରୀକାଳୀନ ୧୧୨",
      call_108: "🚑 ଆମ୍ବୁଲାନ୍ସ ୧୦୮",
      advisory_title: "ସରକାରୀ ସତର୍କତା ବୁଲେଟିନ୍",
      advanced_view: "ନିୟନ୍ତ୍ରଣ କକ୍ଷ କନ୍ସୋଲ୍ ଖୋଲନ୍ତୁ ›",
      select_loc_title: "ଆପଣଙ୍କ ଜିଲ୍ଲା ଚୟନ କରନ୍ତୁ",
      use_gps: "📍 ବର୍ତ୍ତମାନର ଜିପିଏସ୍ ସ୍ଥାନ ବ୍ୟବହାର କରନ୍ତୁ",
      select_lang_title: "ଭାଷା ଚୟନ କରନ୍ତୁ (Select Language)",
    },
  },

  // District Coordinates for Map Focus
  DISTRICT_COORDS: {
    "South 24 Parganas": [88.20, 21.80],
    "Purba Medinipur": [87.80, 21.90],
    "North 24 Parganas": [88.55, 22.65],
    "Kolkata": [88.36, 22.57],
  },

  init() {
    this.bindEvents();
    this.updateChromeText();

    // Check if offline status cached
    const cached = localStorage.getItem("aegis_citizen_cached_status");
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        this.renderStatus(parsed, true);
      } catch (e) {
        console.warn("Cached status parse error", e);
      }
    }

    // Attempt geolocation or fetch default
    this.autoDetectLocation();
  },

  bindEvents() {
    // Top Bar Buttons
    document.getElementById("btn-lang-selector")?.addEventListener("click", () => this.openModal("modal-lang"));
    document.getElementById("btn-loc-selector")?.addEventListener("click", () => this.openModal("modal-loc"));

    // Language Options
    document.querySelectorAll(".lang-opt-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const lang = btn.dataset.lang;
        this.setLanguage(lang);
        this.closeModal("modal-lang");
      });
    });

    // District Options
    document.querySelectorAll(".loc-district-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const district = btn.dataset.district;
        this.setDistrict(district);
        this.closeModal("modal-loc");
      });
    });

    // GPS Detect Button
    document.getElementById("btn-use-gps")?.addEventListener("click", () => {
      this.closeModal("modal-loc");
      this.detectGPS();
    });

    // Progressive Disclosure Drawer
    document.getElementById("btn-action-drawer")?.addEventListener("click", () => {
      const drawer = document.getElementById("action-drawer");
      drawer.classList.toggle("open");
      if (drawer.classList.contains("open")) {
        drawer.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });

    // Map & Details Modal
    document.getElementById("btn-map-details")?.addEventListener("click", () => {
      this.openModal("modal-map");
      this.initMapIfNeeded();
    });

    // Modal Close Buttons
    document.querySelectorAll(".close-modal-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const modal = btn.closest(".modal-overlay");
        if (modal) modal.classList.remove("open");
      });
    });

    // Modal Background Click Closes
    document.querySelectorAll(".modal-overlay").forEach((modal) => {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.remove("open");
      });
    });
  },

  openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add("open");
  },

  closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove("open");
  },

  setLanguage(lang) {
    this.currentLang = lang;
    localStorage.setItem("aegis_citizen_lang", lang);
    this.updateChromeText();
    this.fetchStatus();
  },

  setDistrict(district) {
    this.currentDistrict = district;
    localStorage.setItem("aegis_citizen_district", district);
    this.fetchStatus();
  },

  updateChromeText() {
    const t = this.UI_I18N[this.currentLang] || this.UI_I18N.en;

    // Update Action Button Text
    const actBtn = document.getElementById("btn-action-drawer-text");
    if (actBtn) actBtn.textContent = t.action_btn;

    // Update Map Button Text
    const mapBtn = document.getElementById("btn-map-details-text");
    if (mapBtn) mapBtn.textContent = t.map_btn;

    // Update Officials Link
    const offLink = document.getElementById("officials-link");
    if (offLink) offLink.textContent = t.for_officials;

    // Language Chip Label
    const langNames = { en: "EN", bn: "বাংলা", hi: "हिन्दी", or: "ଓଡ଼ିଆ" };
    const langChip = document.getElementById("current-lang-label");
    if (langChip) langChip.textContent = langNames[this.currentLang] || "EN";

    // Call Button Labels
    const call1077 = document.getElementById("call-1077-label");
    if (call1077) call1077.textContent = t.call_1077;
    const call112 = document.getElementById("call-112-label");
    if (call112) call112.textContent = t.call_112;
    const call108 = document.getElementById("call-108-label");
    if (call108) call108.textContent = t.call_108;
  },

  autoDetectLocation() {
    // If user has not explicitly chosen a district, try GPS once
    if (!localStorage.getItem("aegis_citizen_district") && "geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this.fetchStatusWithCoords(pos.coords.latitude, pos.coords.longitude);
        },
        () => {
          this.fetchStatus();
        },
        { timeout: 5000 }
      );
    } else {
      this.fetchStatus();
    }
  },

  detectGPS() {
    if (!("geolocation" in navigator)) {
      alert("Geolocation is not supported by your browser");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.fetchStatusWithCoords(pos.coords.latitude, pos.coords.longitude);
      },
      (err) => {
        console.warn("GPS error", err);
        alert("Unable to acquire GPS position. Falling back to selected district.");
        this.fetchStatus();
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  },

  async fetchStatusWithCoords(lat, lon) {
    try {
      const url = `${API_BASE}/status?lat=${lat}&lon=${lon}&lang=${this.currentLang}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      this.currentDistrict = data.district;
      localStorage.setItem("aegis_citizen_district", data.district);
      this.renderStatus(data, false);
    } catch (err) {
      console.warn("Fetch with coords failed, trying standard fetch", err);
      this.fetchStatus();
    }
  },

  async fetchStatus() {
    const banner = document.getElementById("offline-banner");
    try {
      const url = `${API_BASE}/status?district=${encodeURIComponent(this.currentDistrict)}&lang=${this.currentLang}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (banner) banner.style.display = "none";
      localStorage.setItem("aegis_citizen_cached_status", JSON.stringify(data));
      this.renderStatus(data, false);
    } catch (err) {
      console.warn("Network fetch failed, attempting cached fallback", err);
      if (banner) banner.style.display = "block";
      const cached = localStorage.getItem("aegis_citizen_cached_status");
      if (cached) {
        this.renderStatus(JSON.parse(cached), true);
      }
    }
  },

  renderStatus(data, isOffline) {
    this.statusData = data;

    // 1. Update District Label in Chip
    const locLabel = document.getElementById("current-location-label");
    if (locLabel) locLabel.textContent = data.district;

    // 2. State & Styling Setup
    const appEl = document.getElementById("citizen-app-root");
    const stateKey = (data.state || "Safe").toLowerCase(); // safe, watch, warning, danger
    appEl.className = `citizen-app state-${stateKey}`;

    // Update CSS custom property tokens dynamically
    const colors = {
      safe: "#10b981",
      watch: "#f59e0b",
      warning: "#f97316",
      danger: "#ef4444",
    };
    const glows = {
      safe: "rgba(16, 185, 129, 0.35)",
      watch: "rgba(245, 158, 11, 0.35)",
      warning: "rgba(249, 115, 22, 0.4)",
      danger: "rgba(239, 68, 68, 0.55)",
    };
    const surfaces = {
      safe: "rgba(6, 78, 59, 0.4)",
      watch: "rgba(113, 63, 18, 0.4)",
      warning: "rgba(124, 45, 18, 0.45)",
      danger: "rgba(69, 10, 10, 0.6)",
    };
    const borders = {
      safe: "rgba(16, 185, 129, 0.4)",
      watch: "rgba(245, 158, 11, 0.4)",
      warning: "rgba(249, 115, 22, 0.5)",
      danger: "rgba(239, 68, 68, 0.6)",
    };

    document.documentElement.style.setProperty("--state-accent", colors[stateKey] || colors.safe);
    document.documentElement.style.setProperty("--state-glow", glows[stateKey] || glows.safe);
    document.documentElement.style.setProperty("--state-surface", surfaces[stateKey] || surfaces.safe);
    document.documentElement.style.setProperty("--state-border", borders[stateKey] || borders.safe);

    // 3. Status Icon SVG Replacement
    const iconContainer = document.getElementById("status-icon-svg-container");
    if (iconContainer) {
      iconContainer.innerHTML = this.getIconSvg(data.icon || "check");
    }

    // 4. Headline & Plain Message
    const headlineEl = document.getElementById("status-headline");
    if (headlineEl) headlineEl.textContent = data.headline;

    const messageEl = document.getElementById("status-message");
    if (messageEl) messageEl.textContent = data.plain_message;

    // 5. Last Checked Timestamp
    const lastCheckedEl = document.getElementById("last-checked-label");
    const t = this.UI_I18N[this.currentLang] || this.UI_I18N.en;
    if (lastCheckedEl) {
      lastCheckedEl.textContent = isOffline
        ? `${t.offline_warning}`
        : `${t.last_checked_prefix} ${t.just_now}`;
    }

    // 6. Action Drawer Content
    this.renderActionDrawer(data);

    // 7. Update Selected District Pill in Location Modal
    document.querySelectorAll(".loc-district-btn").forEach((btn) => {
      btn.classList.toggle("selected", btn.dataset.district === data.district);
    });

    // 8. Update Official Advisory in Map Modal
    const advTextEl = document.getElementById("official-advisory-text");
    if (advTextEl) {
      advTextEl.textContent = data.advisory_text || "Official advisory for this district is currently active in the control room.";
    }
  },

  getIconSvg(iconType) {
    switch (iconType) {
      case "siren":
        // Emergency siren / beacon icon
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="status-icon-svg">
          <path d="M12 2v3m-7.07 1.93l2.12 2.12m12.02-2.12l-2.12 2.12"/>
          <path d="M6 14a6 6 0 0 1 12 0v5H6v-5z"/>
          <path d="M4 19h16"/>
          <path d="M9 14h6"/>
        </svg>`;
      case "triangle":
        // Warning triangle icon
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="status-icon-svg">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>`;
      case "eye":
        // Alert / vigilance eye icon
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="status-icon-svg">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>`;
      case "check":
      default:
        // Shield checkmark / safe icon
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="status-icon-svg">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          <path d="m9 12 2 2 4-4"/>
        </svg>`;
    }
  },

  renderActionDrawer(data) {
    const listEl = document.getElementById("action-checklist");
    if (listEl && Array.isArray(data.actions)) {
      listEl.innerHTML = data.actions
        .map(
          (act) => `
        <li class="action-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="action-item-icon">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span>${act}</span>
        </li>`
        )
        .join("");
    }

    // Shelter Info
    const shelter = data.shelter_info || {};
    const nameEl = document.getElementById("shelter-name");
    if (nameEl) nameEl.textContent = shelter.name || "Designated Emergency Shelter";

    const distEl = document.getElementById("shelter-distance");
    if (distEl) distEl.textContent = shelter.distance_km ? `${shelter.distance_km} km` : "Nearby";

    const addrEl = document.getElementById("shelter-address");
    if (addrEl) addrEl.textContent = shelter.address || `${data.district} Sector`;

    const capEl = document.getElementById("shelter-capacity");
    if (capEl) capEl.textContent = shelter.capacity ? `Capacity: ~${shelter.capacity.toLocaleString()} evacuees` : "Government verified shelter";
  },

  initMapIfNeeded() {
    if (this.mapInitialized) {
      if (this.mapInstance) {
        this.mapInstance.resize();
        this.focusDistrictOnMap();
      }
      return;
    }

    // Check if MapLibre is available on window
    if (!window.maplibregl) {
      console.warn("MapLibre GL not yet loaded");
      return;
    }

    const container = document.getElementById("simple-map-container");
    if (!container) return;

    const coords = this.DISTRICT_COORDS[this.currentDistrict] || [88.20, 21.80];

    try {
      this.mapInstance = new maplibregl.Map({
        container: "simple-map-container",
        style: {
          version: 8,
          sources: {
            "osm-tiles": {
              type: "raster",
              tiles: [
                "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
                "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
              ],
              tileSize: 256,
              attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
            },
          },
          layers: [
            {
              id: "osm-tiles-layer",
              type: "raster",
              source: "osm-tiles",
              minzoom: 0,
              maxzoom: 19,
            },
          ],
        },
        center: coords,
        zoom: 9.2,
      });

      this.mapInstance.on("load", async () => {
        this.mapInitialized = true;
        this.loadFloodLayer();
        this.addMapPins();
      });
    } catch (e) {
      console.error("Map initialization failed", e);
    }
  },

  async loadFloodLayer() {
    if (!this.mapInstance) return;
    try {
      const hazardUrl = `${API_BASE}/scenarios/amphan-2020-t-72h/hazard?t=0&threshold=0.3`;
      const res = await fetch(hazardUrl);
      if (!res.ok) return;
      const geojson = await res.json();

      if (!this.mapInstance.getSource("flood-source")) {
        this.mapInstance.addSource("flood-source", {
          type: "geojson",
          data: geojson,
        });

        this.mapInstance.addLayer({
          id: "flood-layer-fill",
          type: "fill",
          source: "flood-source",
          paint: {
            "fill-color": "#ef4444",
            "fill-opacity": 0.45,
          },
        });

        this.mapInstance.addLayer({
          id: "flood-layer-line",
          type: "line",
          source: "flood-source",
          paint: {
            "line-color": "#dc2626",
            "line-width": 1.5,
          },
        });
      }
    } catch (err) {
      console.warn("Could not load flood layer on simple map", err);
    }
  },

  addMapPins() {
    if (!this.mapInstance) return;
    const coords = this.DISTRICT_COORDS[this.currentDistrict] || [88.20, 21.80];

    // User Location Marker
    const userEl = document.createElement("div");
    userEl.className = "legend-swatch-pin";
    userEl.style.width = "16px";
    userEl.style.height = "16px";
    userEl.style.boxShadow = "0 0 10px #38bdf8";

    new maplibregl.Marker({ element: userEl })
      .setLngLat(coords)
      .setPopup(new maplibregl.Popup({ offset: 12 }).setText("Your Location"))
      .addTo(this.mapInstance);

    // Shelter Marker (slightly offset)
    const shelterCoords = [coords[0] + 0.015, coords[1] + 0.012];
    const shelterEl = document.createElement("div");
    shelterEl.innerHTML = "🏛️";
    shelterEl.style.fontSize = "22px";
    shelterEl.style.cursor = "pointer";

    new maplibregl.Marker({ element: shelterEl })
      .setLngLat(shelterCoords)
      .setPopup(new maplibregl.Popup({ offset: 12 }).setText(this.statusData?.shelter_info?.name || "Emergency Shelter"))
      .addTo(this.mapInstance);
  },

  focusDistrictOnMap() {
    if (!this.mapInstance) return;
    const coords = this.DISTRICT_COORDS[this.currentDistrict] || [88.20, 21.80];
    this.mapInstance.flyTo({ center: coords, zoom: 9.5, essential: true });
  },
};

// Auto-run on DOM ready
document.addEventListener("DOMContentLoaded", () => CitizenApp.init());
