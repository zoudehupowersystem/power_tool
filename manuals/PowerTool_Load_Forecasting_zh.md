# 负荷预测

负荷预测页用于做 24 小时日前负荷曲线估计，面向调度员快速校核次日峰谷、日电量和不确定性区间。

## 数据

- 内置 `CAISO_LOAD_SAMPLE`、`ERCOT_LOAD_SAMPLE`、`GEFCOM_LOAD_SAMPLE` 三个离线演示数据集。
- 也可导入 CSV，常见表头会自动识别：`timestamp` / `time` / `datetime`、`load_mw` / `demand_mw` / `SYS_FCST_ACT_MW` / `total_load`、`temperature_c` 等。
- 内置数据是小型演示样例，生产分析应替换为 ISO/RTO 或企业历史负荷、天气和节假日数据。

## 方法

模型对每个小时构造以下调度友好特征：

- 小时、星期几、周末、美国固定节假日与典型移动节假日。
- 南北半球季节项，避免将北半球夏季模式直接套用到南半球。
- 经纬度、海拔高度和自动气候板块；平原可将海拔填 0。
- 温度、温度二次项，用于反映制冷/采暖负荷敏感性。

若本地安装了 scikit-learn，则使用 HuberRegressor；否则使用内置岭回归。结果包括 P10-P90 经验残差带，便于调度员做备用和风险提示。
