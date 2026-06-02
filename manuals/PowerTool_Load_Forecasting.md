# Day-Ahead / Annual Load Forecasting

Load forecasting now has two tabs: **Day-Ahead Load Forecasting** for dispatch-oriented 24-hour or 96-point curves, and **Annual Load Forecasting** for 5–20 year grid-planning forecasts without spatial load forecasting.

## Day-Ahead Load Forecasting

The day-ahead load forecasting page estimates a 24-hour load curve and reports next-day peaks, valleys, daily energy, and uncertainty bands. The default resolution is 15 minutes, and users can set any integer interval from 1 to 30 minutes.

### Data

- Bundled offline examples/schema samples: `CAISO_LOAD_SAMPLE`, `ERCOT_LOAD_SAMPLE`, `GEFCOM_LOAD_SAMPLE`, `CSG_LOAD_FORECAST_SCHEMA_SAMPLE`, and `ELECTRICIAN_CUP_LOAD_SCHEMA_SAMPLE`.
- CSV import recognizes common headers such as `timestamp` / `time` / `datetime`, `load_mw` / `demand_mw` / `SYS_FCST_ACT_MW` / `total_load`, `temperature_c`, `日期`, `时刻`, `统调负荷`, `负荷`, and `温度`.
- Bundled data are compact demonstration samples. Production studies should use ISO/RTO or utility historical load, weather, and holiday data.

### Method

The model builds dispatcher-readable hourly features:

- Hour, weekday, weekend, and selected U.S. holidays.
- Hemisphere-aware season terms.
- Latitude, longitude, altitude, and an automatic climate block.
- Temperature and a quadratic temperature term for cooling/heating sensitivity.
- Missing weather is inferred from historical same-hour medians first, then from latitude, longitude, altitude, and climate block baselines.
- Built-in holidays cover China (CN) and the United States (US); other countries can be added through `data/forecast_holidays.json` or a configured calendar path.

The default engine is the scikit-learn automatic engine. The application requires scikit-learn and prefers gradient boosting / random forest models. The output includes an empirical P10-P90 residual band. High-resolution 1–30 minute outputs use 30-minute anchor interpolation plus light curve smoothing.

## Annual Load Forecasting

The annual load forecasting tab supports planning forecasts for future horizons from 5 to 20 years.

### Inputs

- Historical annual energy and maximum-load data, with a bundled hypothetical `data/annual_load_forecast_sample.json` Jiangnan New District sample.
- Latitude, longitude, and climate block.
- GDP, population, and primary/secondary/tertiary industry growth rates.
- Load coincidence factor.
- Policy adjustments such as dual-carbon targets and re-electrification.

### Methods and outputs

Selectable methods include trend extrapolation, elasticity coefficient, and a composite method. Outputs include annual energy in GWh, maximum load in MW, P10-P90 planning uncertainty bands, load factor, and spring/summer/autumn/winter 24-hour typical load-shape curves.
