from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from power_tool_sag import analyze_conductor_sag, estimate_conductor_temperature


BASE_ARGS = {
    "span_m": 400.0,
    "left_support_height_m": 35.0,
    "right_support_height_m": 38.0,
    "line_mass_kg_per_m": 1.35,
    "cross_section_mm2": 400.0,
    "elastic_modulus_gpa": 63.0,
    "thermal_expansion_per_c": 19e-6,
    "reference_temperature_c": 15.0,
    "reference_horizontal_tension_kN": 25.0,
    "ambient_temp_c": 25.0,
    "resistance_20c_ohm_per_km": 0.072,
    "resistance_temp_coeff_per_c": 0.00403,
    "cooling_coeff_w_per_mk": 0.85,
    "solar_gain_w_per_m": 8.0,
}


def test_temperature_increase_raises_sag_and_reduces_horizontal_tension() -> None:
    cool = analyze_conductor_sag(
        driver_mode="temperature",
        conductor_temperature_c=20.0,
        current_a=400.0,
        **BASE_ARGS,
    )
    hot = analyze_conductor_sag(
        driver_mode="temperature",
        conductor_temperature_c=80.0,
        current_a=400.0,
        **BASE_ARGS,
    )

    assert hot.operating_state.maximum_sag_m > cool.operating_state.maximum_sag_m
    assert hot.operating_state.midspan_sag_m > cool.operating_state.midspan_sag_m
    assert hot.operating_state.horizontal_tension_n < cool.operating_state.horizontal_tension_n



def test_reference_temperature_recovers_reference_horizontal_tension() -> None:
    result = analyze_conductor_sag(
        driver_mode="temperature",
        conductor_temperature_c=BASE_ARGS["reference_temperature_c"],
        current_a=300.0,
        **BASE_ARGS,
    )

    href_n = BASE_ARGS["reference_horizontal_tension_kN"] * 1000.0
    assert abs(result.operating_state.horizontal_tension_n - href_n) < 1e-6
    assert abs(result.reference_state.maximum_sag_m - result.operating_state.maximum_sag_m) < 1e-9



def test_current_mode_returns_thermal_balance_and_hotter_conductor() -> None:
    low = estimate_conductor_temperature(
        current_a=200.0,
        ambient_temp_c=25.0,
        resistance_20c_ohm_per_km=0.072,
        resistance_temp_coeff_per_c=0.00403,
        cooling_coeff_w_per_mk=0.85,
        solar_gain_w_per_m=8.0,
    )
    high = estimate_conductor_temperature(
        current_a=700.0,
        ambient_temp_c=25.0,
        resistance_20c_ohm_per_km=0.072,
        resistance_temp_coeff_per_c=0.00403,
        cooling_coeff_w_per_mk=0.85,
        solar_gain_w_per_m=8.0,
    )

    assert high.conductor_temp_c > low.conductor_temp_c > 25.0

    result = analyze_conductor_sag(
        driver_mode="current",
        conductor_temperature_c=60.0,
        current_a=700.0,
        **BASE_ARGS,
    )
    assert result.thermal_balance is not None
    assert result.conductor_temperature_c == result.thermal_balance.conductor_temp_c
    assert result.conductor_temperature_c > BASE_ARGS["ambient_temp_c"]



def test_unequal_support_heights_shift_lowest_point_and_keep_positive_clearance() -> None:
    result = analyze_conductor_sag(
        driver_mode="temperature",
        conductor_temperature_c=60.0,
        current_a=500.0,
        **BASE_ARGS,
    )

    state = result.operating_state
    assert abs(state.lowest_point_x_m - BASE_ARGS["span_m"] / 2.0) > 0.05
    assert 0.0 <= state.minimum_clearance_x_m <= BASE_ARGS["span_m"]
    assert state.minimum_clearance_m > 0.0
    assert state.left_support_tension_n != state.right_support_tension_n
