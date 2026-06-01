# 新能源预测

新能源预测页用于做 24 小时日前新能源出力估计，适合对光伏、风电或聚合新能源曲线进行快速校核。

## 数据

- 内置 `CAISO_RENEWABLE_SAMPLE` 与 `NREL_SOLAR_WIND_SAMPLE` 两个离线演示数据集。
- CSV 可包含 `solar_mw`、`wind_mw`、`renewable_mw`、`ghi_wm2`、`wind_speed_mps`、`temperature_c` 等字段。
- 若没有 `renewable_mw`，程序会将 `solar_mw + wind_mw` 作为聚合新能源出力。

## 方法

模型考虑日期、小时、南北半球季节、经纬度、海拔和气候板块，并结合 GHI 与风速小时型。可输入装机容量上限，预测值会裁剪到 `[0, 装机容量]` 区间。

该页适合调度员快速查看日间光伏峰值、夜间风电贡献、峰谷时段以及 P10-P90 风险带；正式出清和安全校核应使用完整气象预报与调度主站模型。
