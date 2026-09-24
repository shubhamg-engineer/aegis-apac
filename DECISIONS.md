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

## 5. Infrastructure Dependency & Cascade Rules (All Are Assumptions)

* **Substation:** Fails when inundation depth exceeds `0.4 m`.
* **Roads:** Impassable for light emergency vehicles at `0.3 m`; impassable for heavy trucks at `0.6 m`.
* **Hospital:** Impaired if site depth > `0.3 m`, or if grid power is lost longer than backup generator endurance (default `8 hours`), or if access roads are cut.
* **Shelter:** Unusable if site depth > `0.15 m` or if unreachable.
* **Telecom Tower:** Fails when power outage exceeds battery endurance (default `4 hours`).
* *UI Guardrail:* Every inferred edge and default threshold carries `assumption: true`.

---

## 6. Ensemble Perturbation Scaling

* Perturbation scale for the 40 ensemble members increases with lead time according to published India Meteorological Department (IMD) annual cyclone verification error statistics:
  * 24h track error: $\sim 60\text{ km}$
  * 48h track error: $\sim 110\text{ km}$
  * 72h track error: $\sim 160\text{ km}$
  * Central pressure error: $\pm 8\text{ hPa}$ at 72h.

---

## 7. Gemini Guardrails & Verification Policy

* **No Hallucinated Numbers:** Depths, lead times, coordinates, and cascade chains are generated strictly by deterministic algorithms.
* **100% Validation:** The automated validator scans every entity, number, and time in LLM drafts against the input JSON. On mismatch, the safe template fallback is dispatched.
* **Human Approval:** No alert is dispatched without human approval in the UI.
