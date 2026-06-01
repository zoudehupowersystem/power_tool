# Renewable Forecasting

The renewable forecasting page estimates a 24-hour day-ahead renewable output curve for quick screening of PV, wind, or aggregate renewable production.

## Data

- Bundled offline examples: `CAISO_RENEWABLE_SAMPLE` and `NREL_SOLAR_WIND_SAMPLE`.
- CSV imports may include `solar_mw`, `wind_mw`, `renewable_mw`, `ghi_wm2`, `wind_speed_mps`, and `temperature_c`.
- If `renewable_mw` is absent, the tool uses `solar_mw + wind_mw` as aggregate renewable output.

## Method

The model uses date, hour, hemisphere-aware season, latitude, longitude, altitude, climate block, GHI, and wind-speed patterns. Missing weather is inferred from historical same-hour patterns and geography/climate baselines. If a capacity limit is entered, forecasts are clipped to `[0, capacity]`. For solar/PV resources, post-processing enforces zero output whenever the solar altitude angle is below 0°, instead of relying on the model to learn sunset behavior. Built-in holidays cover China (CN) and the United States (US); other calendars can be added through `data/forecast_holidays.json` or a configured calendar path.

The page is intended for dispatcher screening of solar peaks, overnight wind contribution, ramps, and P10-P90 risk bands. Production market clearing and security studies should use complete weather forecasts and the control-center forecasting model.
