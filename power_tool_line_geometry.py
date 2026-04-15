"""Compute positive- and zero-sequence overhead-line parameters from geometric data. / 由几何数据计算架空线路正序/零序参数。"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from power_tool_common import InputError, _validate_nonnegative, _validate_positive

_MU0 = 4.0 * math.pi * 1e-7
_EPS0 = 8.854187817e-12
_A = np.array(
    [
        [1.0 + 0.0j, 1.0 + 0.0j, 1.0 + 0.0j],
        [1.0 + 0.0j, complex(-0.5, -math.sqrt(3.0) / 2.0), complex(-0.5, math.sqrt(3.0) / 2.0)],
        [1.0 + 0.0j, complex(-0.5, math.sqrt(3.0) / 2.0), complex(-0.5, -math.sqrt(3.0) / 2.0)],
    ],
    dtype=complex,
)
_A_INV = np.linalg.inv(_A)
_TRANSPOSE_PERMUTATIONS: tuple[tuple[int, int, int], ...] = ((0, 1, 2), (1, 2, 0), (2, 0, 1))


@dataclass(frozen=True)
class LineGeometryResult:
    frequency_hz: float
    soil_resistivity_ohm_m: float
    has_ground_wire: bool
    phase_bundle_count: int
    phase_bundle_resistance_ohm_per_km: float
    phase_bundle_gmr_m: float
    phase_bundle_radius_m: float
    D_ab_m: float
    D_bc_m: float
    D_ca_m: float
    Z1_ohm_per_km: complex
    Z0_ohm_per_km: complex
    Y1_S_per_km: complex
    Y0_S_per_km: complex
    C1_uF_per_km: float
    C0_uF_per_km: float
    B1_uS_per_km: float
    B0_uS_per_km: float
    Zabc_ohm_per_km: np.ndarray
    Yabc_S_per_km: np.ndarray
    notes: str


@dataclass(frozen=True)
class _Conductor:
    x_m: float
    h_m: float
    resistance_ohm_per_km: float
    gmr_m: float
    radius_m: float


def bundle_equivalent_parameters(
    resistance_sub_ohm_per_km: float,
    gmr_sub_m: float,
    radius_sub_m: float,
    bundle_count: int = 1,
    bundle_spacing_m: float = 0.0,
) -> tuple[float, float, float]:
    """Derive equivalent phase-conductor parameters from sub-conductor data. / 由单分裂导线参数得到等效相导线参数。
    
    Return values / 返回值依次为：
    - Equivalent phase-conductor resistance (Ω/km). / 等效相导线电阻（Ω/km）
    - Equivalent phase-conductor GMR (m). / 等效相导线 GMR（m）
    - Equivalent phase-conductor electrostatic radius (m). / 等效相导线电容半径（m）
    
    Conventions / 约定：
    - `bundle_count=1` means a single conductor. / `bundle_count=1` 表示单导线。
    - `bundle_count=2/3/4` are approximated as duplex, equilateral-triplex, and square-quad bundles. / `bundle_count=2/3/4` 分别按双分裂、等边三分裂、正方形四分裂近似。
    - `resistance_sub_ohm_per_km`, `gmr_sub_m`, and `radius_sub_m` are all single sub-conductor data. / `resistance_sub_ohm_per_km`、`gmr_sub_m`、`radius_sub_m` 均为单根子导线数据。"""
    _validate_positive("单分裂导线电阻", resistance_sub_ohm_per_km)
    _validate_positive("单分裂导线 GMR", gmr_sub_m)
    _validate_positive("单分裂导线半径", radius_sub_m)

    if bundle_count not in {1, 2, 3, 4}:
        raise InputError("分裂根数仅支持 1、2、3、4。")

    if bundle_count == 1:
        return resistance_sub_ohm_per_km, gmr_sub_m, radius_sub_m

    _validate_positive("分裂间距", bundle_spacing_m)

    resistance_eq = resistance_sub_ohm_per_km / float(bundle_count)
    if bundle_count == 2:
        gmr_eq = math.sqrt(gmr_sub_m * bundle_spacing_m)
        radius_eq = math.sqrt(radius_sub_m * bundle_spacing_m)
    elif bundle_count == 3:
        gmr_eq = (gmr_sub_m * bundle_spacing_m * bundle_spacing_m) ** (1.0 / 3.0)
        radius_eq = (radius_sub_m * bundle_spacing_m * bundle_spacing_m) ** (1.0 / 3.0)
    else:  # bundle_count == 4, approximated as a square arrangement. / bundle_count == 4，按正方形排列近似
        factor = 2.0 ** 0.125
        gmr_eq = factor * (gmr_sub_m * bundle_spacing_m ** 3) ** 0.25
        radius_eq = factor * (radius_sub_m * bundle_spacing_m ** 3) ** 0.25
    return resistance_eq, gmr_eq, radius_eq


def _validate_phase_positions(phase_positions: Sequence[tuple[float, float]]) -> None:
    if len(phase_positions) != 3:
        raise InputError("相导线几何位置必须恰好提供 A/B/C 三相。")

    names = ("A", "B", "C")
    for name, (x_m, h_m) in zip(names, phase_positions):
        if not math.isfinite(x_m) or not math.isfinite(h_m):
            raise InputError(f"{name} 相坐标必须是有限实数。")
        _validate_positive(f"{name} 相离地高度", h_m)

    for (name_i, (xi, hi)), (name_j, (xj, hj)) in (
        ((names[0], phase_positions[0]), (names[1], phase_positions[1])),
        ((names[1], phase_positions[1]), (names[2], phase_positions[2])),
        ((names[0], phase_positions[0]), (names[2], phase_positions[2])),
    ):
        if math.hypot(xi - xj, hi - hj) <= 1e-9:
            raise InputError(f"{name_i} 与 {name_j} 相几何位置重合，无法计算。")


def _complex_depth(soil_resistivity_ohm_m: float, omega: float) -> complex:
    return cmath.sqrt(soil_resistivity_ohm_m / (1j * omega * _MU0))


def _primitive_series_matrix(
    conductors: Sequence[_Conductor],
    frequency_hz: float,
    soil_resistivity_ohm_m: float,
) -> np.ndarray:
    omega = 2.0 * math.pi * frequency_hz
    p = _complex_depth(soil_resistivity_ohm_m, omega)
    coef = 1j * omega * _MU0 * 1000.0 / (2.0 * math.pi)  # Ω/km / 单位为 Ω/km
    n = len(conductors)
    mat = np.zeros((n, n), dtype=complex)

    for i, ci in enumerate(conductors):
        for j, cj in enumerate(conductors):
            if i == j:
                if ci.h_m <= ci.radius_m:
                    raise InputError("导线离地高度必须大于导线物理半径。")
                mat[i, i] = ci.resistance_ohm_per_km + coef * cmath.log(2.0 * (ci.h_m + p) / ci.gmr_m)
            else:
                dij = math.hypot(ci.x_m - cj.x_m, ci.h_m - cj.h_m)
                if dij <= 1e-12:
                    raise InputError("两导线之间距离为 0，无法构造阻抗矩阵。")
                dij_p = cmath.sqrt((ci.x_m - cj.x_m) ** 2 + (ci.h_m + cj.h_m + 2.0 * p) ** 2)
                mat[i, j] = coef * cmath.log(dij_p / dij)
    return mat


def _primitive_potential_matrix(conductors: Sequence[_Conductor]) -> np.ndarray:
    coef = 1.0 / (2.0 * math.pi * _EPS0)
    n = len(conductors)
    mat = np.zeros((n, n), dtype=float)

    for i, ci in enumerate(conductors):
        for j, cj in enumerate(conductors):
            if i == j:
                if ci.h_m <= ci.radius_m:
                    raise InputError("导线离地高度必须大于导线物理半径。")
                mat[i, i] = coef * math.log(2.0 * ci.h_m / ci.radius_m)
            else:
                dij = math.hypot(ci.x_m - cj.x_m, ci.h_m - cj.h_m)
                if dij <= 1e-12:
                    raise InputError("两导线之间距离为 0，无法构造电位系数矩阵。")
                dij_img = math.hypot(ci.x_m - cj.x_m, ci.h_m + cj.h_m)
                mat[i, j] = coef * math.log(dij_img / dij)
    return mat


def _kron_reduce_with_ground(mat: np.ndarray) -> np.ndarray:
    if mat.shape[0] <= 3:
        return mat.copy()
    mpp = mat[:3, :3]
    mpg = mat[:3, 3:]
    mgp = mat[3:, :3]
    mgg = mat[3:, 3:]
    return mpp - mpg @ np.linalg.inv(mgg) @ mgp


def _circulantize_three_phase(mat: np.ndarray) -> np.ndarray:
    diag = complex(np.trace(mat) / 3.0)
    off = complex((np.sum(mat) - np.trace(mat)) / 6.0)
    out = np.full((3, 3), off, dtype=complex)
    np.fill_diagonal(out, diag)
    return out


def _sequence_transform(mat_abc: np.ndarray) -> np.ndarray:
    return _A_INV @ mat_abc @ _A


def calculate_overhead_line_sequence(
    *,
    frequency_hz: float,
    soil_resistivity_ohm_m: float,
    phase_positions: Sequence[tuple[float, float]],
    phase_resistance_ohm_per_km: float,
    phase_gmr_m: float,
    phase_radius_m: float,
    phase_bundle_count: int = 1,
    phase_bundle_spacing_m: float = 0.0,
    has_ground_wire: bool = False,
    ground_wire_position: tuple[float, float] | None = None,
    ground_wire_resistance_ohm_per_km: float = 0.0,
    ground_wire_gmr_m: float = 0.0,
    ground_wire_radius_m: float = 0.0,
) -> LineGeometryResult:
    """Calculate overhead-line sequence parameters from conductor geometry. / 按导线几何数据计算架空线路序参数。
    
    Parameter notes / 参数说明
    ----------------------------
    `phase_positions` contains the `(x, h)` coordinates of the three phase conductors in metres, where `h` is the height above ground. / `phase_positions` 为三相导线的 `(x, h)` 坐标（m），其中 `h` 为离地高度。
    
    Model / 计算模型：
    - Series parameters use the complex-depth approximation to include earth-return effect and soil resistivity. / 串联参数采用复深度近似计及大地回路与土壤电阻率。
    - Shunt capacitance/admittance uses the method-of-images potential-coefficient matrix. / 对地电容/电纳采用镜像法电位系数矩阵。
    - If a ground wire is enabled, it is treated as a continuously grounded conductor and eliminated through Kron reduction. / 若启用地线，则按连续接地导体处理，并通过 Kron 消去得到三相等值矩阵。
    - Final positive- and zero-sequence values are averaged over a fully transposed three-section line. / 最终按三段完全换位平均，输出正序和零序参数。"""
    _validate_positive("频率", frequency_hz)
    _validate_positive("土壤电阻率", soil_resistivity_ohm_m)
    _validate_phase_positions(phase_positions)

    phase_r_eq, phase_gmr_eq, phase_radius_eq = bundle_equivalent_parameters(
        phase_resistance_ohm_per_km,
        phase_gmr_m,
        phase_radius_m,
        phase_bundle_count,
        phase_bundle_spacing_m,
    )

    phase_cond = [
        _Conductor(x_m=x_m, h_m=h_m, resistance_ohm_per_km=phase_r_eq, gmr_m=phase_gmr_eq, radius_m=phase_radius_eq)
        for x_m, h_m in phase_positions
    ]

    ground_cond: list[_Conductor] = []
    if has_ground_wire:
        if ground_wire_position is None:
            raise InputError("已勾选有地线，但未提供地线几何位置。")
        xg_m, hg_m = ground_wire_position
        if not math.isfinite(xg_m) or not math.isfinite(hg_m):
            raise InputError("地线坐标必须是有限实数。")
        _validate_positive("地线离地高度", hg_m)
        _validate_nonnegative("地线交流电阻", ground_wire_resistance_ohm_per_km)
        _validate_positive("地线 GMR", ground_wire_gmr_m)
        _validate_positive("地线半径", ground_wire_radius_m)
        ground_cond.append(
            _Conductor(
                x_m=xg_m,
                h_m=hg_m,
                resistance_ohm_per_km=ground_wire_resistance_ohm_per_km,
                gmr_m=ground_wire_gmr_m,
                radius_m=ground_wire_radius_m,
            )
        )

    z_abc_acc = np.zeros((3, 3), dtype=complex)
    y_abc_acc = np.zeros((3, 3), dtype=complex)

    for perm in _TRANSPOSE_PERMUTATIONS:
        phase_section = [phase_cond[idx] for idx in perm]
        conductors = phase_section + ground_cond

        z_primitive = _primitive_series_matrix(conductors, frequency_hz, soil_resistivity_ohm_m)
        z_reduced = _kron_reduce_with_ground(z_primitive)
        z_abc_acc += z_reduced

        p_primitive = _primitive_potential_matrix(conductors)
        p_reduced = _kron_reduce_with_ground(p_primitive)
        c_abc_f_per_km = np.linalg.inv(p_reduced) * 1000.0
        y_abc_acc += 1j * 2.0 * math.pi * frequency_hz * c_abc_f_per_km

    z_abc = _circulantize_three_phase(z_abc_acc / 3.0)
    y_abc = _circulantize_three_phase(y_abc_acc / 3.0)

    z_012 = _sequence_transform(z_abc)
    y_012 = _sequence_transform(y_abc)

    z0 = complex(z_012[0, 0])
    z1 = complex(z_012[1, 1])
    y0 = complex(y_012[0, 0])
    y1 = complex(y_012[1, 1])

    omega = 2.0 * math.pi * frequency_hz
    c1_uF_per_km = max(0.0, y1.imag / omega * 1e6)
    c0_uF_per_km = max(0.0, y0.imag / omega * 1e6)
    b1_uS_per_km = y1.imag * 1e6
    b0_uS_per_km = y0.imag * 1e6

    (xa, ha), (xb, hb), (xc, hc) = phase_positions
    d_ab = math.hypot(xa - xb, ha - hb)
    d_bc = math.hypot(xb - xc, hb - hc)
    d_ca = math.hypot(xc - xa, hc - ha)

    notes = (
        "假设：单回架空线路、三相导线型号一致并按三段完全换位平均；"
        "串联参数用复深度近似计及土壤电阻率，大地回路电阻/电抗已包含在序阻抗内；"
        "对地电容/电纳采用镜像法电位系数矩阵，介质电导与土壤介电损耗未计。"
    )
    if has_ground_wire:
        notes += " 地线按连续接地导体处理，并通过 Kron 消去得到三相等值矩阵。"
    else:
        notes += " 当前计算未考虑地线屏蔽效应。"
    if phase_bundle_count == 4:
        notes += " 四分裂导线按正方形排列近似。"

    return LineGeometryResult(
        frequency_hz=frequency_hz,
        soil_resistivity_ohm_m=soil_resistivity_ohm_m,
        has_ground_wire=has_ground_wire,
        phase_bundle_count=phase_bundle_count,
        phase_bundle_resistance_ohm_per_km=phase_r_eq,
        phase_bundle_gmr_m=phase_gmr_eq,
        phase_bundle_radius_m=phase_radius_eq,
        D_ab_m=d_ab,
        D_bc_m=d_bc,
        D_ca_m=d_ca,
        Z1_ohm_per_km=z1,
        Z0_ohm_per_km=z0,
        Y1_S_per_km=y1,
        Y0_S_per_km=y0,
        C1_uF_per_km=c1_uF_per_km,
        C0_uF_per_km=c0_uF_per_km,
        B1_uS_per_km=b1_uS_per_km,
        B0_uS_per_km=b0_uS_per_km,
        Zabc_ohm_per_km=z_abc,
        Yabc_S_per_km=y_abc,
        notes=notes,
    )


__all__ = [
    "LineGeometryResult",
    "bundle_equivalent_parameters",
    "calculate_overhead_line_sequence",
]
