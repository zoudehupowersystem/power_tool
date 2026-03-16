# power_tool

电力系统工程近似计算 GUI 工具（Tkinter + Matplotlib）。

本项目用于工程场景下的**快速估算与参数折算**，覆盖频率动态、机电振荡、静稳极限、长线路自然功率、暂稳快估，以及线路/变压器参数校核与标幺值转换。

> ⚠️ 说明：本工具基于工程近似模型，不替代潮流、特征值分析、机电暂态时域仿真与正式校核。

---

## 1. 功能概览（按标签页）

主标签页：

1. 频率动态
2. 机电振荡
3. 静态电压稳定
4. 线路自然功率与无功
5. 暂稳评估（冲击法 + 等面积法）
6. 参数校核与标幺值（含 3 个子标签页）
   - 架空线路
   - 两绕组变压器
   - 三绕组变压器

---

## 2. 环境配置

### 2.1 依赖

- Python 3.10+
- `numpy`
- `matplotlib`
- `tkinter`（多数 Python 发行版自带）

### 2.2 推荐安装方式

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install numpy matplotlib
```

### 2.3 启动

```bash
python power_tool.py
```

---

## 3. 测试与自检

本项目目前没有独立测试框架（pytest/unittest 套件），推荐最小自检：

```bash
python -m py_compile power_tool.py
python - <<'PY'
from power_tool import frequency_response_summary
print(frequency_response_summary(0.08, 8, 5, 1.2, 4.0, 50))
PY
```

---

## 4. 标签页详解（含推导 + 默认参数算例）

> 下文算例全部采用 GUI 默认参数，便于你与软件输出逐项核对。

---

### 4.1 标签页一：频率动态

**默认参数**

- `f0=50 Hz`
- `ΔP_OL0=0.08 pu`
- `T_s=8 s`
- `T_G=5 s`
- `k_D=1.2`
- `k_G=4.0`

**核心模型（含一次调频二阶）**


a) 稳态频差：

$$
\Delta f_{ss}=-\frac{\Delta P_{OL0}}{k_D+k_G}
$$

代入：

$$
\Delta f_{ss}=-\frac{0.08}{1.2+4.0}=-0.01538\,pu
$$

换算 Hz：

$$
\Delta f_{ss,Hz}=\Delta f_{ss}\cdot f_0=-0.01538\times 50=-0.769\,Hz
$$

b) 初始 RoCoF（频率变化率）：

$$
\dot{\Delta f}(0)=-\frac{\Delta P_{OL0}}{T_s}=-\frac{0.08}{8}=-0.01\,pu/s
$$

换算 Hz/s：

$$
-0.01\times 50=-0.5\,Hz/s
$$

c) 阻尼判别：代码内判别式给出欠阻尼（会出现频率谷值）。

d) 默认算例结果（程序输出）：

- 最低点时刻约 `t_nadir=5.234 s`
- 最低频差约 `-0.02512 pu`
- 最低频率约 `48.744 Hz`

这与“先下后回”的频率曲线一致。

---

### 4.2 标签页二：机电振荡

**默认参数**

- `E'_q=1.12 pu`
- `U=1.0 pu`
- `X_Σ=0.55 pu`
- `P0=0.8 pu`
- `T_j=9 s`
- `f0=50 Hz`

**推导链条**

1) 先求初始功角：

$$
\delta_0=\arcsin\left(\frac{P_0X_\Sigma}{E'_qU}\right)
=\arcsin\left(\frac{0.8\times0.55}{1.12\times1.0}\right)
=\arcsin(0.392857)=23.13^\circ
$$

2) 同步转矩系数：

$$
K_s=\frac{E'_qU}{X_\Sigma}\cos\delta_0
=\frac{1.12}{0.55}\cos(23.13^\circ)
\approx1.873
$$

3) 小扰动固有角频率：

$$
\omega_n=\sqrt{\frac{\omega_0K_s}{T_j}},\quad \omega_0=2\pi f_0=314.159
$$

$$
\omega_n\approx\sqrt{\frac{314.159\times1.873}{9}}=8.085\,rad/s
$$

4) 频率：

$$
f_n=\frac{\omega_n}{2\pi}=1.287\,Hz
$$

---

### 4.3 标签页三：静态电压稳定

**默认参数**

- `U_g=1.0 pu`
- `X_Σ=0.32 pu`
- `cosφ=0.95`
- `S_base=100 MVA`

**推导步骤**

1) 先求 $\sin\varphi$：

$$
\sin\varphi=\sqrt{1-\cos^2\varphi}=\sqrt{1-0.95^2}=0.31225
$$

2) 极限有功（代码公式）：

$$
P_{max}=\frac{U_g^2}{2X_\Sigma}\cdot\frac{\cos\varphi}{1+\sin\varphi}
$$

$$
P_{max}=\frac{1}{0.64}\cdot\frac{0.95}{1.31225}=1.13117\,pu
$$

3) 换算 MW：

$$
P_{max,MW}=1.13117\times100=113.12\,MW
$$

4) 临界受端电压（与送端同基准）：

$$
V_{min}=\frac{U_g}{\sqrt{2+2\sin\varphi}}=
\frac{1.0}{\sqrt{2+2\times0.31225}}=0.61727\,pu
$$

---

### 4.4 标签页四：线路自然功率与无功

**默认参数**

- `U=500 kV`
- `Z_c=250 Ω`
- `P=700 MW`
- `Q_N=1.2 Mvar/km`
- `l=200 km`

**推导**

1) 自然功率：

$$
P_n=\frac{U^2}{Z_c}=\frac{500^2}{250}=1000\,MW
$$

2) 无功差额：

$$
\Delta Q=\left[\left(\frac{P}{P_n}\right)^2-1\right]Q_Nl
$$

$$
\Delta Q=\left[(0.7)^2-1\right]\times1.2\times200
=(-0.51)\times240=-122.4\,Mvar
$$

3) 解释：`ΔQ<0`，线路总体发无功（净容性）。

---

### 4.5 标签页五：暂稳评估

该页有两块：冲击法 + 等面积法。

#### 4.5.1 冲击法快估

**默认参数**

- `ΔPa=0.9 pu`
- `Δt=0.12 s`
- `f_d=1.106 Hz`
- `Pmax_post=1.65 pu`
- `Pm=0.9 pu`

**计算**

1) 速度冲量折算：

$$
\Delta p=\Delta P_a\Delta t\cdot2\pi f_d
=0.9\times0.12\times2\pi\times1.106
=0.75051\,pu
$$

2) 暂稳传输能力估计：

$$
P_{st}=P_{max,post}-\Delta p=1.65-0.75051=0.89949\,pu
$$

3) 与当前功率比较：

$$
margin=P_{st}-P_m=0.89949-0.9=-0.00051\,pu
$$

结论：裕度略小于 0，显示“第一摆稳定裕度不足”。

#### 4.5.2 等面积法（单机无穷大）

**默认参数**

- `Pm=0.9`
- `Pmax_pre=1.65`
- `Pmax_fault=0`
- `Pmax_post=1.65`
- `Δt=0.12 s`
- `Tj=9 s`
- `f0=50 Hz`

**关键步骤（程序实现）**

1) 先求初始平衡角：

$$
\delta_0=\arcsin(P_m/P_{max,pre})=\arcsin(0.9/1.65)=33.06^\circ
$$

2) 用 RK4 解故障期摆动方程，得到切除角：

$$
\delta_c\approx46.02^\circ
$$

3) 面积比较（程序数值积分）：

- `A_acc=0.2036 pu·rad`
- `A_dec_avail=0.9434 pu·rad`

4) 稳定结论：`A_dec_avail > A_acc`，且 `δc < δu`，判定稳定。

5) 默认工况关键输出：

- `δcr≈75.75°`
- `tcr≈0.2179 s`
- 面积裕度约 `+363.4%`

---

### 4.6 标签页六：参数校核与标幺值（总览）

此标签页分为 3 个子标签页，每个子页都包含：

- 有名值折算
- 标幺值计算
- 合理区间告警（warning/error）

---

### 4.7 子标签页：架空线路

**默认参数**

- `R1=0.028 Ω/km`
- `X1=0.299 Ω/km`
- `C1=0.013 μF/km`
- `length=200 km`
- `Sbase=100 MVA`
- `Ubase=500 kV`

**推导**

1) 总串联参数：

$$
R=R_1l=0.028\times200=5.6\,\Omega
$$
$$
X=X_1l=0.299\times200=59.8\,\Omega
$$

2) 对地半电纳（50 Hz）：

$$
B/2=\omega C_1l/2
$$

其中 $\omega=2\pi\times50$，$C_1=0.013\times10^{-6}F/km$，代入得

$$
B/2\approx4.084\times10^{-4}\,S
$$

3) 基准阻抗：

$$
Z_{base}=\frac{U_{base}^2}{S_{base}}=\frac{500^2}{100}=2500\,\Omega
$$

4) 标幺：

$$
R_{pu}=5.6/2500=0.00224
$$
$$
X_{pu}=59.8/2500=0.02392
$$

程序默认算例无告警。

---

### 4.8 子标签页：两绕组变压器

**默认参数**

- `Pk=290 kW`
- `Uk=11.73 %`
- `P0=51.3 kW`
- `I0=0.3 %`
- `SN=20 MVA`
- `UN=35 kV`
- `Sbase=100 MVA`
- `Ubase=35 kV`

**推导**

1) 短路电阻：

$$
R_k=\frac{P_kU_N^2}{S_N^2\cdot1000}
=\frac{290\times35^2}{20^2\times1000}=0.8881\,\Omega
$$

2) 短路阻抗：

$$
Z_k=\frac{U_k\%}{100}\frac{U_N^2}{S_N}=7.1843\,\Omega
$$

3) 短路电抗：

$$
X_k=\sqrt{Z_k^2-R_k^2}=7.1295\,\Omega
$$

4) 换算到标幺（`Zbase=12.25Ω`）：

$$
R_{k,pu}=0.0725,\quad X_{k,pu}=0.5820
$$

5) 默认算例 `Uk%` 交叉校核一致（约 11.73%），无告警。

---

### 4.9 子标签页：三绕组变压器

**默认参数（GUI）**

- `Pk_HM=503.6 kW, Uk_HM=17.5%`
- `Pk_HL=129.0 kW, Uk_HL=11.0%`
- `Pk_ML=120.7 kW, Uk_ML=6.0%`
- `P0=76.1 kW, I0=0.07%`
- `SN_H=180 MVA, SN_M=180 MVA, SN_L=90 MVA`
- `UN_H=220 kV`
- `Sbase=100 MVA, Ubase=220 kV`

**计算说明**

程序先把两两短路试验量折算到统一基准，再做 T 型分解，最后输出每支路 R/X 的有名值与标幺值。

默认算例输出关键点：

- `RH_pu≈0.000101, XH_pu≈0.05843`
- `RM_pu≈0.000159, XM_pu≈-0.04821`
- `RL_pu≈0.000000, XL_pu≈0.05379`

并给出 warning（这在三绕组分解中并不罕见）：

- 一组输入短路电压超典型范围
- 中压支路分解后 `Uk%` 为负，提示复核厂家试验数据

> 工程解释：三绕组参数若来自不同试验条件或不同容量基准，分解出现“负电抗/负Uk%”并不一定表示程序错误，通常意味着数据不一致或模型近似边界触发。

---

## 5. 三绕组变压器计算约定（实现一致性说明）

本工具中的三绕组参数折算遵循以下约定：

1. **公共容量基准**采用高压侧额定容量 `SN_H`。
2. 三组短路损耗分解（T 型等值）前：
   - `Pk_HM / Pk_HL / Pk_ML` 均按对应绕组对的 `min(SN_i, SN_j)` 测试电流折算到 `SN_H`。
3. 三组短路电压 `Uk_HM / Uk_HL / Uk_ML`：
   - 直接按设备报参值参与分解，不对 `Uk_ML` 再做容量换算。
4. 分解后若某支路 `Uk%`（对应电抗）出现负值，程序会给出 **WARNING** 提示，提醒结合厂家试验数据复核（这在三绕组 T 型等值中可能出现，不必直接判错）。

---

## 6. 注意事项

- 所有输入应使用同一组单位（kV、MVA、kW、%）。
- 变压器参数请尽量使用同一台设备同一试验报告的数据，避免“拼接参数”。
- 对告警项建议结合设备铭牌/试验报告复核，不建议盲目据此做运行边界决策。
