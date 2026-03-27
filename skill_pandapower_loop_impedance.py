"""可直接调用的合环回路阻抗 skill 实现。"""

from __future__ import annotations

import importlib
import importlib.util
import math
from typing import Any

import numpy as np

from power_tool_skill import execute_skill_request


JsonDict = dict[str, Any]


def _require(payload: JsonDict, key: str) -> Any:
    if key not in payload:
        raise ValueError(f"缺少必填参数: {key}")
    return payload[key]


def _resolve_bus_index(parsed: JsonDict, bus_ref: str | int) -> int:
    buses = list(parsed.get("buses", []))
    if isinstance(bus_ref, int):
        return bus_ref
    target = str(bus_ref).strip()
    if target.isdigit():
        return int(target)
    for b in buses:
        if str(b.get("name", "")).strip() == target:
            idx = b.get("index")
            if isinstance(idx, int):
                return idx
            if isinstance(idx, str) and idx.isdigit():
                return int(idx)
    raise ValueError(f"未找到母线: {bus_ref}")


def _complex_voltage_from_res_bus(row: Any) -> complex:
    vm = float(row["vm_pu"])
    va_rad = math.radians(float(row["va_degree"]))
    return vm * complex(math.cos(va_rad), math.sin(va_rad))


def compute_loop_impedance_ybus(model_path: str, bus_i: int, bus_j: int) -> JsonDict:
    if importlib.util.find_spec("pandapower") is None:
        raise RuntimeError("未安装 pandapower，请先安装后再运行该 skill。")
    if importlib.util.find_spec("scipy") is None:
        raise RuntimeError("未安装 scipy，Ybus 法需要 scipy.sparse 线性求解。")

    pp = importlib.import_module("pandapower")
    spsolve = importlib.import_module("scipy.sparse.linalg").spsolve

    net = pp.from_json(model_path)
    pp.runpp(net)

    ybus = net._ppc["internal"]["Ybus"]
    n = int(ybus.shape[0])

    e = np.zeros(n, dtype=complex)
    e[int(bus_i)] = 1.0
    e[int(bus_j)] = -1.0
    z_vec = spsolve(ybus, e)
    z_eq = complex(z_vec[int(bus_i)] - z_vec[int(bus_j)])

    return {
        "method": "ybus",
        "r_loop_ohm": float(z_eq.real),
        "x_loop_ohm": float(z_eq.imag),
        "z_abs_ohm": float(abs(z_eq)),
        "z_angle_deg": float(math.degrees(math.atan2(z_eq.imag, z_eq.real))),
    }


def run_skill(payload: JsonDict) -> JsonDict:
    """执行流程：解析模型 -> 计算合环阻抗 -> 组装 loop_closure 入参建议。"""
    try:
        model_path = str(_require(payload, "model_path"))
        bus_i_ref = _require(payload, "bus_i")
        bus_j_ref = _require(payload, "bus_j")
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    parsed_ret = execute_skill_request({"skill": "parse_pandapower_model", "args": {"model_path": model_path}})
    if not parsed_ret.get("ok"):
        return {"ok": False, "error": f"解析模型失败: {parsed_ret.get('error', 'unknown error')}"}

    parsed = dict(parsed_ret.get("result", {}))
    try:
        bus_i = _resolve_bus_index(parsed, bus_i_ref)
        bus_j = _resolve_bus_index(parsed, bus_j_ref)
        z = compute_loop_impedance_ybus(model_path, bus_i, bus_j)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    loop_args_hint = {
        "r_loop_ohm": z["r_loop_ohm"],
        "x_loop_ohm": z["x_loop_ohm"],
        "closure_pair": {"bus_i": bus_i, "bus_j": bus_j},
    }

    return {
        "ok": True,
        "parsed_model": {
            "inventory": parsed.get("inventory", {}),
            "adjacency": parsed.get("adjacency", {}),
        },
        "loop_impedance": z,
        "loop_closure_args_hint": loop_args_hint,
    }


__all__ = ["compute_loop_impedance_ybus", "run_skill"]
