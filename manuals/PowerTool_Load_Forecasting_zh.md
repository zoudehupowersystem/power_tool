# 负荷预测

负荷预测页用于做 24 小时日前负荷曲线估计，面向调度员快速校核次日峰谷、日电量和不确定性区间。

## 数据

- 内置 `CAISO_LOAD_SAMPLE`、`ERCOT_LOAD_SAMPLE`、`GEFCOM_LOAD_SAMPLE`、`CSG_LOAD_FORECAST_SCHEMA_SAMPLE`、`ELECTRICIAN_CUP_LOAD_SCHEMA_SAMPLE` 等离线演示/格式样例。
- 也可导入 CSV，常见表头会自动识别：`timestamp` / `time` / `datetime`、`load_mw` / `demand_mw` / `SYS_FCST_ACT_MW` / `total_load`、`temperature_c`、`日期`、`时刻`、`统调负荷`、`负荷`、`温度` 等。
- 内置数据是小型演示样例，生产分析应替换为 ISO/RTO 或企业历史负荷、天气和节假日数据。

## 方法

模型对每个小时构造以下调度友好特征：

- 小时、星期几、周末、美国固定节假日与典型移动节假日。
- 南北半球季节项，避免将北半球夏季模式直接套用到南半球。
- 经纬度、海拔高度和自动气候板块；平原可将海拔填 0。
- 温度、温度二次项，用于反映制冷/采暖负荷敏感性。
- 气象数据缺失时，先用历史同小时中位数，再用经纬度、海拔和气候板块估算温度/GHI/风速。
- 节假日内置中国（CN）和美国（US），其它国家/地区可编辑 `data/forecast_holidays.json` 或通过配置路径扩展。

若本地安装了 scikit-learn，则使用 HuberRegressor；否则使用内置岭回归。结果包括 P10-P90 经验残差带，便于调度员做备用和风险提示。
