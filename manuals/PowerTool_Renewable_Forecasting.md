# Renewable Forecasting

The renewable forecasting page estimates a 24-hour day-ahead renewable output curve for exactly one selected resource type: PV/solar or wind.

## Data

- Bundled offline examples/schema samples: `CAISO_RENEWABLE_SAMPLE`, `NREL_SOLAR_WIND_SAMPLE`, and `BAIDU_KDD_SDWPF_WIND_SAMPLE`.
- CSV imports may include `solar_mw`, `wind_mw`, `ghi_wm2`, `wind_speed_mps`, `temperature_c`, `Wspd`, and `Patv`.
- Select `solar` or `wind` in the resource-type field; the tool models the selected `solar_mw` or `wind_mw` column independently and no longer produces aggregate renewable forecasts.

## Method

The model uses the mandatory scikit-learn forecasting engine together with date, hour, hemisphere-aware season, latitude, longitude, altitude, an automatically inferred climate block, GHI, and wind-speed patterns. Missing weather is inferred from historical same-hour patterns and geography/climate baselines. If a capacity limit is entered, forecasts are clipped to `[0, capacity]`. For solar/PV resources, post-processing enforces zero output whenever the solar altitude angle is below 0°, instead of relying on the model to learn sunset behavior. Built-in holidays cover China (CN) and the United States (US); other calendars can be added through `data/forecast_holidays.json` or a configured calendar path.

The page reports solar peaks, overnight wind contribution, ramps, and P10-P90 risk bands for the selected wind or solar resource.

## Solar-position, weather and PV-array correction

The renewable forecasting page now includes a solar-position helper. The default site is Nanjing, China (32.0603°N, 118.7969°E). The left parameter area sets sky condition, cloud cover, irradiance multiplier, PV tilt, PV azimuth, albedo and module temperature coefficient. The analysis time is located in the lower-right control area of the Solar Position / Track tab: it can be typed directly, selected with the sunrise-to-sunset slider, or adjusted by dragging inside the solar-altitude chart. The tool computes solar altitude, azimuth, weather-corrected GHI, plane-of-array irradiance, incidence angle and a relative PV power correction factor.

Solar forecasting is linked to these quantities. Solar altitude, azimuth, POA irradiance, incidence-angle cosine, PV tilt and PV azimuth are included in the feature vector, and the final PV forecast is physically adjusted by weather, array geometry and module-temperature coefficient. Irradiance units in plots and tables use W/m2 to avoid missing superscript glyphs on some systems. Azimuth convention: 0° north, 90° east, 180° south, 270° west.
