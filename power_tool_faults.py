"""短路电流计算内核。"""


from __future__ import annotations


import math


from typing import Optional


from power_tool_common import (
    InputError,
    ShortCircuitSummary,
    _validate_positive,
    _validate_nonnegative,
)


def _phase_currents_from_sequence(I0: complex, I1: complex, I2: complex) -> tuple[complex, complex, complex]:
    a = complex(-0.5, math.sqrt(3.0) / 2.0)
    a2 = complex(-0.5, -math.sqrt(3.0) / 2.0)
    Ia = I0 + I1 + I2
    Ib = I0 + a2 * I1 + a * I2
    Ic = I0 + a * I1 + a2 * I2
    return Ia, Ib, Ic

def _zr_from_xr(z_mag: float, xr: float) -> tuple[float, float]:
    xr = max(xr, 1e-6)
    r = z_mag / math.sqrt(1.0 + xr * xr)
    x = r * xr
    return r, x

def _neutral_impedance(mode: str, rn: float, xn: float) -> tuple[complex, str]:
    key = mode.strip()
    if key == "直接接地":
        return 0j, key
    if key == "中性点不接地":
        return complex(1e9, 0.0), key
    if key == "经消弧线圈接地":
        _validate_nonnegative("消弧线圈电抗 Xn", xn)
        return complex(0.0, xn), key
    if key == "经电阻接地":
        _validate_nonnegative("接地电阻 Rn", rn)
        return complex(rn, 0.0), key
    raise InputError("中性点方式不支持。可选：直接接地/中性点不接地/经消弧线圈接地/经电阻接地。")

def short_circuit_capacity(U_kV_ll: float,
                           fault_type: str,
                           s_sc_mva: float,
                           xr_sys: float,
                           line_len_km: float,
                           line_r1_ohm_km: float,
                           line_x1_ohm_km: float,
                           line_r0_ohm_km: float,
                           line_x0_ohm_km: float,
                           neutral_mode: str,
                           neutral_rn_ohm: float,
                           neutral_xn_ohm: float,
                           Rf_ohm: float,
                           breaker_IkA: Optional[float],
                           network_mode: str = "单电源",
                           s_sc_right_mva: Optional[float] = None,
                           xr_sys_right: Optional[float] = None,
                           fault_pos_from_left_pct: float = 100.0) -> ShortCircuitSummary:
    _validate_positive("U", U_kV_ll)
    _validate_positive("系统短路容量 S_sc", s_sc_mva)
    _validate_positive("系统 X/R", xr_sys)
    _validate_nonnegative("线路长度", line_len_km)
    _validate_nonnegative("过渡电阻 Rf", Rf_ohm)
    if not (0.0 <= fault_pos_from_left_pct <= 100.0):
        raise InputError("故障点位置百分比必须在 0~100 之间。")

    zsys_mag = U_kV_ll * U_kV_ll / s_sc_mva
    r_sys, x_sys = _zr_from_xr(zsys_mag, xr_sys)
    Zsys1_left = complex(r_sys, x_sys)
    Zsys2_left = complex(r_sys, x_sys)

    Zl1_total = complex(line_r1_ohm_km * line_len_km, line_x1_ohm_km * line_len_km)
    Zl2_total = Zl1_total
    Zl0_total = complex(line_r0_ohm_km * line_len_km, line_x0_ohm_km * line_len_km)

    mode = network_mode.strip()
    ratio_left = fault_pos_from_left_pct / 100.0
    ratio_right = 1.0 - ratio_left
    Zn, neutral_name = _neutral_impedance(neutral_mode, neutral_rn_ohm, neutral_xn_ohm)
    if mode == "单电源":
        Z1 = Zsys1_left + Zl1_total
        Z2 = Zsys2_left + Zl2_total
        Z0 = Zsys1_left + Zl0_total
        mode_name = "单电源+线路末端故障"
    elif mode == "双电源":
        if s_sc_right_mva is None or xr_sys_right is None:
            raise InputError("双电源模式下需输入右侧电源短路容量与 X/R。")
        _validate_positive("右侧系统短路容量 S_sc_right", s_sc_right_mva)
        _validate_positive("右侧系统 X/R", xr_sys_right)
        zsys_mag_right = U_kV_ll * U_kV_ll / s_sc_right_mva
        r_sys_right, x_sys_right = _zr_from_xr(zsys_mag_right, xr_sys_right)
        Zsys1_right = complex(r_sys_right, x_sys_right)
        Zsys2_right = complex(r_sys_right, x_sys_right)

        Zl1_left = Zl1_total * ratio_left
        Zl1_right = Zl1_total * ratio_right
        Zl2_left = Zl2_total * ratio_left
        Zl2_right = Zl2_total * ratio_right
        Zl0_left = Zl0_total * ratio_left
        Zl0_right = Zl0_total * ratio_right

        Z1_left = Zsys1_left + Zl1_left
        Z1_right = Zsys1_right + Zl1_right
        Z2_left = Zsys2_left + Zl2_left
        Z2_right = Zsys2_right + Zl2_right
        Z0_left = Zsys1_left + Zl0_left
        Z0_right = Zsys1_right + Zl0_right

        Z1 = (Z1_left * Z1_right) / (Z1_left + Z1_right)
        Z2 = (Z2_left * Z2_right) / (Z2_left + Z2_right)
        Z0 = (Z0_left * Z0_right) / (Z0_left + Z0_right)
        mode_name = "线路两侧双电源+线路故障点"
    else:
        raise InputError("短路模型不支持。可选：单电源/双电源。")

    Zf = complex(Rf_ohm, 0.0)

    E = U_kV_ll * 1e3 / math.sqrt(3.0)
    ft = fault_type.strip()
    if ft in {"三相短路", "三相接地", "ABC三相短路"}:
        I1 = E / (Z1 + Zf); I2 = 0j; I0 = 0j
        fault_name = "三相短路"; Z_eq = Z1 + Zf
    elif ft in {"A相接地", "B相接地", "C相接地", "单相接地", "A-G", "B-G", "C-G"}:
        denom = Z1 + Z2 + Z0 + 3.0 * (Zn + Zf)
        Ieq = E / denom

        if ft in {"A相接地", "单相接地", "A-G"}:
            Ia, Ib, Ic = 3.0 * Ieq, 0j, 0j
            fault_name = "A相接地"
        elif ft in {"B相接地", "B-G"}:
            Ia, Ib, Ic = 0j, 3.0 * Ieq, 0j
            fault_name = "B相接地"
        else:
            Ia, Ib, Ic = 0j, 0j, 3.0 * Ieq
            fault_name = "C相接地"

        I0 = (Ia + Ib + Ic) / 3.0
        a = complex(-0.5, math.sqrt(3.0) / 2.0)
        a2 = complex(-0.5, -math.sqrt(3.0) / 2.0)
        I1 = (Ia + a * Ib + a2 * Ic) / 3.0
        I2 = (Ia + a2 * Ib + a * Ic) / 3.0
        Z_eq = denom / 3.0
    elif ft in {"AB两相短路", "BC两相短路", "CA两相短路", "两相短路"}:
        denom = Z1 + Z2 + Zf
        I1 = E / denom; I2 = -I1; I0 = 0j
        fault_name = ft; Z_eq = denom / 2.0
    elif ft in {"AB两相接地", "BC两相接地", "CA两相接地", "两相接地"}:
        z0g = Z0 + 3.0 * (Zn + Zf)
        zpar = (Z2 * z0g) / (Z2 + z0g)
        I1 = E / (Z1 + zpar)
        Vx = E - I1 * Z1
        I2 = -Vx / Z2
        I0 = -Vx / z0g
        fault_name = ft; Z_eq = Z1 + zpar
    else:
        raise InputError("故障类型不支持。请使用中文故障类型（如A/B/C相接地、AB/BC/CA两相接地、AB/BC/CA两相短路、三相接地）。")

    if ft not in {"A相接地", "B相接地", "C相接地", "单相接地", "A-G", "B-G", "C-G"}:
        Ia, Ib, Ic = _phase_currents_from_sequence(I0, I1, I2)

    V1 = E - I1 * Z1
    V2 = -I2 * Z2
    V0 = -I0 * Z0
    Va, Vb, Vc = _phase_currents_from_sequence(V0, V1, V2)
    i_break_kA = max(abs(Ia), abs(Ib), abs(Ic)) / 1e3

    R_eq = max(Z_eq.real, 1e-6)
    X_eq = abs(Z_eq.imag)
    tau_dc = X_eq / (2.0 * math.pi * 50.0 * R_eq)

    ok = None
    if breaker_IkA is not None:
        _validate_positive("断路器额定开断电流", breaker_IkA)
        ok = breaker_IkA >= i_break_kA

    notes = (
        f"当前模型：{mode_name}。"
        " 已计入中性点接地方式与过渡电阻；波形含交流分量+指数衰减直流偏置。"
    )

    return ShortCircuitSummary(
        network_mode=mode_name,
        fault_type=fault_name, neutral_mode=neutral_name,
        U_kV=U_kV_ll, line_len_km=line_len_km,
        fault_pos_from_left_pct=fault_pos_from_left_pct,
        Z1_ohm=Z1, Z2_ohm=Z2, Z0_ohm=Z0, Zn_ohm=Zn, Rf_ohm=Rf_ohm,
        I0_A=I0, I1_A=I1, I2_A=I2, Ia_A=Ia, Ib_A=Ib, Ic_A=Ic,
        V0_V=V0, V1_V=V1, V2_V=V2, Va_V=Va, Vb_V=Vb, Vc_V=Vc,
        I_break_kA=i_break_kA, tau_dc_s=tau_dc, breaker_ok=ok, notes=notes,
    )


__all__ = [
    "short_circuit_capacity",
]
