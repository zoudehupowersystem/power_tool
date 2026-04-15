"""Single-span conductor sag analysis with catenary geometry and simplified thermal coupling. / 单档导线弧垂分析：悬链线几何 + 简化热平衡耦合。"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from power_tool_common import InputError, _validate_nonnegative, _validate_positive

_G = 9.80665


@dataclass
class ThermalBalanceResult:
    """Simplified steady-state thermal-balance result. / 简化稳态热平衡结果。"""

    current_a: float
    ambient_temp_c: float
    conductor_temp_c: float
    temperature_rise_c: float
    resistance_ohm_per_m: float
    joule_heating_w_per_m: float
    solar_gain_w_per_m: float
    cooling_w_per_m: float


@dataclass
class CatenaryState:
    """Geometric state of a single-span catenary. / 单档悬链线几何状态。"""

    horizontal_tension_n: float
    average_tension_n: float
    left_support_tension_n: float
    right_support_tension_n: float
    catenary_constant_m: float
    arc_length_m: float
    lowest_point_x_m: float
    lowest_point_height_m: float
    minimum_clearance_x_m: float
    minimum_clearance_m: float
    maximum_sag_x_m: float
    maximum_sag_m: float
    midspan_sag_m: float
    support_angle_left_deg: float
    support_angle_right_deg: float
    x_profile_m: np.ndarray
    y_profile_m: np.ndarray
    y_chord_m: np.ndarray
    lowest_point_inside_span: bool


@dataclass
class SagAnalysisResult:
    """Combined mechanical and thermal sag-analysis result. / 热-机械耦合弧垂分析结果。"""

    driver_mode: str
    span_m: float
    left_support_height_m: float
    right_support_height_m: float
    line_mass_kg_per_m: float
    unit_weight_n_per_m: float
    cross_section_mm2: float
    elastic_modulus_gpa: float
    thermal_expansion_per_c: float
    reference_temperature_c: float
    reference_horizontal_tension_n: float
    conductor_temperature_c: float
    current_a: float
    thermal_balance: ThermalBalanceResult | None
    reference_state: CatenaryState
    operating_state: CatenaryState


def _validate_finite(name: str, value: float) -> None:
    """Validate that a scalar is finite. / 校验输入是否为有限实数。"""
    if not math.isfinite(value):
        raise InputError(f"{name} 不是有限实数。")


def conductor_resistance_ohm_per_m(
    resistance_20c_ohm_per_km: float,
    resistance_temp_coeff_per_c: float,
    conductor_temp_c: float,
) -> float:
    """Return the conductor resistance per metre at the specified conductor temperature. / 返回指定导线温度下的每米电阻。"""
    _validate_positive("20°C 电阻", resistance_20c_ohm_per_km)
    _validate_nonnegative("电阻温度系数", resistance_temp_coeff_per_c)
    _validate_finite("导线温度", conductor_temp_c)
    return resistance_20c_ohm_per_km / 1000.0 * (1.0 + resistance_temp_coeff_per_c * (conductor_temp_c - 20.0))


def estimate_conductor_temperature(
    *,
    current_a: float,
    ambient_temp_c: float,
    resistance_20c_ohm_per_km: float,
    resistance_temp_coeff_per_c: float,
    cooling_coeff_w_per_mk: float,
    solar_gain_w_per_m: float = 0.0,
) -> ThermalBalanceResult:
    """Estimate steady-state conductor temperature from a lumped heat balance. / 用集总热平衡近似估算稳态导线温度。

    Model / 模型
    ------------
    The tool uses a linearized steady-state relation
    `I²R(T) + q_s = k_c (T - T_a)` with `R(T) = R20 [1 + α_R (T - 20°C)]`.
    This is intentionally simpler than IEEE 738 and is intended for fast engineering interaction. /
    本工具采用线性化稳态关系 `I²R(T) + q_s = k_c (T - T_a)`，其中
    `R(T) = R20 [1 + α_R (T - 20°C)]`。它刻意比 IEEE 738 更简化，面向快速工程交互。"""
    _validate_nonnegative("载流量", current_a)
    _validate_positive("20°C 电阻", resistance_20c_ohm_per_km)
    _validate_nonnegative("电阻温度系数", resistance_temp_coeff_per_c)
    _validate_positive("等效冷却系数", cooling_coeff_w_per_mk)
    _validate_nonnegative("太阳热增益", solar_gain_w_per_m)
    _validate_finite("环境温度", ambient_temp_c)

    r20 = resistance_20c_ohm_per_km / 1000.0
    denominator = cooling_coeff_w_per_mk - current_a * current_a * r20 * resistance_temp_coeff_per_c
    if denominator <= 1e-9:
        raise InputError(
            "当前载流量与冷却参数组合会导致简化热平衡方程失去稳态解，请降低载流量或增大冷却系数。"
        )

    numerator = (
        current_a * current_a * r20 * (1.0 - 20.0 * resistance_temp_coeff_per_c)
        + cooling_coeff_w_per_mk * ambient_temp_c
        + solar_gain_w_per_m
    )
    conductor_temp_c = numerator / denominator
    resistance_ohm_per_m = conductor_resistance_ohm_per_m(
        resistance_20c_ohm_per_km,
        resistance_temp_coeff_per_c,
        conductor_temp_c,
    )
    joule = current_a * current_a * resistance_ohm_per_m
    cooling = cooling_coeff_w_per_mk * (conductor_temp_c - ambient_temp_c)
    return ThermalBalanceResult(
        current_a=current_a,
        ambient_temp_c=ambient_temp_c,
        conductor_temp_c=conductor_temp_c,
        temperature_rise_c=conductor_temp_c - ambient_temp_c,
        resistance_ohm_per_m=resistance_ohm_per_m,
        joule_heating_w_per_m=joule,
        solar_gain_w_per_m=solar_gain_w_per_m,
        cooling_w_per_m=cooling,
    )


def _catenary_state(
    *,
    span_m: float,
    left_support_height_m: float,
    right_support_height_m: float,
    unit_weight_n_per_m: float,
    horizontal_tension_n: float,
    num_points: int = 401,
) -> CatenaryState:
    """Return the geometric state for a given horizontal tension. / 对给定水平张力求取悬链线几何状态。"""
    _validate_positive("档距", span_m)
    _validate_positive("单位重量", unit_weight_n_per_m)
    _validate_positive("水平张力", horizontal_tension_n)
    _validate_nonnegative("左挂点高度", left_support_height_m)
    _validate_nonnegative("右挂点高度", right_support_height_m)

    a = horizontal_tension_n / unit_weight_n_per_m
    delta_h = right_support_height_m - left_support_height_m
    half_arg = span_m / (2.0 * a)
    sinh_half = math.sinh(half_arg)
    offset = a * math.asinh(delta_h / (2.0 * a * sinh_half))
    x_low = span_m / 2.0 - offset

    y_left_rel = a * (math.cosh((0.0 - x_low) / a) - 1.0)
    y_low_abs = left_support_height_m - y_left_rel

    x = np.linspace(0.0, span_m, num_points)
    y = y_low_abs + a * (np.cosh((x - x_low) / a) - 1.0)
    y_chord = left_support_height_m + delta_h * x / span_m

    x_sag = x_low + a * math.asinh(delta_h / span_m)
    x_sag = min(max(x_sag, 0.0), span_m)
    y_sag = y_low_abs + a * (math.cosh((x_sag - x_low) / a) - 1.0)
    y_chord_sag = left_support_height_m + delta_h * x_sag / span_m
    max_sag = y_chord_sag - y_sag

    x_mid = span_m / 2.0
    y_mid = y_low_abs + a * (math.cosh((x_mid - x_low) / a) - 1.0)
    y_chord_mid = left_support_height_m + delta_h * x_mid / span_m
    midspan_sag = y_chord_mid - y_mid

    x_clear = min(max(x_low, 0.0), span_m)
    y_clear = y_low_abs + a * (math.cosh((x_clear - x_low) / a) - 1.0)
    lowest_inside = 0.0 <= x_low <= span_m

    arc_length = math.sqrt((2.0 * a * sinh_half) ** 2 + delta_h ** 2)

    left_tension = horizontal_tension_n * math.cosh((0.0 - x_low) / a)
    right_tension = horizontal_tension_n * math.cosh((span_m - x_low) / a)
    average_tension = 0.5 * (left_tension + right_tension)

    angle_left = math.degrees(math.atan(math.sinh((0.0 - x_low) / a)))
    angle_right = math.degrees(math.atan(math.sinh((span_m - x_low) / a)))

    return CatenaryState(
        horizontal_tension_n=horizontal_tension_n,
        average_tension_n=average_tension,
        left_support_tension_n=left_tension,
        right_support_tension_n=right_tension,
        catenary_constant_m=a,
        arc_length_m=arc_length,
        lowest_point_x_m=x_low,
        lowest_point_height_m=y_low_abs,
        minimum_clearance_x_m=x_clear,
        minimum_clearance_m=y_clear,
        maximum_sag_x_m=x_sag,
        maximum_sag_m=max_sag,
        midspan_sag_m=midspan_sag,
        support_angle_left_deg=angle_left,
        support_angle_right_deg=angle_right,
        x_profile_m=x,
        y_profile_m=y,
        y_chord_m=y_chord,
        lowest_point_inside_span=lowest_inside,
    )


def _solve_horizontal_tension_for_temperature(
    *,
    span_m: float,
    left_support_height_m: float,
    right_support_height_m: float,
    unit_weight_n_per_m: float,
    cross_section_mm2: float,
    elastic_modulus_gpa: float,
    thermal_expansion_per_c: float,
    reference_temperature_c: float,
    reference_horizontal_tension_n: float,
    conductor_temperature_c: float,
) -> tuple[float, CatenaryState, CatenaryState]:
    """Solve the horizontal tension from temperature using a reference state. / 根据参考状态与导线温度求解当前水平张力。"""
    _validate_positive("截面积", cross_section_mm2)
    _validate_positive("等效弹性模量", elastic_modulus_gpa)
    _validate_nonnegative("线膨胀系数", thermal_expansion_per_c)
    _validate_finite("参考温度", reference_temperature_c)
    _validate_finite("导线温度", conductor_temperature_c)

    area_m2 = cross_section_mm2 * 1e-6
    elastic_modulus_pa = elastic_modulus_gpa * 1e9

    ref_state = _catenary_state(
        span_m=span_m,
        left_support_height_m=left_support_height_m,
        right_support_height_m=right_support_height_m,
        unit_weight_n_per_m=unit_weight_n_per_m,
        horizontal_tension_n=reference_horizontal_tension_n,
    )
    sigma_ref = ref_state.average_tension_n / area_m2
    base_natural_length = ref_state.arc_length_m / (1.0 + sigma_ref / elastic_modulus_pa)
    thermal_factor = 1.0 + thermal_expansion_per_c * (conductor_temperature_c - reference_temperature_c)
    if thermal_factor <= 0.0:
        raise InputError("线膨胀系数与温度组合无效，导致等效自然长度非正。")

    def compatibility_residual(horizontal_tension_n: float) -> float:
        state = _catenary_state(
            span_m=span_m,
            left_support_height_m=left_support_height_m,
            right_support_height_m=right_support_height_m,
            unit_weight_n_per_m=unit_weight_n_per_m,
            horizontal_tension_n=horizontal_tension_n,
            num_points=121,
        )
        sigma = state.average_tension_n / area_m2
        compatible_length = base_natural_length * thermal_factor * (1.0 + sigma / elastic_modulus_pa)
        return state.arc_length_m - compatible_length

    if abs(conductor_temperature_c - reference_temperature_c) < 1e-12:
        return reference_horizontal_tension_n, ref_state, ref_state

    low_floor = max(25.0, 0.01 * unit_weight_n_per_m * span_m)
    if conductor_temperature_c > reference_temperature_c:
        lo = min(low_floor, reference_horizontal_tension_n)
        hi = reference_horizontal_tension_n
        f_hi = compatibility_residual(hi)
        f_lo = compatibility_residual(lo)
        for _ in range(80):
            if f_lo * f_hi <= 0.0:
                break
            lo = max(low_floor * 0.5, lo * 0.5)
            f_lo = compatibility_residual(lo)
        else:
            raise InputError("高温工况下未能为张力求解找到有效区间，请检查参考张力或几何参数。")
    else:
        lo = reference_horizontal_tension_n
        hi = max(reference_horizontal_tension_n * 1.2 + 100.0, reference_horizontal_tension_n + 100.0)
        f_lo = compatibility_residual(lo)
        f_hi = compatibility_residual(hi)
        for _ in range(80):
            if f_lo * f_hi <= 0.0:
                break
            hi *= 1.5
            f_hi = compatibility_residual(hi)
        else:
            raise InputError("低温工况下未能为张力求解找到有效区间，请检查参考张力或几何参数。")

    for _ in range(120):
        mid = 0.5 * (lo + hi)
        f_mid = compatibility_residual(mid)
        if abs(f_mid) < 1e-10:
            break
        if f_lo * f_mid <= 0.0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid
    solved_h = 0.5 * (lo + hi)
    op_state = _catenary_state(
        span_m=span_m,
        left_support_height_m=left_support_height_m,
        right_support_height_m=right_support_height_m,
        unit_weight_n_per_m=unit_weight_n_per_m,
        horizontal_tension_n=solved_h,
    )
    return solved_h, ref_state, op_state


def analyze_conductor_sag(
    *,
    span_m: float,
    left_support_height_m: float,
    right_support_height_m: float,
    line_mass_kg_per_m: float,
    cross_section_mm2: float,
    elastic_modulus_gpa: float,
    thermal_expansion_per_c: float,
    reference_temperature_c: float,
    reference_horizontal_tension_kN: float,
    driver_mode: str,
    conductor_temperature_c: float,
    current_a: float,
    ambient_temp_c: float,
    resistance_20c_ohm_per_km: float,
    resistance_temp_coeff_per_c: float,
    cooling_coeff_w_per_mk: float,
    solar_gain_w_per_m: float = 0.0,
) -> SagAnalysisResult:
    """Run a coupled conductor-sag analysis. / 执行导线弧垂热-机械耦合分析。

    Parameters / 参数
    ----------------
    `driver_mode` accepts either `"temperature"` or `"current"`.
    In current mode the tool first estimates conductor temperature from the simplified thermal-balance model, then solves the sag-tension state. /
    `driver_mode` 取值为 `"temperature"` 或 `"current"`。
    在电流模式下，程序先由简化热平衡估算导线温度，再求解弧垂-张力状态。"""
    _validate_positive("档距", span_m)
    _validate_positive("单位质量", line_mass_kg_per_m)
    _validate_nonnegative("左挂点高度", left_support_height_m)
    _validate_nonnegative("右挂点高度", right_support_height_m)
    _validate_positive("参考水平张力", reference_horizontal_tension_kN)
    _validate_nonnegative("载流量", current_a)
    _validate_finite("导线温度", conductor_temperature_c)
    _validate_finite("环境温度", ambient_temp_c)

    driver = (driver_mode or "temperature").strip().lower()
    if driver not in {"temperature", "current"}:
        raise InputError("驱动方式必须为 temperature 或 current。")

    unit_weight = line_mass_kg_per_m * _G
    reference_horizontal_tension_n = reference_horizontal_tension_kN * 1000.0

    thermal_balance: ThermalBalanceResult | None = None
    active_temp = conductor_temperature_c
    if driver == "current":
        thermal_balance = estimate_conductor_temperature(
            current_a=current_a,
            ambient_temp_c=ambient_temp_c,
            resistance_20c_ohm_per_km=resistance_20c_ohm_per_km,
            resistance_temp_coeff_per_c=resistance_temp_coeff_per_c,
            cooling_coeff_w_per_mk=cooling_coeff_w_per_mk,
            solar_gain_w_per_m=solar_gain_w_per_m,
        )
        active_temp = thermal_balance.conductor_temp_c

    _, ref_state, op_state = _solve_horizontal_tension_for_temperature(
        span_m=span_m,
        left_support_height_m=left_support_height_m,
        right_support_height_m=right_support_height_m,
        unit_weight_n_per_m=unit_weight,
        cross_section_mm2=cross_section_mm2,
        elastic_modulus_gpa=elastic_modulus_gpa,
        thermal_expansion_per_c=thermal_expansion_per_c,
        reference_temperature_c=reference_temperature_c,
        reference_horizontal_tension_n=reference_horizontal_tension_n,
        conductor_temperature_c=active_temp,
    )

    return SagAnalysisResult(
        driver_mode=driver,
        span_m=span_m,
        left_support_height_m=left_support_height_m,
        right_support_height_m=right_support_height_m,
        line_mass_kg_per_m=line_mass_kg_per_m,
        unit_weight_n_per_m=unit_weight,
        cross_section_mm2=cross_section_mm2,
        elastic_modulus_gpa=elastic_modulus_gpa,
        thermal_expansion_per_c=thermal_expansion_per_c,
        reference_temperature_c=reference_temperature_c,
        reference_horizontal_tension_n=reference_horizontal_tension_n,
        conductor_temperature_c=active_temp,
        current_a=current_a,
        thermal_balance=thermal_balance,
        reference_state=ref_state,
        operating_state=op_state,
    )


__all__ = [
    "ThermalBalanceResult",
    "CatenaryState",
    "SagAnalysisResult",
    "conductor_resistance_ohm_per_m",
    "estimate_conductor_temperature",
    "analyze_conductor_sag",
]
