import json
from pathlib import Path

GOLDEN_DIR = Path("data/golden/amphan-2020")

# Realistic multi-polygon probabilistic flood layers representing coastal storm surge and estuarine inundation
# Amphan Track: Making landfall near Sagar Island / Bakkhali, pushing high storm surge through Hooghly, Muriganga, and Matla estuaries.

hazard_data = {
    "type": "FeatureCollection",
    "features": [
        # ───────── T-24h (24h Pre-Landfall: Outer surge approaching southern coastal tip) ─────────
        {
            "type": "Feature",
            "properties": {
                "time_step_h": -24,
                "threshold_m": 0.3,
                "prob": 0.48,
                "level": "moderate",
                "label": "T-24h: P(depth > 0.3m) Coastal Fringe Surge"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [87.48, 21.58], [87.62, 21.63], [87.95, 21.52], [88.10, 21.55],
                        [88.28, 21.52], [88.45, 21.58], [88.75, 21.60], [89.05, 21.65],
                        [89.05, 21.52], [88.60, 21.42], [88.15, 21.40], [87.75, 21.45],
                        [87.48, 21.58]
                    ]
                ]
            }
        },

        # ───────── T-12h (12h Pre-Landfall: High surge advancing into Sagar Island, Namkhana & Digha) ─────────
        {
            "type": "Feature",
            "properties": {
                "time_step_h": -12,
                "threshold_m": 0.3,
                "prob": 0.74,
                "level": "high",
                "label": "T-12h: P(depth > 0.3m) Estuarine Surge Ingress"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [87.45, 21.60], [87.58, 21.66], [87.85, 21.68], [88.02, 21.72],
                        [88.12, 21.82], [88.25, 21.80], [88.35, 21.72], [88.55, 21.85],
                        [88.85, 21.90], [89.10, 21.80], [89.15, 21.55], [88.80, 21.50],
                        [88.40, 21.48], [88.05, 21.48], [87.70, 21.50], [87.45, 21.60]
                    ]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "time_step_h": -12,
                "threshold_m": 1.0,
                "prob": 0.52,
                "level": "severe",
                "label": "T-12h: P(depth > 1.0m) Critical Island Tips"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [88.02, 21.56], [88.14, 21.65], [88.22, 21.60], [88.30, 21.56],
                        [88.25, 21.50], [88.08, 21.50], [88.02, 21.56]
                    ]
                ]
            }
        },

        # ───────── T+0h (Landfall Peak: Widespread Severe & Catastrophic Inundation) ─────────
        {
            "type": "Feature",
            "properties": {
                "time_step_h": 0,
                "threshold_m": 0.3,
                "prob": 0.94,
                "level": "severe",
                "label": "T+0h: P(depth > 0.3m) Widespread Vehicle Cutoff Inundation"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [87.40, 21.62], [87.55, 21.68], [87.85, 21.75], [87.98, 21.95],
                        [88.08, 22.08], [88.18, 22.25], [88.32, 22.40], [88.50, 22.35],
                        [88.75, 22.38], [89.05, 22.30], [89.20, 22.10], [89.15, 21.65],
                        [88.75, 21.55], [88.40, 21.52], [88.00, 21.50], [87.65, 21.55],
                        [87.40, 21.62]
                    ]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "time_step_h": 0,
                "threshold_m": 1.0,
                "prob": 0.82,
                "level": "catastrophic",
                "label": "T+0h: P(depth > 1.0m) Severe Infrastructure Submergence Zone"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [87.96, 21.55], [88.10, 21.72], [88.22, 21.85], [88.30, 21.80],
                        [88.26, 21.65], [88.35, 21.60], [88.25, 21.52], [88.05, 21.50],
                        [87.96, 21.55]
                    ]
                ]
            }
        },

        # ───────── T+6h / T+12h (Receding Storm Surge & Drainage Runoff) ─────────
        {
            "type": "Feature",
            "properties": {
                "time_step_h": 12,
                "threshold_m": 0.3,
                "prob": 0.58,
                "level": "moderate",
                "label": "T+12h: P(depth > 0.3m) Residual Waterlogging"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [87.95, 21.58], [88.05, 21.72], [88.20, 21.78], [88.35, 21.70],
                        [88.30, 21.58], [88.10, 21.54], [87.95, 21.58]
                    ]
                ]
            }
        }
    ]
}

(GOLDEN_DIR / "hazard_layers.json").write_text(json.dumps(hazard_data, indent=2), encoding="utf-8")
print(f"Updated hazard_layers.json with {len(hazard_data['features'])} realistic multi-step flood polygons")
