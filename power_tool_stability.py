"""Approximate transient-stability analysis: impact method, critical clearing angle, and equal-area criterion. / 暂态稳定近似分析：冲击法、临界切除角、等面积法。"""


from __future__ import annotations


import math


from typing import Optional


from power_tool_common import (
    InputError,
    ImpactMethodSummary,
    CriticalCutSummary,
    EACResult,
    _validate_positive,
    _validate_nonnegative,
)


def impact_method(delta_p: float,
                  delta_t_s: float,
                  f_d_hz: float,
                  p_current_pu: Optional[float] = None) -> ImpactMethodSummary:
    """Quick estimate of the power-oscillation amplitude using the impact method. / 冲击法快估功率振荡幅度。"""
    _validate_positive("ΔP", delta_p)
    _validate_positive("Δt", delta_t_s)
    _validate_positive("f_d", f_d_hz)

    dp = delta_p * delta_t_s * 2.0 * math.pi * f_d_hz
    amp = dp

    margin = None
    if p_current_pu is not None:
        margin = amp - abs(p_current_pu)
        status = "振荡幅值可接受" if margin <= 0 else "振荡幅值偏大"
    else:
        status = "未输入当前传输功率，无法给出相对幅值判据"

    notes = (
        "冲击法在此仅用于估算第一摆功率振荡幅度（ΔP_osc≈ΔP·Δt·2πf_d），"
        "不再用于极限功率判断。若需稳定极限应采用等面积法或时域仿真。"
    )

    return ImpactMethodSummary(
        Dp_pu=dp,
        osc_amp_pu=amp,
        margin_pu=margin,
        status=status,
        notes=notes,
    )

def critical_cut_angle_approx(Pm: float,
                               Pmax_post: float,
                               Tj: float,
                               f0: float,
                               delta_t_given: Optional[float] = None) -> CriticalCutSummary:
    """Engineering quick estimate of the critical clearing angle and critical clearing time (§7.6 approximation). / 临界切除角与临界切除时间的工程快速估算（§7.6 近似公式）。
    
    Assumptions / 适用假设：
    - Solid three-phase fault with electromagnetic power approximately zero during the fault (`Pmax_fault = 0`). / 三相金属性短路，故障期间电磁功率约为 0。
    - The pre-fault and post-fault transfer maxima are identical and both use `Pmax_post`. / 故障前后最大功率相同，均取 `Pmax_post`。
    - During the fault, the accelerating power is approximated as a constant `Pm`. / 故障期间加速功率近似为常数 `Pm`。
    
    Formula / 公式：
    δ0  = arcsin(Pm / Pmax)
    δcr = arccos[ Pm/Pmax · (π − 2δ0) − cos δ0 ]
    tcr = sqrt( 2·Tj·(δcr − δ0) / (ω0·Pm) )"""
    _validate_positive("Pm（临界切除）", Pm)
    _validate_positive("Pmax_post（临界切除）", Pmax_post)
    _validate_positive("Tj（临界切除）", Tj)
    _validate_positive("f0（临界切除）", f0)

    if Pm >= Pmax_post:
        raise InputError("临界切除角估算：Pm 必须小于 Pmax_post，否则故障后无稳定平衡点。")

    omega0 = 2.0 * math.pi * f0
    ratio = Pm / Pmax_post

    delta0 = math.asin(ratio)              # In radians; the stable equilibrium angle before the fault (and also after the fault here). / 弧度，故障前（同时也是故障后）稳定平衡角

    # Critical clearing angle: closed-form expression for the extreme case Pmax_fault = 0 and Pmax_pre = Pmax_post. / 临界切除角（等面积法在 Pmax_fault=0、Pmax_pre=Pmax_post 极端情形下的解析式）
    cos_cr = ratio * (math.pi - 2.0 * delta0) - math.cos(delta0)
    cos_cr = max(-1.0, min(1.0, cos_cr))   # Numerical safeguard. / 数值保护
    delta_cr = math.acos(cos_cr)

    # Critical clearing time under the constant-acceleration approximation. / 临界切除时间（匀加速近似）
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

def _acc_area(delta0: float, deltac: float, Pm: float, Pmax_f: float) -> float:
    """Acceleration area ∫[δ0→δc] (Pm − Pmax_f·sinδ) dδ. / 加速面积 ∫[δ0→δc] (Pm − Pmax_f·sinδ) dδ。"""
    return Pm * (deltac - delta0) - Pmax_f * (math.cos(delta0) - math.cos(deltac))

def _dec_area(deltac: float, deltamax: float, Pm: float, Pmax_post: float) -> float:
    """Deceleration area ∫[δc→δmax] (Pmax_post·sinδ − Pm) dδ. / 减速面积 ∫[δc→δmax] (Pmax_post·sinδ − Pm) dδ。"""
    return Pmax_post * (math.cos(deltac) - math.cos(deltamax)) - Pm * (deltamax - deltac)

def _swing_integrate_to_angle(delta0: float, target: float,
                              Pm: float, Pmax_f: float,
                              Tj: float, f0: float,
                              max_t: float = 5.0, dt: float = 1e-4) -> float:
    """Integrate the swing equation with RK4 from δ0 and return the time required to reach the target angle (radians). / 用 RK4 积分摆动方程，从 δ0 出发，返回到达目标角（弧度）所需时间。
    Equation / 方程：d²δ/dt² = (ω0/Tj)·(Pm − Pmax_f·sinδ)
    If the target is not reached, `max_t` is returned, indicating that the required clearing time exceeds the integration limit. / 找不到时返回 `max_t`，表示极限切除时间超过积分上限。"""
    omega0 = 2.0 * math.pi * f0
    k = omega0 / Tj

    # State vector: y = [δ, dδ/dt]. / 状态：y = [δ, dδ/dt]
    def deriv(y: list[float]) -> list[float]:
        d, v = y
        return [v, k * (Pm - Pmax_f * math.sin(d))]

    y = [delta0, 0.0]
    t = 0.0
    while t < max_t:
        if y[0] >= target:
            return t
        # RK4 integration / RK4 积分
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
    """Equal-area criterion for a single-machine infinite-bus system. / 单机无穷大系统等面积法。
    
    Three power-angle curves / 三段功角曲线：
        Pre-fault  `Pe_pre   = Pmax_pre   · sin δ` / 故障前 `Pe_pre   = Pmax_pre   · sin δ`
        Faulted    `Pe_fault = Pmax_fault · sin δ` / 故障中 `Pe_fault = Pmax_fault · sin δ`
        Post-fault `Pe_post  = Pmax_post  · sin δ` / 故障后 `Pe_post  = Pmax_post  · sin δ`
    
    Parameters / 参数
    -----------------
    Pm: Mechanical power in per unit, assumed constant. / 机械功率（pu，假设恒定）。
    Pmax_pre: Pre-fault maximum transferable power (pu). / 故障前最大传输功率（pu）。
    Pmax_fault: Maximum transferable power during the fault (pu); use 0 for a solid three-phase fault. / 故障中最大传输功率（pu），三相故障取 0。
    Pmax_post: Post-fault maximum transferable power (pu). / 故障后最大传输功率（pu）。
    delta_t_s: Fault clearing time (s). / 故障切除时间（s）。
    Tj: Inertia time constant (s). / 惯性时间常数（s）。
    f0: Rated frequency (Hz). / 额定频率（Hz）。"""
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

    # 1. Key angles / 关键角度 ──────────────────────────────────────────────────────
    delta0 = math.asin(Pm / Pmax_pre)          # Pre-fault SEP (stable equilibrium point). / 故障前 SEP
    deltau = math.pi - math.asin(Pm / Pmax_post)  # Post-fault UEP (unstable equilibrium point). / 故障后 UEP

    # 2. Fault-clearing angle from RK4 swing-equation integration / 故障切除角（RK4 数值积分摆动方程） ───────────────────────────
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

    # 3. Acceleration area / 加速面积 ──────────────────────────────────────────────────────
    A_acc = _acc_area(delta0, deltac, Pm, Pmax_fault)
    if A_acc < 0:
        A_acc = 0.0  # Protection for extreme cases with extremely fast clearing. / 极端情况（切除极快）保护

    # 4. Available deceleration area (δc → δu) / 可用减速面积（δc → δu） ─────────────────────────────────────
    A_dec_avail = _dec_area(deltac, deltau, Pm, Pmax_post)
    if A_dec_avail < 0:
        A_dec_avail = 0.0

    # 5. Limiting clearing angle from the closed-form solution / 极限切除角（闭式解） ───────────────────────────────────────
    # cos(δc_cr) = [Pm·(δu−δ0) + Pmax_post·cos(δu) − Pmax_fault·cos(δ0)] / 极限切除角闭式公式分子与分母关系
    #              / (Pmax_post − Pmax_fault) / 分母为故障后与故障中最大功率之差
    denom = Pmax_post - Pmax_fault
    if abs(denom) < 1e-9:
        # If faulted and post-fault power curves are identical, there is no additional acceleration, so the limiting clearing angle equals the unstable equilibrium angle. / 故障中与故障后功率相同 → 无加速，极限切除角即为不稳定平衡角
        delta_cr = deltau
    else:
        cos_cr = (Pm * (deltau - delta0) + Pmax_post * math.cos(deltau)
                  - Pmax_fault * math.cos(delta0)) / denom
        cos_cr = max(-1.0, min(1.0, cos_cr))   # Numerical safeguard. / 数值保护
        delta_cr = math.acos(cos_cr)

    # 6. Limiting clearing time from numerical integration / 极限切除时间（数值积分） ─────────────────────────────────────
    t_cr = _swing_integrate_to_angle(delta0, delta_cr, Pm, Pmax_fault, Tj, f0)

    # 7. Stability judgement and actual maximum swing angle / 稳定判断与实际最大摆角 ─────────────────────────────────────
    stable = (A_dec_avail >= A_acc - 1e-9) and (deltac < deltau)

    deltamax_rad = deltamax_deg = A_dec_actual = None
    if stable and A_acc > 1e-9:
        # Use bisection on [deltac, deltau] to solve A_dec(deltamax) = A_acc. / 在 [deltac, deltau] 内用二分法求 A_dec(deltamax) = A_acc
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

    # 8. Margin / 裕度 ─────────────────────────────────────────────────────────────────
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


__all__ = [
    "impact_method",
    "critical_cut_angle_approx",
    "equal_area_criterion",
]
