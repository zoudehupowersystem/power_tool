"""场景3：母线电压越限治理（主网/配网分流）。"""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any


JsonDict = dict[str, Any]


def _require(payload: JsonDict, key: str) -> Any:
    if key not in payload:
        raise ValueError(f"缺少必填参数: {key}")
    return payload[key]


def _classify_grid(vn_kv: float) -> str:
    return "main_grid" if vn_kv >= 110.0 else "distribution_grid"


def run_skill(payload: JsonDict) -> JsonDict:
    try:
        model_path = str(_require(payload, "model_path"))
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    if importlib.util.find_spec("pandapower") is None:
        return {"ok": False, "error": "未安装 pandapower。"}

    pp = importlib.import_module("pandapower")
    try:
        net = pp.from_json(model_path)
        pp.runpp(net)
    except Exception as exc:
        return {"ok": False, "error": f"潮流运行失败: {exc}"}

    vmin = float(payload.get("vmin_pu", 0.95))
    vmax = float(payload.get("vmax_pu", 1.05))

    violated = []
    for bi, row in net.res_bus.iterrows():
        vm = float(row["vm_pu"])
        if vm < vmin or vm > vmax:
            violated.append({"bus": int(bi), "vm_pu": vm, "vn_kv": float(net.bus.at[bi, "vn_kv"])})

    if not violated:
        return {"ok": True, "message": "无越限母线", "violations": []}

    grid_type = _classify_grid(max(v["vn_kv"] for v in violated))
    if grid_type == "main_grid":
        opf_result = {"ok": False, "error": "runopp 未执行"}
        try:
            if hasattr(pp, "runopp"):
                pp.runopp(net)
                opf_result = {"ok": True, "min_vm_pu": float(net.res_bus["vm_pu"].min()), "max_vm_pu": float(net.res_bus["vm_pu"].max())}
        except Exception as exc:
            opf_result = {"ok": False, "error": str(exc)}

        return {"ok": True, "grid_type": grid_type, "violations": violated, "action": "pandapower_opf", "opf": opf_result}

    actions = []
    for v in violated:
        if v["vm_pu"] < vmin:
            actions.append({"bus": v["bus"], "action": "add_capacitor", "q_mvar": float(payload.get("cap_step_mvar", 2.0))})
            actions.append({"bus": v["bus"], "action": "raise_nearby_tap", "tap_step": int(payload.get("tap_step", 1))})
        else:
            actions.append({"bus": v["bus"], "action": "add_reactor", "q_mvar": float(payload.get("rea_step_mvar", 2.0))})
            actions.append({"bus": v["bus"], "action": "lower_nearby_tap", "tap_step": int(payload.get("tap_step", 1))})

    return {
        "ok": True,
        "grid_type": grid_type,
        "violations": violated,
        "action": "distribution_control_plan",
        "plan": actions,
        "assumptions": ["存在可投切电容器/电抗器", "相邻变压器具备可调档能力"],
    }


__all__ = ["run_skill"]
