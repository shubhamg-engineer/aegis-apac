# Aegis-APAC: Product Requirements Document (PRD) v2

**Version:** 2.0 (hackathon MVP)
**Track:** Cyclone Impact and Infrastructure Vulnerability Forecaster (Bay of Bengal / coastal APAC)
**Companion file:** `aegis-apac-build-plan-v2.md` (phase order, hours, tests). If the two conflict on *what* to build, this PRD wins. On *order of work*, the build plan wins.

---

## 1. Product overview

Aegis-APAC is an **impact-based cyclone forecasting and anticipatory-action platform**. For an approaching cyclone it:

1. Estimates surge and rainfall flooding as **probabilities** from an ensemble of perturbed storms.
2. Predicts **which critical facilities fail, when, and why**, including knock-on (cascade) failures.
3. Recommends **actions**: evacuation and shelter assignment, roads to close, facilities to protect or de-energise first.
4. Drafts **role-specific, multilingual advisories** that a human approves before dispatch, exported in standard alert format (CAP).
5. Reports a **parametric trigger** view with basis risk, for early liquidity decisions.
6. **Proves itself** by replaying a real past cyclone using only data available before landfall, and comparing against naive baselines.

**Pitch:** From "where is the storm going" to "who has to do what, by when."

## 2. Problem statement

Cyclone response is still largely post-landfall. Hazard maps show where water may go but not which hospital loses power, which shelter loses road access, or how many hours of warning each facility has. Advisories are generic, slow to localise, and rarely in the local language. Pre-positioned relief and parametric insurance need early, defensible triggers.

## 3. Goals and non-goals

### Goals (MVP)
- G1. Probabilistic surge, rainfall and combined flood layers for one pilot region and one backtest storm.
- G2. Facility-level impact prediction with explicit cascade chains and hours of warning.
- G3. Validated advisories in English, Hindi, Bengali and Odia, with human approval and CAP export.
- G4. Credibility: a backtest against a real event, calibrated honestly, compared with baselines.
- G5. A digital public good: open standards, open API, open licence, region-pluggable through config.
- G6. A polished 3-minute demo that always works (golden scenario).

### Non-goals (MVP)
- Not a replacement for national meteorological forecasts; we consume them.
- Not a certified operational warning system; advisories are decision support and always need human approval.
- No live integration with utility SCADA or hospital systems; dependencies are inferred and labelled as assumptions.
- No public user accounts, native mobile apps, blockchain or smart contracts, or real SMS gateway integration.
- Not multi-region at runtime in the MVP (design for it through `regions/<name>/config.yaml`, do not build it).

## 4. Brief compliance matrix

| Requirement in the track brief | How we meet it | Requirement IDs |
|---|---|---|
| AI-powered predictive risk and vulnerability platform | Ensemble hazard, cascade engine, decision layer | FR-HAZ, FR-ENS, FR-CAS, FR-DEC |
| Google Earth Engine satellite feeds | DEM, rainfall and Sentinel-1 through Earth Engine batch jobs | FR-DATA |
| Real-time meteorological data | Storm track and intensity ingestion, forecast-cycle refresh design | FR-DATA, FR-ENS |
| Gemini 3.7 Flash multimodal reasoning | Advisories, bulletin reader, photo analysis, visual QA reviewer | FR-LLM |
| Simulate cyclone storm surges | Surge model with calibration | FR-HAZ-1 to FR-HAZ-3 |
| Predict local rainfall damage pathways | Flow accumulation, drainage pathways, rainfall flooding | FR-HAZ-4, FR-HAZ-5 |
| Map exposure for power grids, arterial roads, medical shelters | Infrastructure graph, exposure and risk per facility | FR-CAS |
| Automate early-warning advisory dispatch to municipal and disaster authorities | Draft, validate, approve, CAP export, simulated dispatch | FR-LLM-5 to FR-LLM-8 |
| Pre-landfall evacuation planning and infrastructure hardening | Evacuation and protection priorities | FR-DEC |
| Parametric insurance liquidity | Trigger index and basis-risk report | FR-PAR |

## 5. Personas

| Persona | Needs | Key screens |
|---|---|---|
| District Collector / DDMA officer | What to evacuate, where, by when; approve advisories | Map, Actions, Advisory approval |
| State disaster control room analyst | Probabilities, uncertainty, cascade chains across districts | Map, Facility panel, Cascade view |
| Power utility operator | Which feeders and substations to de-energise proactively | Facility panel, Actions |
| Hospital / health officer | Hours of warning, backup power and road access risk | Facility panel |
| Citizen (recipient only) | Clear alert in own language | Advisory text (SMS/CAP output) |
| Hackathon judge | Value in 3 minutes, proof it works | Demo flow, backtest view |

## 6. Scope and priorities

**Pilot region and storm** are chosen in Phase 0 and recorded in `DECISIONS.md`. Candidates: Cyclone Amphan (2020, Sundarbans / West Bengal coast) or Cyclone Dana (2024, Odisha coast). Criteria: track and intensity data, a usable post-event flood reference, enough OSM infrastructure. If two storms have usable data, calibrate on one and validate on the other.

| Priority | Feature |
|---|---|
| **Must** | Contracts and walking skeleton; data layer; hazard engine with calibration; ensemble probabilities; infrastructure graph and cascade engine; decision layer; advisory generator with validator and approval; API; 3D map with time slider; backtest with baselines; deployed demo with golden scenario |
| **Should** | Parametric trigger report; photo damage analysis; bulletin reader; visual QA reviewer; CAP 1.2 export; assumption badges everywhere; second-storm validation |
| **Could** | Offline responder view (PWA); voice or siren scripts; additional languages |

## 7. Primary journey (also the demo script)

1. A forecast for the backtest storm is loaded (golden scenario).
2. The map shows **flood probability** at each time step; a toggle shows **rainfall damage pathways**.
3. The user clicks a substation. The **cascade view** shows: substation floods, feeder area loses power, hospital backup lasts N hours (labelled assumption), the access road becomes impassable at time T, with **hours of warning**.
4. The **Actions panel** shows evacuation and shelter assignments and a protection priority list, each with supporting probabilities.
5. The user opens an advisory for a district collector, switches language, reads the "why", and approves. A CAP file is produced and a simulated dispatch is logged.
6. The **backtest view** shows predicted versus observed flooding and the comparison with baselines.
7. The **parametric view** shows trigger probability per district and the basis-risk table.

## 8. Functional requirements

### 8.1 Data ingestion (FR-DATA)
- **FR-DATA-1** One reproducible command builds all layers for the pilot area: storm track and intensity (IBTrACS), terrain (Copernicus DEM through Earth Engine), rainfall (GPM IMERG), population (WorldPop or GHSL), infrastructure (OSM), coastline and sea mask, flow direction and accumulation from the DEM.
- **FR-DATA-2** Consistent CRS; a metadata file per layer (source, date, licence, resolution, attribution).
- **FR-DATA-3** Earth Engine is used only in batch jobs. Verify dataset IDs in the catalog before coding. Set a daily compute cap.
- **FR-DATA-4** Log known dataset limitations in `DECISIONS.md` (for example: the DEM is a surface model including buildings and vegetation).
- **Acceptance:** one command regenerates all layers; a viewer displays them.

### 8.2 Hazard engine (FR-HAZ)
- **FR-HAZ-1** Parametric wind and pressure field from track, central pressure and radius of maximum winds (Holland-type profile).
- **FR-HAZ-2** Coastal water level = inverse-barometer effect + wind setup + astronomical tide, using a simple documented formulation with a calibration factor in config.
- **FR-HAZ-3** Inundation: effective water level decreases inland with distance (configurable coefficient); flood only cells below that level and hydraulically connected to the sea.
- **FR-HAZ-4** Rainfall: runoff routed by flow accumulation; output damage pathways (drainage channels and accumulation zones).
- **FR-HAZ-5** Combined depth layer at fixed time steps: landfall minus 24, 12, 6, 0 h, plus 6 h.
- **FR-HAZ-6** Calibration: fit the surge factor and inland attenuation coefficient against observations and the flood reference; record values and method.
- **Acceptance:** tests confirm higher surge gives more flooding, disconnected basins stay dry, zero surge gives no coastal flooding, rain-only flooding is confined to accumulation zones.

### 8.3 Ensemble (FR-ENS)
- **FR-ENS-1** 30 to 50 members perturbing track, intensity and size. Perturbation scale grows with lead time and is based on published official forecast-error statistics for the basin (cite the source in `DECISIONS.md`).
- **FR-ENS-2** Exceedance probabilities: P(depth > 0.3 m) and P(depth > 1.0 m), plus time of first exceedance.
- **FR-ENS-3** Output as Cloud-Optimised GeoTIFFs or map tiles. Record runtime.
- **Acceptance:** probability layers exist for all time steps; probabilities lie in [0, 1] and are monotonic in threshold.

### 8.4 Infrastructure graph and cascade engine (FR-CAS)
- **FR-CAS-1** Directed dependency graph from OSM: substation to served area; power to hospital, water and telecom; roads and bridges to shelters and hospitals.
- **FR-CAS-2** Failure rules use configurable thresholds (defaults in section 13.3; all are assumptions).
- **FR-CAS-3** Every inferred edge and default value carries `assumption: true`; the UI displays it.
- **FR-CAS-4** Cascade is run per ensemble member. Output per node: failure probability, earliest likely time, ordered cause chain, hours of warning.
- **Acceptance:** ranked at-risk list with cause chains for the backtest storm; toy-graph tests pass (cascade, backup power delay, redundancy).

### 8.5 Decision layer (FR-DEC)
- **FR-DEC-1** Road blockage windows.
- **FR-DEC-2** Evacuee-to-shelter assignment respecting capacity and road access.
- **FR-DEC-3** Protection priority list.
- **FR-DEC-4** Structured JSON per district that validates against the `Action` contract; each action references the risk results that justify it.

### 8.6 Parametric trigger (FR-PAR)
- **FR-PAR-1** Trigger index per district defined from modelled hazard (for example depth and wind thresholds inside a geofence). Thresholds are configurable.
- **FR-PAR-2** Output probability the trigger fires, based on the ensemble.
- **FR-PAR-3** Basis-risk analysis from the backtest: fires without damage, damage without firing.
- **FR-PAR-4** No blockchain. An append-only audit ledger in the database is sufficient.

### 8.7 Gemini layer (FR-LLM)
- **FR-LLM-1** Advisory generator: input is decision JSON; output is a role-specific advisory (collector, power operator, citizens) via a response schema, in English, Hindi, Bengali and Odia.
- **FR-LLM-2** Validator: every number, time and name in an advisory must exist in the input JSON. On failure, reject and fall back to a template.
- **FR-LLM-3** Bulletin reader: extract storm parameters from bulletin text or PDF into structured fields.
- **FR-LLM-4** Photo analysis: image to structured flood/damage estimate with confidence.
- **FR-LLM-5** Visual QA reviewer: given a rendered map image and the computed facility list, flag inconsistencies for a human. It never overrides computed values.
- **FR-LLM-6** Approval workflow: draft, approved, dispatched; every transition is logged with timestamp and actor.
- **FR-LLM-7** CAP 1.2 export of approved alerts and a simulated dispatch adapter (log and email preview).
- **FR-LLM-8** Gemini never computes depths, timings or geometry.
- **FR-LLM-9** Cache by hash of (decision JSON, role, language); retry with backoff; concurrency limit; model ID read from `GEMINI_MODEL`.
- **Acceptance:** four languages generate; a tampered advisory is rejected; the fallback works when the model errors; the CAP file validates; the reviewer flags a planted inconsistency.

### 8.8 API (FR-API)
- **FR-API-1** FastAPI service serving precomputed results with caching.
- **FR-API-2** Minimum endpoints: `GET /scenarios`, `GET /scenarios/{id}`, `GET /scenarios/{id}/hazard?t=&threshold=`, `GET /scenarios/{id}/pathways`, `GET /scenarios/{id}/facilities`, `GET /facilities/{id}/risk`, `GET /facilities/{id}/cascade`, `GET /scenarios/{id}/actions`, `GET /scenarios/{id}/parametric`, `GET /advisories`, `POST /advisories/{id}/approve` (authenticated), `GET /advisories/{id}/cap`, `GET /backtest/{storm}/metrics`, `GET /health`.
- **FR-API-3** Auto-generated OpenAPI docs; append-only audit log.
- **Acceptance:** every endpoint has a test; responses validate against contracts.

### 8.9 Frontend (FR-UI)
- **FR-UI-1** 3D map (MapLibre plus deck.gl) with time slider; toggles for probability layers, damage pathways, population, infrastructure.
- **FR-UI-2** Facility panel: risk, time of failure, hours of warning, cause chain, assumption badge.
- **FR-UI-3** Cascade view.
- **FR-UI-4** Actions panel; advisory approval panel with language switch and "why" explanation.
- **FR-UI-5** Backtest view and parametric view.
- **FR-UI-6** Uncertainty always visible; never a single unqualified value.
- **FR-UI-7** Responsive on phones; loading and error states; basic keyboard accessibility.
- **FR-UI-8** Basemap without a paid token; attribution displayed.
- **Acceptance:** the journey in section 7 works end to end in `DEMO_MODE`, covered by a Playwright test.

### 8.10 Backtest and evaluation (FR-BT)
- **FR-BT-1** Replay the storm using only data available 72 hours before landfall.
- **FR-BT-2** Compare predicted flood extent with the post-event flood reference (precision, recall, IoU).
- **FR-BT-3** Compare against baselines: **B1** static elevation-threshold hazard zone; **B2** deterministic single run without cascade. Compare lead time and false-alarm rate for facility warnings.
- **FR-BT-4** Report ensemble reliability where data allows.
- **FR-BT-5** If a second storm is usable, validate the calibrated model on it; otherwise state clearly that calibration and validation used the same event.
- **FR-BT-6** Report honestly, including unflattering results, plus a limitations section.
- **Acceptance:** metrics table, baseline comparison and three slide-ready figures in `docs/`.

## 9. Non-functional requirements

| Area | Requirement |
|---|---|
| **Performance (proposed targets; measure and adjust)** | Cached API p95 under 500 ms; map tiles under 2 s on a normal connection; ensemble runtime measured and documented; demo runs from precomputed data |
| **Scalability** | See section 10.2 |
| **Reliability** | Degraded modes: template advisories if Gemini fails; cached layers if a live source fails; CAP output does not depend on the web UI; queue-based dispatch with retries and idempotency keys |
| **Security** | No secrets in the repo; environment variables only; approval endpoints require an operator token; audit log is append-only |
| **Privacy** | No personal data collected; citizen photos processed for the estimate and not retained beyond the demo |
| **Cost control** | Daily Earth Engine cap; Gemini responses cached; everything precomputed for the demo |
| **Internationalisation** | UI and advisories in English, Hindi, Bengali, Odia; no hard-coded strings |
| **Openness** | CAP 1.2, GeoJSON, Cloud-Optimised GeoTIFF, OpenAPI; open licence; data attributions and licences respected (OSM, DEM, population, imagery); verify each licence |
| **Observability** | Structured logs, health endpoint, basic metrics, error tracking |
| **Testability** | Unit, property, contract, golden-file, end-to-end, load and adversarial tests (see build plan) |

## 10. Architecture

### 10.1 Data flow

```
 IBTrACS / bulletins    Earth Engine (DEM, IMERG, Sentinel-1)    OSM / population
        \                        |                                  /
         v                       v                                 v
                    [ Ingest jobs (batch) ] -> data/ -> Cloud Storage
                                   |
                                   v
       [ Hazard engine + calibration ] -> [ Ensemble 30-50 members ] -> probability layers, pathways
                                   |
                                   v
        [ Infrastructure graph + cascade engine ] -> facility risk, cause chains, hours of warning
                                   |
                     +-------------+--------------+
                     v                            v
            [ Decision layer ]           [ Parametric trigger ]
                     |                            |
                     v                            v
  [ Gemini: advisory -> validator -> human approval -> CAP -> simulated dispatch ]
                     |
                     v
   [ FastAPI (Cloud Run) ] -> [ CDN / Cloud Storage tiles ] -> [ React + MapLibre + deck.gl ]
```

### 10.2 Traffic and scalability plan (design assumptions, not measurements)

Assumed scale: about 100 coastal districts, a few thousand official users, and a possible 100x jump in public read traffic in the day before landfall.

| Component | Load driver | Scaling approach | Target |
|---|---|---|---|
| Public map and tiles | Public readers | Static tiles in Cloud Storage behind a CDN; no compute per view | High cache hit ratio; load test with a simulated crowd |
| API (cached JSON) | Official users | Cloud Run autoscaling; scale-to-zero in quiet mode, warm minimum in storm mode | p95 under 500 ms on cached endpoints |
| Batch hazard and ensemble | Forecast cycles (about every 6 hours per active storm) | Scheduled jobs; members run in parallel workers | Runtime measured; results precomputed |
| Earth Engine | Batch exports only | Never called per user request; daily cap set | Within noncommercial quota |
| Gemini | Only when decision JSON changes | Cache by hash; concurrency limit; retry with backoff; template fallback | Rough estimate: about 5,000 calls per day at full scale (about 3k input and 0.8k output tokens each) is roughly $25 per day at the introductory price of $0.75 / $3.75 per million tokens (verify current pricing) |
| Dispatch | Approved alerts | Queue with retries and idempotency keys; alerts are pushed, not pulled | No duplicate sends |

**Operating modes:** quiet (near-zero cost), watch (a depression forms), storm (final 72 hours).

## 11. Data sources and licences

| Need | Source | Notes |
|---|---|---|
| Storm track and intensity | IBTrACS | Verify fields for the chosen storm |
| Terrain | Copernicus DEM (Earth Engine) | Surface model; note limitations; check licence and attribution |
| Rainfall | GPM IMERG (Earth Engine) | Verify dataset ID |
| Post-event flooding | Sentinel-1 (Earth Engine) or a published flood extent product | Backtest validation only, not a pre-landfall input; verify availability |
| Infrastructure | OpenStreetMap | Attribution required; dependencies are inferred |
| Population | WorldPop or GHSL | Verify version and licence |
| LLM | Gemini API | Confirm model ID and quota in AI Studio |
| Forecast error statistics | Official basin forecast verification reports | Needed to scale ensemble perturbations; cite in `DECISIONS.md` |

## 12. Data contracts (frozen in Phase 1)

Schemas live in `contracts/`. Illustrative examples:

```json
// Facility
{
  "id": "osm:node/123",
  "type": "substation | hospital | shelter | telecom_tower | bridge | road_segment",
  "name": "string",
  "geometry": { "type": "Point", "coordinates": [0.0, 0.0] },
  "elevation_m": 2.1,
  "attributes": { "backup_power_hours": 8, "capacity": 300 },
  "assumption_fields": ["backup_power_hours"]
}

// RiskResult
{
  "facility_id": "osm:node/123",
  "scenario_id": "amphan-2020-t-72h",
  "failure_probability": 0.72,
  "earliest_failure_time": "2020-05-20T09:00:00Z",
  "hours_of_warning": 14.5,
  "cause_chain": [
    { "node": "osm:node/45", "event": "flooded", "probability": 0.81, "assumption": false },
    { "node": "osm:node/123", "event": "loses_grid_power", "probability": 0.72, "assumption": true }
  ]
}

// Action
{
  "id": "act-001",
  "district": "string",
  "type": "evacuate | close_road | deenergise | protect_facility | pre_position_relief",
  "deadline": "2020-05-20T06:00:00Z",
  "supporting_risk_ids": ["osm:node/123"],
  "confidence": 0.7
}

// Advisory
{
  "id": "adv-001",
  "role": "collector | power_operator | citizens",
  "language": "en | hi | bn | or",
  "status": "draft | approved | dispatched",
  "text": "string",
  "validation": { "passed": true, "checked_values": 12, "failures": [] },
  "history": [{ "status": "draft", "at": "ISO-8601", "actor": "system" }]
}
```

Also define `Edge` (from, to, relation, `assumption`), `HazardLayerIndex` (time step, threshold, file reference), `Scenario`, `ParametricResult`, `AuditEvent`.

## 13. Model specifications

### 13.1 Hazard
- **Wind and pressure:** Holland-type parametric profile from track, central pressure and radius of maximum winds.
- **Water level:** inverse-barometer effect (pressure deficit) + wind setup (simple documented formulation with a calibration factor) + astronomical tide.
- **Inundation:** effective level = water level minus attenuation (coefficient times distance inland). Flood cells that are below the effective level **and** connected to the sea.
- **Rainfall pathways:** flow accumulation from the DEM; rainfall runoff routed along drainage; depth accumulates in low-lying zones.
- **Calibration:** grid search for the surge factor and attenuation coefficient against observations and the flood reference; record values.
- **Known limitation to state openly:** a simplified model on a surface DEM cannot replace a full hydrodynamic model.

### 13.2 Ensemble
Perturb along-track and cross-track position, intensity and size. Scale with lead time using published basin forecast-error statistics. Aggregate exceedance probability and time of first exceedance.

### 13.3 Cascade defaults (all are assumptions and configurable)

| Item | Default rule |
|---|---|
| Substation | Offline when flood depth at site exceeds 0.4 m |
| Road segment | Impassable above 0.3 m for normal vehicles; above 0.6 m for high-clearance vehicles |
| Bridge | Impassable if approach roads are impassable |
| Hospital | Impaired if site depth exceeds 0.3 m or if power is lost longer than backup duration (default 8 h) or access roads are cut |
| Shelter | Unusable if site depth exceeds 0.15 m or unreachable |
| Telecom tower | Offline if power is lost longer than battery backup (default 4 h) |

### 13.4 Decision
Shelter assignment by capacity-constrained greedy or min-cost flow. Protection priority ranks facilities by failure probability times downstream impact (people served).

### 13.5 Parametric
Trigger index per district from modelled hazard inside a geofence; probability from the ensemble; basis risk from the backtest.

## 14. Gemini specification

| Use | Input | Output | Guardrail |
|---|---|---|---|
| Advisory | Decision JSON | Schema-constrained advisory in the chosen language | Validator plus template fallback plus human approval |
| Bulletin reader | Bulletin text or PDF | Structured storm parameters | Parsed values are shown for confirmation |
| Photo analysis | Image | Structured flood/damage estimate with confidence | Advisory only; never overrides computed values |
| Visual QA reviewer | Rendered map image plus facility list | Flags for human review | Read-only; cannot change data |

Never send secrets or personal data. Log prompts and outputs in the audit trail (without secrets).

## 15. UI specification (summary)

- **Layout:** map centre; left panel for layers and time slider; right panel for facility details, cascade and actions; bottom or modal for advisory approval.
- **Always visible:** time of forecast, ensemble size, uncertainty indicators, assumption badges.
- **Advisory panel:** language tabs, "why" explanation (which risk results back each statement), approve button, CAP download.
- **Backtest and parametric tabs:** tables and charts from the evaluation outputs.
- **Style:** clear, high-contrast, readable on a projector and on a phone.

## 16. Evaluation plan

| Measure | Method | Reported as |
|---|---|---|
| Flood extent agreement | Prediction vs post-event flood reference | Precision, recall, IoU |
| Value over baselines | Compare with B1 and B2 | Lead time, false-alarm rate |
| Ensemble reliability | Predicted probability vs observed frequency | Reliability table, if data allows |
| Advisory safety | Tampered and error cases | 100% of tampered test cases rejected |
| Demo readiness | Playwright end-to-end run | Passes without errors |

**Rules:** quote only numbers our own evaluation produces; do not invent impact figures; state limitations plainly.

## 17. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Simplified surge physics is challenged | Document method; calibrate; show baselines and uncertainty; list limitations |
| DEM errors larger than modelled surge on flat deltas | State limitation; validate against the flood reference; consider a bare-earth alternative if licence and access allow |
| Inferred dependencies are wrong | Label as assumptions; configurable thresholds |
| Gemini writes an incorrect time or road | Validator, template fallback, human approval |
| Free-tier quotas run out (Earth Engine, Gemini, Antigravity) | Precompute and cache; daily caps; one phase at a time |
| Live demo fails | `DEMO_MODE` with golden scenario; recorded video as backup |
| Scope creep | Cut order in the build plan; never cut skeleton, ensemble, cascade, validator, backtest |
| Licence or attribution problems | Record licences in Phase 0; display attributions |

## 18. Milestones

Phases 0 to 11 as defined in `aegis-apac-build-plan-v2.md`: setup and decisions; contracts and skeleton; data; hazard and calibration; ensemble; graph and cascade; decision and parametric; Gemini layer; frontend depth; backtest and baselines; hardening and deploy; submission assets. Total about 64 hours plus buffer.

## 19. Definition of done (MVP)

- [ ] Every "Must" feature meets its acceptance criteria
- [ ] Golden scenario runs with `DEMO_MODE=true`
- [ ] Backtest metrics, baseline comparison and three figures in `docs/`
- [ ] Assumptions labelled in the UI and in `DECISIONS.md`
- [ ] Advisories pass the validator and the approval step
- [ ] Public demo URL works from a fresh browser
- [ ] A fresh clone runs by following the README
- [ ] No secrets in the repo; licences and attributions included
- [ ] Demo video under 3 minutes

## 20. Open questions (resolve in Phase 0; log in `DECISIONS.md`)

1. Which storm and region for the primary backtest, and is a second storm usable for validation?
2. Is a bare-earth DEM available and licensed for our use, or do we keep Copernicus with stated limitations?
3. Which exact Gemini model ID and quota apply to our API key?
4. Which free basemap source do we use?
5. What are the hackathon's submission requirements and deadline (video length, deck, live demo)?
6. Where can we get published basin forecast-error statistics for scaling the ensemble?

## 21. Instructions for the coding agent

1. Read this PRD and `aegis-apac-build-plan-v2.md` fully before writing code.
2. Create the repo structure, then do **Phase 0 only**. Present a plan first.
3. After each phase: run tests, commit, and report what you did, what you assumed, and any requirement you could not meet.
4. Do not invent facts, dataset IDs, or API behaviour. Verify against official documentation.
5. Do not add features outside this PRD without asking.
6. Follow the hard rules in the build plan, especially: numbers come from code, advisories are validated, assumptions are labelled, and a human approves alerts.
