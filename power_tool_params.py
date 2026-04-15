"""Kernel for parameter validation and per-unit conversion. / 参数校核与标幺值折算内核。"""


from __future__ import annotations


import math


from power_tool_common import (
    ParamWarning,
    LineParamResult,
    TwoWindingResult,
    ThreeWindingResult,
    _validate_positive,
)


_LINE_RANGES = {
    "R1_ohm_km":  (0.004, 0.70,  "线路电阻 R₁（Ω/km）", "典型 0.007~0.65 Ω/km"),
    "X1_ohm_km":  (0.18,  0.45,  "线路电抗 X₁（Ω/km）", "典型 0.20~0.42 Ω/km"),
    "C1_uF_km":   (0.004, 0.016, "线路电容 C₁（μF/km）","典型 0.008~0.014 μF/km"),
    "Zc_ohm":     (180,   520,   "波阻抗 Zc（Ω）",       "典型 240~420 Ω"),
}

_TX2_RANGES = {
    "Uk_pct":  (3.5,  24.0, "短路电压 Uk%",        "典型 4~18%；特高压主变可至 24%"),
    "I0_pct":  (0.05, 8.0,  "空载电流百分比 I₀%",  "典型 0.1~5%"),
    "Pk_SN":   (0.5,  15.0, "短路损耗/额定容量 (kW/MVA)", "典型 2~12 kW/MVA；大型变压器取下限，小变压器可至 15 kW/MVA"),
    "P0_SN":   (0.05, 6.0,  "空载损耗/额定容量 (kW/MVA)", "典型 0.1~3 kW/MVA；小变压器可偏高"),
}

_TX3_RANGES = {
    "Uk_pct":  (4.0,  25.0, "短路电压 Uk%",       "三绕组 典型 10~20%"),
    "I0_pct":  (0.05, 6.0,  "空载电流百分比 I₀%", "典型 0.1~3%"),
}

def _check_range(name: str, value: float, low: float, high: float,
                 hint: str, severity: str = "WARNING") -> Optional[ParamWarning]:
    if value < low or value > high:
        return ParamWarning(param=name, value=value, low=low, high=high,
                            hint=hint, severity=severity)
    return None

def _format_warnings(warnings: list[ParamWarning]) -> str:
    if not warnings:
        return "✓ 所有参数均在合理范围内。"
    lines = []
    for w in warnings:
        sym = "⚠" if w.severity == "WARNING" else "✗"
        lines.append(
            f"{sym} [{w.severity}] {w.param} = {w.value:.6g}  "
            f"（合理区间 {w.low:.6g} ~ {w.high:.6g}）\n    提示：{w.hint}"
        )
    return "\n".join(lines)

def convert_line_to_pu(R1: float, X1: float, C1_uF: float,
                       length_km: float,
                       Sbase_MVA: float, Ubase_kV: float) -> LineParamResult:
    """Convert lumped line parameters (π equivalent) into per-unit values. / 线路集中参数转换（π 型等值）并转标幺值。
    
    Parameters / 参数
    -----------------
    R1, X1: Series resistance and reactance per kilometre (Ω/km). / 单位长度电阻/电抗（Ω/km）。
    C1_uF: Capacitance per kilometre (μF/km). / 单位长度电容（μF/km）。
    length_km: Line length (km). / 线路长度（km）。
    Sbase_MVA, Ubase_kV: Base power (MVA) and base voltage (kV line-to-line). / 基准容量（MVA）和基准电压（kV，线电压）。"""
    _validate_positive("R1", R1)
    _validate_positive("X1", X1)
    _validate_positive("C1", C1_uF)
    _validate_positive("线路长度", length_km)
    _validate_positive("Sbase", Sbase_MVA)
    _validate_positive("Ubase", Ubase_kV)

    omega = 2.0 * math.pi * 50.0          # 50 Hz / 工频 50 Hz
    C1_F = C1_uF * 1e-6                    # μF/km → F/km / 微法每千米转换为法每千米
    B1_S = omega * C1_F                    # Shunt susceptance per unit length (S/km). / 单位长度电纳（S/km）

    R_total = R1 * length_km              # Ohms / 欧姆
    X_total = X1 * length_km              # Ohms / 欧姆
    B_half  = B1_S * length_km / 2.0      # Siemens, equal to B/2 in the π model. / 西门子，对应 π 型等值的 B/2

    Zc_ohm = math.sqrt(X1 / (omega * C1_F)) if C1_F > 1e-20 else 0.0

    Zbase = Ubase_kV ** 2 / Sbase_MVA     # Base impedance in ohms, since kV²/MVA = Ω. / 基准阻抗，kV²/MVA = Ω
    Ybase = 1.0 / Zbase                   # Siemens / 西门子

    R_pu     = R_total / Zbase
    X_pu     = X_total / Zbase
    B_half_pu = B_half  / Ybase           # Equals B_half * Zbase. / 等于 B_half * Zbase

    # Validation checks / 校核
    warns: list[ParamWarning] = []
    for key, (lo, hi, name, hint) in _LINE_RANGES.items():
        val = {"R1_ohm_km": R1, "X1_ohm_km": X1,
               "C1_uF_km":  C1_uF, "Zc_ohm": Zc_ohm}[key]
        w = _check_range(name, val, lo, hi, hint)
        if w:
            warns.append(w)
    # Extra check: X1/R1 ratio (for EHV lines X >> R, while distribution lines often have X ≈ R). / 额外校核：X1/R1 比值（对超高压线路，X>>R；配电线路 X≈R）
    if X1 < R1 * 0.5:
        warns.append(ParamWarning(
            param="X₁/R₁ 比值", value=X1/R1,
            low=0.5, high=float("inf"),
            hint="高压/超高压线路通常 X₁ >> R₁；若比值 <0.5 请核查参数来源。",
            severity="WARNING"))

    return LineParamResult(
        R_total_ohm=R_total, X_total_ohm=X_total, B_half_S=B_half,
        Zc_ohm=Zc_ohm,
        R_pu=R_pu, X_pu=X_pu, B_half_pu=B_half_pu,
        Zbase_ohm=Zbase, Ybase_S=Ybase,
        warnings=warns,
    )

def convert_2wt_to_pu(Pk_kW: float, Uk_pct: float,
                      P0_kW: float, I0_pct: float,
                      SN_MVA: float, UN_kV: float,
                      Sbase_MVA: float, Ubase_kV: float) -> TwoWindingResult:
    """Convert two-winding-transformer test data into named values and per-unit values referred to the HV side. / 两绕组变压器参数折算（以高压侧为折算基准）。
    
    Parameters / 参数
    -----------------
    Pk_kW: Load-loss or short-circuit loss (kW). / 短路损耗（kW）。
    Uk_pct: Short-circuit voltage in percent (e.g. 11.5). / 短路电压百分比（%，如 11.5）。
    P0_kW: No-load loss (kW). / 空载损耗（kW）。
    I0_pct: No-load current in percent (e.g. 0.3). / 空载电流百分比（%，如 0.3）。
    SN_MVA: Transformer rated power (MVA). / 变压器额定容量（MVA）。
    UN_kV: Rated HV-side voltage (kV). / 高压侧额定电压（kV）。
    Sbase_MVA, Ubase_kV: System base quantities, typically with Ubase = UN_kV. / 系统基准，通常取 Ubase = UN_kV。"""
    _validate_positive("短路损耗 Pk", Pk_kW)
    _validate_positive("短路电压 Uk%", Uk_pct)
    _validate_positive("空载损耗 P0", P0_kW)
    _validate_positive("空载电流 I0%", I0_pct)
    _validate_positive("SN", SN_MVA)
    _validate_positive("UN", UN_kV)
    _validate_positive("Sbase", Sbase_MVA)
    _validate_positive("Ubase", Ubase_kV)

    # Named quantities referred to the HV side / 有名值（折算到高压侧） ─────────────────────────────────────
    # Short-circuit resistance: Rk = Pk * UN² / (SN² * 1000). / 短路电阻: Rk = Pk * UN² / (SN² * 1000)   [Pk kW, UN kV, SN MVA → Ω]
    Rk_ohm = Pk_kW * UN_kV ** 2 / (SN_MVA ** 2 * 1000.0)

    # Short-circuit impedance: Zk = (Uk%/100) * UN² / SN. / 短路阻抗: Zk = (Uk%/100) * UN² / SN       [UN kV, SN MVA → Ω]
    Zk_ohm = (Uk_pct / 100.0) * UN_kV ** 2 / SN_MVA
    Xk_ohm = math.sqrt(max(0.0, Zk_ohm ** 2 - Rk_ohm ** 2))

    # No-load conductance: G0 = P0_kW * 1e3 / UN_V². / 空载电导: G0 = P0_kW * 1e3 / UN_V²        [S]
    G0_S = P0_kW * 1e3 / (UN_kV * 1e3) ** 2    # Equivalent to P0_kW / (UN_kV² * 1000). / 等价于 P0_kW / (UN_kV² * 1000)

    # No-load admittance magnitude: |Y0| = (I0%/100) * SN_MVA / UN_kV². / 空载导纳: |Y0| = (I0%/100) * SN_MVA / UN_kV²  [S]
    Y0_S = (I0_pct / 100.0) * SN_MVA / (UN_kV ** 2)
    B0_S = math.sqrt(max(0.0, Y0_S ** 2 - G0_S ** 2))

    # Per-unit quantities / 标幺值 ──────────────────────────────────────────────────────────
    Zbase = Ubase_kV ** 2 / Sbase_MVA       # Ohms / 欧姆
    Rk_pu = Rk_ohm / Zbase
    Xk_pu = Xk_ohm / Zbase
    G0_pu = G0_S   * Zbase
    B0_pu = B0_S   * Zbase

    # Recompute Uk% for cross-checking (per unit on Sbase/Ubase back to percent on SN/UN). / 反算 Uk% 用于交叉校验（标幺值 on Sbase/Ubase → 百分比 on SN/UN）
    Uk_check = (math.sqrt(Rk_pu ** 2 + Xk_pu ** 2)
                * (SN_MVA / Sbase_MVA) * (Ubase_kV / UN_kV) ** 2 * 100.0)

    # Validation checks / 校核 ─────────────────────────────────────────────────────────────
    warns: list[ParamWarning] = []
    pk_sn = Pk_kW / SN_MVA          # kW/MVA ≈ W/VA × 1000 / kW/MVA 近似等于 W/VA × 1000
    p0_sn = P0_kW / SN_MVA
    for key, (lo, hi, name, hint) in _TX2_RANGES.items():
        val = {"Uk_pct": Uk_pct, "I0_pct": I0_pct,
               "Pk_SN": pk_sn, "P0_SN": p0_sn}[key]
        w = _check_range(name, val, lo, hi, hint)
        if w:
            warns.append(w)
    # Rk must not exceed Zk; otherwise Xk would become imaginary. / Rk 不得超过 Zk（否则 Xk 虚数）
    if Rk_ohm >= Zk_ohm:
        warns.append(ParamWarning(
            "短路电阻 Rk vs 短路阻抗 Zk", Rk_ohm, 0, Zk_ohm,
            "短路损耗折算后的 Rk 不应超过 Zk，请核查 Pk 与 Uk% 是否配套。",
            "ERROR"))
    if Uk_pct > 0 and abs(Uk_check - Uk_pct) / Uk_pct > 0.05:
        warns.append(ParamWarning(
            "Uk% 交叉校验", Uk_check, Uk_pct * 0.95, Uk_pct * 1.05,
            f"由 Rk/Xk 反算得 Uk%≈{Uk_check:.2f}%，与输入 {Uk_pct:.2f}% 偏差 >5%，"
            "可能基准电压选取与额定电压不一致。",
            "WARNING"))

    return TwoWindingResult(
        Rk_ohm=Rk_ohm, Xk_ohm=Xk_ohm, G0_S=G0_S, B0_S=B0_S,
        Rk_pu=Rk_pu, Xk_pu=Xk_pu, G0_pu=G0_pu, B0_pu=B0_pu,
        Uk_pct_check=Uk_check,
        Zbase_ohm=Zbase,
        warnings=warns,
    )

def convert_3wt_to_pu(
        Pk_HM_kW: float, Pk_HL_kW: float, Pk_ML_kW: float,
        Uk_HM_pct: float, Uk_HL_pct: float, Uk_ML_pct: float,
        P0_kW: float, I0_pct: float,
        SN_H_MVA: float, SN_M_MVA: float, SN_L_MVA: float,
        UN_H_kV: float,
        Sbase_MVA: float, Ubase_kV: float) -> ThreeWindingResult:
    """Convert three-winding-transformer test data into named values and per-unit values referred to the HV side. / 三绕组变压器参数折算（以高压侧为折算基准）。
    All Uk% and Pk values are interpreted on the SN_H rating base. / 所有 Uk%、Pk 均参考到 SN_H 额定容量下。
    
    Test-data conventions / 测试数据约定：
    - `Pk_HM` is the H-M short-circuit loss in kW, with L open-circuited and current referred to the H/M test side. / `Pk_HM` 为 H-M 两绕组短路损耗（kW，L 开路）。
    - `Pk_HL` is the H-L short-circuit loss in kW, with M open-circuited. / `Pk_HL` 为 H-L 两绕组短路损耗（kW，M 开路）。
    - `Pk_ML` is the M-L short-circuit loss in kW, with H open-circuited; it may need to be converted to the common base. / `Pk_ML` 为 M-L 两绕组短路损耗（kW，H 开路），必要时需折算到公共基准。
    - `Uk%` participates directly in the three-winding decomposition without an extra M-L capacity conversion. / `Uk%` 按设备报参值直接参与三绕组分解（不做 M-L 容量折算）。"""
    for nm, v in [("Pk_HM", Pk_HM_kW), ("Pk_HL", Pk_HL_kW), ("Pk_ML", Pk_ML_kW),
                  ("Uk_HM%", Uk_HM_pct), ("Uk_HL%", Uk_HL_pct), ("Uk_ML%", Uk_ML_pct),
                  ("P0", P0_kW), ("I0%", I0_pct),
                  ("SN_H", SN_H_MVA), ("SN_M", SN_M_MVA), ("SN_L", SN_L_MVA),
                  ("UN_H", UN_H_kV), ("Sbase", Sbase_MVA), ("Ubase", Ubase_kV)]:
        _validate_positive(nm, v)

    # Use the HV-winding rating as the common base for three-winding short-circuit parameters, which is the most common engineering convention. / 统一以高压绕组容量作为三绕组短路参数公共基准（工程上最常见报参方式）。
    # Note: if the M-L test is performed at the rated current of the smaller side (often min(SN_M, SN_L)), / 注意：若 M-L 试验在较小侧额定电流下完成（常见为 min(SN_M, SN_L)），
    # first convert it to SN_H before applying the T-equivalent decomposition. / 需先折算到 SN_H，再做 T 型分解。
    SN_base = SN_H_MVA

    # Convert Pk and Uk% to the common power base SN_base / 折算 Pk 和 Uk% 到公共容量基准 SN_base ────────────────────────
    # Pairwise short-circuit-loss tests are often performed at the rated current of the smaller winding in the pair. / 两两短路损耗试验的电流常按该对绕组中较小容量一侧取值，
    # Therefore the results are converted to the common base SN_H using min(SN_i, SN_j) for each pair. / 因此按各对 min(SN_i, SN_j) 折算到统一基准 SN_H。
    SN_HM_test = min(SN_H_MVA, SN_M_MVA)
    SN_HL_test = min(SN_H_MVA, SN_L_MVA)
    SN_ML_test = min(SN_M_MVA, SN_L_MVA)
    scale_HM = (SN_base / SN_HM_test) ** 2
    scale_HL = (SN_base / SN_HL_test) ** 2
    scale_ML = (SN_base / SN_ML_test) ** 2
    Pk_HM_norm = Pk_HM_kW * scale_HM
    Pk_HL_norm = Pk_HL_kW * scale_HL
    Pk_ML_norm = Pk_ML_kW * scale_ML

    # Use Uk% directly on the common rating base provided by the equipment and do not apply a second capacity conversion. / Uk% 按设备给定的同一容量基准直接使用，不再按容量二次换算，
    # Otherwise the three-winding decomposition can be overstated and drift away from standard factory-test practice. / 否则会显著放大三绕组分解结果并偏离出厂试验常用计算。
    Uk_ML_norm = Uk_ML_pct

    Uk_HM_norm = Uk_HM_pct * (SN_base / SN_H_MVA)
    Uk_HL_norm = Uk_HL_pct * (SN_base / SN_H_MVA)

    # Decompose into individual windings (T-equivalent). / 分解到各绕组（T 型等值） ─────────────────────────────────────
    Pk_H = (Pk_HM_norm + Pk_HL_norm - Pk_ML_norm) / 2.0
    Pk_M = (Pk_HM_norm + Pk_ML_norm - Pk_HL_norm) / 2.0
    Pk_L = (Pk_HL_norm + Pk_ML_norm - Pk_HM_norm) / 2.0
    Pk_H = max(0.0, Pk_H)   # Numerical safeguard against tiny negative values. / 数值保护（可能出现微小负值）
    Pk_M = max(0.0, Pk_M)
    Pk_L = max(0.0, Pk_L)

    Uk_H_pct = (Uk_HM_norm + Uk_HL_norm - Uk_ML_norm) / 2.0
    Uk_M_pct = (Uk_HM_norm + Uk_ML_norm - Uk_HL_norm) / 2.0
    Uk_L_pct = (Uk_HL_norm + Uk_ML_norm - Uk_HM_norm) / 2.0

    # Named quantities referred to the HV side with respect to SN_base / 有名值（折算到高压侧，参考 SN_base） ─────────────────────────
    def _R(Pk_w, UN, SN):  # Pk in kW, UN in kV, SN in MVA → Ω / Pk 为 kW、UN 为 kV、SN 为 MVA 时结果单位为 Ω
        return Pk_w * UN ** 2 / (SN ** 2 * 1000.0)

    def _X(Uk_p, UN, SN):  # Uk% in %, UN in kV, SN in MVA → Ω / Uk%、UN、SN 按该单位输入时结果单位为 Ω
        Zk = (Uk_p / 100.0) * UN ** 2 / SN
        return Zk  # Approximate X ≈ Z, consistent with common transformer practice. / 近似 X ≈ Z（同变压器惯例）

    RH_ohm = _R(Pk_H,    UN_H_kV, SN_base)
    RM_ohm = _R(Pk_M,    UN_H_kV, SN_base)
    RL_ohm = _R(Pk_L,    UN_H_kV, SN_base)
    XH_ohm = _X(Uk_H_pct, UN_H_kV, SN_base)
    XM_ohm = _X(Uk_M_pct, UN_H_kV, SN_base)
    XL_ohm = _X(Uk_L_pct, UN_H_kV, SN_base)

    # No-load (magnetizing) parameters referred to the HV side. / 空载（励磁）参数（以高压侧折算）
    G0_S = P0_kW * 1e3 / (UN_H_kV * 1e3) ** 2
    Y0_S = (I0_pct / 100.0) * SN_H_MVA / (UN_H_kV ** 2)
    B0_S = math.sqrt(max(0.0, Y0_S ** 2 - G0_S ** 2))

    # Per-unit quantities / 标幺值 ──────────────────────────────────────────────────────────
    Zbase = Ubase_kV ** 2 / Sbase_MVA
    RH_pu = RH_ohm / Zbase; XH_pu = XH_ohm / Zbase
    RM_pu = RM_ohm / Zbase; XM_pu = XM_ohm / Zbase
    RL_pu = RL_ohm / Zbase; XL_pu = XL_ohm / Zbase
    G0_pu = G0_S   * Zbase;  B0_pu = B0_S   * Zbase

    # Validation checks / 校核 ─────────────────────────────────────────────────────────────
    warns: list[ParamWarning] = []
    for Ukp, label in [(Uk_HM_pct, "Uk_HM%"), (Uk_HL_pct, "Uk_HL%"), (Uk_ML_pct, "Uk_ML%")]:
        lo, hi, name, hint = _TX3_RANGES["Uk_pct"]
        w = _check_range(f"{label}（{name}）", Ukp, lo, hi, hint)
        if w:
            warns.append(w)
    lo, hi, name, hint = _TX3_RANGES["I0_pct"]
    w = _check_range(name, I0_pct, lo, hi, hint)
    if w:
        warns.append(w)
    # Check whether Uk_M_pct becomes negative, which is physically suspicious. / 检查 Uk_M_pct 是否可能为负（不合理）
    if Uk_M_pct < 0:
        warns.append(ParamWarning("Uk_M%（分解后）", Uk_M_pct, 0, float("inf"),
                                  "中压绕组分解后 Uk% 为负。三绕组 T 型分解中可出现负值，"
                                  "请结合出厂试验/厂家参数复核。",
                                  "WARNING"))
    if Uk_L_pct < 0:
        warns.append(ParamWarning("Uk_L%（分解后）", Uk_L_pct, 0, float("inf"),
                                  "低压绕组分解后 Uk% 为负。三绕组 T 型分解中可出现负值，"
                                  "请结合出厂试验/厂家参数复核。",
                                  "WARNING"))

    return ThreeWindingResult(
        RH_pu=RH_pu, XH_pu=XH_pu,
        RM_pu=RM_pu, XM_pu=XM_pu,
        RL_pu=RL_pu, XL_pu=XL_pu,
        G0_pu=G0_pu, B0_pu=B0_pu,
        RH_ohm=RH_ohm, XH_ohm=XH_ohm,
        RM_ohm=RM_ohm, XM_ohm=XM_ohm,
        RL_ohm=RL_ohm, XL_ohm=XL_ohm,
        Zbase_ohm=Zbase,
        warnings=warns,
    )


__all__ = [
    "_format_warnings",
    "convert_line_to_pu",
    "convert_2wt_to_pu",
    "convert_3wt_to_pu",
]
