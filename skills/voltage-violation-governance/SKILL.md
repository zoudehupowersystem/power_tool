# Skill: 母线电压越限治理（主网/配网分流）

对应代码：`skill_voltage_violation_governance.py`。

输入：`model_path`、可选 `vmin_pu/vmax_pu`。
输出：
- 主网：调用 pandapower OPF（可用时）
- 配网：输出电容/电抗投切 + 相邻变压器调档计划

```python
from skill_voltage_violation_governance import run_skill
print(run_skill({"model_path": "net.json"}))
```
