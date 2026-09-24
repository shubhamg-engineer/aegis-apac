"""Phase 0 Sanity Tests: Verification of Setup, Rules, and Decisions."""

import os
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).parent.parent

def test_repo_structure_exists():
    """Verify all mandatory project directories exist."""
    required_dirs = [
        "contracts",
        "data/raw",
        "data/processed",
        "data/golden",
        "regions/bengal_delta",
        "src/ingest",
        "src/hazard",
        "src/graph",
        "src/decision",
        "src/parametric",
        "src/llm",
        "src/api",
        "src/backtest",
        "tests",
        "web",
        "docs",
    ]
    for rel_path in required_dirs:
        dir_path = REPO_ROOT / rel_path
        assert dir_path.is_dir(), f"Missing required directory: {rel_path}"

def test_agents_rules_file():
    """Verify AGENTS.md exists and contains the hard rules."""
    agents_file = REPO_ROOT / "AGENTS.md"
    assert agents_file.is_file(), "AGENTS.md missing"
    content = agents_file.read_text(encoding="utf-8")
    assert "Numbers come from code" in content
    assert "validated" in content
    assert "assumption: true" in content
    assert "Human approval" in content

def test_decisions_log_content():
    """Verify DECISIONS.md contains primary storm and limitations."""
    decisions_file = REPO_ROOT / "DECISIONS.md"
    assert decisions_file.is_file(), "DECISIONS.md missing"
    content = decisions_file.read_text(encoding="utf-8")
    assert "Cyclone Amphan" in content
    assert "Cyclone Dana" in content
    assert "bengal_delta" in content.lower()
    assert "Copernicus DEM" in content
    assert "CartoDB Positron" in content

def test_region_config_valid():
    """Verify regions/bengal_delta/config.yaml is valid YAML and has required fields."""
    config_file = REPO_ROOT / "regions" / "bengal_delta" / "config.yaml"
    assert config_file.is_file(), "region config.yaml missing"
    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    assert data["region"]["id"] == "bengal_delta"
    assert "min_lon" in data["aoi"]
    assert "max_lat" in data["aoi"]
    assert data["storms"]["primary_backtest"] == "amphan_2020"
    
    # Check 4 mandatory languages (EN, BN, HI, OR)
    lang_codes = [lang["code"] for lang in data["languages"]]
    for expected in ["en", "bn", "hi", "or"]:
        assert expected in lang_codes, f"Language {expected} not configured"

def test_env_example_exists():
    """Verify .env.example exists with critical keys."""
    env_example = REPO_ROOT / ".env.example"
    assert env_example.is_file(), ".env.example missing"
    content = env_example.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" in content
    assert "DEMO_MODE" in content
