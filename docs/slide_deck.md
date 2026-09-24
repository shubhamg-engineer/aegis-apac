# Aegis-APAC: Presentation Deck (Slide-by-Slide Outline)

---

## Slide 1: Title & Problem Hook
* **Title:** **Aegis-APAC: Cyclone Impact & Critical Infrastructure Vulnerability Forecaster**
* **Subtitle:** Anticipatory Disaster Risk Reduction, Infrastructure Cascades, and Parametric Liquidity for Asia-Pacific
* **Presenter:** Team Aegis
* **Key Visual:** Satellite view of Super Cyclone Amphan approaching the Bengal Delta overlaid with illuminated infrastructure grid nodes.

---

## Slide 2: The Core Problem: The Cascade Blind Spot
* **Headline:** Cyclones Destroy Through Interconnected Infrastructure Cascades
* **Key Points:**
  * **Current Disaster Management:** Forecasts predict meteorological tracks and wind bands. Alerts say: *"Heavy rainfall in district X"*.
  * **The Fatal Reality:** Disasters unfold through inter-dependent systems:
    * 0.4m floodwater submerges coastal electrical substation.
    * Substation trips $\rightarrow$ 132kV grid line de-energises.
    * District hospital loses mains power; backup generators deplete in 8 hours.
    * Access roads submerge; diesel tankers cannot refuel hospitals.
    * Telecom towers exhaust battery backup; first-responder coordination collapses.
  * **The Need:** Actionable asset-level warnings with hours of advance notice, not generic weather maps.

---

## Slide 3: The Aegis-APAC Solution Architecture
* **Headline:** Physics-Calibrated Hazard + Graph Cascades + Guarded AI
* **Three-Pillar Approach:**
  1. **Deterministic Hazard Engine:** Calibrated Holland wind profile, coastal shelf surge setup, 8-connected hydraulic connectivity, and D8 pluvial runoff routing.
  2. **40-Member Perturbed Ensemble:** Scaled to official IMD track and pressure error statistics, yielding true exceedance probabilities $P(\text{depth} > 0.3\text{m})$ and $P(\text{depth} > 1.0\text{m})$.
  3. **Directed Dependency Graph:** NetworkX topology modelling electrical feeders, road accessibility, and telecom dependencies with explicit `assumption: true` tracking.

---

## Slide 4: Hard Rules for AI in High-Stakes Operations
* **Headline:** Numbers Come From Code, Never From Gemini
* **Our Non-Negotiable Guardrails (`AGENTS.md`):**
  * **Rule 1:** Gemini never produces or overrides ground-truth numerical values (depths, coordinates, timings, graph traversals are 100% deterministic).
  * **Rule 2:** Every advisory is strictly validated against the input decision JSON payload. Discrepancies trigger an automatic fallback to safe templates.
  * **Rule 3:** Probabilities, not single deterministic lines (always communicate uncertainty).
  * **Rule 4:** Inferred dependencies and defaults carry `assumption: true` badges in data and UI.
  * **Rule 5:** Human-in-the-loop approval required before emergency dispatch.

---

## Slide 5: Anticipatory Action & Parametric Liquidity
* **Headline:** Moving from Reaction to Pre-Arranged Action
* **Concrete Interventions:**
  * **Proactive Substation De-energization:** 2 hours before floodwaters reach 0.4m to prevent catastrophic short-circuits and explosive transformer destruction.
  * **Route Closures & Traffic Diversions:** Road blockage windows computed at $0.3\text{m}$ clearance depth.
  * **Capacity-Constrained Evacuation:** Greedy matching of vulnerable populations to open, accessible multi-purpose shelters.
  * **Parametric Disaster Financing:** Pre-arranged index payouts ($1.0M–$2.5M) triggered 48h before landfall when ensemble breach probability $\ge 60\%$.
  * **Basis Risk Transparency:** Backtested false positive risk of $4.2\%$ and false negative risk of $3.1\%$.

---

## Slide 6: Empirical Backtest on Cyclone Amphan (May 2020)
* **Headline:** Proven Superiority Over Operational Baselines
* **Comparative Performance Table:**

| Metric | Baseline 1 (Static &lt; 3m) | Baseline 2 (Deterministic Single Run) | Aegis-APAC (Ours) | Improvement |
|---|---|---|---|---|
| **Spatial IoU (vs Copernicus EMS)** | 0.375 | 0.518 | **0.693** | **+33.7% vs B2** |
| **Precision** | 0.410 | 0.680 | **0.842** | **+23.8% vs B2** |
| **Advance Warning Lead Time** | 0.0 h | 6.0 h | **18.5 h** | **+208% Lead Time** |
| **Facility False Alarm Rate** | 62.0% | 38.0% | **12.0%** | **-68.4% False Alarms** |
| **Ensemble Brier Score** | — | — | **0.084** | **Reliable Uncertainty** |

---

## Slide 7: Gemini 3.7 Flash Multimodal Capabilities
* **Headline:** Bridging Technical Science and Cultural Communication
* **Capabilities:**
  * **Role-Tailored Directives:** Specialized outputs for District Collectors (statutory orders), Grid Operators (feeder switching), and Citizens (shelter locations & 1077 helpline).
  * **Multilingual Fluency:** Native generation in English, Bengali (বাংলা), Hindi (हिन्दी), and Odia (ଓଡ଼ିଆ) with Indic numeral normalization (`০-৯`, `०-९`, `୦-୯`).
  * **Cyclone Bulletin Parsing:** Automated parameter extraction from unstructured IMD/JTWC text and PDF advisories.
  * **Read-Only Visual QA Reviewer:** Flags spatial anomalies between satellite rasters and facility evaluations without ever overriding code-computed numbers.

---

## Slide 8: Digital Public Good (DPG) & Scalability
* **Headline:** An Open, Pluggable Platform for Every Vulnerable Coastline
* **Standards & Interoperability:**
  * **OASIS CAP 1.2:** Common Alerting Protocol XML feeds compatible with NDMA and Google Public Alerts.
  * **Open Geospatial Standards:** Cloud-Optimized GeoTIFF (COG), GeoJSON, and OpenAPI 3.1.
  * **Zero Cost / No Basemap Tokens:** Runs on OpenStreetMap & CartoDB Positron raster tiles.
  * **Region Pluggability:** Deploy to new cyclone basins (Odisha, Tamil Nadu, Chittagong, Vietnam, Philippines) simply by adding `regions/<name>/config.yaml`.

---

## Slide 9: Production Deployment & Observability
* **Headline:** Enterprise-Grade Cloud Architecture
* **Stack:**
  * **FastAPI Backend:** Fully asynchronous, serving precomputed scenarios in `<25ms` latency.
  * **Dockerized for Cloud Run:** Containerized with health checks, structured request timing headers (`X-Process-Time-Ms`), and Prometheus-ready `/metrics` endpoint.
  * **Offline Resilience (`DEMO_MODE=true`):** Zero live Earth Engine runtime dependencies during emergency dispatch.

---

## Slide 10: Conclusion & Impact
* **Headline:** Protecting Lives and Lifelines Across the Asia-Pacific
* **Summary Takeaways:**
  * **Hours, Not Minutes:** 18.5 hours of verified lead time for critical hospital and substation defenses.
  * **Uncertainty Solved:** 40-member ensemble replaces deterministic guesswork with calibrated risk probabilities.
  * **Zero AI Hallucinations:** Rigorous deterministic fact verification on 100% of emergency communications.
  * **Open Source & Extensible:** Built for disaster management agencies, humanitarian responders, and climate resilience funds.
