from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import skill_nminus1_frequency_security as s1
import skill_smib_from_powerflow as s2
import skill_voltage_violation_governance as s3


def test_s1_requires_model_path() -> None:
    out = s1.run_skill({})
    assert out["ok"] is False


def test_s2_requires_model_path() -> None:
    out = s2.run_skill({})
    assert out["ok"] is False


def test_s3_requires_model_path() -> None:
    out = s3.run_skill({})
    assert out["ok"] is False


def test_s1_reports_missing_pandapower(monkeypatch) -> None:
    monkeypatch.setattr(s1.importlib.util, "find_spec", lambda name: None if name == "pandapower" else object())
    out = s1.run_skill({"model_path": "x.json"})
    assert out["ok"] is False


def test_s2_reports_missing_pandapower(monkeypatch) -> None:
    monkeypatch.setattr(s2.importlib.util, "find_spec", lambda name: None if name == "pandapower" else object())
    out = s2.run_skill({"model_path": "x.json"})
    assert out["ok"] is False


def test_s3_reports_missing_pandapower(monkeypatch) -> None:
    monkeypatch.setattr(s3.importlib.util, "find_spec", lambda name: None if name == "pandapower" else object())
    out = s3.run_skill({"model_path": "x.json"})
    assert out["ok"] is False
