# Renewable Forecasting

The renewable forecasting page estimates a 24-hour day-ahead renewable output curve for exactly one selected resource type: PV/solar or wind.

## Data

- Bundled offline examples: `CAISO_RENEWABLE_SAMPLE` and `NREL_SOLAR_WIND_SAMPLE`.
- CSV imports may include `solar_mw`, `wind_mw`, `ghi_wm2`, `wind_speed_mps`, and `temperature_c`.
- Select `solar` or `wind` in the resource-type field; the tool models the selected `solar_mw` or `wind_mw` column independently and no longer produces aggregate renewable forecasts.

## Method

The model uses date, hour, hemisphere-aware season, latitude, longitude, altitude, an automatically inferred climate block, GHI, and wind-speed patterns. Missing weather is inferred from historical same-hour patterns and geography/climate baselines. If a capacity limit is entered, forecasts are clipped to `[0, capacity]`. For solar/PV resources, post-processing enforces zero output whenever the solar altitude angle is below 0°, instead of relying on the model to learn sunset behavior. Built-in holidays cover China (CN) and the United States (US); other calendars can be added through `data/forecast_holidays.json` or a configured calendar path.

The page is intended for dispatcher screening of solar peaks, overnight wind contribution, ramps, and P10-P90 risk bands. Production market clearing and security studies should use complete weather forecasts and the control-center forecasting model.
