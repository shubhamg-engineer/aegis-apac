# Aegis-APAC: Simple Mode UI Spec (Citizen Home Screen)

**Purpose:** A second, radically simple screen so anyone in India can open the site, see if they're in danger, and know what to do — in seconds, no explanation needed. This does **not** replace the existing Cascade/Actions/Advisory/Backtest dashboard. That stays as the **Ops Console**, for officials and judges. This spec adds a **Citizen Home** screen that is the default landing page.

**Reference:** builds on `aegis-apac-prd-v2.md` (the citizen persona, FR-UI, FR-LLM advisory contract) and reuses existing backend data (`RiskResult`, `Advisory`, `ParametricResult`). No new hazard/cascade logic needed — this is a presentation layer.

---

## 1. Product structure (two tiers)

```
/                     -> Citizen Home  (default, this spec)
/console              -> existing Ops dashboard (Cascade/Actions/Advisory/Backtest)
```

A single small link/icon on Citizen Home, low-emphasis, labelled "For officials" or "Control Room", opens `/console`. Nothing on Citizen Home should look like a dashboard.

## 2. Design principle

**One glance, one answer.** The person should know two things within 2 seconds of the page loading, with no scrolling and no interpretation required:
1. Where the system thinks they are.
2. Whether they're in danger right now, and if so, what to do.

Everything else is optional, one tap away. No percentages, no jargon, no "P50/P95", no raw coordinates, no technical facility names on this screen — those stay in the Ops Console.

## 3. Screen layout (mobile-first, works on a 3-year-old Android phone)

```
┌─────────────────────────────┐
│  🌐 EN ▾        [Location▾]  │  <- language + location, always visible, top
│                               │
│                               │
│        [STATUS ICON]         │  <- huge, centered, one glance
│         SAFE                 │  <- one word, large type
│                               │
│   No cyclone threat in       │  <- one plain sentence
│   your area right now.       │
│                               │
│   Last checked: 2 min ago    │
│                               │
│  ┌─────────────────────────┐ │
│  │   What should I do?     │ │  <- appears ONLY if not Safe
│  └─────────────────────────┘ │
│                               │
│  ┌─────────────────────────┐ │
│  │   See map & details  ›  │ │  <- progressive disclosure
│  └─────────────────────────┘ │
│                               │
│         For officials         │  <- small, bottom, low emphasis
└─────────────────────────────┘
```

## 4. The four states

Map directly from existing `RiskResult` / `ParametricResult` data for the person's district — no new model needed, just an aggregation rule (section 7).

| State | Color | Icon | Headline | Body |
|---|---|---|---|---|
| **Safe** | Green | ✓ / calm | "SAFE" | "No cyclone threat in your area right now." |
| **Watch** | Yellow | eye / cloud | "STAY ALERT" | "A storm is forming. No action needed yet. We'll notify you if that changes." |
| **Warning** | Orange | triangle | "GET READY" | One plain sentence from the approved advisory, simplified (e.g. "Flooding possible in your area within 24 hours. Prepare to move if told to.") |
| **Danger** | Red, full-bleed background | siren | "TAKE ACTION NOW" | The single most important instruction from the approved advisory (e.g. "Evacuate to [shelter name] before [time].") |

Color, icon and headline must be readable without any text at all (color-blind-safe combinations too — don't rely on red/green alone; icon shape must also differ).

## 5. Progressive disclosure (tap to expand, never shown by default)

- **"What should I do?"** (Warning/Danger only) → expands to: the plain-language action, nearest shelter name and distance if evacuation applies, and a one-tap "Call emergency helpline" button. Pulls from the existing `Action`/`Advisory` objects, rewritten in plain language (see section 8).
- **"See map & details"** → opens a simplified map: just the flood zone shading and the person's location pin. No layer toggles, no time slider, no infrastructure icons by default. A small "Advanced view" link at the bottom of this map goes to `/console`.
- **Advisory text**, if the person wants it verbatim, is available as a second tap from "See map & details", not shown on Home.

## 6. Location

- On load, request browser geolocation. On success, silently resolve to the nearest district/region and show it in the top-right chip (e.g. "South 24 Parganas").
- If denied or unavailable, show a simple search box ("Search your city or district") — reuse the location search already built for the Ops Console.
- Never block the status screen waiting on location — show a neutral "Select your location" prompt state with no status icon until resolved, rather than a spinner over a blank screen.

## 7. Status aggregation rule (new, small piece of backend logic)

Add one lightweight endpoint: `GET /status?lat=&lon=` (or `?district=`) that:
1. Finds the nearest scenario/district match.
2. Takes the highest current facility failure probability and the parametric trigger probability for that district from existing `RiskResult`/`ParametricResult` data.
3. Maps to a state with fixed, documented thresholds (example, adjust in config): Safe if no active scenario; Watch if an active scenario exists but max probability < 30%; Warning if 30–70%; Danger if > 70% **or** an approved evacuation `Action` exists for that district.
4. Returns `{ state, headline, plain_message, last_updated, advisory_id? }`. The `plain_message` is pre-generated (see section 8), not written live by the frontend.

This is a thin read/aggregation layer over data that already exists — it does not duplicate the hazard or cascade engines.

## 8. Plain-language advisory rewriting

The existing advisory generator (FR-LLM-1) already produces a full, role-specific advisory for officials. For Citizen Home, add one more Gemini output alongside it, in the same generation step: a **one-sentence, plain-language citizen instruction**, same validator rules as the full advisory (every place/time named must exist in the input JSON, template fallback on failure). Do not write a second, separate citizen advisory pipeline — generate it as one more field in the existing advisory response schema.

Example: existing collector advisory → "URGENT: District South 24 Parganas. Predicted surge inundation reaches 0.62m at Sagar Island. 33kV Sagar Substation failure probability 88%..." becomes citizen line → "Move to Sagar Central Shelter before 4:00 AM."

## 9. Visual and technical rules

- **Fast first paint.** No 3D map, no heavy JS bundle on the Home route. Status screen must render from a single small API call.
- **Large type, high contrast**, works in direct sunlight and on small screens. Minimum body text ~16px, headline ~40px+.
- **Language switcher at the very top**, not buried in a menu — reuse the existing English/Hindi/Bengali/Odia set from the advisory panel.
- **No numbers on Home** unless absolutely necessary (a shelter distance in km is fine; a failure probability percentage is not).
- **Works offline-ish:** cache the last known status and show it with a clear "last updated" timestamp and an "offline — showing last known status" banner if the network call fails, rather than a blank error screen.
- Icons should be simple, universally recognizable shapes (checkmark, eye, triangle, siren) — avoid anything that needs a legend.

## 10. What NOT to change

- Do not remove, rename, or simplify anything in the existing Ops Console (`/console`). Judges evaluating technical depth still need the Cascade/Actions/Advisory/Backtest views exactly as built.
- Do not fork the hazard, cascade, or decision engines. Citizen Home reads from the same computed results.
- Do not build native apps or push notifications in this pass — that's future scope, mention it only in the roadmap slide.

## 11. Effort estimate (addition to the existing build plan)

| Task | Hours |
|---|---|
| `/status` aggregation endpoint | 1.5 |
| Citizen Home screen (all 4 states, location, language) | 3.5 |
| Simplified map view (flood shading + pin only) | 1.5 |
| Plain-language advisory field (schema + validator reuse) | 1.5 |
| **Total** | **~8** |

This fits inside the existing buffer in the 64-hour plan if the Ops Console work is otherwise on schedule; if not, this is the one thing worth protecting even over Ops Console polish, since it's what most judges and, more importantly, most real users will actually see first.

## 12. Instructions for the coding agent

1. Read this file plus `aegis-apac-prd-v2.md` sections 7 (journey), 8.9 (FR-UI) and 8.7 (FR-LLM).
2. Do not touch existing `/console` routes or components except to add the small "For officials" link out from Citizen Home.
3. Build the `/status` endpoint first, then the Citizen Home screen against mock data, then wire in the real endpoint, then add the plain-language advisory field.
4. Test on a throttled mobile network profile, not just desktop.
5. Report back what was built and what was assumed, same as every other phase.
