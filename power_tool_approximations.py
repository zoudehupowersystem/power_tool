"""Approximate analytical models for frequency, electromechanical oscillation, static voltage stability, and natural power. / 近似解析模型：频率、机电振荡、静稳、自然功率。"""


from __future__ import annotations


import math


from typing import Optional


import numpy as np


from power_tool_common import (
    EPS,
    InputError,
    FrequencyResponseSummary,
    ElectromechSummary,
    VoltageStabilitySummary,
    NaturalPowerSummary,
    _validate_positive,
    _validate_nonnegative,
)


def classify_damping(Ts: float, TG: float, kD: float, kG: float) -> tuple[str, float]:
    """Return the damping regime and discriminant Δ = a1^2 - 4a0. / 返回阻尼类型和判别式 Δ = a1^2 - 4a0。"""
    ks = kD + kG
    _validate_positive("T_s", Ts)
    _validate_positive("T_G", TG)
    _validate_nonnegative("k_D", kD)
    _validate_nonnegative("k_G", kG)
    _validate_positive("k_D + k_G", ks)

    a1 = (Ts + kD * TG) / (Ts * TG)
    a0 = ks / (Ts * TG)
    disc = a1 * a1 - 4.0 * a0

    if disc > EPS:
        return "过阻尼", disc
    if disc < -EPS:
        return "欠阻尼", disc
    return "临界阻尼", disc

def frequency_response_value(t: np.ndarray | float,
                             delta_p_ol0: float,
                             Ts: float,
                             TG: float,
                             kD: float,
                             kG: float) -> np.ndarray | float:
    """Analytical solution of the second-order frequency-response model with primary frequency control. / 含一次调频二阶模型的解析解。
    Input and output are per-unit frequency deviations Δf. / 输入/输出均为标幺频差 Δf。"""
    _validate_positive("T_s", Ts)
    _validate_positive("T_G", TG)
    _validate_nonnegative("k_D", kD)
    _validate_nonnegative("k_G", kG)
    _validate_positive("ΔP_OL0", delta_p_ol0)

    ks = kD + kG
    _validate_positive("k_D + k_G", ks)

    y_ss = -delta_p_ol0 / ks
    dy0 = -delta_p_ol0 / Ts
    a1 = (Ts + kD * TG) / (Ts * TG)
    a0 = ks / (Ts * TG)
    disc = a1 * a1 - 4.0 * a0

    t_arr = np.asarray(t, dtype=float)

    if disc < -EPS:
        alpha = a1 / 2.0
        omega_d = math.sqrt(-disc) / 2.0
        C1 = -y_ss
        C2 = (dy0 + alpha * C1) / omega_d
        y = y_ss + np.exp(-alpha * t_arr) * (
            C1 * np.cos(omega_d * t_arr) + C2 * np.sin(omega_d * t_arr)
        )
    elif disc > EPS:
        root = math.sqrt(disc)
        r1 = (-a1 + root) / 2.0
        r2 = (-a1 - root) / 2.0
        # c1 + c2 = -y_ss / 两个指数项系数之和等于 -y_ss
        # c1*r1 + c2*r2 = dy0 / 导数初值约束为 dy0
        c1 = (dy0 + y_ss * r2) / (r1 - r2)
        c2 = -y_ss - c1
        y = y_ss + c1 * np.exp(r1 * t_arr) + c2 * np.exp(r2 * t_arr)
    else:
        r = -a1 / 2.0
        c1 = -y_ss
        c2 = dy0 - r * c1
        y = y_ss + (c1 + c2 * t_arr) * np.exp(r * t_arr)

    if np.isscalar(t):
        return float(np.asarray(y))
    return y

def first_order_frequency_response_value(t: np.ndarray | float,
                                         delta_p_ol0: float,
                                         Ts: float,
                                         kD: float) -> np.ndarray | float:
    """First-order model without primary frequency control. / 无一次调频的一阶模型。
    T_s dΔf/dt + k_D Δf = -ΔP_OL0. If k_D = 0, the response degenerates to a linear frequency ramp. / T_s dΔf/dt + k_D Δf = -ΔP_OL0。若 k_D = 0，则退化为匀速下滑。"""
    _validate_positive("T_s", Ts)
    _validate_nonnegative("k_D", kD)
    _validate_positive("ΔP_OL0", delta_p_ol0)

    t_arr = np.asarray(t, dtype=float)
    if kD > EPS:
        y = -delta_p_ol0 / kD * (1.0 - np.exp(-kD * t_arr / Ts))
    else:
        y = -(delta_p_ol0 / Ts) * t_arr

    if np.isscalar(t):
        return float(np.asarray(y))
    return y

def frequency_response_summary(delta_p_ol0: float,
                               Ts: float,
                               TG: float,
                               kD: float,
                               kG: float,
                               f0_hz: float) -> FrequencyResponseSummary:
    """Return key engineering quantities of disturbance frequency dynamics. / 返回事故频率动态的关键工程量。"""
    _validate_positive("f0", f0_hz)
    regime, disc = classify_damping(Ts, TG, kD, kG)

    ks = kD + kG
    alpha = (Ts + kD * TG) / (2.0 * Ts * TG)
    rocof_pu = -delta_p_ol0 / Ts
    rocof_hz = rocof_pu * f0_hz
    steady_pu = -delta_p_ol0 / ks
    steady_hz = steady_pu * f0_hz

    if regime == "欠阻尼":
        omega_d = math.sqrt(-disc) / 2.0
        # Use atan2 to avoid quadrant ambiguity. / 采用 atan2 以避免象限误判
        nadir_time = math.atan2(2.0 * Ts * TG * omega_d, kD * TG - Ts) / omega_d
        nadir_pu = float(frequency_response_value(nadir_time, delta_p_ol0, Ts, TG, kD, kG))
        notes = (
            "欠阻尼：存在典型“先下后回”的频率最低点。"
            " 最低点时刻采用 atan2 形式，避免普通 arctan 造成象限选错。"
        )
    else:
        omega_d = None
        nadir_time = None
        nadir_pu = steady_pu
        notes = (
            f"{regime}：该参数组合下通常表现为单调趋近新稳态，"
            "不存在典型欠阻尼意义上的“先跌到最低点再回升”的频率谷值。"
        )

    nadir_hz = nadir_pu * f0_hz
    f_min_hz = f0_hz * (1.0 + nadir_pu)

    if kD < EPS:
        notes += " 此外，k_D≈0 时，文中 T_f=T_s/k_D 的写法不宜直接使用；程序内部已自动绕开该奇异形式。"

    return FrequencyResponseSummary(
        regime=regime,
        alpha=alpha,
        omega_d=omega_d,
        rocof_pu_s=rocof_pu,
        rocof_hz_s=rocof_hz,
        steady_pu=steady_pu,
        steady_hz=steady_hz,
        nadir_time_s=nadir_time,
        nadir_pu=nadir_pu,
        nadir_hz=nadir_hz,
        f_min_hz=f_min_hz,
        notes=notes,
    )

def electromechanical_frequency(Eq_prime: float,
                                U: float,
                                X_sigma: float,
                                P0: float,
                                Tj: float,
                                f0_hz: float) -> ElectromechSummary:
    """Quick estimate of electromechanical oscillation frequency. / 机电振荡频率快估。"""
    _validate_positive("E'_q", Eq_prime)
    _validate_positive("U", U)
    _validate_positive("X_Σ", X_sigma)
    _validate_positive("T_j", Tj)
    _validate_positive("f0", f0_hz)

    ratio = P0 * X_sigma / (Eq_prime * U)
    if abs(ratio) > 1.0:
        raise InputError(
            "P0·X_Σ/(E'_q·U) 的绝对值大于 1，无法求取 arcsin，说明该运行点与经典功角模型不相容。"
        )

    delta0 = math.asin(ratio)
    Ks = Eq_prime * U / X_sigma * math.cos(delta0)
    omega0 = 2.0 * math.pi * f0_hz
    omega_n = math.sqrt(omega0 * Ks / Tj)
    f_n = omega_n / (2.0 * math.pi)

    notes = (
        "该公式给出的是小扰动主导机电模态频率的近似值。"
        " 阻尼、参与因子以及互联系统模态耦合仍需特征值分析或时域仿真。"
    )

    return ElectromechSummary(
        delta0_deg=math.degrees(delta0),
        Ks=Ks,
        omega_n=omega_n,
        f_n=f_n,
        notes=notes,
    )

def static_voltage_stability(Ug: float,
                             X_sigma: float,
                             cos_phi: float,
                             s_base_mva: Optional[float]) -> VoltageStabilitySummary:
    """Static-voltage-stability limit for a two-bus system with neglected resistance and lagging load power factor. / 二节点、忽略电阻、滞后负荷功率因数下的静态电压稳定极限。"""
    _validate_positive("U_g", Ug)
    _validate_positive("X_Σ", X_sigma)
    if not (0.0 < cos_phi <= 1.0):
        raise InputError("功率因数 cosφ 必须满足 0 < cosφ ≤ 1，且此处默认滞后负荷。")

    sin_phi = math.sqrt(max(0.0, 1.0 - cos_phi * cos_phi))
    pmax_pu = Ug * Ug / (2.0 * X_sigma) * (cos_phi / (1.0 + sin_phi))
    vmin_norm = 1.0 / math.sqrt(2.0 + 2.0 * sin_phi)
    vmin_same_base = Ug * vmin_norm

    pmax_mw = None
    if s_base_mva is not None and s_base_mva > 0:
        pmax_mw = pmax_pu * s_base_mva

    notes = (
        "适用前提：二节点等值、送端电压刚性、忽略电阻、负荷功率因数近似恒定。"
        " 若系统存在显著电阻、分接头动作、复杂无功补偿或多节点耦合，应改用潮流/连续潮流/QV-PV 分析。"
    )

    return VoltageStabilitySummary(
        sin_phi=sin_phi,
        Pmax_pu=pmax_pu,
        Pmax_MW=pmax_mw,
        Vmin_norm_to_sending=vmin_norm,
        Vmin_same_base_as_Ug=vmin_same_base,
        notes=notes,
    )

def natural_power_and_reactive(U_kV_ll: float,
                               Zc_ohm: Optional[float],
                               L_per_length: Optional[float],
                               C_per_length: Optional[float],
                               P_MW: float,
                               QN_Mvar_per_km: float,
                               length_km: float) -> NaturalPowerSummary:
    """Quick estimate of natural power and reactive-power behavior for long lines. / 长线路自然功率与无功行为快估。
    Assumptions / 约定：
    - U_kV_ll uses three-phase line-to-line RMS voltage in kV. / U_kV_ll 采用三相线电压 kV（RMS）。
    - Zc is in ohms. / Zc 单位为 Ω。
    - If Zc is supplied directly, it takes precedence; otherwise it is computed from sqrt(L/C). / 若直接给 Zc，则优先使用；否则由 sqrt(L/C) 计算。"""
    _validate_positive("U", U_kV_ll)
    _validate_nonnegative("P", P_MW)
    _validate_nonnegative("Q_N", QN_Mvar_per_km)
    _validate_positive("线路长度", length_km)

    if Zc_ohm is not None and Zc_ohm > 0:
        zc = Zc_ohm
    else:
        if L_per_length is None or C_per_length is None:
            raise InputError("请提供 Z_c，或同时提供单位长度 L 与 C。")
        _validate_positive("L", L_per_length)
        _validate_positive("C", C_per_length)
        zc = math.sqrt(L_per_length / C_per_length)

    p_n_mw = U_kV_ll * U_kV_ll / zc
    if p_n_mw <= 0:
        raise InputError("自然功率计算失败，请检查输入。")

    delta_q = (((P_MW / p_n_mw) ** 2) - 1.0) * QN_Mvar_per_km * length_km

    if abs(delta_q) < 1e-9:
        state = "近似自平衡"
    elif delta_q < 0:
        state = "总体发无功（净容性）"
    else:
        state = "总体吸无功（净感性）"

    notes = (
        "该估算最适用于额定电压附近、无损或低损、无复杂串并联补偿的超高压长线路。"
        " 实际电压偏离额定值时，线路充电无功应按 V² 修正。"
    )

    return NaturalPowerSummary(
        Zc_ohm=zc,
        Pn_MW=p_n_mw,
        delta_Q_Mvar=delta_q,
        line_state=state,
        notes=notes,
    )


__all__ = [
    "classify_damping",
    "frequency_response_value",
    "first_order_frequency_response_value",
    "frequency_response_summary",
    "electromechanical_frequency",
    "static_voltage_stability",
    "natural_power_and_reactive",
]
