"""Approximate loop-closure analysis for distribution networks: steady loop current plus simplified impulsive transient. / 配电网合环近似分析：多连接点稳态环流与简化冲击暂态。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from power_tool_common import InputError, _validate_nonnegative, _validate_positive


@dataclass
class LoopClosureSegmentResult:
    index: int
    from_label: str
    to_label: str
    length_km: float
    side: str
    pre_current_A: complex
    post_current_A: complex
    pre_magnitude_A: float
    post_magnitude_A: float
    post_angle_deg: float


@dataclass
class LoopClosureWaveforms:
    t_s: np.ndarray
    loop_a_A: np.ndarray
    loop_b_A: np.ndarray
    loop_c_A: np.ndarray
    left_a_A: np.ndarray
    left_b_A: np.ndarray
    left_c_A: np.ndarray
    right_a_A: np.ndarray
    right_b_A: np.ndarray
    right_c_A: np.ndarray


@dataclass
class LoopClosureResult:
    closure_node_index: int
    node_labels: list[str]
    node_injections_A: list[float]
    segment_lengths_km: list[float]
    line_to_line_delta_kV: float
    loop_impedance_ohm: complex
    loop_impedance_angle_deg: float
    tau_s: float
    two_tau_s: float
    steady_loop_current_A: complex
    steady_loop_current_magnitude_A: float
    steady_loop_current_angle_deg: float
    pre_left_source_A: complex
    pre_right_source_A: complex
    post_left_source_A: complex
    post_right_source_A: complex
    overload_limit_A: Optional[float]
    overloaded_segments: list[str]
    segment_results: list[LoopClosureSegmentResult]
    waveforms: LoopClosureWaveforms
    notes: str


def _complex_polar(magnitude: float, angle_deg: float) -> complex:
    angle_rad = math.radians(angle_deg)
    return magnitude * complex(math.cos(angle_rad), math.sin(angle_rad))


def _phase_waveform(t: np.ndarray, omega: float, phasor: complex, phase_shift_rad: float = 0.0) -> np.ndarray:
    mag = abs(phasor)
    angle = math.atan2(phasor.imag, phasor.real)
    return math.sqrt(2.0) * mag * np.sin(omega * t + angle + phase_shift_rad)


def _rl_closure_waveform(
    t: np.ndarray,
    omega: float,
    steady_phasor: complex,
    close_time_s: float,
    tau_s: float,
    phase_shift_rad: float = 0.0,
) -> np.ndarray:
    mag = abs(steady_phasor)
    angle = math.atan2(steady_phasor.imag, steady_phasor.real) + phase_shift_rad
    out = np.zeros_like(t)
    mask = t >= close_time_s
    if not np.any(mask) or mag <= 0.0:
        return out
    t_on = t[mask]
    steady = math.sqrt(2.0) * mag * np.sin(omega * t_on + angle)
    if tau_s <= 0.0:
        decay = 0.0
    else:
        decay = math.sqrt(2.0) * mag * math.sin(omega * close_time_s + angle) * np.exp(-(t_on - close_time_s) / tau_s)
    out[mask] = steady - decay
    return out


def _normalize_segment_lengths(total_length_km: float, ratios: Sequence[float]) -> list[float]:
    if total_length_km <= 0.0:
        return [0.0 for _ in ratios]
    ratio_sum = float(sum(ratios))
    if ratio_sum <= 0.0:
        raise InputError("线段比例之和必须大于 0。")
    return [total_length_km * float(r) / ratio_sum for r in ratios]


def loop_closure_analysis(
    u1_kv_ll: float,
    u2_kv_ll: float,
    angle_deg: float,
    r_loop_ohm: float,
    x_loop_ohm: float,
    frequency_hz: float,
    closure_node_index: int,
    node_injections_A: Sequence[float],
    node_labels: Optional[Sequence[str]] = None,
    power_factor: float = 0.99,
    pf_mode: str = "lagging",
    total_length_km: float = 0.0,
    segment_ratios: Optional[Sequence[float]] = None,
    ampacity_A: Optional[float] = None,
    overload_factor: float = 1.5,
    close_time_s: float = 0.10,
    t_end_s: float = 0.30,
    n_samples: int = 2400,
) -> LoopClosureResult:
    """Approximate loop-closure analysis for a distribution network. / 配电网合环近似分析。
    
    Parameter notes / 参数说明
    ----------------------------
    node_injections_A:
        Net current at each connection node, in amperes. / 连接点净电流，单位 A。
        Positive values denote load current, and negative values denote DG backfeed current. / 正值表示负荷电流，负值表示分布式电源向线路回送电流。
        The row indexed by `closure_node_index` must be an empty point, i.e. zero net current. / `closure_node_index` 对应行必须为空点，即净电流为 0。
    pf_mode:
        "lagging" or "leading". / “滞后”或“超前”。"""
    _validate_positive("U1", u1_kv_ll)
    _validate_positive("U2", u2_kv_ll)
    _validate_positive("合环回路电阻 RΣ", r_loop_ohm)
    _validate_nonnegative("合环回路电抗 XΣ", x_loop_ohm)
    _validate_positive("系统频率", frequency_hz)
    _validate_nonnegative("线路总长度", total_length_km)
    _validate_positive("功率因数 cosφ", power_factor)
    if power_factor > 1.0:
        raise InputError("功率因数 cosφ 必须满足 0 < cosφ ≤ 1。")
    _validate_positive("过载系数", overload_factor)
    _validate_nonnegative("合环时刻", close_time_s)
    _validate_positive("仿真结束时刻", t_end_s)
    if t_end_s <= close_time_s:
        raise InputError("仿真结束时刻必须大于合环时刻。")
    if n_samples < 200:
        raise InputError("暂态仿真采样点数过少，建议不少于 200。")

    node_values = [float(v) for v in node_injections_A]
    n_nodes = len(node_values)
    if n_nodes <= 0:
        raise InputError("至少需要 1 个连接点。")
    if not (1 <= closure_node_index <= n_nodes):
        raise InputError(f"合环点编号必须位于 1~{n_nodes} 之间。")
    closure_zero_idx = closure_node_index - 1
    if abs(node_values[closure_zero_idx]) > 1e-9:
        raise InputError("合环点对应连接点必须为空点，其净潮流电流应填 0。")

    if node_labels is None:
        labels = [f"点{i}" for i in range(1, n_nodes + 1)]
    else:
        if len(node_labels) != n_nodes:
            raise InputError("连接点标签数量必须与 N 相同。")
        labels = [str(lbl).strip() or f"点{i}" for i, lbl in enumerate(node_labels, start=1)]

    if segment_ratios is None:
        ratios = [1.0] * (n_nodes + 1)
    else:
        if len(segment_ratios) != n_nodes + 1:
            raise InputError(f"线段比例数量必须为 N+1={n_nodes + 1}。")
        ratios = [float(r) for r in segment_ratios]
    for idx, ratio in enumerate(ratios, start=1):
        _validate_positive(f"线段比例 r{idx}", ratio)
    segment_lengths_km = _normalize_segment_lengths(total_length_km, ratios)

    if ampacity_A is not None:
        _validate_positive("线路额定载流量", ampacity_A)
        overload_limit = ampacity_A * overload_factor
    else:
        overload_limit = None

    pf_angle_deg = math.degrees(math.acos(power_factor))
    pf_mode_key = pf_mode.strip().lower()
    if pf_mode_key in {"lagging", "滞后", "load"}:
        current_angle_offset_deg = -pf_angle_deg
        pf_text = "滞后"
    elif pf_mode_key in {"leading", "超前"}:
        current_angle_offset_deg = +pf_angle_deg
        pf_text = "超前"
    else:
        raise InputError("功率因数类型仅支持：滞后 / 超前。")

    loop_impedance = complex(r_loop_ohm, x_loop_ohm)
    loop_impedance_angle_deg = math.degrees(math.atan2(loop_impedance.imag, loop_impedance.real))

    u1 = _complex_polar(u1_kv_ll * 1e3, 0.0)
    u2 = _complex_polar(u2_kv_ll * 1e3, angle_deg)
    delta_u_ll = abs(u2 - u1) / 1e3
    i_loop = (u2 - u1) / (math.sqrt(3.0) * loop_impedance)

    omega = 2.0 * math.pi * frequency_hz
    tau_s = x_loop_ohm / (omega * r_loop_ohm) if x_loop_ohm > 0.0 else 0.0
    two_tau_s = 2.0 * tau_s

    left_base = _complex_polar(1.0, current_angle_offset_deg)
    right_base = _complex_polar(1.0, angle_deg + current_angle_offset_deg)

    points = ["左端"] + labels + ["右端"]
    segment_results: list[LoopClosureSegmentResult] = []
    overloaded_segments: list[str] = []

    for seg in range(n_nodes + 1):
        if seg < closure_node_index:
            scalar = float(sum(node_values[seg:closure_node_index - 1]))
            side = "left"
            pre = scalar * left_base
            post = pre - i_loop
        else:
            scalar = float(sum(node_values[closure_node_index:seg]))
            side = "right"
            pre = scalar * right_base
            post = pre + i_loop

        name = f"{points[seg]} → {points[seg + 1]}"
        post_mag = abs(post)
        if overload_limit is not None and post_mag > overload_limit + 1e-9:
            overloaded_segments.append(name)

        segment_results.append(
            LoopClosureSegmentResult(
                index=seg + 1,
                from_label=points[seg],
                to_label=points[seg + 1],
                length_km=segment_lengths_km[seg],
                side=side,
                pre_current_A=pre,
                post_current_A=post,
                pre_magnitude_A=abs(pre),
                post_magnitude_A=post_mag,
                post_angle_deg=math.degrees(math.atan2(post.imag, post.real)),
            )
        )

    pre_left_source = segment_results[0].pre_current_A
    post_left_source = segment_results[0].post_current_A
    pre_right_source = segment_results[-1].pre_current_A
    post_right_source = segment_results[-1].post_current_A

    t = np.linspace(0.0, t_end_s, int(n_samples), dtype=float)
    phase_shifts = (0.0, -2.0 * math.pi / 3.0, 2.0 * math.pi / 3.0)

    loop_a = _rl_closure_waveform(t, omega, i_loop, close_time_s, tau_s, phase_shifts[0])
    loop_b = _rl_closure_waveform(t, omega, i_loop, close_time_s, tau_s, phase_shifts[1])
    loop_c = _rl_closure_waveform(t, omega, i_loop, close_time_s, tau_s, phase_shifts[2])

    left_pre_a = _phase_waveform(t, omega, pre_left_source, phase_shifts[0])
    left_pre_b = _phase_waveform(t, omega, pre_left_source, phase_shifts[1])
    left_pre_c = _phase_waveform(t, omega, pre_left_source, phase_shifts[2])
    right_pre_a = _phase_waveform(t, omega, pre_right_source, phase_shifts[0])
    right_pre_b = _phase_waveform(t, omega, pre_right_source, phase_shifts[1])
    right_pre_c = _phase_waveform(t, omega, pre_right_source, phase_shifts[2])

    left_a = left_pre_a.copy()
    left_b = left_pre_b.copy()
    left_c = left_pre_c.copy()
    right_a = right_pre_a.copy()
    right_b = right_pre_b.copy()
    right_c = right_pre_c.copy()
    mask = t >= close_time_s
    left_a[mask] = left_pre_a[mask] - loop_a[mask]
    left_b[mask] = left_pre_b[mask] - loop_b[mask]
    left_c[mask] = left_pre_c[mask] - loop_c[mask]
    right_a[mask] = right_pre_a[mask] + loop_a[mask]
    right_b[mask] = right_pre_b[mask] + loop_b[mask]
    right_c[mask] = right_pre_c[mask] + loop_c[mask]

    waveforms = LoopClosureWaveforms(
        t_s=t,
        loop_a_A=loop_a,
        loop_b_A=loop_b,
        loop_c_A=loop_c,
        left_a_A=left_a,
        left_b_A=left_b,
        left_c_A=left_c,
        right_a_A=right_a,
        right_b_A=right_b,
        right_c_A=right_c,
    )

    notes = (
        "本模块是配电网合环的工程近似工具：各连接点以净线电流表示，"
        "正值表示负荷、负值表示分布式电源回送；合环前默认同侧连接点具有统一功率因数。"
        " 合环暂态采用单一 R-L 回路叠加法，适合环流、电流分布与保护配合的快速判断，"
        "不等价于 PSCAD/EMTP 或 Simulink 的详细电磁暂态仿真。"
    )

    return LoopClosureResult(
        closure_node_index=closure_node_index,
        node_labels=labels,
        node_injections_A=node_values,
        segment_lengths_km=segment_lengths_km,
        line_to_line_delta_kV=delta_u_ll,
        loop_impedance_ohm=loop_impedance,
        loop_impedance_angle_deg=loop_impedance_angle_deg,
        tau_s=tau_s,
        two_tau_s=two_tau_s,
        steady_loop_current_A=i_loop,
        steady_loop_current_magnitude_A=abs(i_loop),
        steady_loop_current_angle_deg=math.degrees(math.atan2(i_loop.imag, i_loop.real)),
        pre_left_source_A=pre_left_source,
        pre_right_source_A=pre_right_source,
        post_left_source_A=post_left_source,
        post_right_source_A=post_right_source,
        overload_limit_A=overload_limit,
        overloaded_segments=overloaded_segments,
        segment_results=segment_results,
        waveforms=waveforms,
        notes=notes + f" 统一功率因数按 {power_factor:.4f}（{pf_text}）处理。",
    )


__all__ = [
    "LoopClosureSegmentResult",
    "LoopClosureWaveforms",
    "LoopClosureResult",
    "loop_closure_analysis",
]
