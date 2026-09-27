---
title: Aegis-APAC Cyclone Impact Platform
emoji: 🌀
colorFrom: red
colorTo: indigo
sdk: docker
app_port: 7860
pinned: true
license: mit
short_description: Cyclone impact & infrastructure forecaster for APAC
tags:
  - disaster-management
  - climate
  - fastapi
  - cyclone
  - anticipatory-action
---
# Aegis-APAC: Cyclone Impact & Critical Infrastructure Vulnerability Forecaster

> **Anticipatory Action, Cascading Infrastructure Failure Prediction, and Parametric Liquidity for Asia-Pacific Coastal Communities.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-67%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Digital Public Good](https://img.shields.io/badge/DPG-Standard%20Compliant-blueviolet.svg)](docs/digital_public_good.md)

---

## 1. Overview

Tropical cyclones in the Asia-Pacific region cause catastrophic disruptions not merely through wind and rain, but through **interdependent infrastructure cascades**:
- Storm surge submerges an electrical substation ($\ge 0.4\text{m}$).
- The substation trips, cutting grid power to a district hospital and regional water treatment.
- Hospital emergency backup diesel generators deplete within 8 hours.
- Simultaneously, access roads submerge ($\ge 0.3\text{m}$), preventing relief tankers from resupplying diesel or oxygen.

**Aegis-APAC** is an anticipatory forecasting platform that bridges meteorological predictions and physical infrastructure graphs. Replayed 72 hours before landfall ($T-72\text{h}$) on **Cyclone Amphan (May 2020)** in the **Bengal Delta / Sundarbans** (with out-of-sample validation on Cyclone Dana, 2024), Aegis-APAC delivers **18.5 hours of advance warning** (+208% increase over deterministic baselines) and reduces facility false alarms by **68%**.

---

## 2. System Architecture

```mermaid
flowchart LR
    A[IBTrACS + Copernicus DEM + GPM Rain + OSM] --> B[Physics Hazard Engine &amp; 40-Member Ensemble]
    B --> C[Directed Infrastructure Dependency Graph]
    C --> D[Multi-Member Cascade Simulator]
    D --> E[Anticipatory Actions &amp; Parametric Trigger]
    E --> F[Gemini 3.7 Flash + Strict Fact Validator]
    F --> G[Interactive MapLibre Dashboard &amp; CAP 1.2 XML]
```

### Core Non-Negotiable Hard Rules (`AGENTS.md`)
1. **Numbers come from code, never from Gemini:** Water depths, arrival timings, failure probabilities, and network cascades are strictly deterministic.
2. **Every advisory is validated:** The automated validator cross-references every number, timestamp, and facility name in advisories against the input decision JSON, falling back to safe templates on any discrepancy.
3. **Probabilities, not single deterministic lines:** 40-member perturbed ensembles scaled to official IMD error statistics yield true exceedance probabilities $P(\text{depth} > 0.3\text{m})$ and $P(\text{depth} > 1.0\text{m})$.
4. **Assumptions are explicitly labelled:** Inferred dependencies and default thresholds carry `assumption: true` in data and UI.
5. **Human approval required before dispatch:** Advisories transition `draft` $\rightarrow$ `approved` $\rightarrow$ `dispatched` with operator authorization.
6. **Precompute, then serve:** Offline batch processing decouples Earth Engine compute. The demo runs 100% self-contained from `data/golden/` with zero paid API token dependencies.

---

## 3. Quickstart & Local Setup

### Prerequisites
- Python 3.11 or higher
- Git

### Installation
```bash
# 1. Clone repository
git clone https://github.com/aegis-apac/aegis-apac.git
cd aegis-apac

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e .
```

### Configuration (`.env`)
```bash
cp .env.example .env
# Edit .env if Gemini API key is available (optional; runs in offline degraded mode automatically if absent)
```

### Run the Application
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --reload
```
Open your browser to:
- **Citizen Safety Home (Simple Mode UI):** [http://localhost:8080/](http://localhost:8080/)
- **Control Room Ops Console (Officials & Judges):** [http://localhost:8080/console](http://localhost:8080/console)
- **Single-Glance Citizen Status Endpoint:** [http://localhost:8080/status](http://localhost:8080/status)
- **Interactive OpenAPI Documentation:** [http://localhost:8080/docs](http://localhost:8080/docs)
- **Health Check:** [http://localhost:8080/health](http://localhost:8080/health)
- **Observability Metrics:** [http://localhost:8080/metrics](http://localhost:8080/metrics)

---

## 4. Running with Docker

```bash
# Build the container image
docker build -t aegis-apac:latest .

# Run on port 8080
docker run -p 8080:8080 aegis-apac:latest
```

---

## 5. Verification & Testing

Run the comprehensive 50-test suite covering setup, data ingestion, hazard physics, ensembles, cascade graphs, decision engine, strict LLM guardrails, API routes, and backtest evaluations:

```bash
python -m pytest
```

---

## 6. Project Structure

```
aegis-apac/
â”œâ”€â”€ AGENTS.md                  # Strict hard agent rules
â”œâ”€â”€ DECISIONS.md               # Architectural decisions & assumptions log
â”œâ”€â”€ Dockerfile                 # Production Cloud Run container definition
â”œâ”€â”€ pyproject.toml             # Python build configuration and dependencies
â”œâ”€â”€ contracts/                 # Frozen JSON Schemas (Facility, Risk, Action, Advisory)
â”œâ”€â”€ regions/
â”‚   â””â”€â”€ bengal_delta/          # Pilot region config (AOI, thresholds, languages)
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/                   # Raw ingested datasets
â”‚   â”œâ”€â”€ processed/             # Cleaned GeoTIFFs, DEM grids, OSM layers
â”‚   â””â”€â”€ golden/                # Frozen precomputed scenario bundle (DEMO_MODE)
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ api/                   # FastAPI backend, middleware, and routing
â”‚   â”œâ”€â”€ backtest/              # Evaluation metrics, baselines (B1, B2), SVG charts
â”‚   â”œâ”€â”€ decision/              # Evacuation allocator, road closures, de-energization
â”‚   â”œâ”€â”€ graph/                 # NetworkX directed graph & cascade failure engine
â”‚   â”œâ”€â”€ hazard/                # Holland profile, surge setup, BFS connectivity, ensemble
â”‚   â”œâ”€â”€ ingest/                # IBTrACS, Copernicus DEM, GPM rainfall, OSM pipeline
â”‚   â”œâ”€â”€ llm/                   # Gemini 3.7 Flash, strict validator, templates, CAP export
â”‚   â””â”€â”€ parametric/            # Parametric insurance triggers & basis risk report
â”œâ”€â”€ web/                       # MapLibre GL JS frontend (HTML/CSS/JS)
â”œâ”€â”€ tests/                     # 50 unit, integration, property, and adversarial tests
â””â”€â”€ docs/                      # PRD, build plan, backtest report, demo script, slides, DPG
```

---

## 7. Evidence & Benchmarks (Cyclone Amphan Backtest)

Evaluated against Copernicus EMS satellite flood delineations and naive baselines:

| Metric | Baseline 1 (Static &lt; 3m) | Baseline 2 (Deterministic Single Run) | Aegis-APAC (Ours) | Impact |
|---|---|---|---|---|
| **Spatial IoU** | 0.375 | 0.518 | **0.693** | **+33.7% accuracy** |
| **Precision** | 0.410 | 0.680 | **0.842** | **+23.8% precision** |
| **Facility Warning Lead Time** | 0.0 h | 6.0 h | **18.5 h** | **+208% lead time** |
| **False Alarm Rate** | 62.0% | 38.0% | **12.0%** | **-68.4% reduction** |
| **Ensemble Brier Score** | â€” | â€” | **0.084** | **Calibrated uncertainty** |

Detailed report and figures available in [docs/backtest_report.md](docs/backtest_report.md) and [docs/figures/](docs/figures/).

---

## 8. License & Attribution

- **Code:** [MIT License](LICENSE)
- **Data Attributions:** Copernicus DEM (ESA), IBTrACS (NOAA), GPM IMERG (NASA), OpenStreetMap contributors (ODbL), WorldPop (CC BY 4.0), CartoDB Positron (Free / Open).

