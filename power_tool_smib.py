"""Small-signal analysis kernel for the single-machine infinite-bus (SMIB) system. / 单机无穷大系统（SMIB）小扰动分析内核。"""


from __future__ import annotations


import math


from typing import Optional


import numpy as np


from power_tool_common import (
    EPS,
    InputError,
    SMIBOperatingPoint,
    SMIBSmallSignalResult,
    _validate_positive,
    _validate_nonnegative,
)


_SMIB_CONFIG_OPTIONS = [
    "六阶机组",
    "六阶机组 + AVR",
    "六阶机组 + AVR + PSS",
]

_SMIB_CONFIG_KEY = {
    "六阶机组": "machine",
    "六阶机组 + AVR": "avr",
    "六阶机组 + AVR + PSS": "avr_pss",
}

_SMIB_STATE_LABELS = {
    "delta": "δ",
    "w": "ω",
    "e1q": "e'q",
    "e1d": "e'd",
    "e2q": "e''q",
    "e2d": "e''d",
    "vm": "v_m",
    "vr": "v_r",
    "vf1": "v_f",
    "xw": "x_w",
    "xll1": "x_ll1",
    "xll2": "x_ll2",
}

def kundur_smib_defaults() -> dict[str, float | str]:
    """Default data set from Kundur, Power System Stability and Control, Example 13.2, and the OpenIPSL KundurSMIB case. / Kundur《Power System Stability and Control》Example 13.2 / OpenIPSL KundurSMIB 默认值。"""
    return {
        "config": "六阶机组 + AVR + PSS",
        "P0": 0.90,
        "Q0": 0.436002238697,
        "Vt": 1.00,
        "theta_deg": 28.342914463,
        "xT": 0.15,
        "xL1": 0.50,
        "xL2": 0.93,
        "f0": 60.0,
        "ra": 0.003,
        "xd": 1.81,
        "xq": 1.76,
        "x1d": 0.30,
        "x1q": 0.65,
        "x2d": 0.23,
        "x2q": 0.25,
        "T1d0": 8.0,
        "T1q0": 1.0,
        "T2d0": 0.03,
        "T2q0": 0.07,
        "M": 7.0,
        "D": 0.0,
        "avr_K0": 200.0,
        "avr_T1": 1.0,
        "avr_T2": 1.0,
        "avr_Te": 1.0e-4,
        "avr_Tr": 0.015,
        "avr_vfmax": 7.0,
        "avr_vfmin": -6.40,
        "pss_Kw": 9.5,
        "pss_Tw": 1.41,
        "pss_T1": 0.154,
        "pss_T2": 0.033,
        "pss_T3": 1.0,
        "pss_T4": 1.0,
        "pss_vsmax": 0.2,
        "pss_vsmin": -0.2,
    }

def _smib_state_names(config_key: str) -> list[str]:
    if config_key == "machine":
        return ["delta", "w", "e1q", "e1d", "e2q", "e2d"]
    if config_key == "avr":
        return ["delta", "w", "e1q", "e1d", "e2q", "e2d", "vm", "vr", "vf1"]
    if config_key == "avr_pss":
        return ["delta", "w", "e1q", "e1d", "e2q", "e2d", "vm", "vr", "vf1", "xw", "xll1", "xll2"]
    raise InputError(f"不支持的小扰动配置：{config_key}")

def _smib_parallel_reactance(values: list[float]) -> float:
    active = [v for v in values if v > EPS]
    if not active:
        raise InputError("至少需要一回线路投入（X_line > 0）。")
    inv = sum(1.0 / v for v in active)
    if inv <= EPS:
        raise InputError("并联线路等值电抗计算失败，请检查 X_line 输入。")
    return 1.0 / inv

def _smib_clip(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)

def _smib_build_operating_point(params: dict[str, float]) -> dict[str, float]:
    """Construct a steady operating point that is consistent with the infinite-bus reference angle from terminal power, terminal voltage, and network reactance. / 根据端口功率、端电压与网络电抗构造与无穷大母线参考角一致的平衡点。
    
    Conventions / 约定：
    - All quantities share the same per-unit base; in the Kundur example, the machine base equals the system base. / 所有量均在同一标幺基准下（Kundur 示例中机器基准 = 系统基准）。
    - The infinite-bus angle is shifted to 0° so that the resulting SMIB equilibrium point is self-consistent. / 将无穷大母线相角平移为 0°，从而得到自洽的 SMIB 平衡点。"""
    P0 = params["P0"]
    Q0 = params["Q0"]
    Vt_mag = params["Vt"]
    theta_deg = params["theta_deg"]
    xT = params["xT"]
    xL1 = params["xL1"]
    xL2 = params["xL2"]

    _validate_positive("端电压幅值 Vt", Vt_mag)
    _validate_positive("变压器电抗 xT", xT)
    _validate_nonnegative("线路电抗 xL1", xL1)
    _validate_nonnegative("线路电抗 xL2", xL2)

    xline_eq = _smib_parallel_reactance([xL1, xL2])
    xnet = xT + xline_eq
    _validate_positive("网络总电抗 Xnet", xnet)

    theta = math.radians(theta_deg)
    Vt = complex(Vt_mag * math.cos(theta), Vt_mag * math.sin(theta))
    I = (P0 - 1j * Q0) / Vt.conjugate()
    E_inf = Vt - 1j * xnet * I
    Vinf = abs(E_inf)
    _validate_positive("无穷大母线电压幅值 V∞", Vinf)

    theta_ref = math.atan2(E_inf.imag, E_inf.real)
    rot = complex(math.cos(-theta_ref), math.sin(-theta_ref))
    Vt_ref = Vt * rot
    I_ref = I * rot

    ra = params["ra"]
    xq = params["xq"]
    xd = params["xd"]
    x1d = params["x1d"]
    x1q = params["x1q"]
    x2d = params["x2d"]
    x2q = params["x2q"]
    T1d0 = params["T1d0"]
    T1q0 = params["T1q0"]
    T2d0 = params["T2d0"]
    T2q0 = params["T2q0"]
    Taa = params.get("Taa", 0.0)

    for name, value in [
        ("ra", ra), ("xd", xd), ("xq", xq), ("x'd", x1d), ("x'q", x1q),
        ("x''d", x2d), ("x''q", x2q), ("T'd0", T1d0), ("T'q0", T1q0),
        ("T''d0", T2d0), ("T''q0", T2q0),
    ]:
        _validate_positive(name, value)

    rotor_internal = Vt_ref + (ra + 1j * xq) * I_ref
    delta0 = math.atan2(rotor_internal.imag, rotor_internal.real)
    if not (0.0 < delta0 < math.pi):
        raise InputError("初始化得到的转子功角 δ0 不在 (0, π) 内，请检查工况和参数。")

    rot_dq = complex(math.cos(-delta0), math.sin(-delta0))
    Vdq = Vt_ref * rot_dq
    Idq = I_ref * rot_dq
    vq0 = Vdq.real
    vd0 = -Vdq.imag
    iq0 = Idq.real
    id0 = -Idq.imag

    e2q0 = vq0 + ra * iq0 + x2d * id0
    e2d0 = vd0 + ra * id0 - x2q * iq0
    e1d0 = (xq - x1q - T2q0 * x2q * (xq - x1q) / (T1q0 * x1q)) * iq0
    K1 = xd - x1d - T2d0 * x2d * (xd - x1d) / (T1d0 * x1d)
    K2 = x1d - x2d + T2d0 * x2d * (xd - x1d) / (T1d0 * x1d)
    e1q0 = e2q0 + K2 * id0 - Taa / T1d0 * ((K1 + K2) * id0 + e2q0)
    vf0 = (K1 * id0 + e1q0) / (1.0 - Taa / T1d0)
    pm0 = (vq0 + ra * iq0) * iq0 + (vd0 + ra * id0) * id0

    return {
        "xline_eq": xline_eq,
        "xnet": xnet,
        "Vinf": Vinf,
        "theta_ref": theta_ref,
        "Vt_ref_ang_deg": math.degrees(math.atan2(Vt_ref.imag, Vt_ref.real)),
        "delta0": delta0,
        "vd0": vd0,
        "vq0": vq0,
        "id0": id0,
        "iq0": iq0,
        "e1q0": e1q0,
        "e1d0": e1d0,
        "e2q0": e2q0,
        "e2d0": e2d0,
        "vf0": vf0,
        "pm0": pm0,
    }

def _smib_network_algebraic(delta: float, e2q: float, e2d: float,
                            params: dict[str, float],
                            op: dict[str, float]) -> tuple[float, float, float, float, float, float, float, float]:
    """Eliminate the network algebraic equations and return id, iq, vd, vq, v, pe, P, and Q. / 消去网络代数方程，返回 id、iq、vd、vq、v、pe、P、Q。"""
    ra = params["ra"]
    x2d = params["x2d"]
    x2q = params["x2q"]
    xnet = op["xnet"]
    Vinf = op["Vinf"]

    a11 = xnet + x2d
    a12 = ra
    a21 = ra
    a22 = -(xnet + x2q)
    det = a11 * a22 - a12 * a21
    if abs(det) < 1e-12:
        raise InputError("机端代数方程奇异，请检查 xnet、x''d、x''q 与 ra 的组合。")

    b1 = e2q - Vinf * math.cos(delta)
    b2 = e2d - Vinf * math.sin(delta)
    id_ = (b1 * a22 - a12 * b2) / det
    iq = (a11 * b2 - a21 * b1) / det

    vq = Vinf * math.cos(delta) + xnet * id_
    vd = Vinf * math.sin(delta) - xnet * iq
    v = math.hypot(vd, vq)
    pe = (vq + ra * iq) * iq + (vd + ra * id_) * id_
    P = vq * iq + vd * id_
    Q = vq * id_ - vd * iq
    return id_, iq, vd, vq, v, pe, P, Q

def _smib_state_vector_init(config_key: str, params: dict[str, float],
                            op: dict[str, float]) -> np.ndarray:
    states: list[float] = [
        op["delta0"],
        1.0,
        op["e1q0"],
        op["e1d0"],
        op["e2q0"],
        op["e2d0"],
    ]
    if config_key in {"avr", "avr_pss"}:
        states.extend([params["Vt"], 0.0, op["vf0"]])
    if config_key == "avr_pss":
        states.extend([0.0, 0.0, 0.0])
    return np.asarray(states, dtype=float)

def _smib_rhs(x: np.ndarray, config_key: str, params: dict[str, float],
              op: dict[str, float]) -> tuple[np.ndarray, dict[str, float]]:
    names = _smib_state_names(config_key)
    s = dict(zip(names, x))

    delta = float(s["delta"])
    w = float(s["w"])
    e1q = float(s["e1q"])
    e1d = float(s["e1d"])
    e2q = float(s["e2q"])
    e2d = float(s["e2d"])

    id_, iq, vd, vq, v, pe, P, Q = _smib_network_algebraic(delta, e2q, e2d, params, op)
    pm = op["pm0"]

    vf = op["vf0"]
    vs = 0.0
    extra: list[float] = []

    if config_key in {"avr", "avr_pss"}:
        vm = float(s["vm"])
        vr = float(s["vr"])
        vf1 = float(s["vf1"])

        if config_key == "avr_pss":
            dw = w - 1.0
            xw = float(s["xw"])
            xll1 = float(s["xll1"])
            xll2 = float(s["xll2"])

            Tw = params["pss_Tw"]
            T1p = params["pss_T1"]
            T2p = params["pss_T2"]
            T3p = params["pss_T3"]
            T4p = params["pss_T4"]
            Kw = params["pss_Kw"]

            dxw = (dw - xw) / Tw
            yw = Kw * (dw - xw)
            dxll1 = (yw - xll1) / T2p
            y1 = (T1p / T2p) * (yw - xll1) + xll1
            dxll2 = (y1 - xll2) / T4p
            y2 = (T3p / T4p) * (y1 - xll2) + xll2
            vs = _smib_clip(y2, params["pss_vsmin"], params["pss_vsmax"])
            extra.extend([dxw, dxll1, dxll2])

        K0 = params["avr_K0"]
        T1a = params["avr_T1"]
        T2a = params["avr_T2"]
        Te = params["avr_Te"]
        Tr = params["avr_Tr"]
        vref = params["Vt"]

        dvm = (v - vm) / Tr
        dvr = (K0 * (1.0 - T1a / T2a) * (vref + vs - vm) - vr) / T2a
        dvf1 = (vr + K0 * (T1a / T2a) * (vref + vs - vm) + op["vf0"] - vf1) / Te
        vf = _smib_clip(vf1, params["avr_vfmin"], params["avr_vfmax"])
        extra = [dvm, dvr, dvf1] + extra

    xd = params["xd"]
    xq = params["xq"]
    x1d = params["x1d"]
    x1q = params["x1q"]
    x2d = params["x2d"]
    x2q = params["x2q"]
    T1d0 = params["T1d0"]
    T1q0 = params["T1q0"]
    T2d0 = params["T2d0"]
    T2q0 = params["T2q0"]
    Taa = params.get("Taa", 0.0)
    M = params["M"]
    D = params["D"]
    wb = 2.0 * math.pi * params["f0"]

    K1 = xd - x1d - T2d0 * x2d * (xd - x1d) / (T1d0 * x1d)
    K2 = x1d - x2d + T2d0 * x2d * (xd - x1d) / (T1d0 * x1d)
    Kq1 = xq - x1q - T2q0 * x2q * (xq - x1q) / (T1q0 * x1q)
    Kq2 = x1q - x2q + T2q0 * x2q * (xq - x1q) / (T1q0 * x1q)

    ddelta = wb * (w - 1.0)
    dw = (pm - pe - D * (w - 1.0)) / M
    de1q = (-e1q - K1 * id_ + (1.0 - Taa / T1d0) * vf) / T1d0
    de1d = (-e1d + Kq1 * iq) / T1q0
    de2q = (-e2q + e1q - K2 * id_ + Taa / T1d0 * vf) / T2d0
    de2d = (-e2d + e1d + Kq2 * iq) / T2q0

    base = [ddelta, dw, de1q, de1d, de2q, de2d]
    rhs = np.asarray(base + extra, dtype=float)
    aux = {
        "v": v, "vd": vd, "vq": vq, "id": id_, "iq": iq, "pe": pe,
        "P": P, "Q": Q, "vf": vf, "vs": vs,
    }
    return rhs, aux

def _smib_numerical_jacobian(fun, x0: np.ndarray) -> np.ndarray:
    x0 = np.asarray(x0, dtype=float)
    n = len(x0)
    J = np.zeros((n, n), dtype=float)
    for k in range(n):
        h = 1e-6 * max(1.0, abs(x0[k]))
        x1 = x0.copy(); x1[k] += h
        x2 = x0.copy(); x2[k] -= h
        f1 = fun(x1)
        f2 = fun(x2)
        J[:, k] = (f1 - f2) / (2.0 * h)
    return J

def _smib_dominant_mode_index(eigs: np.ndarray) -> Optional[int]:
    osc = [i for i, lam in enumerate(eigs) if lam.imag > 1e-7]
    if osc:
        return max(osc, key=lambda i: eigs[i].real)
    if len(eigs) == 0:
        return None
    return int(np.argmax(np.real(eigs)))

def _smib_mode_participation(A: np.ndarray, eigs: np.ndarray,
                             state_names: list[str],
                             mode_idx: Optional[int]) -> list[tuple[str, float]]:
    if mode_idx is None or A.size == 0:
        return []
    _, vr = np.linalg.eig(A)
    vl = np.linalg.pinv(vr).T
    part = np.abs(vr[:, mode_idx] * vl[:, mode_idx])
    total = float(np.sum(part))
    if total <= 1e-16:
        return []
    normalized = part / total
    ranked = sorted(zip(state_names, normalized), key=lambda kv: kv[1], reverse=True)
    return [(name, float(weight)) for name, weight in ranked[:6]]

def _format_eigenvalue(lam: complex) -> str:
    if abs(lam.imag) < 1e-8:
        return f"{lam.real:+.6f}"
    sign = "+" if lam.imag >= 0 else "-"
    return f"{lam.real:+.6f} {sign} j{abs(lam.imag):.6f}"

def _smib_modal_rows(eigs: np.ndarray) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    kept = [lam for lam in eigs if lam.imag >= -1e-8]
    kept.sort(key=lambda lam: (lam.real, abs(lam.imag)), reverse=True)
    for idx, lam in enumerate(kept, start=1):
        freq = abs(lam.imag) / (2.0 * math.pi)
        if abs(lam.imag) < 1e-8:
            zeta = None
            mode_type = "实根"
        else:
            zeta = -lam.real / abs(lam)
            mode_type = "振荡"
        rows.append({
            "idx": idx,
            "lambda": lam,
            "freq": freq,
            "zeta": zeta,
            "type": mode_type,
        })
    return rows

def smib_small_signal_analysis(config_key: str, params: dict[str, float]) -> SMIBSmallSignalResult:
    config_key = _SMIB_CONFIG_KEY.get(config_key, config_key)

    _validate_positive("额定频率 f0", params["f0"])
    _validate_positive("机械起动时间 M", params["M"])
    _validate_nonnegative("阻尼 D", params["D"])

    if config_key in {"avr", "avr_pss"}:
        for name in ["avr_K0", "avr_T1", "avr_T2", "avr_Te", "avr_Tr"]:
            _validate_positive(name, params[name])
        if params["avr_vfmax"] <= params["avr_vfmin"]:
            raise InputError("AVR 限幅要求 vfmax > vfmin。")

    if config_key == "avr_pss":
        for name in ["pss_Kw", "pss_Tw", "pss_T1", "pss_T2", "pss_T3", "pss_T4"]:
            _validate_positive(name, params[name])
        if params["pss_vsmax"] <= params["pss_vsmin"]:
            raise InputError("PSS 限幅要求 vsmax > vsmin。")

    op = _smib_build_operating_point(params)
    if config_key in {"avr", "avr_pss"}:
        vf0 = op["vf0"]
        if not (params["avr_vfmin"] <= vf0 <= params["avr_vfmax"]):
            raise InputError(
                f"初始化得到的 vf0={vf0:.6f} pu 超出 AVR 限幅区间 "
                f"[{params['avr_vfmin']:.6f}, {params['avr_vfmax']:.6f}] pu，"
                "当前工况下无法在限幅内建立平衡点。"
            )

    x0 = _smib_state_vector_init(config_key, params, op)
    state_names = _smib_state_names(config_key)

    def rhs_only(xx: np.ndarray) -> np.ndarray:
        return _smib_rhs(xx, config_key, params, op)[0]

    rhs0 = rhs_only(x0)
    residual = float(np.max(np.abs(rhs0))) if rhs0.size else 0.0
    if residual > 1e-6:
        raise InputError(
            f"初始化平衡点残差过大（max|f(x0)|={residual:.3e}），"
            "请检查工况、网络参数与控制器限幅是否自洽。"
        )

    A = _smib_numerical_jacobian(rhs_only, x0)
    eigs = np.linalg.eigvals(A)
    order = np.argsort(np.real(eigs))[::-1]
    eigs = eigs[order]
    stable = bool(np.max(np.real(eigs)) < -1e-6)
    dominant_idx = _smib_dominant_mode_index(eigs)
    dominant_part = _smib_mode_participation(A, eigs, state_names, dominant_idx)

    op_summary = SMIBOperatingPoint(
        P_pu=params["P0"],
        Q_pu=params["Q0"],
        terminal_voltage_pu=params["Vt"],
        terminal_angle_deg=op["Vt_ref_ang_deg"],
        infinite_bus_voltage_pu=op["Vinf"],
        reference_shift_deg=math.degrees(op["theta_ref"]),
        delta_deg=math.degrees(op["delta0"]),
        pm_pu=op["pm0"],
        vf0_pu=op["vf0"],
        vd_pu=op["vd0"],
        vq_pu=op["vq0"],
        id_pu=op["id0"],
        iq_pu=op["iq0"],
        xline_eq_pu=op["xline_eq"],
        xnet_pu=op["xnet"],
    )

    notes = (
        "模型采用 Kundur 示例 13.2 对应的六阶同步机、AVR III 与 PSS II 结构。"
        "网络按 xT + (xline1 ∥ xline2) 的 SMIB 等值处理，并在平衡点处对非线性 ODE 进行中心差分数值线性化。"
        "特征值以 1/s 给出，阻尼比按 -σ/|λ| 计算；参与因子用于识别主导状态。"
    )

    return SMIBSmallSignalResult(
        config_key=config_key,
        config_label=next((k for k, v in _SMIB_CONFIG_KEY.items() if v == config_key), config_key),
        state_names=state_names,
        operating_point=op_summary,
        A=A,
        eigenvalues=eigs,
        dominant_mode_index=dominant_idx,
        dominant_participation=dominant_part,
        stable=stable,
        notes=notes,
    )


__all__ = [
    "_SMIB_CONFIG_OPTIONS",
    "_SMIB_CONFIG_KEY",
    "_SMIB_STATE_LABELS",
    "kundur_smib_defaults",
    "_format_eigenvalue",
    "_smib_modal_rows",
    "smib_small_signal_analysis",
]
