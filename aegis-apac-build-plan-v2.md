# Aegis-APAC: Build Plan v2 (for Google Antigravity)

**Companion file:** `aegis-apac-prd-v2.md`. The PRD says *what* to build and why. This plan says *in what order* and *how to verify each step*. If they conflict on what to build, the PRD wins. On order of work, this plan wins.

**Effort:** about 64 hours plus buffer. No calendar dates. Work is organised by phase.

---

## 0. What changed from v1 (and why)

1. **Walking skeleton first (Phase 1).** A thin end-to-end version (mock data, API, map, advisory stub) exists early, so a demo is always possible. Every later phase deepens one slice instead of building blind.
2. **Contracts before code.** JSON schemas for facilities, risk results, actions and advisories are frozen in Phase 1. This lets separate agents work in parallel without breaking each other.
3. **Golden scenario.** A frozen, precomputed scenario bundle drives the demo, so the demo never depends on live services.
4. **Calibration and baselines.** The hazard model is calibrated against observations and compared with naive baselines, so we can show our method adds value.
5. **Brief compliance.** Every requirement in the track brief is mapped to a feature (see the PRD's compliance matrix), including rainfall damage pathways and parametric triggers.
6. **Testing strategy and Antigravity operating manual** are explicit.

---

## 1. Antigravity operating manual

1. Give the agent **one phase at a time**. Never ask for the whole project at once.
2. Ask for a **plan first** and review it before it writes code. Reject plans that add features outside the PRD.
3. After each phase, require: tests pass, a short summary, assumptions logged in `DECISIONS.md`, and a git commit.
4. Keep a short rules file in the repo root (an `AGENTS.md`-style file, or use Antigravity's rules feature; check how it loads rules) containing the hard rules from section 2.
5. **One module per agent** when running agents in parallel (see section 9). No agent edits another module's code, only the shared `contracts/` folder through a reviewed change.
6. Do not let agents refactor working code "for cleanliness" late in the project.
7. Free-tier quotas are limited and can lock you out for days. Keep prompts focused, and precompute expensive work once.

**Kickoff prompt:**
> Read `docs/aegis-apac-prd-v2.md` and `docs/aegis-apac-build-plan-v2.md` fully. Create the repo structure from section 5 of the plan. Do Phase 0 only. Give me your plan first. When Phase 0 passes its checks, summarise what you did and what you assumed, then stop.

---

## 2. Hard rules

- **Numbers come from code, never from Gemini.** Depths, timings, geometry and graph logic are deterministic. Gemini writes, explains, reads multimodal input, and acts as a reviewer. It never produces the source-of-truth numbers.
- **Every advisory is validated.** Any number, time, or road/facility name in an advisory must exist in the computed input JSON. If validation fails, fall back to a template advisory.
- **Probabilities, not single lines.** Hazard outputs are ensemble-based.
- **Assumptions are labelled** in data and UI (`assumption: true`).
- **Human approval** before any alert is marked dispatched.
- **One pilot region and one primary backtest storm.** Depth over breadth.
- **Precompute, then serve.** Earth Engine runs in batch only. The web app never calls Earth Engine per request.
- **Configuration over hard-coding.** Thresholds, perturbation ranges, model IDs and region settings live in config files.
- **Never invent facts.** Verify dataset IDs, model IDs and library behaviour against official documentation.

---

## 3. Tech stack

| Layer | Choice |
|---|---|
| Science and backend | Python 3.11, FastAPI |
| Geospatial | earthengine-api, geopandas, shapely, rasterio, numpy, xarray; a hydrology library for flow accumulation (for example pysheds or richdem; verify) |
| Graph | NetworkX |
| Storage | Files in `data/` locally; Google Cloud Storage for deployment; SQLite for audit log and advisory state |
| LLM | Gemini API through the `google-genai` SDK; model ID from the env var `GEMINI_MODEL` (default `gemini-3.7-flash`; confirm the ID in AI Studio) |
| Frontend | Vite, React, TypeScript, MapLibre GL JS, deck.gl |
| Testing | pytest (with hypothesis for property tests), Playwright for end-to-end |
| Hosting | Frontend on Firebase Hosting or Vercel; API on Cloud Run; tiles from Cloud Storage behind a CDN |

**Environment variables (`.env.example`):** `GEMINI_API_KEY`, `GEMINI_MODEL`, `GCP_PROJECT`, `EE_PROJECT`, `DATA_DIR`, `REGION_CONFIG`, `DEMO_MODE` (true uses the golden scenario), `ADMIN_TOKEN` (for approval endpoints).

---

## 4. Prerequisites

- Google account and Cloud project; Earth Engine registered as a **noncommercial** project; `earthengine authenticate` works
- Gemini API key from Google AI Studio
- GitHub repo, Python 3.11, Node 20+, Git
- A free basemap approach that needs no paid token (decide in Phase 0)

---

## 5. Repository structure

```
aegis-apac/
  README.md
  AGENTS.md              # short hard rules for agents
  DECISIONS.md           # every assumption and simplification
  .env.example
  contracts/             # JSON schemas + example payloads (frozen in Phase 1)
  regions/
    <region-name>/config.yaml   # AOI, thresholds, languages, data paths
  data/
    raw/  processed/  golden/   # golden = frozen demo bundle
  src/
    ingest/  hazard/  graph/  decision/  parametric/  llm/  api/  backtest/
  tests/
  web/
  docs/                  # PRD, plan, architecture diagram, backtest report, demo script
```

---

## 6. Phase template (applies to every phase)

- **Definition of ready:** contracts it depends on exist; previous phase committed.
- **Definition of done:** all "Done when" checks pass; tests written and passing; `DECISIONS.md` updated; commit made; summary written.

---

## 7. Phases

### Phase 0: Setup and decisions (about 2 h)
**Goal:** Working repo and firm decisions that everything else depends on.
**Tasks**
- Create the repo structure and environments; configure linting and pytest.
- Choose the **primary backtest storm and pilot region**. Candidates: Cyclone Amphan (2020, Sundarbans / West Bengal coast) or Cyclone Dana (2024, Odisha coast). If two storms have usable data, plan to **calibrate on one and validate on the other**.
- Check that the storm has IBTrACS track and intensity, a usable post-event flood reference (Sentinel-1 through Earth Engine, or a published flood extent product; verify), and enough OSM infrastructure in the area.
- Decide the basemap (free, no paid token) and record licences and attribution needed for each data source.
- Create `regions/<name>/config.yaml` with the AOI.
**Done when:** tools authenticate; AOI saved; storm and reference-data availability confirmed in `DECISIONS.md`; basemap chosen.

### Phase 1: Contracts and walking skeleton (about 5 h)
**Goal:** A thin end-to-end slice with mock data, so the demo path exists from day one.
**Tasks**
- Write JSON schemas and example payloads in `contracts/` for: `Facility`, `Edge`, `RiskResult`, `Action`, `Advisory`, `HazardLayerIndex`, `Scenario` (see the PRD data contracts).
- Build a minimal FastAPI app that serves mock scenario data through the real endpoints.
- Build a minimal frontend: map, time slider, one mock probability layer, facility list, one advisory stub with approve button.
- Create `DEMO_MODE` that loads from `data/golden/`.
- Freeze the contracts. Later changes need an explicit reviewed change.
**Done when:** running the API and web app shows the full journey with mock data; contracts have validation tests; a Playwright smoke test passes.

### Phase 2: Data layer (about 6 h)
**Goal:** One reproducible script builds all real input layers for the AOI.
**Tasks**
- Storm track and intensity (IBTrACS).
- Terrain: Copernicus DEM through Earth Engine (verify the dataset ID, for example `COPERNICUS/DEM/GLO30`), exported for the AOI. Record in `DECISIONS.md` that it is a surface model that includes buildings and vegetation; evaluate a bare-earth alternative only if its licence and access allow.
- Rainfall: GPM IMERG through Earth Engine (verify the ID).
- Population: WorldPop or GHSL.
- Infrastructure from OSM: substations, power lines, hospitals and clinics, shelters and schools, roads and bridges, telecom towers.
- Coastline and sea mask; drainage/flow-direction layers derived from the DEM.
- Consistent CRS; metadata file per layer (source, date, licence, resolution).
**Done when:** one command regenerates all layers; a viewer shows them; layer metadata complete; Earth Engine daily compute limit set in the Cloud console.

### Phase 3: Hazard engine v1 and calibration (about 9 h)
**Goal:** Flood depth rasters for one scenario, calibrated against observations.
**Tasks**
- Parametric wind and pressure field from track, central pressure and radius of maximum winds (Holland-type profile).
- Coastal water level = inverse-barometer effect + wind setup + astronomical tide. Use a simple documented wind-setup formulation (for example wind stress over a shelf of given width and depth), with a **calibration factor** stored in config.
- Inundation: effective water level decreases inland with distance (configurable coefficient); flood only cells that are below that level **and hydraulically connected to the sea**.
- Rainfall: runoff volume routed by flow accumulation; output **damage pathways** (drainage channels and accumulation zones) and rainfall flood depth in low-lying areas.
- Combine surge and rain into a combined depth layer at fixed time steps: landfall minus 24, 12, 6, 0 h, plus 6 h.
- Calibrate the inland attenuation coefficient and the surge factor by comparing to observed or reported values and the flood reference (grid search is fine). Record the values and how they were chosen.
**Tests:** higher surge gives a larger flooded area; disconnected inland basins stay dry; zero surge gives no coastal flooding; rain-only run floods only accumulation zones; property tests on monotonicity.
**Done when:** runs on the backtest storm in a measured, documented time; tests pass; calibration recorded.

### Phase 4: Ensemble and probabilities (about 5 h)
**Goal:** Turn one scenario into probabilities.
**Tasks**
- Generate 30 to 50 members by perturbing track (cross-track and along-track), intensity and size. Scale perturbations with forecast lead time using published official forecast-error statistics for the basin; **cite the source in `DECISIONS.md`**.
- Aggregate to exceedance-probability rasters: P(depth > 0.3 m) and P(depth > 1.0 m), plus time of first exceedance.
- Write outputs as Cloud-Optimised GeoTIFFs or map tiles.
- Parallelise members; record runtime.
**Done when:** probability layers exist for every time step; runtime documented; a sanity test shows probabilities between 0 and 1 and monotonic in threshold.

### Phase 5: Infrastructure graph and cascade engine (about 7 h)
**Goal:** Predict which facilities fail, when, and why.
**Tasks**
- Build a directed dependency graph: substation to served area; power to hospital, water and telecom; roads and bridges to shelters and hospitals. Use nearest-feeder and capacity defaults where data is missing, and mark those edges `assumption: true`.
- Failure rules with **configurable thresholds** (defaults in the PRD, all labelled as assumptions).
- Run the cascade for each ensemble member. Output per node: probability of failure, earliest likely time, the ordered cause chain, and hours of warning before failure.
- Produce a ranked at-risk facility list.
**Tests:** toy-graph unit tests (single failure cascades correctly; backup-power duration delays failure; redundant paths prevent failure).
**Done when:** ranked list with cause chains exists for the backtest storm; tests pass.

### Phase 6: Decision layer and parametric trigger (about 3 h)
**Goal:** Actions, not just maps.
**Tasks**
- Road blockage windows.
- Evacuation and shelter assignment respecting capacity and road access (greedy or min-cost flow).
- Protection priority list (which facilities to harden or de-energise first).
- **Parametric trigger report:** define a trigger index per district from modelled hazard (for example depth and wind thresholds in a geofence), output the probability the trigger fires, and compute basis risk from the backtest (fires without damage, damage without firing). No blockchain.
- Output structured JSON matching the `Action` contract.
**Done when:** JSON validates against contracts; every action links to the risk results that justify it.

### Phase 7: Gemini layer (about 6 h)
**Goal:** Language, multimodal work and review, with guardrails.
**Tasks**
- **Advisory generator:** input is the decision JSON, output is a role-specific advisory (district collector, power operator, citizens) using a response schema, in English, Hindi, Bengali and Odia.
- **Validator:** every number, time and name must appear in the input JSON. Reject and fall back to a template on failure.
- **Bulletin reader:** extract storm parameters from advisory text or PDF into structured fields.
- **Photo analysis:** image to structured flood/damage estimate with confidence; test on a small sample set.
- **Visual QA reviewer:** send a rendered map image plus the computed facility list to Gemini and ask it to flag inconsistencies (for example a facility marked dry that appears inside a flood polygon). Output is a list of flags for a human, never an override.
- **Approval workflow:** draft, approved, dispatched, with audit log.
- **CAP 1.2 export**, plus a simulated dispatch adapter (log and email preview; real SMS is out of scope).
- Cache responses by hash of (decision JSON, role, language). Add retry with backoff and a concurrency limit.
**Tests:** a tampered advisory is rejected; fallback template used when the model errors; CAP file validates; the reviewer flags a deliberately planted inconsistency.
**Done when:** all four languages generate; all tests pass.

### Phase 8: Frontend depth (about 9 h)
**Goal:** The demo experience.
**Tasks**
- 3D map with a time slider; toggles for hazard probability layers, damage pathways, population and infrastructure.
- Facility panel: risk, time of failure, hours of warning, cause chain, **assumption badge**.
- Cascade view for a selected facility.
- Actions panel and advisory approval panel with a language switch and a "why" explanation.
- Backtest view (predicted versus observed) and parametric trigger view.
- Uncertainty always visible. Responsive layout for phones.
- Loading and error states; keyboard accessibility basics.
**Done when:** the full journey in the PRD can be clicked through in `DEMO_MODE` without errors; a Playwright end-to-end test covers it.

### Phase 9: Backtest, baselines and evidence (about 6 h)
**Goal:** Proof that it works and that it beats naive alternatives.
**Tasks**
- Replay the storm using only data available 72 hours before landfall.
- Compare predicted flood extent with the post-event flood reference (precision, recall, IoU).
- **Baselines:** (B1) static elevation-threshold hazard zone; (B2) deterministic single-run without cascade. Compare lead time and false-alarm rate for facility warnings against these.
- Report ensemble reliability (do 70% predictions come true about 70% of the time?) if data allows.
- If a second storm exists, validate the calibrated model on it. If not, state clearly that calibration and validation used the same event.
- Produce three slide-ready figures and a short report with an honest limitations section.
**Done when:** metrics table, baseline comparison and three figures exist in `docs/`. Report results as they are, even where they are unflattering.

### Phase 10: Hardening, deployment and observability (about 3 h)
**Tasks**
- Deploy API (Cloud Run), tiles (Cloud Storage plus CDN) and frontend.
- Structured logging, health endpoint, error tracking, simple metrics.
- Load test the tile path and cached API endpoints (goal set in the PRD).
- Confirm degraded modes: Gemini down uses templates; live source down uses cached layers.
- README with setup steps and an architecture diagram; fresh-clone test.
**Done when:** the public demo URL works from a fresh browser; a fresh clone runs following the README; no secrets in the repo.

### Phase 11: Submission assets (about 3 h)
**Tasks**
- 3-minute demo script and screen recording (no cuts to hide errors).
- Slide deck: problem, solution, backtest and baseline results, architecture, scalability, impact, roadmap.
- One-page architecture diagram.
- Digital-public-good statement: open standards (CAP, GeoJSON, COG, OpenAPI), open licence, region plug-in via `regions/<name>/config.yaml`.
- FAQ for judges: physics limits, assumptions, data licences, adding another region.
**Done when:** the video is under 3 minutes and shows the full flow.

---

## 8. Effort summary

| Phase | Hours |
|---|---|
| 0 Setup and decisions | 2 |
| 1 Contracts and skeleton | 5 |
| 2 Data layer | 6 |
| 3 Hazard and calibration | 9 |
| 4 Ensemble | 5 |
| 5 Graph and cascade | 7 |
| 6 Decision and parametric | 3 |
| 7 Gemini layer | 6 |
| 8 Frontend depth | 9 |
| 9 Backtest and baselines | 6 |
| 10 Hardening and deploy | 3 |
| 11 Submission assets | 3 |
| **Total** | **64** |

## 9. Parallel work (after Phase 1)

If several people or agents work at once, split by module and never share code across module boundaries except through `contracts/`:
- **A:** Data layer (Phase 2)
- **B:** Hazard and ensemble (Phases 3 and 4)
- **C:** Graph, cascade, decision and parametric (Phases 5 and 6)
- **D:** Gemini layer (Phase 7)
- **E:** Frontend (Phase 8)
Integration point: everything reads and writes payloads that match the frozen contracts.

## 10. Testing strategy

- **Unit and property tests** for hazard, graph and validator logic.
- **Contract tests:** every payload validates against its schema.
- **Golden-file tests:** the golden scenario bundle produces the same key outputs.
- **End-to-end:** Playwright runs the demo journey in `DEMO_MODE`.
- **Load test:** tile and cached API paths.
- **Adversarial test:** tampered advisories, missing data, model errors.

## 11. Cut order if time runs short

1. Voice or siren scripts
2. Offline PWA
3. Visual QA reviewer
4. Extra languages beyond English, Hindi, Bengali, Odia
5. Second-storm validation

**Never cut:** walking skeleton, ensemble probabilities, cascade engine, advisory validator, backtest with baselines.

## 12. Final checklist

- [ ] Golden scenario works with `DEMO_MODE=true`
- [ ] Backtest metrics, baseline comparison and three figures exist
- [ ] Assumptions labelled in the UI and in `DECISIONS.md`
- [ ] Advisories pass the validator and the approval step
- [ ] Public demo URL works
- [ ] Fresh clone runs from the README
- [ ] No secrets in the repo; data licences and attributions included
- [ ] Demo video under 3 minutes
