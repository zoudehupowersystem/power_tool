from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import skill_pandapower_loop_impedance as s


def test_run_skill_requires_params() -> None:
    out = s.run_skill({})
    assert out["ok"] is False
    assert "缺少必填参数" in out["error"]


def test_run_skill_success_with_mock(monkeypatch) -> None:
    def fake_exec(payload):
        assert payload["skill"] == "parse_pandapower_model"
        return {
            "ok": True,
            "result": {
                "inventory": {"bus": 2},
                "adjacency": {"BUS1": ["BUS2"]},
                "buses": [
                    {"index": 0, "name": "BUS1"},
                    {"index": 1, "name": "BUS2"},
                ],
            },
        }

    def fake_z(model_path: str, bus_i: int, bus_j: int):
        assert model_path == "demo.json"
        assert bus_i == 0
        assert bus_j == 1
        return {"method": "ybus", "r_loop_ohm": 1.1, "x_loop_ohm": 3.3, "z_abs_ohm": 3.48, "z_angle_deg": 71.6}

    monkeypatch.setattr(s, "execute_skill_request", fake_exec)
    monkeypatch.setattr(s, "compute_loop_impedance_ybus", fake_z)

    out = s.run_skill({"model_path": "demo.json", "bus_i": "BUS1", "bus_j": "BUS2"})
    assert out["ok"] is True
    assert out["loop_impedance"]["r_loop_ohm"] == 1.1
    assert out["loop_closure_args_hint"]["closure_pair"]["bus_i"] == 0
