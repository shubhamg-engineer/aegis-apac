# Aegis-APAC: 3-Minute Video Walkthrough Script

**Target Duration:** Exactly 180 seconds (3:00)  
**Presenter Tone:** Authoritative, operational, technically rigorous, urgent.

---

## Storyboard & Timestamp Breakdown

### [0:00 - 0:30] Scene 1: The Critical Gap & System Overview
* **Visual:** Full-screen title graphic transitioning to the Aegis-APAC command console in dark mode. Zoom in on the Bengal Delta AOI.
* **Narrator:**
  > "Tropical cyclones in the Asia-Pacific do not kill through wind alone—they devastate communities by severing lifelines. When a coastal electrical substation floods, hospitals lose grid power, access roads submerge, and emergency communications collapse.
  > Current meteorological alerts issue generic district-wide warnings that arrive too late for proactive mitigation.
  > This is **Aegis-APAC**: an anticipatory cyclone impact and infrastructure vulnerability forecaster. It combines physics-calibrated storm surge modeling, 40-member ensemble uncertainty, and directed dependency graphs to predict which facilities will fail, when, and why—up to 72 hours before landfall."

---

### [0:30 - 1:15] Scene 2: Hydrodynamic Ensembles & Dynamic Time Slider
* **Visual:** Screen interaction: Mouse navigates to the Forecast Lead Time slider. Drag from `-24h` to `-12h`, `-6h`, and `0h (Landfall)`. Show hazard contours expanding along the coast and inland waterways. Toggle on `P(depth > 1.0m)` and `Rainfall Damage Pathways`.
* **Narrator:**
  > "Here, we replay Super Cyclone Amphan using exclusively data available 72 hours before landfall.
  > Unlike deterministic models that predict a single uncertain line, Aegis-APAC runs a 40-member perturbed ensemble scaled to official IMD forecast error statistics.
  > As we scrub through time from T-24 hours to landfall, our hydrodynamic engine calculates both coastal wind setup and pluvial runoff. Notice that overland inundation strictly follows hydraulic connectivity from the marine boundary—inland basins below sea level remain dry unless an overland flow path connects them."

---

### [1:15 - 1:50] Scene 3: The Cascade Failure Inspector
* **Visual:** Click on the red marker for `Digha Coastal Substation` on the map. The right sidebar immediately populates the Cascade Graph panel with an animated probability bar (`85%`), warning horizon (`18.0 hrs`), and ordered cause chain. Highlight the `[assumption: true]` badge.
* **Narrator:**
  > "Let's inspect Digha Coastal Substation. It faces an 85% probability of inundation above 0.4 meters, with 18 hours of advance warning.
  > But the true danger is secondary cascading failure. Notice our directed dependency graph: when this substation drowns, power is cut to Contai Sub-Divisional Hospital and regional water treatment.
  > Crucially, we enforce hard rules: every inferred link and engineering threshold is explicitly labelled with an **assumption badge**. Hospital backup generators provide an 8-hour buffer before critical care units fail."

---

### [1:50 - 2:20] Scene 4: Anticipatory Actions & Parametric Financing
* **Visual:** Switch to the `Actions` tab. Show the ranked list: controlled de-energization, road closures, shelter allocation. Then highlight the left sidebar `Parametric Liquidity Trigger` box.
* **Narrator:**
  > "Aegis-APAC translates hazard predictions into immediate operational directives.
  > In the Actions tab, power utilities receive an automated mandate to de-energise substation switchgear 2 hours before floodwaters reach 0.4 meters—preventing multi-million dollar transformer explosions.
  > Simultaneously, vulnerable populations are algorithmically matched to accessible cyclone shelters respecting road clearance.
  > On the left, our parametric trigger engine evaluates district geofences. For South 24 Parganas, an 84% breach probability automatically authorizes a pre-arranged $2,000,000 emergency liquidity payout 48 hours before landfall."

---

### [2:20 - 2:45] Scene 5: Guarded Multimodal LLM & CAP Dispatch
* **Visual:** Switch to `Advisories` tab. Click the role toggle (`Collector`, `Grid Operator`, `Citizens`). Switch language to Bengali (`বাংলা`) and Hindi (`हिन्दी`). Highlight the green `✓ Deterministic Validator: PASSED` banner. Click `Authorize & Dispatch`. Click `Inspect CAP 1.2 XML`.
* **Narrator:**
  > "Emergency advisories must be actionable and culturally grounded. Aegis-APAC generates role-specific advisories for District Collectors, power operators, and citizens in English, Bengali, Hindi, and Odia.
  > But here is our non-negotiable hard rule: **Gemini never generates or hallucinates numbers.**
  > Our automated validator verifies every single number, timestamp, and road name against the computed decision payload. If a discrepancy exists, it falls back to a deterministic safe template.
  > Only after human operator confirmation is the alert approved and exported to standard OASIS CAP 1.2 XML for broadcast."

---

### [2:45 - 3:00] Scene 6: Backtest Proof & Conclusion
* **Visual:** Switch to `Backtest` tab. Show the comparative table and slide-ready SVG vector charts.
* **Narrator:**
  > "The results speak for themselves. Backtested against Copernicus satellite observations, Aegis-APAC achieves an IoU of 0.693, increases facility warning lead times by **208%**, and reduces false alarms by **68%** compared to naive baselines.
  > Open standards, zero hallucinated numbers, and open data. Aegis-APAC: Protecting communities before the storm arrives."
