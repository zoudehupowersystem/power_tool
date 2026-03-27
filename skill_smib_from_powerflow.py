"""场景2：考虑潮流运行点的发电机小扰动分析。"""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any

from power_tool_skill import execute_skill_request


JsonDict = dict[str, Any]


def _require(payload: JsonDict, key: str) -> Any:
    if key not in payload:
        raise ValueError(f"缺少必填参数: {key}")
    return payload[key]


def run_skill(payload: JsonDict) -> JsonDict:
    try:
        model_path = str(_require(payload, "model_path"))
        gen_index = int(payload.get("gen_index", 0))
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

    if gen_index not in net.gen.index:
        return {"ok": False, "error": f"发电机索引不存在: {gen_index}"}

    gen_bus = int(net.gen.at[gen_index, "bus"])
    p_mw = float(net.res_gen.at[gen_index, "p_mw"])
    vm_pu = float(net.res_bus.at[gen_bus, "vm_pu"])

    params = dict(payload.get("smib_params", {}))
    params.setdefault("Pm", max(0.1, min(1.2, p_mw / max(float(net.sn_mva), 1e-6))))
    params.setdefault("U", vm_pu)

    smib = execute_skill_request(
        {
            "skill": "smib_small_signal",
            "args": {"config": str(payload.get("smib_config", "工况与网络")), "params": params},
        }
    )
    if not smib.get("ok"):
        return {"ok": False, "error": f"SMIB 分析失败: {smib.get('error', 'unknown error')}"}

    return {"ok": True, "operating_point": {"gen_index": gen_index, "gen_bus": gen_bus, "p_mw": p_mw, "vm_pu": vm_pu}, "smib": smib["result"]}


__all__ = ["run_skill"]
