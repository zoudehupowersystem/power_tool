# Skill: pandapower 合环回路阻抗提取（给 PowerTool 合环分析用）

## 1) 目的
把“配网完整模型”转换为 PowerTool 合环模块可直接使用的参数：
- `r_loop_ohm`
- `x_loop_ohm`

并形成可复现流程记录，便于 Agent 多步执行与审计。

---

## 2) 适用场景
- 用户提供了 pandapower 模型文件（JSON）并指定两个候选合环点。
- 需要在合环前评估稳态环流与冲击暂态，但当前 PowerTool `loop_closure` 需要人工输入 `RΣ/XΣ`。

---

## 3) 前置能力（当前仓库已具备）
- 解析模型设备与拓扑：`parse_pandapower_model`
- 潮流计算：`pandapower_power_flow`
- 合环评估：`loop_closure`
- 依赖安装：`install_python_packages`

---

## 4) 标准流程（Agent 执行模板）

### Step A. 准备依赖
1. 若环境无 pandapower：调用 `install_python_packages`。
2. 推荐默认 `pandapower` 优先，必要时按配置切换镜像源。

### Step B. 解析模型文件
1. 调用 `parse_pandapower_model`（`model_path`）。
2. 提取并确认：
   - 目标合环点母线名称/索引
   - 连接关系（`edges`, `adjacency`）
   - 关键设备（line/trafo/switch）

### Step C. 求两点等值阻抗（给 `RΣ/XΣ`）
可选两种方法：

#### 方法 C1：Ybus 等值法（优先）
1. 在 pandapower 运行潮流，获得节点导纳矩阵 `Ybus`。
2. 求 `Zbus = inv(Ybus)`（或使用线性求解避免显式求逆）。
3. 对两个合环点 i/j，计算：

\[
Z_{ij,eq}=Z_{ii}+Z_{jj}-Z_{ij}-Z_{ji}
\]

4. 取：
   - `r_loop_ohm = Re(Z_ij_eq)`
   - `x_loop_ohm = Im(Z_ij_eq)`

#### 方法 C2：小扰动潮流反算法（备用）
1. 基准潮流运行。
2. 对两点施加小扰动电流（+ΔI/-ΔI），重复潮流。
3. 记录 `Δ(V_i - V_j)`，近似：

\[
Z_{ij,eq} \approx \frac{\Delta(V_i-V_j)}{\Delta I}
\]

4. 同样取实虚部作为 `RΣ/XΣ`。

> 建议：两种方法可做交叉校核；差异超过阈值时提示“模型或工况非线性显著”。

### Step D. 调用 PowerTool 合环分析
把 C 步得到的 `r_loop_ohm/x_loop_ohm` 传给 `loop_closure`，并补齐：
- `node_injections_A`
- `closure_node_index`
- `u1_kv_ll/u2_kv_ll/angle_deg`
- 载流校核参数（可选）

### Step E. 输出报告
至少输出：
1. 模型摘要（设备数量、拓扑概览）
2. 合环点信息（母线名、位置）
3. `RΣ/XΣ` 计算方法与结果
4. 环流/冲击结果与超限段
5. 风险结论与建议动作（执行条件/回退条件）

---

## 5) 输出 JSON 约定（建议）

```json
{
  "ok": true,
  "method": "ybus|perturbation",
  "closure_pair": {"bus_i": "BUS_A", "bus_j": "BUS_B"},
  "loop_impedance": {
    "r_loop_ohm": 1.23,
    "x_loop_ohm": 4.56,
    "z_abs_ohm": 4.72,
    "z_angle_deg": 74.8
  },
  "quality": {
    "cross_check_error_pct": 3.1,
    "notes": "..."
  },
  "next_action": {
    "skill": "loop_closure",
    "args_hint": {"r_loop_ohm": 1.23, "x_loop_ohm": 4.56}
  }
}
```

---

## 6) 常见错误与防呆
1. **单位错误**：把 `Ω/km` 当成总阻抗输入。
2. **合环点定义错误**：选错母线或非空点。
3. **工况不一致**：阻抗提取工况与合环评估工况不一致。
4. **扰动过大**：小扰动法中 ΔI 过大导致线性近似失效。

---

## 7) 自然语言触发示例
- “读取这个 pandapower 文件，帮我给 12 号和 37 号母线算合环回路阻抗，再跑合环风险评估。”
- “先解析模型拓扑，找两个候选合环点，分别估算 RΣ/XΣ 并比较风险。”

---

## 8) 实施建议
- 优先实现 C2（小扰动法）可快速落地；
- 再补 C1（Ybus 法）做高精度与可解释性增强；
- 最后把两者做一致性校验并给出置信等级。
