# PowerTool 新架构说明（内层软件 + 外层 Agent/Skill）

## 1. 总体结构

```text
┌──────────────────────────────────────────────────────┐
│ 外层（可替换）                                       │
│ - local_agent.py                                    │
│ - power_tool_skill.py                               │
│ - skill_*.py（场景化脚本）                          │
│ - skills/*/SKILL.md（流程文档）                     │
└──────────────────────────────────────────────────────┘
                         │ 结构化调用（JSON）
┌──────────────────────────────────────────────────────┐
│ 内层（PowerTool 独立软件）                           │
│ - GUI: power_tool_gui.py                            │
│ - 内核: power_tool_approximations.py / ...          │
│ - 入口: power_tool.py / PowerTool/main.py           │
│ - 清单: PowerTool/core_manifest.json                │
└──────────────────────────────────────────────────────┘
```

核心原则：
1. PowerTool 内层可单独运行和交付（GUI + Python API）。
2. 外层 Agent/Skill 通过稳定接口调用内层，不反向侵入 GUI 主流程。
3. 可替换外层模型/编排框架，不影响内层工程计算内核。

---

## 2. 目录职责

- `PowerTool/`：内层边界标识、入口包装、核心模块清单。
- `power_tool_*.py`：内层计算内核和 GUI 入口。
- `power_tool_skill.py`：统一 skill 注册与执行网关。
- `local_agent.py`：多步 Agent 编排、报告输出、配置化后端。
- `skill_*.py`：场景化可直接调用脚本。
- `skills/*/SKILL.md`：工程流程模板与调用说明。

---

## 3. 接口与耦合约束

- **内层对外能力**：Python 函数 / dataclass 结果。
- **外层调用协议**：`execute_skill_request({"skill": ..., "args": ...})`。
- **报告产物**：Agent 输出 `summary` + `report_md`。
- **最佳努力策略**：技能外问题返回 best-effort 建议并说明局限（不直接中止）。

---

## 4. 架构验证测试（已纳入仓库）

### 4.1 结构验证
- `tests/test_architecture_layout.py`
  - 检查 `PowerTool/` 边界目录与清单文件存在；
  - 验证 `core_manifest.json` 关键字段。

### 4.2 Agent/Skill 验证
- `tests/test_skill_agent.py`
  - 技能目录、参数校验、bootstrap、pip 源策略、Markdown 报告、best-effort 回退。

### 4.3 场景脚本验证
- `tests/test_loop_impedance_skill.py`
- `tests/test_scenario_skills.py`

### 4.4 推荐回归命令

```bash
python -m pytest -q tests/test_architecture_layout.py \
  tests/test_skill_agent.py \
  tests/test_loop_impedance_skill.py \
  tests/test_scenario_skills.py
```

> 在缺少 `requests/numpy/pandapower` 的环境中，先按 README 安装依赖；
> 对 `pandapower` 缺失场景，测试会验证“优雅报错”路径。
