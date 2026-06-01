# Load Forecasting

The load forecasting page estimates a 24-hour day-ahead load curve and reports next-day peaks, valleys, daily energy, and uncertainty bands.

## Data

- Bundled offline examples/schema samples: `CAISO_LOAD_SAMPLE`, `ERCOT_LOAD_SAMPLE`, `GEFCOM_LOAD_SAMPLE`, `CSG_LOAD_FORECAST_SCHEMA_SAMPLE`, and `ELECTRICIAN_CUP_LOAD_SCHEMA_SAMPLE`.
- CSV import recognizes common headers such as `timestamp` / `time` / `datetime`, `load_mw` / `demand_mw` / `SYS_FCST_ACT_MW` / `total_load`, `temperature_c`, `日期`, `时刻`, `统调负荷`, `负荷`, and `温度`.
- Bundled data are compact demonstration samples. Production studies should use ISO/RTO or utility historical load, weather, and holiday data.

## Method

The model builds dispatcher-readable hourly features:

- Hour, weekday, weekend, and selected U.S. holidays.
- Hemisphere-aware season terms.
- Latitude, longitude, altitude, and an automatic climate block.
- Temperature and a quadratic temperature term for cooling/heating sensitivity.
- Missing weather is inferred from historical same-hour medians first, then from latitude, longitude, altitude, and climate block baselines.
- Built-in holidays cover China (CN) and the United States (US); other countries can be added through `data/forecast_holidays.json` or a configured calendar path.

If scikit-learn is installed, HuberRegressor is used; otherwise the built-in ridge regression fallback is used. The output includes an empirical P10-P90 residual band.
