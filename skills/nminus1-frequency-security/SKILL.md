# Skill: N-1 潮流+频率安全校核

对应代码：`skill_nminus1_frequency_security.py`。

输入：`model_path`、`contingencies`、`frequency_args`。
输出：基准潮流、各 N-1 场景结果、关键设备与关键断面排序。

```python
from skill_nminus1_frequency_security import run_skill
print(run_skill({"model_path": "net.json", "contingencies": [{"id":"L12","type":"line_outage","index":12}]}))
```
