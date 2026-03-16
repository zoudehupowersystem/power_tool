
# -*- coding: utf-8 -*-
"""
电力系统工程近似公式 GUI 工具

用途：
1. 事故频率动态快估（含一次调频的二阶模型 + 无一次调频的一阶对照）
2. 机电振荡频率估算
3. 静态电压稳定极限估算
4. 长线路自然功率与无功行为估算
5. 暂态稳定：冲击法快估 + 等面积法（单机无穷大系统）

依赖：
    Python >= 3.10
    numpy
    matplotlib
    tkinter（标准库，Windows/Linux 常见 Python 发行版通常自带）

说明：
- 本工具实现的是工程近似模型，不替代潮流、特征值分析、时域仿真和正式稳控校核。
- 频率动态页采用解析解，自动区分欠阻尼、临界阻尼、过阻尼。
- GUI 使用 Tkinter，便于工程人员直接使用。
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Optional

import matplotlib
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

# ── 中文字体配置 ──────────────────────────────────────────────────────────────
# 按优先级依次尝试常见中文字体，取第一个系统中实际存在的字体。
import matplotlib.font_manager as _fm

_CN_FONT_CANDIDATES = [
    "WenQuanYi Zen Hei",      # wqy-zenhei，Linux 常见中文字体
    "WenQuanYi Micro Hei",
    "Noto Sans CJK JP",       # matplotlib 识别此名称（文件内含全部 CJK 字符）
    "Noto Serif CJK JP",
    "SimHei",                 # Windows / 部分 Linux 发行版
    "SimSun",
    "Microsoft YaHei",
    "AR PL UMing CN",
]

_available_fonts = {f.name for f in _fm.fontManager.ttflist}
_cn_font = next((f for f in _CN_FONT_CANDIDATES if f in _available_fonts), None)

if _cn_font:
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = [_cn_font] + matplotlib.rcParams["font.sans-serif"]

matplotlib.rcParams["axes.unicode_minus"] = False   # 修复负号显示为方块的问题
# ─────────────────────────────────────────────────────────────────────────────


EPS = 1e-10


class InputError(ValueError):
    """用户输入错误。"""


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise InputError(f"{name} 必须大于 0，当前为 {value:g}。")


def _validate_nonnegative(name: str, value: float) -> None:
    if value < 0:
        raise InputError(f"{name} 不能小于 0，当前为 {value:g}。")


def _safe_float(text: str, name: str) -> float:
    try:
        value = float(text.strip())
    except Exception as exc:
        raise InputError(f"{name} 不是有效数字：{text!r}") from exc
    if not math.isfinite(value):
        raise InputError(f"{name} 不是有限实数。")
    return value


@dataclass
class FrequencyResponseSummary:
    regime: str
    alpha: float
    omega_d: Optional[float]
    rocof_pu_s: float
    rocof_hz_s: float
    steady_pu: float
    steady_hz: float
    nadir_time_s: Optional[float]
    nadir_pu: float
    nadir_hz: float
    f_min_hz: float
    notes: str


@dataclass
class ElectromechSummary:
    delta0_deg: float
    Ks: float
    omega_n: float
    f_n: float
    notes: str


@dataclass
class VoltageStabilitySummary:
    sin_phi: float
    Pmax_pu: float
    Pmax_MW: Optional[float]
    Vmin_norm_to_sending: float
    Vmin_same_base_as_Ug: float
    notes: str


@dataclass
class NaturalPowerSummary:
    Zc_ohm: float
    Pn_MW: float
    delta_Q_Mvar: float
    line_state: str
    notes: str


@dataclass
class ImpactMethodSummary:
    Dp_pu: float
    Pst_pu: float
    margin_pu: Optional[float]
    status: str
    notes: str


@dataclass
class CriticalCutSummary:
    """临界切除角 / 临界切除时间快速估算结果（§7.6 近似公式）。"""
    delta0_deg: float       # 初始平衡角（°）
    delta0_rad: float
    delta_cr_deg: float     # 临界切除角（°）
    delta_cr_rad: float
    t_cr_s: float           # 临界切除时间（s）
    margin_pct: Optional[float]   # 相对给定切除时间的时间裕度 (t_cr - Δt)/t_cr × 100 %
    status: str
    notes: str


@dataclass
class EACResult:
    """等面积法（单机无穷大）计算结果。"""
    # 关键角度（均以弧度和度数双重存储）
    delta0_rad: float;  delta0_deg: float    # 故障前稳定平衡角
    deltac_rad: float;  deltac_deg: float    # 故障切除角
    deltau_rad: float;  deltau_deg: float    # 故障后不稳定平衡角
    # 等面积
    A_acc: float                              # 加速面积
    A_dec_avail: float                        # 可用减速面积（δc → δu）
    A_dec_actual: Optional[float]             # 实际用掉的减速面积（δc → δmax）
    # 极限切除角 / 极限切除时间
    delta_cr_rad: float; delta_cr_deg: float
    t_cr_s: float                             # 极限切除时间（数值积分）
    # 实际最大摆角（仅稳定时有意义）
    deltamax_rad: Optional[float]
    deltamax_deg: Optional[float]
    # 稳定性判断
    stable: bool
    margin_pct: float                         # (A_dec_avail - A_acc)/A_acc × 100 %
    notes: str


# ── 设备参数典型区间（来源：§3 及《电力系统设计手册》）──────────────────────
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


@dataclass
class ParamWarning:
    param: str
    value: float
    low: float
    high: float
    hint: str
    severity: str  # "WARNING" / "ERROR"


@dataclass
class LineParamResult:
    R_total_ohm: float
    X_total_ohm: float
    B_half_S: float         # B/2 (S)
    Zc_ohm: float
    R_pu: float
    X_pu: float
    B_half_pu: float
    Zbase_ohm: float
    Ybase_S: float
    warnings: list[ParamWarning]


@dataclass
class TwoWindingResult:
    Rk_ohm: float
    Xk_ohm: float
    G0_S: float
    B0_S: float
    Rk_pu: float
    Xk_pu: float
    G0_pu: float
    B0_pu: float
    Uk_pct_check: float     # recomputed from Rk/Xk for cross-check
    Zbase_ohm: float
    warnings: list[ParamWarning]


@dataclass
class ThreeWindingResult:
    # per-unit values on Sbase/Ubase
    RH_pu: float; XH_pu: float
    RM_pu: float; XM_pu: float
    RL_pu: float; XL_pu: float
    G0_pu: float; B0_pu: float
    # ohm values on HV side
    RH_ohm: float; XH_ohm: float
    RM_ohm: float; XM_ohm: float
    RL_ohm: float; XL_ohm: float
    Zbase_ohm: float
    warnings: list[ParamWarning]


# ── 参数检查辅助函数 ───────────────────────────────────────────────────────────

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


# ── 线路参数校核与标幺值转换 ─────────────────────────────────────────────────

def convert_line_to_pu(R1: float, X1: float, C1_uF: float,
                       length_km: float,
                       Sbase_MVA: float, Ubase_kV: float) -> LineParamResult:
    """
    线路集中参数转换（π 型等值）并转标幺值。

    参数
    ----
    R1, X1 : 单位长度电阻/电抗（Ω/km）
    C1_uF  : 单位长度电容（μF/km）
    length_km : 线路长度（km）
    Sbase_MVA, Ubase_kV : 基准容量（MVA）和基准电压（kV，线电压）
    """
    _validate_positive("R1", R1)
    _validate_positive("X1", X1)
    _validate_positive("C1", C1_uF)
    _validate_positive("线路长度", length_km)
    _validate_positive("Sbase", Sbase_MVA)
    _validate_positive("Ubase", Ubase_kV)

    omega = 2.0 * math.pi * 50.0          # 50 Hz
    C1_F = C1_uF * 1e-6                    # μF/km → F/km
    B1_S = omega * C1_F                    # 单位长度电纳（S/km）

    R_total = R1 * length_km              # Ω
    X_total = X1 * length_km              # Ω
    B_half  = B1_S * length_km / 2.0      # S (π型等值 B/2)

    Zc_ohm = math.sqrt(X1 / (omega * C1_F)) if C1_F > 1e-20 else 0.0

    Zbase = Ubase_kV ** 2 / Sbase_MVA     # Ω（kV²/MVA = Ω）
    Ybase = 1.0 / Zbase                   # S

    R_pu     = R_total / Zbase
    X_pu     = X_total / Zbase
    B_half_pu = B_half  / Ybase           # = B_half * Zbase

    # 校核
    warns: list[ParamWarning] = []
    for key, (lo, hi, name, hint) in _LINE_RANGES.items():
        val = {"R1_ohm_km": R1, "X1_ohm_km": X1,
               "C1_uF_km":  C1_uF, "Zc_ohm": Zc_ohm}[key]
        w = _check_range(name, val, lo, hi, hint)
        if w:
            warns.append(w)
    # 额外校核：X1/R1 比值（对超高压线路，X>>R；配电线路 X≈R）
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


# ── 两绕组变压器参数校核与标幺值转换 ─────────────────────────────────────────

def convert_2wt_to_pu(Pk_kW: float, Uk_pct: float,
                      P0_kW: float, I0_pct: float,
                      SN_MVA: float, UN_kV: float,
                      Sbase_MVA: float, Ubase_kV: float) -> TwoWindingResult:
    """
    两绕组变压器参数折算（以高压侧为折算基准）。

    参数
    ----
    Pk_kW   : 短路损耗（kW）
    Uk_pct  : 短路电压百分比（%，如 11.5）
    P0_kW   : 空载损耗（kW）
    I0_pct  : 空载电流百分比（%，如 0.3）
    SN_MVA  : 变压器额定容量（MVA）
    UN_kV   : 高压侧额定电压（kV）
    Sbase_MVA, Ubase_kV : 系统基准（通常 Ubase = UN_kV）
    """
    _validate_positive("短路损耗 Pk", Pk_kW)
    _validate_positive("短路电压 Uk%", Uk_pct)
    _validate_positive("空载损耗 P0", P0_kW)
    _validate_positive("空载电流 I0%", I0_pct)
    _validate_positive("SN", SN_MVA)
    _validate_positive("UN", UN_kV)
    _validate_positive("Sbase", Sbase_MVA)
    _validate_positive("Ubase", Ubase_kV)

    # ── 有名值（折算到高压侧）──────────────────────────────────────────
    # 短路电阻: Rk = Pk * UN² / (SN² * 1000)   [Pk kW, UN kV, SN MVA → Ω]
    Rk_ohm = Pk_kW * UN_kV ** 2 / (SN_MVA ** 2 * 1000.0)

    # 短路阻抗: Zk = (Uk%/100) * UN² / SN       [UN kV, SN MVA → Ω]
    Zk_ohm = (Uk_pct / 100.0) * UN_kV ** 2 / SN_MVA
    Xk_ohm = math.sqrt(max(0.0, Zk_ohm ** 2 - Rk_ohm ** 2))

    # 空载电导: G0 = P0_kW * 1e3 / UN_V²        [S]
    G0_S = Pk_kW  # temp placeholder
    G0_S = P0_kW * 1e3 / (UN_kV * 1e3) ** 2    # = P0_kW / (UN_kV² * 1000)

    # 空载导纳: |Y0| = (I0%/100) * SN_MVA / UN_kV²  [S]
    Y0_S = (I0_pct / 100.0) * SN_MVA / (UN_kV ** 2)
    B0_S = math.sqrt(max(0.0, Y0_S ** 2 - G0_S ** 2))

    # ── 标幺值 ──────────────────────────────────────────────────────────
    Zbase = Ubase_kV ** 2 / Sbase_MVA       # Ω
    Rk_pu = Rk_ohm / Zbase
    Xk_pu = Xk_ohm / Zbase
    G0_pu = G0_S   * Zbase
    B0_pu = B0_S   * Zbase

    # 反算 Uk% 用于交叉校验（标幺值 on Sbase/Ubase → 百分比 on SN/UN）
    Uk_check = (math.sqrt(Rk_pu ** 2 + Xk_pu ** 2)
                * (SN_MVA / Sbase_MVA) * (Ubase_kV / UN_kV) ** 2 * 100.0)

    # ── 校核 ─────────────────────────────────────────────────────────────
    warns: list[ParamWarning] = []
    pk_sn = Pk_kW / SN_MVA          # kW/MVA ≈ W/VA × 1000
    p0_sn = P0_kW / SN_MVA
    for key, (lo, hi, name, hint) in _TX2_RANGES.items():
        val = {"Uk_pct": Uk_pct, "I0_pct": I0_pct,
               "Pk_SN": pk_sn, "P0_SN": p0_sn}[key]
        w = _check_range(name, val, lo, hi, hint)
        if w:
            warns.append(w)
    # Rk 不得超过 Zk（否则 Xk 虚数）
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


# ── 三绕组变压器参数校核与标幺值转换 ─────────────────────────────────────────

def convert_3wt_to_pu(
        Pk_HM_kW: float, Pk_HL_kW: float, Pk_ML_kW: float,
        Uk_HM_pct: float, Uk_HL_pct: float, Uk_ML_pct: float,
        P0_kW: float, I0_pct: float,
        SN_H_MVA: float, SN_M_MVA: float, SN_L_MVA: float,
        UN_H_kV: float,
        Sbase_MVA: float, Ubase_kV: float) -> ThreeWindingResult:
    """
    三绕组变压器参数折算（以高压侧为折算基准）。
    所有 Uk%、Pk 均参考到 SN_H 额定容量下。

    测试数据约定：
    - Pk_HM 为 H-M 两绕组短路损耗（kW，L 开路，在 SN_H 额定电流下）
    - Pk_HL 为 H-L 两绕组短路损耗（kW，M 开路，在 SN_H 额定电流下）
    - Pk_ML 为 M-L 两绕组短路损耗（kW，H 开路，在 SN_M 额定电流下 → 需折算）
    - Uk%   按设备报参值直接参与三绕组分解（不做 M-L 容量折算）
    """
    for nm, v in [("Pk_HM", Pk_HM_kW), ("Pk_HL", Pk_HL_kW), ("Pk_ML", Pk_ML_kW),
                  ("Uk_HM%", Uk_HM_pct), ("Uk_HL%", Uk_HL_pct), ("Uk_ML%", Uk_ML_pct),
                  ("P0", P0_kW), ("I0%", I0_pct),
                  ("SN_H", SN_H_MVA), ("SN_M", SN_M_MVA), ("SN_L", SN_L_MVA),
                  ("UN_H", UN_H_kV), ("Sbase", Sbase_MVA), ("Ubase", Ubase_kV)]:
        _validate_positive(nm, v)

    # 统一以高压绕组容量作为三绕组短路参数公共基准（工程上最常见报参方式）。
    # 注意：若 M-L 试验在较小侧额定电流下完成（常见为 min(SN_M, SN_L)），
    # 需先折算到 SN_H，再做 T 型分解。
    SN_base = SN_H_MVA

    # ── 折算 Pk 和 Uk% 到公共容量基准 SN_base ────────────────────────
    # 两两短路损耗试验的电流常按该对绕组中较小容量一侧取值，
    # 因此按各对 min(SN_i, SN_j) 折算到统一基准 SN_H。
    SN_HM_test = min(SN_H_MVA, SN_M_MVA)
    SN_HL_test = min(SN_H_MVA, SN_L_MVA)
    SN_ML_test = min(SN_M_MVA, SN_L_MVA)
    scale_HM = (SN_base / SN_HM_test) ** 2
    scale_HL = (SN_base / SN_HL_test) ** 2
    scale_ML = (SN_base / SN_ML_test) ** 2
    Pk_HM_norm = Pk_HM_kW * scale_HM
    Pk_HL_norm = Pk_HL_kW * scale_HL
    Pk_ML_norm = Pk_ML_kW * scale_ML

    # Uk% 按设备给定的同一容量基准直接使用，不再按容量二次换算，
    # 否则会显著放大三绕组分解结果并偏离出厂试验常用计算。
    Uk_ML_norm = Uk_ML_pct

    Uk_HM_norm = Uk_HM_pct * (SN_base / SN_H_MVA)
    Uk_HL_norm = Uk_HL_pct * (SN_base / SN_H_MVA)

    # ── 分解到各绕组（T 型等值） ─────────────────────────────────────
    Pk_H = (Pk_HM_norm + Pk_HL_norm - Pk_ML_norm) / 2.0
    Pk_M = (Pk_HM_norm + Pk_ML_norm - Pk_HL_norm) / 2.0
    Pk_L = (Pk_HL_norm + Pk_ML_norm - Pk_HM_norm) / 2.0
    Pk_H = max(0.0, Pk_H)   # 数值保护（可能出现微小负值）
    Pk_M = max(0.0, Pk_M)
    Pk_L = max(0.0, Pk_L)

    Uk_H_pct = (Uk_HM_norm + Uk_HL_norm - Uk_ML_norm) / 2.0
    Uk_M_pct = (Uk_HM_norm + Uk_ML_norm - Uk_HL_norm) / 2.0
    Uk_L_pct = (Uk_HL_norm + Uk_ML_norm - Uk_HM_norm) / 2.0

    # ── 有名值（折算到高压侧，参考 SN_base） ─────────────────────────
    def _R(Pk_w, UN, SN):  # Pk in kW, UN in kV, SN in MVA → Ω
        return Pk_w * UN ** 2 / (SN ** 2 * 1000.0)

    def _X(Uk_p, UN, SN):  # Uk% in %, UN in kV, SN in MVA → Ω
        Zk = (Uk_p / 100.0) * UN ** 2 / SN
        return Zk  # 近似 X ≈ Z（同变压器惯例）

    RH_ohm = _R(Pk_H,    UN_H_kV, SN_base)
    RM_ohm = _R(Pk_M,    UN_H_kV, SN_base)
    RL_ohm = _R(Pk_L,    UN_H_kV, SN_base)
    XH_ohm = _X(Uk_H_pct, UN_H_kV, SN_base)
    XM_ohm = _X(Uk_M_pct, UN_H_kV, SN_base)
    XL_ohm = _X(Uk_L_pct, UN_H_kV, SN_base)

    # 空载（励磁）参数（以高压侧折算）
    G0_S = P0_kW * 1e3 / (UN_H_kV * 1e3) ** 2
    Y0_S = (I0_pct / 100.0) * SN_H_MVA / (UN_H_kV ** 2)
    B0_S = math.sqrt(max(0.0, Y0_S ** 2 - G0_S ** 2))

    # ── 标幺值 ──────────────────────────────────────────────────────────
    Zbase = Ubase_kV ** 2 / Sbase_MVA
    RH_pu = RH_ohm / Zbase; XH_pu = XH_ohm / Zbase
    RM_pu = RM_ohm / Zbase; XM_pu = XM_ohm / Zbase
    RL_pu = RL_ohm / Zbase; XL_pu = XL_ohm / Zbase
    G0_pu = G0_S   * Zbase;  B0_pu = B0_S   * Zbase

    # ── 校核 ─────────────────────────────────────────────────────────────
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
    # 检查 Uk_M_pct 是否可能为负（不合理）
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


def classify_damping(Ts: float, TG: float, kD: float, kG: float) -> tuple[str, float]:
    """返回阻尼类型和判别式 Δ = a1^2 - 4a0。"""
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
    """
    含一次调频二阶模型的解析解。
    输入/输出均为标幺频差 Δf。
    """
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
        # c1 + c2 = -y_ss
        # c1*r1 + c2*r2 = dy0
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
    """
    无一次调频的一阶模型：
        T_s dΔf/dt + k_D Δf = -ΔP_OL0
    若 k_D = 0，则退化为匀速下滑：Δf = -(ΔP_OL0/T_s) t。
    """
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
    """返回事故频率动态的关键工程量。"""
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
        # 采用 atan2 以避免象限误判
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
    """机电振荡频率快估。"""
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
    """二节点、忽略电阻、滞后负荷功率因数下的静态电压稳定极限。"""
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
    """
    长线路自然功率与无功行为快估。
    约定：
    - U_kV_ll 采用三相线电压 kV（RMS）
    - Zc 单位为 Ω
    - 若直接给 Zc，则优先使用；否则由 sqrt(L/C) 计算
    """
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


def impact_method(delta_p: float,
                  delta_t_s: float,
                  f_d_hz: float,
                  pmax_post_pu: float,
                  p_current_pu: Optional[float]) -> ImpactMethodSummary:
    """暂态稳定冲击法快估。"""
    _validate_positive("ΔP", delta_p)
    _validate_positive("Δt", delta_t_s)
    _validate_positive("f_d", f_d_hz)
    _validate_positive("P_max^post", pmax_post_pu)

    dp = delta_p * delta_t_s * 2.0 * math.pi * f_d_hz
    pst = pmax_post_pu - dp

    margin = None
    if p_current_pu is not None:
        margin = pst - p_current_pu
        status = "近似可接受" if margin >= 0 else "第一摆稳定裕度不足"
    else:
        status = "未输入当前传输功率，无法给出裕度判据"

    notes = (
        "冲击法强调“故障加速功率 × 持续时间”形成的速度冲量，是工程快估而非严格等面积法。"
        " 当故障期间角度偏移不可忽略、后故障平衡点改变明显或接近临界切除时，应改用正式暂态稳定仿真。"
    )

    return ImpactMethodSummary(
        Dp_pu=dp,
        Pst_pu=pst,
        margin_pu=margin,
        status=status,
        notes=notes,
    )


def critical_cut_angle_approx(Pm: float,
                               Pmax_post: float,
                               Tj: float,
                               f0: float,
                               delta_t_given: Optional[float] = None) -> CriticalCutSummary:
    """
    临界切除角与临界切除时间的工程快速估算（§7.6 近似公式）。

    适用假设：
      - 三相金属性短路，故障期间电磁功率 ≈ 0（Pmax_fault = 0）
      - 故障前后最大功率相同，均取 Pmax_post
      - 故障期间加速功率近似为常数 Pm（匀加速积分）

    公式：
      δ0  = arcsin(Pm / Pmax)
      δcr = arccos[ Pm/Pmax · (π − 2δ0) − cos δ0 ]
      tcr = sqrt( 2·Tj·(δcr − δ0) / (ω0·Pm) )
    """
    _validate_positive("Pm（临界切除）", Pm)
    _validate_positive("Pmax_post（临界切除）", Pmax_post)
    _validate_positive("Tj（临界切除）", Tj)
    _validate_positive("f0（临界切除）", f0)

    if Pm >= Pmax_post:
        raise InputError("临界切除角估算：Pm 必须小于 Pmax_post，否则故障后无稳定平衡点。")

    omega0 = 2.0 * math.pi * f0
    ratio = Pm / Pmax_post

    delta0 = math.asin(ratio)              # 弧度，故障前（同时也是故障后）稳定平衡角

    # 临界切除角（等面积法在 Pmax_fault=0、Pmax_pre=Pmax_post 极端情形下的解析式）
    cos_cr = ratio * (math.pi - 2.0 * delta0) - math.cos(delta0)
    cos_cr = max(-1.0, min(1.0, cos_cr))   # 数值保护
    delta_cr = math.acos(cos_cr)

    # 临界切除时间（匀加速近似）
    t_cr = math.sqrt(2.0 * Tj * (delta_cr - delta0) / (omega0 * Pm))

    margin_pct = None
    if delta_t_given is not None and delta_t_given > 0:
        margin_pct = (t_cr - delta_t_given) / t_cr * 100.0
        if margin_pct >= 0:
            status = f"切除时间充裕（裕量 {margin_pct:.1f} %）"
        else:
            status = f"切除时间不足（超限 {-margin_pct:.1f} %）"
    else:
        status = "未输入实际切除时间，无法判断裕量"

    notes = (
        "本公式为 §7.6 近似解析式，假设：①三相金属性短路（Pmax_fault≈0）；"
        "②故障前后最大功率相同（均取 Pmax_post）；"
        "③故障期间加速功率近似为恒定 Pm（匀加速）。\n"
        "若故障后网络与故障前不同（如切除一回线），建议使用右侧等面积法作完整校核。"
    )

    return CriticalCutSummary(
        delta0_deg=math.degrees(delta0),
        delta0_rad=delta0,
        delta_cr_deg=math.degrees(delta_cr),
        delta_cr_rad=delta_cr,
        t_cr_s=t_cr,
        margin_pct=margin_pct,
        status=status,
        notes=notes,
    )


# ── 等面积法辅助函数 ──────────────────────────────────────────────────────────

def _acc_area(delta0: float, deltac: float, Pm: float, Pmax_f: float) -> float:
    """加速面积 ∫[δ0→δc] (Pm − Pmax_f·sinδ) dδ。"""
    return Pm * (deltac - delta0) - Pmax_f * (math.cos(delta0) - math.cos(deltac))


def _dec_area(deltac: float, deltamax: float, Pm: float, Pmax_post: float) -> float:
    """减速面积 ∫[δc→δmax] (Pmax_post·sinδ − Pm) dδ。"""
    return Pmax_post * (math.cos(deltac) - math.cos(deltamax)) - Pm * (deltamax - deltac)


def _swing_integrate_to_angle(delta0: float, target: float,
                              Pm: float, Pmax_f: float,
                              Tj: float, f0: float,
                              max_t: float = 5.0, dt: float = 1e-4) -> float:
    """
    用 RK4 积分摆动方程，从 δ0 出发，返回到达 target 角（弧度）所需时间。
    方程：d²δ/dt² = (ω0/Tj)·(Pm − Pmax_f·sinδ)
    找不到时返回 max_t（表示超过积分上限，极限切除时间过长）。
    """
    omega0 = 2.0 * math.pi * f0
    k = omega0 / Tj

    # 状态：y = [δ, dδ/dt]
    def deriv(y: list[float]) -> list[float]:
        d, v = y
        return [v, k * (Pm - Pmax_f * math.sin(d))]

    y = [delta0, 0.0]
    t = 0.0
    while t < max_t:
        if y[0] >= target:
            return t
        # RK4
        k1 = deriv(y)
        k2 = deriv([y[0] + 0.5*dt*k1[0], y[1] + 0.5*dt*k1[1]])
        k3 = deriv([y[0] + 0.5*dt*k2[0], y[1] + 0.5*dt*k2[1]])
        k4 = deriv([y[0] + dt*k3[0],     y[1] + dt*k3[1]])
        y[0] += dt/6*(k1[0]+2*k2[0]+2*k3[0]+k4[0])
        y[1] += dt/6*(k1[1]+2*k2[1]+2*k3[1]+k4[1])
        t += dt
    return max_t


def equal_area_criterion(Pm: float,
                         Pmax_pre: float,
                         Pmax_fault: float,
                         Pmax_post: float,
                         delta_t_s: float,
                         Tj: float,
                         f0: float) -> EACResult:
    """
    单机无穷大系统等面积法。

    三段功角曲线：
        故障前  Pe_pre   = Pmax_pre   · sin δ
        故障中  Pe_fault = Pmax_fault · sin δ  (三相故障时 = 0)
        故障后  Pe_post  = Pmax_post  · sin δ

    参数
    ----
    Pm          机械功率（pu，假设恒定）
    Pmax_pre    故障前最大传输功率（pu）
    Pmax_fault  故障中最大传输功率（pu），三相故障取 0
    Pmax_post   故障后最大传输功率（pu）
    delta_t_s   故障切除时间（s）
    Tj          惯性时间常数（s）
    f0          额定频率（Hz）
    """
    _validate_positive("Pm", Pm)
    _validate_positive("Pmax_pre", Pmax_pre)
    _validate_nonnegative("Pmax_fault", Pmax_fault)
    _validate_positive("Pmax_post", Pmax_post)
    _validate_positive("Δt", delta_t_s)
    _validate_positive("Tj", Tj)
    _validate_positive("f0", f0)

    if Pm >= Pmax_pre:
        raise InputError("Pm 必须小于 Pmax_pre，否则故障前无稳定运行点。")
    if Pm >= Pmax_post:
        raise InputError("Pm 必须小于 Pmax_post，否则故障后无稳定平衡点。")

    # ── 1. 关键角度 ──────────────────────────────────────────────────────
    delta0 = math.asin(Pm / Pmax_pre)          # 故障前 SEP
    deltau = math.pi - math.asin(Pm / Pmax_post)  # 故障后 UEP

    # ── 2. 故障切除角（RK4 数值积分摆动方程）────────────────────────────
    omega0 = 2.0 * math.pi * f0
    k_swing = omega0 / Tj

    def deriv(y: list) -> list:
        d, v = y
        return [v, k_swing * (Pm - Pmax_fault * math.sin(d))]

    y = [delta0, 0.0]
    t = 0.0
    dt = 1e-4
    while t < delta_t_s - dt * 0.5:
        k1 = deriv(y)
        k2 = deriv([y[0]+0.5*dt*k1[0], y[1]+0.5*dt*k1[1]])
        k3 = deriv([y[0]+0.5*dt*k2[0], y[1]+0.5*dt*k2[1]])
        k4 = deriv([y[0]+dt*k3[0],     y[1]+dt*k3[1]])
        y[0] += dt/6*(k1[0]+2*k2[0]+2*k3[0]+k4[0])
        y[1] += dt/6*(k1[1]+2*k2[1]+2*k3[1]+k4[1])
        t += dt
    deltac = y[0]

    # ── 3. 加速面积 ──────────────────────────────────────────────────────
    A_acc = _acc_area(delta0, deltac, Pm, Pmax_fault)
    if A_acc < 0:
        A_acc = 0.0  # 极端情况（切除极快）保护

    # ── 4. 可用减速面积（δc → δu）────────────────────────────────────────
    A_dec_avail = _dec_area(deltac, deltau, Pm, Pmax_post)
    if A_dec_avail < 0:
        A_dec_avail = 0.0

    # ── 5. 极限切除角（闭式解）──────────────────────────────────────────
    # cos(δc_cr) = [Pm·(δu−δ0) + Pmax_post·cos(δu) − Pmax_fault·cos(δ0)]
    #              / (Pmax_post − Pmax_fault)
    denom = Pmax_post - Pmax_fault
    if abs(denom) < 1e-9:
        # 故障中与故障后功率相同 → 无加速，极限切除角即为不稳定平衡角
        delta_cr = deltau
    else:
        cos_cr = (Pm * (deltau - delta0) + Pmax_post * math.cos(deltau)
                  - Pmax_fault * math.cos(delta0)) / denom
        cos_cr = max(-1.0, min(1.0, cos_cr))   # 数值保护
        delta_cr = math.acos(cos_cr)

    # ── 6. 极限切除时间（数值积分）──────────────────────────────────────
    t_cr = _swing_integrate_to_angle(delta0, delta_cr, Pm, Pmax_fault, Tj, f0)

    # ── 7. 稳定判断与实际最大摆角 ────────────────────────────────────────
    stable = (A_dec_avail >= A_acc - 1e-9) and (deltac < deltau)

    deltamax_rad = deltamax_deg = A_dec_actual = None
    if stable and A_acc > 1e-9:
        # 在 [deltac, deltau] 内用二分法求 A_dec(deltamax) = A_acc
        lo, hi = deltac, deltau
        for _ in range(60):
            mid = (lo + hi) / 2.0
            if _dec_area(deltac, mid, Pm, Pmax_post) < A_acc:
                lo = mid
            else:
                hi = mid
        deltamax_rad = (lo + hi) / 2.0
        deltamax_deg = math.degrees(deltamax_rad)
        A_dec_actual = _dec_area(deltac, deltamax_rad, Pm, Pmax_post)
    elif stable:
        deltamax_rad = deltac
        deltamax_deg = math.degrees(deltac)
        A_dec_actual = 0.0

    # ── 8. 裕度 ──────────────────────────────────────────────────────────
    margin_pct = (A_dec_avail - A_acc) / A_acc * 100.0 if A_acc > 1e-9 else float("inf")

    notes = (
        "极限切除角由闭式公式计算（需 Pmax_post ≠ Pmax_fault）；"
        "极限切除时间由 RK4 数值积分摆动方程得到。"
        "裕度 = (可用减速面积 − 加速面积) / 加速面积 × 100 %。"
        "本模型为单机无穷大、忽略阻尼、机械功率恒定的经典假设。"
    )

    return EACResult(
        delta0_rad=delta0,       delta0_deg=math.degrees(delta0),
        deltac_rad=deltac,       deltac_deg=math.degrees(deltac),
        deltau_rad=deltau,       deltau_deg=math.degrees(deltau),
        A_acc=A_acc,
        A_dec_avail=A_dec_avail,
        A_dec_actual=A_dec_actual,
        delta_cr_rad=delta_cr,   delta_cr_deg=math.degrees(delta_cr),
        t_cr_s=t_cr,
        deltamax_rad=deltamax_rad,
        deltamax_deg=deltamax_deg,
        stable=stable,
        margin_pct=margin_pct,
        notes=notes,
    )


class ApproximationToolGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("电力系统近似公式工程工具")
        self.geometry("1340x920")
        self.minsize(1180, 820)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew")

        self.freq_tab = ttk.Frame(notebook)
        self.osc_tab = ttk.Frame(notebook)
        self.volt_tab = ttk.Frame(notebook)
        self.line_tab = ttk.Frame(notebook)
        self.impact_tab = ttk.Frame(notebook)
        self.param_tab = ttk.Frame(notebook)

        notebook.add(self.freq_tab, text="频率动态")
        notebook.add(self.osc_tab, text="机电振荡")
        notebook.add(self.volt_tab, text="静态电压稳定")
        notebook.add(self.line_tab, text="线路自然功率与无功")
        notebook.add(self.impact_tab, text="暂稳评估")
        notebook.add(self.param_tab, text="参数校核与标幺值")

        self._build_frequency_tab()
        self._build_oscillation_tab()
        self._build_voltage_tab()
        self._build_line_tab()
        self._build_impact_tab()
        self._build_param_tab()

    @staticmethod
    def _add_entry(parent: ttk.Frame,
                   row: int,
                   label: str,
                   default: str,
                   column: int = 0,
                   width: int = 14) -> tk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=4, pady=4)
        entry = tk.Entry(parent, width=width)
        entry.grid(row=row, column=column + 1, sticky="ew", padx=4, pady=4)
        entry.insert(0, default)
        return entry

    @staticmethod
    def _set_text(widget: ScrolledText, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state="disabled")

    def _build_frequency_tab(self) -> None:
        self.freq_tab.columnconfigure(1, weight=1)
        self.freq_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.freq_tab, padding=10)
        right = ttk.Frame(self.freq_tab, padding=10)
        left.grid(row=0, column=0, sticky="nsw")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(left, text="二阶频率动态（含一次调频）", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        self.freq_f0 = self._add_entry(left, 1, "额定频率 f0 / Hz", "50")
        self.freq_dp = self._add_entry(left, 2, "功率缺额 ΔP_OL0 / pu", "0.08")
        self.freq_ts = self._add_entry(left, 3, "系统惯性时间常数 T_s / s", "8")
        self.freq_tg = self._add_entry(left, 4, "一次调频时间常数 T_G / s", "5")
        self.freq_kd = self._add_entry(left, 5, "负荷频率系数 k_D / pu/pu", "1.2")
        self.freq_kg = self._add_entry(left, 6, "一次调频系数 k_G / pu/pu", "4.0")
        self.freq_tend = self._add_entry(left, 7, "绘图时长 / s", "30")

        self.show_first_order = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="同时绘制无一次调频一阶对照", variable=self.show_first_order).grid(
            row=8, column=0, columnspan=2, sticky="w", padx=4, pady=4
        )

        ttk.Button(left, text="计算并绘图", command=self.calculate_frequency).grid(
            row=9, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4)
        )

        ttk.Label(left, text="结果", font=("TkDefaultFont", 10, "bold")).grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(10, 4)
        )

        self.freq_result = ScrolledText(left, width=52, height=24, wrap=tk.WORD)
        self.freq_result.grid(row=11, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        self.freq_result.configure(state="disabled")

        ttk.Label(right, text="频率曲线", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        self.freq_fig = Figure(figsize=(7.4, 5.2), dpi=100)
        self.freq_ax = self.freq_fig.add_subplot(111)
        self.freq_ax.set_xlabel("t / s")
        self.freq_ax.set_ylabel("f / Hz")
        self.freq_ax.grid(True)

        self.freq_canvas = FigureCanvasTkAgg(self.freq_fig, master=right)
        self.freq_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        self.freq_toolbar = NavigationToolbar2Tk(self.freq_canvas, right, pack_toolbar=False)
        self.freq_toolbar.update()
        self.freq_toolbar.grid(row=2, column=0, sticky="ew")

        self.calculate_frequency()

    def _build_oscillation_tab(self) -> None:
        frame = ttk.Frame(self.osc_tab, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="机电振荡频率快估", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        self.osc_eq = self._add_entry(frame, 1, "内电势 E'_q / pu", "1.12")
        self.osc_u = self._add_entry(frame, 2, "端电压 U / pu", "1.0")
        self.osc_x = self._add_entry(frame, 3, "等值电抗 X_Σ / pu", "0.55")
        self.osc_p0 = self._add_entry(frame, 4, "初始有功 P0 / pu", "0.8")
        self.osc_tj = self._add_entry(frame, 5, "惯性时间常数 T_j / s", "9")
        self.osc_f0 = self._add_entry(frame, 6, "同步频率 f0 / Hz", "50")

        ttk.Button(frame, text="计算", command=self.calculate_oscillation).grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4)
        )

        self.osc_result = ScrolledText(frame, width=85, height=24, wrap=tk.WORD)
        self.osc_result.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=4, pady=8)
        self.osc_result.configure(state="disabled")

        self.calculate_oscillation()

    def _build_voltage_tab(self) -> None:
        frame = ttk.Frame(self.volt_tab, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="静态电压稳定极限快估", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        self.volt_ug = self._add_entry(frame, 1, "送端电压 U_g / pu", "1.0")
        self.volt_x = self._add_entry(frame, 2, "总电抗 X_Σ / pu", "0.32")
        self.volt_pf = self._add_entry(frame, 3, "功率因数 cosφ（默认滞后）", "0.95")
        self.volt_sbase = self._add_entry(frame, 4, "容量基准 S_base / MVA（可改）", "100")

        ttk.Button(frame, text="计算", command=self.calculate_voltage).grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4)
        )

        self.volt_result = ScrolledText(frame, width=85, height=24, wrap=tk.WORD)
        self.volt_result.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=4, pady=8)
        self.volt_result.configure(state="disabled")

        self.calculate_voltage()

    def _build_line_tab(self) -> None:
        frame = ttk.Frame(self.line_tab, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="长线路自然功率与无功行为快估", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        self.line_u = self._add_entry(frame, 1, "线路额定电压 U / kV（线电压）", "500")
        self.line_zc = self._add_entry(frame, 2, "波阻抗 Z_c / Ω（优先）", "250")
        self.line_l = self._add_entry(frame, 3, "单位长度电感 L（可留空）", "")
        self.line_c = self._add_entry(frame, 4, "单位长度电容 C（可留空）", "")
        self.line_p = self._add_entry(frame, 5, "实际传输有功 P / MW", "700")
        self.line_qn = self._add_entry(frame, 6, "单位长度充电功率 Q_N / (Mvar/km)", "1.2")
        self.line_len = self._add_entry(frame, 7, "线路长度 l / km", "200")

        ttk.Button(frame, text="计算", command=self.calculate_line).grid(
            row=8, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4)
        )

        self.line_result = ScrolledText(frame, width=85, height=24, wrap=tk.WORD)
        self.line_result.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=4, pady=8)
        self.line_result.configure(state="disabled")

        self.calculate_line()

    def _build_impact_tab(self) -> None:
        # ── 顶层布局：左侧两个输入框（上下排列）+ 右侧 P-δ 图 ──────────────
        self.impact_tab.columnconfigure(0, weight=0)
        self.impact_tab.columnconfigure(1, weight=1)
        self.impact_tab.rowconfigure(0, weight=1)

        left  = ttk.Frame(self.impact_tab, padding=6)
        right = ttk.Frame(self.impact_tab, padding=6)
        left.grid(row=0, column=0, sticky="nsw")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        # ══════════════════════════════════════════════════════════════════
        # 上框：冲击法快估
        # ══════════════════════════════════════════════════════════════════
        imp_frame = ttk.LabelFrame(left, text="冲击法快估", padding=8)
        imp_frame.pack(fill="x", expand=False, pady=(0, 6))
        imp_frame.columnconfigure(0, weight=0)
        imp_frame.columnconfigure(1, weight=1)

        self.imp_dp   = self._add_entry(imp_frame, 0, "故障加速功率 ΔPa / pu", "0.9")
        self.imp_dt   = self._add_entry(imp_frame, 1, "故障切除时间 Δt / s", "0.12")
        self.imp_fd   = self._add_entry(imp_frame, 2, "故障后振荡频率 f_d / Hz", "1.106")
        self.imp_pmax = self._add_entry(imp_frame, 3, "故障后最大传输功率 Pmax_post / pu", "1.65")
        self.imp_pcur = self._add_entry(imp_frame, 4, "当前传输功率 Pm / pu（冲击法裕度 & 临界切除用）", "0.90")
        self.imp_tj   = self._add_entry(imp_frame, 5, "惯性时间常数 T_j / s（临界切除用）", "9")
        self.imp_f0   = self._add_entry(imp_frame, 6, "额定频率 f0 / Hz（临界切除用）", "50")

        ttk.Button(imp_frame, text="计算", command=self.calculate_impact).grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 2)
        )

        self.imp_result = ScrolledText(imp_frame, width=50, height=12, wrap=tk.WORD)
        self.imp_result.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=2, pady=4)
        self.imp_result.configure(state="disabled")

        # ══════════════════════════════════════════════════════════════════
        # 下框：等面积法
        # ══════════════════════════════════════════════════════════════════
        eac_frame = ttk.LabelFrame(left, text="等面积法（单机无穷大）", padding=8)
        eac_frame.pack(fill="both", expand=True, pady=(0, 0))
        eac_frame.columnconfigure(0, weight=0)
        eac_frame.columnconfigure(1, weight=1)

        self.eac_pm    = self._add_entry(eac_frame, 0, "机械功率 Pm / pu", "0.90")
        self.eac_ppre  = self._add_entry(eac_frame, 1, "故障前 Pmax_pre / pu", "1.65")
        self.eac_pf    = self._add_entry(eac_frame, 2, "故障中 Pmax_fault / pu（三相故障填 0）", "0.0")
        self.eac_ppost = self._add_entry(eac_frame, 3, "故障后 Pmax_post / pu", "1.65")
        self.eac_dt    = self._add_entry(eac_frame, 4, "故障切除时间 Δt / s", "0.12")
        self.eac_tj    = self._add_entry(eac_frame, 5, "惯性时间常数 Tj / s", "9")
        self.eac_f0    = self._add_entry(eac_frame, 6, "额定频率 f0 / Hz", "50")

        ttk.Button(eac_frame, text="计算并绘图", command=self.calculate_eac).grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 2)
        )

        self.eac_result = ScrolledText(eac_frame, width=50, height=14, wrap=tk.WORD)
        self.eac_result.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=2, pady=4)
        eac_frame.rowconfigure(8, weight=1)
        self.eac_result.configure(state="disabled")

        # ══════════════════════════════════════════════════════════════════
        # 右侧：P-δ 功角曲线图
        # ══════════════════════════════════════════════════════════════════
        ttk.Label(right, text="功角曲线（等面积法）", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )

        self.eac_fig = Figure(figsize=(7.2, 5.4), dpi=100)
        self.eac_ax  = self.eac_fig.add_subplot(111)
        self.eac_ax.set_xlabel("δ / °")
        self.eac_ax.set_ylabel("P / pu")
        self.eac_ax.set_title("功角曲线（等待计算）")
        self.eac_ax.grid(True)

        self.eac_canvas = FigureCanvasTkAgg(self.eac_fig, master=right)
        self.eac_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        self.eac_toolbar = NavigationToolbar2Tk(self.eac_canvas, right, pack_toolbar=False)
        self.eac_toolbar.update()
        self.eac_toolbar.grid(row=2, column=0, sticky="ew")

        # 初始化
        self.calculate_impact()
        self.calculate_eac()

    def calculate_frequency(self) -> None:
        try:
            f0 = _safe_float(self.freq_f0.get(), "额定频率 f0")
            delta_p = _safe_float(self.freq_dp.get(), "功率缺额 ΔP_OL0")
            Ts = _safe_float(self.freq_ts.get(), "T_s")
            TG = _safe_float(self.freq_tg.get(), "T_G")
            kD = _safe_float(self.freq_kd.get(), "k_D")
            kG = _safe_float(self.freq_kg.get(), "k_G")
            t_end = _safe_float(self.freq_tend.get(), "绘图时长")

            summary = frequency_response_summary(delta_p, Ts, TG, kD, kG, f0)

            t = np.linspace(0.0, t_end, 1400)
            y2 = frequency_response_value(t, delta_p, Ts, TG, kD, kG)
            f2 = f0 * (1.0 + y2)

            self.freq_ax.clear()
            self.freq_ax.plot(t, f2, label="含一次调频二阶模型", linewidth=2.0)
            if self.show_first_order.get():
                y1 = first_order_frequency_response_value(t, delta_p, Ts, kD)
                f1 = f0 * (1.0 + y1)
                self.freq_ax.plot(t, f1, "--", label="无一次调频一阶对照", linewidth=1.7)

            self.freq_ax.axhline(
                y=f0 * (1.0 + summary.steady_pu),
                linestyle=":",
                linewidth=1.2,
                label="二阶模型稳态频率"
            )

            if summary.nadir_time_s is not None and 0.0 <= summary.nadir_time_s <= t_end + 1e-9:
                self.freq_ax.scatter(
                    [summary.nadir_time_s],
                    [summary.f_min_hz],
                    s=40,
                    label=f"最低点 ({summary.nadir_time_s:.3f} s)"
                )

            self.freq_ax.set_xlabel("t / s")
            self.freq_ax.set_ylabel("f / Hz")
            self.freq_ax.set_title(f"频率响应曲线（{summary.regime}）")
            self.freq_ax.grid(True)
            self.freq_ax.legend(loc="best")
            self.freq_fig.tight_layout()
            self.freq_canvas.draw()

            text = (
                f"阻尼类型：{summary.regime}\n"
                f"α = {summary.alpha:.6f} 1/s\n"
                f"Ω = {summary.omega_d:.6f} rad/s\n" if summary.omega_d is not None else
                f"阻尼类型：{summary.regime}\n"
                f"α = {summary.alpha:.6f} 1/s\n"
            )

            text += (
                f"初始频率变化率 RoCoF = {summary.rocof_pu_s:.6f} pu/s = {summary.rocof_hz_s:.6f} Hz/s\n"
                f"稳态频差 Δf∞ = {summary.steady_pu:.6f} pu = {summary.steady_hz:.6f} Hz\n"
            )

            if summary.nadir_time_s is not None:
                text += (
                    f"频率最低点时刻 t_m = {summary.nadir_time_s:.6f} s\n"
                    f"最低频差 Δf_min = {summary.nadir_pu:.6f} pu = {summary.nadir_hz:.6f} Hz\n"
                    f"最低频率 f_min = {summary.f_min_hz:.6f} Hz\n"
                )
            else:
                text += (
                    "该参数组合不产生典型欠阻尼最低点。\n"
                    f"单调极限（稳态）Δf∞ = {summary.steady_pu:.6f} pu，"
                    f"对应频率 {f0 * (1.0 + summary.steady_pu):.6f} Hz\n"
                )

            text += "\n说明：\n" + summary.notes
            self._set_text(self.freq_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_oscillation(self) -> None:
        try:
            Eq = _safe_float(self.osc_eq.get(), "E'_q")
            U = _safe_float(self.osc_u.get(), "U")
            X = _safe_float(self.osc_x.get(), "X_Σ")
            P0 = _safe_float(self.osc_p0.get(), "P0")
            Tj = _safe_float(self.osc_tj.get(), "T_j")
            f0 = _safe_float(self.osc_f0.get(), "f0")

            summary = electromechanical_frequency(Eq, U, X, P0, Tj, f0)

            text = (
                f"初始功角 δ0 = {summary.delta0_deg:.6f} °\n"
                f"同步转矩系数 K_s = {summary.Ks:.6f} pu/rad（按本文近似定义）\n"
                f"固有角频率 ω_n = {summary.omega_n:.6f} rad/s\n"
                f"机电振荡频率 f_n = {summary.f_n:.6f} Hz\n\n"
                f"说明：\n{summary.notes}"
            )
            self._set_text(self.osc_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_voltage(self) -> None:
        try:
            Ug = _safe_float(self.volt_ug.get(), "U_g")
            X = _safe_float(self.volt_x.get(), "X_Σ")
            cos_phi = _safe_float(self.volt_pf.get(), "cosφ")
            s_base_text = self.volt_sbase.get().strip()
            s_base = _safe_float(s_base_text, "S_base") if s_base_text else None

            summary = static_voltage_stability(Ug, X, cos_phi, s_base)

            text = (
                f"sinφ = {summary.sin_phi:.6f}\n"
                f"最大可送有功 P_L,max = {summary.Pmax_pu:.6f} pu\n"
            )
            if summary.Pmax_MW is not None:
                text += f"折算有名值 = {summary.Pmax_MW:.6f} MW\n"
            text += (
                f"受端最低电压（相对送端电压归一化）V_min/U_g = {summary.Vmin_norm_to_sending:.6f} pu\n"
                f"受端最低电压（与 U_g 同一基准）V_min = {summary.Vmin_same_base_as_Ug:.6f} pu\n\n"
                f"说明：\n{summary.notes}"
            )
            self._set_text(self.volt_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_line(self) -> None:
        try:
            U = _safe_float(self.line_u.get(), "U")
            zc_text = self.line_zc.get().strip()
            zc = _safe_float(zc_text, "Z_c") if zc_text else None

            l_text = self.line_l.get().strip()
            c_text = self.line_c.get().strip()
            L = _safe_float(l_text, "L") if l_text else None
            C = _safe_float(c_text, "C") if c_text else None

            P = _safe_float(self.line_p.get(), "P")
            QN = _safe_float(self.line_qn.get(), "Q_N")
            length = _safe_float(self.line_len.get(), "l")

            summary = natural_power_and_reactive(U, zc, L, C, P, QN, length)

            text = (
                f"波阻抗 Z_c = {summary.Zc_ohm:.6f} Ω\n"
                f"自然功率 P_N = {summary.Pn_MW:.6f} MW\n"
                f"线路无功估算 ΔQ_L = {summary.delta_Q_Mvar:.6f} Mvar\n"
                f"运行区间判断：{summary.line_state}\n\n"
                f"说明：\n{summary.notes}"
            )
            self._set_text(self.line_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_impact(self) -> None:
        try:
            delta_p = _safe_float(self.imp_dp.get(), "ΔPa")
            delta_t = _safe_float(self.imp_dt.get(), "Δt")
            f_d     = _safe_float(self.imp_fd.get(), "f_d")
            pmax_post = _safe_float(self.imp_pmax.get(), "Pmax_post")
            pcur_text = self.imp_pcur.get().strip()
            pcur = _safe_float(pcur_text, "Pm") if pcur_text else None
            tj_text = self.imp_tj.get().strip()
            f0_text = self.imp_f0.get().strip()

            summary = impact_method(delta_p, delta_t, f_d, pmax_post, pcur)

            text = (
                f"══ 冲击法快估 ══════════════════════\n"
                f"冲击量 Dp = {summary.Dp_pu:.6f} pu\n"
                f"暂稳极限 Pst = {summary.Pst_pu:.6f} pu\n"
            )
            if summary.margin_pu is not None:
                text += f"相对当前传输功率的裕度 = {summary.margin_pu:.6f} pu\n"
            text += f"结论：{summary.status}\n"

            # ── 临界切除角快速估算 ────────────────────────────────────────
            if pcur_text and tj_text and f0_text:
                try:
                    Pm_val  = _safe_float(pcur_text, "Pm")
                    Tj_val  = _safe_float(tj_text,   "T_j")
                    f0_val  = _safe_float(f0_text,   "f0")
                    ccs = critical_cut_angle_approx(Pm_val, pmax_post, Tj_val, f0_val, delta_t)
                    text += (
                        f"\n══ 临界切除角快速估算（§7.6） ══════\n"
                        f"初始平衡角   δ0  = {ccs.delta0_deg:.3f}°\n"
                        f"临界切除角   δcr = {ccs.delta_cr_deg:.3f}°\n"
                        f"临界切除时间 tcr = {ccs.t_cr_s:.4f} s\n"
                        f"当前切除时间 Δt  = {delta_t:.4f} s  "
                        f"({'< tcr OK' if delta_t < ccs.t_cr_s else '>= tcr NG'})\n"
                    )
                    if ccs.margin_pct is not None:
                        text += f"时间裕量 = {ccs.margin_pct:+.1f} %\n"
                    text += f"结论：{ccs.status}\n"
                    text += f"\n说明（冲击法）：\n{summary.notes}\n"
                    text += f"\n说明（临界切除）：\n{ccs.notes}"
                except InputError as ie:
                    text += f"\n临界切除角估算：{ie}\n"
                    text += f"\n说明：\n{summary.notes}"
            else:
                text += (
                    "\n（如需临界切除角快速估算，请同时填写 Pm、T_j 和 f0）\n"
                    f"\n说明：\n{summary.notes}"
                )

            self._set_text(self.imp_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_eac(self) -> None:
        try:
            Pm        = _safe_float(self.eac_pm.get(),    "Pm")
            Pmax_pre  = _safe_float(self.eac_ppre.get(),  "Pmax_pre")
            Pmax_f    = _safe_float(self.eac_pf.get(),    "Pmax_fault")
            Pmax_post = _safe_float(self.eac_ppost.get(), "Pmax_post")
            dt        = _safe_float(self.eac_dt.get(),    "Δt")
            Tj        = _safe_float(self.eac_tj.get(),    "Tj")
            f0        = _safe_float(self.eac_f0.get(),    "f0")

            r = equal_area_criterion(Pm, Pmax_pre, Pmax_f, Pmax_post, dt, Tj, f0)

            # ── 结果文字 ────────────────────────────────────────────────
            stab_str = "[稳定]" if r.stable else "[失稳]（加速面积 > 可用减速面积）"
            text = (
                f"稳定性判断：{stab_str}\n"
                f"裕度 = {r.margin_pct:+.2f} %\n"
                f"\n── 关键角度 ──────────────────────\n"
                f"故障前平衡角 δ0  = {r.delta0_deg:.3f}°\n"
                f"故障切除角   δc  = {r.deltac_deg:.3f}°\n"
                f"不稳定平衡角 δu  = {r.deltau_deg:.3f}°\n"
            )
            if r.deltamax_deg is not None:
                text += f"实际最大摆角 δmax= {r.deltamax_deg:.3f}°\n"
            text += (
                f"\n── 等面积 ────────────────────────\n"
                f"加速面积  Aacc       = {r.A_acc:.6f} pu·rad\n"
                f"可用减速面积 Adec    = {r.A_dec_avail:.6f} pu·rad\n"
            )
            if r.A_dec_actual is not None:
                text += f"实际减速面积 Adec_act= {r.A_dec_actual:.6f} pu·rad\n"
            text += (
                f"\n── 极限切除 ──────────────────────\n"
                f"极限切除角 δcr = {r.delta_cr_deg:.3f}°\n"
                f"极限切除时间 tcr = {r.t_cr_s:.4f} s\n"
                f"当前切除时间 Δt  = {dt:.4f} s  "
                f"({'< tcr OK' if dt < r.t_cr_s else '>= tcr NG'})\n"
                f"\n说明：\n{r.notes}"
            )
            self._set_text(self.eac_result, text)

            # ── P-δ 图 ──────────────────────────────────────────────────
            ax = self.eac_ax
            ax.clear()

            delta_deg = np.linspace(0, 200, 1000)
            delta_rad = np.radians(delta_deg)

            Pe_pre   = Pmax_pre  * np.sin(delta_rad)
            Pe_fault = Pmax_f    * np.sin(delta_rad)
            Pe_post  = Pmax_post * np.sin(delta_rad)

            ax.plot(delta_deg, Pe_pre,   "b-",  linewidth=1.8,
                    label=f"故障前  Pmax={Pmax_pre:.3f} pu")
            fault_lbl = (f"故障中  Pmax={Pmax_f:.3f} pu"
                         + ("（三相短路≈0）" if Pmax_f < 1e-9 else ""))
            ax.plot(delta_deg, Pe_fault, "r--", linewidth=1.5, label=fault_lbl)
            ax.plot(delta_deg, Pe_post,  "g-",  linewidth=1.8,
                    label=f"故障后  Pmax={Pmax_post:.3f} pu")
            ax.axhline(Pm, color="k", linewidth=1.4, linestyle=":",
                       label=f"Pm = {Pm:.3f} pu")

            # 加速面积（红色填充）δ0 → δc，曲线为故障中正弦
            d_acc = np.linspace(r.delta0_rad, r.deltac_rad, 500)
            Pe_f_acc = Pmax_f * np.sin(d_acc)
            # 正加速（Pm > Pe_fault）→ 红色；负加速（Pe_fault > Pm）→ 蓝紫色
            ax.fill_between(np.degrees(d_acc), Pm, Pe_f_acc,
                            where=(Pm >= Pe_f_acc),
                            color="tomato", alpha=0.45,
                            label=f"加速面积（+）{r.A_acc:.4f} pu·rad")
            if np.any(Pe_f_acc > Pm):
                neg_area = float(
                    np.trapz(np.maximum(0, Pe_f_acc - Pm), d_acc))
                ax.fill_between(np.degrees(d_acc), Pe_f_acc, Pm,
                                where=(Pe_f_acc > Pm),
                                color="mediumpurple", alpha=0.40,
                                label=f"减速（故障中）{neg_area:.4f} pu·rad")

            # 减速面积（绿色填充）δc → δmax（或 δu）
            d_end = r.deltamax_rad if r.deltamax_rad is not None else r.deltau_rad
            d_dec = np.linspace(r.deltac_rad, d_end, 500)
            Pe_post_dec = Pmax_post * np.sin(d_dec)
            ax.fill_between(np.degrees(d_dec),
                            Pe_post_dec, Pm,
                            where=(Pe_post_dec >= Pm),
                            color="limegreen", alpha=0.45,
                            label=f"减速面积 {r.A_dec_avail:.4f} pu·rad")

            # 关键角度标注
            def _vline(deg: float, color: str, ls: str, label: str) -> None:
                ax.axvline(deg, color=color, linestyle=ls, linewidth=1.2, label=label)

            _vline(r.delta0_deg,  "blue",  "-.",  f"δ₀={r.delta0_deg:.1f}°")
            _vline(r.deltac_deg,  "red",   "--",  f"δc={r.deltac_deg:.1f}°")
            _vline(r.deltau_deg,  "green", "-.",  f"δu={r.deltau_deg:.1f}°")
            _vline(r.delta_cr_deg,"purple",":",   f"δcr={r.delta_cr_deg:.1f}°")
            if r.deltamax_deg is not None:
                _vline(r.deltamax_deg, "darkorange", "--",
                       f"δmax={r.deltamax_deg:.1f}°")

            ax.set_xlabel("δ / °")
            ax.set_ylabel("P / pu")
            title_flag = "[稳定]" if r.stable else "[失稳]"
            ax.set_title(
                f"功角曲线  {title_flag}  裕度 {r.margin_pct:+.1f}%  "
                f"tcr={r.t_cr_s:.3f} s"
            )
            ax.set_xlim(0, 200)
            ymax = max(Pmax_pre, Pmax_post, Pm) * 1.18
            ax.set_ylim(-0.08, ymax)
            ax.legend(loc="upper right", fontsize=7.5, ncol=2)
            ax.grid(True, alpha=0.4)
            self.eac_fig.tight_layout()
            self.eac_canvas.draw()

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))


    # ════════════════════════════════════════════════════════════════════
    # 参数校核与标幺值转换标签页
    # ════════════════════════════════════════════════════════════════════

    def _build_param_tab(self) -> None:
        """构建"参数校核与标幺值转换"标签页（含线路、双绕组变压器、三绕组变压器子页）。"""
        self.param_tab.columnconfigure(0, weight=1)
        self.param_tab.rowconfigure(0, weight=1)

        nb = ttk.Notebook(self.param_tab)
        nb.grid(row=0, column=0, sticky="nsew")

        self._ptab_line = ttk.Frame(nb)
        self._ptab_2wt  = ttk.Frame(nb)
        self._ptab_3wt  = ttk.Frame(nb)
        nb.add(self._ptab_line, text="架空线路")
        nb.add(self._ptab_2wt,  text="两绕组变压器")
        nb.add(self._ptab_3wt,  text="三绕组变压器")

        self._build_line_param_sub()
        self._build_2wt_sub()
        self._build_3wt_sub()

    # ── 架空线路子页 ─────────────────────────────────────────────────────────

    def _build_line_param_sub(self) -> None:
        f = self._ptab_line
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="架空线路参数校核与标幺值转换（π 型等值）",
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4))

        hint = ("典型范围参考（§3.3/3.4）：R₁ 0.005~0.65 Ω/km，"
                "X₁ 0.20~0.42 Ω/km，C₁ 0.008~0.014 μF/km，"
                "Zc 240~420 Ω；超高压取下限，配电取上限。")
        ttk.Label(f, text=hint, wraplength=620, foreground="#555555").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

        self.lp_r1    = self._add_entry(f,  2, "单位长度电阻 R₁ / (Ω/km)", "0.028")
        self.lp_x1    = self._add_entry(f,  3, "单位长度电抗 X₁ / (Ω/km)", "0.299")
        self.lp_c1    = self._add_entry(f,  4, "单位长度电容 C₁ / (μF/km)", "0.013")
        self.lp_len   = self._add_entry(f,  5, "线路长度 / km", "200")
        self.lp_sbase = self._add_entry(f,  6, "基准容量 Sbase / MVA", "100")
        self.lp_ubase = self._add_entry(f,  7, "基准电压 Ubase / kV（线电压）", "500")

        ttk.Button(f, text="计算并校核", command=self.calculate_line_param).grid(
            row=8, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))

        self.lp_result = ScrolledText(f, width=85, height=20, wrap=tk.WORD)
        self.lp_result.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)
        f.rowconfigure(9, weight=1)
        self.lp_result.configure(state="disabled")
        self.calculate_line_param()

    # ── 两绕组变压器子页 ─────────────────────────────────────────────────────

    def _build_2wt_sub(self) -> None:
        f = self._ptab_2wt
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="两绕组变压器参数校核与标幺值转换",
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4))

        hint = ("典型范围（§3.5）：Uk% 4~18%（特高压主变 18~24%），"
                "I₀% 0.1~5%，短路损耗 1~7 kW/MVA，空载损耗 0.1~3 kW/MVA。")
        ttk.Label(f, text=hint, wraplength=620, foreground="#555555").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

        self.tx2_pk    = self._add_entry(f,  2, "短路损耗 Pk / kW", "290")
        self.tx2_uk    = self._add_entry(f,  3, "短路电压 Uk / %", "11.73")
        self.tx2_p0    = self._add_entry(f,  4, "空载损耗 P0 / kW", "51.3")
        self.tx2_i0    = self._add_entry(f,  5, "空载电流 I₀ / %", "0.3")
        self.tx2_sn    = self._add_entry(f,  6, "额定容量 SN / MVA", "20")
        self.tx2_un    = self._add_entry(f,  7, "高压侧额定电压 UN / kV", "35")
        self.tx2_sbase = self._add_entry(f,  8, "基准容量 Sbase / MVA", "100")
        self.tx2_ubase = self._add_entry(f,  9, "基准电压 Ubase / kV（通常 = UN）", "35")

        ttk.Button(f, text="计算并校核", command=self.calculate_2wt).grid(
            row=10, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))

        self.tx2_result = ScrolledText(f, width=85, height=18, wrap=tk.WORD)
        self.tx2_result.grid(row=11, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)
        f.rowconfigure(11, weight=1)
        self.tx2_result.configure(state="disabled")
        self.calculate_2wt()

    # ── 三绕组变压器子页 ─────────────────────────────────────────────────────

    def _build_3wt_sub(self) -> None:
        f = self._ptab_3wt
        f.columnconfigure(1, weight=1)
        f.columnconfigure(3, weight=1)

        ttk.Label(f, text="三绕组变压器参数校核与标幺值转换",
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(8, 4))

        hint = ("输入约定：Pk 为两两短路试验损耗（kW），Uk% 为两两短路电压（%）。"
                "Pk_HL、Uk_HL 若测试是在低压侧额定电流下做的，"
                "程序会自动按 SN_H/SN_L 折算到高压侧额定电流基准。")
        ttk.Label(f, text=hint, wraplength=900, foreground="#555555").grid(
            row=1, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 6))

        row = 2
        self.tx3_pk_hm  = self._add_entry(f, row,   "短路损耗 Pk_HM / kW",    "503.6",  column=0)
        self.tx3_uk_hm  = self._add_entry(f, row,   "Uk_HM / %",              "17.5",   column=2)
        row += 1
        self.tx3_pk_hl  = self._add_entry(f, row,   "短路损耗 Pk_HL / kW",    "129.0",  column=0)
        self.tx3_uk_hl  = self._add_entry(f, row,   "Uk_HL / %",              "11.0",   column=2)
        row += 1
        self.tx3_pk_ml  = self._add_entry(f, row,   "短路损耗 Pk_ML / kW",    "120.7",  column=0)
        self.tx3_uk_ml  = self._add_entry(f, row,   "Uk_ML / %",              "6.0",    column=2)
        row += 1
        self.tx3_p0     = self._add_entry(f, row,   "空载损耗 P0 / kW",       "76.1",   column=0)
        self.tx3_i0     = self._add_entry(f, row,   "空载电流 I₀ / %",        "0.07",   column=2)
        row += 1
        self.tx3_sn_h   = self._add_entry(f, row,   "高压侧额定容量 SN_H / MVA", "180", column=0)
        self.tx3_un_h   = self._add_entry(f, row,   "高压侧额定电压 UN_H / kV",  "220", column=2)
        row += 1
        self.tx3_sn_m   = self._add_entry(f, row,   "中压侧额定容量 SN_M / MVA", "180", column=0)
        self.tx3_sn_l   = self._add_entry(f, row,   "低压侧额定容量 SN_L / MVA", "90",  column=2)
        row += 1
        self.tx3_sbase  = self._add_entry(f, row,   "基准容量 Sbase / MVA",    "100",   column=0)
        self.tx3_ubase  = self._add_entry(f, row,   "基准电压 Ubase / kV",     "220",   column=2)

        row += 1
        ttk.Button(f, text="计算并校核", command=self.calculate_3wt).grid(
            row=row, column=0, columnspan=4, sticky="ew", padx=8, pady=(8, 4))

        row += 1
        self.tx3_result = ScrolledText(f, width=95, height=18, wrap=tk.WORD)
        self.tx3_result.grid(row=row, column=0, columnspan=4, sticky="nsew", padx=8, pady=4)
        f.rowconfigure(row, weight=1)
        self.tx3_result.configure(state="disabled")
        self.calculate_3wt()

    # ── 参数校核计算处理函数 ─────────────────────────────────────────────────

    def calculate_line_param(self) -> None:
        try:
            R1    = _safe_float(self.lp_r1.get(),    "R₁")
            X1    = _safe_float(self.lp_x1.get(),    "X₁")
            C1    = _safe_float(self.lp_c1.get(),    "C₁")
            length = _safe_float(self.lp_len.get(),  "线路长度")
            Sbase = _safe_float(self.lp_sbase.get(), "Sbase")
            Ubase = _safe_float(self.lp_ubase.get(), "Ubase")

            r = convert_line_to_pu(R1, X1, C1, length, Sbase, Ubase)

            text = (
                f"══ 有名值（π型等值，折算后）══════════════════════\n"
                f"  总电阻  R  = {r.R_total_ohm:.6f} Ω\n"
                f"  总电抗  X  = {r.X_total_ohm:.6f} Ω\n"
                f"  对地电纳半值 B/2 = {r.B_half_S:.8f} S\n"
                f"  波阻抗  Zc = {r.Zc_ohm:.4f} Ω\n"
                f"\n══ 标幺值（Sbase={Sbase:.4g} MVA，Ubase={Ubase:.4g} kV）══════\n"
                f"  基准阻抗 Zbase = {r.Zbase_ohm:.4f} Ω，  "
                f"基准导纳 Ybase = {r.Ybase_S:.8f} S\n"
                f"  R_pu   = {r.R_pu:.8f}  pu\n"
                f"  X_pu   = {r.X_pu:.8f}  pu\n"
                f"  B/2_pu = {r.B_half_pu:.8f}  pu\n"
                f"\n══ 参数校核 ═══════════════════════════════════════\n"
                + _format_warnings(r.warnings)
            )
            self._set_text(self.lp_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_2wt(self) -> None:
        try:
            Pk    = _safe_float(self.tx2_pk.get(),    "Pk")
            Uk    = _safe_float(self.tx2_uk.get(),    "Uk%")
            P0    = _safe_float(self.tx2_p0.get(),    "P0")
            I0    = _safe_float(self.tx2_i0.get(),    "I0%")
            SN    = _safe_float(self.tx2_sn.get(),    "SN")
            UN    = _safe_float(self.tx2_un.get(),    "UN")
            Sbase = _safe_float(self.tx2_sbase.get(), "Sbase")
            Ubase = _safe_float(self.tx2_ubase.get(), "Ubase")

            r = convert_2wt_to_pu(Pk, Uk, P0, I0, SN, UN, Sbase, Ubase)

            text = (
                f"══ 有名值（折算到高压侧 {UN:.4g} kV）══════════════════\n"
                f"  短路电阻   Rk  = {r.Rk_ohm:.6f}  Ω\n"
                f"  短路电抗   Xk  = {r.Xk_ohm:.6f}  Ω\n"
                f"  励磁电导   G₀  = {r.G0_S:.2e}  S\n"
                f"  励磁电纳   B₀  = {r.B0_S:.2e}  S\n"
                f"\n══ 标幺值（Sbase={Sbase:.4g} MVA，Ubase={Ubase:.4g} kV）══════\n"
                f"  基准阻抗 Zbase = {r.Zbase_ohm:.4f} Ω\n"
                f"  Rk_pu  = {r.Rk_pu:.8f}  pu\n"
                f"  Xk_pu  = {r.Xk_pu:.8f}  pu\n"
                f"  G₀_pu  = {r.G0_pu:.8f}  pu\n"
                f"  B₀_pu  = {r.B0_pu:.8f}  pu\n"
                f"  （反算 Uk% ≈ {r.Uk_pct_check:.4f}%，输入 {Uk:.4f}%）\n"
                f"\n══ 参数校核 ═══════════════════════════════════════\n"
                + _format_warnings(r.warnings)
            )
            self._set_text(self.tx2_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_3wt(self) -> None:
        try:
            Pk_HM  = _safe_float(self.tx3_pk_hm.get(),  "Pk_HM")
            Pk_HL  = _safe_float(self.tx3_pk_hl.get(),  "Pk_HL")
            Pk_ML  = _safe_float(self.tx3_pk_ml.get(),  "Pk_ML")
            Uk_HM  = _safe_float(self.tx3_uk_hm.get(),  "Uk_HM%")
            Uk_HL  = _safe_float(self.tx3_uk_hl.get(),  "Uk_HL%")
            Uk_ML  = _safe_float(self.tx3_uk_ml.get(),  "Uk_ML%")
            P0     = _safe_float(self.tx3_p0.get(),     "P0")
            I0     = _safe_float(self.tx3_i0.get(),     "I0%")
            SN_H   = _safe_float(self.tx3_sn_h.get(),   "SN_H")
            SN_M   = _safe_float(self.tx3_sn_m.get(),   "SN_M")
            SN_L   = _safe_float(self.tx3_sn_l.get(),   "SN_L")
            UN_H   = _safe_float(self.tx3_un_h.get(),   "UN_H")
            Sbase  = _safe_float(self.tx3_sbase.get(),  "Sbase")
            Ubase  = _safe_float(self.tx3_ubase.get(),  "Ubase")

            r = convert_3wt_to_pu(
                Pk_HM, Pk_HL, Pk_ML,
                Uk_HM, Uk_HL, Uk_ML,
                P0, I0,
                SN_H, SN_M, SN_L, UN_H,
                Sbase, Ubase)

            SN_base = max(SN_H, SN_M, SN_L)
            text = (
                f"══ 折算参考容量 SN_base = {SN_base:.4g} MVA，折算基压 {UN_H:.4g} kV ══════\n"
                f"\n── 有名值（T型等值，折算到高压侧）────────────────────\n"
                f"  高压绕组  RH = {r.RH_ohm:.6f} Ω，  XH = {r.XH_ohm:.6f} Ω\n"
                f"  中压绕组  RM = {r.RM_ohm:.6f} Ω，  XM = {r.XM_ohm:.6f} Ω\n"
                f"  低压绕组  RL = {r.RL_ohm:.6f} Ω，  XL = {r.XL_ohm:.6f} Ω\n"
                f"\n── 标幺值（Sbase={Sbase:.4g} MVA，Ubase={Ubase:.4g} kV）─────────────\n"
                f"  基准阻抗 Zbase = {r.Zbase_ohm:.4f} Ω\n"
                f"  高压绕组  RH_pu = {r.RH_pu:.8f}，  XH_pu = {r.XH_pu:.8f}\n"
                f"  中压绕组  RM_pu = {r.RM_pu:.8f}，  XM_pu = {r.XM_pu:.8f}\n"
                f"  低压绕组  RL_pu = {r.RL_pu:.8f}，  XL_pu = {r.XL_pu:.8f}\n"
                f"  励磁电导  G₀_pu = {r.G0_pu:.8f}，  励磁电纳 B₀_pu = {r.B0_pu:.8f}\n"
                f"\n══ 参数校核 ═══════════════════════════════════════\n"
                + _format_warnings(r.warnings)
            )
            self._set_text(self.tx3_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))


def main() -> None:
    app = ApproximationToolGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
