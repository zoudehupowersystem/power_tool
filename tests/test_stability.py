from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import pytest

from power_tool_stability import critical_cut_angle_approx, equal_area_criterion, impact_method


def test_impact_method_default_case_regression() -> None:
    result = impact_method(0.9, 0.12, 1.106, 0.9)
    assert result.Dp_pu == pytest.approx(0.7505139185719872, rel=1e-12)
    assert result.osc_amp_pu == pytest.approx(0.7505139185719872, rel=1e-12)
    assert result.margin_pu == pytest.approx(-0.14948608142801283, rel=1e-12)
    assert result.status == "振荡幅值可接受"


def test_critical_cut_angle_default_case_regression() -> None:
    result = critical_cut_angle_approx(0.9, 1.65, 9.0, 50.0, 0.12)
    assert result.delta0_deg == pytest.approx(33.05573115085401, rel=1e-12)
    assert result.delta_cr_deg == pytest.approx(75.7545727534849, rel=1e-12)
    assert result.t_cr_s == pytest.approx(0.21781450212567696, rel=1e-12)
    assert result.margin_pct == pytest.approx(44.90724959591483, rel=1e-12)


def test_equal_area_default_case_regression() -> None:
    result = equal_area_criterion(0.9, 1.65, 0.3, 1.65, 0.12, 9.0, 50.0)
    assert result.stable is True
    assert result.margin_pct == pytest.approx(629.6353870362495, rel=1e-12)
    assert result.delta_cr_deg == pytest.approx(83.42486401082289, rel=1e-12)
    assert result.t_cr_s == pytest.approx(0.26759999999998685, rel=1e-10)
    assert result.deltamax_deg == pytest.approx(61.93952481688824, rel=1e-12)
