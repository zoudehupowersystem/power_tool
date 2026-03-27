from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from local_agent import (
    _extract_json,
    _inject_pip_source,
    build_markdown_report,
    load_agent_config,
    maybe_bootstrap_dependencies,
)
from power_tool_skill import execute_skill_request, list_skills


def test_skill_catalog_contains_composite_workflow() -> None:
    names = {item["name"] for item in list_skills()}
    assert "workflow_stability_screening" in names
    assert "frequency_dynamic" in names
    assert "short_circuit" in names
    assert "pandapower_power_flow" in names
    assert "parse_pandapower_model" in names


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


def test_install_python_packages_supports_index_url_options() -> None:
    payload = {
        "skill": "install_python_packages",
        "args": {
            "packages": ["pandapower"],
            "allow_install": False,
            "index_url": "https://mirrors.aliyun.com/pypi/simple",
            "trusted_host": "mirrors.aliyun.com",
            "extra_pip_args": ["--prefer-binary"],
        },
    }
    result = execute_skill_request(payload)
    assert result["ok"] is True
    cmd = result["result"]["command"]
    assert "-i" in cmd and "https://mirrors.aliyun.com/pypi/simple" in cmd
    assert "--trusted-host" in cmd and "mirrors.aliyun.com" in cmd
    assert "--prefer-binary" in cmd


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
    assert cfg["pip"]["index_mode"] == "default"


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
        },
        "pip": {"index_mode": "aliyun"},
    }
    first = maybe_bootstrap_dependencies(cfg)
    second = maybe_bootstrap_dependencies(cfg)
    assert first["ok"] is True and first["skipped"] is False
    assert second["ok"] is True and second["skipped"] is True
    assert marker.exists()
    assert len(calls) == 1
    assert calls[0]["args"]["index_url"] == "https://mirrors.aliyun.com/pypi/simple"


def test_inject_pip_source_can_switch_back_to_default() -> None:
    merged = _inject_pip_source({"packages": ["pandapower"]}, {"index_mode": "default"})
    assert "index_url" not in merged


def test_parse_pandapower_model_from_json_file(tmp_path: Path) -> None:
    model = {
        "bus": {
            "_object": "DataFrame",
            "columns": ["name", "vn_kv", "in_service"],
            "index": [0, 1],
            "data": [["BUS1", 110.0, True], ["BUS2", 110.0, True]],
        },
        "line": {
            "_object": "DataFrame",
            "columns": ["from_bus", "to_bus", "in_service"],
            "index": [0],
            "data": [[0, 1, True]],
        },
        "load": {
            "_object": "DataFrame",
            "columns": ["bus", "p_mw", "q_mvar"],
            "index": [0],
            "data": [[1, 40.0, 10.0]],
        },
    }
    f = tmp_path / "net.json"
    f.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    payload = {"skill": "parse_pandapower_model", "args": {"model_path": str(f)}}
    result = execute_skill_request(payload)
    assert result["ok"] is True
    parsed = result["result"]
    assert parsed["inventory"]["bus"] == 2
    assert parsed["inventory"]["line"] == 1
    assert "BUS2" in parsed["adjacency"]["BUS1"]


def test_build_markdown_report_contains_steps_and_summary() -> None:
    trace = [
        {"type": "tool", "content": {"ok": True, "skill": "frequency_dynamic", "result": {"f_min_hz": 49.1}}},
        {"type": "tool", "content": {"ok": False, "skill": "short_circuit", "error": "参数缺失"}},
    ]
    md = build_markdown_report("请评估系统安全性", trace, "建议先处理低频风险")
    assert "# PowerTool Agent 汇总报告" in md
    assert "Step 1" in md and "frequency_dynamic" in md
    assert "Step 2" in md and "short_circuit" in md
    assert "建议先处理低频风险" in md
