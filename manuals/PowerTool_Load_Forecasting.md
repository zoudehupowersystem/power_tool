# Load Forecasting

The load forecasting page estimates a 24-hour day-ahead load curve for dispatcher screening of next-day peaks, valleys, daily energy, and uncertainty bands.

## Data

- Bundled offline examples: `CAISO_LOAD_SAMPLE`, `ERCOT_LOAD_SAMPLE`, and `GEFCOM_LOAD_SAMPLE`.
- CSV import recognizes common headers such as `timestamp` / `time` / `datetime`, `load_mw` / `demand_mw` / `SYS_FCST_ACT_MW` / `total_load`, and `temperature_c`.
- Bundled data are compact demonstration samples. Production studies should use ISO/RTO or utility historical load, weather, and holiday data.

## Method

The model builds dispatcher-readable hourly features:

- Hour, weekday, weekend, and selected U.S. holidays.
- Hemisphere-aware season terms.
- Latitude, longitude, altitude, and an automatic climate block.
- Temperature and a quadratic temperature term for cooling/heating sensitivity.

If scikit-learn is installed, HuberRegressor is used; otherwise the built-in ridge regression fallback is used. The output includes an empirical P10-P90 residual band.
