/**
 * Aegis-APAC Operational Dashboard
 * ──────────────────────────────────────────────────────────────────────────
 * Architecture:
 *   ApiClient  ─ singleton, handles retry / dedup / abort / response cache
 *   AppState   ─ single source of truth; .set() triggers reactive renders
 *   Renderer   ─ pure functions: state → DOM (no side-effects on data)
 *   MapEngine  ─ MapLibre wrapper; GeoJSON sources reused, never recreated
 * ──────────────────────────────────────────────────────────────────────────
 */

"use strict";

// ═══════════════════════════════════════════════════════════════════════════
// 0. CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════

const API_BASE      = window.__API_BASE || window.location.origin;
const SCENARIO_ID   = "amphan-2020-t-72h";
const ADMIN_TOKEN   = "aegis_hackathon_demo_secret_token_2026";

const ROLE_LABELS = {
  collector:      "District Collector / DDMA",
  power_operator: "Grid Dispatcher (State Utility)",
  citizens:       "Public Safety Bulletin",
};

const TYPE_COLORS = {
  hospital:      "#10b981",
  substation:    "#ef4444",
  shelter:       "#3b82f6",
  bridge:        "#f59e0b",
  road:          "#8b5cf6",
  road_segment:  "#8b5cf6",
  telecom_tower: "#a78bfa",
  school:        "#fb923c",
  police:        "#facc15",
  fire_station:  "#f43f5e",
};

// ═══════════════════════════════════════════════════════════════════════════
// 1. API CLIENT  — retry, dedup, abort, TTL cache
// ═══════════════════════════════════════════════════════════════════════════

const ApiClient = (() => {
  const _cache    = new Map();   // url → { data, ts }
  const _inflight = new Map();   // url → Promise
  const TTL_MS    = 30_000;      // 30 s cache

  async function _fetchWithRetry(url, opts = {}, maxRetries = 3) {
    let lastErr;
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const res = await fetch(url, opts);
        if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
        return res;
      } catch (err) {
        lastErr = err;
        if (err.name === "AbortError") throw err;            // don't retry
        if (attempt < maxRetries - 1) {
          await new Promise(r => setTimeout(r, 300 * (attempt + 1)));
        }
      }
    }
    throw lastErr;
  }

  async function get(path, { ttl = TTL_MS, signal } = {}) {
    const url = API_BASE + path;
    const now  = Date.now();

    // Cache hit
    const cached = _cache.get(url);
    if (cached && (now - cached.ts) < ttl) return cached.data;

    // In-flight dedup
    if (_inflight.has(url)) return _inflight.get(url);

    const promise = _fetchWithRetry(url, { signal })
      .then(r => r.json())
      .then(data => {
        _cache.set(url, { data, ts: Date.now() });
        _inflight.delete(url);
        return data;
      })
      .catch(err => {
        _inflight.delete(url);
        throw err;
      });

    _inflight.set(url, promise);
    return promise;
  }

  async function post(path, body, { headers = {} } = {}) {
    const url = API_BASE + path;
    const res = await _fetchWithRetry(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${ADMIN_TOKEN}`,
        ...headers,
      },
      body: JSON.stringify(body),
    });
    return res.json();
  }

  async function getText(path) {
    const url = API_BASE + path;
    const res = await _fetchWithRetry(url);
    return res.text();
  }

  function invalidate(path) {
    _cache.delete(API_BASE + path);
  }

  return { get, post, getText, invalidate };
})();

// ═══════════════════════════════════════════════════════════════════════════
// 2. APP STATE  — single source of truth, subscriber-based reactivity
// ═══════════════════════════════════════════════════════════════════════════

const AppState = (() => {
  const _state = {
    // Server
    health:        null,
    metrics:       null,
    // Scenario
    scenario:      null,
    // Map
    timeStep:      0,
    layers: {
      "flood-03":  true,
      "flood-10":  true,
      "pathways":  true,
      "facilities": true,
    },
    // Data
    facilities:    [],
    actions:       [],
    advisories:    [],
    parametric:    [],
    backtest:      null,
    // UI
    activeTab:     "cascade",
    activeRole:    "collector",
    activeLang:    "en",
    selectedFacilityId: null,
    cascadeData:   null,
    // Advisory workflow
    currentAdvisoryId: null,
    // Loading / error
    loading:       new Set(),
    errors:        new Map(),
  };

  const _subscribers = new Map();

  function get(key) { return _state[key]; }

  function set(key, value) {
    _state[key] = value;
    const subs = _subscribers.get(key) || [];
    subs.forEach(fn => fn(value, _state));
    // Also notify "*" (global listeners)
    (_subscribers.get("*") || []).forEach(fn => fn(key, value, _state));
  }

  function on(key, fn) {
    if (!_subscribers.has(key)) _subscribers.set(key, []);
    _subscribers.get(key).push(fn);
    return () => {          // return unsubscribe handle
      const arr = _subscribers.get(key);
      const i = arr.indexOf(fn);
      if (i !== -1) arr.splice(i, 1);
    };
  }

  function startLoading(key) {
    const s = new Set(_state.loading);
    s.add(key);
    set("loading", s);
  }

  function stopLoading(key) {
    const s = new Set(_state.loading);
    s.delete(key);
    set("loading", s);
  }

  function setError(key, err) {
    const m = new Map(_state.errors);
    m.set(key, err);
    set("errors", m);
    console.error(`[Aegis] ${key}:`, err);
  }

  function clearError(key) {
    const m = new Map(_state.errors);
    m.delete(key);
    set("errors", m);
  }

  return { get, set, on, startLoading, stopLoading, setError, clearError };
})();

// ═══════════════════════════════════════════════════════════════════════════
// 3. MAP ENGINE  — MapLibre wrapper; sources are created once, then updated
// ═══════════════════════════════════════════════════════════════════════════

const MapEngine = (() => {
  let _map = null;
  let _markers = {};

  function init() {
    _map = new maplibregl.Map({
      container: "map",
      style: "https://tiles.stadiamaps.com/styles/alidade_smooth_dark.json",
      center: [88.15, 21.75],
      zoom: 9.8,
      pitch: 20,
      attributionControl: false,
    });

    _map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    _map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    _map.on("load", () => {
      _addHazardSources();
      _addPathwaySource();
      DataLoader.loadHazardLayers();
      DataLoader.loadPathways();
      DataLoader.loadFacilities();
    });

    return _map;
  }

  function _addHazardSources() {
    _map.addSource("hazard-source", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });

    // P(depth > 0.3m) — amber  [API uses 'prob' not 'probability']
    _map.addLayer({
      id: "hazard-flood-03",
      type: "fill",
      source: "hazard-source",
      filter: ["==", ["get", "threshold_m"], 0.3],
      paint: {
        "fill-color": [
          "interpolate", ["linear"], ["get", "prob"],
          0.0, "rgba(249,115,22,0.0)",
          0.3, "rgba(249,115,22,0.20)",
          0.6, "rgba(249,115,22,0.50)",
          1.0, "rgba(249,115,22,0.72)",
        ],
        "fill-outline-color": "rgba(234,88,12,0.4)",
      },
    });

    // P(depth > 1.0m) — red
    _map.addLayer({
      id: "hazard-flood-10",
      type: "fill",
      source: "hazard-source",
      filter: ["==", ["get", "threshold_m"], 1.0],
      paint: {
        "fill-color": [
          "interpolate", ["linear"], ["get", "prob"],
          0.0, "rgba(239,68,68,0.0)",
          0.3, "rgba(239,68,68,0.28)",
          0.6, "rgba(239,68,68,0.58)",
          1.0, "rgba(239,68,68,0.82)",
        ],
        "fill-outline-color": "rgba(220,38,38,0.5)",
      },
    });
  }

  function _addPathwaySource() {
    _map.addSource("pathways-source", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });

    _map.addLayer({
      id: "pathways-layer",
      type: "line",
      source: "pathways-source",
      paint: {
        "line-color": "#06b6d4",
        "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1.5, 12, 3],
        "line-dasharray": [2, 1],
        "line-opacity": 0.85,
      },
    });
  }

  function updateHazardData(geojson) {
    if (!_map || !_map.getSource("hazard-source")) return;
    _map.getSource("hazard-source").setData(geojson);
  }

  function updatePathwayData(geojson) {
    if (!_map || !_map.getSource("pathways-source")) return;
    _map.getSource("pathways-source").setData(geojson);
  }

  function setLayerVisibility(layerId, visible) {
    if (!_map || !_map.getLayer(layerId)) return;
    _map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
  }

  function setMarkersVisibility(visible) {
    Object.values(_markers).forEach(m => {
      m.getElement().style.display = visible ? "block" : "none";
    });
  }

  function placeMarkers(facilities) {
    // Remove stale markers
    Object.values(_markers).forEach(m => m.remove());
    _markers = {};

    facilities.forEach(facility => {
      let coords;
      if (facility.geometry.type === "Point") {
        coords = facility.geometry.coordinates;
      } else if (facility.geometry.type === "LineString") {
        const pts = facility.geometry.coordinates;
        const mid = Math.floor(pts.length / 2);
        coords = pts[mid] || pts[0];
      } else {
        return;
      }

      const color = TYPE_COLORS[facility.type] || "#facc15";
      const el = document.createElement("div");
      el.className = "facility-marker";
      el.setAttribute("data-type", facility.type);
      el.style.cssText = `
        width:20px;height:20px;border-radius:50%;
        background:${color};border:2px solid rgba(255,255,255,0.85);
        cursor:pointer;box-shadow:0 0 0 0 ${color};
        animation:markerPulse 2.5s ease-out infinite;
        transition:transform 0.15s;
      `;
      el.title = facility.name;

      el.addEventListener("click", () => {
        AppState.set("selectedFacilityId", facility.id);
        AppState.set("activeTab", "cascade");
        Renderer.renderTabs();
        DataLoader.loadCascade(facility.id);
      });

      el.addEventListener("mouseenter", () => { el.style.transform = "scale(1.4)"; });
      el.addEventListener("mouseleave", () => { el.style.transform = "scale(1)"; });

      const riskPct = facility.failure_probability != null
        ? Math.round(facility.failure_probability * 100) + "%"
        : "—";
      const riskColor = (facility.failure_probability || 0) > 0.6 ? "#ef4444"
                      : (facility.failure_probability || 0) > 0.3 ? "#f97316" : "#22c55e";

      const popup = new maplibregl.Popup({ offset: 20, closeButton: false, maxWidth: "220px" })
        .setHTML(`
          <div style="font-family:Inter,sans-serif;">
            <div style="font-weight:700;font-size:12px;color:#e2e8f0;margin-bottom:4px">${facility.name}</div>
            <div style="font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:#94a3b8;margin-bottom:8px">${facility.type.replace(/_/g,' ')}</div>
            <div style="display:flex;justify-content:space-between;margin-bottom:3px">
              <span style="font-size:11px;color:#94a3b8">Failure risk</span>
              <span style="font-size:11px;font-weight:700;color:${riskColor}">${riskPct}</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
              <span style="font-size:11px;color:#94a3b8">Elevation</span>
              <span style="font-size:11px;color:#e2e8f0">${facility.elevation_m} m asl</span>
            </div>
            <div style="margin-top:8px;font-size:10.5px;color:#38bdf8;cursor:pointer;text-align:center" onclick="AppState.set('selectedFacilityId','${facility.id}');AppState.set('activeTab','cascade');Renderer.renderTabs();DataLoader.loadCascade('${facility.id}')">Inspect cascade →</div>
          </div>
        `);

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat(coords)
        .setPopup(popup)
        .addTo(_map);

      _markers[facility.id] = marker;
    });
  }

  function getMap() { return _map; }

  return { init, getMap, updateHazardData, updatePathwayData, setLayerVisibility, setMarkersVisibility, placeMarkers };
})();

// ═══════════════════════════════════════════════════════════════════════════
// 4. DATA LOADER  — all API calls; writes only to AppState
// ═══════════════════════════════════════════════════════════════════════════

const DataLoader = (() => {
  let _hazardAbort = null;
  let _hazardDebounce = null;

  async function loadHealth() {
    AppState.startLoading("health");
    try {
      const data = await ApiClient.get("/health", { ttl: 10_000 });
      AppState.set("health", data);
      AppState.clearError("health");
    } catch (err) {
      AppState.setError("health", err);
    } finally {
      AppState.stopLoading("health");
    }
  }

  async function loadMetrics() {
    try {
      const data = await ApiClient.get("/metrics", { ttl: 5_000 });
      AppState.set("metrics", data);
    } catch (_) { /* non-critical */ }
  }

  async function loadHazardLayers() {
    // Debounce rapid time-step changes
    clearTimeout(_hazardDebounce);
    _hazardDebounce = setTimeout(async () => {
      if (_hazardAbort) _hazardAbort.abort();
      _hazardAbort = new AbortController();

      const t = AppState.get("timeStep");
      AppState.startLoading("hazard");
      try {
        const data = await ApiClient.get(
          `/scenarios/${SCENARIO_ID}/hazard?t=${t}`,
          { ttl: 60_000, signal: _hazardAbort.signal }
        );
        MapEngine.updateHazardData(data);
        AppState.clearError("hazard");
      } catch (err) {
        if (err.name !== "AbortError") AppState.setError("hazard", err);
      } finally {
        AppState.stopLoading("hazard");
      }
    }, 250);
  }

  async function loadPathways() {
    try {
      const data = await ApiClient.get(`/scenarios/${SCENARIO_ID}/pathways`, { ttl: 300_000 });
      MapEngine.updatePathwayData(data);
    } catch (err) {
      AppState.setError("pathways", err);
    }
  }

  async function loadFacilities() {
    AppState.startLoading("facilities");
    try {
      const data = await ApiClient.get(`/scenarios/${SCENARIO_ID}/facilities`, { ttl: 300_000 });
      AppState.set("facilities", data);
      MapEngine.placeMarkers(data);
      // Auto-select the critical substation on first load
      const defaultId = "osm:substation:sagar";
      AppState.set("selectedFacilityId", defaultId);
      await loadCascade(defaultId);
      AppState.clearError("facilities");
    } catch (err) {
      AppState.setError("facilities", err);
    } finally {
      AppState.stopLoading("facilities");
    }
  }

  async function loadCascade(facilityId) {
    AppState.startLoading("cascade");
    AppState.set("cascadeData", null);
    try {
      const data = await ApiClient.get(`/facilities/${encodeURIComponent(facilityId)}/cascade`);
      AppState.set("cascadeData", data);
      AppState.clearError("cascade");
    } catch (err) {
      AppState.setError("cascade", err);
    } finally {
      AppState.stopLoading("cascade");
    }
  }

  async function loadActions() {
    AppState.startLoading("actions");
    try {
      const data = await ApiClient.get(`/scenarios/${SCENARIO_ID}/actions`, { ttl: 300_000 });
      AppState.set("actions", data);
      AppState.clearError("actions");
    } catch (err) {
      AppState.setError("actions", err);
    } finally {
      AppState.stopLoading("actions");
    }
  }

  async function loadAdvisories() {
    AppState.startLoading("advisories");
    try {
      const data = await ApiClient.get(
        `/advisories?scenario_id=${SCENARIO_ID}`,
        { ttl: 15_000 }
      );
      AppState.set("advisories", data);
      AppState.clearError("advisories");
    } catch (err) {
      AppState.setError("advisories", err);
    } finally {
      AppState.stopLoading("advisories");
    }
  }

  async function loadParametric() {
    AppState.startLoading("parametric");
    try {
      const data = await ApiClient.get(`/scenarios/${SCENARIO_ID}/parametric`, { ttl: 120_000 });
      AppState.set("parametric", data);
      AppState.clearError("parametric");
    } catch (err) {
      AppState.setError("parametric", err);
    } finally {
      AppState.stopLoading("parametric");
    }
  }

  async function loadBacktest() {
    AppState.startLoading("backtest");
    try {
      const data = await ApiClient.get(`/backtest/amphan-2020/metrics`, { ttl: 300_000 });
      AppState.set("backtest", data);
      AppState.clearError("backtest");
    } catch (err) {
      AppState.setError("backtest", err);
    } finally {
      AppState.stopLoading("backtest");
    }
  }

  async function approveAdvisory(advisoryId, operatorName) {
    const url = `/advisories/${encodeURIComponent(advisoryId)}/approve?operator_name=${encodeURIComponent(operatorName)}`;
    const updated = await ApiClient.post(url, {});
    // Patch local advisory cache
    ApiClient.invalidate(`/advisories?scenario_id=${SCENARIO_ID}`);
    const current = AppState.get("advisories");
    const idx = current.findIndex(a => a.id === updated.id);
    if (idx !== -1) {
      const next = [...current];
      next[idx] = updated;
      AppState.set("advisories", next);
    }
    return updated;
  }

  async function fetchCAPXml(advisoryId) {
    return ApiClient.getText(`/advisories/${encodeURIComponent(advisoryId)}/cap`);
  }

  return {
    loadHealth, loadMetrics, loadHazardLayers, loadPathways,
    loadFacilities, loadCascade, loadActions, loadAdvisories,
    loadParametric, loadBacktest, approveAdvisory, fetchCAPXml,
  };
})();

// ═══════════════════════════════════════════════════════════════════════════
// 5. RENDERER  — pure DOM mutations driven by AppState
// ═══════════════════════════════════════════════════════════════════════════

const Renderer = (() => {

  // ── 5a. Header & System Status ──────────────────────────────────────────
  function renderHealth(health) {
    const el   = document.getElementById("system-status");
    const dot  = document.getElementById("status-dot");
    if (!el) return;
    if (!health) {
      el.textContent = "Connecting…";
      el.style.color = "#94a3b8";
      return;
    }
    const ok = health.status === "healthy";
    el.textContent = ok ? "System Healthy" : "System Degraded";
    el.style.color = ok ? "#34d399" : "#f97316";
    if (dot) dot.style.background = ok ? "#34d399" : "#f97316";

    const scenEl = document.getElementById("scenario-badge-text");
    if (scenEl && health.region) {
      scenEl.textContent = `Amphan (2020) · ${health.region.replace("_", " ").toUpperCase()} · T-72h Ensemble`;
    }

    const modeEl = document.getElementById("demo-mode-tag");
    if (modeEl) modeEl.style.display = health.demo_mode ? "inline-flex" : "none";

    const apiKeyEl = document.getElementById("gemini-status");
    if (apiKeyEl) {
      const geminiOk = health.components?.gemini_api === "configured";
      apiKeyEl.textContent = geminiOk ? "Gemini ✓" : "Template Mode";
      apiKeyEl.style.color = geminiOk ? "#34d399" : "#f59e0b";
    }
  }

  function renderMetrics(metrics) {
    if (!metrics) return;
    _setText("metric-total-req",  metrics.total_requests);
    _setText("metric-p50",        `${metrics.latency_p50_ms} ms`);
    _setText("metric-p95",        `${metrics.latency_p95_ms} ms`);
    _setText("metric-5xx",        metrics.status_5xx);
  }

  // ── 5b. Cascade / Facility Inspector ────────────────────────────────────
  function renderCascade(cascadeData) {
    const container = document.getElementById("facility-detail");
    if (!container) return;

    if (!cascadeData) {
      container.innerHTML = `
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <p>Click a facility marker on the map to inspect its failure probability and cascade chain.</p>
        </div>`;
      return;
    }

    const { risk, nodes, cause_chain } = cascadeData;
    const facilityId = cascadeData.target_facility_id;
    const facility   = nodes.find(n => n.id === facilityId);
    const probPct    = Math.round(risk.failure_probability * 100);
    const barColor   = probPct > 70 ? "#ef4444" : probPct > 40 ? "#f97316" : "#10b981";
    const failTime   = risk.earliest_failure_time
      ? new Date(risk.earliest_failure_time).toUTCString().slice(17, 22) + " UTC"
      : "—";

    const chainHtml = (cause_chain || []).map((ev, i) => `
      <div class="chain-step">
        <div class="chain-num">${i + 1}</div>
        <div class="chain-body">
          <div class="chain-node">${ev.node}</div>
          <div class="chain-event">${ev.event.replace(/_/g, " ")} — ${Math.round(ev.probability * 100)}%</div>
          ${ev.assumption ? `<span class="assumption-badge">⚠ assumption: true (inferred dependency)</span>` : ""}
        </div>
      </div>`).join("") || `<div class="muted-text">No cascade propagation detected.</div>`;

    container.innerHTML = `
      <div class="facility-card">
        <div class="facility-header">
          <div>
            <div class="facility-title">${facility ? facility.name : facilityId}</div>
            <div class="facility-id">${facilityId}</div>
          </div>
          <span class="facility-type-badge" style="background:${barColor}22;color:${barColor};border-color:${barColor}44;">
            ${facility ? facility.type : ""}
          </span>
        </div>

        <div class="facility-metrics">
          <div class="metric-row">
            <span>Elevation</span>
            <strong>${facility ? facility.elevation_m : "—"} m asl</strong>
          </div>
          <div class="metric-row">
            <span>Failure Probability</span>
            <strong style="color:${barColor}">${probPct}%</strong>
          </div>
          <div class="prob-bar-bg">
            <div class="prob-bar-fill" style="width:${probPct}%;background:${barColor};box-shadow:0 0 6px ${barColor}88;"></div>
          </div>
          <div class="metric-row" style="margin-top:0.25rem">
            <span>Earliest Failure</span>
            <strong>${failTime}</strong>
          </div>
          <div class="metric-row">
            <span>Warning Lead Time</span>
            <strong style="color:var(--accent-cyan)">${risk.hours_of_warning} h</strong>
          </div>
        </div>
      </div>

      <div class="section-label">Cascade Failure Chain</div>
      <div class="chain-container">${chainHtml}</div>

      <div class="section-label" style="margin-top:1rem">Connected Infrastructure (${nodes.length})</div>
      <div class="nodes-grid">
        ${nodes.map(n => {
          const c = TYPE_COLORS[n.type] || "#94a3b8";
          return `<div class="node-chip" style="border-color:${c}33;color:${c};">
            <span class="node-dot" style="background:${c}"></span>${n.name || n.id}
          </div>`;
        }).join("")}
      </div>`;
  }

  // ── 5c. Actions ─────────────────────────────────────────────────────────
  function renderActions(actions) {
    const container = document.getElementById("actions-list");
    if (!container) return;
    if (!actions || actions.length === 0) {
      container.innerHTML = `<div class="empty-state"><p>No recommended actions loaded.</p></div>`;
      return;
    }

    const typeConfig = {
      evacuate:    { icon: "🚨", color: "#ef4444", label: "Evacuation Order" },
      close_road:  { icon: "🚧", color: "#f97316", label: "Road Closure" },
      deenergise:  { icon: "⚡", color: "#eab308", label: "Grid De-energise" },
      preposition: { icon: "📦", color: "#3b82f6", label: "Prepositioning" },
      shelter:     { icon: "🏠", color: "#10b981", label: "Shelter Activation" },
    };

    container.innerHTML = actions.map(action => {
      const cfg = typeConfig[action.type] || { icon: "📋", color: "#8b5cf6", label: action.type };
      const conf = Math.round(action.confidence * 100);
      const deadline = new Date(action.deadline).toLocaleString("en-IN", {
        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "UTC",
      }) + " UTC";

      return `
        <div class="action-card" style="--action-color:${cfg.color}">
          <div class="action-header">
            <div class="action-icon">${cfg.icon}</div>
            <div>
              <div class="action-label">${cfg.label}</div>
              <div class="action-target">${action.target_area || action.target || "Regional"}</div>
            </div>
            <div class="action-conf" style="color:${cfg.color}">${conf}%</div>
          </div>
          <div class="action-desc">${action.description}</div>
          <div class="action-deadline">⏱ Deadline: <strong>${deadline}</strong></div>
        </div>`;
    }).join("");
  }

  // ── 5d. Advisory & Approval ──────────────────────────────────────────────
  function renderAdvisory() {
    const advisories = AppState.get("advisories");
    const role       = AppState.get("activeRole");
    const lang       = AppState.get("activeLang");

    const adv = advisories.find(a => a.language === lang && a.role === role)
             || advisories.find(a => a.language === lang)
             || advisories.find(a => a.role === role)
             || advisories[0];

    if (!adv) return;
    AppState.set("currentAdvisoryId", adv.id);

    _setText("advisory-role-label", ROLE_LABELS[adv.role] || adv.role);
    _setText("advisory-body", adv.text);

    // Validation badge
    const valEl = document.getElementById("validation-detail");
    if (valEl && adv.validation) {
      valEl.textContent = adv.validation.passed
        ? `${adv.validation.checked_values || "All"} values validated — 0 hallucinations.`
        : `⚠ Failures: ${(adv.validation.failures || []).join(", ")}`;
      valEl.style.color = adv.validation.passed ? "#34d399" : "#ef4444";
    }

    // Approval button
    const btn = document.getElementById("approve-dispatch-btn");
    if (!btn) return;
    const isApproved = adv.status === "approved" || adv.status === "dispatched";
    const actor = adv.history?.[adv.history.length - 1]?.actor;

    btn.disabled = isApproved;
    btn.className = "approve-btn" + (isApproved ? " is-approved" : "");
    btn.innerHTML = isApproved
      ? `<span class="btn-icon">✓</span> Approved${actor ? ` by ${actor}` : ""}`
      : `<span class="btn-icon">✓</span> Authorize & Dispatch`;
  }

  // ── 5e. Parametric ──────────────────────────────────────────────────────
  function renderParametric(districtName) {
    const all  = AppState.get("parametric");
    const item = all.find(p => p.district.toLowerCase() === districtName.toLowerCase());

    if (!item) {
      _setText("parametric-prob",   "No data");
      _setText("parametric-payout", "No parametric data for this district");
      _setText("parametric-assumption", "");
      return;
    }

    const pct = Math.round(item.trigger_probability * 100);
    _setText("parametric-district-label", `${item.district} Geofence`);

    const probEl = document.getElementById("parametric-prob");
    if (probEl) {
      probEl.textContent  = `${pct}%`;
      probEl.style.color  = item.payout_triggered ? "#34d399" : "#94a3b8";
    }

    const payEl = document.getElementById("parametric-payout");
    if (payEl) {
      payEl.innerHTML = item.payout_triggered
        ? `Condition Met · <strong>$${Number(item.payout_amount_usd).toLocaleString()} Payout</strong>`
        : `Below Threshold (< 60%) · <strong>No Payout</strong>`;
    }

    const assEl = document.getElementById("parametric-assumption");
    if (assEl) assEl.textContent = `⚠ assumption: true · ${item.basis_risk || ""}`;
  }

  // ── 5f. Backtest ─────────────────────────────────────────────────────────
  function renderBacktest(data) {
    if (!data) return;
    const grid = document.getElementById("backtest-metrics-grid");
    if (grid) {
      const fm = data.flood_metrics || {};
      grid.innerHTML = [
        { label: "IoU (Jaccard)",  value: fm.iou,       color: "#38bdf8" },
        { label: "F1-Score",       value: fm.f1,        color: "#38bdf8" },
        { label: "Precision",      value: fm.precision, color: "#34d399" },
        { label: "Recall",         value: fm.recall,    color: "#34d399" },
      ].map(({ label, value, color }) => `
        <div class="metric-cell">
          <div class="metric-cell-val" style="color:${color}">${value != null ? value.toFixed(3) : "—"}</div>
          <div class="metric-cell-label">${label}</div>
        </div>`).join("");
    }

    const tableEl = document.getElementById("baseline-table-body");
    if (tableEl && data.baseline_comparison) {
      tableEl.innerHTML = data.baseline_comparison.map((b, i) => `
        <tr class="${i === 0 ? "row-highlight" : ""}">
          <td>${b.model}</td>
          <td>${b.lead_time_warning_hours}h</td>
          <td>${Math.round((b.facility_false_alarm_rate || 0) * 100)}%</td>
          <td>${b.precision != null ? Math.round(b.precision * 100) + "%" : "—"}</td>
          <td>${b.f1 != null ? b.f1.toFixed(3) : "—"}</td>
        </tr>`).join("");
    }
  }

  // ── 5g. Tabs ─────────────────────────────────────────────────────────────
  function renderTabs() {
    const active = AppState.get("activeTab");
    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.classList.toggle("is-active", btn.dataset.tab === active);
    });
    document.querySelectorAll(".tab-panel").forEach(panel => {
      panel.classList.toggle("is-active", panel.id === `tab-${active}`);
    });
  }

  // ── 5h. Parametric district selector ─────────────────────────────────────
  function initParametricSelect() {
    const sel = document.getElementById("parametric-district-select");
    if (sel) {
      sel.addEventListener("change", () => renderParametric(sel.value));
    }
  }

  // ── helpers ──────────────────────────────────────────────────────────────
  function _setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? "—";
  }

  return {
    renderHealth, renderMetrics, renderCascade, renderActions,
    renderAdvisory, renderParametric, renderBacktest, renderTabs,
    initParametricSelect,
  };
})();

// ═══════════════════════════════════════════════════════════════════════════
// 6. STATE → RENDERER SUBSCRIPTIONS
// ═══════════════════════════════════════════════════════════════════════════

AppState.on("health",       v => Renderer.renderHealth(v));
AppState.on("metrics",      v => Renderer.renderMetrics(v));
AppState.on("cascadeData",  v => Renderer.renderCascade(v));
AppState.on("actions",      v => Renderer.renderActions(v));
AppState.on("advisories",   ()  => Renderer.renderAdvisory());
AppState.on("activeRole",   ()  => Renderer.renderAdvisory());
AppState.on("activeLang",   ()  => Renderer.renderAdvisory());
AppState.on("parametric",   ()  => {
  const sel = document.getElementById("parametric-district-select");
  Renderer.renderParametric(sel ? sel.value : "South 24 Parganas");
});
AppState.on("backtest",     v => Renderer.renderBacktest(v));
AppState.on("activeTab",    ()  => Renderer.renderTabs());
AppState.on("layers",       layers => {
  MapEngine.setLayerVisibility("hazard-flood-03",  layers["flood-03"]);
  MapEngine.setLayerVisibility("hazard-flood-10",  layers["flood-10"]);
  MapEngine.setLayerVisibility("pathways-layer",   layers["pathways"]);
  MapEngine.setMarkersVisibility(layers["facilities"]);
});

// Loading state → visual indicator
AppState.on("loading", loading => {
  const spinner = document.getElementById("global-spinner");
  if (spinner) spinner.style.display = loading.size > 0 ? "flex" : "none";
});

// ═══════════════════════════════════════════════════════════════════════════
// 7. UI EVENT HANDLERS  — thin, delegate to AppState + DataLoader
// ═══════════════════════════════════════════════════════════════════════════

function setTimeStep(step) {
  AppState.set("timeStep", step);
  // Update active button appearance
  document.querySelectorAll(".time-btn[data-step]").forEach(btn => {
    btn.classList.toggle("is-active", Number(btn.dataset.step) === step);
  });
  const label = step === 0 ? "Landfall (T+0h)" : step < 0 ? `T${step}h Pre-Landfall` : `T+${step}h Post-Landfall`;
  _setText("time-display", label);
  DataLoader.loadHazardLayers();
}

function toggleLayer(layerKey, isVisible) {
  const current = AppState.get("layers");
  AppState.set("layers", { ...current, [layerKey]: isVisible });
}

function switchTab(tabId) {
  AppState.set("activeTab", tabId);
  if (tabId === "actions"    && !AppState.get("actions").length)      DataLoader.loadActions();
  if (tabId === "advisories" && !AppState.get("advisories").length)   DataLoader.loadAdvisories();
  if (tabId === "backtest"   && !AppState.get("backtest"))             DataLoader.loadBacktest();
}

function switchRole(role) {
  AppState.set("activeRole", role);
  document.querySelectorAll(".role-btn").forEach(btn =>
    btn.classList.toggle("is-active", btn.dataset.role === role));
}

function switchLang(lang) {
  AppState.set("activeLang", lang);
  document.querySelectorAll(".lang-btn").forEach(btn =>
    btn.classList.toggle("is-active", btn.dataset.lang === lang));
}

async function handleApproveAdvisory() {
  const btn = document.getElementById("approve-dispatch-btn");
  const advId = AppState.get("currentAdvisoryId");
  if (!advId || !btn) return;

  btn.disabled = true;
  btn.innerHTML = `<span class="btn-spinner"></span> Submitting…`;

  try {
    await DataLoader.approveAdvisory(advId, "StateControlRoom_Analyst");
    showToast("Advisory approved and queued for CAP 1.2 dispatch.", "success");
  } catch (err) {
    showToast("Authorization failed: " + err.message, "error");
    btn.disabled = false;
    btn.innerHTML = `<span class="btn-icon">✓</span> Authorize & Dispatch`;
  }
}

async function viewCAPModal() {
  const modal   = document.getElementById("cap-modal");
  const content = document.getElementById("cap-xml-content");
  const advId   = AppState.get("currentAdvisoryId");
  if (!modal || !content || !advId) return;

  modal.classList.add("is-open");
  content.textContent = "Fetching CAP 1.2 XML payload…";

  try {
    const xml = await DataLoader.fetchCAPXml(advId);
    content.textContent = xml;
  } catch (err) {
    content.textContent = "Error: " + err.message;
  }
}

function closeCAPModal() {
  document.getElementById("cap-modal")?.classList.remove("is-open");
}

// Click outside to close
document.addEventListener("click", e => {
  const modal = document.getElementById("cap-modal");
  if (modal && e.target === modal) closeCAPModal();
});

// ── Toast notifications ───────────────────────────────────────────────────

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container") || _createToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === "success" ? "✓" : type === "error" ? "✕" : "ℹ"}</span>
    <span>${message}</span>`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("toast-visible"));
  setTimeout(() => {
    toast.classList.remove("toast-visible");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
  }, 4000);
}

function _createToastContainer() {
  const div = document.createElement("div");
  div.id = "toast-container";
  document.body.appendChild(div);
  return div;
}

// ── Helper ───────────────────────────────────────────────────────────────

function _setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? "—";
}

// ═══════════════════════════════════════════════════════════════════════════
// 8. METRICS POLLING (every 30 s, low-priority)
// ═══════════════════════════════════════════════════════════════════════════

function _startMetricsPoll() {
  DataLoader.loadMetrics();
  setInterval(DataLoader.loadMetrics, 30_000);
}

// ═══════════════════════════════════════════════════════════════════════════
// 9. REGION SEARCH  — Nominatim geocoder, flies map to result
// ═══════════════════════════════════════════════════════════════════════════

let _searchDebounce = null;

async function onSearchInput(val) {
  const clearBtn = document.getElementById("search-clear-btn");
  const resultsEl = document.getElementById("search-results");

  if (clearBtn) clearBtn.style.display = val.length > 0 ? "block" : "none";

  clearTimeout(_searchDebounce);
  if (val.trim().length < 2) {
    resultsEl.style.display = "none";
    return;
  }

  _searchDebounce = setTimeout(async () => {
    try {
      // Bias search toward Bengal Delta region (viewbox: W,S,E,N)
      const url = `https://nominatim.openstreetmap.org/search?` +
        `q=${encodeURIComponent(val)}&format=json&limit=6&addressdetails=1` +
        `&viewbox=86.5,19.5,90.5,24.5&bounded=0`;
      const res = await fetch(url, { headers: { "Accept-Language": "en" } });
      const data = await res.json();
      _renderSearchResults(data, resultsEl);
    } catch (e) {
      resultsEl.innerHTML = `<div class="search-no-results">Search unavailable</div>`;
      resultsEl.style.display = "block";
    }
  }, 350);
}

function _renderSearchResults(data, el) {
  if (!data.length) {
    el.innerHTML = `<div class="search-no-results">No results found</div>`;
    el.style.display = "block";
    return;
  }
  el.innerHTML = data.map((r, i) => {
    const name = r.display_name.split(",").slice(0, 3).join(", ");
    const type = (r.type || r.class || "").replace(/_/g, " ");
    return `<div class="search-result-item" onclick="selectSearchResult(${r.lat},${r.lon},'${name.replace(/'/g,"\\'")}')">
      <span class="search-result-name">${name}</span>
      <span class="search-result-type">${type} · ${r.lat.substring ? parseFloat(r.lat).toFixed(3) : r.lat}°N, ${parseFloat(r.lon).toFixed(3)}°E</span>
    </div>`;
  }).join("");
  el.style.display = "block";
}

function selectSearchResult(lat, lon, name) {
  const map = MapEngine.getMap();
  if (map) {
    map.flyTo({ center: [parseFloat(lon), parseFloat(lat)], zoom: 12, speed: 1.4 });
  }
  document.getElementById("region-search").value = name;
  document.getElementById("search-results").style.display = "none";
  showToast(`📍 ${name}`, "success");
}

function clearSearch() {
  document.getElementById("region-search").value = "";
  document.getElementById("search-results").style.display = "none";
  document.getElementById("search-clear-btn").style.display = "none";
}

function onSearchKey(e) {
  if (e.key === "Escape") clearSearch();
}

// Close search dropdown when clicking outside
document.addEventListener("click", (e) => {
  if (!e.target.closest(".search-wrap")) {
    const el = document.getElementById("search-results");
    if (el) el.style.display = "none";
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// 9. BOOTSTRAP
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  // Initial UI state
  Renderer.initParametricSelect();
  Renderer.renderTabs();

  // Initialize map (triggers loadHazardLayers, loadPathways, loadFacilities internally)
  MapEngine.init();

  // Load non-map data in priority order
  DataLoader.loadHealth();
  DataLoader.loadAdvisories();
  DataLoader.loadActions();
  DataLoader.loadParametric();

  // Defer backtest (least critical, load during idle)
  if ("requestIdleCallback" in window) {
    requestIdleCallback(() => DataLoader.loadBacktest(), { timeout: 5000 });
  } else {
    setTimeout(DataLoader.loadBacktest, 2000);
  }

  _startMetricsPoll();
});
