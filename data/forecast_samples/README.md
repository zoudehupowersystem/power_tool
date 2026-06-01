# Forecast sample datasets

These compact CSV files are bundled for offline demonstrations and automated tests. They intentionally use common columns found in ISO/RTO and forecasting-competition exports (`timestamp`, `load_mw`, `solar_mw`, `wind_mw`, `renewable_mw`, `temperature_c`, `ghi_wm2`, and `wind_speed_mps`).

The samples are small synthetic training slices shaped after public data schemas rather than complete operational records. Operators should replace them with actual CAISO OASIS, ERCOT, NYISO, PJM, NREL NSRDB/wind-toolkit, or GEFCom files for production studies.

When weather fields are missing, the tool infers temperature, GHI, and wind speed from historical same-hour medians and geography/climate baselines. Solar/PV forecasts apply a hard post-processing rule that sets output to zero whenever the solar altitude angle is below 0 degrees. Holiday calendars are built in for `US` and `CN`; edit `../forecast_holidays.json` or pass a custom `ForecastConfig.holiday_config_path` for other countries.

Reference entry points used when designing the supported schema aliases:

- CAISO OASIS and Today's Outlook demand / wind / solar exports: <https://oasis.caiso.com/> and <https://www.caiso.com/todays-outlook>
- ERCOT hourly load archives: <https://www.ercot.com/gridinfo/load/load_hist/>
- NREL/NLR solar resource API fields such as latitude, longitude, average GHI and DNI: <https://developer.nrel.gov/docs/solar/solar-resource-v1/>
- GEFCom load, wind and solar forecasting competition files: <https://ieee-pes-data-sharing.org/>

See `dataset_catalog.json` for per-file reference metadata.
