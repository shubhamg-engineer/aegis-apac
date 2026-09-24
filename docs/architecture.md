# Aegis-APAC: System Architecture & Data Flow

## 1. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph DataIngest["1. Offline Batch Data Layer (Precompute & Freeze)"]
        IBTrACS[("IBTrACS Cyclone Tracks<br/>(Best Track &amp; T-72h Filter)")]
        CopDEM[("Copernicus DEM GLO-30<br/>(30m DSM &amp; Sea Mask)")]
        GPM[("NASA GPM IMERG<br/>(Precipitation Accumulation)")]
        OSM[("OpenStreetMap<br/>(Substations, Hospitals, Roads, Shelters)")]
        Hydro["D8 Flow Routing &amp; Channel Extraction"]
        
        CopDEM --> Hydro
        Hydro --> Channels["Drainage Pathways GeoJSON"]
    end

    subgraph HazardEnsemble["2. Hydrodynamic & Ensemble Hazard Engine"]
        Perturb["Perturbation Generator<br/>(30-50 Members via IMD Error Stats)"]
        Holland["Holland Wind-Pressure Model<br/>(Parametric Radial Decay + Asymmetry)"]
        Surge["Coastal Water Level Model<br/>(Barometer + Shelf Wind Setup + 1.8m Tide)"]
        Inundation["Hydraulic Inundation Model<br/>(Distance Attenuation + 8-Connected BFS)"]
        Pluvial["Pluvial Runoff Model<br/>(D8 Flow Accumulation Sinks)"]
        
        Perturb --> Holland
        Holland --> Surge
        Surge --> Inundation
        GPM --> Pluvial
        Inundation &amp; Pluvial --> CombinedDepth["Total Flood Depth Rasters<br/>(T-24h, T-12h, T-6h, 0h, +6h)"]
        CombinedDepth --> Probabilities["Exceedance Probability Grids<br/>P(depth > 0.3m), P(depth > 1.0m), T_first"]
    end

    subgraph CascadeEngine["3. Infrastructure Graph & Cascade Failure Engine"]
        Graph["Directed NetworkX Dependency Graph<br/>(Substations, Hospitals, Roads, Shelters, Telecom)"]
        InferredEdges["Inferred Structural Edges<br/>[powers, accesses, depends_on]<br/>badge: assumption: true"]
        Rules["Physical &amp; Temporal Thresholds<br/>(Substation >0.4m, Road >0.3m, Hospital Backup 8h)"]
        CascadeSim["Multi-Member Cascade Simulator"]
        RiskResults["Ranked RiskResult Contracts<br/>(Failure Prob, Earliest Time, Cause Chains, Warning Hours)"]
        
        OSM --> InferredEdges --> Graph
        Probabilities --> CascadeSim
        Graph &amp; Rules --> CascadeSim --> RiskResults
    end

    subgraph DecisionParametric["4. Decision Layer & Parametric Trigger"]
        Decisions["Anticipatory Decision Engine"]
        Actions["Operational Action Contracts<br/>(De-energize, Close Roads, Evacuate Shelters, Relief)"]
        Parametric["Parametric Insurance Engine<br/>(District Geofence Thresholds &amp; Basis Risk)"]
        
        RiskResults --> Decisions --> Actions
        Probabilities --> Parametric
    end

    subgraph MultimodalLLM["5. Gemini Multimodal Layer & Strict Guardrails"]
        Gemini["Gemini 3.7 Flash API<br/>(Multimodal Advisory Drafts)"]
        Templates["Deterministic Safe Template Engine<br/>(Guaranteed 100% Grounded Fallback)"]
        Validator{"Strict Factual Validator<br/>(Rule 1 &amp; 2: Disallow Ungrounded Numbers/Names)"}
        ApprovedAdvisory["Validated Advisory<br/>(Collector, Grid Operator, Citizens)"]
        
        Actions &amp; RiskResults --> Gemini
        Actions &amp; RiskResults --> Templates
        Gemini --> Validator
        Validator -- "Discrepancy Detected" --> Templates
        Validator -- "Passed 100%" --> ApprovedAdvisory
        Templates --> ApprovedAdvisory
    end

    subgraph PresentationDispatch["6. API, Dashboard & Interoperable Dispatch"]
        FastAPI["FastAPI Backend<br/>(OpenAPI / Standard Endpoints)"]
        WebUI["MapLibre GL Interactive Dashboard<br/>(Dark Mode, Time Slider, Cascade Inspector)"]
        HumanApproval{"Human Operator<br/>Approval Workflow"}
        CAP["CAP 1.2 XML Broadcast<br/>(OASIS Common Alerting Protocol)"]
        
        FastAPI --> WebUI
        ApprovedAdvisory --> WebUI
        WebUI --> HumanApproval
        HumanApproval -- "Approved (ADMIN_TOKEN)" --> CAP
    end
```

---

## 2. Hard Architectural Invariants

1. **Numbers come from code, never from Gemini:**
   All flood depths, arrival timings, failure probabilities, and network cascade routes are strictly deterministic. Gemini generates role-tailored prose and parses multimodal inputs; it is cryptographically barred from altering ground-truth values.
2. **Every advisory is factually validated:**
   The `AdvisoryValidator` extracts every number, timestamp, road, and facility in the advisory text and cross-references it with the input JSON. Mismatches trigger immediate fallback to `DeterministicTemplateEngine`.
3. **Precompute, then serve:**
   Heavy geospatial processing (Copernicus DEM, Earth Engine, D8 flow routing) runs in offline batch pipelines. The web API serves precomputed tiles and GeoJSON scenarios with zero external runtime dependencies.
4. **Decoupled regional configuration:**
   Adding a new cyclone corridor (e.g. Odisha, Tamil Nadu, Chittagong) requires only adding a `regions/<name>/config.yaml` file without altering core simulation or API logic.
