# Aegis-APAC: Digital Public Good (DPG) & Open Source Statement

Aegis-APAC is designed from the ground up as a **Digital Public Good (DPG)** in alignment with the [Digital Public Goods Standard](https://digitalpublicgoods.net/standard/). It aims to democratize advanced anticipatory disaster forecasting and infrastructure vulnerability modeling for vulnerable coastal communities across the Asia-Pacific region.

---

## 1. Open Source Licensing & Attribution

* **Software License:** MIT Open Source License. Complete source code, build scripts, data contracts, and tests are freely available and modifiable without proprietary lock-in.
* **Open Data Licenses & Attributions:**
  * **Digital Elevation Model (DEM):** Copernicus DEM GLO-30 (European Space Agency / Copernicus Open Data).
  * **Meteorological Track Data:** NOAA / IBTrACS v04 (Public Domain).
  * **Satellite Precipitation:** NASA GPM IMERG Final Run (NASA Open Data Policy).
  * **Infrastructure & Road Networks:** OpenStreetMap contributors (Open Database License, ODbL).
  * **Population Density:** WorldPop 100m Constrained (Creative Commons Attribution 4.0 International, CC BY 4.0).
  * **Basemap Tiles:** CartoDB Positron / OSM (Free, no paid API tokens required).

---

## 2. Adherence to Open Technical Standards

Aegis-APAC avoids proprietary protocols in favor of recognized global standards:

1. **OASIS Common Alerting Protocol (CAP 1.2):**
   * All approved early-warning advisories can be exported via `GET /advisories/{id}/cap` as standard CAP 1.2 XML.
   * Directly interoperable with National Disaster Management Authorities (NDMA), WMO Alert Hub, and Google Public Alerts.
2. **OpenAPI 3.1 & RESTful Architecture:**
   * Fully documented OpenAPI specifications accessible via `/docs` and `/redoc`.
   * Standard JSON serialization contracts defined with frozen JSON schemas (`contracts/*.schema.json`).
3. **Open Geospatial Standards (OGC):**
   * Hazard contours, drainage channels, and facility points strictly adhere to RFC 7946 GeoJSON.
   * Coordinate Reference Systems: EPSG:4326 (WGS 84) for geographical interchange and EPSG:32645 (UTM Zone 45N) for metric computations.
4. **Cloud-Optimized Formats:**
   * Compatible with Cloud-Optimized GeoTIFFs (COG) and standard XYZ web map tiles.

---

## 3. Pluggable Regional Architecture

The platform requires zero code changes to be deployed to new vulnerable cyclone corridors (e.g. Odisha, Tamil Nadu, Chittagong, the Mekong Delta in Vietnam, or coastal Philippines).

To deploy in a new region:
1. Create `regions/<region_name>/config.yaml`.
2. Define the Area of Interest (AOI) bounding box, regional languages, and engineering thresholds.
3. Run the automated data ingestion pipeline:
   ```bash
   python -m src.ingest.pipeline --region <region_name> --storm <storm_id>
   ```

---

## 4. Data Sovereignty, Privacy & Offline Resilience

* **Zero Citizen PII:** Aegis-APAC models aggregate ward-level census populations and public infrastructure. It does not track, store, or process personally identifiable citizen data.
* **Precomputed Offline Operation (`DEMO_MODE=true`):** Heavy geospatial computations are decoupled into offline batch jobs. During live disasters or network blackouts, the entire platform runs self-contained from local caches without needing live connections to Google Earth Engine.
* **Cloud Agnostic:** Can be run on Google Cloud Platform (Cloud Run, Cloud Storage), AWS, Azure, or on-premises servers in national emergency operations centers.
