from __future__ import annotations

import csv
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from power_tool_forecast import (
    ForecastConfig,
    classify_climate_block,
    forecast_day_ahead,
    list_builtin_datasets,
    list_forecast_algorithms,
    load_builtin_forecast_dataset,
    load_forecast_csv,
    solar_day_profile,
    solar_irradiance_on_panel,
    solar_position,
    solar_timezone_offset_hours,
    NANJING_LATITUDE,
    NANJING_LONGITUDE,
)


def test_builtin_load_forecast_returns_24_hours() -> None:
    rows = load_builtin_forecast_dataset("CAISO_LOAD_SAMPLE")
    result = forecast_day_ahead(
        rows,
        ForecastConfig(kind="load", target_date=date(2025, 6, 22), latitude=34.05, longitude=-118.25, altitude_m=90),
    )
    assert len(result.points) == 96
    assert result.points[0].timestamp.hour == 0
    assert result.points[-1].timestamp.hour == 23
    assert result.points[-1].timestamp.minute == 45
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
    assert len(result.points) == 96
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


def test_missing_weather_is_inferred_from_history_and_geography() -> None:
    rows = load_builtin_forecast_dataset("CAISO_LOAD_SAMPLE")
    stripped = [{"timestamp": row["timestamp"], "load_mw": row["load_mw"]} for row in rows]
    result = forecast_day_ahead(
        stripped,
        ForecastConfig(kind="load", target_date=date(2025, 6, 22), latitude=34.05, longitude=-118.25, altitude_m=90),
    )
    assert len(result.points) == 96
    assert all(p.temperature_c == p.temperature_c for p in result.points)
    assert any(p.ghi_wm2 > 0 for p in result.points)


def test_solar_post_processing_forces_night_to_zero() -> None:
    rows = load_builtin_forecast_dataset("CAISO_RENEWABLE_SAMPLE")
    solar_rows = [
        {"timestamp": row["timestamp"], "renewable_mw": row.get("solar_mw", 0.0), "solar_mw": row.get("solar_mw", 0.0)}
        for row in rows
    ]
    result = forecast_day_ahead(
        solar_rows,
        ForecastConfig(
            kind="renewable",
            target_date=date(2025, 6, 22),
            latitude=35.37,
            longitude=-119.02,
            altitude_m=120,
            renewable_capacity_mw=20000,
            renewable_resource="solar",
        ),
    )
    night_points = [p for p in result.points if p.timestamp.hour in {0, 1, 2, 3, 4, 21, 22, 23}]
    assert night_points
    assert all(p.value_mw == 0 and p.p10_mw == 0 and p.p90_mw == 0 for p in night_points)
    assert any(p.value_mw > 0 for p in result.points if 10 <= p.timestamp.hour <= 15)


def test_cn_and_custom_holiday_calendar(tmp_path: Path) -> None:
    rows = load_builtin_forecast_dataset("CAISO_LOAD_SAMPLE")
    cn_result = forecast_day_ahead(
        rows,
        ForecastConfig(kind="load", target_date=date(2025, 10, 1), latitude=31.23, longitude=121.47, holiday_country="CN"),
    )
    assert "节假日" in cn_result.points[0].drivers

    custom_path = tmp_path / "holidays.json"
    custom_path.write_text('{"FR": {"fixed_mmdd": ["07-14"], "nth_weekday": [], "dates": []}}', encoding="utf-8")
    custom_result = forecast_day_ahead(
        rows,
        ForecastConfig(kind="load", target_date=date(2025, 7, 14), holiday_country="FR", holiday_config_path=custom_path),
    )
    assert "节假日" in custom_result.points[0].drivers


def test_renewable_resource_selection_is_independent() -> None:
    rows = load_builtin_forecast_dataset("CAISO_RENEWABLE_SAMPLE")
    solar = forecast_day_ahead(
        rows,
        ForecastConfig(kind="renewable", target_date=date(2025, 6, 22), latitude=35.37, longitude=-119.02, renewable_resource="solar"),
    )
    wind = forecast_day_ahead(
        rows,
        ForecastConfig(kind="renewable", target_date=date(2025, 6, 22), latitude=35.37, longitude=-119.02, renewable_resource="wind"),
    )
    assert any("资源=光伏" in p.drivers for p in solar.points)
    assert any("资源=风电" in p.drivers for p in wind.points)
    assert [round(p.value_mw, 1) for p in solar.points] != [round(p.value_mw, 1) for p in wind.points]


def test_renewable_aggregate_mode_is_rejected() -> None:
    rows = load_builtin_forecast_dataset("CAISO_RENEWABLE_SAMPLE")
    try:
        forecast_day_ahead(
            rows,
            ForecastConfig(kind="renewable", target_date=date(2025, 6, 22), renewable_resource="aggregate"),
        )
    except ValueError as exc:
        assert "仅支持" in str(exc)
    else:
        raise AssertionError("aggregate renewable forecast should be rejected")


def test_chinese_and_baidu_kdd_schema_samples_parse() -> None:
    csg_rows = load_builtin_forecast_dataset("CSG_LOAD_FORECAST_SCHEMA_SAMPLE")
    cup_rows = load_builtin_forecast_dataset("ELECTRICIAN_CUP_LOAD_SCHEMA_SAMPLE")
    kdd_rows = load_builtin_forecast_dataset("BAIDU_KDD_SDWPF_WIND_SAMPLE")
    assert len(csg_rows) >= 48 and csg_rows[0]["load_mw"] > 0
    assert len(cup_rows) >= 48 and cup_rows[0]["load_mw"] > 0
    assert len(kdd_rows) >= 48 and kdd_rows[0]["wind_mw"] >= 0
    wind = forecast_day_ahead(
        kdd_rows,
        ForecastConfig(kind="renewable", target_date=date(2025, 1, 22), latitude=41.0, longitude=115.0, renewable_resource="wind"),
    )
    assert len(wind.points) == 96
    assert any("资源=风电" in p.drivers for p in wind.points)


def test_solar_helper_uses_standard_timezone_and_reports_noon() -> None:
    pos = solar_position(datetime(2025, 6, 22, 12, 0), 31.23, 121.47)
    profile = solar_day_profile(date(2025, 6, 22), 31.23, 121.47)
    assert solar_timezone_offset_hours(121.47) == 8
    assert pos.timezone_offset_hours == 8
    assert 170 <= pos.azimuth_deg <= 200
    assert pos.altitude_deg > 75
    assert profile.sunrise is not None and profile.sunset is not None
    assert profile.sunrise < profile.solar_noon < profile.sunset
    assert abs(profile.solar_noon.hour + profile.solar_noon.minute / 60.0 - 12.0) > 0.01


def test_solar_helper_reference_irradiance_is_zero_at_night() -> None:
    pos = solar_position(datetime(2025, 12, 22, 2, 0), 35.0, 110.0)
    assert pos.altitude_deg < 0
    assert pos.clear_sky_ghi_wm2 == 0
    assert pos.extraterrestrial_irradiance_wm2 == 0


def test_forecast_config_defaults_to_nanjing_china() -> None:
    from power_tool_forecast import load_forecast_builtin_config

    cfg = ForecastConfig(kind="renewable", target_date=date(2025, 6, 22))
    defaults = load_forecast_builtin_config()["defaults"]
    assert abs(cfg.latitude - NANJING_LATITUDE) < 1e-9
    assert abs(cfg.longitude - NANJING_LONGITUDE) < 1e-9
    assert cfg.holiday_country == "CN"
    assert cfg.interval_minutes == 15
    assert cfg.algorithm == "sklearn_auto"
    assert defaults["algorithm"] == "sklearn_auto"
    assert defaults["interval_minutes"] == 15
    assert "sklearn" in next(info.requires for info in list_forecast_algorithms("load") if info.code == "sklearn_auto")


def test_weather_and_panel_orientation_reduce_or_change_poa() -> None:
    ts = datetime(2025, 6, 22, 12, 0)
    clear = solar_irradiance_on_panel(ts, NANJING_LATITUDE, NANJING_LONGITUDE, 25.0, "clear", 0, 1.0, 30, 180)
    overcast = solar_irradiance_on_panel(ts, NANJING_LATITUDE, NANJING_LONGITUDE, 25.0, "overcast", 90, 1.0, 30, 180)
    west_facing = solar_irradiance_on_panel(ts, NANJING_LATITUDE, NANJING_LONGITUDE, 25.0, "clear", 0, 1.0, 30, 270)
    assert clear.corrected_ghi_wm2 > overcast.corrected_ghi_wm2
    assert clear.poa_wm2 > overcast.poa_wm2
    assert clear.poa_wm2 != west_facing.poa_wm2


def test_solar_forecast_is_linked_to_weather_and_panel_correction() -> None:
    rows = load_builtin_forecast_dataset("CAISO_RENEWABLE_SAMPLE")
    clear = forecast_day_ahead(
        rows,
        ForecastConfig(kind="renewable", target_date=date(2025, 6, 22), renewable_resource="solar", weather_condition="clear", cloud_cover_pct=0, pv_tilt_deg=30, pv_azimuth_deg=180),
    )
    cloudy = forecast_day_ahead(
        rows,
        ForecastConfig(kind="renewable", target_date=date(2025, 6, 22), renewable_resource="solar", weather_condition="overcast", cloud_cover_pct=90, pv_tilt_deg=30, pv_azimuth_deg=180),
    )
    assert max(p.poa_wm2 for p in clear.points) > max(p.poa_wm2 for p in cloudy.points)
    assert sum(p.value_mw for p in clear.points) > sum(p.value_mw for p in cloudy.points)
    assert any("POA=" in p.drivers and "光伏修正=" in p.drivers for p in clear.points)


def test_annual_load_forecast_planning_sample() -> None:
    from power_tool_forecast import (
        AnnualLoadForecastConfig,
        forecast_annual_load,
        annual_seasonal_shapes_for_year,
        format_annual_load_forecast_summary,
        load_annual_load_sample,
    )

    dataset = load_annual_load_sample()
    result = forecast_annual_load(dataset, AnnualLoadForecastConfig(horizon_years=12, algorithm="综合法"))
    assert len(result.years) == 12
    assert result.years[0].year == 2026
    assert result.years[-1].energy_gwh > result.years[0].energy_gwh
    assert result.years[-1].max_load_mw > result.years[0].max_load_mw
    assert result.base_max_load_mw > 0
    assert len(result.seasonal_shapes) == 4
    assert all(len(shape.values_mw) == 24 for shape in result.seasonal_shapes)
    base_shapes = annual_seasonal_shapes_for_year(result, result.base_year)
    final_shapes = annual_seasonal_shapes_for_year(result, result.years[-1].year)
    assert len(base_shapes) == len(final_shapes) == 4
    assert max(base_shapes[0].values_mw) < max(final_shapes[0].values_mw)
    assert "不包含空间负荷预测" in format_annual_load_forecast_summary(result)


def test_forecast_interval_accepts_one_to_thirty_minutes_and_smooths() -> None:
    rows = load_builtin_forecast_dataset("CAISO_LOAD_SAMPLE")
    one_min = forecast_day_ahead(
        rows,
        ForecastConfig(kind="load", target_date=date(2025, 6, 22), latitude=34.05, longitude=-118.25, interval_minutes=1),
    )
    thirty_min = forecast_day_ahead(
        rows,
        ForecastConfig(kind="load", target_date=date(2025, 6, 22), latitude=34.05, longitude=-118.25, interval_minutes=30),
    )
    assert len(one_min.points) == 24 * 60
    assert len(thirty_min.points) == 48
    assert "线性插值" in "\n".join(one_min.notes)
    assert max(p.value_mw for p in one_min.points) > min(p.value_mw for p in one_min.points)


def test_forecast_interval_rejects_out_of_range() -> None:
    rows = load_builtin_forecast_dataset("CAISO_LOAD_SAMPLE")
    try:
        forecast_day_ahead(rows, ForecastConfig(kind="load", target_date=date(2025, 6, 22), interval_minutes=31))
    except ValueError as exc:
        assert "1 到 30" in str(exc)
    else:
        raise AssertionError("interval above 30 minutes should be rejected")


def test_annual_load_forecast_exports_json_and_csv(tmp_path: Path) -> None:
    from power_tool_forecast import (
        AnnualLoadForecastConfig,
        annual_load_forecast_to_dict,
        export_annual_load_forecast_csv,
        export_annual_load_forecast_json,
        forecast_annual_load,
        load_annual_load_sample,
    )

    result = forecast_annual_load(load_annual_load_sample(), AnnualLoadForecastConfig(horizon_years=5))
    data = annual_load_forecast_to_dict(result)
    assert len(data["years"]) == 5
    assert len(data["seasonal_shapes_by_year"]) == 6

    json_path = export_annual_load_forecast_json(result, tmp_path / "annual.json")
    csv_path = export_annual_load_forecast_csv(result, tmp_path / "annual.csv")
    assert '"seasonal_shapes_by_year"' in json_path.read_text(encoding="utf-8")
    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "annual_years" in csv_text
    assert "seasonal_shapes_by_year" in csv_text
    assert "春季" in csv_text
