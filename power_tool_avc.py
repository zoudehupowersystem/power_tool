from __future__ import annotations

from dataclasses import dataclass

from power_tool_common import InputError, _validate_positive


@dataclass(frozen=True)
class AVCStrategyResult:
    zone_name: str
    v_zone: str
    q_zone: str
    q_abs_ref: float
    lv_est_kv: float
    lv_after_kv: float
    tap_now: int
    tap_target: int
    q_now_mvar: float
    q_after_mvar: float
    q_comp_mvar: float
    action_steps: list[str]
    x_sys_pu: float
    x_tx_pu: float
    x_total_pu: float
    i_now_pu: float
    i_after_pu: float
    p_src_now_mw: float
    p_src_after_mw: float
    q_src_now_mvar: float
    q_src_after_mvar: float
    q_drop_now_mvar: float
    q_drop_after_mvar: float


def simulate_avc_strategy(
    *,
    hv_base: float,
    lv_base: float,
    vh: float,
    lv_min: float,
    lv_max: float,
    tap_min: int,
    tap_max: int,
    tap_now: int,
    tap_step_pct: float,
    cap_num: int,
    cap_each: float,
    rea_num: int,
    rea_each: float,
    p_mw: float,
    q_mvar: float,
    sys_sc_mva: float,
    tx_mva: float,
    tx_uk_pct: float,
) -> AVCStrategyResult:
    if tap_min > tap_max:
        raise InputError("最小档位不能大于最大档位。")
    tap_now = min(max(int(tap_now), int(tap_min)), int(tap_max))
    _validate_positive("高压侧额定电压", hv_base)
    _validate_positive("低压侧额定电压", lv_base)
    _validate_positive("单档调节率", tap_step_pct)
    _validate_positive("高压侧系统容量", sys_sc_mva)
    _validate_positive("变压器容量", tx_mva)
    _validate_positive("变压器短路电压", tx_uk_pct)

    x_sys_pu = tx_mva / sys_sc_mva
    x_tx_pu = tx_uk_pct / 100.0
    x_total_pu = x_sys_pu + x_tx_pu

    def _solve_avc_power_flow(vh_kv: float, tap: int, p_load_mw: float, q_load_mvar: float) -> tuple[float, float, float, float, float]:
        tap_factor = 1.0 + tap * tap_step_pct / 100.0
        v_source_pu = (vh_kv / hv_base) * tap_factor
        s_load_pu = complex(p_load_mw, q_load_mvar) / tx_mva
        v_lv = complex(max(v_source_pu, 1e-4), 0.0)
        for _ in range(30):
            if abs(v_lv) < 1e-8:
                v_lv = complex(1e-4, 0.0)
            i_line = (s_load_pu / v_lv).conjugate()
            v_next = complex(v_source_pu, 0.0) - 1j * x_total_pu * i_line
            if abs(v_next - v_lv) < 1e-8:
                v_lv = v_next
                break
            v_lv = v_next
        i_line = (s_load_pu / v_lv).conjugate()
        s_source_pu = complex(v_source_pu, 0.0) * i_line.conjugate()
        i_pu = abs(i_line)
        v_lv_kv = abs(v_lv) * lv_base
        p_source_mw = s_source_pu.real * tx_mva
        q_source_mvar = s_source_pu.imag * tx_mva
        q_drop_mvar = x_total_pu * (i_pu ** 2) * tx_mva
        return v_lv_kv, p_source_mw, q_source_mvar, q_drop_mvar, i_pu

    lv_est, p_src_now, q_src_now, q_drop_now, i_now = _solve_avc_power_flow(vh, tap_now, p_mw, q_mvar)
    q_cap_total = max(0, cap_num) * max(0.0, cap_each)
    q_rea_total = max(0, rea_num) * max(0.0, rea_each)
    q_after = q_mvar
    tap_target = tap_now
    action_steps: list[str] = []

    def _score_voltage(lv_kv: float, q_trial: float) -> float:
        under = max(0.0, lv_min - lv_kv)
        over = max(0.0, lv_kv - lv_max)
        band_penalty = 8.0 * (under + over)
        return abs(lv_kv - 0.5 * (lv_min + lv_max)) + band_penalty + 0.03 * abs(q_trial)

    def _pick_compensation(initial_q: float, tap_eval: int, is_capacitor: bool) -> tuple[float, int, float]:
        steps = max(0, cap_num if is_capacitor else rea_num)
        step_mvar = max(0.0, cap_each if is_capacitor else rea_each)
        direction = -1.0 if is_capacitor else 1.0
        best_q = initial_q
        best_steps = 0
        best_lv, *_ = _solve_avc_power_flow(vh, tap_eval, p_mw, best_q)
        best_score = _score_voltage(best_lv, best_q)
        for n in range(1, steps + 1):
            q_trial = initial_q + direction * n * step_mvar
            lv_trial, *_ = _solve_avc_power_flow(vh, tap_eval, p_mw, q_trial)
            score = _score_voltage(lv_trial, q_trial)
            if score < best_score - 1e-9:
                best_score = score
                best_q = q_trial
                best_steps = n
                best_lv = lv_trial
        return best_q, best_steps, best_lv

    if lv_est < lv_min:
        v_zone = "低压区"
    elif lv_est > lv_max:
        v_zone = "高压区"
    else:
        v_zone = "正常电压区"

    q_abs_ref = max(10.0, 0.2 * max(abs(p_mw), 1.0))
    if q_mvar > q_abs_ref:
        q_zone = "感性无功偏大"
    elif q_mvar < -q_abs_ref:
        q_zone = "容性无功偏大"
    else:
        q_zone = "无功正常区"

    if v_zone == "低压区":
        if tap_target < tap_max:
            tap_target += 1
            action_steps.append("升高变压器档位 +1")
        if q_cap_total > 0:
            q_prev = q_after
            q_after, cap_steps, lv_trial = _pick_compensation(q_after, tap_target, is_capacitor=True)
            if cap_steps > 0:
                dq = q_prev - q_after
                action_steps.append(f"投入电容器 {cap_steps} 组（{dq:.2f} Mvar），估算低压侧电压可到 {lv_trial:.3f} kV")
    elif v_zone == "高压区":
        if tap_target > tap_min:
            tap_target -= 1
            action_steps.append("降低变压器档位 -1")
        if q_rea_total > 0:
            q_prev = q_after
            q_after, rea_steps, lv_trial = _pick_compensation(q_after, tap_target, is_capacitor=False)
            if rea_steps > 0:
                dq = q_after - q_prev
                action_steps.append(f"投入电抗器 {rea_steps} 组（{dq:.2f} Mvar），估算低压侧电压可到 {lv_trial:.3f} kV")
    else:
        if q_zone == "感性无功偏大" and q_cap_total > 0:
            q_prev = q_after
            q_after, cap_steps, lv_trial = _pick_compensation(q_after, tap_target, is_capacitor=True)
            if cap_steps > 0:
                dq = q_prev - q_after
                action_steps.append(f"正常电压下投电容器 {cap_steps} 组（补偿 {dq:.2f} Mvar，V≈{lv_trial:.3f} kV）")
        elif q_zone == "容性无功偏大" and q_rea_total > 0:
            q_prev = q_after
            q_after, rea_steps, lv_trial = _pick_compensation(q_after, tap_target, is_capacitor=False)
            if rea_steps > 0:
                dq = q_after - q_prev
                action_steps.append(f"正常电压下投电抗器 {rea_steps} 组（吸收 {dq:.2f} Mvar，V≈{lv_trial:.3f} kV）")
        else:
            action_steps.append("保持当前档位与无功补偿状态")

    q_comp = q_mvar - q_after
    lv_after, p_src_after, q_src_after, q_drop_after, i_after = _solve_avc_power_flow(vh, tap_target, p_mw, q_after)

    zone_map = {
        ("低压区", "感性无功偏大"): "Ⅰ区（低压+感性）",
        ("低压区", "无功正常区"): "Ⅱ区（低压+无功正常）",
        ("低压区", "容性无功偏大"): "Ⅲ区（低压+容性）",
        ("正常电压区", "感性无功偏大"): "Ⅳ区（电压正常+感性）",
        ("正常电压区", "无功正常区"): "Ⅴ区（目标区）",
        ("正常电压区", "容性无功偏大"): "Ⅵ区（电压正常+容性）",
        ("高压区", "感性无功偏大"): "Ⅶ区（高压+感性）",
        ("高压区", "无功正常区"): "Ⅷ区（高压+无功正常）",
        ("高压区", "容性无功偏大"): "Ⅸ区（高压+容性）",
    }
    return AVCStrategyResult(
        zone_name=zone_map[(v_zone, q_zone)],
        v_zone=v_zone,
        q_zone=q_zone,
        q_abs_ref=q_abs_ref,
        lv_est_kv=lv_est,
        lv_after_kv=lv_after,
        tap_now=tap_now,
        tap_target=tap_target,
        q_now_mvar=q_mvar,
        q_after_mvar=q_after,
        q_comp_mvar=q_comp,
        action_steps=action_steps,
        x_sys_pu=x_sys_pu,
        x_tx_pu=x_tx_pu,
        x_total_pu=x_total_pu,
        i_now_pu=i_now,
        i_after_pu=i_after,
        p_src_now_mw=p_src_now,
        p_src_after_mw=p_src_after,
        q_src_now_mvar=q_src_now,
        q_src_after_mvar=q_src_after,
        q_drop_now_mvar=q_drop_now,
        q_drop_after_mvar=q_drop_after,
    )
