"""Day-ahead load and renewable forecasting helpers for dispatch-oriented studies."""

from __future__ import annotations

import csv
import importlib
import importlib.util
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np


DATA_DIR = Path(__file__).resolve().parent / "data" / "forecast_samples"


@dataclass(frozen=True)
class ForecastDatasetInfo:
    name: str
    kind: str
    path: Path
    source: str
    region: str
    latitude: float
    longitude: float
    altitude_m: float
    notes: str


@dataclass(frozen=True)
class ForecastConfig:
    kind: str
    target_date: date
    latitude: float = 34.05
    longitude: float = -118.25
    altitude_m: float = 80.0
    climate_hint: str = "auto"
    holiday_country: str = "US"
    renewable_capacity_mw: float | None = None


@dataclass(frozen=True)
class ForecastPoint:
    timestamp: datetime
    value_mw: float
    p10_mw: float
    p90_mw: float
    temperature_c: float
    ghi_wm2: float
    wind_speed_mps: float
    drivers: str


@dataclass(frozen=True)
class ForecastResult:
    kind: str
    climate_block: str
    model_name: str
    metric_mae_mw: float
    points: tuple[ForecastPoint, ...]
    notes: tuple[str, ...]


_DATASET_SPECS: tuple[dict[str, object], ...] = (
    {
        "name": "CAISO_LOAD_SAMPLE",
        "kind": "load",
        "file": "caiso_load_sample.csv",
        "source": "CAISO OASIS / Today's Outlook schema sample",
        "region": "California ISO",
        "latitude": 34.05,
        "longitude": -118.25,
        "altitude_m": 90.0,
        "notes": "Hourly training sample shaped like CAISO demand exports; replace with OASIS SLD_FCST/SYS_FCST_ACT_MW for production studies.",
    },
    {
        "name": "ERCOT_LOAD_SAMPLE",
        "kind": "load",
        "file": "ercot_load_sample.csv",
        "source": "ERCOT hourly load archive schema sample",
        "region": "ERCOT Texas",
        "latitude": 30.27,
        "longitude": -97.74,
        "altitude_m": 150.0,
        "notes": "Hourly training sample using ERCOT-style total load and weather-zone concepts.",
    },
    {
        "name": "GEFCOM_LOAD_SAMPLE",
        "kind": "load",
        "file": "gefcom_load_sample.csv",
        "source": "GEFCom load competition schema sample",
        "region": "GEFCom synthetic utility",
        "latitude": 40.71,
        "longitude": -74.00,
        "altitude_m": 10.0,
        "notes": "Compact built-in sample with GEFCom-like load/temperature columns for algorithm smoke tests.",
    },
    {
        "name": "CAISO_RENEWABLE_SAMPLE",
        "kind": "renewable",
        "file": "caiso_renewable_sample.csv",
        "source": "CAISO wind/solar forecast and supply-trend schema sample",
        "region": "California ISO renewables",
        "latitude": 35.37,
        "longitude": -119.02,
        "altitude_m": 120.0,
        "notes": "Contains hourly solar, wind and aggregate renewable MW fields for day-ahead renewable studies.",
    },
    {
        "name": "NREL_SOLAR_WIND_SAMPLE",
        "kind": "renewable",
        "file": "nrel_renewable_sample.csv",
        "source": "NREL NSRDB / wind-toolkit style resource sample",
        "region": "Southwest renewable plant",
        "latitude": 39.74,
        "longitude": -105.18,
        "altitude_m": 1600.0,
        "notes": "Weather-resource sample with GHI and wind speed, suitable for PV/wind conversion testing.",
    },
)


CLIMATE_BLOCKS: tuple[tuple[str, float, float, float, float, str], ...] = (
    ("polar", 60, 90, -180, 180, "高纬寒冷/极地"),
    ("boreal_continental", 45, 60, -170, 180, "寒温带大陆"),
    ("marine_west_coast", 35, 60, -130, -115, "美国西海岸/海洋性"),
    ("mediterranean", 30, 45, -125, -115, "地中海型夏干"),
    ("humid_subtropical", 20, 38, -105, -70, "湿润亚热带"),
    ("arid_desert", 15, 38, -125, -95, "干旱荒漠/高日照"),
    ("tropical", -23.5, 23.5, -180, 180, "热带"),
    ("southern_temperate", -45, -23.5, -180, 180, "南半球温带"),
    ("southern_cool", -70, -45, -180, 180, "南半球寒温带"),
)


_COLUMN_ALIASES = {
    "timestamp": {"timestamp", "time", "datetime", "date_time", "interval_start", "interval_start_time", "opr_dt", "date"},
    "hour": {"hour", "he", "hour_ending", "opr_hr", "opr_hour"},
    "load_mw": {"load_mw", "demand_mw", "mw", "sys_fct_act_mw", "sys_fcst_act_mw", "total_load", "ercot", "load"},
    "renewable_mw": {"renewable_mw", "renewables_mw", "total_renewable_mw", "renewable", "ren_mw"},
    "solar_mw": {"solar_mw", "solar", "pv_mw", "solar_power_mw"},
    "wind_mw": {"wind_mw", "wind", "wind_power_mw"},
    "temperature_c": {"temperature_c", "temp_c", "temperature", "dry_bulb_c", "t"},
    "ghi_wm2": {"ghi_wm2", "ghi", "global_horizontal_irradiance", "solar_irradiance"},
    "wind_speed_mps": {"wind_speed_mps", "wind_speed", "ws_mps", "windspeed"},
}


_US_FIXED_HOLIDAYS = {(1, 1), (7, 4), (11, 11), (12, 25)}


def list_builtin_datasets(kind: str | None = None) -> list[ForecastDatasetInfo]:
    infos = []
    for spec in _DATASET_SPECS:
        if kind is not None and spec["kind"] != kind:
            continue
        infos.append(
            ForecastDatasetInfo(
                name=str(spec["name"]),
                kind=str(spec["kind"]),
                path=DATA_DIR / str(spec["file"]),
                source=str(spec["source"]),
                region=str(spec["region"]),
                latitude=float(spec["latitude"]),
                longitude=float(spec["longitude"]),
                altitude_m=float(spec["altitude_m"]),
                notes=str(spec["notes"]),
            )
        )
    return infos


def builtin_dataset_info(name: str) -> ForecastDatasetInfo:
    for info in list_builtin_datasets():
        if info.name == name:
            return info
    raise ValueError(f"未知内置数据集：{name}")


def _canonical_header(header: str) -> str | None:
    key = header.strip().lower().replace(" ", "_").replace("-", "_")
    for canonical, aliases in _COLUMN_ALIASES.items():
        if key in aliases:
            return canonical
    return None


def _parse_timestamp(text: str) -> datetime:
    raw = text.strip().replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d"):
        try:
            if fmt is None:
                return datetime.fromisoformat(raw).replace(tzinfo=None)
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    raise ValueError(f"无法解析时间戳：{text}")


def _safe_float_value(value: str | None, default: float = float("nan")) -> float:
    if value is None or str(value).strip() == "":
        return default
    return float(str(value).replace(",", ""))


def load_forecast_csv(path: str | Path, kind: str = "load") -> list[dict[str, float | datetime]]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV 缺少表头。")
        mapping = {name: _canonical_header(name) for name in reader.fieldnames}
        if "timestamp" not in mapping.values():
            raise ValueError("CSV 需要 timestamp/time/datetime/date_time 等时间列。")
        rows: list[dict[str, float | datetime]] = []
        for raw in reader:
            item: dict[str, float | datetime] = {}
            for original, canonical in mapping.items():
                if canonical is None:
                    continue
                if canonical == "timestamp":
                    item[canonical] = _parse_timestamp(raw.get(original, ""))
                else:
                    item[canonical] = _safe_float_value(raw.get(original))
            if "timestamp" in item and "hour" in item and isinstance(item["timestamp"], datetime):
                hour = int(item.pop("hour"))
                hour = hour - 1 if 1 <= hour <= 24 else hour
                item["timestamp"] = item["timestamp"].replace(hour=max(0, min(23, hour)), minute=0, second=0, microsecond=0)
            if kind == "renewable" and "renewable_mw" not in item:
                solar = float(item.get("solar_mw", 0.0) or 0.0)
                wind = float(item.get("wind_mw", 0.0) or 0.0)
                item["renewable_mw"] = solar + wind
            rows.append(item)
    rows.sort(key=lambda r: r["timestamp"])  # type: ignore[index]
    if len(rows) < 48:
        raise ValueError("至少需要 48 个小时点用于日前预测。")
    return rows


def load_builtin_forecast_dataset(name: str) -> list[dict[str, float | datetime]]:
    info = builtin_dataset_info(name)
    return load_forecast_csv(info.path, info.kind)


def classify_climate_block(latitude: float, longitude: float, altitude_m: float = 0.0, hint: str = "auto") -> str:
    if hint and hint.lower() not in {"auto", "自动"}:
        return hint
    if altitude_m >= 1200:
        return "高海拔/山地气候"
    lat = float(latitude)
    lon = float(longitude)
    for code, lat_min, lat_max, lon_min, lon_max, label in CLIMATE_BLOCKS:
        if lat_min <= lat < lat_max and lon_min <= lon <= lon_max:
            return label
    abs_lat = abs(lat)
    if abs_lat < 23.5:
        return "热带"
    if abs_lat < 35:
        return "副热带/暖温带"
    if abs_lat < 55:
        return "温带"
    return "高纬寒冷"


def _is_holiday(d: date, country: str) -> bool:
    if country.upper() == "US" and (d.month, d.day) in _US_FIXED_HOLIDAYS:
        return True
    # Thanksgiving: fourth Thursday of November; Labor Day: first Monday of September.
    if country.upper() == "US" and d.month == 11 and d.weekday() == 3 and 22 <= d.day <= 28:
        return True
    if country.upper() == "US" and d.month == 9 and d.weekday() == 0 and 1 <= d.day <= 7:
        return True
    return False


def _season_value(d: date, latitude: float) -> float:
    day = d.timetuple().tm_yday
    shift = 172 if latitude >= 0 else 355
    return math.cos(2.0 * math.pi * (day - shift) / 365.25)


def _solar_shape(ts: datetime, latitude: float) -> float:
    daylight = max(8.0, 12.0 + 4.0 * math.cos(2.0 * math.pi * (ts.timetuple().tm_yday - (172 if latitude >= 0 else 355)) / 365.25))
    sunrise = 12.0 - daylight / 2.0
    phase = (ts.hour + 0.5 - sunrise) / daylight
    if phase <= 0.0 or phase >= 1.0:
        return 0.0
    return math.sin(math.pi * phase) ** 1.35


def _climatology(rows: list[dict[str, float | datetime]], key: str, ts: datetime, fallback: float) -> float:
    same_hour = [float(r[key]) for r in rows if key in r and not math.isnan(float(r[key])) and isinstance(r["timestamp"], datetime) and r["timestamp"].hour == ts.hour]
    if same_hour:
        return float(np.median(same_hour))
    values = [float(r[key]) for r in rows if key in r and not math.isnan(float(r[key]))]
    return float(np.median(values)) if values else fallback


def _feature_vector(ts: datetime, config: ForecastConfig, temp_c: float, ghi_wm2: float, wind_mps: float) -> list[float]:
    dow = ts.weekday()
    hour_angle = 2.0 * math.pi * ts.hour / 24.0
    dow_angle = 2.0 * math.pi * dow / 7.0
    season = _season_value(ts.date(), config.latitude)
    weekend = 1.0 if dow >= 5 else 0.0
    holiday = 1.0 if _is_holiday(ts.date(), config.holiday_country) else 0.0
    return [
        1.0,
        math.sin(hour_angle), math.cos(hour_angle),
        math.sin(dow_angle), math.cos(dow_angle), weekend, holiday,
        season, season * season,
        float(config.latitude) / 90.0, float(config.longitude) / 180.0, min(max(config.altitude_m, 0.0), 5000.0) / 5000.0,
        temp_c, temp_c * temp_c / 40.0,
        ghi_wm2 / 1000.0, wind_mps / 20.0,
    ]


def _target_value(row: dict[str, float | datetime], kind: str) -> float:
    if kind == "renewable":
        return float(row.get("renewable_mw", 0.0) or 0.0)
    return float(row.get("load_mw", 0.0) or 0.0)


def _sklearn_predict(x_train: np.ndarray, y_train: np.ndarray, x_future: np.ndarray) -> tuple[str, np.ndarray] | None:
    if importlib.util.find_spec("sklearn") is None:
        return None
    linear_model = importlib.import_module("sklearn.linear_model")
    model = linear_model.HuberRegressor(epsilon=1.35, alpha=0.0001, max_iter=500)
    model.fit(x_train, y_train)
    return "Scikit-learn HuberRegressor", np.asarray(model.predict(x_future), dtype=float)


def _ridge_predict(x_train: np.ndarray, y_train: np.ndarray, x_future: np.ndarray) -> tuple[str, np.ndarray]:
    scale = np.std(x_train, axis=0)
    scale[scale < 1e-9] = 1.0
    x_scaled = x_train / scale
    xf_scaled = x_future / scale
    lam = 0.25
    beta = np.linalg.pinv(x_scaled.T @ x_scaled + lam * np.eye(x_scaled.shape[1])) @ x_scaled.T @ y_train
    return "内置岭回归（未安装 scikit-learn 时使用）", xf_scaled @ beta


def forecast_day_ahead(rows: Iterable[dict[str, float | datetime]], config: ForecastConfig) -> ForecastResult:
    history = sorted(list(rows), key=lambda r: r["timestamp"])  # type: ignore[index]
    if len(history) < 48:
        raise ValueError("至少需要 48 个小时历史数据。")
    climate = classify_climate_block(config.latitude, config.longitude, config.altitude_m, config.climate_hint)
    train_features: list[list[float]] = []
    targets: list[float] = []
    for row in history:
        ts = row["timestamp"]
        if not isinstance(ts, datetime):
            continue
        temp = float(row.get("temperature_c", _climatology(history, "temperature_c", ts, 20.0)) or 20.0)
        ghi = float(row.get("ghi_wm2", 900.0 * _solar_shape(ts, config.latitude)) or 0.0)
        wind = float(row.get("wind_speed_mps", _climatology(history, "wind_speed_mps", ts, 5.5)) or 5.5)
        train_features.append(_feature_vector(ts, config, temp, ghi, wind))
        targets.append(_target_value(row, config.kind))
    x_train = np.asarray(train_features, dtype=float)
    y_train = np.asarray(targets, dtype=float)
    future_times = [datetime.combine(config.target_date, datetime.min.time()) + timedelta(hours=h) for h in range(24)]
    future_weather: list[tuple[float, float, float]] = []
    for ts in future_times:
        temp = _climatology(history, "temperature_c", ts, 18.0) + 3.5 * _season_value(ts.date(), config.latitude)
        ghi = max(_climatology(history, "ghi_wm2", ts, 850.0 * _solar_shape(ts, config.latitude)), 850.0 * _solar_shape(ts, config.latitude))
        wind = max(0.5, _climatology(history, "wind_speed_mps", ts, 5.5))
        future_weather.append((temp, ghi, wind))
    x_future = np.asarray([_feature_vector(ts, config, *weather) for ts, weather in zip(future_times, future_weather)], dtype=float)
    model_output = _sklearn_predict(x_train, y_train, x_future)
    if model_output is None:
        model_name, forecast = _ridge_predict(x_train, y_train, x_future)
    else:
        model_name, forecast = model_output
    if config.kind == "renewable" and config.renewable_capacity_mw is not None and config.renewable_capacity_mw > 0:
        forecast = np.clip(forecast, 0.0, config.renewable_capacity_mw)
    else:
        forecast = np.maximum(forecast, 0.0)
    if model_output is None:
        _fitted_name, fitted = _ridge_predict(x_train, y_train, x_train)
    else:
        linear_model = importlib.import_module("sklearn.linear_model")
        fitted_model = linear_model.HuberRegressor(epsilon=1.35, alpha=0.0001, max_iter=500)
        fitted_model.fit(x_train, y_train)
        fitted = np.asarray(fitted_model.predict(x_train), dtype=float)
    residual = y_train - fitted
    mae = float(np.mean(np.abs(residual))) if residual.size else 0.0
    band = max(float(np.quantile(np.abs(residual), 0.80)) if residual.size else 0.0, 0.03 * float(np.mean(np.maximum(y_train, 1.0))))
    points: list[ForecastPoint] = []
    for ts, value, (temp, ghi, wind) in zip(future_times, forecast, future_weather):
        driver = f"星期{ts.weekday()+1}/{'节假日' if _is_holiday(ts.date(), config.holiday_country) else '工作日' if ts.weekday() < 5 else '周末'}，{climate}，T={temp:.1f}℃，GHI={ghi:.0f}W/m²，风={wind:.1f}m/s"
        points.append(ForecastPoint(ts, float(value), max(0.0, float(value - band)), float(value + band), temp, ghi, wind, driver))
    notes = (
        "日前 24 小时预测；结果用于调度员筛查和计划校核，不替代正式市场/调度系统。",
        "特征已包含小时、星期、节假日、南北半球季节项、经纬度、海拔和气候板块。",
        "可直接导入 CAISO/NYISO/ERCOT/PJM/GEFCom/NREL 风格 CSV；表头会自动映射常见字段。",
    )
    return ForecastResult(config.kind, climate, model_name, mae, tuple(points), notes)


def format_forecast_summary(result: ForecastResult) -> str:
    unit_title = "负荷" if result.kind == "load" else "新能源"
    values = [p.value_mw for p in result.points]
    peak = max(result.points, key=lambda p: p.value_mw)
    valley = min(result.points, key=lambda p: p.value_mw)
    lines = [
        f"══ {unit_title}日前 24 小时预测 ══════════════════════",
        f"模型：{result.model_name}",
        f"气候板块：{result.climate_block}",
        f"训练残差 MAE：{result.metric_mae_mw:.2f} MW",
        f"峰值：{peak.value_mw:.1f} MW @ {peak.timestamp:%Y-%m-%d %H:%M}",
        f"谷值：{valley.value_mw:.1f} MW @ {valley.timestamp:%Y-%m-%d %H:%M}",
        f"日电量/发电量：{sum(values):.1f} MWh",
        "",
        "小时                  P10      预测      P90      调度提示",
    ]
    for p in result.points:
        lines.append(f"{p.timestamp:%Y-%m-%d %H:%M}  {p.p10_mw:8.1f}  {p.value_mw:8.1f}  {p.p90_mw:8.1f}  {p.drivers}")
    lines.extend(["", "说明：", *[f"- {note}" for note in result.notes]])
    return "\n".join(lines)
