"""共享类型、输入校验与数据加载。"""


from __future__ import annotations


import json


import math


from dataclasses import dataclass


from pathlib import Path


from typing import Optional


import numpy as np


EPS = 1e-10

def load_line_params_reference() -> dict:
    """读取架空线路典型参数 JSON 数据。"""
    data_path = Path(__file__).resolve().with_name("line_params_reference.json")
    if not data_path.exists():
        raise FileNotFoundError(f"未找到典型参数文件：{data_path.name}")
    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    sections = data.get("sections")
    if not isinstance(sections, list):
        raise ValueError("典型参数 JSON 格式错误：缺少 sections 列表。")
    return data

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

@dataclass
class ShortCircuitSummary:
    network_mode: str
    fault_type: str
    neutral_mode: str
    U_kV: float
    line_len_km: float
    fault_pos_from_left_pct: float
    Z1_ohm: complex
    Z2_ohm: complex
    Z0_ohm: complex
    Zn_ohm: complex
    Rf_ohm: float
    I0_A: complex
    I1_A: complex
    I2_A: complex
    Ia_A: complex
    Ib_A: complex
    Ic_A: complex
    V0_V: complex
    V1_V: complex
    V2_V: complex
    Va_V: complex
    Vb_V: complex
    Vc_V: complex
    Ia_from_left_A: complex
    Ib_from_left_A: complex
    Ic_from_left_A: complex
    Ia_from_right_A: complex
    Ib_from_right_A: complex
    Ic_from_right_A: complex
    I_break_left_kA: float
    I_break_right_kA: float
    I_break_kA: float
    tau_dc_s: float
    breaker_ok: Optional[bool]
    notes: str

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

@dataclass
class SMIBOperatingPoint:
    P_pu: float
    Q_pu: float
    terminal_voltage_pu: float
    terminal_angle_deg: float
    infinite_bus_voltage_pu: float
    reference_shift_deg: float
    delta_deg: float
    pm_pu: float
    vf0_pu: float
    vd_pu: float
    vq_pu: float
    id_pu: float
    iq_pu: float
    xline_eq_pu: float
    xnet_pu: float

@dataclass
class SMIBSmallSignalResult:
    config_key: str
    config_label: str
    state_names: list[str]
    operating_point: SMIBOperatingPoint
    A: np.ndarray
    eigenvalues: np.ndarray
    dominant_mode_index: Optional[int]
    dominant_participation: list[tuple[str, float]]
    stable: bool
    notes: str


__all__ = [
    "EPS",
    "load_line_params_reference",
    "InputError",
    "_validate_positive",
    "_validate_nonnegative",
    "_safe_float",
    "FrequencyResponseSummary",
    "ElectromechSummary",
    "VoltageStabilitySummary",
    "NaturalPowerSummary",
    "ImpactMethodSummary",
    "CriticalCutSummary",
    "EACResult",
    "ShortCircuitSummary",
    "ParamWarning",
    "LineParamResult",
    "TwoWindingResult",
    "ThreeWindingResult",
    "SMIBOperatingPoint",
    "SMIBSmallSignalResult",
]
