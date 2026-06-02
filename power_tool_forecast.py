"""Day-ahead load and renewable forecasting helpers for dispatch-oriented studies."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor


DATA_DIR = Path(__file__).resolve().parent / "data" / "forecast_samples"
HOLIDAY_CONFIG_PATH = Path(__file__).resolve().parent / "data" / "forecast_holidays.json"
FORECAST_BUILTIN_CONFIG_PATH = Path(__file__).resolve().parent / "data" / "forecast_builtin_config.json"

# Default photovoltaic-study site: Nanjing, China / 默认光伏分析站点：中国南京
NANJING_LATITUDE = 32.0603
NANJING_LONGITUDE = 118.7969
NANJING_ALTITUDE_M = 20.0


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
class ForecastAlgorithmInfo:
    code: str
    label: str
    description: str
    supports: tuple[str, ...]
    requires: tuple[str, ...] = ()
    priority: int = 100


@dataclass(frozen=True)
class ForecastConfig:
    kind: str
    target_date: date
    latitude: float = NANJING_LATITUDE
    longitude: float = NANJING_LONGITUDE
    altitude_m: float = NANJING_ALTITUDE_M
    holiday_country: str = "CN"
    holiday_config_path: str | Path | None = None
    renewable_capacity_mw: float | None = None
    renewable_resource: str = "solar"
    algorithm: str = "sklearn_auto"
    selected_algorithms: tuple[str, ...] | None = None
    interval_minutes: int = 15
    horizon_hours: int = 24
    use_special_events: bool = True
    event_config_path: str | Path | None = None
    weather_condition: str = "clear"
    cloud_cover_pct: float = 0.0
    irradiance_adjustment: float = 1.0
    pv_tilt_deg: float = 30.0
    pv_azimuth_deg: float = 180.0
    pv_albedo: float = 0.20
    pv_temp_coeff_pct_per_c: float = -0.35
    pv_noct_c: float = 45.0


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
    poa_wm2: float = 0.0
    solar_altitude_deg: float = float("nan")
    solar_azimuth_deg: float = float("nan")
    incidence_angle_deg: float = float("nan")
    weather_factor: float = 1.0
    pv_power_factor: float = 1.0


@dataclass(frozen=True)
class ForecastAlgorithmMetric:
    code: str
    label: str
    mae_mw: float
    rmse_mw: float
    mape_pct: float
    weight: float
    available: bool = True
    note: str = ""


@dataclass(frozen=True)
class ForecastResult:
    kind: str
    climate_block: str
    model_name: str
    metric_mae_mw: float
    points: tuple[ForecastPoint, ...]
    notes: tuple[str, ...]
    algorithm_metrics: tuple[ForecastAlgorithmMetric, ...] = ()
    daily_stats: tuple[tuple[str, float], ...] = ()
    algorithm_code: str = ""
    interval_minutes: int = 15


@dataclass(frozen=True)
class SolarPosition:
    timestamp: datetime
    timezone_offset_hours: int
    standard_meridian_deg: float
    equation_of_time_min: float
    local_solar_time_hours: float
    declination_deg: float
    hour_angle_deg: float
    altitude_deg: float
    azimuth_deg: float
    zenith_deg: float
    extraterrestrial_irradiance_wm2: float
    clear_sky_ghi_wm2: float


@dataclass(frozen=True)
class SolarDayProfile:
    target_date: date
    latitude: float
    longitude: float
    timezone_offset_hours: int
    standard_meridian_deg: float
    sunrise: datetime | None
    sunset: datetime | None
    solar_noon: datetime
    solar_noon_altitude_deg: float
    daylight_hours: float
    points: tuple[SolarPosition, ...]


@dataclass(frozen=True)
class SolarIrradianceResult:
    position: SolarPosition
    weather_factor: float
    corrected_ghi_wm2: float
    direct_horizontal_wm2: float
    diffuse_horizontal_wm2: float
    poa_direct_wm2: float
    poa_diffuse_wm2: float
    poa_ground_wm2: float
    poa_wm2: float
    incidence_angle_deg: float
    pv_cell_temperature_c: float
    pv_power_factor: float


@dataclass(frozen=True)
class _AlgorithmRun:
    code: str
    label: str
    values: np.ndarray
    validation: np.ndarray
    available: bool = True
    note: str = ""


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
        "notes": "Contains hourly solar and wind MW fields; forecast runs should select one independent resource type at a time.",
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
    {
        "name": "BAIDU_KDD_SDWPF_WIND_SAMPLE",
        "kind": "renewable",
        "file": "baidu_kdd_sdwpf_wind_sample.csv",
        "source": "Baidu KDD Cup 2022 / SDWPF wind-power schema sample",
        "region": "China wind farm schema sample",
        "latitude": 41.0,
        "longitude": 115.0,
        "altitude_m": 900.0,
        "notes": "Compact schema sample for the public SDWPF/Baidu KDD Cup 2022 fields such as TurbID, Day, Tmstamp, Wspd and Patv.",
    },
    {
        "name": "CSG_LOAD_FORECAST_SCHEMA_SAMPLE",
        "kind": "load",
        "file": "csg_load_forecast_sample.csv",
        "source": "Southern Grid dispatch AI / load-forecasting public dataset schema sample",
        "region": "China Southern Grid load schema sample",
        "latitude": 23.13,
        "longitude": 113.26,
        "altitude_m": 20.0,
        "notes": "Compact Chinese-column load forecast sample using 日期/时刻/统调负荷/气温-style headers.",
    },
    {
        "name": "ELECTRICIAN_CUP_LOAD_SCHEMA_SAMPLE",
        "kind": "load",
        "file": "electrician_cup_load_sample.csv",
        "source": "Electrician Cup load-forecasting schema sample",
        "region": "China Electrician Cup load schema sample",
        "latitude": 31.23,
        "longitude": 121.47,
        "altitude_m": 10.0,
        "notes": "Compact schema sample for 电工杯-style load forecasting tables with 日期/时刻/负荷/温度 columns.",
    },
)


_DEFAULT_FORECAST_BUILTIN_CONFIG: dict[str, object] = {
    "schema_version": "2026.06",
    "defaults": {
        "algorithm": "sklearn_auto",
        "interval_minutes": 15,
        "horizon_hours": 24,
        "ensemble_candidates": ["gradient_boosting", "random_forest", "huber", "ridge", "hourly_analog", "exp_smoothing", "seasonal_naive"],
        "validation_min_points": 24,
        "validation_fraction": 0.20,
        "confidence_quantile": 0.80,
    },
    "algorithm_catalog": [
        {
            "code": "sklearn_auto",
            "label": "scikit-learn自动引擎",
            "description": "默认引擎；强制依赖 scikit-learn，并优先使用梯度提升树/随机森林。",
            "supports": ["load", "renewable"],
            "requires": ["sklearn"],
            "priority": 5,
        },
        {
            "code": "adaptive_ensemble",
            "label": "自适应综合方案",
            "description": "对候选算法做滚动留出校验，按误差反比自动分配权重，形成综合预测方案。",
            "supports": ["load", "renewable"],
            "requires": [],
            "priority": 10,
        },
        {
            "code": "ridge",
            "label": "岭回归",
            "description": "线性可解释模型，包含小时、星期、节假日、季节、气象和地理特征。",
            "supports": ["load", "renewable"],
            "requires": [],
            "priority": 20,
        },
        {
            "code": "huber",
            "label": "Huber鲁棒回归",
            "description": "对异常点更稳健；使用两阶段 Huber 权重岭回归，作为鲁棒基线。",
            "supports": ["load", "renewable"],
            "requires": [],
            "priority": 30,
        },
        {
            "code": "hourly_analog",
            "label": "相似日同刻法",
            "description": "按同小时、日型、节假日和气象相似度选取历史样本，适合人工经验校核。",
            "supports": ["load", "renewable"],
            "requires": [],
            "priority": 40,
        },
        {
            "code": "exp_smoothing",
            "label": "同刻指数平滑",
            "description": "对同一时刻的历史值做递近加权，偏重近期负荷或出力规律。",
            "supports": ["load", "renewable"],
            "requires": [],
            "priority": 50,
        },
        {
            "code": "seasonal_naive",
            "label": "周周期基准",
            "description": "优先使用上一周同刻值，缺失时使用前一日或同刻中位数，作为保底预测。",
            "supports": ["load", "renewable"],
            "requires": [],
            "priority": 60,
        },
        {
            "code": "random_forest",
            "label": "随机森林",
            "description": "基于强制依赖 scikit-learn 的非线性树模型，适合气象非线性较强场景。",
            "supports": ["load", "renewable"],
            "requires": ["sklearn"],
            "priority": 70,
        },
        {
            "code": "gradient_boosting",
            "label": "梯度提升树",
            "description": "基于强制依赖 scikit-learn 的提升树模型，适合小样本非线性拟合对比。",
            "supports": ["load", "renewable"],
            "requires": ["sklearn"],
            "priority": 80,
        },
    ],
    "regions": [
        {"name": "南京默认站点", "kind": "renewable", "resource": "solar", "latitude": NANJING_LATITUDE, "longitude": NANJING_LONGITUDE, "altitude_m": NANJING_ALTITUDE_M, "holiday_country": "CN", "pv_tilt_deg": 30, "pv_azimuth_deg": 180},
        {"name": "南京负荷示例", "kind": "load", "latitude": NANJING_LATITUDE, "longitude": NANJING_LONGITUDE, "altitude_m": NANJING_ALTITUDE_M, "holiday_country": "CN"},
        {"name": "华东负荷示例", "kind": "load", "latitude": 31.23, "longitude": 121.47, "altitude_m": 10, "holiday_country": "CN"},
        {"name": "华南负荷示例", "kind": "load", "latitude": 23.13, "longitude": 113.26, "altitude_m": 20, "holiday_country": "CN"},
        {"name": "西北光伏基地示例", "kind": "renewable", "resource": "solar", "latitude": 38.5, "longitude": 101.0, "altitude_m": 1450, "holiday_country": "CN"},
        {"name": "冀北风电基地示例", "kind": "renewable", "resource": "wind", "latitude": 41.0, "longitude": 115.0, "altitude_m": 900, "holiday_country": "CN"},
    ],
    "special_events": [
        {
            "name": "高温错峰/需求侧响应示例",
            "region": "*",
            "kind": "load",
            "enabled": False,
            "start": "2025-06-22 13:00",
            "end": "2025-06-22 18:00",
            "ramp_hours": 1.0,
            "lag_hours": 0.0,
            "adjustment_mw": -300.0,
            "relative_adjustment": 0.0,
            "description": "默认关闭。启用后用于演示调度场景中特殊事件对预测结果的修正。",
        },
        {
            "name": "大风限电/弃风风险示例",
            "region": "*",
            "kind": "renewable",
            "resource": "wind",
            "enabled": False,
            "start": "2025-06-22 00:00",
            "end": "2025-06-22 06:00",
            "ramp_hours": 0.5,
            "lag_hours": 0.0,
            "adjustment_mw": 0.0,
            "relative_adjustment": -0.08,
            "description": "默认关闭。启用后用于演示新能源外部约束修正。",
        },
    ],
}


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
    "timestamp": {"timestamp", "time", "datetime", "date_time", "interval_start", "interval_start_time", "opr_dt", "date", "日期", "数据时间", "时间", "采样时间"},
    "day_index": {"day", "turbine_day", "样本日"},
    "minute_offset": {"tmstamp", "minute", "minutes", "分钟", "时刻", "minute_offset"},
    "interval_index": {"period", "point", "point_index", "interval", "idx", "序号", "点号", "时段", "时点", "96点"},
    "hour": {"hour", "he", "hour_ending", "opr_hr", "opr_hour", "小时"},
    "load_mw": {"load_mw", "demand_mw", "mw", "sys_fct_act_mw", "sys_fcst_act_mw", "total_load", "ercot", "load", "负荷", "统调负荷", "系统负荷", "电力负荷", "实测负荷", "样本负荷"},
    "renewable_mw": {"renewable_mw", "renewables_mw", "total_renewable_mw", "renewable", "ren_mw", "新能源", "新能源出力"},
    "solar_mw": {"solar_mw", "solar", "pv_mw", "solar_power_mw", "光伏", "光伏功率", "光伏出力", "光伏发电"},
    "wind_mw": {"wind_mw", "wind", "wind_power_mw", "patv", "active_power", "风电", "风电功率", "风电出力", "实际功率"},
    "temperature_c": {"temperature_c", "temp_c", "temperature", "dry_bulb_c", "t", "气温", "温度", "环境温度"},
    "ghi_wm2": {"ghi_wm2", "ghi", "global_horizontal_irradiance", "solar_irradiance", "辐照度", "总辐照", "水平辐照"},
    "wind_speed_mps": {"wind_speed_mps", "wind_speed", "ws_mps", "windspeed", "wspd", "风速"},
}


_BUILTIN_HOLIDAY_CALENDAR = {
    "US": {
        "fixed_mmdd": ["01-01", "07-04", "11-11", "12-25"],
        "nth_weekday": [
            {"month": 9, "weekday": 0, "nth": 1, "name": "Labor Day"},
            {"month": 11, "weekday": 3, "nth": 4, "name": "Thanksgiving"},
        ],
        "dates": [],
    },
    "CN": {
        "fixed_mmdd": ["01-01", "05-01", "10-01", "10-02", "10-03", "10-04", "10-05", "10-06", "10-07"],
        "nth_weekday": [],
        "dates": [
            "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31", "2025-02-01", "2025-02-02", "2025-02-03",
            "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-21", "2026-02-22",
        ],
    },
}


_HOLIDAY_CALENDAR_CACHE: dict[Path, dict[str, object]] = {}
_FORECAST_BUILTIN_CONFIG_CACHE: dict[Path, dict[str, object]] = {}


def _deepcopy_jsonable(data: object) -> object:
    return json.loads(json.dumps(data, ensure_ascii=False))


def _merge_named_lists(base: list[dict[str, object]], override: list[dict[str, object]], key: str = "code") -> list[dict[str, object]]:
    merged = {str(item.get(key)): dict(item) for item in base if isinstance(item, dict) and item.get(key) is not None}
    for item in override:
        if isinstance(item, dict) and item.get(key) is not None:
            merged[str(item.get(key))] = {**merged.get(str(item.get(key)), {}), **item}
    return list(merged.values())


def load_forecast_builtin_config(path: str | Path | None = None) -> dict[str, object]:
    """Load the built-in JSON forecast configuration and merge it with safe defaults."""
    config = _deepcopy_jsonable(_DEFAULT_FORECAST_BUILTIN_CONFIG)
    config_path = Path(path) if path is not None else FORECAST_BUILTIN_CONFIG_PATH
    if not config_path.exists():
        return config  # type: ignore[return-value]
    config_path = config_path.resolve()
    if config_path in _FORECAST_BUILTIN_CONFIG_CACHE:
        external = _FORECAST_BUILTIN_CONFIG_CACHE[config_path]
    else:
        with config_path.open("r", encoding="utf-8") as f:
            external = json.load(f)
        _FORECAST_BUILTIN_CONFIG_CACHE[config_path] = external
    if not isinstance(external, dict):
        return config  # type: ignore[return-value]
    assert isinstance(config, dict)
    for key, value in external.items():
        if key == "defaults" and isinstance(value, dict) and isinstance(config.get(key), dict):
            merged = dict(config[key])  # type: ignore[index]
            merged.update(value)
            config[key] = merged
        elif key == "algorithm_catalog" and isinstance(value, list) and isinstance(config.get(key), list):
            config[key] = _merge_named_lists(config[key], value, "code")  # type: ignore[arg-type,index]
        elif key in {"regions", "special_events"} and isinstance(value, list) and isinstance(config.get(key), list):
            config[key] = value
        else:
            config[key] = value
    return config


def list_forecast_algorithms(kind: str | None = None) -> list[ForecastAlgorithmInfo]:
    cfg = load_forecast_builtin_config()
    algorithms: list[ForecastAlgorithmInfo] = []
    for item in cfg.get("algorithm_catalog", []):
        if not isinstance(item, dict):
            continue
        supports = tuple(str(x) for x in item.get("supports", ["load", "renewable"]))
        if kind is not None and kind not in supports:
            continue
        algorithms.append(
            ForecastAlgorithmInfo(
                code=str(item.get("code", "")),
                label=str(item.get("label", item.get("code", ""))),
                description=str(item.get("description", "")),
                supports=supports,
                requires=tuple(str(x) for x in item.get("requires", [])),
                priority=int(item.get("priority", 100)),
            )
        )
    return sorted([a for a in algorithms if a.code], key=lambda a: (a.priority, a.code))


def forecast_algorithm_label(code: str) -> str:
    for info in list_forecast_algorithms():
        if info.code == code:
            return info.label
    return code


def load_holiday_calendar(path: str | Path | None = None) -> dict[str, object]:
    calendar: dict[str, object] = json.loads(json.dumps(_BUILTIN_HOLIDAY_CALENDAR))
    config_path = Path(path) if path is not None else HOLIDAY_CONFIG_PATH
    if not config_path.exists():
        return calendar
    config_path = config_path.resolve()
    if config_path in _HOLIDAY_CALENDAR_CACHE:
        external = _HOLIDAY_CALENDAR_CACHE[config_path]
    else:
        with config_path.open("r", encoding="utf-8") as f:
            external = json.load(f)
        _HOLIDAY_CALENDAR_CACHE[config_path] = external
    for country, settings in external.items():
        base = calendar.setdefault(country.upper(), {"fixed_mmdd": [], "nth_weekday": [], "dates": []})
        if isinstance(settings, dict):
            for key in ("fixed_mmdd", "nth_weekday", "dates", "workdays"):
                if key in settings:
                    base[key] = settings[key]  # type: ignore[index]
    return calendar


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
    key = header.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
    for canonical, aliases in _COLUMN_ALIASES.items():
        if key in aliases:
            return canonical
    return None


def _parse_timestamp(text: str) -> datetime:
    raw = text.strip().replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
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
        mapped_values = set(mapping.values())
        if "timestamp" not in mapped_values and not ({"day_index", "minute_offset"} <= mapped_values):
            raise ValueError("CSV 需要 timestamp/time/datetime/date_time 等时间列，或 Day + Tmstamp 组合列。")
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
            if "timestamp" not in item and "day_index" in item and "minute_offset" in item:
                day = int(item.pop("day_index"))
                minute_offset = int(item.pop("minute_offset"))
                item["timestamp"] = datetime(2025, 1, 1) + timedelta(days=max(day - 1, 0), minutes=minute_offset)
            if "timestamp" in item and "minute_offset" in item and isinstance(item["timestamp"], datetime):
                minute_offset = int(item.pop("minute_offset"))
                item["timestamp"] = item["timestamp"].replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=minute_offset)
            if "timestamp" in item and "interval_index" in item and isinstance(item["timestamp"], datetime):
                idx = int(item.pop("interval_index"))
                idx0 = max(0, idx - 1) if idx >= 1 else max(0, idx)
                item["timestamp"] = item["timestamp"].replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=15 * idx0)
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


def classify_climate_block(latitude: float, longitude: float, altitude_m: float = 0.0) -> str:
    if altitude_m >= 1200:
        return "高海拔/山地气候"
    lat = float(latitude)
    lon = float(longitude)
    for _code, lat_min, lat_max, lon_min, lon_max, label in CLIMATE_BLOCKS:
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


def _is_holiday(d: date, country: str, calendar_path: str | Path | None = None) -> bool:
    calendar = load_holiday_calendar(calendar_path)
    rules = calendar.get(country.upper()) or calendar.get(country)
    if not isinstance(rules, dict):
        return False
    workdays = {str(item) for item in rules.get("workdays", [])}
    if d.isoformat() in workdays:
        return False
    fixed = {str(item) for item in rules.get("fixed_mmdd", [])}
    if f"{d.month:02d}-{d.day:02d}" in fixed:
        return True
    exact_dates = {str(item) for item in rules.get("dates", [])}
    if d.isoformat() in exact_dates:
        return True
    for rule in rules.get("nth_weekday", []):
        if not isinstance(rule, dict):
            continue
        if d.month != int(rule.get("month", -1)) or d.weekday() != int(rule.get("weekday", -1)):
            continue
        nth = int(rule.get("nth", 0))
        occurrence = (d.day - 1) // 7 + 1
        if nth > 0 and occurrence == nth:
            return True
        if nth < 0 and (d + timedelta(days=7)).month != d.month:
            return True
    return False


def _season_value(d: date, latitude: float) -> float:
    day = d.timetuple().tm_yday
    shift = 172 if latitude >= 0 else 355
    return math.cos(2.0 * math.pi * (day - shift) / 365.25)


def _solar_shape(ts: datetime, latitude: float) -> float:
    daylight = max(8.0, 12.0 + 4.0 * math.cos(2.0 * math.pi * (ts.timetuple().tm_yday - (172 if latitude >= 0 else 355)) / 365.25))
    sunrise = 12.0 - daylight / 2.0
    phase = (ts.hour + ts.minute / 60.0 + 0.5 - sunrise) / daylight
    if phase <= 0.0 or phase >= 1.0:
        return 0.0
    return math.sin(math.pi * phase) ** 1.35


def _finite_float(value: object, default: float = float("nan")) -> float:
    try:
        x = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return x if math.isfinite(x) else default


def solar_timezone_offset_hours(longitude: float) -> int:
    """Return the nominal civil timezone implied by longitude. / 根据经度返回名义标准时区。"""
    offset = int(round(float(longitude) / 15.0))
    return max(-12, min(14, offset))


def _solar_declination_deg(day_of_year: int) -> float:
    return 23.44 * math.sin(2.0 * math.pi * (284 + day_of_year) / 365.25)


def solar_equation_of_time_minutes(day_of_year: int) -> float:
    b = math.radians(360.0 * (day_of_year - 81) / 364.0)
    return 9.87 * math.sin(2.0 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def solar_position(ts: datetime, latitude: float, longitude: float, timezone_offset_hours: int | None = None) -> SolarPosition:
    """Compute apparent solar position and reference irradiance in local standard time.

    The input ``ts`` is treated as local standard civil time for the timezone selected
    from the longitude unless ``timezone_offset_hours`` is supplied explicitly.
    / 计算当地标准时下的太阳位置与参考辐照度。
    """
    tz = solar_timezone_offset_hours(longitude) if timezone_offset_hours is None else int(timezone_offset_hours)
    standard_meridian = 15.0 * tz
    day = ts.timetuple().tm_yday
    eot = solar_equation_of_time_minutes(day)
    local_civil_hours = ts.hour + ts.minute / 60.0 + ts.second / 3600.0
    time_correction = 4.0 * (float(longitude) - standard_meridian) + eot
    local_solar_hours = local_civil_hours + time_correction / 60.0
    decl_deg = _solar_declination_deg(day)
    hour_angle_deg = 15.0 * (local_solar_hours - 12.0)

    lat = math.radians(float(latitude))
    decl = math.radians(decl_deg)
    hour_angle = math.radians(hour_angle_deg)
    sin_alt = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(hour_angle)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    altitude_deg = math.degrees(math.asin(sin_alt))
    zenith_deg = 90.0 - altitude_deg

    azimuth_deg = (
        math.degrees(
            math.atan2(
                -math.sin(hour_angle),
                math.tan(decl) * math.cos(lat) - math.sin(lat) * math.cos(hour_angle),
            )
        )
        + 360.0
    ) % 360.0

    cos_zenith = max(0.0, math.cos(math.radians(zenith_deg)))
    eccentricity = 1.0 + 0.033 * math.cos(2.0 * math.pi * day / 365.25)
    extraterrestrial = 1367.0 * eccentricity * cos_zenith
    clear_sky_ghi = 0.0 if cos_zenith <= 0.0 else 1098.0 * cos_zenith * math.exp(-0.059 / max(cos_zenith, 1e-6))

    return SolarPosition(
        timestamp=ts,
        timezone_offset_hours=tz,
        standard_meridian_deg=standard_meridian,
        equation_of_time_min=eot,
        local_solar_time_hours=local_solar_hours,
        declination_deg=decl_deg,
        hour_angle_deg=hour_angle_deg,
        altitude_deg=altitude_deg,
        azimuth_deg=azimuth_deg,
        zenith_deg=zenith_deg,
        extraterrestrial_irradiance_wm2=float(max(0.0, extraterrestrial)),
        clear_sky_ghi_wm2=float(max(0.0, clear_sky_ghi)),
    )


def solar_altitude_deg(ts: datetime, latitude: float, longitude: float) -> float:
    return solar_position(ts, latitude, longitude).altitude_deg


def solar_day_profile(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_offset_hours: int | None = None,
    step_minutes: int = 10,
) -> SolarDayProfile:
    """Return a visualisation-friendly daily solar track. / 返回适合可视化的全天太阳轨迹。"""
    if step_minutes <= 0 or step_minutes > 180:
        raise ValueError('step_minutes must be within 1..180')
    tz = solar_timezone_offset_hours(longitude) if timezone_offset_hours is None else int(timezone_offset_hours)
    standard_meridian = 15.0 * tz
    day = target_date.timetuple().tm_yday
    decl_deg = _solar_declination_deg(day)
    decl = math.radians(decl_deg)
    lat = math.radians(float(latitude))
    eot = solar_equation_of_time_minutes(day)
    solar_noon_hours = 12.0 - (4.0 * (float(longitude) - standard_meridian) + eot) / 60.0
    solar_noon_dt = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=solar_noon_hours)
    solar_noon_pos = solar_position(solar_noon_dt, latitude, longitude, tz)

    cos_omega0 = -math.tan(lat) * math.tan(decl)
    if cos_omega0 <= -1.0:
        daylight_hours = 24.0
        sunrise_dt = datetime.combine(target_date, datetime.min.time())
        sunset_dt = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=23, minutes=59)
    elif cos_omega0 >= 1.0:
        daylight_hours = 0.0
        sunrise_dt = None
        sunset_dt = None
    else:
        omega0 = math.degrees(math.acos(cos_omega0))
        daylight_hours = 2.0 * omega0 / 15.0
        sunrise_dt = solar_noon_dt - timedelta(hours=daylight_hours / 2.0)
        sunset_dt = solar_noon_dt + timedelta(hours=daylight_hours / 2.0)

    points: list[SolarPosition] = []
    t0 = datetime.combine(target_date, datetime.min.time())
    total_steps = int(round(24 * 60 / step_minutes))
    for idx in range(total_steps + 1):
        ts = t0 + timedelta(minutes=idx * step_minutes)
        if ts.date() != target_date and idx != total_steps:
            continue
        points.append(solar_position(ts, latitude, longitude, tz))

    return SolarDayProfile(
        target_date=target_date,
        latitude=float(latitude),
        longitude=float(longitude),
        timezone_offset_hours=tz,
        standard_meridian_deg=standard_meridian,
        sunrise=sunrise_dt,
        sunset=sunset_dt,
        solar_noon=solar_noon_dt,
        solar_noon_altitude_deg=solar_noon_pos.altitude_deg,
        daylight_hours=max(0.0, daylight_hours),
        points=tuple(points),
    )


def _normalize_weather_condition(condition: str) -> str:
    key = str(condition or "clear").strip().lower()
    mapping = {
        "clear": "clear", "sunny": "clear", "晴": "clear", "晴空": "clear",
        "partly_cloudy": "partly_cloudy", "partly": "partly_cloudy", "few_clouds": "partly_cloudy", "少云": "partly_cloudy", "晴间多云": "partly_cloudy",
        "cloudy": "cloudy", "多云": "cloudy",
        "overcast": "overcast", "阴": "overcast", "阴天": "overcast",
        "rain": "rain_snow", "snow": "rain_snow", "rain_snow": "rain_snow", "雨": "rain_snow", "雨雪": "rain_snow",
        "haze": "haze", "fog": "haze", "雾": "haze", "霾": "haze", "雾霾": "haze",
    }
    return mapping.get(key, key if key in {"clear", "partly_cloudy", "cloudy", "overcast", "rain_snow", "haze"} else "clear")


def solar_weather_factor(condition: str = "clear", cloud_cover_pct: float = 0.0, irradiance_adjustment: float = 1.0) -> float:
    """Return an empirical 0..1.25 irradiance factor for weather correction. / 天气修正系数。"""
    kind = _normalize_weather_condition(condition)
    base = {
        "clear": 1.00,
        "partly_cloudy": 0.82,
        "cloudy": 0.58,
        "overcast": 0.30,
        "rain_snow": 0.16,
        "haze": 0.68,
    }.get(kind, 1.0)
    cloud = min(max(float(cloud_cover_pct), 0.0), 100.0) / 100.0
    cloud_factor = 1.0 - 0.52 * (cloud ** 1.35)
    manual = min(max(float(irradiance_adjustment), 0.05), 1.25)
    return float(min(max(base * cloud_factor * manual, 0.02), 1.25))


def _solar_diffuse_fraction(weather_factor: float) -> float:
    # Diffuse component grows under clouds/haze; bounded for numerical stability.
    return float(min(max(0.18 + 0.58 * (1.0 - min(max(weather_factor, 0.0), 1.0)), 0.16), 0.82))


def solar_irradiance_on_panel(
    ts: datetime,
    latitude: float,
    longitude: float,
    temperature_c: float = 25.0,
    weather_condition: str = "clear",
    cloud_cover_pct: float = 0.0,
    irradiance_adjustment: float = 1.0,
    panel_tilt_deg: float = 30.0,
    panel_azimuth_deg: float = 180.0,
    albedo: float = 0.20,
    temp_coeff_pct_per_c: float = -0.35,
    noct_c: float = 45.0,
    input_ghi_wm2: float | None = None,
) -> SolarIrradianceResult:
    """Compute weather-corrected horizontal and tilted-plane irradiance for PV studies.

    Azimuth convention is the same as ``solar_position``: 0° north, 90° east,
    180° south, 270° west.  The PV power factor is relative to a horizontal
    clear-sky reference at the same instant and includes a simple cell-temperature
    derating.
    / 计算光伏组件倾斜面辐照度与相对功率修正系数。
    """
    pos = solar_position(ts, latitude, longitude)
    weather_factor = solar_weather_factor(weather_condition, cloud_cover_pct, irradiance_adjustment)
    clear_ghi = max(0.0, pos.clear_sky_ghi_wm2)
    if input_ghi_wm2 is None or not math.isfinite(float(input_ghi_wm2)):
        corrected_ghi = clear_ghi * weather_factor
    else:
        # Treat provided GHI as the baseline weather expectation and still allow user correction.
        corrected_ghi = max(0.0, float(input_ghi_wm2)) * weather_factor
    if pos.altitude_deg <= 0.0 or corrected_ghi <= 0.0:
        return SolarIrradianceResult(pos, weather_factor, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 90.0, float(temperature_c), 0.0)

    beta = math.radians(min(max(float(panel_tilt_deg), 0.0), 90.0))
    surface_az = math.radians(float(panel_azimuth_deg) % 360.0)
    sun_az = math.radians(pos.azimuth_deg)
    sin_alt = max(math.sin(math.radians(pos.altitude_deg)), 1e-6)
    cos_inc = math.sin(math.radians(pos.altitude_deg)) * math.cos(beta) + math.cos(math.radians(pos.altitude_deg)) * math.sin(beta) * math.cos(sun_az - surface_az)
    cos_inc = max(0.0, min(1.0, cos_inc))
    incidence_angle = math.degrees(math.acos(max(-1.0, min(1.0, cos_inc))))

    diffuse_fraction = _solar_diffuse_fraction(weather_factor)
    diffuse_horizontal = corrected_ghi * diffuse_fraction
    direct_horizontal = max(0.0, corrected_ghi - diffuse_horizontal)
    dni = direct_horizontal / sin_alt
    poa_direct = dni * cos_inc
    poa_diffuse = diffuse_horizontal * (1.0 + math.cos(beta)) / 2.0
    poa_ground = corrected_ghi * min(max(float(albedo), 0.0), 0.9) * (1.0 - math.cos(beta)) / 2.0
    poa = max(0.0, poa_direct + poa_diffuse + poa_ground)

    cell_temp = float(temperature_c) + max(float(noct_c) - 20.0, 0.0) / 800.0 * poa
    temp_derate = 1.0 + (float(temp_coeff_pct_per_c) / 100.0) * (cell_temp - 25.0)
    temp_derate = min(max(temp_derate, 0.65), 1.08)
    clear_reference = max(clear_ghi, 1.0)
    pv_power_factor = min(max((poa / clear_reference) * temp_derate, 0.0), 1.45)

    return SolarIrradianceResult(
        position=pos,
        weather_factor=weather_factor,
        corrected_ghi_wm2=float(corrected_ghi),
        direct_horizontal_wm2=float(direct_horizontal),
        diffuse_horizontal_wm2=float(diffuse_horizontal),
        poa_direct_wm2=float(poa_direct),
        poa_diffuse_wm2=float(poa_diffuse),
        poa_ground_wm2=float(poa_ground),
        poa_wm2=float(poa),
        incidence_angle_deg=float(incidence_angle),
        pv_cell_temperature_c=float(cell_temp),
        pv_power_factor=float(pv_power_factor),
    )


def _solar_daylight_factor(ts: datetime, latitude: float, longitude: float) -> float:
    altitude = solar_altitude_deg(ts, latitude, longitude)
    if altitude <= 0.0:
        return 0.0
    return min(1.0, math.sin(math.radians(altitude)) / max(math.sin(math.radians(70.0)), 1e-6))



def _geo_weather_baseline(ts: datetime, config: ForecastConfig, climate: str) -> tuple[float, float, float]:
    season = _season_value(ts.date(), config.latitude)
    diurnal = math.sin(2.0 * math.pi * (ts.hour + ts.minute / 60.0 - 14) / 24.0)
    abs_lat = abs(float(config.latitude))
    if "热带" in climate:
        base_temp, seasonal_amp, diurnal_amp, clear_ghi, wind = 27.0, 2.5, 4.0, 940.0, 4.5
    elif "高海拔" in climate or "山地" in climate:
        base_temp, seasonal_amp, diurnal_amp, clear_ghi, wind = 10.0, 9.0, 8.0, 980.0, 6.8
    elif "寒" in climate or "极地" in climate:
        base_temp, seasonal_amp, diurnal_amp, clear_ghi, wind = 3.0, 15.0, 5.0, 650.0, 7.0
    elif "干旱" in climate or "地中海" in climate:
        base_temp, seasonal_amp, diurnal_amp, clear_ghi, wind = 18.0, 10.0, 9.0, 1000.0, 5.2
    elif "美国西海岸" in climate or "海洋" in climate:
        base_temp, seasonal_amp, diurnal_amp, clear_ghi, wind = 14.0, 5.0, 4.5, 820.0, 5.8
    else:
        base_temp, seasonal_amp, diurnal_amp, clear_ghi, wind = 16.0, 11.0, 6.5, 850.0, 5.5
    altitude_lapse = 6.5 * max(float(config.altitude_m), 0.0) / 1000.0
    latitude_cooling = max(0.0, abs_lat - 35.0) * 0.08
    temp = base_temp + seasonal_amp * season + diurnal_amp * diurnal - altitude_lapse - latitude_cooling
    ghi = clear_ghi * _solar_daylight_factor(ts, config.latitude, config.longitude)
    wind_speed = max(0.5, wind + 0.8 * math.sin(2.0 * math.pi * (ts.hour + ts.minute / 60.0 + 3) / 24.0) + 0.35 * abs(season))
    return temp, ghi, wind_speed


def _climatology(rows: list[dict[str, float | datetime]], key: str, ts: datetime, fallback: float) -> float:
    same_slot = [
        _finite_float(r.get(key))
        for r in rows
        if isinstance(r.get("timestamp"), datetime)
        and r["timestamp"].hour == ts.hour
        and r["timestamp"].minute == ts.minute
        and math.isfinite(_finite_float(r.get(key)))
    ]
    if same_slot:
        return float(np.median(same_slot))
    same_hour = [
        _finite_float(r.get(key))
        for r in rows
        if isinstance(r.get("timestamp"), datetime) and r["timestamp"].hour == ts.hour and math.isfinite(_finite_float(r.get(key)))
    ]
    if same_hour:
        return float(np.median(same_hour))
    values = [_finite_float(r.get(key)) for r in rows if math.isfinite(_finite_float(r.get(key)))]
    return float(np.median(values)) if values else fallback


def _inferred_weather(rows: list[dict[str, float | datetime]], ts: datetime, config: ForecastConfig, climate: str) -> tuple[float, float, float]:
    geo_temp, geo_ghi, geo_wind = _geo_weather_baseline(ts, config, climate)
    temp = _climatology(rows, "temperature_c", ts, geo_temp)
    ghi = _climatology(rows, "ghi_wm2", ts, geo_ghi)
    wind = _climatology(rows, "wind_speed_mps", ts, geo_wind)
    if not math.isfinite(temp):
        temp = geo_temp
    if not math.isfinite(ghi):
        ghi = geo_ghi
    if not math.isfinite(wind):
        wind = geo_wind
    daylight = _solar_daylight_factor(ts, config.latitude, config.longitude)
    if daylight <= 0.0:
        ghi = 0.0
    elif ghi <= 0.0:
        ghi = geo_ghi
    return float(temp), max(0.0, float(ghi)), max(0.0, float(wind))


def _row_weather(row: dict[str, float | datetime], rows: list[dict[str, float | datetime]], config: ForecastConfig, climate: str) -> tuple[float, float, float]:
    ts = row["timestamp"]
    if not isinstance(ts, datetime):
        return _geo_weather_baseline(datetime.combine(config.target_date, datetime.min.time()), config, climate)
    inferred = _inferred_weather(rows, ts, config, climate)
    temp = _finite_float(row.get("temperature_c"), inferred[0])
    ghi = _finite_float(row.get("ghi_wm2"), inferred[1])
    wind = _finite_float(row.get("wind_speed_mps"), inferred[2])
    if _solar_daylight_factor(ts, config.latitude, config.longitude) <= 0.0:
        ghi = 0.0
    return temp, max(0.0, ghi), max(0.0, wind)


def _renewable_resource(config: ForecastConfig) -> str:
    requested = config.renewable_resource.strip().lower()
    mapping = {"pv": "solar", "光伏": "solar", "solar": "solar", "wind": "wind", "风电": "wind"}
    resource = mapping.get(requested, requested)
    if resource not in {"solar", "wind"}:
        raise ValueError("新能源预测仅支持 wind/风电 或 solar/光伏 两种独立类型。")
    return resource


def _feature_vector(ts: datetime, config: ForecastConfig, temp_c: float, ghi_wm2: float, wind_mps: float) -> list[float]:
    dow = ts.weekday()
    tod = ts.hour + ts.minute / 60.0
    hour_angle = 2.0 * math.pi * tod / 24.0
    dow_angle = 2.0 * math.pi * dow / 7.0
    season = _season_value(ts.date(), config.latitude)
    weekend = 1.0 if dow >= 5 else 0.0
    holiday = 1.0 if _is_holiday(ts.date(), config.holiday_country, config.holiday_config_path) else 0.0
    minute_slot = tod / 24.0
    solar = solar_irradiance_on_panel(
        ts,
        config.latitude,
        config.longitude,
        temp_c,
        weather_condition="clear",
        cloud_cover_pct=0.0,
        irradiance_adjustment=1.0,
        panel_tilt_deg=config.pv_tilt_deg,
        panel_azimuth_deg=config.pv_azimuth_deg,
        albedo=config.pv_albedo,
        temp_coeff_pct_per_c=config.pv_temp_coeff_pct_per_c,
        noct_c=config.pv_noct_c,
        input_ghi_wm2=ghi_wm2,
    )
    sun_alt = solar.position.altitude_deg
    sun_az_rad = math.radians(solar.position.azimuth_deg)
    inc_cos = math.cos(math.radians(solar.incidence_angle_deg)) if math.isfinite(solar.incidence_angle_deg) else 0.0
    return [
        1.0,
        math.sin(hour_angle), math.cos(hour_angle), math.sin(2 * hour_angle), math.cos(2 * hour_angle), minute_slot,
        math.sin(dow_angle), math.cos(dow_angle), weekend, holiday,
        season, season * season,
        float(config.latitude) / 90.0, float(config.longitude) / 180.0, min(max(config.altitude_m, 0.0), 5000.0) / 5000.0,
        temp_c, temp_c * temp_c / 40.0,
        ghi_wm2 / 1000.0, wind_mps / 20.0,
        max(sun_alt, -15.0) / 90.0, math.sin(sun_az_rad), math.cos(sun_az_rad),
        solar.poa_wm2 / 1000.0, max(0.0, inc_cos), solar.pv_power_factor,
        min(max(config.pv_tilt_deg, 0.0), 90.0) / 90.0, math.sin(math.radians(config.pv_azimuth_deg)), math.cos(math.radians(config.pv_azimuth_deg)),
    ]


def _target_value(row: dict[str, float | datetime], config: ForecastConfig, resource: str = "load") -> float:
    if config.kind == "renewable":
        if resource == "solar":
            return max(0.0, _finite_float(row.get("solar_mw"), 0.0))
        if resource == "wind":
            return max(0.0, _finite_float(row.get("wind_mw"), 0.0))
    return max(0.0, _finite_float(row.get("load_mw"), 0.0))


def _rows_to_features(
    rows: Sequence[dict[str, float | datetime]],
    config: ForecastConfig,
    climate: str,
    resource: str,
    weather_source_rows: Sequence[dict[str, float | datetime]] | None = None,
) -> tuple[list[datetime], np.ndarray, np.ndarray, list[tuple[float, float, float]]]:
    source_rows = list(weather_source_rows if weather_source_rows is not None else rows)
    times: list[datetime] = []
    features: list[list[float]] = []
    targets: list[float] = []
    weathers: list[tuple[float, float, float]] = []
    for row in rows:
        ts = row.get("timestamp")
        if not isinstance(ts, datetime):
            continue
        temp, ghi, wind = _row_weather(row, source_rows, config, climate)
        times.append(ts)
        features.append(_feature_vector(ts, config, temp, ghi, wind))
        targets.append(_target_value(row, config, resource))
        weathers.append((temp, ghi, wind))
    return times, np.asarray(features, dtype=float), np.asarray(targets, dtype=float), weathers


def _future_grid(config: ForecastConfig) -> list[datetime]:
    interval = int(config.interval_minutes)
    if interval < 1 or interval > 30:
        raise ValueError("时段间隔需为 1 到 30 分钟之间的整数。")
    if config.horizon_hours <= 0:
        raise ValueError("预测时长必须大于 0。")
    total_minutes = int(round(config.horizon_hours * 60))
    n_points = int(math.ceil(total_minutes / interval))
    start = datetime.combine(config.target_date, datetime.min.time())
    return [start + timedelta(minutes=interval * i) for i in range(n_points) if interval * i < total_minutes]


def _future_features(times: Sequence[datetime], history: list[dict[str, float | datetime]], config: ForecastConfig, climate: str) -> tuple[np.ndarray, list[tuple[float, float, float]]]:
    future_weather: list[tuple[float, float, float]] = []
    solar_resource = config.kind == "renewable" and _renewable_resource(config) == "solar"
    for ts in times:
        temp, ghi, wind = _inferred_weather(history, ts, config, climate)
        if solar_resource:
            irr = solar_irradiance_on_panel(
                ts, config.latitude, config.longitude, temp,
                config.weather_condition, config.cloud_cover_pct, config.irradiance_adjustment,
                config.pv_tilt_deg, config.pv_azimuth_deg, config.pv_albedo,
                config.pv_temp_coeff_pct_per_c, config.pv_noct_c,
                input_ghi_wm2=None,
            )
            ghi = irr.corrected_ghi_wm2
        future_weather.append((float(temp), float(ghi), float(wind)))
    x_future = np.asarray([_feature_vector(ts, config, *weather) for ts, weather in zip(times, future_weather)], dtype=float)
    return x_future, future_weather


def _standardize_train_future(x_train: np.ndarray, x_future: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    scale = np.std(x_train, axis=0)
    scale[scale < 1e-9] = 1.0
    return x_train / scale, x_future / scale, scale


def _ridge_values(x_train: np.ndarray, y_train: np.ndarray, x_future: np.ndarray, lam: float = 0.25) -> np.ndarray:
    if x_train.size == 0 or y_train.size == 0:
        return np.zeros(x_future.shape[0], dtype=float)
    x_scaled, xf_scaled, _scale = _standardize_train_future(x_train, x_future)
    beta = np.linalg.pinv(x_scaled.T @ x_scaled + lam * np.eye(x_scaled.shape[1])) @ x_scaled.T @ y_train
    return np.asarray(xf_scaled @ beta, dtype=float)


def _weighted_ridge_values(x_train: np.ndarray, y_train: np.ndarray, x_future: np.ndarray, weights: np.ndarray, lam: float = 0.35) -> np.ndarray:
    x_scaled, xf_scaled, _scale = _standardize_train_future(x_train, x_future)
    w = np.sqrt(np.maximum(weights, 1e-6))
    xw = x_scaled * w[:, None]
    yw = y_train * w
    beta = np.linalg.pinv(xw.T @ xw + lam * np.eye(xw.shape[1])) @ xw.T @ yw
    return np.asarray(xf_scaled @ beta, dtype=float)


def _huber_values(x_train: np.ndarray, y_train: np.ndarray, x_future: np.ndarray) -> tuple[np.ndarray, str]:
    """Fast robust regression approximation.

    The production tool is intentionally self-contained. Instead of depending on
    an iterative sklearn HuberRegressor, which can be slow on unscaled dispatch
    features, this two-pass estimator first fits ridge regression, then
    down-weights high-residual samples with a Huber-style influence function.
    """
    initial = _ridge_values(x_train, y_train, x_train)
    residual = np.abs(y_train - initial)
    scale = np.median(residual) * 1.4826 + 1e-6
    weights = np.where(residual <= 1.35 * scale, 1.0, (1.35 * scale) / np.maximum(residual, 1e-6))
    return _weighted_ridge_values(x_train, y_train, x_future, weights), "两阶段Huber权重岭回归。"

def _sklearn_tree_values(code: str, x_train: np.ndarray, y_train: np.ndarray, x_future: np.ndarray) -> tuple[np.ndarray | None, str]:
    try:
        if code == "random_forest":
            model = RandomForestRegressor(n_estimators=32, max_depth=7, min_samples_leaf=2, random_state=42, n_jobs=1)
        else:
            model = GradientBoostingRegressor(n_estimators=60, max_depth=3, learning_rate=0.06, random_state=42)
        model.fit(x_train, y_train)
        return np.asarray(model.predict(x_future), dtype=float), ""
    except Exception as exc:  # pragma: no cover - sklearn version details vary
        return None, f"scikit-learn 树模型调用失败：{exc}"


def _slot_key(ts: datetime) -> tuple[int, int]:
    return ts.hour, ts.minute


def _median_target(rows: Sequence[dict[str, float | datetime]], config: ForecastConfig, resource: str, default: float = 0.0) -> float:
    vals = [_target_value(r, config, resource) for r in rows if isinstance(r.get("timestamp"), datetime)]
    return float(np.median(vals)) if vals else default


def _slot_rows(rows: Sequence[dict[str, float | datetime]], ts: datetime) -> list[dict[str, float | datetime]]:
    exact = [r for r in rows if isinstance(r.get("timestamp"), datetime) and _slot_key(r["timestamp"]) == _slot_key(ts)]  # type: ignore[index]
    if exact:
        return exact
    return [r for r in rows if isinstance(r.get("timestamp"), datetime) and r["timestamp"].hour == ts.hour]  # type: ignore[index]


def _seasonal_naive_predict(rows: Sequence[dict[str, float | datetime]], future_times: Sequence[datetime], config: ForecastConfig, resource: str) -> np.ndarray:
    lookup: dict[datetime, float] = {}
    for row in rows:
        ts = row.get("timestamp")
        if isinstance(ts, datetime):
            lookup[ts.replace(second=0, microsecond=0)] = _target_value(row, config, resource)
    default = _median_target(rows, config, resource, 0.0)
    out: list[float] = []
    for ts in future_times:
        candidates = [ts - timedelta(days=7), ts - timedelta(days=1)]
        value = None
        for cand in candidates:
            if cand in lookup:
                value = lookup[cand]
                break
        if value is None:
            slot = [_target_value(r, config, resource) for r in _slot_rows(rows, ts)]
            value = float(np.median(slot)) if slot else default
        out.append(value)
    return np.asarray(out, dtype=float)


def _exp_smoothing_predict(rows: Sequence[dict[str, float | datetime]], future_times: Sequence[datetime], config: ForecastConfig, resource: str) -> np.ndarray:
    default = _median_target(rows, config, resource, 0.0)
    out: list[float] = []
    for ts in future_times:
        slot_rows = sorted(_slot_rows(rows, ts), key=lambda r: r["timestamp"])  # type: ignore[index]
        values = np.asarray([_target_value(r, config, resource) for r in slot_rows], dtype=float)
        if values.size == 0:
            out.append(default)
            continue
        alpha = 0.35 if values.size >= 5 else 0.55
        smoothed = values[0]
        for value in values[1:]:
            smoothed = alpha * value + (1.0 - alpha) * smoothed
        out.append(float(smoothed))
    return np.asarray(out, dtype=float)


def _hourly_analog_predict(
    rows: Sequence[dict[str, float | datetime]],
    future_times: Sequence[datetime],
    future_weather: Sequence[tuple[float, float, float]],
    config: ForecastConfig,
    resource: str,
) -> np.ndarray:
    default = _median_target(rows, config, resource, 0.0)
    out: list[float] = []
    for ts, weather in zip(future_times, future_weather):
        candidates = _slot_rows(rows, ts)
        scored: list[tuple[float, float]] = []
        target_day_type = 2 if _is_holiday(ts.date(), config.holiday_country, config.holiday_config_path) else 1 if ts.weekday() >= 5 else 0
        for row in candidates:
            rts = row.get("timestamp")
            if not isinstance(rts, datetime) or rts >= ts:
                continue
            row_day_type = 2 if _is_holiday(rts.date(), config.holiday_country, config.holiday_config_path) else 1 if rts.weekday() >= 5 else 0
            recency_days = max((ts - rts).total_seconds() / 86400.0, 0.0)
            temp = _finite_float(row.get("temperature_c"), weather[0])
            ghi = _finite_float(row.get("ghi_wm2"), weather[1])
            wind = _finite_float(row.get("wind_speed_mps"), weather[2])
            weather_distance = abs(temp - weather[0]) / 10.0 + abs(ghi - weather[1]) / 800.0 + abs(wind - weather[2]) / 8.0
            day_penalty = 0.0 if row_day_type == target_day_type else 0.45
            weekday_penalty = 0.0 if rts.weekday() == ts.weekday() else 0.12
            score = weather_distance + day_penalty + weekday_penalty + min(recency_days / 180.0, 1.0)
            scored.append((score, _target_value(row, config, resource)))
        if not scored:
            out.append(default)
            continue
        scored.sort(key=lambda item: item[0])
        top = scored[: min(8, len(scored))]
        weights = np.asarray([1.0 / (0.08 + s) for s, _v in top], dtype=float)
        vals = np.asarray([v for _s, v in top], dtype=float)
        out.append(float(np.sum(weights * vals) / np.sum(weights)))
    return np.asarray(out, dtype=float)


def _algorithm_supported(code: str, kind: str) -> bool:
    return any(info.code == code and kind in info.supports for info in list_forecast_algorithms(kind))


def _predict_algorithm(
    code: str,
    label: str,
    rows_train: list[dict[str, float | datetime]],
    config: ForecastConfig,
    climate: str,
    resource: str,
    future_times: Sequence[datetime],
    future_weather: Sequence[tuple[float, float, float]],
    x_train: np.ndarray | None = None,
    y_train: np.ndarray | None = None,
    x_future: np.ndarray | None = None,
) -> tuple[np.ndarray, bool, str]:
    if not _algorithm_supported(code, config.kind):
        return np.zeros(len(future_times), dtype=float), False, f"算法 {code} 不支持 {config.kind}。"
    if x_train is None or y_train is None:
        _times, x_train, y_train, _weathers = _rows_to_features(rows_train, config, climate, resource)
    if x_future is None:
        x_future, _fw = _future_features(future_times, rows_train, config, climate)
    if y_train.size == 0:
        return np.zeros(len(future_times), dtype=float), False, "训练样本为空。"
    if code == "sklearn_auto":
        for sklearn_code in ("gradient_boosting", "random_forest"):
            values, note = _sklearn_tree_values(sklearn_code, x_train, y_train, x_future)
            if values is not None:
                return values, True, f"默认 scikit-learn 引擎：{forecast_algorithm_label(sklearn_code)}。" + (f" {note}" if note else "")
        return np.zeros(len(future_times), dtype=float), False, "scikit-learn 自动引擎未能完成梯度提升树或随机森林训练。"
    if code in {"ridge", "adaptive_ridge"}:
        return _ridge_values(x_train, y_train, x_future), True, ""
    if code == "huber":
        values, note = _huber_values(x_train, y_train, x_future)
        return values, True, note
    if code == "seasonal_naive":
        return _seasonal_naive_predict(rows_train, future_times, config, resource), True, ""
    if code == "exp_smoothing":
        return _exp_smoothing_predict(rows_train, future_times, config, resource), True, ""
    if code == "hourly_analog":
        return _hourly_analog_predict(rows_train, future_times, future_weather, config, resource), True, ""
    if code in {"random_forest", "gradient_boosting"}:
        values, note = _sklearn_tree_values(code, x_train, y_train, x_future)
        if values is None:
            return np.zeros(len(future_times), dtype=float), False, note
        return values, True, note
    return _ridge_values(x_train, y_train, x_future), True, f"未知算法 {code} 已按岭回归执行。"


def _validation_split(history: list[dict[str, float | datetime]], config: ForecastConfig) -> tuple[list[dict[str, float | datetime]], list[dict[str, float | datetime]]]:
    cfg = load_forecast_builtin_config()
    defaults = cfg.get("defaults", {}) if isinstance(cfg.get("defaults"), dict) else {}
    min_points = int(defaults.get("validation_min_points", max(12, int(config.horizon_hours * 60 / config.interval_minutes))))
    fraction = float(defaults.get("validation_fraction", 0.20))
    n_valid = max(min_points, int(round(len(history) * fraction)))
    n_valid = min(max(n_valid, 12), max(0, len(history) - 24))
    if n_valid < 12:
        return history, []
    return history[:-n_valid], history[-n_valid:]


def _metrics(actual: np.ndarray, predicted: np.ndarray, weight: float = 0.0, code: str = "", label: str = "", available: bool = True, note: str = "") -> ForecastAlgorithmMetric:
    if actual.size == 0 or predicted.size == 0:
        return ForecastAlgorithmMetric(code, label, float("nan"), float("nan"), float("nan"), weight, available, note)
    n = min(actual.size, predicted.size)
    a = actual[:n]
    p = predicted[:n]
    err = p - a
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    denom = np.maximum(np.abs(a), 1.0)
    mape = float(np.mean(np.abs(err) / denom) * 100.0)
    return ForecastAlgorithmMetric(code, label, mae, rmse, mape, weight, available, note)


def _candidate_algorithms(config: ForecastConfig) -> list[str]:
    if config.selected_algorithms:
        return [str(code) for code in config.selected_algorithms]
    cfg = load_forecast_builtin_config()
    defaults = cfg.get("defaults", {}) if isinstance(cfg.get("defaults"), dict) else {}
    fallback_candidates = ["gradient_boosting", "random_forest", "huber", "ridge", "hourly_analog", "exp_smoothing", "seasonal_naive"]
    candidates = defaults.get("ensemble_candidates", fallback_candidates)
    if not isinstance(candidates, list):
        candidates = fallback_candidates
    return [str(code) for code in candidates if str(code) != "adaptive_ensemble"]


def _run_algorithm_suite(
    history: list[dict[str, float | datetime]],
    config: ForecastConfig,
    climate: str,
    resource: str,
    future_times: Sequence[datetime],
    future_weather: Sequence[tuple[float, float, float]],
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_future: np.ndarray,
) -> tuple[np.ndarray, str, tuple[ForecastAlgorithmMetric, ...], np.ndarray, str]:
    requested = (config.algorithm or "adaptive_ensemble").strip()
    catalog = {info.code: info for info in list_forecast_algorithms(config.kind)}
    if requested not in catalog:
        requested = "adaptive_ensemble"
    train_rows, valid_rows = _validation_split(history, config)
    valid_times, _x_valid_rows, y_valid, valid_weather = _rows_to_features(valid_rows, config, climate, resource, history)
    if valid_times:
        _t_train, x_train_valid, y_train_valid, _w = _rows_to_features(train_rows, config, climate, resource)
        x_valid_future = np.asarray([_feature_vector(ts, config, *weather) for ts, weather in zip(valid_times, valid_weather)], dtype=float)
    else:
        x_train_valid, y_train_valid, x_valid_future = x_train, y_train, np.empty((0, x_train.shape[1]), dtype=float)

    def one(code: str) -> _AlgorithmRun:
        info = catalog.get(code) or ForecastAlgorithmInfo(code, code, "", (config.kind,))
        final_values, available, note = _predict_algorithm(code, info.label, history, config, climate, resource, future_times, future_weather, x_train, y_train, x_future)
        if valid_times and available:
            valid_values, valid_available, valid_note = _predict_algorithm(code, info.label, train_rows, config, climate, resource, valid_times, valid_weather, x_train_valid, y_train_valid, x_valid_future)
            available = available and valid_available
            note = "; ".join(part for part in (note, valid_note) if part)
        else:
            valid_values = np.asarray([], dtype=float)
        return _AlgorithmRun(code, info.label, final_values, valid_values, available, note)

    if requested == "adaptive_ensemble":
        runs = [one(code) for code in _candidate_algorithms(config)]
        usable = [run for run in runs if run.available]
        if not usable:
            fallback = one("ridge")
            usable = [fallback]
            runs = [fallback]
        raw_weights: list[float] = []
        for run in usable:
            if valid_times and run.validation.size:
                mae = _metrics(y_valid, run.validation).mae_mw
                if not math.isfinite(mae):
                    mae = float(np.mean(np.maximum(y_train, 1.0))) * 0.1
            else:
                mae = float(np.mean(np.maximum(y_train, 1.0))) * 0.08
            raw_weights.append(1.0 / max(mae, 1e-6) ** 2)
        denom = sum(raw_weights) or 1.0
        weights = [w / denom for w in raw_weights]
        forecast = np.zeros(len(future_times), dtype=float)
        validation = np.zeros(len(valid_times), dtype=float) if valid_times else np.asarray([], dtype=float)
        metrics: list[ForecastAlgorithmMetric] = []
        weight_by_code = {run.code: weight for run, weight in zip(usable, weights)}
        for run in runs:
            weight = weight_by_code.get(run.code, 0.0)
            if run.available and weight > 0:
                forecast += weight * run.values
                if valid_times and run.validation.size:
                    validation += weight * run.validation
            if valid_times and run.validation.size:
                metrics.append(_metrics(y_valid, run.validation, weight, run.code, run.label, run.available, run.note))
            else:
                metrics.append(ForecastAlgorithmMetric(run.code, run.label, float("nan"), float("nan"), float("nan"), weight, run.available, run.note))
        if valid_times:
            metrics.append(_metrics(y_valid, validation, 1.0, "adaptive_ensemble", catalog["adaptive_ensemble"].label, True, "综合预测方案"))
        model_name = "自适应综合方案（" + "，".join(f"{run.label}:{weight_by_code.get(run.code, 0.0):.2f}" for run in usable) + "）"
        residual = y_valid - validation if valid_times and validation.size else y_train - _ridge_values(x_train, y_train, x_train)
        return forecast, model_name, tuple(metrics), residual, requested

    info = catalog[requested]
    forecast, available, note = _predict_algorithm(requested, info.label, history, config, climate, resource, future_times, future_weather, x_train, y_train, x_future)
    if not available:
        forecast = _ridge_values(x_train, y_train, x_future)
        model_name = f"{info.label}不可用，已回退为岭回归"
        residual = y_train - _ridge_values(x_train, y_train, x_train)
        metric = ForecastAlgorithmMetric(requested, info.label, float("nan"), float("nan"), float("nan"), 0.0, False, note)
        return forecast, model_name, (metric,), residual, requested
    if valid_times:
        valid_values, valid_available, valid_note = _predict_algorithm(requested, info.label, train_rows, config, climate, resource, valid_times, valid_weather, x_train_valid, y_train_valid, x_valid_future)
        note = "; ".join(part for part in (note, valid_note) if part)
        residual = y_valid - valid_values
        metric = _metrics(y_valid, valid_values, 1.0, requested, info.label, valid_available, note)
    else:
        fitted = _ridge_values(x_train, y_train, x_train) if requested in {"ridge", "huber", "random_forest", "gradient_boosting"} else forecast[:0]
        residual = y_train - fitted if fitted.size == y_train.size else y_train - _ridge_values(x_train, y_train, x_train)
        metric = ForecastAlgorithmMetric(requested, info.label, float(np.mean(np.abs(residual))) if residual.size else 0.0, float("nan"), float("nan"), 1.0, True, note)
    model_name = info.label + (f"（{note}）" if note else "")
    return forecast, model_name, (metric,), residual, requested


def _apply_renewable_limits(forecast: np.ndarray, future_times: Sequence[datetime], config: ForecastConfig, resource: str) -> np.ndarray:
    values = np.asarray(forecast, dtype=float).copy()
    if config.kind == "renewable" and config.renewable_capacity_mw is not None and config.renewable_capacity_mw > 0:
        values = np.clip(values, 0.0, config.renewable_capacity_mw)
    else:
        values = np.maximum(values, 0.0)
    if resource == "solar":
        for pos, ts in enumerate(future_times):
            if solar_altitude_deg(ts, config.latitude, config.longitude) < 0.0:
                values[pos] = 0.0
    return values


def _solar_physical_correction(
    forecast: np.ndarray,
    future_times: Sequence[datetime],
    future_weather: Sequence[tuple[float, float, float]],
    config: ForecastConfig,
    resource: str,
) -> tuple[np.ndarray, tuple[SolarIrradianceResult, ...]]:
    if config.kind != "renewable" or resource != "solar":
        return np.asarray(forecast, dtype=float), ()
    corrected = np.asarray(forecast, dtype=float).copy()
    irradiance_rows: list[SolarIrradianceResult] = []
    for idx, (ts, weather) in enumerate(zip(future_times, future_weather)):
        temp = weather[0]
        irr = solar_irradiance_on_panel(
            ts, config.latitude, config.longitude, temp,
            config.weather_condition, config.cloud_cover_pct, config.irradiance_adjustment,
            config.pv_tilt_deg, config.pv_azimuth_deg, config.pv_albedo,
            config.pv_temp_coeff_pct_per_c, config.pv_noct_c,
            input_ghi_wm2=None,
        )
        irradiance_rows.append(irr)
        if irr.position.altitude_deg <= 0.0:
            corrected[idx] = 0.0
        else:
            corrected[idx] *= irr.pv_power_factor
    return corrected, tuple(irradiance_rows)


def _parse_event_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return _parse_timestamp(value)
    except ValueError:
        return None


def _active_event_multiplier(ts: datetime, event: dict[str, object]) -> float:
    start = _parse_event_time(event.get("start"))
    end = _parse_event_time(event.get("end"))
    if start is None or end is None:
        return 0.0
    lag = float(event.get("lag_hours", 0.0) or 0.0)
    start = start + timedelta(hours=lag)
    end = end + timedelta(hours=lag)
    if ts < start or ts > end:
        return 0.0
    ramp = max(float(event.get("ramp_hours", 0.0) or 0.0), 0.0)
    if ramp <= 1e-9:
        return 1.0
    ramp_delta = timedelta(hours=ramp)
    if ts < start + ramp_delta:
        return max(0.0, min(1.0, (ts - start).total_seconds() / ramp_delta.total_seconds()))
    if ts > end - ramp_delta:
        return max(0.0, min(1.0, (end - ts).total_seconds() / ramp_delta.total_seconds()))
    return 1.0


def _apply_special_events(values: np.ndarray, times: Sequence[datetime], config: ForecastConfig, resource: str) -> tuple[np.ndarray, list[str]]:
    if not config.use_special_events:
        return values, []
    cfg = load_forecast_builtin_config(config.event_config_path)
    events = cfg.get("special_events", []) if isinstance(cfg, dict) else []
    if not isinstance(events, list):
        return values, []
    adjusted = np.asarray(values, dtype=float).copy()
    applied: list[str] = []
    for event in events:
        if not isinstance(event, dict) or not event.get("enabled", False):
            continue
        if str(event.get("kind", config.kind)) not in {"*", config.kind}:
            continue
        if config.kind == "renewable" and str(event.get("resource", resource)) not in {"*", resource}:
            continue
        delta = float(event.get("adjustment_mw", 0.0) or 0.0)
        rel = float(event.get("relative_adjustment", 0.0) or 0.0)
        any_applied = False
        for idx, ts in enumerate(times):
            factor = _active_event_multiplier(ts, event)
            if factor <= 0.0:
                continue
            adjusted[idx] = max(0.0, adjusted[idx] * (1.0 + rel * factor) + delta * factor)
            any_applied = True
        if any_applied:
            applied.append(str(event.get("name", "特殊事件")))
    return adjusted, applied


def _daily_stats(
    points: Sequence[ForecastPoint],
    capacity: float | None = None,
    interval_minutes: int = 60,
) -> tuple[tuple[str, float], ...]:
    values = np.asarray([p.value_mw for p in points], dtype=float)
    if values.size == 0:
        return ()
    peak = float(np.max(values))
    valley = float(np.min(values))
    avg = float(np.mean(values))
    diff = peak - valley
    load_factor = avg / peak if peak > 1e-9 else 0.0
    ramps = np.diff(values)
    max_up = float(np.max(ramps)) if ramps.size else 0.0
    max_down = float(np.min(ramps)) if ramps.size else 0.0
    energy = float(np.sum(values) * max(interval_minutes, 1) / 60.0)
    stats = [
        ("峰值MW", peak),
        ("谷值MW", valley),
        ("峰谷差MW", diff),
        ("平均MW", avg),
        ("负荷率/容量因子", load_factor),
        ("最大上爬坡MW/点", max_up),
        ("最大下爬坡MW/点", max_down),
        ("日电量/发电量MWh", energy),
    ]
    if capacity is not None and capacity > 0:
        stats.append(("装机利用率", avg / capacity))
    return tuple(stats)


def _interpolate_and_smooth_forecast(forecast: np.ndarray, config: ForecastConfig) -> np.ndarray:
    """Apply sub-hour interpolation and light curve smoothing for high-resolution outputs."""
    values = np.asarray(forecast, dtype=float)
    n = values.size
    if n < 3:
        return values
    interval = max(1, int(config.interval_minutes))
    adjusted = values.copy()

    # For 1–29 minute outputs, use 30-minute anchor points and linearly
    # interpolate back to the user-selected grid.  This avoids stair-step
    # behavior when historical samples are hourly or half-hourly.
    if interval < 30:
        anchor_step = max(1, int(round(30.0 / interval)))
        if anchor_step > 1 and n > anchor_step:
            x = np.arange(n, dtype=float)
            anchors = np.arange(0, n, anchor_step, dtype=int)
            if anchors[-1] != n - 1:
                anchors = np.append(anchors, n - 1)
            interpolated = np.interp(x, anchors.astype(float), adjusted[anchors])
            adjusted = 0.35 * adjusted + 0.65 * interpolated

    # Triangular smoothing keeps day-ahead and renewable curves readable while
    # retaining most of the model signal.  Physical renewable limits are applied
    # again after smoothing in the main workflow.
    window = max(3, int(round(30.0 / interval)) + 1)
    if window % 2 == 0:
        window += 1
    window = min(window, n if n % 2 == 1 else n - 1)
    if window >= 3:
        half = window // 2
        weights = np.asarray([half + 1 - abs(i - half) for i in range(window)], dtype=float)
        weights /= float(np.sum(weights))
        padded = np.pad(adjusted, (half, half), mode="edge")
        smoothed = np.convolve(padded, weights, mode="valid")
        adjusted = 0.25 * values + 0.75 * smoothed
    return np.maximum(adjusted, 0.0)


def forecast_day_ahead(rows: Iterable[dict[str, float | datetime]], config: ForecastConfig) -> ForecastResult:
    history = sorted(list(rows), key=lambda r: r["timestamp"])  # type: ignore[index]
    if len(history) < 48:
        raise ValueError("至少需要 48 个小时历史数据。")
    climate = classify_climate_block(config.latitude, config.longitude, config.altitude_m)
    renewable_resource = _renewable_resource(config) if config.kind == "renewable" else "load"
    _times, x_train, y_train, _train_weather = _rows_to_features(history, config, climate, renewable_resource)
    future_times = _future_grid(config)
    x_future, future_weather = _future_features(future_times, history, config, climate)
    forecast, model_name, metrics, residual, algorithm_code = _run_algorithm_suite(
        history, config, climate, renewable_resource, future_times, future_weather, x_train, y_train, x_future
    )
    forecast, solar_irradiance_rows = _solar_physical_correction(forecast, future_times, future_weather, config, renewable_resource)
    forecast = _apply_renewable_limits(forecast, future_times, config, renewable_resource)
    forecast, applied_events = _apply_special_events(forecast, future_times, config, renewable_resource)
    forecast = _interpolate_and_smooth_forecast(forecast, config)
    forecast = _apply_renewable_limits(forecast, future_times, config, renewable_resource)
    mae = float(np.mean(np.abs(residual))) if residual.size else 0.0
    cfg = load_forecast_builtin_config()
    defaults = cfg.get("defaults", {}) if isinstance(cfg.get("defaults"), dict) else {}
    q = float(defaults.get("confidence_quantile", 0.80))
    q = min(max(q, 0.50), 0.95)
    band = max(float(np.quantile(np.abs(residual), q)) if residual.size else 0.0, 0.03 * float(np.mean(np.maximum(y_train, 1.0))))
    points: list[ForecastPoint] = []
    solar_by_ts = {irr.position.timestamp: irr for irr in solar_irradiance_rows}
    for ts, value, (temp, ghi, wind) in zip(future_times, forecast, future_weather):
        solar_irr = solar_by_ts.get(ts)
        solar_alt = solar_irr.position.altitude_deg if solar_irr is not None else solar_altitude_deg(ts, config.latitude, config.longitude)
        solar_az = solar_irr.position.azimuth_deg if solar_irr is not None else float("nan")
        poa = solar_irr.poa_wm2 if solar_irr is not None else 0.0
        incidence = solar_irr.incidence_angle_deg if solar_irr is not None else float("nan")
        weather_factor = solar_irr.weather_factor if solar_irr is not None else 1.0
        pv_power_factor = solar_irr.pv_power_factor if solar_irr is not None else 1.0
        if solar_irr is not None:
            ghi = solar_irr.corrected_ghi_wm2
        is_solar_night = renewable_resource == "solar" and solar_alt < 0.0
        p10 = max(0.0, float(value - band))
        p90 = float(value + band)
        if is_solar_night:
            value = 0.0
            p10 = 0.0
            p90 = 0.0
        holiday_text = '节假日' if _is_holiday(ts.date(), config.holiday_country, config.holiday_config_path) else '工作日' if ts.weekday() < 5 else '周末'
        resource_text = f"，资源={'光伏' if renewable_resource == 'solar' else '风电'}" if config.kind == "renewable" else ""
        driver = f"星期{ts.weekday()+1}/{holiday_text}，{climate}{resource_text}，T={temp:.1f}℃，GHI={ghi:.0f}W/m2，风={wind:.1f}m/s"
        if solar_irr is not None:
            driver += f"，太阳高={solar_alt:.1f}°，方位={solar_az:.0f}°，POA={poa:.0f}W/m2，入射角={incidence:.1f}°，天气系数={weather_factor:.2f}，光伏修正={pv_power_factor:.2f}"
        if applied_events:
            driver += "，事件修正=" + "/".join(applied_events)
        points.append(ForecastPoint(ts, float(value), p10, p90, temp, ghi, wind, driver, poa, solar_alt, solar_az, incidence, weather_factor, pv_power_factor))
    stats = _daily_stats(
        points,
        config.renewable_capacity_mw if config.kind == "renewable" else None,
        config.interval_minutes,
    )
    notes = [
        f"日前 {config.horizon_hours} 小时、{len(points)} 点预测；时段间隔 {config.interval_minutes} 分钟。",
        "特征已包含小时、星期、节假日、南北半球季节项、经纬度、海拔、太阳高度角、太阳方位角、组件倾斜面辐照度 POA 和气候板块。",
        "缺失气象数据时会优先使用历史同小时/同刻气候值，并用经纬度、海拔和气候板块估算温度/GHI/风速；光伏未来 GHI 会继续叠加用户天气场景修正。",
        "默认引擎为 scikit-learn 自动引擎；本软件强制要求安装 scikit-learn，并优先调用梯度提升树/随机森林。",
        "算法可由用户选择；自适应综合方案会对候选模型做留出校验，并按误差反比分配权重。",
        "1–30 分钟时间颗粒度均支持；高分辨率输出会基于 30 分钟锚点做线性插值，并进行轻量曲线平滑。",
        "新能源预测仅支持风电与光伏两类独立资源；光伏资源已联动太阳位置、天气修正、组件倾角/方位角、POA 辐照度和组件温度系数，夜间仍强制清零。",
        "节假日内置中国和美国；其它国家/地区可通过 data/forecast_holidays.json 或 ForecastConfig.holiday_config_path 扩展。",
        "特殊事件修正可通过 data/forecast_builtin_config.json 开启，支持绝对 MW 和相对比例修正。",
        "可直接导入 CAISO/NYISO/ERCOT/PJM/GEFCom/NREL 风格 CSV；表头会自动映射常见字段，并兼容中文日期/时刻/负荷字段。",
    ]
    return ForecastResult(config.kind, climate, model_name, mae, tuple(points), tuple(notes), metrics, stats, algorithm_code, config.interval_minutes)


def _stat_value(stats: Sequence[tuple[str, float]], name: str, default: float = 0.0) -> float:
    for key, value in stats:
        if key == name:
            return value
    return default


def format_forecast_summary(result: ForecastResult) -> str:
    unit_title = "负荷" if result.kind == "load" else "新能源"
    values = [p.value_mw for p in result.points]
    peak = max(result.points, key=lambda p: p.value_mw)
    valley = min(result.points, key=lambda p: p.value_mw)
    lines = [
        f"══ {unit_title}日前 {len(result.points)} 点预测 ══════════════════════",
        f"模型：{result.model_name}",
        f"气候板块：{result.climate_block}",
        f"留出校验/残差 MAE：{result.metric_mae_mw:.2f} MW",
        f"峰值：{peak.value_mw:.1f} MW @ {peak.timestamp:%Y-%m-%d %H:%M}",
        f"谷值：{valley.value_mw:.1f} MW @ {valley.timestamp:%Y-%m-%d %H:%M}",
        f"峰谷差：{_stat_value(result.daily_stats, '峰谷差MW'):.1f} MW；负荷率/容量因子：{_stat_value(result.daily_stats, '负荷率/容量因子'):.3f}",
        f"日电量/发电量：{sum(values) * result.interval_minutes / 60.0:.1f} MWh",
        "",
    ]
    if result.algorithm_metrics:
        lines.append("── 算法校验与权重 ─────────────────────────────")
        lines.append("算法                     权重      MAE/MW    RMSE/MW   MAPE/%   状态")
        for m in result.algorithm_metrics:
            mae = "-" if not math.isfinite(m.mae_mw) else f"{m.mae_mw:.2f}"
            rmse = "-" if not math.isfinite(m.rmse_mw) else f"{m.rmse_mw:.2f}"
            mape = "-" if not math.isfinite(m.mape_pct) else f"{m.mape_pct:.2f}"
            status = "可用" if m.available else "不可用"
            if m.note:
                status += f"；{m.note}"
            lines.append(f"{m.label:<22} {m.weight:7.3f}  {mae:>8}  {rmse:>8}  {mape:>7}  {status}")
        lines.append("")
    lines.extend(["小时                  P10      预测      P90      调度提示"])
    for p in result.points:
        lines.append(f"{p.timestamp:%Y-%m-%d %H:%M}  {p.p10_mw:8.1f}  {p.value_mw:8.1f}  {p.p90_mw:8.1f}  {p.drivers}")
    lines.extend(["", "── 日特性摘要 ───────────────────────────────"])
    for name, value in result.daily_stats:
        if "率" in name or "因子" in name:
            lines.append(f"{name}: {value:.4f}")
        else:
            lines.append(f"{name}: {value:.2f}")
    lines.extend(["", "说明：", *[f"- {note}" for note in result.notes]])
    return "\n".join(lines)


def forecast_result_to_dict(result: ForecastResult) -> dict[str, object]:
    return {
        "kind": result.kind,
        "climate_block": result.climate_block,
        "model_name": result.model_name,
        "algorithm_code": result.algorithm_code,
        "metric_mae_mw": result.metric_mae_mw,
        "interval_minutes": result.interval_minutes,
        "daily_stats": {key: value for key, value in result.daily_stats},
        "algorithm_metrics": [
            {
                "code": m.code,
                "label": m.label,
                "mae_mw": m.mae_mw,
                "rmse_mw": m.rmse_mw,
                "mape_pct": m.mape_pct,
                "weight": m.weight,
                "available": m.available,
                "note": m.note,
            }
            for m in result.algorithm_metrics
        ],
        "points": [
            {
                "timestamp": p.timestamp.isoformat(sep=" "),
                "value_mw": p.value_mw,
                "p10_mw": p.p10_mw,
                "p90_mw": p.p90_mw,
                "temperature_c": p.temperature_c,
                "ghi_wm2": p.ghi_wm2,
                "wind_speed_mps": p.wind_speed_mps,
                "poa_wm2": p.poa_wm2,
                "solar_altitude_deg": p.solar_altitude_deg,
                "solar_azimuth_deg": p.solar_azimuth_deg,
                "incidence_angle_deg": p.incidence_angle_deg,
                "weather_factor": p.weather_factor,
                "pv_power_factor": p.pv_power_factor,
                "drivers": p.drivers,
            }
            for p in result.points
        ],
        "notes": list(result.notes),
    }


def export_forecast_result_json(result: ForecastResult, path: str | Path) -> Path:
    target = Path(path)
    target.write_text(json.dumps(forecast_result_to_dict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def export_forecast_result_csv(result: ForecastResult, path: str | Path) -> Path:
    target = Path(path)
    with target.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "value_mw", "p10_mw", "p90_mw", "temperature_c", "ghi_wm2", "poa_wm2", "solar_altitude_deg", "solar_azimuth_deg", "incidence_angle_deg", "weather_factor", "pv_power_factor", "wind_speed_mps", "drivers"])
        for p in result.points:
            writer.writerow([p.timestamp.isoformat(sep=" "), f"{p.value_mw:.6g}", f"{p.p10_mw:.6g}", f"{p.p90_mw:.6g}", f"{p.temperature_c:.6g}", f"{p.ghi_wm2:.6g}", f"{p.poa_wm2:.6g}", f"{p.solar_altitude_deg:.6g}", f"{p.solar_azimuth_deg:.6g}", f"{p.incidence_angle_deg:.6g}", f"{p.weather_factor:.6g}", f"{p.pv_power_factor:.6g}", f"{p.wind_speed_mps:.6g}", p.drivers])
    return target

ANNUAL_LOAD_SAMPLE_PATH = Path(__file__).resolve().parent / "data" / "annual_load_forecast_sample.json"


@dataclass(frozen=True)
class AnnualLoadHistoryPoint:
    year: int
    energy_gwh: float
    max_load_mw: float
    gdp_billion: float
    population_million: float
    primary_gdp_billion: float = 0.0
    secondary_gdp_billion: float = 0.0
    tertiary_gdp_billion: float = 0.0


@dataclass(frozen=True)
class AnnualLoadForecastConfig:
    horizon_years: int = 10
    latitude: float = NANJING_LATITUDE
    longitude: float = NANJING_LONGITUDE
    climate_block: str = ""
    algorithm: str = "综合法"
    gdp_growth_pct: float = 5.0
    population_growth_pct: float = 1.0
    primary_growth_pct: float = 2.0
    secondary_growth_pct: float = 4.0
    tertiary_growth_pct: float = 6.0
    coincidence_factor: float = 0.92
    dual_carbon_factor_pct: float = -0.8
    electrification_factor_pct: float = 1.5


@dataclass(frozen=True)
class AnnualLoadForecastYear:
    year: int
    energy_gwh: float
    max_load_mw: float
    p10_energy_gwh: float
    p90_energy_gwh: float
    p10_max_load_mw: float
    p90_max_load_mw: float
    load_factor: float


@dataclass(frozen=True)
class SeasonalLoadShape:
    season: str
    values_mw: tuple[float, ...]


@dataclass(frozen=True)
class AnnualLoadForecastResult:
    region: str
    source: str
    climate_block: str
    algorithm: str
    base_year: int
    base_max_load_mw: float
    years: tuple[AnnualLoadForecastYear, ...]
    seasonal_shapes: tuple[SeasonalLoadShape, ...]
    notes: tuple[str, ...]


def load_annual_load_sample(path: str | Path | None = None) -> dict[str, object]:
    """Load the built-in annual planning sample dataset."""
    target = Path(path) if path is not None else ANNUAL_LOAD_SAMPLE_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def _annual_history_from_dataset(dataset: dict[str, object]) -> list[AnnualLoadHistoryPoint]:
    rows: list[AnnualLoadHistoryPoint] = []
    for raw in dataset.get("history", []):
        if not isinstance(raw, dict):
            continue
        rows.append(AnnualLoadHistoryPoint(
            year=int(raw["year"]),
            energy_gwh=float(raw["energy_gwh"]),
            max_load_mw=float(raw["max_load_mw"]),
            gdp_billion=float(raw.get("gdp_billion", 0.0)),
            population_million=float(raw.get("population_million", 0.0)),
            primary_gdp_billion=float(raw.get("primary_gdp_billion", 0.0)),
            secondary_gdp_billion=float(raw.get("secondary_gdp_billion", 0.0)),
            tertiary_gdp_billion=float(raw.get("tertiary_gdp_billion", 0.0)),
        ))
    rows.sort(key=lambda p: p.year)
    return rows


def _cagr(first: float, last: float, periods: int) -> float:
    if first <= 0 or last <= 0 or periods <= 0:
        return 0.0
    return (last / first) ** (1.0 / periods) - 1.0


def _linear_forecast(years: np.ndarray, values: np.ndarray, future_years: np.ndarray) -> np.ndarray:
    if len(values) < 2:
        return np.full(len(future_years), float(values[-1]) if len(values) else 0.0)
    coef = np.polyfit(years.astype(float), values.astype(float), 1)
    predicted = np.polyval(coef, future_years.astype(float))
    return np.maximum(predicted, values[-1] * 0.50)


def forecast_annual_load(dataset: dict[str, object], config: AnnualLoadForecastConfig) -> AnnualLoadForecastResult:
    """Forecast annual electricity use and coincident maximum load for grid planning."""
    horizon = max(5, min(20, int(config.horizon_years)))
    history = _annual_history_from_dataset(dataset)
    if len(history) < 2:
        raise ValueError("年度负荷预测至少需要两年历史电量与最大负荷数据。")

    base = history[-1]
    hist_years = np.asarray([p.year for p in history], dtype=float)
    hist_energy = np.asarray([p.energy_gwh for p in history], dtype=float)
    hist_peak = np.asarray([p.max_load_mw for p in history], dtype=float)
    future_years = np.arange(base.year + 1, base.year + horizon + 1, dtype=int)

    # 1) 趋势外推法：历史线性趋势与 CAGR 折中，避免单一年份波动支配长期结果。
    trend_linear = _linear_forecast(hist_years, hist_energy, future_years.astype(float))
    energy_cagr = _cagr(hist_energy[0], hist_energy[-1], len(hist_energy) - 1)
    trend_cagr = np.asarray([base.energy_gwh * (1.0 + energy_cagr) ** i for i in range(1, horizon + 1)], dtype=float)
    trend_energy = 0.55 * trend_cagr + 0.45 * trend_linear

    # 2) 弹性系数法：由历史电量/GDP 弹性估计，并允许分产业、人口输入修正。
    gdp_cagr = _cagr(history[0].gdp_billion, base.gdp_billion, len(history) - 1)
    elasticity = (energy_cagr / gdp_cagr) if gdp_cagr > 1e-6 else 0.85
    elasticity = float(min(1.35, max(0.45, elasticity)))
    sector_mix_growth = (
        0.08 * config.primary_growth_pct + 0.58 * config.secondary_growth_pct + 0.34 * config.tertiary_growth_pct
    ) / 100.0
    macro_growth = 0.65 * config.gdp_growth_pct / 100.0 + 0.20 * sector_mix_growth + 0.15 * config.population_growth_pct / 100.0
    policy_growth = (config.dual_carbon_factor_pct + config.electrification_factor_pct) / 100.0
    elasticity_growth = max(-0.02, elasticity * macro_growth + policy_growth)
    elasticity_energy = np.asarray([base.energy_gwh * (1.0 + elasticity_growth) ** i for i in range(1, horizon + 1)], dtype=float)

    # 3) 综合法：长期规划推荐，以趋势稳态、宏观弹性、政策修正加权。
    algorithm = config.algorithm.strip() or "综合法"
    if "趋势" in algorithm:
        energy = trend_energy
        method_note = "趋势外推法：历史 CAGR 与线性趋势折中。"
    elif "弹性" in algorithm:
        energy = elasticity_energy
        method_note = "弹性系数法：GDP/人口/分产业增长与历史电量弹性联动。"
    else:
        energy = 0.45 * trend_energy + 0.55 * elasticity_energy
        method_note = "综合法：趋势外推、弹性系数、双碳与再电气化政策修正加权。"

    peak_cagr = _cagr(hist_peak[0], hist_peak[-1], len(hist_peak) - 1)
    avg_load_base = base.energy_gwh * 1000.0 / 8760.0
    load_factor_base = avg_load_base / max(base.max_load_mw, 1e-6)
    climate = config.climate_block or str(dataset.get("climate_block") or classify_climate_block(config.latitude, config.longitude, NANJING_ALTITUDE_M))
    hot_summer = any(token in climate for token in ("夏热", "华东", "华南", "湿润", "亚热带"))
    climate_peak_adder = 0.010 if hot_summer else 0.004
    peak_growth = 0.58 * peak_cagr + 0.42 * elasticity_growth + climate_peak_adder
    peak_growth += max(0.0, 0.96 - config.coincidence_factor) * 0.010

    years: list[AnnualLoadForecastYear] = []
    for idx, (yr, e) in enumerate(zip(future_years, energy), start=1):
        lf = min(0.72, max(0.45, load_factor_base - 0.0025 * idx + 0.001 * (config.dual_carbon_factor_pct < 0)))
        peak_from_energy = e * 1000.0 / (8760.0 * lf)
        peak_from_growth = base.max_load_mw * (1.0 + peak_growth) ** idx
        peak = (0.62 * peak_from_energy + 0.38 * peak_from_growth) * max(0.70, min(1.05, config.coincidence_factor / 0.92))
        spread = 0.055 + 0.006 * idx
        years.append(AnnualLoadForecastYear(
            year=int(yr),
            energy_gwh=float(e),
            max_load_mw=float(peak),
            p10_energy_gwh=float(e * (1.0 - spread)),
            p90_energy_gwh=float(e * (1.0 + spread)),
            p10_max_load_mw=float(peak * (1.0 - spread * 1.1)),
            p90_max_load_mw=float(peak * (1.0 + spread * 1.1)),
            load_factor=float(lf),
        ))

    final_peak = years[-1].max_load_mw
    season_profiles = {
        "春季": [0.62,0.58,0.55,0.54,0.56,0.62,0.72,0.80,0.84,0.83,0.80,0.79,0.78,0.79,0.82,0.86,0.90,0.94,0.96,0.92,0.84,0.76,0.70,0.65],
        "夏季": [0.70,0.66,0.63,0.62,0.64,0.70,0.80,0.88,0.92,0.94,0.96,0.98,0.97,0.96,0.98,1.00,0.99,0.98,0.97,0.94,0.88,0.82,0.78,0.73],
        "秋季": [0.60,0.56,0.54,0.53,0.55,0.61,0.71,0.79,0.83,0.82,0.79,0.78,0.77,0.78,0.81,0.85,0.89,0.92,0.93,0.89,0.82,0.74,0.68,0.63],
        "冬季": [0.68,0.64,0.61,0.60,0.62,0.70,0.82,0.90,0.93,0.92,0.88,0.84,0.82,0.83,0.86,0.90,0.95,0.98,0.99,0.94,0.87,0.80,0.75,0.71],
    }
    if not hot_summer:
        season_profiles["冬季"], season_profiles["夏季"] = season_profiles["夏季"], season_profiles["冬季"]
    shapes = tuple(SeasonalLoadShape(season, tuple(final_peak * v for v in profile)) for season, profile in season_profiles.items())
    notes = (
        f"样例来源：{dataset.get('source', '内置数据集')}；本功能面向规划，不包含空间负荷预测。",
        method_note,
        "输入考虑历史负荷、经纬度/气候板块、GDP/人口及分产业增长、负荷同时率、双碳目标与再电气化政策。",
        "P10/P90 为规划不确定性带，年限越远区间越宽；结果宜结合用户报装、产业项目清单和地方能源规划校核。",
    )
    return AnnualLoadForecastResult(
        region=str(dataset.get("region", "规划区域")),
        source=str(dataset.get("source", "内置年度负荷规划样例")),
        climate_block=climate,
        algorithm=algorithm,
        base_year=base.year,
        base_max_load_mw=base.max_load_mw,
        years=tuple(years),
        seasonal_shapes=shapes,
        notes=notes,
    )


def annual_seasonal_shapes_for_year(result: AnnualLoadForecastResult, year: int | float) -> tuple[SeasonalLoadShape, ...]:
    """Return seasonal 24-hour shapes scaled to a selected planning year."""
    if not result.seasonal_shapes:
        return ()
    selected_year = int(round(float(year)))
    year_axis = [result.base_year, *[row.year for row in result.years]]
    peak_axis = [result.base_max_load_mw, *[row.max_load_mw for row in result.years]]
    if not year_axis or not peak_axis:
        return result.seasonal_shapes
    selected_year = max(min(selected_year, max(year_axis)), min(year_axis))
    selected_peak = float(np.interp(selected_year, year_axis, peak_axis))
    final_peak = max(float(result.years[-1].max_load_mw if result.years else peak_axis[-1]), 1e-9)
    scale = selected_peak / final_peak
    return tuple(SeasonalLoadShape(shape.season, tuple(float(v) * scale for v in shape.values_mw)) for shape in result.seasonal_shapes)


def format_annual_load_forecast_summary(result: AnnualLoadForecastResult) -> str:
    lines = [
        "══ 年度负荷预测（规划用） ═════════════════════",
        f"区域：{result.region}",
        f"气候板块：{result.climate_block}",
        f"基准年：{result.base_year}；方法：{result.algorithm}",
        "",
        "年份      电量/GWh       P10-P90/GWh       最大负荷/MW       P10-P90/MW     负荷率",
    ]
    for row in result.years:
        lines.append(
            f"{row.year:<6d} {row.energy_gwh:10.1f}  {row.p10_energy_gwh:8.1f}-{row.p90_energy_gwh:<8.1f}"
            f" {row.max_load_mw:12.1f}  {row.p10_max_load_mw:8.1f}-{row.p90_max_load_mw:<8.1f} {row.load_factor:7.3f}"
        )
    lines.extend(["", "典型负荷形态：右侧曲线展示最终规划年春/夏/秋/冬 24 小时典型日形态。", "", "说明："])
    lines.extend([f"- {note}" for note in result.notes])
    return "\n".join(lines)
