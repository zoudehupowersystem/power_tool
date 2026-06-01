from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from power_tool_forecast import (
    ForecastConfig,
    classify_climate_block,
    forecast_day_ahead,
    list_builtin_datasets,
    load_builtin_forecast_dataset,
    load_forecast_csv,
)


def test_builtin_load_forecast_returns_24_hours() -> None:
    rows = load_builtin_forecast_dataset("CAISO_LOAD_SAMPLE")
    result = forecast_day_ahead(
        rows,
        ForecastConfig(kind="load", target_date=date(2025, 6, 22), latitude=34.05, longitude=-118.25, altitude_m=90),
    )
    assert len(result.points) == 24
    assert result.points[0].timestamp.hour == 0
    assert result.points[-1].timestamp.hour == 23
    assert max(p.value_mw for p in result.points) > min(p.value_mw for p in result.points)
    assert "地中海" in result.climate_block


def test_builtin_renewable_forecast_is_capacity_limited() -> None:
    rows = load_builtin_forecast_dataset("CAISO_RENEWABLE_SAMPLE")
    result = forecast_day_ahead(
        rows,
        ForecastConfig(
            kind="renewable",
            target_date=date(2025, 6, 22),
            latitude=35.37,
            longitude=-119.02,
            altitude_m=120,
            renewable_capacity_mw=5000,
        ),
    )
    assert len(result.points) == 24
    assert all(0 <= p.value_mw <= 5000 for p in result.points)
    assert any(p.ghi_wm2 > 0 for p in result.points)


def test_iso_alias_csv_loader(tmp_path: Path) -> None:
    path = tmp_path / "ercot_alias.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Interval Start", "Demand MW", "Temperature"])
        for hour in range(72):
            writer.writerow([f"2025-01-{1 + hour // 24:02d} {hour % 24:02d}:00", 1000 + hour, 20])
    rows = load_forecast_csv(path, "load")
    assert len(rows) == 72
    assert rows[0]["load_mw"] == 1000


def test_caiso_opr_dt_and_hour_loader(tmp_path: Path) -> None:
    path = tmp_path / "caiso_oasis_alias.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["OPR_DT", "OPR_HR", "SYS_FCST_ACT_MW", "temp_c"])
        for hour in range(72):
            day = 1 + hour // 24
            hour_ending = hour % 24 + 1
            writer.writerow([f"2025-01-{day:02d}", hour_ending, 22000 + hour, 18])
    rows = load_forecast_csv(path, "load")
    assert len(rows) == 72
    assert rows[0]["timestamp"].hour == 0
    assert rows[23]["timestamp"].hour == 23
    assert rows[0]["load_mw"] == 22000


def test_dataset_registry_and_climate_classification() -> None:
    load_names = {info.name for info in list_builtin_datasets("load")}
    renewable_names = {info.name for info in list_builtin_datasets("renewable")}
    assert {"CAISO_LOAD_SAMPLE", "ERCOT_LOAD_SAMPLE", "GEFCOM_LOAD_SAMPLE"} <= load_names
    assert {"CAISO_RENEWABLE_SAMPLE", "NREL_SOLAR_WIND_SAMPLE"} <= renewable_names
    assert classify_climate_block(39.7, -105.2, 1600) == "高海拔/山地气候"
