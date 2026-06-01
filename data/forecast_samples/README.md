# Forecast sample datasets

These compact CSV files are bundled for offline demonstrations and automated tests. They intentionally use common columns found in ISO/RTO, Chinese public/competition, and forecasting-competition exports (`timestamp`, `load_mw`, `solar_mw`, `wind_mw`, `temperature_c`, `ghi_wm2`, `wind_speed_mps`, plus aliases such as `日期`, `时刻`, `统调负荷`, `Wspd`, and `Patv`).

The samples are small synthetic training slices shaped after public data schemas rather than complete operational records. Operators can replace them with actual CAISO OASIS, ERCOT, NYISO, PJM, NREL NSRDB/wind-toolkit, GEFCom, Baidu KDD Cup 2022/SDWPF, Southern Grid load-forecasting, or 电工杯-style files.

When weather fields are missing, the tool infers temperature, GHI, and wind speed from historical same-hour medians and geography/climate baselines. Renewable forecasts are run as independent `solar` or `wind` jobs, not as an aggregate renewable target. Solar/PV forecasts apply a hard post-processing rule that sets output to zero whenever the solar altitude angle is below 0 degrees. Holiday calendars are built in for `US` and `CN`; edit `../forecast_holidays.json` or pass a custom `ForecastConfig.holiday_config_path` for other countries.

Reference entry points used when designing the supported schema aliases:

- CAISO OASIS and Today's Outlook demand / wind / solar exports: <https://oasis.caiso.com/> and <https://www.caiso.com/todays-outlook>
- ERCOT hourly load archives: <https://www.ercot.com/gridinfo/load/load_hist/>
- NREL/NLR solar resource API fields such as latitude, longitude, average GHI and DNI: <https://developer.nrel.gov/docs/solar/solar-resource-v1/>
- GEFCom load, wind and solar forecasting competition files: <https://ieee-pes-data-sharing.org/>
- Baidu KDD Cup 2022 / SDWPF wind forecasting data schema: <https://baidukddcup2022.github.io/> and the SDWPF paper.
- Southern Grid load-forecasting dataset publication: <https://www.nda.gov.cn/sjj/ywpd/szkjyjcss/0926/20250926161610699430676_pc.html>
- 电工杯 load-forecasting schema references found during research were primarily third-party mirrors; the included file is therefore a parser-compatible schema sample, not a mirrored official dataset.

See `dataset_catalog.json` for per-file reference metadata.
