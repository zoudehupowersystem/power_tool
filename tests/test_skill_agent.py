from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from local_agent import _extract_json, load_agent_config, maybe_bootstrap_dependencies
from power_tool_skill import execute_skill_request, list_skills


def test_skill_catalog_contains_composite_workflow() -> None:
    names = {item["name"] for item in list_skills()}
    assert "workflow_stability_screening" in names
    assert "frequency_dynamic" in names
    assert "short_circuit" in names
    assert "pandapower_power_flow" in names


def test_execute_skill_request_frequency_dynamic_success() -> None:
    payload = {
        "skill": "frequency_dynamic",
        "args": {
            "delta_p_ol0": 0.08,
            "Ts": 8.0,
            "TG": 5.0,
            "kD": 1.2,
            "kG": 4.0,
            "f0_hz": 50.0,
        },
    }
    result = execute_skill_request(payload)
    assert result["ok"] is True
    assert result["skill"] == "frequency_dynamic"
    assert result["result"]["regime"] == "欠阻尼"


def test_execute_skill_request_supports_composite_workflow() -> None:
    payload = {
        "skill": "workflow_stability_screening",
        "args": {
            "frequency": {
                "delta_p_ol0": 0.08,
                "Ts": 8.0,
                "TG": 5.0,
                "kD": 1.2,
                "kG": 4.0,
                "f0_hz": 50.0,
            },
            "impact": {"delta_p": 0.2, "delta_t_s": 0.1, "f_d_hz": 2.0, "p_current_pu": 0.9},
            "critical": {"Pm": 0.85, "Pmax_post": 1.9, "Tj": 9.0, "f0": 50.0, "delta_t_given": 0.12},
            "equal_area": {
                "Pm": 0.85,
                "Pmax_pre": 2.1,
                "Pmax_fault": 0.7,
                "Pmax_post": 1.9,
                "delta_t_s": 0.12,
                "Tj": 9.0,
                "f0": 50.0,
            },
        },
    }
    result = execute_skill_request(payload)
    assert result["ok"] is True
    assert "conclusion" in result["result"]
    assert "frequency_nadir_hz" in result["result"]["conclusion"]


def test_extract_json_accepts_markdown_code_block() -> None:
    text = """```json
{"action":"final","summary":"完成"}
```"""
    data = _extract_json(text)
    assert data["action"] == "final"
    assert data["summary"] == "完成"


def test_execute_skill_request_returns_error_on_missing_param() -> None:
    payload = {
        "skill": "frequency_dynamic",
        "args": {
            "delta_p_ol0": 0.08,
        },
    }
    result = execute_skill_request(payload)
    assert result["ok"] is False
    assert "缺少必填参数" in result["error"]


def test_install_python_packages_dry_run_prefers_pandapower() -> None:
    payload = {
        "skill": "install_python_packages",
        "args": {
            "packages": ["numpy", "pandapower", "scipy"],
            "allow_install": False,
            "preferred_packages": ["pandapower"],
        },
    }
    result = execute_skill_request(payload)
    assert result["ok"] is True
    assert result["result"]["dry_run"] is True
    assert result["result"]["install_order"][0] == "pandapower"


def test_load_agent_config_merges_user_override(tmp_path: Path) -> None:
    cfg_path = tmp_path / "local_agent_config.json"
    cfg_path.write_text(
        '{"provider":{"mode":"api","model":"qwen3.5-plus"},"agent":{"max_steps":3}}',
        encoding="utf-8",
    )
    cfg = load_agent_config(cfg_path)
    assert cfg["provider"]["mode"] == "api"
    assert cfg["provider"]["model"] == "qwen3.5-plus"
    assert cfg["agent"]["max_steps"] == 3
    assert cfg["tool_policy"]["preferred_packages"][0] == "pandapower"
    assert cfg["bootstrap"]["marker_file"] == ".powertool_bootstrap_done.json"


def test_pandapower_power_flow_reports_missing_dependency(monkeypatch) -> None:
    import importlib.util

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None if name == "pandapower" else object())
    payload = {
        "skill": "pandapower_power_flow",
        "args": {
            "buses": [{"name": "BUS1", "vn_kv": 110.0}, {"name": "BUS2", "vn_kv": 110.0}],
            "ext_grid": {"bus": "BUS1", "vm_pu": 1.0},
            "lines": [
                {
                    "from_bus": "BUS1",
                    "to_bus": "BUS2",
                    "r_ohm_per_km": 0.05,
                    "x_ohm_per_km": 0.2,
                    "length_km": 10.0,
                }
            ],
            "loads": [{"bus": "BUS2", "p_mw": 40.0, "q_mvar": 10.0}],
        },
    }
    result = execute_skill_request(payload)
    assert result["ok"] is False
    assert "未检测到 pandapower" in result["error"]


def test_bootstrap_installs_once_and_creates_marker(monkeypatch, tmp_path: Path) -> None:
    import local_agent

    calls: list[dict] = []

    def fake_exec(payload):
        calls.append(payload)
        return {"ok": True, "result": {"dry_run": False}}

    monkeypatch.setattr(local_agent, "execute_skill_request", fake_exec)
    marker = tmp_path / "bootstrap.json"
    cfg = {
        "bootstrap": {
            "install_pandapower_on_first_run": True,
            "marker_file": str(marker),
        }
    }
    first = maybe_bootstrap_dependencies(cfg)
    second = maybe_bootstrap_dependencies(cfg)
    assert first["ok"] is True and first["skipped"] is False
    assert second["ok"] is True and second["skipped"] is True
    assert marker.exists()
    assert len(calls) == 1
