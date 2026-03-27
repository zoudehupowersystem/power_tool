"""PowerTool 面向 Agent 的技能层封装。"""

from __future__ import annotations

import json
import importlib
import importlib.util
import math
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

import numpy as np

from power_tool_approximations import (
    electromechanical_frequency,
    frequency_response_summary,
    natural_power_and_reactive,
    static_voltage_stability,
)
from power_tool_avc import simulate_avc_strategy
from power_tool_common import InputError
from power_tool_faults import short_circuit_capacity
from power_tool_loop_closure import loop_closure_analysis
from power_tool_params import convert_2wt_to_pu, convert_3wt_to_pu, convert_line_to_pu
from power_tool_pandapower_parser import parse_pandapower_model_dict, parse_pandapower_model_file
from power_tool_smib import kundur_smib_defaults, smib_small_signal_analysis
from power_tool_stability import critical_cut_angle_approx, equal_area_criterion, impact_method


class SkillExecutionError(RuntimeError):
    """技能调用异常。"""


JsonDict = dict[str, Any]
SkillFunc = Callable[[JsonDict], JsonDict]


def _jsonable(value: Any) -> Any:
    """将 dataclass / ndarray / complex 等对象转换为可 JSON 序列化结构。"""
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, complex):
        return {
            "re": value.real,
            "im": value.imag,
            "mag": abs(value),
            "angle_deg": math.degrees(math.atan2(value.imag, value.real)),
        }
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def _require(args: JsonDict, key: str) -> Any:
    if key not in args:
        raise SkillExecutionError(f"缺少必填参数: {key}")
    return args[key]


def _run_or_raise(func: Callable[..., Any], **kwargs: Any) -> JsonDict:
    try:
        result = func(**kwargs)
        return {"ok": True, "data": _jsonable(result)}
    except InputError as exc:
        raise SkillExecutionError(str(exc)) from exc


def skill_frequency_dynamic(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        frequency_response_summary,
        delta_p_ol0=float(_require(args, "delta_p_ol0")),
        Ts=float(_require(args, "Ts")),
        TG=float(_require(args, "TG")),
        kD=float(_require(args, "kD")),
        kG=float(_require(args, "kG")),
        f0_hz=float(args.get("f0_hz", 50.0)),
    )


def skill_electromechanical_frequency(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        electromechanical_frequency,
        Eq_prime=float(_require(args, "Eq_prime")),
        U=float(_require(args, "U")),
        X_sigma=float(_require(args, "X_sigma")),
        P0=float(_require(args, "P0")),
        Tj=float(_require(args, "Tj")),
        f0_hz=float(args.get("f0_hz", 50.0)),
    )


def skill_static_voltage_stability(args: JsonDict) -> JsonDict:
    s_base = args.get("s_base_mva")
    return _run_or_raise(
        static_voltage_stability,
        Ug=float(_require(args, "Ug")),
        X_sigma=float(_require(args, "X_sigma")),
        cos_phi=float(_require(args, "cos_phi")),
        s_base_mva=(None if s_base is None else float(s_base)),
    )


def skill_natural_power(args: JsonDict) -> JsonDict:
    zc = args.get("Zc_ohm")
    l_per = args.get("L_per_length")
    c_per = args.get("C_per_length")
    return _run_or_raise(
        natural_power_and_reactive,
        U_kV_ll=float(_require(args, "U_kV_ll")),
        Zc_ohm=(None if zc is None else float(zc)),
        L_per_length=(None if l_per is None else float(l_per)),
        C_per_length=(None if c_per is None else float(c_per)),
        P_MW=float(_require(args, "P_MW")),
        QN_Mvar_per_km=float(_require(args, "QN_Mvar_per_km")),
        length_km=float(_require(args, "length_km")),
    )


def skill_impact_method(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        impact_method,
        delta_p=float(_require(args, "delta_p")),
        delta_t_s=float(_require(args, "delta_t_s")),
        f_d_hz=float(_require(args, "f_d_hz")),
        p_current_pu=(None if args.get("p_current_pu") is None else float(args["p_current_pu"])),
    )


def skill_critical_cut(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        critical_cut_angle_approx,
        Pm=float(_require(args, "Pm")),
        Pmax_post=float(_require(args, "Pmax_post")),
        Tj=float(_require(args, "Tj")),
        f0=float(args.get("f0", 50.0)),
        delta_t_given=(None if args.get("delta_t_given") is None else float(args["delta_t_given"])),
    )


def skill_equal_area(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        equal_area_criterion,
        Pm=float(_require(args, "Pm")),
        Pmax_pre=float(_require(args, "Pmax_pre")),
        Pmax_fault=float(_require(args, "Pmax_fault")),
        Pmax_post=float(_require(args, "Pmax_post")),
        delta_t_s=float(_require(args, "delta_t_s")),
        Tj=float(_require(args, "Tj")),
        f0=float(args.get("f0", 50.0)),
    )


def skill_smib(args: JsonDict) -> JsonDict:
    params = kundur_smib_defaults()
    default_cfg = str(params.pop("config"))
    user_params = dict(args.get("params", {}))
    params.update(user_params)
    config_key = str(args.get("config", default_cfg))
    return _run_or_raise(smib_small_signal_analysis, config_key=config_key, params=params)


def skill_loop_closure(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        loop_closure_analysis,
        node_injections_A=list(_require(args, "node_injections_A")),
        closure_node_index=int(_require(args, "closure_node_index")),
        u1_kv_ll=float(_require(args, "u1_kv_ll")),
        u2_kv_ll=float(_require(args, "u2_kv_ll")),
        angle_deg=float(_require(args, "angle_deg")),
        r_loop_ohm=float(_require(args, "r_loop_ohm")),
        x_loop_ohm=float(_require(args, "x_loop_ohm")),
        frequency_hz=float(args.get("frequency_hz", 50.0)),
        node_labels=args.get("node_labels"),
        power_factor=float(args.get("power_factor", 0.99)),
        pf_mode=str(args.get("pf_mode", "lagging")),
        total_length_km=float(args.get("total_length_km", 0.0)),
        segment_ratios=args.get("segment_ratios"),
        ampacity_A=(None if args.get("ampacity_A") is None else float(args["ampacity_A"])),
        overload_factor=float(args.get("overload_factor", 1.5)),
        close_time_s=float(args.get("close_time_s", 0.10)),
        t_end_s=float(args.get("t_end_s", 0.30)),
        n_samples=int(args.get("n_samples", 2400)),
    )


def skill_short_circuit(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        short_circuit_capacity,
        U_kV_ll=float(_require(args, "U_kV_ll")),
        fault_type=str(_require(args, "fault_type")),
        s_sc_mva=float(_require(args, "s_sc_mva")),
        xr_sys=float(_require(args, "xr_sys")),
        line_len_km=float(_require(args, "line_len_km")),
        line_r1_ohm_km=float(_require(args, "line_r1_ohm_km")),
        line_x1_ohm_km=float(_require(args, "line_x1_ohm_km")),
        line_r0_ohm_km=float(_require(args, "line_r0_ohm_km")),
        line_x0_ohm_km=float(_require(args, "line_x0_ohm_km")),
        neutral_mode=str(_require(args, "neutral_mode")),
        neutral_rn_ohm=float(args.get("neutral_rn_ohm", 0.0)),
        neutral_xn_ohm=float(args.get("neutral_xn_ohm", 0.0)),
        Rf_ohm=float(args.get("Rf_ohm", 0.0)),
        breaker_IkA=(None if args.get("breaker_IkA") is None else float(args["breaker_IkA"])),
        network_mode=str(args.get("network_mode", "单电源")),
        s_sc_right_mva=(None if args.get("s_sc_right_mva") is None else float(args["s_sc_right_mva"])),
        xr_sys_right=(None if args.get("xr_sys_right") is None else float(args["xr_sys_right"])),
        fault_pos_from_left_pct=float(args.get("fault_pos_from_left_pct", 100.0)),
        e_left_pu=float(args.get("e_left_pu", 1.0)),
        e_right_pu=float(args.get("e_right_pu", 1.0)),
        delta_left_deg=float(args.get("delta_left_deg", 0.0)),
        delta_right_deg=float(args.get("delta_right_deg", 0.0)),
        neutral_mode_right=args.get("neutral_mode_right"),
        neutral_rn_right_ohm=(None if args.get("neutral_rn_right_ohm") is None else float(args["neutral_rn_right_ohm"])),
        neutral_xn_right_ohm=(None if args.get("neutral_xn_right_ohm") is None else float(args["neutral_xn_right_ohm"])),
    )


def skill_line_params(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        convert_line_to_pu,
        R1=float(_require(args, "R1")),
        X1=float(_require(args, "X1")),
        C1_uF=float(_require(args, "C1_uF")),
        length_km=float(_require(args, "length_km")),
        Sbase_MVA=float(_require(args, "Sbase_MVA")),
        Ubase_kV=float(_require(args, "Ubase_kV")),
    )


def skill_two_winding_params(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        convert_2wt_to_pu,
        Pk_kW=float(_require(args, "Pk_kW")),
        Uk_pct=float(_require(args, "Uk_pct")),
        P0_kW=float(_require(args, "P0_kW")),
        I0_pct=float(_require(args, "I0_pct")),
        SN_MVA=float(_require(args, "SN_MVA")),
        UN_kV=float(_require(args, "UN_kV")),
        Sbase_MVA=float(_require(args, "Sbase_MVA")),
        Ubase_kV=float(_require(args, "Ubase_kV")),
    )


def skill_three_winding_params(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        convert_3wt_to_pu,
        Pk_HM_kW=float(_require(args, "Pk_HM_kW")),
        Pk_HL_kW=float(_require(args, "Pk_HL_kW")),
        Pk_ML_kW=float(_require(args, "Pk_ML_kW")),
        Uk_HM_pct=float(_require(args, "Uk_HM_pct")),
        Uk_HL_pct=float(_require(args, "Uk_HL_pct")),
        Uk_ML_pct=float(_require(args, "Uk_ML_pct")),
        P0_kW=float(_require(args, "P0_kW")),
        I0_pct=float(_require(args, "I0_pct")),
        SN_H_MVA=float(_require(args, "SN_H_MVA")),
        SN_M_MVA=float(_require(args, "SN_M_MVA")),
        SN_L_MVA=float(_require(args, "SN_L_MVA")),
        UN_H_kV=float(_require(args, "UN_H_kV")),
        Sbase_MVA=float(_require(args, "Sbase_MVA")),
        Ubase_kV=float(_require(args, "Ubase_kV")),
    )


def skill_avc(args: JsonDict) -> JsonDict:
    return _run_or_raise(
        simulate_avc_strategy,
        hv_base=float(_require(args, "hv_base")),
        lv_base=float(_require(args, "lv_base")),
        vh=float(_require(args, "vh")),
        lv_min=float(_require(args, "lv_min")),
        lv_max=float(_require(args, "lv_max")),
        tap_min=int(_require(args, "tap_min")),
        tap_max=int(_require(args, "tap_max")),
        tap_now=int(_require(args, "tap_now")),
        tap_step_pct=float(_require(args, "tap_step_pct")),
        cap_num=int(_require(args, "cap_num")),
        cap_each=float(_require(args, "cap_each")),
        rea_num=int(_require(args, "rea_num")),
        rea_each=float(_require(args, "rea_each")),
        p_mw=float(_require(args, "p_mw")),
        q_mvar=float(_require(args, "q_mvar")),
        sys_sc_mva=float(_require(args, "sys_sc_mva")),
        tx_mva=float(_require(args, "tx_mva")),
        tx_uk_pct=float(_require(args, "tx_uk_pct")),
    )


def skill_install_python_packages(args: JsonDict) -> JsonDict:
    """安装 Python 包；默认优先安装 pandapower。"""
    requested = list(args.get("packages", []))
    if not requested:
        requested = ["pandapower"]

    preferred = list(args.get("preferred_packages", ["pandapower"]))
    deduped: list[str] = []
    for pkg in requested:
        name = str(pkg).strip()
        if name and name not in deduped:
            deduped.append(name)

    priority = [pkg for pkg in preferred if pkg in deduped]
    tail = [pkg for pkg in deduped if pkg not in priority]
    install_order = priority + tail

    allow_install = bool(args.get("allow_install", False))
    python_bin = str(args.get("python_bin", sys.executable))
    index_url = args.get("index_url")
    extra_index_url = args.get("extra_index_url")
    trusted_host = args.get("trusted_host")
    extra_pip_args = list(args.get("extra_pip_args", []))
    timeout = float(args.get("timeout_s", 600.0))

    base_cmd = [python_bin, "-m", "pip", "install", *install_order]
    if index_url:
        base_cmd.extend(["-i", str(index_url)])
    if extra_index_url:
        base_cmd.extend(["--extra-index-url", str(extra_index_url)])
    if trusted_host:
        base_cmd.extend(["--trusted-host", str(trusted_host)])
    for arg in extra_pip_args:
        base_cmd.append(str(arg))

    if not allow_install:
        return {
            "ok": True,
            "data": {
                "dry_run": True,
                "install_order": install_order,
                "command": base_cmd,
                "message": "未执行安装。若确认安装，请将 allow_install=true。",
            },
        }

    completed = subprocess.run(
        base_cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise SkillExecutionError(
            "安装失败: "
            + completed.stderr[-2000:].strip()
            + f" (code={completed.returncode})"
        )
    return {
        "ok": True,
        "data": {
            "dry_run": False,
            "install_order": install_order,
            "command": base_cmd,
            "stdout_tail": completed.stdout[-2000:],
        },
    }


def skill_pandapower_power_flow(args: JsonDict) -> JsonDict:
    """使用 pandapower 执行潮流计算。"""
    if importlib.util.find_spec("pandapower") is None:
        raise SkillExecutionError(
            "未检测到 pandapower。请先调用 install_python_packages 安装（建议优先 pandapower）。"
        )

    pp = importlib.import_module("pandapower")
    net = pp.create_empty_network(sn_mva=float(args.get("sn_mva", 100.0)))

    bus_map: dict[str, int] = {}
    for idx, bus in enumerate(list(_require(args, "buses"))):
        cfg = dict(bus)
        name = str(cfg.get("name", f"BUS{idx+1}"))
        bus_map[name] = pp.create_bus(
            net,
            vn_kv=float(cfg.get("vn_kv", 110.0)),
            name=name,
            type=str(cfg.get("type", "b")),
        )

    ext_grid = dict(_require(args, "ext_grid"))
    eg_bus = bus_map[str(_require(ext_grid, "bus"))]
    pp.create_ext_grid(
        net,
        bus=eg_bus,
        vm_pu=float(ext_grid.get("vm_pu", 1.0)),
        va_degree=float(ext_grid.get("va_degree", 0.0)),
    )

    for item in list(args.get("lines", [])):
        line = dict(item)
        pp.create_line_from_parameters(
            net,
            from_bus=bus_map[str(_require(line, "from_bus"))],
            to_bus=bus_map[str(_require(line, "to_bus"))],
            length_km=float(line.get("length_km", 1.0)),
            r_ohm_per_km=float(_require(line, "r_ohm_per_km")),
            x_ohm_per_km=float(_require(line, "x_ohm_per_km")),
            c_nf_per_km=float(line.get("c_nf_per_km", 0.0)),
            max_i_ka=float(line.get("max_i_ka", 1.0)),
            name=str(line.get("name", f"{line.get('from_bus')}-{line.get('to_bus')}")),
        )

    for item in list(args.get("loads", [])):
        load = dict(item)
        pp.create_load(
            net,
            bus=bus_map[str(_require(load, "bus"))],
            p_mw=float(_require(load, "p_mw")),
            q_mvar=float(load.get("q_mvar", 0.0)),
            name=str(load.get("name", "")),
        )

    for item in list(args.get("gens", [])):
        gen = dict(item)
        pp.create_gen(
            net,
            bus=bus_map[str(_require(gen, "bus"))],
            p_mw=float(_require(gen, "p_mw")),
            vm_pu=float(gen.get("vm_pu", 1.0)),
            name=str(gen.get("name", "")),
            slack=bool(gen.get("slack", False)),
        )

    pp.runpp(
        net,
        algorithm=str(args.get("algorithm", "nr")),
        init=str(args.get("init", "auto")),
        max_iteration=int(args.get("max_iteration", 50)),
        tolerance_mva=float(args.get("tolerance_mva", 1e-8)),
    )

    bus_results: list[dict[str, Any]] = []
    for _, row in net.res_bus.iterrows():
        bus_results.append(
            {
                "vm_pu": float(row["vm_pu"]),
                "va_degree": float(row["va_degree"]),
                "p_mw": float(row["p_mw"]),
                "q_mvar": float(row["q_mvar"]),
            }
        )

    line_results: list[dict[str, Any]] = []
    if hasattr(net, "res_line") and not net.res_line.empty:
        for _, row in net.res_line.iterrows():
            line_results.append(
                {
                    "loading_pct": float(row["loading_percent"]),
                    "p_from_mw": float(row["p_from_mw"]),
                    "q_from_mvar": float(row["q_from_mvar"]),
                    "i_from_ka": float(row["i_from_ka"]),
                }
            )

    min_vm = min((r["vm_pu"] for r in bus_results), default=1.0)
    max_line_loading = max((r["loading_pct"] for r in line_results), default=0.0)
    summary = {
        "converged": bool(getattr(net, "converged", False)),
        "min_vm_pu": min_vm,
        "max_line_loading_pct": max_line_loading,
    }
    return {"ok": True, "data": {"summary": summary, "buses": bus_results, "lines": line_results}}


def skill_parse_pandapower_model(args: JsonDict) -> JsonDict:
    """解析 pandapower 模型文件或对象，返回设备清单与拓扑连接。"""
    model_path = args.get("model_path")
    if model_path:
        parsed = parse_pandapower_model_file(str(model_path))
        return {"ok": True, "data": parsed}

    net_obj = args.get("model")
    if isinstance(net_obj, dict):
        parsed = parse_pandapower_model_dict(dict(net_obj))
        return {"ok": True, "data": parsed}

    raise SkillExecutionError("请提供 model_path（pandapower JSON 文件）或 model（字典对象）。")


def workflow_stability_screening(args: JsonDict) -> JsonDict:
    """组合调用：频率动态 + 冲击法 + 临界切除角 + 等面积法。"""
    freq_args = dict(_require(args, "frequency"))
    impact_args = dict(_require(args, "impact"))
    critical_args = dict(_require(args, "critical"))
    eac_args = dict(_require(args, "equal_area"))

    freq = skill_frequency_dynamic(freq_args)
    impact = skill_impact_method(impact_args)
    critical = skill_critical_cut(critical_args)
    eac = skill_equal_area(eac_args)

    stable = bool(eac["data"]["stable"])
    rocof_hz = float(freq["data"]["rocof_hz_s"])
    nadir = float(freq["data"]["f_min_hz"])

    conclusion = {
        "frequency_risk": "high" if nadir < float(args.get("freq_alarm_hz", 49.0)) else "normal",
        "transient_stability": "stable" if stable else "unstable",
        "rocof_hz_s": rocof_hz,
        "frequency_nadir_hz": nadir,
    }
    return {
        "ok": True,
        "data": {
            "frequency": freq["data"],
            "impact": impact["data"],
            "critical": critical["data"],
            "equal_area": eac["data"],
            "conclusion": conclusion,
        },
    }


SKILL_REGISTRY: dict[str, SkillFunc] = {
    "frequency_dynamic": skill_frequency_dynamic,
    "electromechanical_frequency": skill_electromechanical_frequency,
    "static_voltage_stability": skill_static_voltage_stability,
    "natural_power": skill_natural_power,
    "impact_method": skill_impact_method,
    "critical_cut": skill_critical_cut,
    "equal_area": skill_equal_area,
    "smib_small_signal": skill_smib,
    "loop_closure": skill_loop_closure,
    "short_circuit": skill_short_circuit,
    "line_params": skill_line_params,
    "two_winding_params": skill_two_winding_params,
    "three_winding_params": skill_three_winding_params,
    "avc_strategy": skill_avc,
    "install_python_packages": skill_install_python_packages,
    "parse_pandapower_model": skill_parse_pandapower_model,
    "pandapower_power_flow": skill_pandapower_power_flow,
    "workflow_stability_screening": workflow_stability_screening,
}


SKILL_DESCRIPTIONS: dict[str, str] = {
    "frequency_dynamic": "频率动态二阶模型，输出 RoCoF、nadir、稳态频差。",
    "electromechanical_frequency": "机电振荡频率快估。",
    "static_voltage_stability": "二节点静态电压稳定极限估算。",
    "natural_power": "长线路自然功率与无功行为快估。",
    "impact_method": "冲击法第一摆振荡幅值快估。",
    "critical_cut": "临界切除角/时间近似计算。",
    "equal_area": "单机无穷大等面积法稳定性计算。",
    "smib_small_signal": "SMIB 小扰动分析（特征值/稳定性）。",
    "loop_closure": "配电网合环稳态与暂态近似分析。",
    "short_circuit": "短路电流计算。",
    "line_params": "架空线路参数折算到标幺。",
    "two_winding_params": "两绕组变压器参数折算到标幺。",
    "three_winding_params": "三绕组三绕组变压器参数折算到标幺。",
    "avc_strategy": "AVC 策略模拟。",
    "install_python_packages": "安装 Python 包（默认优先 pandapower，可 dry-run）。",
    "parse_pandapower_model": "解析 pandapower 模型文件，提取设备清单与拓扑连接。",
    "pandapower_power_flow": "基于 pandapower 的电网潮流计算（PowerTool 与潮流能力融合）。",
    "workflow_stability_screening": "组合工作流：频率+暂稳联合筛查。",
}


def list_skills() -> list[dict[str, str]]:
    return [{"name": name, "description": SKILL_DESCRIPTIONS[name]} for name in sorted(SKILL_REGISTRY)]


def execute_skill(name: str, args: JsonDict) -> JsonDict:
    fn = SKILL_REGISTRY.get(name)
    if fn is None:
        raise SkillExecutionError(f"未知技能: {name}")
    try:
        return fn(dict(args))
    except SkillExecutionError:
        raise
    except Exception as exc:
        raise SkillExecutionError(f"技能 {name} 执行失败: {exc}") from exc


def execute_skill_request(payload: JsonDict) -> JsonDict:
    """统一请求入口，便于被 HTTP/MCP/CLI 包装调用。"""
    skill = str(_require(payload, "skill"))
    args = dict(payload.get("args", {}))
    try:
        result = execute_skill(skill, args)
        return {"ok": True, "skill": skill, "result": result.get("data", result)}
    except SkillExecutionError as exc:
        return {"ok": False, "skill": skill, "error": str(exc)}


def format_skill_catalog() -> str:
    rows = [f"- {item['name']}: {item['description']}" for item in list_skills()]
    return "\n".join(rows)


def load_json_payload(text: str) -> JsonDict:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise SkillExecutionError("JSON 顶层必须为对象。")
    return data


__all__ = [
    "SkillExecutionError",
    "SKILL_REGISTRY",
    "SKILL_DESCRIPTIONS",
    "execute_skill",
    "execute_skill_request",
    "format_skill_catalog",
    "list_skills",
    "load_json_payload",
]
