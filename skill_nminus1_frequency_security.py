"""场景1：潮流+频率 N-1 安全校核（可直接调用）。"""

from __future__ import annotations

import importlib
import importlib.util
from collections import defaultdict
from typing import Any

from power_tool_skill import execute_skill_request


JsonDict = dict[str, Any]


def _require(payload: JsonDict, key: str) -> Any:
    if key not in payload:
        raise ValueError(f"缺少必填参数: {key}")
    return payload[key]


def _load_net(model_path: str):
    if importlib.util.find_spec("pandapower") is None:
        raise RuntimeError("未安装 pandapower。")
    pp = importlib.import_module("pandapower")
    net = pp.from_json(model_path)
    return pp, net


def _run_flow_case(pp: Any, net: Any) -> JsonDict:
    pp.runpp(net)
    min_vm = float(net.res_bus["vm_pu"].min()) if len(net.res_bus) else 1.0
    max_line_loading = float(net.res_line["loading_percent"].max()) if len(net.res_line) else 0.0
    return {
        "min_vm_pu": min_vm,
        "max_line_loading_pct": max_line_loading,
        "undervoltage_buses": [int(i) for i, r in net.res_bus.iterrows() if float(r["vm_pu"]) < 0.95],
        "overload_lines": [int(i) for i, r in net.res_line.iterrows() if float(r["loading_percent"]) > 100.0],
    }


def run_skill(payload: JsonDict) -> JsonDict:
    try:
        model_path = str(_require(payload, "model_path"))
        contingencies = list(payload.get("contingencies", []))
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    try:
        pp, base_net = _load_net(model_path)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    freq_args = dict(payload.get("frequency_args", {}))
    freq_defaults = {
        "delta_p_ol0": 0.08,
        "Ts": 8.0,
        "TG": 5.0,
        "kD": 1.2,
        "kG": 4.0,
        "f0_hz": 50.0,
    }
    freq_defaults.update(freq_args)

    cases: list[JsonDict] = []
    critical_equipment = defaultdict(float)
    critical_sections = defaultdict(float)

    try:
        base_flow = _run_flow_case(pp, base_net)
    except Exception as exc:
        return {"ok": False, "error": f"基准潮流失败: {exc}"}

    for c in contingencies:
        case = dict(c)
        cid = str(case.get("id", "N-1"))
        ctype = str(case.get("type", "line_outage"))
        cidx = int(case.get("index", -1))

        net = pp.from_json(model_path)
        try:
            if ctype == "line_outage" and cidx >= 0 and cidx in net.line.index:
                net.line.at[cidx, "in_service"] = False
            elif ctype == "trafo_outage" and cidx >= 0 and cidx in net.trafo.index:
                net.trafo.at[cidx, "in_service"] = False

            flow = _run_flow_case(pp, net)
            freq = execute_skill_request({"skill": "frequency_dynamic", "args": freq_defaults})
            nadir = float(freq.get("result", {}).get("f_min_hz", 50.0)) if freq.get("ok") else 50.0
            severity = max(0.0, 0.95 - flow["min_vm_pu"]) * 100 + max(0.0, 49.0 - nadir) * 10

            for li in flow["overload_lines"]:
                critical_equipment[f"line:{li}"] += 1.0 + severity
                critical_sections[f"section_line_{li}"] += 1.0 + severity
            for bi in flow["undervoltage_buses"]:
                critical_equipment[f"bus:{bi}"] += 1.0 + severity

            cases.append(
                {
                    "id": cid,
                    "contingency": {"type": ctype, "index": cidx},
                    "flow": flow,
                    "frequency": freq,
                    "severity": severity,
                }
            )
        except Exception as exc:
            cases.append({"id": cid, "contingency": {"type": ctype, "index": cidx}, "ok": False, "error": str(exc)})

    key_equipment = [{"name": k, "score": v} for k, v in sorted(critical_equipment.items(), key=lambda kv: kv[1], reverse=True)[:10]]
    key_sections = [{"name": k, "score": v} for k, v in sorted(critical_sections.items(), key=lambda kv: kv[1], reverse=True)[:10]]

    return {"ok": True, "base_flow": base_flow, "cases": cases, "key_equipment": key_equipment, "key_sections": key_sections}


__all__ = ["run_skill"]
