"""Runtime translation helpers and bilingual label mappings. / 运行时翻译辅助与双语标签映射。"""

from __future__ import annotations

from typing import Any, Iterable
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.axes import Axes

# Exact display mapping for discrete UI values. / 离散界面取值的精确显示映射。
DISPLAY_ZH_TO_EN: dict[str, str] = {
    "电力系统近似公式工程工具": "Power System Approximation Engineering Tool",
    "频率动态": "Frequency Dynamics",
    "机电振荡": "Electromechanical Oscillation",
    "电压无功分析": "Voltage / Reactive Power Analysis",
    "暂稳评估": "Transient Stability Assessment",
    "小扰动分析": "Small-Signal Analysis",
    "小扰动分析（SMIB）": "Small-Signal Analysis (SMIB)",
    "配电网合环分析": "Distribution Loop-Closure Analysis",
    "参数校核与标幺值": "Parameter Validation & Per-Unit",
    "短路电流计算": "Short-Circuit Current Calculation",
    "录波曲线": "Waveform Viewer",
    "静态电压稳定": "Static Voltage Stability",
    "线路自然功率与无功": "Line Natural Power & Reactive Power",
    "AVC策略模拟": "AVC Strategy Simulation",
    "架空线路": "Overhead Line",
    "导线弧垂": "Conductor Sag",
    "两绕组变压器": "Two-Winding Transformer",
    "三绕组变压器": "Three-Winding Transformer",
    "电压相量": "Voltage Phasors",
    "电流相量": "Current Phasors",
    "V 序分量": "V Sequence Components",
    "I 序分量": "I Sequence Components",
    "使用手册": "Manual",
    "提问": "Question",
    "启用思考模式": "Enable reasoning mode",
    "发送到 PowerTool AI": "Send to PowerTool AI",
    "填入当前算例摘要": "Insert current case summary",
    "AI 回复": "AI Response",
    "PowerTool AI 已就绪。": "PowerTool AI is ready.",
    "PowerTool AI 正在处理中，请稍候…": "PowerTool AI is processing…",
    "请结合当前界面，解释这个算例的意义、关键结果和下一步建议。": "Please explain the meaning of this case, the key results, and the recommended next steps based on the current page.",
    "请结合当前界面分析：": "Please analyze the current page:",
    "计算": "Calculate",
    "计算并绘图": "Calculate & Plot",
    "计算并校核": "Calculate & Validate",
    "执行9区策略模拟": "Run 9-zone strategy simulation",
    "计算1型 AVR/PSS 指标": "Calculate Type-1 AVR/PSS metrics",
    "恢复 Kundur 默认值": "Restore Kundur defaults",
    "读取失败": "Read Failed",
    "计算错误": "Calculation Error",
    "输入错误": "Input Error",
    "提示": "Notice",
    "尚未计算": "Not Calculated",
    "录波加载失败": "Waveform Load Failed",
    "录波分析失败": "Waveform Analysis Failed",
    "导出完成": "Export Complete",
    "导出失败": "Export Failed",
    "无法绘图": "Plot Failed",
    "未设置": "Not set",
    "未选择": "Not selected",
    "未载入": "Not loaded",
    "显示风格": "Display mode",
    "一键切换风格": "Toggle style",
    "录波重新导出": "Waveform re-export",
    "选择一个或多个通道": "Select one or more channels",
    "导出": "Export",
    "取消": "Cancel",
    "浏览...": "Browse...",
    "返回概览": "Back to overview",
    "应用配置": "Apply configuration",
    "等待 T1 光标": "Waiting for T1 cursor",
    "录波曲线浏览": "Waveform Viewer",
    "谐波分析最高次数": "Maximum harmonic order",
    "刷新": "Refresh",
    "三相电压通道": "Three-phase voltage channels",
    "三相电流通道": "Three-phase current channels",
    "名称": "Name",
    "幅值": "Magnitude",
    "实部": "Real",
    "虚部": "Imag",
    "单位：-": "Unit: -",
    "多通道同图 / MATLAB 单轴叠加风格": "Multi-channel overlay / MATLAB single-axis style",
    "多通道同图 / MATLAB 学术论文风格（分轴堆叠）": "Multi-channel overlay / MATLAB paper style (stacked axes)",
    "通道 / 线形": "Channel / trace",
    "幅值": "Magnitude",
    "值": "Value",
    "故障相电流": "Fault phase currents",
    "故障序电流": "Fault sequence currents",
    "故障相电压": "Fault phase voltages",
    "故障序电压": "Fault sequence voltages",
    "配电网合环点位示意与各段电流": "Loop-closure topology and segment currents",
    "合环环流（A 相瞬时值）": "Loop current (phase A instantaneous)",
    "左侧线路总电流（三相瞬时值）": "Left-side total line current (three-phase instantaneous)",
    "右侧线路总电流（三相瞬时值）": "Right-side total line current (three-phase instantaneous)",
    "按输入几何尺寸等比例绘制": "Geometry drawn to input scale",
    "地平面": "Ground plane",
    "左端": "Left end",
    "右端": "Right end",
    "合环点": "Closure point",
    "上：合环后稳态电流 A；下：合环前电流 A": "Top: post-closure steady current in A; bottom: pre-closure current in A",
    "请先加载 COMTRADE 录波": "Please load a COMTRADE waveform first",
    "未加载录波文件。": "No waveform file loaded.",
    "未加载文件": "No file loaded",
    "光标：左键放置 T1，右键放置 T2。": "Cursor: left click places T1, right click places T2.",
    "录波曲线 - 多通道同图（MATLAB 单轴叠加风格）": "Waveform - multi-channel overlay (MATLAB single-axis style)",
    "录波曲线 - 多通道同图（MATLAB 学术风格）": "Waveform - multi-channel overlay (MATLAB paper style)",
    "单电源": "Single source",
    "双电源": "Two sources",
    "A相接地": "A-to-ground",
    "B相接地": "B-to-ground",
    "C相接地": "C-to-ground",
    "AB两相接地": "AB-to-ground",
    "BC两相接地": "BC-to-ground",
    "CA两相接地": "CA-to-ground",
    "AB两相短路": "AB line-to-line",
    "BC两相短路": "BC line-to-line",
    "CA两相短路": "CA line-to-line",
    "三相接地": "Three-phase to ground",
    "直接接地": "Solidly grounded",
    "中性点不接地": "Ungrounded neutral",
    "经消弧线圈接地": "Grounded through Petersen coil",
    "经电阻接地": "Grounded through resistor",
    "滞后": "Lagging",
    "超前": "Leading",
    "欠阻尼": "Underdamped",
    "过阻尼": "Overdamped",
    "临界阻尼": "Critically damped",
    "总体发无功（净容性）": "Net reactive injection (net capacitive)",
    "总体吸无功（净感性）": "Net reactive absorption (net inductive)",
    "近似自平衡": "Approximately self-balanced",
    "振荡幅值可接受": "Oscillation amplitude acceptable",
    "振荡幅值偏大": "Oscillation amplitude is large",
    "稳定": "Stable",
    "不稳定": "Unstable",
    "[稳定]": "[Stable]",
    "[失稳]": "[Unstable]",
    "[失稳]（加速面积 > 可用减速面积）": "[Unstable] (accelerating area > available decelerating area)",
    "低压区": "Low-voltage zone",
    "高压区": "High-voltage zone",
    "正常电压区": "Normal-voltage zone",
    "感性无功偏大": "Excess inductive reactive power",
    "容性无功偏大": "Excess capacitive reactive power",
    "无功正常区": "Reactive power within target band",
    "Ⅰ区（低压+感性）": "Zone I (low voltage + inductive)",
    "Ⅱ区（低压+无功正常）": "Zone II (low voltage + reactive normal)",
    "Ⅲ区（低压+容性）": "Zone III (low voltage + capacitive)",
    "Ⅳ区（电压正常+感性）": "Zone IV (normal voltage + inductive)",
    "Ⅴ区（目标区）": "Zone V (target zone)",
    "Ⅵ区（电压正常+容性）": "Zone VI (normal voltage + capacitive)",
    "Ⅶ区（高压+感性）": "Zone VII (high voltage + inductive)",
    "Ⅷ区（高压+无功正常）": "Zone VIII (high voltage + reactive normal)",
    "Ⅸ区（高压+容性）": "Zone IX (high voltage + capacitive)",
    "升高变压器档位 +1": "Raise transformer tap by +1",
    "降低变压器档位 -1": "Lower transformer tap by -1",
    "保持当前档位与无功补偿状态": "Keep the current tap position and reactive compensation state",
}

# Phrase-level replacement for larger spans. / 适用于较长语段的短语替换。
PHRASE_ZH_TO_EN: dict[str, str] = {
    "结果摘要": "Result Summary",
    "计算结果": "Results",
    "详细结果": "Detailed Results",
    "模态结果": "Modal Results",
    "策略结果": "Strategy Results",
    "策略结果": "Strategy Results",
    "参数输入": "Input Parameters",
    "计算参数": "Calculation Parameters",
    "运行点与设备参数": "Operating Point and Equipment Parameters",
    "系统与故障设定": "System and Fault Settings",
    "中性点与开断校核": "Neutral Grounding and Breaker Check",
    "显示与交互": "Display and Interaction",
    "电压与向量图": "Voltage and Vector Plots",
    "电流与向量图": "Current and Vector Plots",
    "点位图与稳态电流": "Topology and Steady-State Currents",
    "显示通道：无": "Displayed channels: none",
    "当前时间窗": "Current time window",
    "文件：": "File:",
    "站名：": "Station:",
    "设备：": "Device:",
    "版本：": "Version:",
    "文件类型：": "File type:",
    "采样率：": "Sampling rate:",
    "模拟量通道：": "Analog channels:",
    "数字量通道：": "Digital channels:",
    "当前录波文件": "Current waveform file",
    "当前模型：": "Current model:",
    "模型配置": "Model Configuration",
    "模型配置: ": "Model configuration: ",
    "配置文件：": "Configuration file:",
    "当前模式：": "Current mode:",
    "当前截图：": "Current screenshot:",
    "用户问题：": "User question:",
    "当前模块：": "Current module:",
    "界面截图说明：": "Screenshot note:",
    "当前算例数值：": "Current numerical case:",
    "说明：": "Notes:",
    "说明": "Notes",
    "提示：": "Hint:",
    "结论：": "Conclusion:",
    "稳定性：": "Stability:",
    "稳定性判断：": "Stability assessment:",
    "运行区间判断：": "Operating-region assessment:",
    "匹配：": "Match:",
    "不匹配：": "Mismatch:",
    "当前分区：": "Current zone:",
    "建议策略：": "Recommended strategy:",
    "调控后估算：": "Estimated state after control:",
    "相对准确潮流计算（当前 / 动作后）：": "More accurate power-flow estimate (current / after action):",
    "无功判据：": "Reactive-power criterion:",
    "电压判据：": "Voltage criterion:",
    "已计入过渡电阻；波形含交流分量+指数衰减直流偏置。": "Transition resistance is included; the waveform contains an AC component plus an exponentially decaying DC offset.",
    "请先加载录波文件。": "Please load a waveform file first.",
    "请先加载 COMTRADE 录波": "Please load a COMTRADE waveform first",
    "请先选择录波文件。": "Please choose a waveform file first.",
    "请输入问题后再发送。": "Please enter a question before sending.",
    "当前页暂未定义数值摘要。": "No numerical summary is defined for the current page yet.",
    "当前页暂未提取到数值算例。": "No numerical case could be extracted from the current page.",
    "PowerTool AI 正在分析：": "PowerTool AI is analyzing: ",
    "PowerTool AI 调用失败：": "PowerTool AI request failed:\n",
    "PowerTool AI 发生未预期异常：": "PowerTool AI encountered an unexpected error:\n",
    "PowerTool AI 发生未预期异常": "PowerTool AI encountered an unexpected error",
    "PowerTool AI 正在处理中，请稍候…": "PowerTool AI is processing…",
    "导出完成": "Export complete",
    "已导出文件：": "Exported files:",
    "未找到当前页面手册：": "Manual not found for the current page: ",
    "使用手册 - ": "Manual - ",
    "谐波分析 - ": "Harmonic Analysis - ",
    "谐波含有率柱状图": "Harmonic content bar chart",
    "谐波": "Harmonics",
    "含有量": "Amplitude",
    "含有率": "Percentage",
    "频率响应曲线": "Frequency response curve",
    "功角曲线（等待计算）": "Power-angle curve (waiting for calculation)",
    "故障点电流向量图（ABC+012）": "Fault-current phasor plot (ABC + 012)",
    "故障点电压向量图（ABC+012）": "Fault-voltage phasor plot (ABC + 012)",
    "架空线路典型参数": "Typical overhead-line parameters",
    "线路参数计算": "Line parameter calculation",
    "录波浏览区": "Waveform browsing area",
    "时间拖动": "Time scrolling",
    "纵向放大": "Zoom Y in",
    "纵向缩小": "Zoom Y out",
    "横向放大": "Zoom X in",
    "横向缩小": "Zoom X out",
    "起始时间": "Start time",
    "结束时间": "End time",
    "窗口宽度": "Window width",
    "选择录波": "Select waveform",
    "加载录波": "Load waveform",
    "序量分析": "Sequence analysis",
    "重新导出": "Re-export",
    "多通道同图": "Multi-channel overlay",
    "通道选择（Ctrl/Shift 多选）": "Channel selection (Ctrl/Shift for multi-select)",
    "分析选中通道": "Analyze selected channels",
    "全选通道": "Select all channels",
    "录波曲线（COMTRADE / Yokogawa / MATLAB）": "Waveform viewer (COMTRADE / Yokogawa / MATLAB)",
    "录波曲线浏览": "Waveform browsing",
    "图表 + 工具栏": "chart + toolbar",
    "二阶频率动态（含一次调频）": "Second-order frequency dynamics (with primary frequency control)",
    "基础模型参数": "Base model parameters",
    "同时绘制无一次调频一阶对照": "Also plot the first-order reference without primary control",
    "二次调频（AGC）": "Secondary frequency control (AGC)",
    "启用 AGC（默认关闭）": "Enable AGC (off by default)",
    "机电振荡频率快估": "Fast estimate of electromechanical oscillation frequency",
    "静态电压稳定极限快估": "Fast estimate of static voltage-stability limit",
    "长线路自然功率与无功行为快估": "Fast estimate of natural power and reactive behavior for long lines",
    "AVC策略模拟（降压变压器+无功补偿）": "AVC strategy simulation (step-down transformer + reactive compensation)",
    "暂稳评估": "Transient Stability Assessment",
    "等面积法（单机无穷大）": "Equal-Area Criterion (SMIB)",
    "冲击法快估": "Impact-method quick estimate",
    "配电网合环近似分析": "Approximate loop-closure analysis for distribution systems",
    "参数校核与标幺值转换": "Parameter Validation and Per-Unit Conversion",
    "架空线路参数校核与标幺值转换（π 型等值）": "Overhead-line parameter validation and per-unit conversion (π equivalent)",
    "输电线路导线弧垂计算（单档悬链线）": "Transmission-line conductor sag (single-span catenary)",
    "两绕组变压器参数校核与标幺值转换": "Two-winding transformer parameter validation and per-unit conversion",
    "三绕组变压器参数校核与标幺值转换": "Three-winding transformer parameter validation and per-unit conversion",
    "短路电流计算": "Short-circuit current calculation",
    "录波概览": "Waveform Overview",
    "当前窗口分析": "Analysis for current window",
    "断路器匹配": "Breaker matching",
    "复合序网计算结果": "Composite sequence-network result",
    "冲击法：功率振荡幅度快估": "Impact method: quick estimate of power-oscillation amplitude",
    "AVC 9区策略模拟结果": "AVC 9-zone strategy result",
    "1型 AVR/PSS 模型校核": "Type-1 AVR/PSS model validation",
    "主导参与状态：": "Dominant participating states:",
    "状态维数：": "State dimension:",
    "特征值复平面": "Eigenvalue complex plane",
    "系统与导线数据": "System and conductor data",
    "三相导线几何坐标": "Three-phase conductor geometry",
    "地线（可选）": "Shield wire (optional)",
}

# Short-token replacement for the remaining mixed strings. / 针对剩余混合字符串的短词替换。
TOKEN_ZH_TO_EN: dict[str, str] = {
    "频率": "Frequency",
    "振荡": "Oscillation",
    "电压": "Voltage",
    "无功": "Reactive Power",
    "有功": "Active Power",
    "暂稳": "Transient Stability",
    "小扰动": "Small-Signal",
    "配电网合环": "Distribution Loop-Closure",
    "参数校核": "Parameter Validation",
    "标幺值": "Per-Unit",
    "短路": "Short-Circuit",
    "录波": "Waveform",
    "曲线": "Curve",
    "结果": "Result",
    "摘要": "Summary",
    "当前": "Current",
    "模式": "Mode",
    "状态": "Status",
    "说明": "Notes",
    "结论": "Conclusion",
    "稳定": "Stable",
    "失稳": "Unstable",
    "故障": "Fault",
    "相电流": "phase currents",
    "序电流": "sequence currents",
    "相电压": "phase voltages",
    "序电压": "sequence voltages",
    "等待计算": "waiting for calculation",
    "等待": "Waiting",
    "未配置": "Not configured",
    "未加载": "Not loaded",
    "未输入": "Not provided",
    "未找到": "Not found",
    "无法": "Unable to",
    "读取": "read",
    "加载": "load",
    "导出": "export",
    "分析": "analysis",
    "计算": "calculate",
    "刷新": "refresh",
    "浏览": "Browse",
    "保存": "Save",
    "选择": "Select",
    "通道": "channel",
    "时间": "time",
    "基波": "Fundamental",
    "直流分量": "DC component",
    "谐波": "harmonic",
    "序分量": "sequence components",
    "电流": "Current",
    "相量": "Phasors",
    "单位": "Unit",
    "名称": "Name",
    "幅值": "Magnitude",
    "相角": "Angle",
    "实部": "Real",
    "虚部": "Imag",
    "系统": "System",
    "线路": "Line",
    "变压器": "Transformer",
    "高压侧": "HV side",
    "低压侧": "LV side",
    "额定": "Rated",
    "容量": "Capacity",
    "电阻": "Resistance",
    "电抗": "Reactance",
    "电纳": "Susceptance",
    "导纳": "Admittance",
    "档位": "tap position",
    "投入": "Switch in",
    "电容器": "capacitor bank",
    "电抗器": "reactor bank",
    "容性": "capacitive",
    "感性": "inductive",
    "无穷大母线": "infinite bus",
    "功角": "power angle",
    "加速面积": "accelerating area",
    "减速面积": "decelerating area",
    "裕度": "margin",
    "匹配": "match",
    "不匹配": "mismatch",
    "中性点": "neutral grounding",
    "直接接地": "solidly grounded",
    "消弧线圈": "Petersen coil",
    "接地电阻": "grounding resistor",
    "地线": "shield wire",
    "地平面": "ground plane",
    "左侧": "left side",
    "右侧": "right side",
    "左端": "left end",
    "右端": "right end",
    "合环": "loop closure",
    "工频": "power frequency",
    "最低频率": "minimum frequency",
    "最低频差": "minimum frequency deviation",
    "稳态频差": "steady-state frequency deviation",
    "阻尼比": "damping ratio",
    "阻尼类型": "damping type",
    "同步转矩系数": "synchronizing torque coefficient",
    "固有角频率": "natural angular frequency",
    "机电振荡频率": "electromechanical oscillation frequency",
    "自然功率": "natural power",
    "运行区间判断": "operating-region assessment",
    "稳定性判断": "stability assessment",
    "故障点": "fault point",
    "文件": "File",
    "版本": "Version",
    "设备": "Device",
    "站名": "Station",
    "采样率": "Sampling rate",
    "模拟量": "Analog",
    "数字量": "Digital",
}


# Additional translation coverage for mixed UI labels and result text. / 扩充混合界面标签与结果文本的翻译覆盖。
DISPLAY_ZH_TO_EN.update({
    "向AI提问时会自动附带当前界面截图和算例摘要": "When you ask PowerTool AI, the current-page screenshot and numerical case summary are attached automatically.",
    "机电振荡频率快估": "Fast estimate of electromechanical oscillation frequency",
    "静态电压稳定极限快估": "Fast estimate of static voltage-stability limit",
    "长线路自然功率与无功行为快估": "Fast estimate of natural power and reactive behavior for long lines",
    "AVC策略模拟（降压变压器+无功补偿）": "AVC strategy simulation (step-down transformer + reactive compensation)",
    "单机无穷大系统小扰动分析": "Small-signal analysis for a single-machine infinite-bus system",
    "工况与网络": "Operating Conditions and Network",
    "六阶机组": "Sixth-order Generator",
    "六阶机组 + AVR": "Sixth-order Generator + AVR",
    "六阶机组 + AVR + PSS": "Sixth-order Generator + AVR + PSS",
    "1型 AVR/PSS": "Type-1 AVR/PSS",
    "线路参数": "Line Parameters",
    "线路参数计算": "Line Parameter Calculation",
    "线路参数计算（由几何数据反算序参数）": "Line parameter calculation (sequence parameters from conductor geometry)",
    "典型参数": "Typical Parameters",
    "回填正序到本页": "Backfill positive-sequence parameters to this page",
    "回填序参数到短路页": "Backfill sequence parameters to the short-circuit page",
    "合环近似参数": "Loop-closure approximate parameters",
    "连接点表": "Connection-point table",
    "线段比例（N+1 段）": "Segment ratios (N+1 sections)",
    "联络点": "Tie point",
    "冲击暂态电流": "Impact transient current",
    "故障点波形与向量图": "Fault-point waveforms and phasor plots",
    "应用时间窗": "Apply time window",
    "恢复初始状态": "Restore initial state",
    "导出格式": "Export format",
    "输出路径/文件名": "Output path / filename",
    "保存 COMTRADE（选择基名或 cfg）": "Save COMTRADE (choose the base name or cfg)",
    "Prony 类估计：": "Prony-like estimate: ",
    "傅里叶分析通道：": "Fourier-analysis channel: ",
    "向量图显示数值标签": "Show numeric labels in phasor plots",
    "仿真周波数（波形）": "Number of simulated cycles (waveform)",
    "按 N 重建表格": "Rebuild tables from N",
    "加载默认值": "Load default values",
    "导线横截面示意图": "Conductor cross-section diagram",
    "有地线": "With shield wire",
    "无地线": "Without shield wire",
    "A相导线": "Phase-A conductor",
    "B相导线": "Phase-B conductor",
    "C相导线": "Phase-C conductor",
    "i1(正序)": "i1 (positive sequence)",
    "i2(负序)": "i2 (negative sequence)",
    "i0(零序)": "i0 (zero sequence)",
    "u1(正序)": "u1 (positive sequence)",
    "u2(负序)": "u2 (negative sequence)",
    "u0(零序)": "u0 (zero sequence)",
    "含一次调频二阶模型": "Second-order model with primary control",
    "无一次调频一阶对照": "First-order reference without primary control",
    "含二次调频（AGC）": "With secondary frequency control (AGC)",
    "二阶模型稳态频率": "Steady-state frequency of the second-order model",
    "最低点": "Minimum point",
    "总览.md": "Overview.md",
    "输入参数": "Input Parameters",
    "参数页子标签: ": "Parameter subpage: ",
    "电压无功子标签: ": "Voltage/reactive-power subpage: ",
    "系统惯性时间常数 T_s / s": "System inertia time constant T_s / s",
    "一次调频时间常数 T_G / s": "Primary-frequency-control time constant T_G / s",
    "负荷频率系数 k_D / pu/pu": "Load-frequency coefficient k_D / pu/pu",
    "一次调频系数 k_G / pu/pu": "Primary-frequency-control coefficient k_G / pu/pu",
    "绘图时长 / s": "Plot duration / s",
    "ACE频偏系数 B / (MW/Hz, 标幺化)": "ACE frequency-deviation coefficient B / (MW/Hz, per-unit normalized)",
    "AGC比例 Kp": "AGC proportional gain Kp",
    "AGC积分 Ki / s⁻¹": "AGC integral gain Ki / s⁻¹",
    "ACE滤波时间常数 Tace / s": "ACE filter time constant Tace / s",
    "主站到机组执行滞后 Tcmd / s": "Master-station-to-generator actuation lag Tcmd / s",
    "二次调频最大调节量 |P2|max / pu": "Maximum secondary-control adjustment |P2|max / pu",
    "频率死区 |Δf| / Hz": "Frequency deadband |Δf| / Hz",
    "端电压 U / pu": "Terminal voltage U / pu",
    "等值电抗 X_Σ / pu": "Equivalent reactance X_Σ / pu",
    "初始有功 P0 / pu": "Initial active power P0 / pu",
    "惯性时间常数 T_j / s": "Inertia time constant T_j / s",
    "同步频率 f0 / Hz": "Synchronous frequency f0 / Hz",
    "送端电压 U_g / pu": "Sending-end voltage U_g / pu",
    "功率因数 cosφ（默认滞后）": "Power factor cosφ (lagging by default)",
    "容量基准 S_base / MVA（可改）": "Capacity base S_base / MVA (editable)",
    "线路额定电压 U / kV（线电压）": "Line rated voltage U / kV (line voltage)",
    "波阻抗 Z_c / Ω（优先）": "Surge impedance Z_c / Ω (preferred)",
    "单位长度电感 L（可留空）": "Per-unit-length inductance L (optional)",
    "单位长度电容 C（可留空）": "Per-unit-length capacitance C (optional)",
    "实际传输有功 P / MW": "Actual transmitted active power P / MW",
    "单位长度充电功率 Q_N / (Mvar/km)": "Per-unit-length charging power Q_N / (Mvar/km)",
    "线路长度 l / km": "Line length l / km",
    "低压侧电压下限 / kV": "LV-side voltage lower limit / kV",
    "低压侧电压上限 / kV": "LV-side voltage upper limit / kV",
    "变压器最小档位": "Transformer minimum tap position",
    "变压器最大档位": "Transformer maximum tap position",
    "单档电压调节率 / %": "Tap-step voltage regulation / %",
    "低压侧电容器组数量": "Number of LV-side capacitor banks",
    "每组电容器容量 / Mvar": "Per-bank capacitor rating / Mvar",
    "低压侧电抗器组数量": "Number of LV-side reactor banks",
    "每组电抗器容量 / Mvar": "Per-bank reactor rating / Mvar",
    "高压侧有功潮流 P / MW": "HV-side active-power flow P / MW",
    "高压侧无功潮流 Q / Mvar（感性为正）": "HV-side reactive-power flow Q / Mvar (positive for inductive)",
    "故障中 Pmax_fault / pu（三相故障填 0）": "Pmax_fault during the fault / pu (enter 0 for a three-phase fault)",
    "故障前 Pmax_pre / pu": "Pre-fault Pmax_pre / pu",
    "故障后 Pmax_post / pu": "Post-fault Pmax_post / pu",
    "故障切除时间 Δt / s": "Fault-clearing time Δt / s",
    "故障加速功率 ΔPa / pu": "Fault accelerating power ΔPa / pu",
    "故障后振荡频率 f_d / Hz": "Post-fault oscillation frequency f_d / Hz",
    "端电压角 θt / °": "Terminal-voltage angle θt / °",
    "机械起动时间 M=2H / s": "Mechanical starting time M = 2H / s",
    "系统电压 U / kV（线电压）": "System voltage U / kV (line voltage)",
    "故障点距左侧百分比 / %": "Fault-point distance from the left side / %",
    "左侧系统 X/R 比": "Left-side system X/R ratio",
    "右侧系统 X/R 比": "Right-side system X/R ratio",
    "左侧预故障电势 E_L / pu": "Left-side pre-fault EMF E_L / pu",
    "左侧预故障相角 δL / °": "Left-side pre-fault phase angle δL / °",
    "右侧预故障电势 E_R / pu": "Right-side pre-fault EMF E_R / pu",
    "右侧预故障相角 δR / °": "Right-side pre-fault phase angle δR / °",
    "线路长度 / km": "Line length / km",
    "过渡电阻 Rf / Ω": "Fault resistance Rf / Ω",
    "线路正序电阻 R1 / (Ω/km)": "Positive-sequence line resistance R1 / (Ω/km)",
    "线路正序电抗 X1 / (Ω/km)": "Positive-sequence line reactance X1 / (Ω/km)",
    "线路零序电阻 R0 / (Ω/km)": "Zero-sequence line resistance R0 / (Ω/km)",
    "线路零序电抗 X0 / (Ω/km)": "Zero-sequence line reactance X0 / (Ω/km)",
    "断路器额定开断电流 Ik / kA（可留空）": "Rated breaker interrupting current Ik / kA (optional)",
    "基准容量 Sbase / MVA": "Base capacity Sbase / MVA",
    "基准电压 Ubase / kV（线电压）": "Base voltage Ubase / kV (line voltage)",
    "基准电压 Ubase / kV（通常 = UN）": "Base voltage Ubase / kV (typically = UN)",
    "中压侧额定容量 SN_M / MVA": "MV-side rated capacity SN_M / MVA",
    "单分裂导线电阻 r / (Ω/km)": "Single-subconductor resistance r / (Ω/km)",
    "单分裂导线 GMR / m": "Single-subconductor GMR / m",
    "单分裂导线半径 r / m": "Single-subconductor radius r / m",
    "分裂间距 d / m（n>1）": "Bundle spacing d / m (n > 1)",
    "地线半径 r / m": "Shield-wire radius r / m",
    "两侧相角差 φ / °": "Phase-angle difference between both sides φ / °",
    "回路电阻 RΣ / Ω": "Loop resistance RΣ / Ω",
    "回路电抗 XΣ / Ω": "Loop reactance XΣ / Ω",
    "总线路长度 / km": "Total line length / km",
    "统一功率因数 cosφ": "Uniform power factor cosφ",
    "功率因数类型": "Power-factor type",
    "额定载流量 / A": "Rated ampacity / A",
    "短时过载系数 K": "Short-time overload factor K",
    "合环时刻 / s": "Closure instant / s",
    "波形结束时刻 / s": "Waveform end time / s",
    "合环时刻": "Closure instant",
    "功率因数 cosφ": "Power factor cosφ",
    "高压额定电压": "HV rated voltage",
    "低压额定电压": "LV rated voltage",
    "低压侧下限": "LV-side lower limit",
    "低压侧上限": "LV-side upper limit",
    "电容器组数量": "Number of capacitor banks",
    "每组电容容量": "Per-bank capacitor rating",
    "电抗器组数量": "Number of reactor banks",
    "每组电抗容量": "Per-bank reactor rating",
    "有功潮流": "Active-power flow",
    "无功潮流": "Reactive-power flow",
    "显示通道：": "Displayed channels: ",
    "谐波次数": "Harmonic order",
    "T1 点号 = ": "T1 point No. = ",
    "结束时间必须大于起始时间。": "The end time must be greater than the start time.",
    "非周期分量：恒定直流=": "Aperiodic component: constant DC = ",
    "衰减直流": "decaying DC",
    "衰减时间常数": "decay time constant",
    "序分量（按前三个选中通道 RMS 估计）：正序=": "Sequence components (estimated from the RMS values of the first three selected channels): positive sequence = ",
    "，负序=": ", negative sequence = ",
    "，零序=": ", zero sequence = ",
    "，不平衡度=": ", unbalance = ",
    "网络模式": "Network mode",
    "故障类型": "Fault type",
    "配置：": "Configuration: ",
    "段号": "Section No.",
    "正常": "Normal",
    "超限": "Over limit",
    "点号": "Point No.",
    "未命名分组": "Unnamed group",
    "无数据": "No data",
    "型号/布置": "Model / arrangement",
    "计算模型：": "Calculation model: ",
    "AB 间距 = ": "AB spacing = ",
    "BC 间距 = ": "BC spacing = ",
    "CA 间距 = ": "CA spacing = ",
    "等效相导线电阻 = ": "Equivalent phase-conductor resistance = ",
    "等效相导线 GMR = ": "Equivalent phase-conductor GMR = ",
    "等效相导线半径 = ": "Equivalent phase-conductor radius = ",
    "每相、每公里的序参数": "Sequence parameters per phase per kilometer",
    "结论：正序参数可直接回填“架空线路”页，零序参数可同步回填“短路电流计算”页。": "Conclusion: the positive-sequence parameters can be written back directly to the Overhead Line page, and the zero-sequence parameters can be written back to the Short-Circuit Current Calculation page.",
    "各段稳态电流": "Steady-state currents of all sections",
    "故障点位置（距左侧）": "Fault-point position (from the left side)",
    "合环点两侧线电压矢量差": "Line-voltage phasor difference across the closure point",
    "瞬时峰值：环流 ": "Instantaneous peak: loop current ",
    "左侧总电流": "left-side total current",
    "右侧总电流": "right-side total current",
    "存在 ": "There are ",
    " 段超过稳态允许载流量。": " sections whose steady-state current exceeds the allowed ampacity.",
    "允许稳态载流上限 = ": "Allowed steady-state ampacity limit = ",
    "仿真周波数": "Number of simulated cycles",
    "SMIB 小扰动特征值分布：": "SMIB small-signal eigenvalue map: ",
})

PHRASE_ZH_TO_EN.update({
    "稳定性判断：": "Stability assessment:",
    "稳定性：": "Stability:",
    "向AI提问时会自动附带当前界面截图和算例摘要": "When you ask PowerTool AI, the current-page screenshot and numerical case summary are attached automatically.",
    "界面按“基础模型—AGC—结果”组织。默认参数对应常规机组一次调频算例；启用 AGC 后会自动放宽绘图时长。": "The page is organized as 'base model - AGC - results'. The default parameters correspond to a representative primary-frequency-control case; enabling AGC automatically extends the plotting duration.",
    "适用于单机与等值系统之间的小扰动初步核算。界面保留轻量输入，但使用更清晰的参数卡片与结果卡片布局。": "Suitable for a first-pass small-signal estimate for a single machine or an equivalent system. The page keeps a compact input set while using clearer parameter and result cards.",
    "界面改为“输入参数—结果说明”双栏结构，适合快速评估受端最低电压、最大有功传输与折算 MW 指标。": "This page uses a two-column layout of 'input parameters - result notes' and is suitable for quick evaluation of the receiving-end minimum voltage, maximum transferable active power, and the converted MW value.",
    "左侧保留线路额定电压、波阻抗、充电功率与长度等输入；右侧集中展示自然功率、无功平衡与实际运行偏离。": "The left panel keeps the line rated voltage, surge impedance, charging power, and length inputs; the right panel concentrates the natural power, reactive-power balance, and deviation from the actual operating point.",
    "将 AVC 页改为滚动输入卡片，减少长表单带来的压迫感；右侧单独显示 9 区策略判断、推荐档位与无功投切结果。": "The AVC page uses scrollable input cards to make the long form easier to handle; the right panel separately shows the nine-zone assessment, the recommended tap position, and the reactive switching result.",
    "左侧统一收纳等面积法与冲击法。上框侧重 P-δ 曲线及临界清除判断，下框用于快估功率振荡幅度。": "The left panel contains both the equal-area criterion and the impact method. The upper block emphasizes the P-δ curve and the critical-clearing assessment, while the lower block provides a quick estimate of the power-oscillation amplitude.",
    "图形区改为浅色工程图风格，重点突出故障前/中/后功角曲线与加减速面积。": "The plotting area uses a light engineering style and highlights the pre-fault, during-fault, and post-fault power-angle curves together with the accelerating and decelerating areas.",
    "提示：主分析采用 Kundur 六阶小扰动模型；1型 AVR/PSS 用于参数校核。": "Note: the main analysis uses Kundur's sixth-order small-signal model; the Type-1 AVR/PSS page is used for parameter validation.",
    "采用 Kundur 经典 SMIB 示例的六阶同步机模型；可切换“机组”“机组+AVR”“机组+AVR+PSS”三种配置。 新增“1型AVR/PSS模型”参数页（按教材框图）用于控制环节频域校核。 程序先由给定运行点构造平衡点，再对非线性模型数值线性化并求取特征值。": "This page uses Kundur's classical SMIB sixth-order synchronous-machine model. Three configurations are available: generator only, generator + AVR, and generator + AVR + PSS. A Type-1 AVR/PSS parameter page has been added for frequency-domain validation of the control blocks according to the textbook block diagram. The program first builds the equilibrium point from the specified operating point, then numerically linearizes the nonlinear model and computes its eigenvalues.",
    "页面按“系统与故障—线路参数—中性点与开断校核—显示设置”重构；左侧改为滚动表单，右侧增加关键指标摘要与更明亮的向量图。": "The page is organized as 'system and fault - line parameters - neutral grounding and breaker check - display settings'. The left side uses a scrollable form, while the right side adds a key-metric summary and brighter phasor plots.",
    "右侧结果区增加关键指标摘要，并将原有极坐标向量图改为浅底高对比版本，使表格、波形与相量关系更容易同时辨认。": "The right result panel adds a key-metric summary and redraws the original polar phasor plot on a light, high-contrast background so that the table, waveforms, and phasors are easier to read together.",
    "保持录波页原有的深色浏览风格，同时将左侧控制区整理为更清晰的白色操作面板。": "The waveform page keeps its original dark browsing style while reorganizing the left control area into a clearer white operation panel.",
    "输入区分为参数、连接点表与线段比例三部分，图形区则拆成稳态点位图与冲击暂态电流两页。": "The input area is divided into parameters, the connection-point table, and segment ratios; the plotting area is split into the steady-state topology view and the impact transient current view.",
    "结果区整理有名值、标幺值与参数校核结论。线路几何反算与典型参数窗口可作为辅助资料页。": "The result area organizes physical-unit values, per-unit values, and parameter-validation conclusions. The line-geometry back-calculation and typical-parameter window serve as supporting reference pages.",
    "右侧统一展示折算阻抗、励磁支路与参数校核结果，便于与铭牌试验数据进行快速比对。": "The right panel uniformly shows the converted impedances, the excitation branch, and the parameter-validation results, making fast comparison with nameplate test data easier.",
    "结果区统一展示折算到高压侧的 T 型等值参数、标幺阻抗与励磁支路校核结论，便于工程核对。": "The result area uniformly shows the T-equivalent parameters referred to the HV side, the per-unit impedances, and the excitation-branch validation results, making engineering cross-checks easier.",
    "输入约定：每个连接点填写净线电流（A）。正值表示负荷，负值表示分布式电源回送，0 表示空点。 合环点必须对应空点。线段比例默认均匀分布；若输入自定义比例，则按 N+1 个线段比例自动归一。": "Input convention: enter the net line current (A) at each connection point. Positive values denote load, negative values denote reverse power from distributed generation, and 0 denotes an empty point. The closure point must correspond to an empty point. Segment ratios are uniform by default; if custom ratios are entered, the N+1 segment ratios are normalized automatically.",
    "输入三相导线横坐标 x、离地高度 h、单分裂导线参数、土壤电阻率，以及是否设置地线。程序按三段完全换位平均：串联参数用复深度近似，电容/电纳用镜像法电位系数。地线若启用，则按连续接地导体并经 Kron 消去处理。": "Enter the x-coordinates of the three phase conductors, the heights above ground, the single-subconductor data, the soil resistivity, and whether a shield wire is present. The program assumes complete transposition averaged over three sections: the series parameters use the complex-depth approximation, while the capacitance/susceptance uses the method-of-images potential coefficients. If the shield wire is enabled, it is treated as a continuously grounded conductor and eliminated through Kron reduction.",
    "提示：左键定位 T1，右键定位 T2；可用于故障前后对比和时间差测量。": "Tip: left click places T1 and right click places T2; use them to compare pre-fault and post-fault behavior and to measure time differences.",
    "当前时间窗采样点不足，无法分析。": "The current time window contains too few samples for analysis.",
    "当前环境未安装 Pillow，未能自动截取界面截图。": "Pillow is not installed in the current environment, so the UI screenshot could not be captured automatically.",
    "已自动截取当前软件界面：": "The current software window was captured automatically: ",
    "自动截图失败：": "Automatic screenshot failed: ",
    "分析完成：": "Analysis completed: ",
    "调用失败，请检查本地模型/API 配置。": "The request failed. Please check the local-model/API configuration.",
    "调用失败，请检查日志与配置。": "The request failed. Please check the logs and configuration.",
    "Efd_min 必须小于 Efd_max。": "Efd_min must be smaller than Efd_max.",
    "Vsmin 必须小于 Vsmax。": "Vsmin must be smaller than Vsmax.",
    "请选择有效的小扰动模型配置。": "Please choose a valid small-signal model configuration.",
    "请先在主窗口左键设置 T1 光标，再进行序量分析。": "First place the T1 cursor in the main window with the left mouse button, and then run sequence analysis.",
    "请在序量分析窗口中至少完整设置一组三相电压或三相电流通道。": "In the sequence-analysis window, configure at least one complete three-phase voltage set or one complete three-phase current set.",
    "请至少选择一个通道。": "Please select at least one channel.",
    "请填写输出路径。": "Please enter an output path.",
    "已导出文件：\n": "Exported files:\n",
    "分裂根数必须为 1、2、3、4。": "The bundle count must be 1, 2, 3, or 4.",
    "线路参数计算窗口尚未初始化。": "The line-parameter calculation window has not been initialized yet.",
    "线路参数计算结果窗口未初始化。": "The line-parameter result window has not been initialized yet.",
    "请先在“线路参数计算”窗口中完成计算。": "Please complete the calculation in the line-parameter calculation window first.",
    "未输入断路器开断电流，未做匹配判断。": "No breaker interrupting current was entered, so no matching assessment was performed.",
    "匹配：额定开断电流 ≥ 计算开断电流。": "Match: rated interrupting current ≥ calculated interrupting current.",
    "不匹配：额定开断电流 < 计算开断电流。": "Mismatch: rated interrupting current < calculated interrupting current.",
    "连接点数量 N 必须为正整数。": "The number of connection points N must be a positive integer.",
    "连接点表或线段比例与当前 N 不一致，请先点击“按 N 重建表格”。": "The connection-point table or the segment ratios do not match the current N. Click 'Rebuild tables from N' first.",
    "未输入载流量上限。": "No ampacity limit was entered.",
    "按当前输入，上述各段稳态电流均未超过允许载流量。": "Under the current inputs, none of the steady-state currents in the sections exceeds the allowed ampacity.",
    "序分量提取：请选择至少 3 个相量/电流同类通道。": "Sequence-component extraction: select at least three channels of the same type (voltage phasors or currents).",
    "评估频率": "Evaluation frequency",
    "开环": "Open-loop",
    "闭环": "Closed-loop",
    "Efd 限幅区间": "Efd limiter range",
    "输入加权": "Input weighting",
    "Vs 估算": "Estimated Vs",
    "最弱阻尼模态": "Least-damped mode",
    "模态表": "Mode table",
    "故障前平衡角": "Pre-fault equilibrium angle",
    "故障切除角": "Fault-clearing angle",
    "不稳定平衡角": "Unstable equilibrium angle",
    "极限切除角": "Critical clearing angle",
    "极限切除时间": "Critical clearing time",
    "当前切除时间": "Current clearing time",
    "加速面积": "Accelerating area",
    "可用减速面积": "Available decelerating area",
    "实际减速面积": "Actual decelerating area",
    "实际最大摆角": "Actual maximum swing angle",
    "频率最低点时刻": "Time of the frequency minimum",
    "折算有名值": "Converted physical-unit value",
    "直流偏置时间常数": "DC-offset time constant",
    "开断校核电流": "Breaker-check current",
    "最大相电流": "Maximum phase current",
    "故障点电流向量图": "Fault-current phasor plot",
    "故障点电压向量图": "Fault-voltage phasor plot",
    "线路与序参数": "Line and sequence parameters",
    "连接点数量": "Number of connection points",
    "稳态电流": "Steady-state current",
    "功角曲线（等面积法）": "Power-angle curve (equal-area criterion)",
    "电压等级：": "Voltage level: ",
    "线路类型：": "Line type: ",
    "有名值": "Physical-unit values",
    "π型等值": "π equivalent",
    "T型等值": "T equivalent",
    "励磁电导": "Excitation conductance",
    "励磁电纳": "Excitation susceptance",
    "励磁回路": "Excitation block",
    "洗出时间": "Washout time",
    "洗出增益": "Washout gain",
    "放大倍数": "Gain",
    "零点": "Zero",
    "极点": "Pole",
    "仿真末端频差": "Frequency deviation at the end of the simulation",
    "末端滤波ACE": "Filtered ACE at the end",
    "末端二次调频出力": "Secondary-control output at the end",
    "阶次   频率/Hz   幅值(pk)    RMS       相角/°": "Order   Frequency/Hz   Magnitude(pk)   RMS   Phase angle/°",
    "环境变量 ": "Environment variable ",
})

TOKEN_ZH_TO_EN.update({
    "功率缺额": "Power deficit",
    "惯性": "Inertia",
    "时长": "duration",
    "时间常数": "time constant",
    "调频": "frequency control",
    "一次调频": "primary frequency control",
    "二次调频": "secondary frequency control",
    "频偏": "frequency deviation",
    "死区": "deadband",
    "比例": "proportional",
    "积分": "integral",
    "滤波": "filter",
    "主站": "master station",
    "执行": "actuation",
    "内电势": "internal EMF",
    "端电压": "terminal voltage",
    "送端": "sending-end",
    "受端": "receiving-end",
    "总电抗": "total reactance",
    "波阻抗": "surge impedance",
    "单位长度": "per-unit-length",
    "电感": "inductance",
    "电容": "capacitance",
    "充电功率": "charging power",
    "最小": "minimum",
    "最大": "maximum",
    "上限": "upper limit",
    "下限": "lower limit",
    "调节率": "regulation step",
    "电容器": "capacitor",
    "电抗器": "reactor",
    "组数量": "bank count",
    "每组": "per bank",
    "潮流": "power flow",
    "机械功率": "mechanical power",
    "加速功率": "accelerating power",
    "切除": "clearing",
    "平衡角": "equilibrium angle",
    "摆角": "swing angle",
    "预故障": "pre-fault",
    "线电压": "line voltage",
    "电势": "EMF",
    "角度": "angle",
    "故障前": "Pre-fault",
    "故障中": "During-fault",
    "故障后": "Post-fault",
    "中性点方式": "neutral-grounding mode",
    "方式": "mode",
    "开断": "interrupting",
    "校核": "validation",
    "周波数": "cycle count",
    "窗口": "window",
    "初始化": "initialized",
    "分裂根数": "bundle count",
    "横坐标": "horizontal coordinate",
    "高度": "height",
    "土壤电阻率": "soil resistivity",
    "电阻率": "resistivity",
    "导线": "conductor",
    "连接点": "connection point",
    "编号": "No.",
    "标签": "Label",
    "线段": "segment",
    "净电流": "net current",
    "稳态": "steady-state",
    "冲击暂态": "impact transient",
    "序号": "No.",
    "特征值": "eigenvalue",
    "独立模态": "independent modes",
    "实根": "real root",
    "非振荡模态": "non-oscillatory mode",
    "参考角平移": "reference-angle shift",
    "最低点时刻": "minimum-point time",
    "最低电压": "minimum voltage",
    "当前区间": "current zone",
    "调后": "after control",
    "动作量": "control action",
    "支路": "branch",
    "绕组": "winding",
    "空载损耗": "no-load loss",
    "空载电流": "no-load current",
    "短路损耗": "short-circuit loss",
    "等值": "equivalent",
    "限幅": "limit",
    "区间": "range",
    "估算": "estimated",
    "有名": "physical-unit",
    "折算": "converted",
    "截图": "screenshot",
    "软件界面": "software window",
    "通道名": "channel name",
    "采样点": "samples",
    "次谐波": "harmonic order",
    "序量": "sequence",
    "增益": "gain",
    "求和点": "summing junction",
    "传函": "transfer function",
    "频域": "frequency-domain",
    "界面": "UI",
    "算例": "case",
    "点位图": "topology view",
    "结果区": "result area",
})

for _k in ("前", "中", "后", "相", "高压", "低压"):
    TOKEN_ZH_TO_EN.pop(_k, None)


# Residual-string coverage identified from GUI inspection. / 针对 GUI 巡检残余字符串的补充覆盖。
DISPLAY_ZH_TO_EN.update({
    "切换到1型 AVR/PSS": "Switch to Type-1 AVR/PSS",
    "电枢电阻 ra / pu": "Armature resistance ra / pu",
    "同步电抗 xd / pu": "Synchronous reactance xd / pu",
    "同步电抗 xq / pu": "Synchronous reactance xq / pu",
    "暂态电抗 x'd / pu": "Transient reactance x'd / pu",
    "暂态电抗 x'q / pu": "Transient reactance x'q / pu",
    "次暂态电抗 x''d / pu": "Subtransient reactance x''d / pu",
    "次暂态电抗 x''q / pu": "Subtransient reactance x''q / pu",
    "开路 T'd0 / s": "Open-circuit T'd0 / s",
    "开路 T'q0 / s": "Open-circuit T'q0 / s",
    "开路 T''d0 / s": "Open-circuit T''d0 / s",
    "开路 T''q0 / s": "Open-circuit T''q0 / s",
    "阻尼 D / pu": "Damping D / pu",
    "测量时间 Tr / s": "Measurement time Tr / s",
    "一阶超前 T1 / s": "First lead T1 / s",
    "一阶滞后 T2 / s": "First lag T2 / s",
    "二阶超前 T3 / s": "Second lead T3 / s",
    "二阶滞后 T4 / s": "Second lag T4 / s",
    "传递函数框图（参考教材 1型 AVR/PSS）：": "Transfer-function block diagram (textbook Type-1 AVR/PSS reference):",
    "基准电压 Ubase / kV": "Base voltage Ubase / kV",
    "1）系统与导线数据": "1) System and conductor data",
    "频率 f / Hz": "Frequency f / Hz",
    "土壤电阻率 ρ / (Ω·m)": "Soil resistivity ρ / (Ω·m)",
    "分裂根数 n（4 根按正方形近似）": "Bundle count n (4 subconductors approximated as a square)",
    "说明：上述 r / GMR / 半径均指单根子导线数据。": "Note: the r / GMR / radius values above all refer to a single subconductor.",
    "2）三相导线几何坐标": "2) Three-phase conductor geometry",
    "A 相 x / m": "Phase-A x / m",
    "A 相 h / m": "Phase-A h / m",
    "B 相 x / m": "Phase-B x / m",
    "B 相 h / m": "Phase-B h / m",
    "C 相 x / m": "Phase-C x / m",
    "C 相 h / m": "Phase-C h / m",
    "3）地线（可选）": "3) Shield wire (optional)",
    "启用地线并计及屏蔽影响": "Enable the shield wire and include its shielding effect",
    "地线 x / m": "Shield-wire x / m",
    "地线 h / m": "Shield-wire h / m",
    "地线电阻 r / (Ω/km)": "Shield-wire resistance r / (Ω/km)",
    "地线 GMR / m": "Shield-wire GMR / m",
    "地线半径 r / m": "Shield-wire radius r / m",
    "地线按单根连续接地导体处理。": "The shield wire is treated as a single continuously grounded conductor.",
    "计算结果": "Calculation results",
    "故障点位置滑条（双电源）": "Fault-point position slider (two sources)",
    "直流时间常数": "DC time constant",
    "单电源+线路末端故障": "Single source + line-end fault",
    "三相短路≈0": "three-phase short circuit ≈ 0",
    "几何与等效数据": "Geometry and equivalent data",
})

PHRASE_ZH_TO_EN.update({
    "右侧绘图区与录波页保持相同的“图表 + 工具栏”组织形式，但改为浅色工程风格。": "The right plotting area keeps the same 'chart + toolbar' organization as the waveform page, but uses a light engineering style.",
    "右侧统一收纳摘要、点位图与冲击暂态电流波形。": "The right panel groups the summary, topology view, and impact-transient current waveforms.",
    "结果区强调固有频率、同步系数与线性化假设。与其它页统一为白色结果面板。": "The result area emphasizes the natural frequency, synchronizing coefficient, and linearization assumptions, and uses the same white result-panel style as the other pages.",
    "结果区强调稳定极限、受端最低电压与工程适用条件，便于与负荷水平或规划指标对照。": "The result area emphasizes the stability limit, the minimum receiving-end voltage, and the engineering applicability conditions, making comparison with loading levels or planning criteria easier.",
    "结果区按照自然功率、充电无功、实际潮流偏离三部分整理，更适合教学展示与方案初步核算。": "The result area is organized into natural power, charging reactive power, and deviation of the actual power flow, making it better suited for teaching demonstrations and first-pass engineering checks.",
    "结果区突出 AVC 当前区间、建议调压方向、档位与补偿设备动作。适合作为运行策略解释面板。": "The result area highlights the current AVC zone, the recommended voltage-control direction, the tap position, and the compensation-device action, making it suitable as an operating-strategy interpretation panel.",
    "提示：当前主分析模型为「": "Note: the current main analysis model is ",
    "」（Kundur 六阶线化）；如需 1型 AVR/PSS 请点击上方按钮切换到参数校核页。": " (Kundur sixth-order linearization). To inspect the Type-1 AVR/PSS model, click the button above to switch to the Parameter Validation page.",
    "说明：程序自动将无穷大母线相角平移为 0°；若 xL2≤0，则视为第二回线路停运。": "Note: the program automatically shifts the infinite-bus angle to 0°. If xL2 ≤ 0, the second line is treated as out of service.",
    "典型范围参考（§3.3/3.4）：R₁ 0.005~0.65 Ω/km，X₁ 0.20~0.42 Ω/km，C₁ 0.008~0.014 μF/km，Zc 240~420 Ω；超高压取下限，配电取上限。点击“线路参数计算”可由导线几何、土壤与地线数据反算 R₁/X₁/R₀/X₀/C₁/C₀。": "Typical reference ranges (§3.3/3.4): R₁ = 0.005–0.65 Ω/km, X₁ = 0.20–0.42 Ω/km, C₁ = 0.008–0.014 μF/km, and Zc = 240–420 Ω. Use the lower end for EHV/UHV lines and the upper end for distribution circuits. Click 'Line Parameter Calculation' to back-calculate R₁/X₁/R₀/X₀/C₁/C₀ from conductor geometry, soil resistivity, and shield-wire data.",
    "典型范围（§3.5）：Uk% 4~18%（特高压主变 18~24%），I₀% 0.1~5%，短路损耗 1~7 kW/MVA，空载损耗 0.1~3 kW/MVA。": "Typical ranges (§3.5): Uk% = 4–18% (18–24% for UHV main transformers), I₀% = 0.1–5%, short-circuit loss = 1–7 kW/MVA, and no-load loss = 0.1–3 kW/MVA.",
    "输入约定：Pk 为两两短路试验损耗（kW），Uk% 为两两短路电压（%）。Pk_HL、Uk_HL 若测试是在低压侧额定电流下做的，程序会自动按 SN_H/SN_L 折算到高压侧额定电流基准。": "Input convention: Pk is the pairwise short-circuit test loss (kW), and Uk% is the pairwise short-circuit voltage (%). If Pk_HL and Uk_HL were tested at the LV-side rated current, the program automatically refers them to the HV-side rated-current base using SN_H/SN_L.",
    "零序参数变化会联动刷新默认中性点参数；若已手工改写，则不会被再次覆盖。": "Changing the zero-sequence parameters refreshes the default neutral-grounding values. Once you edit them manually, they will no longer be overwritten.",
    "单电源模式自动锁定在 100%，双电源模式可拖动定位故障点。": "In single-source mode the slider is fixed at 100%, while in two-source mode it can be dragged to position the fault point.",
    "初始功角 δ0 = ": "Initial power angle δ0 = ",
    "同步转矩系数 K_s = ": "Synchronizing torque coefficient K_s = ",
    "（按本文近似定义）": " (as defined by the approximation used in this article)",
    "固有角频率 ω_n = ": "Natural angular frequency ω_n = ",
    "最大可送有功 P_L,max = ": "Maximum transferable active power P_L,max = ",
    "冲击量 Dp = ": "Impulse quantity Dp = ",
    "估算第一摆功率振荡幅值 ΔP_osc ≈ ": "Estimated first-swing power-oscillation amplitude ΔP_osc ≈ ",
    "电压判据：": "Voltage criterion: ",
    "估算低压侧 Vlv=": "Estimated LV-side Vlv = ",
    "限值[": "limits [",
    "复合序网计算结果": "Composite sequence-network result",
    "直流偏置时间常数 τ = ": "DC-offset time constant τ = ",
    "幾何与等效数据": "Geometry and equivalent data",
    "几何与等效数据": "Geometry and equivalent data",
})

TOKEN_ZH_TO_EN.update({
    "绘图区": "plotting area",
    "波形": "waveforms",
    "固有": "natural",
    "同步系数": "synchronizing coefficient",
    "工程适用条件": "engineering applicability conditions",
    "建议调压方向": "recommended voltage-control direction",
    "补偿设备": "compensation device",
    "主分析模型": "main analysis model",
    "六阶线化": "sixth-order linearization",
    "第二回线路停运": "second line out of service",
    "特高压": "UHV",
    "下限": "lower end",
    "上限": "upper end",
    "几何": "geometry",
    "单根子导线": "single subconductor",
    "末端故障": "line-end fault",
    "位置滑条": "position slider",
    "屏蔽影响": "shielding effect",
    "当前区间": "current zone",
    "限值": "limits",
    "第一摆": "first swing",
    "幅值": "amplitude",
    "参考教材": "textbook reference",
    "按本文近似定义": "as defined by the approximation used in this article",
    "总": "total ",
    "后": "after",
})
for _k in ("总", "后"):
    TOKEN_ZH_TO_EN.pop(_k, None)


# Final cleanup for remaining result-panel strings. / 对剩余结果面板字符串做最后清理。
DISPLAY_ZH_TO_EN.update({
    "计算冲击法": "Calculate Impact Method",
})

PHRASE_ZH_TO_EN.update({
    "有名值（π型等值，折算后）": "Physical-unit values (π equivalent, converted)",
    "总电阻 R = ": "Total resistance R = ",
    "总电抗 X = ": "Total reactance X = ",
    "有名值（折算到高压侧 ": "Physical-unit values (referred to the HV side ",
    "折算参考容量 SN_base = ": "Reference converted capacity SN_base = ",
    "折算基压 ": "Reference converted voltage ",
    "有名值（T型等值，折算到高压侧）": "Physical-unit values (T equivalent, referred to the HV side)",
    "折算到高压侧": "referred to the HV side",
    "折算后": "converted",
})


PHRASE_ZH_TO_EN.update({
    "总电阻  R  = ": "Total resistance R = ",
    "总电抗  X  = ": "Total reactance X = ",
    "对地电纳半值 B/2 = ": "Half shunt susceptance to ground B/2 = ",
    "波阻抗  Zc = ": "Surge impedance Zc = ",
})



# Residual English-UI cleanup after screenshot review. / 根据截图复核补充英文界面残余翻译。
DISPLAY_ZH_TO_EN.update({
    "AVR 传递函数结构图": "AVR transfer-function block diagram",
    "PSS 传递函数结构图": "PSS transfer-function block diagram",
    "1型 PSS 传递函数框图": "Type-1 PSS transfer-function block diagram",
    "1型 AVR 传递函数框图": "Type-1 AVR transfer-function block diagram",
    "单分裂导线电阻": "Single-subconductor resistance",
    "单分裂导线 GMR": "Single-subconductor GMR",
    "单分裂导线半径": "Single-subconductor radius",
    "分裂间距": "Bundle spacing",
    "地线半径": "Shield-wire radius",
    "单档调节率": "Tap-step regulation",
    "额定载流量": "Rated ampacity",
    "长度/km": "Length/km",
    "区间": "Range",
    "类型": "Type",
    "关键角度": "Key angles",
    "极限切除": "Critical clearing",
    "等面积": "Equal-area quantities",
})

PHRASE_ZH_TO_EN.update({
    "假设：单回架空线路、三相导线型号一致并按三段完全换位平均；": "Assumptions: single-circuit overhead line; the three phase conductors are identical and averaged over complete transposition in three sections; ",
    "串联参数用复深度近似计及土壤电阻率，大地回路电阻/电抗已包含在序阻抗内；": "the series parameters use the complex-depth approximation to include soil resistivity, and the earth-return resistance/reactance is already embedded in the sequence impedances; ",
    "对地电容/电纳采用镜像法电位系数矩阵，介质电导与土壤介电损耗未计。": "the capacitance/susceptance to ground is computed from the method-of-images potential-coefficient matrix, while dielectric conductance and soil dielectric loss are neglected.",
    "地线按连续接地导体处理，并通过 Kron 消去得到三相等值矩阵。": "The shield wire is treated as a continuously grounded conductor and eliminated through Kron reduction to obtain the three-phase equivalent matrix.",
    "当前计算未考虑地线屏蔽效应。": "The current calculation does not include the shielding effect of the shield wire.",
    "四分裂导线按正方形排列近似。": "A four-subconductor bundle is approximated by a square arrangement.",
    "标幺值（Sbase=": "Per-unit values (Sbase=",
    "基准阻抗 Zbase = ": "Base impedance Zbase = ",
    "基准导纳 Ybase = ": "Base admittance Ybase = ",
    "✓ 所有参数均在合理范围内。": "✓ All parameters are within reasonable ranges.",
    "左端合环前/后 = ": "Left-end current before/after closure = ",
    "右端合环前/后 = ": "Right-end current before/after closure = ",
    "段号  区间                         长度/km    合环前/A    合环后/A    相角/°   状态\n": "Section No.  Range                      Length/km  Before closure/A  After closure/A  Angle/°  Status\n",
    "本模块是配电网合环的工程近似工具：": "This module is an engineering approximation tool for distribution loop closure: ",
    "各连接点以净线电流表示，正值表示负荷、负值表示分布式电源回送；合环前默认同侧连接点具有统一功率因数。": "each connection point is represented by the net line current; positive values denote load, while negative values denote reverse power from distributed generation. Before closure, all connection points on the same side are assumed to have a uniform power factor.",
    "合环暂态采用单一 R-L 回路叠加法，适合环流、电流分布与保护配合的快速判断，不等价于 PSCAD/EMTP 或 Simulink 的详细电磁暂态仿真。": "The closure transient is approximated by a single R-L loop superposition method, which is suitable for quick assessment of loop current, current distribution, and protection coordination, but it is not equivalent to detailed electromagnetic-transient simulation in PSCAD/EMTP or Simulink.",
    "统一功率因数按 ": "The uniform power factor is taken as ",
    "）处理。": ").",
    "(Lagging)处理.": " (Lagging).",
    "(Leading)处理.": " (Leading).",
    "平衡点（以无穷大母线为角度参考）": "Operating point (with the infinite bus as the angle reference)",
    "模态表（仅列 Im(λ) ≥ 0 的独立模态）": "Mode table (only independent modes with Im(λ) ≥ 0)",
    "序号  特征值 λ / (1/s)                 f / Hz     ζ / %     类型\n": "No.  Eigenvalue λ / (1/s)             f / Hz     ζ / %     Type\n",
    "该模态为实根，非振荡模态。": "This mode is a real root and therefore non-oscillatory.",
    "模型采用 Kundur 示例 13.2 对应的六阶同步机、AVR III 与 PSS II 结构。": "The model uses the sixth-order synchronous generator from Kundur Example 13.2 together with the AVR III and PSS II structures.",
    "网络按 xT + (xline1 ∥ xline2) 的 SMIB 等值处理，并在平衡点处对非线性 ODE 进行中心差分数值线性化。": "The network is represented by the SMIB equivalent xT + (xline1 ∥ xline2), and the nonlinear ODEs are numerically linearized about the operating point by central differences.",
    "特征值以 1/s 给出，阻尼比按 -σ/|λ| 计算；参与因子用于识别主导状态。": "Eigenvalues are reported in 1/s, the damping ratio is computed as -σ/|λ|, and participation factors are used to identify the dominant states.",
    "关键角度": "Key angles",
    "极限切除": "Critical clearing",
    "极限切除角由闭式公式计算（需 Pmax_post ≠ Pmax_fault）；": "The critical clearing angle is obtained from the closed-form expression (requires Pmax_post ≠ Pmax_fault); ",
    "极限切除时间由 RK4 数值积分摆动方程得到。": "the critical clearing time is obtained by RK4 numerical integration of the swing equation.",
    "裕度 = (可用减速面积 − 加速面积) / 加速面积 × 100 %。": "margin = (available decelerating area − accelerating area) / accelerating area × 100 %.",
    "本模型为单机无穷大、忽略阻尼、机械功率恒定的经典假设。": "This model follows the classical single-machine-infinite-bus assumptions: damping is neglected and mechanical power is constant.",
    "受端最低电压（相对送端电压归一化）V_min/U_g = ": "Minimum receiving-end voltage (normalized to the sending-end voltage) V_min/U_g = ",
    "受端最低电压（与 U_g 同一基准）V_min = ": "Minimum receiving-end voltage (on the same base as U_g) V_min = ",
    "适用前提：二节点等值、送端电压刚性、忽略电阻、负荷功率因数近似恒定。": "Applicability assumptions: a two-bus equivalent, a stiff sending-end voltage, neglected resistance, and an approximately constant load power factor.",
    "若系统存在显著电阻、分接头动作、复杂无功补偿或多节点耦合，应改用潮流/连续潮流/QV-PV 分析。": "If the system has significant resistance, tap-changing action, complex reactive-power compensation, or multi-bus coupling, use power-flow / continuation-power-flow / QV-PV analysis instead.",
    "该公式给出的是小扰动主导机电模态频率的近似值。": "This formula gives an approximate value of the dominant electromechanical modal frequency in small-signal conditions.",
    "阻尼、参与因子以及互联系统模态耦合仍需特征值分析或时域仿真。": "Damping, participation factors, and inter-area modal coupling still require eigenvalue analysis or time-domain simulation.",
    "欠阻尼：存在典型“先下后回”的频率最低点。": "Underdamped: a typical frequency nadir exists, with the response dipping first and then recovering.",
    "最低点时刻采用 atan2 形式，避免普通 arctan 造成象限选错。": "The nadir time is computed using atan2 to avoid quadrant errors that can occur with a plain arctan.",
    "该参数组合不产生典型欠阻尼最低点。": "This parameter combination does not produce a typical underdamped frequency nadir.",
    "单调极限（稳态）Δf∞ = ": "Monotonic limit (steady state) Δf∞ = ",
    "初始频率变化率 RoCoF = ": "Initial frequency rate of change RoCoF = ",
    "对应频率 ": "corresponding frequency ",
    "二次调频（AGC-FFC）附加结果": "Additional results for secondary frequency control (AGC-FFC)",
    "ACE按定频率控制（FFC）仅考虑频偏项，主站指令到机组执行采用一阶滞后。": "In the fixed-frequency-control (FFC) formulation, ACE includes only the frequency-deviation term, and the master-station command to generator actuation is modeled as a first-order lag.",
    "两侧相角差 φ": "Phase-angle difference between both sides φ",
    "回路电阻 RΣ": "Loop resistance RΣ",
    "回路电抗 XΣ": "Loop reactance XΣ",
    "总线路长度": "Total line length",
    "波形结束时刻": "Waveform end time",
})

TOKEN_ZH_TO_EN.update({
    "处理": "treated",
})



# Mixed-string cleanup for partially translated runtime text. / 对部分已混译字符串做进一步清理。
PHRASE_ZH_TO_EN.update({
    "假设:": "Assumptions: ",
    "适用前提:": "Applicability assumptions: ",
    "单回Overhead Line": "single-circuit overhead line",
    "三相conductor型号一致并按三段完全换位平均": "the three phase conductors are identical and averaged over complete transposition in three sections",
    "串联参数用复深度近似计及soil resistivity": "the series parameters use the complex-depth approximation to include soil resistivity",
    "大地回路Resistance/Reactance已包含在序阻抗内": "the earth-return resistance/reactance is already embedded in the sequence impedances",
    "对地capacitance/Susceptance采用镜像法电位系数矩阵": "the capacitance/susceptance to ground is computed from the method-of-images potential-coefficient matrix",
    "介质电导与土壤介电损耗未计": "dielectric conductance and soil dielectric loss are neglected",
    "CurrentCalculate未考虑shield wire屏蔽效应": "The current calculation does not include the shielding effect of the shield wire",
    "四分裂conductor按正方形排列近似": "A four-subconductor bundle is approximated by a square arrangement",
    "基准Admittance Ybase = ": "Base admittance Ybase = ",
    "✓ 所有参数均在合理范围内.": "✓ All parameters are within reasonable ranges.",
    "Left endloop closure前/后 = ": "Left-end current before/after closure = ",
    "Right endloop closure前/后 = ": "Right-end current before/after closure = ",
    "Section No. range 长度/km loop closure前/A loop closure后/A Angle/° Status": "Section No.  Range                      Length/km  Before closure/A  After closure/A  Angle/°  Status",
    "本模块是Distribution Loop-Closure的工程近似工具: 各connection point以净线Current表示, 正Value表示负荷, 负Value表示分布式电源回送; loop closure前默认同侧connection point具有统一功率因数.": "This module is an engineering approximation tool for distribution loop closure: each connection point is represented by the net line current; positive values denote load, while negative values denote reverse power from distributed generation. Before closure, all connection points on the same side are assumed to have a uniform power factor.",
    "loop closure暂态采用单一 R-L 回路叠加法, 适loop closure流, Current分布与保护配合的快速判断, 不等价于 PSCAD/EMTP 或 Simulink 的详细电磁暂态仿真.": "The closure transient is approximated by a single R-L loop superposition method, which is suitable for quick assessment of loop current, current distribution, and protection coordination, but it is not equivalent to detailed electromagnetic-transient simulation in PSCAD/EMTP or Simulink.",
    "平衡点(以infinite bus为angle参考)": "Operating point (with the infinite bus as the angle reference)",
    "Mode table(仅列 Im(λ) ≥ 0 的independent modes)": "Mode table (only independent modes with Im(λ) ≥ 0)",
    "No. eigenvalue λ / (1/s) f / Hz ζ / % 类型": "No.  Eigenvalue λ / (1/s)             f / Hz     ζ / %     Type",
    "模型采用 Kundur 示例 13.2 对应的六阶同步机, AVR III 与 PSS II 结构.网络按 xT + (xline1 ∥ xline2) 的 SMIB equivalent处理, 并在平衡点处对非线性 ODE 进行中心差分数Value线性化.eigenvalue以 1/s 给出, damping ratio按 -σ/|λ| Calculate; 参与因子用于识别主导Status.": "The model uses the sixth-order synchronous generator from Kundur Example 13.2 together with the AVR III and PSS II structures. The network is represented by the SMIB equivalent xT + (xline1 ∥ xline2), and the nonlinear ODEs are numerically linearized about the operating point by central differences. Eigenvalues are reported in 1/s, the damping ratio is computed as -σ/|λ|, and participation factors are used to identify the dominant states.",
    "关键angle": "Key angles",
    "极限clearing": "Critical clearing",
    "Critical clearing angle由闭式公式Calculate(需 Pmax_post ≠ Pmax_fault);": "The critical clearing angle is obtained from the closed-form expression (requires Pmax_post ≠ Pmax_fault);",
    "Critical clearing time由 RK4 数Valueintegral摆动方程得到.": "The critical clearing time is obtained by RK4 numerical integration of the swing equation.",
    "本模型为单机无穷大, 忽略阻尼, mechanical power恒定的经典假设.": "This model follows the classical single-machine-infinite-bus assumptions: damping is neglected and mechanical power is constant.",
    "receiving-endminimum voltage(相对送terminal voltage归一化)V_min/U_g = ": "Minimum receiving-end voltage (normalized to the sending-end voltage) V_min/U_g = ",
    "receiving-endminimum voltage(与 U_g 同一基准)V_min = ": "Minimum receiving-end voltage (on the same base as U_g) V_min = ",
    "适用前提: 二节点equivalent, 送terminal voltage刚性, 忽略Resistance, 负荷功率因数近似恒定.": "Applicability assumptions: a two-bus equivalent, a stiff sending-end voltage, neglected resistance, and an approximately constant load power factor.",
    "若System存在显著Resistance, 分接头动作, 复杂Reactive Power补偿或多节点耦合, 应改用power flow/连续power flow/QV-PV analysis.": "If the system has significant resistance, tap-changing action, complex reactive-power compensation, or multi-bus coupling, use power-flow / continuation-power-flow / QV-PV analysis instead.",
    "该公式给出的是Small-Signal主导机电模态Frequency的近似Value.": "This formula gives an approximate value of the dominant electromechanical modal frequency in small-signal conditions.",
    "阻尼, 参与因子以及互联System模态耦合仍需eigenvalueanalysis或时域仿真.": "Damping, participation factors, and inter-area modal coupling still require eigenvalue analysis or time-domain simulation.",
    "初始Frequency变化率 RoCoF = ": "Initial frequency rate of change RoCoF = ",
    'Underdamped: 存在典型"先下后回"的FrequencyMinimum point.': 'Underdamped: a typical frequency nadir exists, with the response dipping first and then recovering.',
    "minimum-point time采用 atan2 形式, 避免普通 arctan 造成象限选错.": "The nadir time is computed using atan2 to avoid quadrant errors that can occur with a plain arctan.",
})

TOKEN_ZH_TO_EN.pop("处理", None)



# Additional GUI/result cleanup found during regression scanning. / 回归扫描中发现的额外界面与结果清理。
DISPLAY_ZH_TO_EN.update({
    "高压绕组": "HV winding",
    "中压绕组": "MV winding",
    "低压绕组": "LV winding",
    "故障点百分比": "Fault-point percentage",
})

PHRASE_ZH_TO_EN.update({
    "波阻抗 Z_c = ": "Surge impedance Z_c = ",
    "自然功率 P_N = ": "Natural power P_N = ",
    "线路无功估算 ΔQ_L = ": "Estimated line reactive power ΔQ_L = ",
    "LineReactive Powerestimated ΔQ_L = ": "Estimated line reactive power ΔQ_L = ",
    "该估算最适用于额定电压附近、无损或低损、无复杂串并联补偿的超高压长线路。": "This estimate is most suitable for EHV/UHV long lines operating near rated voltage, with no loss or low loss and without complex series/shunt compensation.",
    "实际电压偏离额定值时，线路充电无功应按 V² 修正。": "When the actual voltage deviates from the rated value, the line charging reactive power should be corrected in proportion to V².",
    "该estimated最适用于RatedVoltage附近, 无损或低损, 无复杂串并联补偿的超高压长Line.": "This estimate is most suitable for EHV/UHV long lines operating near rated voltage, with no loss or low loss and without complex series/shunt compensation.",
    "实际Voltage偏离RatedValue时, Line充电Reactive Power应按 V² 修正.": "When the actual voltage deviates from the rated value, the line charging reactive power should be corrected in proportion to V².",
    "合环点编号": "Closure point No.",
    "系统频率 / Hz": "System frequency / Hz",
    "提示：已切换到 1型 AVR/PSS 参数页，可直接输入参数并点击“计算1型 AVR/PSS 指标”。": "Hint: switched to the Type-1 AVR/PSS parameter page. You can enter the parameters directly and click 'Calculate Type-1 AVR/PSS metrics'.",
    "说明：该页按截图中的1型 AVR/PSS 传函进行环节校核，用于小扰动控制参数整定参考。": "Note: this page validates the control blocks according to the Type-1 AVR/PSS transfer function shown in the screenshot and is intended as a reference for small-signal controller tuning.",
    "当前内核模型：测量环节 1/(1+sT_r)，主调节器 K_0(1+sT_1)/(1+sT_2)，再串联励磁回路 1/(1+sT_e)。": "Current kernel model: measurement block 1/(1+sT_r), main regulator K_0(1+sT_1)/(1+sT_2), followed by the excitation block 1/(1+sT_e).",
    "当前内核模型含两级超前-滞后补偿与输出限幅；其输出 V_s 叠加到 AVR 求和点。": "The current kernel model includes two lead-lag compensation stages and output limiting; its output V_s is summed at the AVR summing junction.",
    "无功补偿总动作量 = ": "Total reactive-compensation action = ",
    "高压侧注入有功 P = ": "HV-side injected active power P = ",
    "高压侧注入无功 Q = ": "HV-side injected reactive power Q = ",
    "串联电抗附加无功压降 = ": "Additional reactive drop across the series reactance = ",
    "（反算 Uk% ≈ ": "(back-calculated Uk% ≈ ",
    "，输入 ": ", input ",
    "单分裂导线电阻": "Single-subconductor resistance",
    "单分裂导线 GMR": "Single-subconductor GMR",
    "单分裂导线半径": "Single-subconductor radius",
    "分裂间距": "Bundle spacing",
    "地线半径": "Shield-wire radius",
    "分裂根数控件未初始化。": "The bundle-count widget has not been initialized.",
    "两侧相角差 φ": "Phase-angle difference between both sides φ",
    "回路电阻 RΣ": "Loop resistance RΣ",
    "回路电抗 XΣ": "Loop reactance XΣ",
    "总线路长度": "Total line length",
    "波形结束时刻": "Waveform end time",
    "点": "Point",
})

# English key prefixes for highlighting. / 关键结论行的英文前缀。
KEY_CONCLUSION_PREFIXES_EN: tuple[str, ...] = (
    "Operating-region assessment:",
    "Stability assessment:",
    "Conclusion:",
    "Stability:",
    "Match:",
    "Mismatch:",
)

_ACTIVE_LANGUAGE = "zh"
_HOOKS_INSTALLED = False

# Original callables kept for one-time monkey patching. / 保存原始可调用对象以支持一次性猴子补丁。
_ORIG_AXES_SET_TITLE = Axes.set_title
_ORIG_AXES_SET_XLABEL = Axes.set_xlabel
_ORIG_AXES_SET_YLABEL = Axes.set_ylabel
_ORIG_AXES_TEXT = Axes.text
_ORIG_AXES_ANNOTATE = Axes.annotate
_ORIG_AXES_LEGEND = Axes.legend
_ORIG_MESSAGEBOX_SHOWERROR = messagebox.showerror
_ORIG_MESSAGEBOX_SHOWINFO = messagebox.showinfo
_ORIG_MESSAGEBOX_SHOWWARNING = messagebox.showwarning
_ORIG_FILEDIALOG_ASKOPENFILENAME = filedialog.askopenfilename
_ORIG_FILEDIALOG_ASKSAVEASFILENAME = filedialog.asksaveasfilename
_ORIG_TK_TITLE = tk.Tk.title
_ORIG_TOPLEVEL_TITLE = tk.Toplevel.title
_ORIG_TEXT_INSERT = tk.Text.insert


def normalize_language(language: str | None) -> str:
    """Normalize the language code. / 规范化语言代码。"""
    value = (language or "zh").strip().lower()
    return "en" if value.startswith("en") else "zh"


def set_active_language(language: str | None) -> str:
    """Set the active runtime language. / 设置当前运行时语言。"""
    global _ACTIVE_LANGUAGE
    _ACTIVE_LANGUAGE = normalize_language(language)
    return _ACTIVE_LANGUAGE


def active_language() -> str:
    """Return the active runtime language. / 返回当前运行时语言。"""
    return _ACTIVE_LANGUAGE


def _contains_cjk(text: str) -> bool:
    """Check whether text contains CJK characters. / 检查文本是否包含中日韩字符。"""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def logic_text(text: str | None, language: str | None = None) -> str:
    """Convert a display label to the internal logic label. / 将显示标签转换为内部逻辑标签。"""
    if text is None:
        return ""
    value = str(text)
    if normalize_language(language) != "en":
        return value
    reverse = {dst: src for src, dst in DISPLAY_ZH_TO_EN.items()}
    return reverse.get(value, value)


def display_text(text: str | None, language: str | None = None) -> str:
    """Convert a logic label to the current display label. / 将逻辑标签转换为当前显示标签。"""
    if text is None:
        return ""
    value = str(text)
    if normalize_language(language) != "en":
        return value
    return DISPLAY_ZH_TO_EN.get(value, translate_text(value, language))


def translate_text(text: Any, language: str | None = None) -> Any:
    """Translate common UI/result strings into English. / 将常见界面与结果字符串翻译为英文。"""
    lang = normalize_language(language or _ACTIVE_LANGUAGE)
    if lang != "en" or not isinstance(text, str) or not text:
        return text
    if not _contains_cjk(text):
        return text
    translated = text
    replacements: list[tuple[str, str]] = []
    for mapping in (PHRASE_ZH_TO_EN, DISPLAY_ZH_TO_EN, TOKEN_ZH_TO_EN):
        replacements.extend(mapping.items())
    for src, dst in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        translated = translated.replace(src, dst)

    translated = re.sub(r"([ABC])\s*相", r"Phase-\1", translated)
    translated = re.sub(r"([ABC])相", r"Phase-\1", translated)
    translated = re.sub(r"\b([ABC]) phase\b", r"Phase-\1", translated)
    translated = re.sub(r"(\d+)型", r"Type-\1", translated)

    translated = translated.replace("（", "(").replace("）", ")")
    translated = translated.replace("：", ": ")
    translated = translated.replace("，", ", ")
    translated = translated.replace("。", ".")
    translated = translated.replace("；", "; ")
    translated = translated.replace("、", ", ")
    translated = translated.replace("“", '"').replace("”", '"')
    translated = translated.replace("‘", "'").replace("’", "'")
    translated = translated.replace("【", "[").replace("】", "]")
    translated = translated.replace("  /", " /")
    translated = translated.replace(" .", ".")
    translated = re.sub(r":(?=[A-Za-z\[])", ": ", translated)
    translated = re.sub(r"\)(?=[A-Za-z])", ") ", translated)
    translated = re.sub(r"\s+\)", ")", translated)
    while "  " in translated:
        translated = translated.replace("  ", " ")
    return translated
def translate_values(values: Iterable[Any], language: str | None = None) -> tuple[Any, ...]:
    """Translate a widget value list. / 翻译控件取值列表。"""
    return tuple(display_text(value, language) if isinstance(value, str) else value for value in values)


def _translate_kwargs_text(kwargs: dict[str, Any], keys: tuple[str, ...] = ("title", "message", "text")) -> dict[str, Any]:
    """Translate selected keyword arguments. / 翻译选定的关键字参数。"""
    for key in keys:
        if key in kwargs and isinstance(kwargs[key], str):
            kwargs[key] = translate_text(kwargs[key])
    if "filetypes" in kwargs and isinstance(kwargs["filetypes"], (list, tuple)):
        translated_filetypes = []
        for item in kwargs["filetypes"]:
            if isinstance(item, (list, tuple)) and item:
                head = translate_text(item[0]) if isinstance(item[0], str) else item[0]
                translated_filetypes.append((head, *item[1:]))
            else:
                translated_filetypes.append(item)
        kwargs["filetypes"] = translated_filetypes
    return kwargs


def install_runtime_hooks() -> None:
    """Install runtime translation hooks once. / 一次性安装运行时翻译钩子。"""
    global _HOOKS_INSTALLED
    if _HOOKS_INSTALLED:
        return

    def _axes_set_title(self: Axes, label: str, *args: Any, **kwargs: Any):
        return _ORIG_AXES_SET_TITLE(self, translate_text(label), *args, **kwargs)

    def _axes_set_xlabel(self: Axes, xlabel: str, *args: Any, **kwargs: Any):
        return _ORIG_AXES_SET_XLABEL(self, translate_text(xlabel), *args, **kwargs)

    def _axes_set_ylabel(self: Axes, ylabel: str, *args: Any, **kwargs: Any):
        return _ORIG_AXES_SET_YLABEL(self, translate_text(ylabel), *args, **kwargs)

    def _axes_text(self: Axes, x: Any, y: Any, s: str, *args: Any, **kwargs: Any):
        return _ORIG_AXES_TEXT(self, x, y, translate_text(s), *args, **kwargs)

    def _axes_annotate(self: Axes, text: str, *args: Any, **kwargs: Any):
        return _ORIG_AXES_ANNOTATE(self, translate_text(text), *args, **kwargs)

    def _axes_legend(self: Axes, *args: Any, **kwargs: Any):
        if "title" in kwargs:
            kwargs["title"] = translate_text(kwargs["title"])
        legend = _ORIG_AXES_LEGEND(self, *args, **kwargs)
        if legend is not None:
            if legend.get_title() is not None:
                legend.get_title().set_text(translate_text(legend.get_title().get_text()))
            for text_obj in legend.get_texts():
                text_obj.set_text(translate_text(text_obj.get_text()))
        return legend

    def _showerror(title: str | None = None, message: str | None = None, **kwargs: Any):
        kwargs = _translate_kwargs_text(dict(kwargs))
        return _ORIG_MESSAGEBOX_SHOWERROR(translate_text(title), translate_text(message), **kwargs)

    def _showinfo(title: str | None = None, message: str | None = None, **kwargs: Any):
        kwargs = _translate_kwargs_text(dict(kwargs))
        return _ORIG_MESSAGEBOX_SHOWINFO(translate_text(title), translate_text(message), **kwargs)

    def _showwarning(title: str | None = None, message: str | None = None, **kwargs: Any):
        kwargs = _translate_kwargs_text(dict(kwargs))
        return _ORIG_MESSAGEBOX_SHOWWARNING(translate_text(title), translate_text(message), **kwargs)

    def _askopenfilename(*args: Any, **kwargs: Any):
        kwargs = _translate_kwargs_text(dict(kwargs))
        return _ORIG_FILEDIALOG_ASKOPENFILENAME(*args, **kwargs)

    def _asksaveasfilename(*args: Any, **kwargs: Any):
        kwargs = _translate_kwargs_text(dict(kwargs))
        return _ORIG_FILEDIALOG_ASKSAVEASFILENAME(*args, **kwargs)

    def _tk_title(self: tk.Tk, string: str | None = None):
        if string is None:
            return _ORIG_TK_TITLE(self)
        return _ORIG_TK_TITLE(self, translate_text(string))

    def _toplevel_title(self: tk.Toplevel, string: str | None = None):
        if string is None:
            return _ORIG_TOPLEVEL_TITLE(self)
        return _ORIG_TOPLEVEL_TITLE(self, translate_text(string))

    def _text_insert(self: tk.Text, index: str, chars: str, *args: Any):
        return _ORIG_TEXT_INSERT(self, index, translate_text(chars), *args)

    Axes.set_title = _axes_set_title
    Axes.set_xlabel = _axes_set_xlabel
    Axes.set_ylabel = _axes_set_ylabel
    Axes.text = _axes_text
    Axes.annotate = _axes_annotate
    Axes.legend = _axes_legend
    messagebox.showerror = _showerror
    messagebox.showinfo = _showinfo
    messagebox.showwarning = _showwarning
    filedialog.askopenfilename = _askopenfilename
    filedialog.asksaveasfilename = _asksaveasfilename
    tk.Tk.title = _tk_title
    tk.Toplevel.title = _toplevel_title
    tk.Text.insert = _text_insert
    _HOOKS_INSTALLED = True


def translate_widget_tree(widget: tk.Widget, language: str | None = None) -> None:
    """Translate existing Tk widgets recursively. / 递归翻译现有 Tk 控件。"""
    lang = normalize_language(language)
    if lang != "en":
        return

    try:
        if isinstance(widget, ttk.Notebook):
            for tab_id in widget.tabs():
                current_text = widget.tab(tab_id, "text")
                widget.tab(tab_id, text=display_text(current_text, lang))
        elif isinstance(widget, ttk.Treeview):
            for key in widget["columns"]:
                try:
                    current_text = widget.heading(key, option="text")
                    widget.heading(key, text=display_text(current_text, lang))
                except Exception:
                    pass
        elif isinstance(widget, ttk.Combobox):
            values = widget.cget("values")
            if values:
                widget.configure(values=translate_values(values, lang))
            current = widget.get().strip()
            if current:
                widget.set(display_text(logic_text(current, lang), lang))
        elif isinstance(widget, tk.Listbox):
            # Keep listbox content untouched because channel names may come from user data. / 列表框内容保留原样，避免误改用户通道名。
            pass
        elif isinstance(widget, (ttk.Label, ttk.Button, ttk.Checkbutton, ttk.Radiobutton, ttk.LabelFrame)):
            current_text = widget.cget("text")
            if current_text:
                widget.configure(text=display_text(current_text, lang))
        try:
            text_var_name = widget.cget("textvariable")
        except Exception:
            text_var_name = ""
        if text_var_name:
            try:
                current_value = widget.getvar(text_var_name)
                if isinstance(current_value, str) and current_value:
                    widget.setvar(text_var_name, display_text(current_value, lang))
            except Exception:
                pass
    except Exception:
        pass

    for child in widget.winfo_children():
        translate_widget_tree(child, lang)

