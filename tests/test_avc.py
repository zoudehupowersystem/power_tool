from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from power_tool_avc import simulate_avc_strategy


def test_simulate_avc_strategy_returns_target_zone_when_voltage_is_normal() -> None:
    result = simulate_avc_strategy(
        hv_base=220.0,
        lv_base=110.0,
        vh=226.0,
        lv_min=108.0,
        lv_max=116.0,
        tap_min=-8,
        tap_max=8,
        tap_now=0,
        tap_step_pct=1.25,
        cap_num=2,
        cap_each=10.0,
        rea_num=1,
        rea_each=10.0,
        p_mw=160.0,
        q_mvar=5.0,
        sys_sc_mva=6000.0,
        tx_mva=180.0,
        tx_uk_pct=12.0,
    )
    assert result.v_zone == "正常电压区"
    assert result.zone_name == "Ⅴ区（目标区）"
    assert result.tap_target == result.tap_now


def test_simulate_avc_strategy_can_raise_voltage_with_tap_or_capacitor() -> None:
    result = simulate_avc_strategy(
        hv_base=220.0,
        lv_base=110.0,
        vh=214.0,
        lv_min=108.0,
        lv_max=116.0,
        tap_min=-8,
        tap_max=8,
        tap_now=0,
        tap_step_pct=1.25,
        cap_num=3,
        cap_each=10.0,
        rea_num=0,
        rea_each=0.0,
        p_mw=180.0,
        q_mvar=55.0,
        sys_sc_mva=3000.0,
        tx_mva=180.0,
        tx_uk_pct=12.0,
    )
    assert result.tap_target >= result.tap_now
    assert result.lv_after_kv >= result.lv_est_kv
    assert any("电容器" in step or "档位" in step for step in result.action_steps)
