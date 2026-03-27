# Skill: 潮流运行点驱动的发电机小扰动分析

对应代码：`skill_smib_from_powerflow.py`。

输入：`model_path`、`gen_index`、可选 `smib_config/smib_params`。
输出：发电机潮流运行点 + SMIB 小扰动结果。

```python
from skill_smib_from_powerflow import run_skill
print(run_skill({"model_path": "net.json", "gen_index": 0}))
```
