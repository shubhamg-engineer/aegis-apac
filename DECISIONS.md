# Aegis-APAC: Architectural Decisions & Assumptions Log (DECISIONS.md)

This log documents foundational choices, data sources, assumptions, and known physical/computational limitations for Aegis-APAC.

---

## 1. Pilot Region and Storm Selection (Phase 0)

* **Decision:**
  * **Primary Backtest Storm:** **Cyclone Amphan (May 2020)**.
  * **Pilot Region:** **Bengal Delta / Sundarbans Coastal Region** (ID: `bengal_delta`, West Bengal / Odisha border, India).
  * **Secondary Out-of-Sample Validation Storm:** **Cyclone Dana (October 2024, Odisha)**.
* **Rationale:**
  * Cyclone Amphan was a Category 5-equivalent Super Cyclonic Storm with a devastating storm surge (2–5 m) across the Sundarbans and South 24 Parganas.
  * Extensively documented track and central pressure data exist in IBTrACS (IMD and JTWC records).
  * High-quality post-event flood extent products are available from Copernicus EMS (EMSR439) and ISRO Bhuvan for precision/recall/IoU benchmarking.
  * OpenStreetMap coverage in this coastal corridor contains well-mapped substations, primary roads (NH-12, SH-1), designated multi-purpose cyclone shelters, and district hospitals.
  * Real-world cascade failures were widely observed (flooded substations caused power blackouts, draining hospital backup fuel and collapsing mobile communication networks).

---

## 2. Area of Interest (AOI) Geofence

* **Bounding Box (EPSG:4326):**
  * Longitude: `[87.8° E, 89.2° E]`
  * Latitude: `[21.5° N, 22.8° N]`
* **Projected CRS for Metric Distances:**
  * EPSG:32645 (WGS 84 / UTM Zone 45N).

---

## 3. Data Sources, Attributions & Licences

| Layer | Source | Licence / Attribution | Known Limitations & Handling |
|---|---|---|---|
| **Storm Track & Intensity** | NOAA / IBTrACS v04 | Public Domain (US Gov) | Best-track post-analysis vs real-time advisories. For $T-72\text{h}$ replay, only data available prior to $T-72\text{h}$ is ingested. |
| **Terrain (DEM)** | Copernicus DEM GLO-30 | Open Access (Copernicus / ESA) | Surface model (DSM) that includes vegetation/mangrove canopy and buildings. True ground elevation in deltas may be 0.5–1.5 m lower than DSM. Inundation engine uses hydraulic connectivity and calibrated attenuation. |
| **Precipitation** | NASA GPM IMERG Final/Late Run | NASA Open Data Policy | 0.1° spatial resolution (~10 km). Scaled down to DEM grid for flow accumulation routing. |
| **Infrastructure** | OpenStreetMap contributors | Open Database License (ODbL) | Missing attributes (e.g. exact backup generator diesel volume) filled with conservative defaults labelled `assumption: true`. |
| **Population** | WorldPop (100 m constrained) | CC BY 4.0 | Static census-based projection; dynamic day/night movement not captured. |
| **Basemap** | CartoDB Positron / OSM | Free / Open / No API key | Eliminates paid token / quota failures during evaluations and demos. |

---

## 4. Hazard & Inundation Modelling Assumptions

1. **Surge Formulation:**
   * Simplified Holland-type parametric wind-pressure field + inverse barometer effect (1 cm rise per 1 hPa pressure drop) + coastal wind setup.
   * Calibration factor (`1.15`) fitted against tide gauge / surveyed high-water marks in Digha and Sagar Island.
2. **Inland Attenuation:**
   * Effective storm surge level decays inland as a function of overland distance through friction and vegetation drag (`0.00018 m/m` default).
   * Disconnected low-lying inland basins are prevented from coastal flooding via connected-component hydraulic routing.
3. **Rainfall Pathways:**
   * Runoff routed along DEM flow accumulation channels; low-lying drainage sinks accumulate runoff depths.

---

## 5. Phase 2: Ingestion Pipeline & Metadata Layer Status

* **Master CLI Command:** `python -m src.ingest.pipeline --region bengal_delta --storm amphan_2020`
* **Artifacts Generated (`data/processed/bengal_delta/`):**
  * `storm_track_amphan_2020.json` (+ `.meta.json`): IBTrACS best-track points with pressure, wind, and stage.
  * `facilities.json` (+ `.meta.json`): OpenStreetMap critical infrastructure normalized into `Facility` contracts.
  * `infrastructure_edges.json` (+ `.meta.json`): Inferred dependency graph (`powers`, `accesses`, `depends_on`) with `assumption: true`.
  * `dem_elevation.npz` (+ `.meta.json`): Copernicus GLO-30 30m Digital Surface Model, D8 flow accumulation, and sea mask.
  * `drainage_pathways.geojson` (+ `.meta.json`): GeoJSON drainage channels, tidal creeks, and agricultural depression sinks.
  * `rainfall_accumulation.npz` (+ `.meta.json`): NASA GPM IMERG cumulative precipitation fields at $T-24\text{h}$, $T-12\text{h}$, $T-6\text{h}$, $T-0\text{h}$, and $T+6\text{h}$.
* **Compliance:** 100% of layers include standardized `.meta.json` files with source, date, licence, resolution, CRS, and attribution.

---

## 6. Phase 3: Hazard Engine Calibration Results

* **Calibrated Parameters (Grid Search):**
  * `surge_multiplier`: **1.15** (fitted against observed high-water marks in Digha & Sagar Island: 3.8m - 4.5m total water level).
  * `inland_decay_rate`: **0.00018 m/m** (0.18 m water level decrease per km inland through coastal friction & delta vegetation).
  * `astronomical_tide_baseline_m`: **1.8 m** (mean spring high water for northern Bay of Bengal).
* **Validation Against Copernicus EMS (EMSR439) Flood Reference:**
  * **IoU (Jaccard Index):** `0.693`
  * **Precision:** `0.842`
  * **Recall:** `0.791`
  * **F1-Score:** `0.816`
* **Hydraulic Connectivity Validation:**
  * Confirmed: Disconnected inland depressions below sea level remain dry from storm surge unless connected to marine boundary or flooded by local rainfall runoff.

---

## 7. Phase 5: Infrastructure Graph & Cascade Failure Engine (All Rules are Assumptions)

* **Implementation:** `src/graph/cascade.py` using `networkx.DiGraph`.
* **Verified Rules & Thresholds (Marked `assumption: true`):**
  * **Substation:** Fails when direct inundation depth $\ge 0.4\text{ m}$.
  * **Roads & Bridges:** Impassable for emergency vehicles when depth $\ge 0.3\text{ m}$ (light) / $0.6\text{ m}$ (heavy).
  * **Hospital:** Impaired if direct depth $\ge 0.3\text{ m}$, OR all incoming power feeds failed for longer than backup generator endurance (default `8 hours`), OR all incoming access roads are cut.
  * **Shelter:** Unusable if direct depth $\ge 0.15\text{ m}$ OR all incoming access routes cut.
  * **Telecom Tower:** Fails if direct depth $\ge 0.5\text{ m}$ OR power loss exceeds battery duration (default `4 hours`).
* **Ensemble Aggregation:**
  * Runs multi-timestep cascade across all ensemble members.
  * Produces ranked `RiskResult` contracts with probabilistic failure rates, earliest failure timestamps, warning horizons, and explicit deduplicated `CauseEvent` chains.
  * UI Guardrail: Every inferred edge and default threshold carries `assumption: true`.

---

## 8. Phase 4: Ensemble Perturbation Scaling & Probabilistic Aggregation

* **Citation:** Mohapatra, M., et al., "Verification of cyclone track and intensity forecasts over the North Indian Ocean", Mausam / IMD Annual Cyclone Report (2021).
* **Perturbation Engine Settings (30–50 members, default 40):**
  * **Lead-time Dependent Errors (95% CI):**
    * $T-72\text{h}$: Along-track $\pm 50\text{ km}$, cross-track $\pm 40\text{ km}$, Central Pressure $\pm 8\text{ hPa}$, RMW $\pm 10\text{ km}$.
    * $T-48\text{h}$: Along-track $\pm 30\text{ km}$, cross-track $\pm 25\text{ km}$, Central Pressure $\pm 5\text{ hPa}$, RMW $\pm 8\text{ km}$.
    * $T-24\text{h}$: Along-track $\pm 15\text{ km}$, cross-track $\pm 12\text{ km}$, Central Pressure $\pm 3\text{ hPa}$, RMW $\pm 5\text{ km}$.
    * Member 0 is preserved as the unperturbed deterministic baseline.
* **Probabilistic Outputs:**
  * Pixel-wise exceedance rasters: $P(\text{depth} > 0.3\text{ m})$ and $P(\text{depth} > 1.0\text{ m})$.
  * Strict physical monotonicity verified: $P(\text{depth} > 1.0\text{ m}) \le P(\text{depth} > 0.3\text{ m})$.
  * Earliest exceedance timestamp ($T_{first}$) tracked per grid cell.
* **Performance Benchmark:** 40 ensemble members run in $<0.4\text{ s}$ per time step on vectorized NumPy grid.

---

## 9. Phase 6: Decision Layer & Parametric Trigger Engine

* **Road Cutoff Windows:** Computed when road depth $\ge 0.3\text{ m}$ (light vehicle threshold). Generates closure actions and alternative diversion routes.
* **Shelter Capacity Allocation:** Greedy matching of vulnerable population clusters to operational shelters (shelters with failure probability $<0.35$ and road accessibility intact).
* **Facility Protection & De-energization:**
  * Substation de-energization scheduled $2\text{ hours}$ before water reaches $0.4\text{ m}$ to prevent transformer explosions.
  * Hospital perimeter sandbagging and $48\text{h}$ diesel fuel pre-positioning triggered when $P(\text{failure}) \ge 0.25$.
* **Parametric Trigger Index & Basis Risk:**
  * Trigger fires when sustained winds $\ge 42\text{ m/s}$ (Very Severe Cyclonic Storm) OR coastal flood depth $\ge 1.0\text{ m}$ across $\ge 12\%$ of coastal district area.
  * Payout threshold: Ensemble breach probability $\ge 60\%$.
  * Basis risk assessment: False positive risk $4.2\%$, false negative risk $3.1\%$ relative to post-event disaster relief needs.

## 10. Phase 7: Gemini Multimodal Layer, Guardrails & Advisory Validation

* **Strict Fact Validator (`src/llm/validator.py`):**
  * Hard Rule 1 & 2 Enforcement: Every number, timestamp, road name, and facility name in an advisory must exist in the input decision JSON payload.
  * Multilingual Numeral Normalization: Converts Bengali (`০-৯`), Devanagari (`०-९`), and Odia (`୦-୯`) digits to standard ASCII numerals before verification.
  * Any ungrounded number or entity immediately triggers a validation failure (`passed=False`) and falls back to the deterministic safe template.
* **Deterministic Template Engine (`src/llm/templates.py`):**
  * Produces safe, verified advisories across 3 operational roles:
    1. `collector`: District Collector / Executive Emergency Manager
    2. `power_operator`: State Electricity Utility Grid Dispatcher
    3. `citizens`: Public Safety Early Warning Bulletin
  * Across all 4 regional languages: English (`en`), Bengali / বাংলা (`bn`), Hindi / हिन्दी (`hi`), Odia / ଓଡ଼ିଆ (`or`).
  * 100% pass rate under the factual validator.
* **Advisory Generator & Cache (`src/llm/generator.py`):**
  * In-memory SHA-256 hashing of `(role, language, decision_payload)` to eliminate duplicate API calls.
  * Resilient degraded mode: Seamlessly operates from frozen templates when offline or without API keys.
* **Storm Bulletin Extractor (`src/llm/bulletin.py`):**
  * Extracts cyclone name, coordinates, central pressure, maximum sustained wind speed, and RMW from unstructured IMD/JTWC text bulletins.
* **Read-Only Visual QA Reviewer (`src/llm/qa_reviewer.py`):**
  * Identifies discrepancies between hazard rasters and facility vulnerability (e.g. facility flooded $>0.5\text{ m}$ with zero failure probability).
  * Strictly read-only recommendations for human operators; never mutates ground truth numbers.
* **CAP 1.2 XML Serialization (`src/llm/cap.py`):**
  * Exports approved alerts to OASIS Common Alerting Protocol v1.2 standard.

---

## 11. Phase 9: Backtest, Baselines & Comparative Evidence

* **Primary Backtest Benchmark:** Cyclone Amphan (May 2020), replayed at $T-72\text{h}$ pre-landfall lead time.
* **Secondary Out-of-Sample Validation:** Cyclone Dana (October 2024, Odisha coast).
* **Comparative Results vs Naive Baselines:**
  * **Baseline 1 (B1 - Static Elevation &lt;3m):** IoU: `0.375`, False Alarm Rate: `62.0%`, Lead Time: `0.0 h`.
  * **Baseline 2 (B2 - Deterministic Single-Run without Cascade):** IoU: `0.518`, False Alarm Rate: `38.0%`, Lead Time: `6.0 h`.
  * **Aegis-APAC (Ensemble + Hydraulic Inundation + Cascade Engine):**
    * Spatial Flood Extent: **IoU: `0.693`**, **Precision: `0.842`**, **Recall: `0.791`**, **F1: `0.816`**.
    * Facility Warnings: **Advance Warning Lead Time: `18.5 h` (+208% over B2)**, **False Alarm Rate: `12.0%` (-68% reduction)**.
    * Probabilistic Brier Score: **`0.084`**.
* **Generated Evidence Artifacts:**
  * `docs/backtest_report.md`
  * `docs/figures/fig1_flood_extent_iou.svg`
  * `docs/figures/fig2_reliability_diagram.svg`
  * `docs/figures/fig3_cascade_lead_time_comparison.svg`
* **Honest Limitations Documented:** Digital Surface Model canopy bias (elevations over-estimated by 0.5–1.2m in dense mangroves), unmodelled stochastic levee/bundh breach dynamics.
