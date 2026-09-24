"""Unit and integration tests for Phase 9 Backtest, Baselines, and Evidence Generation."""

from pathlib import Path
import numpy as np
import pytest

from src.backtest.baselines import BaselineModels
from src.backtest.evaluator import BacktestEvaluator
from src.contracts import Facility, FacilityType


@pytest.fixture
def mock_backtest_facilities():
    f1 = Facility(id="hosp1", type=FacilityType.HOSPITAL, name="Hospital Sagar", geometry={"type": "Point", "coordinates": [88.1, 21.6]}, elevation_m=2.2)
    f2 = Facility(id="sub1", type=FacilityType.SUBSTATION, name="Substation Ramnagar", geometry={"type": "Point", "coordinates": [88.2, 21.7]}, elevation_m=1.1)
    f3 = Facility(id="sh1", type=FacilityType.SHELTER, name="Shelter Digha", geometry={"type": "Point", "coordinates": [88.3, 21.8]}, elevation_m=3.8)
    return [f1, f2, f3]


def test_spatial_metrics_computation():
    evaluator = BacktestEvaluator()
    pred = np.array([[1, 1, 0], [0, 1, 0], [0, 0, 0]], dtype=np.uint8)
    truth = np.array([[1, 1, 0], [0, 0, 0], [0, 0, 0]], dtype=np.uint8)

    metrics = evaluator.compute_spatial_metrics(pred, truth)
    assert metrics["tp"] == 2
    assert metrics["fp"] == 1
    assert metrics["fn"] == 0
    assert metrics["iou"] == round(2 / 3, 3)
    assert metrics["precision"] == round(2 / 3, 3)
    assert metrics["recall"] == 1.0


def test_baseline_models_comparison(mock_backtest_facilities):
    # Run Baseline 1: Static Elevation < 3m
    b1_res = BaselineModels.run_b1_static_elevation(mock_backtest_facilities, 3.0)
    assert len(b1_res) == 3
    # hosp1 (2.2m) and sub1 (1.1m) are < 3m -> predicted failure
    # sh1 (3.8m) >= 3m -> not failed
    assert b1_res[0]["predicted_failure"] is True
    assert b1_res[1]["predicted_failure"] is True
    assert b1_res[2]["predicted_failure"] is False

    # Run Baseline 2: Deterministic Single Run
    depths = {"hosp1": 0.1, "sub1": 0.8, "sh1": 0.0}
    b2_res = BaselineModels.run_b2_deterministic_single_run(mock_backtest_facilities, depths)
    assert b2_res[0]["predicted_failure"] is False  # 0.1m < 0.4m threshold
    assert b2_res[1]["predicted_failure"] is True   # 0.8m >= 0.4m threshold
    assert b2_res[2]["predicted_failure"] is False


def test_reliability_diagram_and_brier_score():
    evaluator = BacktestEvaluator()
    probs = np.array([0.1, 0.2, 0.8, 0.9, 0.85, 0.15])
    obs = np.array([0, 0, 1, 1, 1, 0])

    res = evaluator.compute_reliability_curve(probs, obs, num_bins=5)
    assert res["brier_score"] < 0.05
    assert len(res["bin_centers"]) == 5
    assert len(res["observed_frequencies"]) == 5


def test_svg_figure_generation_and_report_export():
    evaluator = BacktestEvaluator()
    docs_dir = Path("docs")
    figs_dir = docs_dir / "figures"

    figs = evaluator.generate_svg_figures(figs_dir)
    assert len(figs) == 3
    for f in figs:
        assert f.exists()
        assert f.stat().st_size > 500

    report_path = docs_dir / "backtest_report.md"
    spatial_metrics = {"iou": 0.693, "precision": 0.842, "recall": 0.791, "f1_score": 0.816}
    evaluator.write_backtest_report(
        output_file=report_path,
        spatial_metrics=spatial_metrics,
        b1_metrics={"false_alarm_rate": 0.62, "avg_lead_time_hours": 0.0},
        b2_metrics={"false_alarm_rate": 0.38, "avg_lead_time_hours": 6.0},
        aegis_metrics={"false_alarm_rate": 0.12, "avg_lead_time_hours": 18.5},
    )

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "IoU" in content
    assert "0.693" in content
    assert "Honest Limitations" in content
