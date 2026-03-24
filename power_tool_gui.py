"""Tkinter GUI：负责界面、绘图与计算内核调用。"""


from __future__ import annotations


import math
import threading
from datetime import datetime
from pathlib import Path

import tkinter as tk


from tkinter import filedialog, messagebox, ttk


from tkinter.scrolledtext import ScrolledText


import matplotlib


import matplotlib.font_manager as _fm


import numpy as np


from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


from matplotlib.lines import Line2D
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle


from power_tool_common import InputError, _safe_float, _validate_positive, _validate_nonnegative, load_line_params_reference


from power_tool_params import _format_warnings, convert_2wt_to_pu, convert_3wt_to_pu, convert_line_to_pu


from power_tool_approximations import (
    electromechanical_frequency,
    first_order_frequency_response_value,
    frequency_response_summary,
    frequency_response_value,
    natural_power_and_reactive,
    static_voltage_stability,
)


from power_tool_faults import short_circuit_capacity


from power_tool_stability import critical_cut_angle_approx, equal_area_criterion, impact_method


from power_tool_smib import (
    _SMIB_CONFIG_KEY,
    _SMIB_CONFIG_OPTIONS,
    _SMIB_STATE_LABELS,
    _format_eigenvalue,
    _smib_modal_rows,
    kundur_smib_defaults,
    smib_small_signal_analysis,
)

from power_tool_line_geometry import calculate_overhead_line_sequence
from power_tool_ai import PowerToolAIError, api_key_status, ask_ai, config_path, load_ai_config
from power_tool_loop_closure import loop_closure_analysis
from power_tool_comtrade import (
    estimate_sampling_rate,
    fourier_summary,
    parse_waveform_file,
    prony_like_summary,
    sequence_components,
    sequence_phasors,
    single_frequency_phasor,
)


# ── 中文字体配置 ──────────────────────────────────────────────────────────────
_CN_FONT_CANDIDATES = [
    "WenQuanYi Zen Hei",
    "WenQuanYi Micro Hei",
    "Noto Sans CJK JP",
    "Noto Serif CJK JP",
    "SimHei",
    "SimSun",
    "Microsoft YaHei",
    "AR PL UMing CN",
]

_available_fonts = {f.name for f in _fm.fontManager.ttflist}
_cn_font = next((f for f in _CN_FONT_CANDIDATES if f in _available_fonts), None)

if _cn_font:
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = [_cn_font] + matplotlib.rcParams["font.sans-serif"]

matplotlib.rcParams["axes.unicode_minus"] = False
# ─────────────────────────────────────────────────────────────────────────────

_KEY_CONCLUSION_PREFIXES = (
    "运行区间判断：",
    "稳定性判断：",
    "结论：",
    "稳定性：",
    "匹配：",
    "不匹配：",
)


def _detect_key_conclusion_lines(text: str) -> list[int]:
    """识别结果文本中的关键性结论行，用于红色高亮。"""
    rows: list[int] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped and any(stripped.startswith(prefix) for prefix in _KEY_CONCLUSION_PREFIXES):
            rows.append(idx)
    return rows


def _notebook_style_spec() -> dict[str, dict[str, object]]:
    """Notebook 样式规格：选中标签不缩小，并以深蓝色区分。"""
    return {
        "configure": {
            "TNotebook": {"background": "#f3f5f7", "borderwidth": 0},
            "TNotebook.Tab": {"padding": (16, 8), "borderwidth": 1},
        },
        "map": {
            "padding": [("selected", (16, 8)), ("!selected", (16, 8))],
            "expand": [("selected", (0, 0, 0, 0)), ("!selected", (0, 0, 0, 0))],
            "background": [("selected", "#173f7a"), ("!selected", "#dfe5ec")],
            "foreground": [("selected", "#ffffff"), ("!selected", "#1e2b37")],
        },
    }


def _format_polar_complex(z: complex, unit: str = "") -> str:
    mag = abs(z)
    ang = math.degrees(math.atan2(z.imag, z.real))
    suffix = f" {unit}" if unit else ""
    return f"{mag:.2f} ∠ {ang:+.2f}°{suffix}"


def _draw_block(ax, x: float, y: float, w: float, h: float, text: str, fontsize: int = 10) -> None:
    rect = Rectangle((x, y), w, h, fill=False, linewidth=1.2)
    ax.add_patch(rect)
    ax.text(x + w / 2.0, y + h / 2.0, text, ha="center", va="center", fontsize=fontsize)


def _draw_sum_node(ax, x: float, y: float, r: float = 0.22) -> None:
    circle = Circle((x, y), r, fill=False, linewidth=1.2)
    ax.add_patch(circle)
    ax.text(x, y, "Σ", ha="center", va="center", fontsize=12)


def _draw_signal_arrow(ax, x1: float, y1: float, x2: float, y2: float, text: str | None = None, dy: float = 0.18) -> None:
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", linewidth=1.2))
    if text:
        ax.text((x1 + x2) / 2.0, (y1 + y2) / 2.0 + dy, text, ha="center", va="center", fontsize=10)


def _draw_avr_transfer_diagram(ax) -> None:
    ax.clear()
    ax.set_xlim(0, 10.8)
    ax.set_ylim(0, 3.2)
    ax.axis("off")

    ax.text(0.2, 2.9, "AVR 传递函数结构图", fontsize=11, fontweight="bold", ha="left")
    _draw_block(ax, 1.6, 1.5, 1.8, 0.8, "1\n──────\n1+sT_r")
    _draw_sum_node(ax, 4.5, 1.9)
    _draw_block(ax, 5.2, 1.5, 2.0, 0.8, "K_0 · 1+sT_1\n──────────\n  1+sT_2")
    _draw_block(ax, 7.8, 1.5, 1.3, 0.8, "1\n────\n1+sT_e")

    _draw_signal_arrow(ax, 0.4, 1.9, 1.6, 1.9, "E_t")
    _draw_signal_arrow(ax, 3.4, 1.9, 4.28, 1.9, "v_m")
    _draw_signal_arrow(ax, 4.72, 1.9, 5.2, 1.9)
    _draw_signal_arrow(ax, 7.2, 1.9, 7.8, 1.9)
    _draw_signal_arrow(ax, 9.1, 1.9, 10.3, 1.9, "v_f")

    ax.annotate("", xy=(4.5, 2.12), xytext=(4.5, 2.9), arrowprops=dict(arrowstyle="->", linewidth=1.0))
    ax.text(4.62, 2.74, "+  V_ref", fontsize=10, va="center")
    ax.annotate("", xy=(4.5, 1.68), xytext=(4.5, 0.55), arrowprops=dict(arrowstyle="->", linewidth=1.0))
    ax.text(4.62, 0.95, "+  V_s", fontsize=10, va="center")
    ax.text(4.08, 1.55, "−", fontsize=12, va="center")
    ax.text(4.56, 2.02, "+", fontsize=12, va="center")
    ax.text(4.56, 1.60, "+", fontsize=12, va="center")
    ax.text(0.2, 0.20, "当前内核模型：测量环节 1/(1+sT_r)，主调节器 K_0(1+sT_1)/(1+sT_2)，再串联励磁回路 1/(1+sT_e)。", fontsize=9, ha="left")


def _draw_pss_transfer_diagram(ax) -> None:
    ax.clear()
    ax.set_xlim(0, 11.4)
    ax.set_ylim(0, 2.8)
    ax.axis("off")

    ax.text(0.2, 2.45, "PSS 传递函数结构图", fontsize=11, fontweight="bold", ha="left")
    _draw_block(ax, 1.1, 1.1, 1.1, 0.7, "K_w")
    _draw_block(ax, 2.8, 1.1, 1.7, 0.7, "sT_w\n──────\n1+sT_w")
    _draw_block(ax, 5.1, 1.1, 2.1, 0.7, "1+sT_1\n────────\n1+sT_2")
    _draw_block(ax, 7.9, 1.1, 2.1, 0.7, "1+sT_3\n────────\n1+sT_4")

    _draw_signal_arrow(ax, 0.2, 1.45, 1.1, 1.45, "Δω")
    _draw_signal_arrow(ax, 2.2, 1.45, 2.8, 1.45)
    _draw_signal_arrow(ax, 4.5, 1.45, 5.1, 1.45)
    _draw_signal_arrow(ax, 7.2, 1.45, 7.9, 1.45)
    _draw_signal_arrow(ax, 10.0, 1.45, 11.0, 1.45, "V_s")
    ax.text(0.2, 0.22, "当前内核模型含两级超前-滞后补偿与输出限幅；其输出 V_s 叠加到 AVR 求和点。", fontsize=9, ha="left")


class ApproximationToolGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("电力系统近似公式工程工具")
        self.geometry("1660x930")
        self.minsize(1400, 820)
        self._configure_styles()
        self.ai_config = load_ai_config()
        self._latest_ai_screenshot: Path | None = None
        self._ai_busy = False

        self.columnconfigure(0, weight=5)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        self.main_notebook = ttk.Notebook(self)
        self.main_notebook.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)

        notebook = self.main_notebook
        self.freq_tab = ttk.Frame(notebook)
        self.osc_tab = ttk.Frame(notebook)
        self.volt_tab = ttk.Frame(notebook)
        self.impact_tab = ttk.Frame(notebook)
        self.smib_tab = ttk.Frame(notebook)
        self.loop_tab = ttk.Frame(notebook)
        self.param_tab = ttk.Frame(notebook)
        self.sc_tab = ttk.Frame(notebook)
        self.comtrade_tab = ttk.Frame(notebook)

        notebook.add(self.freq_tab, text="频率动态")
        notebook.add(self.osc_tab, text="机电振荡")
        notebook.add(self.volt_tab, text="电压无功分析")
        notebook.add(self.impact_tab, text="暂稳评估")
        notebook.add(self.smib_tab, text="小扰动分析（SMIB）")
        notebook.add(self.loop_tab, text="配电网合环分析")
        notebook.add(self.param_tab, text="参数校核与标幺值")
        notebook.add(self.sc_tab, text="短路电流计算")
        notebook.add(self.comtrade_tab, text="录波曲线")

        self._line_geometry_window: tk.Toplevel | None = None
        self._line_geometry_entries: dict[str, ttk.Entry] = {}
        self._line_geometry_ground_widgets: list[tk.Widget] = []
        self._line_geometry_has_gw_var: tk.BooleanVar | None = None
        self._line_geometry_bundle_var: tk.StringVar | None = None
        self._line_geometry_result: ScrolledText | None = None
        self._line_geometry_last_result = None
        self._line_geometry_fig = None
        self._line_geometry_canvas = None
        self._line_geometry_ax = None

        self._build_frequency_tab()
        self._build_oscillation_tab()
        self._build_voltage_tab()
        self._build_impact_tab()
        self._build_smib_tab()
        self._build_loop_closure_tab()
        self._build_param_tab()
        self._build_short_circuit_tab()
        self._build_comtrade_tab()
        self._build_ai_sidebar()
        self.main_notebook.bind("<<NotebookTabChanged>>", self._on_ai_context_changed)

    @staticmethod
    def _add_entry(parent: ttk.Frame,
                   row: int,
                   label: str,
                   default: str,
                   column: int = 0,
                   width: int = 14) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=4, pady=4)
        entry = ttk.Entry(parent, width=width)
        entry.grid(row=row, column=column + 1, sticky="ew", padx=4, pady=4)
        entry.insert(0, default)
        return entry

    @staticmethod
    def _set_text(widget: ScrolledText, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.tag_delete("key_conclusion")
        widget.tag_configure("key_conclusion", foreground="#c00000")
        widget.insert(tk.END, text)
        for line_no in _detect_key_conclusion_lines(text):
            widget.tag_add("key_conclusion", f"{line_no}.0", f"{line_no}.end")
        widget.configure(state="disabled")

    def _configure_styles(self) -> None:
        bg = "#f3f5f7"
        panel = "#ffffff"
        self.configure(bg=bg)

        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=panel)
        style.configure("TLabel", background=bg)
        style.configure("Card.TLabel", background=panel)
        style.configure("TLabelframe", background=bg, padding=8)
        style.configure("TLabelframe.Label", background=bg, font=("TkDefaultFont", 10, "bold"))

        notebook_spec = _notebook_style_spec()
        for style_name, options in notebook_spec["configure"].items():
            style.configure(style_name, **options)
        style.map("TNotebook.Tab", **notebook_spec["map"])

        style.configure("TButton", padding=(10, 5))
        style.configure("TEntry", padding=3)
        style.configure("TCombobox", padding=2)

    @staticmethod
    def _set_enabled(widgets: list[tk.Widget], enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for widget in widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass

    @staticmethod
    def _slice_time_window(time_s: np.ndarray, start_s: float, end_s: float) -> np.ndarray:
        if time_s.size == 0:
            return np.array([], dtype=int)
        start_s = max(float(time_s[0]), float(start_s))
        end_s = min(float(time_s[-1]), float(end_s))
        if end_s <= start_s:
            end_s = min(float(time_s[-1]), start_s + max(float(time_s[-1] - time_s[0]) * 0.02, 1e-4))
        mask = (time_s >= start_s) & (time_s <= end_s)
        idx = np.flatnonzero(mask)
        if idx.size < 2:
            lo = int(np.searchsorted(time_s, start_s, side="left"))
            hi = int(np.searchsorted(time_s, end_s, side="right"))
            idx = np.arange(max(0, lo - 1), min(time_s.size, hi + 1))
        return idx

    def _build_ai_sidebar(self) -> None:
        panel = ttk.Frame(self, padding=10, style="Card.TFrame")
        panel.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(4, weight=1)

        ttk.Label(panel, text="PowerTool AI", style="Card.TLabel",
                  font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            panel,
            text="向AI提问时会自动附带当前界面截图和算例摘要",
            style="Card.TLabel", justify="left", wraplength=360,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 8))

        self.ai_status_var = tk.StringVar(value=self._ai_status_summary())
        ttk.Label(panel, textvariable=self.ai_status_var, style="Card.TLabel", justify="left",
                  wraplength=360).grid(row=2, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(panel, text="提问", style="Card.TLabel", font=("TkDefaultFont", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(4, 4))
        self.ai_think_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel, text="启用思考模式", variable=self.ai_think_var).grid(row=3, column=0, sticky="e", pady=(4, 4))
        self.ai_question = ScrolledText(panel, width=44, height=9, wrap=tk.WORD)
        self.ai_question.grid(row=4, column=0, sticky="nsew")
        self.ai_question_placeholder = "请结合当前界面，解释这个算例的意义、关键结果和下一步建议。"
        self.ai_question.insert("1.0", self.ai_question_placeholder)

        action = ttk.Frame(panel, style="Card.TFrame")
        action.grid(row=5, column=0, sticky="ew", pady=(8, 6))
        action.columnconfigure(0, weight=1)
        action.columnconfigure(1, weight=1)
        ttk.Button(action, text="发送到 PowerTool AI", command=self._ask_power_tool_ai).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(action, text="填入当前算例摘要", command=self._insert_current_case_summary).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(panel, text="AI 回复", style="Card.TLabel", font=("TkDefaultFont", 10, "bold")).grid(row=6, column=0, sticky="w", pady=(4, 4))
        self.ai_answer = ScrolledText(panel, width=44, height=18, wrap=tk.WORD)
        self.ai_answer.grid(row=7, column=0, sticky="nsew")
        self.ai_answer.insert("1.0", "PowerTool AI 已就绪。")
        self.ai_answer.configure(state="disabled")

        panel.rowconfigure(7, weight=1)


    def _clear_ai_context(self) -> None:
        self.ai_question.delete("1.0", tk.END)
        self.ai_answer.configure(state="normal")
        self.ai_answer.delete("1.0", tk.END)
        self.ai_answer.insert("1.0", "")
        self.ai_answer.configure(state="disabled")

    def _on_ai_context_changed(self, _event: object | None = None) -> None:
        self._clear_ai_context()
        self.ai_status_var.set(self._ai_status_summary())

    def _ai_status_summary(self) -> str:
        return (
            f"配置文件：{config_path().name}\n"
            f"当前模式：{self.ai_config.provider.mode}\n"
            f"{api_key_status(self.ai_config)}"
        )

    def _reload_ai_config(self) -> None:
        self.ai_config = load_ai_config()
        self.ai_status_var.set(self._ai_status_summary())

    def _set_ai_answer(self, text: str) -> None:
        self.ai_answer.configure(state="normal")
        self.ai_answer.delete("1.0", tk.END)
        self.ai_answer.insert(tk.END, text)
        self.ai_answer.configure(state="disabled")

    def _current_tab_name(self) -> str:
        return self.main_notebook.tab(self.main_notebook.select(), "text")

    def _tab_numeric_summary(self) -> str:
        tab = self._current_tab_name()
        if tab == "频率动态":
            pairs = [("额定频率 f0 / Hz", self.freq_f0), ("功率缺额 ΔP_OL0 / pu", self.freq_dp), ("系统惯性时间常数 T_s / s", self.freq_ts),
                     ("一次调频时间常数 T_G / s", self.freq_tg), ("负荷频率系数 k_D / pu/pu", self.freq_kd), ("一次调频系数 k_G / pu/pu", self.freq_kg),
                     ("绘图时长 / s", self.freq_tend), ("AGC比例 Kp", self.freq_kp_agc), ("AGC积分 Ki", self.freq_ki_agc)]
        elif tab == "机电振荡":
            pairs = [("内电势 E'_q / pu", self.osc_eq), ("端电压 U / pu", self.osc_u), ("等值电抗 X_Σ / pu", self.osc_x), ("初始有功 P0 / pu", self.osc_p0),
                     ("惯性时间常数 T_j / s", self.osc_tj), ("同步频率 f0 / Hz", self.osc_f0)]
        elif tab == "电压无功分析":
            current = self._vr_notebook.tab(self._vr_notebook.select(), "text")
            if current == "静态电压稳定":
                pairs = [("送端电压 U_g / pu", self.volt_ug), ("总电抗 X_Σ / pu", self.volt_x), ("功率因数 cosφ", self.volt_pf), ("容量基准 S_base / MVA", self.volt_sbase)]
            elif current == "线路自然功率与无功":
                pairs = [("线路额定电压 U / kV", self.line_u), ("波阻抗 Z_c / Ω", self.line_zc), ("单位长度电感 L", self.line_l), ("单位长度电容 C", self.line_c),
                         ("实际传输有功 P / MW", self.line_p), ("单位长度充电功率 Q_N / (Mvar/km)", self.line_qn), ("线路长度 l / km", self.line_len)]
            else:
                pairs = [("高压侧当前电压 / kV", self.avc_vh), ("有功潮流 P / MW", self.avc_p), ("无功潮流 Q / Mvar", self.avc_q), ("当前档位", self.avc_tap_now)]
            header = f"电压无功子标签: {current}"
            return header + "\n" + "\n".join(f"{name}: {entry.get().strip()}" for name, entry in pairs)
        elif tab == "暂稳评估":
            pairs = [("冲击法 ΔPa / pu", self.imp_dp), ("冲击法 Δt / s", self.imp_dt), ("冲击法 f_d / Hz", self.imp_fd),
                     ("冲击法 Pm / pu", self.imp_pcur), ("等面积法 Pm / pu", self.eac_pm), ("等面积法 Pmax_pre / pu", self.eac_ppre),
                     ("等面积法 Pmax_fault / pu", self.eac_pf), ("等面积法 Pmax_post / pu", self.eac_ppost), ("等面积法 Δt / s", self.eac_dt)]
        elif tab == "小扰动分析（SMIB）":
            lines = [f"模型配置: {self.smib_config.get().strip()}"]
            for key, entry in self.smib_entries.items():
                lines.append(f"{key}: {entry.get().strip()}")
            return "\n".join(lines)
        elif tab == "配电网合环分析":
            pairs = [("连接点数量 N", self.loop_n), ("U1 / kV", self.loop_u1), ("U2 / kV", self.loop_u2), ("相角 φ / °", self.loop_angle), ("系统频率 / Hz", self.loop_freq)]
        elif tab == "参数校核与标幺值":
            current = self.param_notebook.tab(self.param_notebook.select(), "text")
            if current == "架空线路":
                pairs = [("线路额定电压 U_base / kV", self.lp_ubase), ("容量基准 S_base / MVA", self.lp_sbase), ("线路长度 l / km", self.lp_len),
                         ("R1 / Ω/km", self.lp_r1), ("X1 / Ω/km", self.lp_x1), ("C1 / μF/km", self.lp_c1)]
            elif current == "两绕组变压器":
                pairs = [("S_base / MVA", self.tx2_sbase), ("额定容量 SN / MVA", self.tx2_sn), ("额定电压 UN / kV", self.tx2_un),
                         ("Uk / %", self.tx2_uk), ("Pk / kW", self.tx2_pk), ("I0 / %", self.tx2_i0), ("P0 / kW", self.tx2_p0), ("Ubase / kV", self.tx2_ubase)]
            else:
                pairs = [("S_base / MVA", self.tx3_sbase), ("Ubase / kV", self.tx3_ubase), ("SN_H / MVA", self.tx3_sn_h), ("UN_H / kV", self.tx3_un_h),
                         ("SN_M / MVA", self.tx3_sn_m), ("SN_L / MVA", self.tx3_sn_l), ("Uk_HM / %", self.tx3_uk_hm), ("Uk_HL / %", self.tx3_uk_hl), ("Uk_ML / %", self.tx3_uk_ml)]
            header = f"参数页子标签: {current}"
            return header + "\n" + "\n".join(f"{name}: {entry.get().strip()}" for name, entry in pairs)
        elif tab == "短路电流计算":
            pairs = [("系统电压 / kV", self.sc_u), ("线路长度 / km", self.sc_len), ("R1 / Ω/km", self.sc_r1), ("X1 / Ω/km", self.sc_x1),
                     ("R0 / Ω/km", self.sc_r0), ("X0 / Ω/km", self.sc_x0), ("左侧中性点电阻 / Ω", self.sc_rn), ("故障电阻 / Ω", self.sc_rf),
                     ("右侧相角 / °", self.sc_delta_right), ("故障点位置 / %", self.sc_fault_pos)]
        elif tab == "录波曲线":
            return f"当前录波文件: {getattr(self, '_comtrade_cfg_path', '') or '未载入'}\n当前时间窗: {self.comtrade_time_label.cget('text')}"
        else:
            return "当前页暂未定义数值摘要。"
        return "\n".join(f"{name}: {entry.get().strip()}" for name, entry in pairs)

    def _insert_current_case_summary(self) -> None:
        summary = self._tab_numeric_summary()
        self.ai_question.delete("1.0", tk.END)
        self.ai_question.insert("1.0", f"请结合当前界面分析：\n\n{summary}\n")

    def _capture_current_ui(self) -> tuple[Path | None, str]:
        cache_dir = Path(__file__).resolve().with_name(".power_tool_ai_cache")
        cache_dir.mkdir(exist_ok=True)
        filename = cache_dir / f"ui_capture_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
        try:
            from PIL import ImageGrab  # type: ignore
        except Exception:
            return None, "当前环境未安装 Pillow，未能自动截取界面截图。"
        try:
            self.update_idletasks()
            x0 = self.winfo_rootx()
            y0 = self.winfo_rooty()
            x1 = x0 + self.winfo_width()
            y1 = y0 + self.winfo_height()
            image = ImageGrab.grab(bbox=(x0, y0, x1, y1))
            image.save(filename)
            self._latest_ai_screenshot = filename
            return filename, f"已自动截取当前软件界面：{filename.name}"
        except Exception as exc:
            return None, f"自动截图失败：{exc}"

    def _ask_power_tool_ai(self) -> None:
        if self._ai_busy:
            return
        question = self.ai_question.get("1.0", tk.END).strip()
        if not question:
            messagebox.showinfo("PowerTool AI", "请输入问题后再发送。")
            return
        self._reload_ai_config()
        tab_name = self._current_tab_name()
        case_text = self._tab_numeric_summary()
        screenshot_path, screenshot_note = self._capture_current_ui()
        self._ai_busy = True
        self.ai_status_var.set(f"PowerTool AI 正在分析：{tab_name}")
        self._set_ai_answer("PowerTool AI 正在处理中，请稍候…")

        def worker() -> None:
            try:
                answer = ask_ai(self.ai_config, question, tab_name, case_text, screenshot_note, screenshot_path, think=self.ai_think_var.get())
                status = f"分析完成：{tab_name}"
            except PowerToolAIError as exc:
                answer = f"PowerTool AI 调用失败：\n{exc}"
                status = "调用失败，请检查本地模型/API 配置。"
            except Exception as exc:
                answer = f"PowerTool AI 发生未预期异常：\n{exc}"
                status = "调用失败，请检查日志与配置。"

            def finish() -> None:
                self._ai_busy = False
                self.ai_status_var.set(f"{status}\n当前截图：{screenshot_note}\n{self._ai_status_summary()}")
                self._set_ai_answer(answer)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def _build_frequency_tab(self) -> None:
        self.freq_tab.columnconfigure(1, weight=1)
        self.freq_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.freq_tab, padding=10)
        right = ttk.Frame(self.freq_tab, padding=10)
        left.grid(row=0, column=0, sticky="nsw")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(left, text="二阶频率动态（含一次调频）", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        self.freq_f0 = self._add_entry(left, 1, "额定频率 f0 / Hz", "50")
        self.freq_dp = self._add_entry(left, 2, "功率缺额 ΔP_OL0 / pu", "0.08")
        self.freq_ts = self._add_entry(left, 3, "系统惯性时间常数 T_s / s", "8")
        self.freq_tg = self._add_entry(left, 4, "一次调频时间常数 T_G / s", "5")
        self.freq_kd = self._add_entry(left, 5, "负荷频率系数 k_D / pu/pu", "1.2")
        self.freq_kg = self._add_entry(left, 6, "一次调频系数 k_G / pu/pu", "4.0")
        self.freq_tend = self._add_entry(left, 7, "绘图时长 / s", "30")
        self.enable_agc = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="启用二次调频（AGC，默认关闭）", variable=self.enable_agc, command=self._on_agc_toggle).grid(
            row=8, column=0, columnspan=2, sticky="w", padx=4, pady=2
        )
        self.freq_beta = self._add_entry(left, 9, "ACE频偏系数 B / (MW/Hz, 标幺化)", "15")
        self.freq_kp_agc = self._add_entry(left, 10, "AGC比例 Kp", "0.12")
        self.freq_ki_agc = self._add_entry(left, 11, "AGC积分 Ki / s⁻¹", "0.010")
        self.freq_tace = self._add_entry(left, 12, "ACE滤波时间常数 Tace / s", "8")
        self.freq_tcmd = self._add_entry(left, 13, "主站到机组执行滞后 Tcmd / s", "20")
        self.freq_p2max = self._add_entry(left, 14, "二次调频最大调节量 |P2|max / pu", "0.08")
        self.freq_deadband = self._add_entry(left, 15, "频率死区 |Δf| / Hz", "0.01")

        self.show_first_order = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="同时绘制无一次调频一阶对照", variable=self.show_first_order).grid(
            row=16, column=0, columnspan=2, sticky="w", padx=4, pady=4
        )

        ttk.Button(left, text="计算并绘图", command=self.calculate_frequency).grid(
            row=17, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4)
        )

        ttk.Label(left, text="结果", font=("TkDefaultFont", 10, "bold")).grid(
            row=18, column=0, columnspan=2, sticky="w", pady=(10, 4)
        )

        self.freq_result = ScrolledText(left, width=52, height=24, wrap=tk.WORD)
        self.freq_result.grid(row=19, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        self.freq_result.configure(state="disabled")

        ttk.Label(right, text="频率曲线", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        self.freq_fig = Figure(figsize=(7.4, 5.2), dpi=100)
        self.freq_ax = self.freq_fig.add_subplot(111)
        self.freq_ax.set_xlabel("t / s")
        self.freq_ax.set_ylabel("f / Hz")
        self.freq_ax.grid(True)

        self.freq_canvas = FigureCanvasTkAgg(self.freq_fig, master=right)
        self.freq_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        self.freq_toolbar = NavigationToolbar2Tk(self.freq_canvas, right, pack_toolbar=False)
        self.freq_toolbar.update()
        self.freq_toolbar.grid(row=2, column=0, sticky="ew")

        self._on_agc_toggle()
        self.calculate_frequency()

    def _on_agc_toggle(self) -> None:
        agc_on = bool(self.enable_agc.get())
        state = "normal" if agc_on else "disabled"
        for ent in (self.freq_beta, self.freq_kp_agc, self.freq_ki_agc, self.freq_tace, self.freq_tcmd, self.freq_p2max, self.freq_deadband):
            ent.configure(state=state)
        if agc_on:
            try:
                t_val = float(self.freq_tend.get().strip() or "0")
            except Exception:
                t_val = 0.0
            if t_val < 120.0:
                self.freq_tend.delete(0, tk.END)
                self.freq_tend.insert(0, "300")

    def _build_oscillation_tab(self) -> None:
        frame = ttk.Frame(self.osc_tab, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="机电振荡频率快估", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        self.osc_eq = self._add_entry(frame, 1, "内电势 E'_q / pu", "1.12")
        self.osc_u = self._add_entry(frame, 2, "端电压 U / pu", "1.0")
        self.osc_x = self._add_entry(frame, 3, "等值电抗 X_Σ / pu", "0.55")
        self.osc_p0 = self._add_entry(frame, 4, "初始有功 P0 / pu", "0.8")
        self.osc_tj = self._add_entry(frame, 5, "惯性时间常数 T_j / s", "9")
        self.osc_f0 = self._add_entry(frame, 6, "同步频率 f0 / Hz", "50")

        ttk.Button(frame, text="计算", command=self.calculate_oscillation).grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4)
        )

        self.osc_result = ScrolledText(frame, width=85, height=24, wrap=tk.WORD)
        self.osc_result.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=4, pady=8)
        self.osc_result.configure(state="disabled")

        self.calculate_oscillation()

    def _build_voltage_tab(self) -> None:
        self.volt_tab.columnconfigure(0, weight=1)
        self.volt_tab.rowconfigure(0, weight=1)
        nb = ttk.Notebook(self.volt_tab)
        nb.grid(row=0, column=0, sticky="nsew")
        self._vr_notebook = nb
        self._vr_notebook.bind("<<NotebookTabChanged>>", self._on_ai_context_changed)

        self._vr_static_tab = ttk.Frame(nb)
        self._vr_line_tab = ttk.Frame(nb)
        self._vr_avc_tab = ttk.Frame(nb)
        nb.add(self._vr_static_tab, text="静态电压稳定")
        nb.add(self._vr_line_tab, text="线路自然功率与无功")
        nb.add(self._vr_avc_tab, text="AVC策略模拟")

        # 子页1：静态电压稳定
        frame = ttk.Frame(self._vr_static_tab, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="静态电压稳定极限快估", font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.volt_ug = self._add_entry(frame, 1, "送端电压 U_g / pu", "1.0")
        self.volt_x = self._add_entry(frame, 2, "总电抗 X_Σ / pu", "0.32")
        self.volt_pf = self._add_entry(frame, 3, "功率因数 cosφ（默认滞后）", "0.95")
        self.volt_sbase = self._add_entry(frame, 4, "容量基准 S_base / MVA（可改）", "100")
        ttk.Button(frame, text="计算", command=self.calculate_voltage).grid(row=5, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4))
        self.volt_result = ScrolledText(frame, width=85, height=20, wrap=tk.WORD)
        self.volt_result.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=4, pady=8)
        self.volt_result.configure(state="disabled")

        # 子页2：线路自然功率与无功
        frame2 = ttk.Frame(self._vr_line_tab, padding=12)
        frame2.pack(fill="both", expand=True)
        frame2.columnconfigure(0, weight=0)
        frame2.columnconfigure(1, weight=1)
        ttk.Label(frame2, text="长线路自然功率与无功行为快估", font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.line_u = self._add_entry(frame2, 1, "线路额定电压 U / kV（线电压）", "500")
        self.line_zc = self._add_entry(frame2, 2, "波阻抗 Z_c / Ω（优先）", "250")
        self.line_l = self._add_entry(frame2, 3, "单位长度电感 L（可留空）", "")
        self.line_c = self._add_entry(frame2, 4, "单位长度电容 C（可留空）", "")
        self.line_p = self._add_entry(frame2, 5, "实际传输有功 P / MW", "700")
        self.line_qn = self._add_entry(frame2, 6, "单位长度充电功率 Q_N / (Mvar/km)", "1.2")
        self.line_len = self._add_entry(frame2, 7, "线路长度 l / km", "200")
        ttk.Button(frame2, text="计算", command=self.calculate_line).grid(row=8, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4))
        self.line_result = ScrolledText(frame2, width=85, height=20, wrap=tk.WORD)
        self.line_result.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=4, pady=8)
        self.line_result.configure(state="disabled")

        # 子页3：AVC策略模拟
        frame3 = ttk.Frame(self._vr_avc_tab, padding=12)
        frame3.pack(fill="both", expand=True)
        frame3.columnconfigure(0, weight=0)
        frame3.columnconfigure(1, weight=1)
        ttk.Label(frame3, text="AVC策略模拟（降压变压器+无功补偿）", font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.avc_hv_kv = self._add_entry(frame3, 1, "高压侧额定电压 / kV", "220")
        self.avc_lv_kv = self._add_entry(frame3, 2, "低压侧额定电压 / kV", "110")
        self.avc_vh = self._add_entry(frame3, 3, "高压侧当前电压 / kV", "226")
        self.avc_lv_min = self._add_entry(frame3, 4, "低压侧电压下限 / kV", "108")
        self.avc_lv_max = self._add_entry(frame3, 5, "低压侧电压上限 / kV", "116")
        self.avc_tap_min = self._add_entry(frame3, 6, "变压器最小档位", "-8")
        self.avc_tap_max = self._add_entry(frame3, 7, "变压器最大档位", "8")
        self.avc_tap_now = self._add_entry(frame3, 8, "变压器当前档位", "0")
        self.avc_tap_step = self._add_entry(frame3, 9, "单档电压调节率 / %", "1.25")
        self.avc_cap_num = self._add_entry(frame3, 10, "低压侧电容器组数量", "2")
        self.avc_cap_each = self._add_entry(frame3, 11, "每组电容器容量 / Mvar", "10")
        self.avc_rea_num = self._add_entry(frame3, 12, "低压侧电抗器组数量", "1")
        self.avc_rea_each = self._add_entry(frame3, 13, "每组电抗器容量 / Mvar", "10")
        self.avc_p = self._add_entry(frame3, 14, "高压侧有功潮流 P / MW", "160")
        self.avc_q = self._add_entry(frame3, 15, "高压侧无功潮流 Q / Mvar（感性为正）", "45")
        ttk.Button(frame3, text="执行9区策略模拟", command=self.calculate_avc_strategy).grid(row=16, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4))
        self.avc_result = ScrolledText(frame3, width=85, height=16, wrap=tk.WORD)
        self.avc_result.grid(row=17, column=0, columnspan=2, sticky="nsew", padx=4, pady=8)
        self.avc_result.configure(state="disabled")

        self.calculate_voltage()
        self.calculate_line()
        self.calculate_avc_strategy()

    def _build_impact_tab(self) -> None:
        # ── 顶层布局：左侧两个输入框（上下排列）+ 右侧 P-δ 图 ──────────────
        self.impact_tab.columnconfigure(0, weight=0)
        self.impact_tab.columnconfigure(1, weight=1)
        self.impact_tab.rowconfigure(0, weight=1)

        left  = ttk.Frame(self.impact_tab, padding=6)
        right = ttk.Frame(self.impact_tab, padding=6)
        left.grid(row=0, column=0, sticky="nsw")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        # ══════════════════════════════════════════════════════════════════
        # 上框：冲击法快估
        # ══════════════════════════════════════════════════════════════════
        imp_frame = ttk.LabelFrame(left, text="冲击法快估", padding=8)
        imp_frame.pack(fill="x", expand=False, pady=(0, 6))
        imp_frame.columnconfigure(0, weight=0)
        imp_frame.columnconfigure(1, weight=1)

        self.imp_dp   = self._add_entry(imp_frame, 0, "故障加速功率 ΔPa / pu", "0.9")
        self.imp_dt   = self._add_entry(imp_frame, 1, "故障切除时间 Δt / s", "0.12")
        self.imp_fd   = self._add_entry(imp_frame, 2, "故障后振荡频率 f_d / Hz", "1.106")
        self.imp_pcur = self._add_entry(imp_frame, 3, "当前传输功率 Pm / pu（用于振幅对比 & 临界切除）", "0.90")
        self.imp_tj   = self._add_entry(imp_frame, 4, "惯性时间常数 T_j / s（临界切除用）", "9")
        self.imp_f0   = self._add_entry(imp_frame, 5, "额定频率 f0 / Hz（临界切除用）", "50")

        ttk.Button(imp_frame, text="计算", command=self.calculate_impact).grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 2)
        )

        self.imp_result = ScrolledText(imp_frame, width=50, height=12, wrap=tk.WORD)
        self.imp_result.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=2, pady=4)
        self.imp_result.configure(state="disabled")

        # ══════════════════════════════════════════════════════════════════
        # 下框：等面积法
        # ══════════════════════════════════════════════════════════════════
        eac_frame = ttk.LabelFrame(left, text="等面积法（单机无穷大）", padding=8)
        eac_frame.pack(fill="both", expand=True, pady=(0, 0))
        eac_frame.columnconfigure(0, weight=0)
        eac_frame.columnconfigure(1, weight=1)

        self.eac_pm    = self._add_entry(eac_frame, 0, "机械功率 Pm / pu", "0.90")
        self.eac_ppre  = self._add_entry(eac_frame, 1, "故障前 Pmax_pre / pu", "1.65")
        self.eac_pf    = self._add_entry(eac_frame, 2, "故障中 Pmax_fault / pu（三相故障填 0）", "0.0")
        self.eac_ppost = self._add_entry(eac_frame, 3, "故障后 Pmax_post / pu", "1.65")
        self.eac_dt    = self._add_entry(eac_frame, 4, "故障切除时间 Δt / s", "0.12")
        self.eac_tj    = self._add_entry(eac_frame, 5, "惯性时间常数 Tj / s", "9")
        self.eac_f0    = self._add_entry(eac_frame, 6, "额定频率 f0 / Hz", "50")

        ttk.Button(eac_frame, text="计算并绘图", command=self.calculate_eac).grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 2)
        )

        self.eac_result = ScrolledText(eac_frame, width=50, height=14, wrap=tk.WORD)
        self.eac_result.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=2, pady=4)
        eac_frame.rowconfigure(8, weight=1)
        self.eac_result.configure(state="disabled")
        eac_frame.pack_configure(before=imp_frame)

        # ══════════════════════════════════════════════════════════════════
        # 右侧：P-δ 功角曲线图
        # ══════════════════════════════════════════════════════════════════
        ttk.Label(right, text="功角曲线（等面积法）", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )

        self.eac_fig = Figure(figsize=(7.2, 5.4), dpi=100)
        self.eac_ax  = self.eac_fig.add_subplot(111)
        self.eac_ax.set_xlabel("δ / °")
        self.eac_ax.set_ylabel("P / pu")
        self.eac_ax.set_title("功角曲线（等待计算）")
        self.eac_ax.grid(True)

        self.eac_canvas = FigureCanvasTkAgg(self.eac_fig, master=right)
        self.eac_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        self.eac_toolbar = NavigationToolbar2Tk(self.eac_canvas, right, pack_toolbar=False)
        self.eac_toolbar.update()
        self.eac_toolbar.grid(row=2, column=0, sticky="ew")

        # 初始化
        self.calculate_impact()
        self.calculate_eac()

    def _build_smib_tab(self) -> None:
        self.smib_tab.columnconfigure(1, weight=1)
        self.smib_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.smib_tab, padding=10, style="Card.TFrame")
        right = ttk.Frame(self.smib_tab, padding=10, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 6), pady=2)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=2)

        left.columnconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=2)
        right.rowconfigure(3, weight=3)

        ttk.Label(left, text="单机无穷大系统小扰动分析", style="Card.TLabel",
                  font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        intro = (
            "采用 Kundur 经典 SMIB 示例的六阶同步机模型；可切换“机组”“机组+AVR”“机组+AVR+PSS”三种配置。"
            " 新增“1型AVR/PSS模型”参数页（按教材框图）用于控制环节频域校核。"
            " 程序先由给定运行点构造平衡点，再对非线性模型数值线性化并求取特征值。"
        )
        ttk.Label(left, text=intro, style="Card.TLabel", justify="left",
                  wraplength=430).grid(row=1, column=0, sticky="w", pady=(0, 8))

        topbar = ttk.Frame(left, style="Card.TFrame")
        topbar.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        topbar.columnconfigure(1, weight=1)

        ttk.Label(topbar, text="模型配置", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.smib_config = ttk.Combobox(topbar, state="readonly", width=22, values=_SMIB_CONFIG_OPTIONS)
        self.smib_config.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.smib_config.bind("<<ComboboxSelected>>", self._on_smib_config_change)
        ttk.Button(topbar, text="恢复 Kundur 默认值", command=self._apply_smib_defaults).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(topbar, text="计算并绘图", command=self.calculate_smib).grid(row=0, column=3)

        nb = ttk.Notebook(left)
        nb.grid(row=3, column=0, sticky="nsew")
        left.rowconfigure(3, weight=1)

        page_case = ttk.Frame(nb, padding=8)
        page_machine = ttk.Frame(nb, padding=8)
        page_avr = ttk.Frame(nb, padding=8)
        page_pss = ttk.Frame(nb, padding=8)
        page_type1 = ttk.Frame(nb, padding=8)
        nb.add(page_case, text="工况与网络")
        nb.add(page_machine, text="六阶机组")
        nb.add(page_avr, text="AVR III")
        nb.add(page_pss, text="PSS II")
        nb.add(page_type1, text="1型 AVR/PSS")

        for page in (page_case, page_machine, page_avr, page_pss, page_type1):
            page.columnconfigure(1, weight=1)
            page.columnconfigure(3, weight=1)

        self.smib_entries: dict[str, ttk.Entry] = {}
        self.smib_avr_widgets: list[tk.Widget] = []
        self.smib_pss_widgets: list[tk.Widget] = []

        def add(page: ttk.Frame, key: str, row: int, label: str, default: str, column: int = 0, width: int = 12) -> ttk.Entry:
            entry = self._add_entry(page, row, label, default, column=column, width=width)
            self.smib_entries[key] = entry
            return entry

        add(page_case, "P0", 0, "有功 P0 / pu", "0.90", column=0)
        add(page_case, "Q0", 0, "无功 Q0 / pu", "0.436002238697", column=2)
        add(page_case, "Vt", 1, "端电压 |Vt| / pu", "1.00", column=0)
        add(page_case, "theta_deg", 1, "端电压角 θt / °", "28.342914463", column=2)
        add(page_case, "xT", 2, "变压器电抗 xT / pu", "0.15", column=0)
        add(page_case, "xL1", 2, "线路 1 电抗 xL1 / pu", "0.50", column=2)
        add(page_case, "xL2", 3, "线路 2 电抗 xL2 / pu", "0.93", column=0)
        add(page_case, "f0", 3, "系统频率 f0 / Hz", "60", column=2)
        ttk.Label(page_case, text="说明：程序自动将无穷大母线相角平移为 0°；若 xL2≤0，则视为第二回线路停运。",
                  wraplength=390).grid(row=4, column=0, columnspan=4, sticky="w", padx=4, pady=(6, 0))

        add(page_machine, "ra", 0, "电枢电阻 ra / pu", "0.003", column=0)
        add(page_machine, "xd", 0, "同步电抗 xd / pu", "1.81", column=2)
        add(page_machine, "xq", 1, "同步电抗 xq / pu", "1.76", column=0)
        add(page_machine, "x1d", 1, "暂态电抗 x'd / pu", "0.30", column=2)
        add(page_machine, "x1q", 2, "暂态电抗 x'q / pu", "0.65", column=0)
        add(page_machine, "x2d", 2, "次暂态电抗 x''d / pu", "0.23", column=2)
        add(page_machine, "x2q", 3, "次暂态电抗 x''q / pu", "0.25", column=0)
        add(page_machine, "T1d0", 3, "开路 T'd0 / s", "8.0", column=2)
        add(page_machine, "T1q0", 4, "开路 T'q0 / s", "1.0", column=0)
        add(page_machine, "T2d0", 4, "开路 T''d0 / s", "0.03", column=2)
        add(page_machine, "T2q0", 5, "开路 T''q0 / s", "0.07", column=0)
        add(page_machine, "M", 5, "机械起动时间 M=2H / s", "7.0", column=2)
        add(page_machine, "D", 6, "阻尼 D / pu", "0.0", column=0)

        self.smib_avr_widgets.extend([
            add(page_avr, "avr_K0", 0, "放大倍数 K0", "200", column=0),
            add(page_avr, "avr_T1", 0, "零点 T1 / s", "1.0", column=2),
            add(page_avr, "avr_T2", 1, "极点 T2 / s", "1.0", column=0),
            add(page_avr, "avr_Te", 1, "励磁回路 Te / s", "0.0001", column=2),
            add(page_avr, "avr_Tr", 2, "测量时间 Tr / s", "0.015", column=0),
            add(page_avr, "avr_vfmax", 2, "上限 vfmax / pu", "7.0", column=2),
            add(page_avr, "avr_vfmin", 3, "下限 vfmin / pu", "-6.4", column=0),
        ])

        self.smib_pss_widgets.extend([
            add(page_pss, "pss_Kw", 0, "洗出增益 Kw", "9.5", column=0),
            add(page_pss, "pss_Tw", 0, "洗出时间 Tw / s", "1.41", column=2),
            add(page_pss, "pss_T1", 1, "一阶超前 T1 / s", "0.154", column=0),
            add(page_pss, "pss_T2", 1, "一阶滞后 T2 / s", "0.033", column=2),
            add(page_pss, "pss_T3", 2, "二阶超前 T3 / s", "1.0", column=0),
            add(page_pss, "pss_T4", 2, "二阶滞后 T4 / s", "1.0", column=2),
            add(page_pss, "pss_vsmax", 3, "上限 vsmax / pu", "0.2", column=0),
            add(page_pss, "pss_vsmin", 3, "下限 vsmin / pu", "-0.2", column=2),
        ])

        page_avr.rowconfigure(5, weight=1)
        self.smib_avr_fig = Figure(figsize=(6.4, 2.2), dpi=100)
        self.smib_avr_ax = self.smib_avr_fig.add_subplot(111)
        _draw_avr_transfer_diagram(self.smib_avr_ax)
        self.smib_avr_canvas = FigureCanvasTkAgg(self.smib_avr_fig, master=page_avr)
        self.smib_avr_canvas.get_tk_widget().grid(row=5, column=0, columnspan=4, sticky="nsew", padx=4, pady=(8, 0))
        self.smib_avr_canvas.draw()

        page_pss.rowconfigure(5, weight=1)
        self.smib_pss_fig = Figure(figsize=(6.4, 2.1), dpi=100)
        self.smib_pss_ax = self.smib_pss_fig.add_subplot(111)
        _draw_pss_transfer_diagram(self.smib_pss_ax)
        self.smib_pss_canvas = FigureCanvasTkAgg(self.smib_pss_fig, master=page_pss)
        self.smib_pss_canvas.get_tk_widget().grid(row=5, column=0, columnspan=4, sticky="nsew", padx=4, pady=(8, 0))
        self.smib_pss_canvas.draw()

        self.smib_type1_entries: dict[str, ttk.Entry] = {}
        def add_type1(key: str, row: int, label: str, default: str, column: int = 0) -> None:
            self.smib_type1_entries[key] = self._add_entry(page_type1, row, label, default, column=column, width=11)

        add_type1("Kr", 0, "Kr", "1.0", 0); add_type1("Tr", 0, "Tr / s", "0.02", 2)
        add_type1("Ka", 1, "Ka", "200", 0); add_type1("Ta", 1, "Ta / s", "0.05", 2)
        add_type1("Kf", 2, "Kf", "0.05", 0); add_type1("Tf", 2, "Tf / s", "1.0", 2)
        add_type1("Te", 3, "Te / s", "0.5", 0); add_type1("Efd_max", 3, "Efd_max / pu", "6.0", 2)
        add_type1("Efd_min", 4, "Efd_min / pu", "-6.0", 0)
        add_type1("Kq1", 5, "Kq1", "10", 0); add_type1("Kq2", 5, "Kq2", "2", 2)
        add_type1("Kq3", 6, "Kq3", "1", 0); add_type1("Kpss", 6, "K", "10", 2)
        add_type1("Tq", 7, "Tq / s", "0.1", 0); add_type1("T1e", 7, "T1e / s", "0.15", 2)
        add_type1("T2e", 8, "T2e / s", "0.03", 0); add_type1("T3e", 8, "T3e / s", "0.15", 2)
        add_type1("T4e", 9, "T4e / s", "0.03", 0); add_type1("Vsmax", 9, "Vsmax / pu", "0.2", 2)
        add_type1("Vsmin", 10, "Vsmin / pu", "-0.2", 0); add_type1("f_eval", 10, "评估频率 / Hz", "1.0", 2)
        ttk.Button(page_type1, text="计算1型 AVR/PSS 指标", command=self.calculate_type1_avr_pss).grid(
            row=11, column=0, columnspan=4, sticky="ew", padx=4, pady=(8, 4)
        )
        self.smib_type1_result = ScrolledText(page_type1, width=56, height=8, wrap=tk.WORD)
        self.smib_type1_result.grid(row=12, column=0, columnspan=4, sticky="nsew", padx=4, pady=(2, 2))
        self.smib_type1_result.configure(state="disabled")

        ttk.Label(right, text="模态结果", style="Card.TLabel",
                  font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.smib_result = ScrolledText(right, width=78, height=18, wrap=tk.WORD, font="TkFixedFont")
        self.smib_result.grid(row=1, column=0, sticky="nsew")
        self.smib_result.configure(state="disabled")

        ttk.Label(right, text="特征值复平面", style="Card.TLabel",
                  font=("TkDefaultFont", 11, "bold")).grid(row=2, column=0, sticky="w", pady=(10, 4))
        self.smib_fig = Figure(figsize=(7.6, 4.8), dpi=100)
        self.smib_ax = self.smib_fig.add_subplot(111)
        self.smib_ax.set_xlabel("Re(λ) / 1/s")
        self.smib_ax.set_ylabel("Im(λ) / rad/s")
        self.smib_ax.grid(True, alpha=0.35)

        self.smib_canvas = FigureCanvasTkAgg(self.smib_fig, master=right)
        self.smib_canvas.get_tk_widget().grid(row=3, column=0, sticky="nsew")
        self.smib_toolbar = NavigationToolbar2Tk(self.smib_canvas, right, pack_toolbar=False)
        self.smib_toolbar.update()
        self.smib_toolbar.grid(row=4, column=0, sticky="ew")

        self._apply_smib_defaults()

    def calculate_type1_avr_pss(self) -> None:
        try:
            p = {k: _safe_float(v.get(), k) for k, v in self.smib_type1_entries.items()}
            for key in ("Tr", "Ta", "Tf", "Te", "Tq", "T1e", "T2e", "T3e", "T4e"):
                _validate_positive(key, p[key])
            _validate_positive("评估频率", p["f_eval"])
            if p["Efd_min"] >= p["Efd_max"]:
                raise InputError("Efd_min 必须小于 Efd_max。")
            if p["Vsmin"] >= p["Vsmax"]:
                raise InputError("Vsmin 必须小于 Vsmax。")

            w = 2.0 * math.pi * p["f_eval"]
            s = complex(0.0, w)
            avr_meas = p["Kr"] / (1.0 + s * p["Tr"])
            avr_amp = p["Ka"] / (1.0 + s * p["Ta"])
            avr_exc = 1.0 / (1.0 + s * p["Te"])
            avr_fb = s * p["Kf"] / (1.0 + s * p["Tf"])
            avr_open = avr_meas * avr_amp * avr_exc
            avr_closed = avr_open / (1.0 + avr_open * avr_fb)

            pss_in = p["Kq1"] + p["Kq2"] + p["Kq3"]
            pss_core = (p["Kpss"] + s) / (1.0 + s * p["Tq"])
            lead1 = (1.0 + s * p["T1e"]) / (1.0 + s * p["T2e"])
            lead2 = (1.0 + s * p["T3e"]) / (1.0 + s * p["T4e"])
            pss_tf = pss_in * pss_core * lead1 * lead2
            vs_est = max(p["Vsmin"], min(p["Vsmax"], pss_tf.real))

            def _fmt(z: complex) -> str:
                return f"{abs(z):.4f}∠{math.degrees(math.atan2(z.imag, z.real)):+.2f}°"

            text = (
                "══ 1型 AVR/PSS 模型校核 ═════════════════\n"
                f"评估频率：{p['f_eval']:.4f} Hz\n\n"
                "【AVR】\n"
                f"Gm(s)=Kr/(1+sTr) = {_fmt(avr_meas)}\n"
                f"Ga(s)=Ka/(1+sTa) = {_fmt(avr_amp)}\n"
                f"Ge(s)=1/(1+sTe) = {_fmt(avr_exc)}\n"
                f"Gf(s)=sKf/(1+sTf) = {_fmt(avr_fb)}\n"
                f"开环 Gavr = {_fmt(avr_open)}\n"
                f"闭环 Gavr_cl = {_fmt(avr_closed)}\n"
                f"Efd 限幅区间 = [{p['Efd_min']:.3f}, {p['Efd_max']:.3f}] pu\n\n"
                "【PSS】\n"
                f"输入加权 Kq1+Kq2+Kq3 = {pss_in:.4f}\n"
                f"Gpss(s) = {_fmt(pss_tf)}\n"
                f"Vs 估算（实部限幅）= {vs_est:.4f} pu，限值[{p['Vsmin']:.3f}, {p['Vsmax']:.3f}]\n\n"
                "说明：该页按截图中的1型 AVR/PSS 传函进行环节校核，用于小扰动控制参数整定参考。"
            )
            self._set_text(self.smib_type1_result, text)
        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def _apply_smib_defaults(self) -> None:
        defaults = kundur_smib_defaults()
        self.smib_config.set(str(defaults["config"]))
        for key, value in defaults.items():
            if key == "config":
                continue
            entry = self.smib_entries[key]
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
        self._on_smib_config_change()
        self.calculate_smib()

    def _on_smib_config_change(self, _event: object | None = None) -> None:
        config_key = _SMIB_CONFIG_KEY.get(self.smib_config.get().strip(), "avr_pss")
        self._set_enabled(self.smib_avr_widgets, config_key in {"avr", "avr_pss"})
        self._set_enabled(self.smib_pss_widgets, config_key == "avr_pss")

    def _read_smib_inputs(self) -> tuple[str, dict[str, float]]:
        label = self.smib_config.get().strip() or "六阶机组 + AVR + PSS"
        config_key = _SMIB_CONFIG_KEY.get(label)
        if config_key is None:
            raise InputError("请选择有效的小扰动模型配置。")

        params: dict[str, float] = {}
        for key, entry in self.smib_entries.items():
            text = entry.get().strip()
            if key == "xL2" and text == "":
                params[key] = 0.0
                continue
            params[key] = _safe_float(text, key)

        if params["xL2"] <= 0:
            params["xL2"] = 0.0
        return config_key, params

    def calculate_smib(self) -> None:
        try:
            config_key, params = self._read_smib_inputs()
            result = smib_small_signal_analysis(config_key, params)
            op = result.operating_point
            eigs = result.eigenvalues
            rows = _smib_modal_rows(eigs)
            max_real = float(np.max(np.real(eigs))) if eigs.size else float("nan")

            status = "稳定" if result.stable else "不稳定"
            text = (
                f"配置：{result.config_label}\n"
                f"状态维数：{len(result.state_names)}\n"
                f"稳定性：{status}（max Re(λ) = {max_real:+.6f} 1/s）\n"
                f"\n── 平衡点（以无穷大母线为角度参考）────────────────\n"
                f"V∞ = {op.infinite_bus_voltage_pu:.6f} pu\n"
                f"Vt = {op.terminal_voltage_pu:.6f} ∠ {op.terminal_angle_deg:.6f}° pu\n"
                f"P + jQ = {op.P_pu:.6f} + j{op.Q_pu:.6f} pu\n"
                f"δ0 = {op.delta_deg:.6f}°\n"
                f"pm0 = {op.pm_pu:.6f} pu，vf0 = {op.vf0_pu:.6f} pu\n"
                f"id0 = {op.id_pu:.6f} pu，iq0 = {op.iq_pu:.6f} pu\n"
                f"vd0 = {op.vd_pu:.6f} pu，vq0 = {op.vq_pu:.6f} pu\n"
                f"Xline,eq = {op.xline_eq_pu:.6f} pu，Xnet = {op.xnet_pu:.6f} pu\n"
                f"参考角平移 = {op.reference_shift_deg:+.6f}°\n"
            )

            if result.dominant_mode_index is not None:
                lam = eigs[result.dominant_mode_index]
                freq = abs(lam.imag) / (2.0 * math.pi)
                zeta = None if abs(lam.imag) < 1e-8 else -lam.real / abs(lam)
                text += "\n── 最弱阻尼模态 ───────────────────────────────────\n"
                text += f"λ_dom = {_format_eigenvalue(lam)} 1/s\n"
                if zeta is None:
                    text += "该模态为实根，非振荡模态。\n"
                else:
                    text += f"f_dom = {freq:.6f} Hz，ζ = {zeta * 100:.3f} %\n"
                if result.dominant_participation:
                    parts = []
                    for name, weight in result.dominant_participation[:4]:
                        parts.append(f"{_SMIB_STATE_LABELS.get(name, name)} {weight * 100:.1f}%")
                    text += "主导参与状态：" + "， ".join(parts) + "\n"

            text += "\n── 模态表（仅列 Im(λ) ≥ 0 的独立模态）──────────────\n"
            text += "序号  特征值 λ / (1/s)                 f / Hz     ζ / %     类型\n"
            text += "-" * 70 + "\n"
            for row in rows:
                lam = row["lambda"]
                zeta = row["zeta"]
                ztxt = "   -   " if zeta is None else f"{zeta * 100:8.3f}"
                text += (
                    f"{row['idx']:>2d}    {_format_eigenvalue(lam):<28}  "
                    f"{row['freq']:>8.4f}  {ztxt}   {row['type']}\n"
                )

            text += "\n说明：\n" + result.notes
            self._set_text(self.smib_result, text)

            ax = self.smib_ax
            ax.clear()
            ax.axvline(0.0, linestyle=":", linewidth=1.2)
            ax.axhline(0.0, linestyle="--", linewidth=0.8)
            ax.plot(np.real(eigs), np.imag(eigs), "o", markersize=5)
            for i, lam in enumerate(eigs):
                if abs(lam.imag) > 1e-8 and lam.imag > 0:
                    lbl = f"{abs(lam.imag) / (2.0 * math.pi):.2f} Hz"
                    if i == result.dominant_mode_index or lam.real > -1.5:
                        ax.annotate(lbl, (lam.real, lam.imag), textcoords="offset points", xytext=(4, 4), fontsize=8)
            real_vals = np.real(eigs)
            imag_vals = np.imag(eigs)
            xr = max(1.0, float(np.max(real_vals) - np.min(real_vals)))
            yr = max(1.0, float(np.max(imag_vals) - np.min(imag_vals)))
            ax.set_xlim(float(np.min(real_vals) - 0.12 * xr), float(np.max(real_vals) + 0.12 * xr))
            ax.set_ylim(float(np.min(imag_vals) - 0.12 * yr), float(np.max(imag_vals) + 0.12 * yr))
            ax.set_xlabel("Re(λ) / 1/s")
            ax.set_ylabel("Im(λ) / rad/s")
            ax.set_title(f"SMIB 小扰动特征值分布：{result.config_label}（{status}）")
            ax.grid(True, alpha=0.35)
            self.smib_fig.tight_layout()
            self.smib_canvas.draw()


        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_frequency(self) -> None:
        try:
            f0 = _safe_float(self.freq_f0.get(), "额定频率 f0")
            delta_p = _safe_float(self.freq_dp.get(), "功率缺额 ΔP_OL0")
            Ts = _safe_float(self.freq_ts.get(), "T_s")
            TG = _safe_float(self.freq_tg.get(), "T_G")
            kD = _safe_float(self.freq_kd.get(), "k_D")
            kG = _safe_float(self.freq_kg.get(), "k_G")
            t_end = _safe_float(self.freq_tend.get(), "绘图时长")
            _validate_positive("绘图时长", t_end)
            agc_on = bool(self.enable_agc.get())

            summary = frequency_response_summary(delta_p, Ts, TG, kD, kG, f0)

            t = np.linspace(0.0, t_end, max(1400, int(8 * t_end)))
            y2 = frequency_response_value(t, delta_p, Ts, TG, kD, kG)
            ace_f = None
            p2_act = None
            if agc_on:
                beta_mw_hz = _safe_float(self.freq_beta.get(), "B")
                kp_agc = _safe_float(self.freq_kp_agc.get(), "Kp")
                ki_agc = _safe_float(self.freq_ki_agc.get(), "Ki")
                t_ace = _safe_float(self.freq_tace.get(), "Tace")
                t_cmd = _safe_float(self.freq_tcmd.get(), "Tcmd")
                p2max = _safe_float(self.freq_p2max.get(), "P2max")
                deadband_hz = _safe_float(self.freq_deadband.get(), "频率死区")
                _validate_positive("B", beta_mw_hz)
                _validate_nonnegative("Kp", kp_agc)
                _validate_nonnegative("Ki", ki_agc)
                _validate_positive("Tace", t_ace)
                _validate_positive("Tcmd", t_cmd)
                _validate_nonnegative("P2max", p2max)
                _validate_nonnegative("频率死区", deadband_hz)

                dt = float(t[1] - t[0])
                df = 0.0
                pg1 = 0.0
                ace_state = 0.0
                ace_int = 0.0
                p2 = 0.0
                y2_num = np.zeros_like(t)
                ace_f = np.zeros_like(t)
                p2_act = np.zeros_like(t)
                for i, _ti in enumerate(t):
                    df_hz = df * f0
                    df_eff_hz = 0.0 if abs(df_hz) <= deadband_hz else df_hz
                    ace_raw = beta_mw_hz * df_eff_hz
                    dace = (ace_raw - ace_state) / t_ace
                    ace_state += dt * dace
                    ace_int += dt * ace_state
                    p2_cmd = -(kp_agc * ace_state + ki_agc * ace_int)
                    p2_cmd = max(-p2max, min(p2max, p2_cmd))
                    dp2 = (p2_cmd - p2) / t_cmd
                    p2 += dt * dp2

                    dpg1 = (-pg1 - kG * df) / TG
                    pg1 += dt * dpg1
                    ddf = (-delta_p + pg1 + p2 - kD * df) / Ts
                    df += dt * ddf

                    y2_num[i] = df
                    ace_f[i] = ace_state
                    p2_act[i] = p2
                y2 = y2_num

            f2 = f0 * (1.0 + y2)

            self.freq_ax.clear()
            main_label = "含二次调频（AGC）" if agc_on else "含一次调频二阶模型"
            self.freq_ax.plot(t, f2, label=main_label, linewidth=2.0, color=("#005f73" if agc_on else None))
            if self.show_first_order.get():
                y1 = first_order_frequency_response_value(t, delta_p, Ts, kD)
                f1 = f0 * (1.0 + y1)
                self.freq_ax.plot(t, f1, "--", label="无一次调频一阶对照", linewidth=1.7)

            self.freq_ax.axhline(
                y=f0 * (1.0 + summary.steady_pu),
                linestyle=":",
                linewidth=1.2,
                label="二阶模型稳态频率"
            )

            if summary.nadir_time_s is not None and 0.0 <= summary.nadir_time_s <= t_end + 1e-9:
                self.freq_ax.scatter(
                    [summary.nadir_time_s],
                    [summary.f_min_hz],
                    s=40,
                    label=f"最低点 ({summary.nadir_time_s:.3f} s)"
                )

            self.freq_ax.set_xlabel("t / s")
            self.freq_ax.set_ylabel("f / Hz")
            self.freq_ax.set_title(f"频率响应曲线（{summary.regime}）")
            self.freq_ax.grid(True)
            self.freq_ax.legend(loc="best")
            self.freq_fig.tight_layout()
            self.freq_canvas.draw()

            text = (
                f"阻尼类型：{summary.regime}\n"
                f"α = {summary.alpha:.6f} 1/s\n"
                f"Ω = {summary.omega_d:.6f} rad/s\n" if summary.omega_d is not None else
                f"阻尼类型：{summary.regime}\n"
                f"α = {summary.alpha:.6f} 1/s\n"
            )

            text += (
                f"初始频率变化率 RoCoF = {summary.rocof_pu_s:.6f} pu/s = {summary.rocof_hz_s:.6f} Hz/s\n"
                f"稳态频差 Δf∞ = {summary.steady_pu:.6f} pu = {summary.steady_hz:.6f} Hz\n"
            )

            if summary.nadir_time_s is not None:
                text += (
                    f"频率最低点时刻 t_m = {summary.nadir_time_s:.6f} s\n"
                    f"最低频差 Δf_min = {summary.nadir_pu:.6f} pu = {summary.nadir_hz:.6f} Hz\n"
                    f"最低频率 f_min = {summary.f_min_hz:.6f} Hz\n"
                )
            else:
                text += (
                    "该参数组合不产生典型欠阻尼最低点。\n"
                    f"单调极限（稳态）Δf∞ = {summary.steady_pu:.6f} pu，"
                    f"对应频率 {f0 * (1.0 + summary.steady_pu):.6f} Hz\n"
                )

            text += "\n说明：\n" + summary.notes
            if agc_on and ace_f is not None and p2_act is not None:
                text += (
                    "\n\n══ 二次调频（AGC-FFC）附加结果 ═════════════\n"
                    f"仿真末端频差 = {y2[-1]:+.6f} pu ({y2[-1] * f0:+.4f} Hz)\n"
                    f"末端滤波ACE = {ace_f[-1]:+.6f}\n"
                    f"末端二次调频出力 P2 = {p2_act[-1]:+.6f} pu\n"
                    "ACE按定频率控制（FFC）仅考虑频偏项，主站指令到机组执行采用一阶滞后。"
                )
            self._set_text(self.freq_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_oscillation(self) -> None:
        try:
            Eq = _safe_float(self.osc_eq.get(), "E'_q")
            U = _safe_float(self.osc_u.get(), "U")
            X = _safe_float(self.osc_x.get(), "X_Σ")
            P0 = _safe_float(self.osc_p0.get(), "P0")
            Tj = _safe_float(self.osc_tj.get(), "T_j")
            f0 = _safe_float(self.osc_f0.get(), "f0")

            summary = electromechanical_frequency(Eq, U, X, P0, Tj, f0)

            text = (
                f"初始功角 δ0 = {summary.delta0_deg:.6f} °\n"
                f"同步转矩系数 K_s = {summary.Ks:.6f} pu/rad（按本文近似定义）\n"
                f"固有角频率 ω_n = {summary.omega_n:.6f} rad/s\n"
                f"机电振荡频率 f_n = {summary.f_n:.6f} Hz\n\n"
                f"说明：\n{summary.notes}"
            )
            self._set_text(self.osc_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_voltage(self) -> None:
        try:
            Ug = _safe_float(self.volt_ug.get(), "U_g")
            X = _safe_float(self.volt_x.get(), "X_Σ")
            cos_phi = _safe_float(self.volt_pf.get(), "cosφ")
            s_base_text = self.volt_sbase.get().strip()
            s_base = _safe_float(s_base_text, "S_base") if s_base_text else None

            summary = static_voltage_stability(Ug, X, cos_phi, s_base)

            text = (
                f"sinφ = {summary.sin_phi:.6f}\n"
                f"最大可送有功 P_L,max = {summary.Pmax_pu:.6f} pu\n"
            )
            if summary.Pmax_MW is not None:
                text += f"折算有名值 = {summary.Pmax_MW:.6f} MW\n"
            text += (
                f"受端最低电压（相对送端电压归一化）V_min/U_g = {summary.Vmin_norm_to_sending:.6f} pu\n"
                f"受端最低电压（与 U_g 同一基准）V_min = {summary.Vmin_same_base_as_Ug:.6f} pu\n\n"
                f"说明：\n{summary.notes}"
            )
            self._set_text(self.volt_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_line(self) -> None:
        try:
            U = _safe_float(self.line_u.get(), "U")
            zc_text = self.line_zc.get().strip()
            zc = _safe_float(zc_text, "Z_c") if zc_text else None

            l_text = self.line_l.get().strip()
            c_text = self.line_c.get().strip()
            L = _safe_float(l_text, "L") if l_text else None
            C = _safe_float(c_text, "C") if c_text else None

            P = _safe_float(self.line_p.get(), "P")
            QN = _safe_float(self.line_qn.get(), "Q_N")
            length = _safe_float(self.line_len.get(), "l")

            summary = natural_power_and_reactive(U, zc, L, C, P, QN, length)

            text = (
                f"波阻抗 Z_c = {summary.Zc_ohm:.6f} Ω\n"
                f"自然功率 P_N = {summary.Pn_MW:.6f} MW\n"
                f"线路无功估算 ΔQ_L = {summary.delta_Q_Mvar:.6f} Mvar\n"
                f"运行区间判断：{summary.line_state}\n\n"
                f"说明：\n{summary.notes}"
            )
            self._set_text(self.line_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_avc_strategy(self) -> None:
        """按简化9区策略给出档位+无功补偿调控建议与调后结果。"""
        try:
            hv_base = _safe_float(self.avc_hv_kv.get(), "高压额定电压")
            lv_base = _safe_float(self.avc_lv_kv.get(), "低压额定电压")
            vh = _safe_float(self.avc_vh.get(), "高压侧电压")
            lv_min = _safe_float(self.avc_lv_min.get(), "低压侧下限")
            lv_max = _safe_float(self.avc_lv_max.get(), "低压侧上限")
            tap_min = int(round(_safe_float(self.avc_tap_min.get(), "最小档位")))
            tap_max = int(round(_safe_float(self.avc_tap_max.get(), "最大档位")))
            tap_now = int(round(_safe_float(self.avc_tap_now.get(), "当前档位")))
            tap_step_pct = _safe_float(self.avc_tap_step.get(), "单档调节率")
            cap_num = max(0, int(round(_safe_float(self.avc_cap_num.get(), "电容器组数量"))))
            cap_each = max(0.0, _safe_float(self.avc_cap_each.get(), "每组电容容量"))
            rea_num = max(0, int(round(_safe_float(self.avc_rea_num.get(), "电抗器组数量"))))
            rea_each = max(0.0, _safe_float(self.avc_rea_each.get(), "每组电抗容量"))
            p_mw = _safe_float(self.avc_p.get(), "有功潮流")
            q_mvar = _safe_float(self.avc_q.get(), "无功潮流")

            if tap_min > tap_max:
                raise InputError("最小档位不能大于最大档位。")
            tap_now = min(max(tap_now, tap_min), tap_max)
            _validate_positive("高压侧额定电压", hv_base)
            _validate_positive("低压侧额定电压", lv_base)
            _validate_positive("单档调节率", tap_step_pct)

            # 当前低压估算：基于变比与当前档位（正档升压）
            ratio = lv_base / hv_base
            tap_gain = 1.0 + tap_now * tap_step_pct / 100.0
            lv_est = vh * ratio * tap_gain
            lv_mid = 0.5 * (lv_min + lv_max)

            q_cap_total = cap_num * cap_each
            q_rea_total = rea_num * rea_each
            q_after = q_mvar
            tap_target = tap_now
            action_steps: list[str] = []

            # 9区策略（简化）：电压3区×无功3区
            if lv_est < lv_min:
                v_zone = "低压区"
            elif lv_est > lv_max:
                v_zone = "高压区"
            else:
                v_zone = "正常电压区"

            q_abs_ref = max(10.0, 0.2 * max(abs(p_mw), 1.0))
            if q_mvar > q_abs_ref:
                q_zone = "感性无功偏大"
            elif q_mvar < -q_abs_ref:
                q_zone = "容性无功偏大"
            else:
                q_zone = "无功正常区"

            if v_zone == "低压区":
                if tap_target < tap_max:
                    tap_target += 1
                    action_steps.append("升高变压器档位 +1")
                if q_after > 0 and q_cap_total > 0:
                    dq = min(q_after, q_cap_total)
                    q_after -= dq
                    action_steps.append(f"投入电容器（最多 {q_cap_total:.2f} Mvar，实际补偿 {dq:.2f} Mvar）")
            elif v_zone == "高压区":
                if tap_target > tap_min:
                    tap_target -= 1
                    action_steps.append("降低变压器档位 -1")
                if q_after < 0 and q_rea_total > 0:
                    dq = min(-q_after, q_rea_total)
                    q_after += dq
                    action_steps.append(f"投入电抗器（最多 {q_rea_total:.2f} Mvar，实际吸收 {dq:.2f} Mvar）")
            else:
                if q_zone == "感性无功偏大" and q_cap_total > 0:
                    dq = min(q_after, q_cap_total)
                    q_after -= dq
                    action_steps.append(f"正常电压下优先投电容器，补偿 {dq:.2f} Mvar")
                elif q_zone == "容性无功偏大" and q_rea_total > 0:
                    dq = min(-q_after, q_rea_total)
                    q_after += dq
                    action_steps.append(f"正常电压下优先投电抗器，吸收 {dq:.2f} Mvar")
                else:
                    action_steps.append("保持当前档位与无功补偿状态")

            # 调后电压估算（简单线性灵敏度）
            tap_delta = tap_target - tap_now
            lv_after = vh * ratio * (1.0 + tap_target * tap_step_pct / 100.0)
            q_comp = q_mvar - q_after
            lv_after += 0.015 * q_comp

            zone_map = {
                ("低压区", "感性无功偏大"): "Ⅰ区（低压+感性）",
                ("低压区", "无功正常区"): "Ⅱ区（低压+无功正常）",
                ("低压区", "容性无功偏大"): "Ⅲ区（低压+容性）",
                ("正常电压区", "感性无功偏大"): "Ⅳ区（电压正常+感性）",
                ("正常电压区", "无功正常区"): "Ⅴ区（目标区）",
                ("正常电压区", "容性无功偏大"): "Ⅵ区（电压正常+容性）",
                ("高压区", "感性无功偏大"): "Ⅶ区（高压+感性）",
                ("高压区", "无功正常区"): "Ⅷ区（高压+无功正常）",
                ("高压区", "容性无功偏大"): "Ⅸ区（高压+容性）",
            }
            zone_name = zone_map[(v_zone, q_zone)]
            result_text = (
                f"══ AVC 9区策略模拟结果 ═══════════════════════\n"
                f"当前分区：{zone_name}\n"
                f"电压判据：{v_zone}（估算低压侧 Vlv={lv_est:.3f} kV，限值[{lv_min:.3f}, {lv_max:.3f}]）\n"
                f"无功判据：{q_zone}（Q={q_mvar:.3f} Mvar，阈值±{q_abs_ref:.3f} Mvar）\n\n"
                f"建议策略：\n  - " + "\n  - ".join(action_steps) + "\n\n"
                f"调控后估算：\n"
                f"  档位 {tap_now} → {tap_target}\n"
                f"  无功 {q_mvar:.3f} → {q_after:.3f} Mvar\n"
                f"  低压侧电压 {lv_est:.3f} → {lv_after:.3f} kV\n"
                f"  无功补偿总动作量 = {q_comp:+.3f} Mvar\n"
            )
            self._set_text(self.avc_result, result_text)
        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_impact(self) -> None:
        try:
            delta_p = _safe_float(self.imp_dp.get(), "ΔPa")
            delta_t = _safe_float(self.imp_dt.get(), "Δt")
            f_d     = _safe_float(self.imp_fd.get(), "f_d")
            pcur_text = self.imp_pcur.get().strip()
            pcur = _safe_float(pcur_text, "Pm") if pcur_text else None
            tj_text = self.imp_tj.get().strip()
            f0_text = self.imp_f0.get().strip()

            summary = impact_method(delta_p, delta_t, f_d, pcur)

            text = (
                f"══ 冲击法：功率振荡幅度快估 ═════════════\n"
                f"冲击量 Dp = {summary.Dp_pu:.6f} pu\n"
                f"估算第一摆功率振荡幅值 ΔP_osc ≈ {summary.osc_amp_pu:.6f} pu\n"
            )
            if summary.margin_pu is not None:
                text += f"与当前功率幅值对比量 = {summary.margin_pu:.6f} pu\n"
            text += f"结论：{summary.status}\n"

            # ── 临界切除角快速估算 ────────────────────────────────────────
            if pcur_text and tj_text and f0_text:
                try:
                    Pm_val  = _safe_float(pcur_text, "Pm")
                    Tj_val  = _safe_float(tj_text,   "T_j")
                    f0_val  = _safe_float(f0_text,   "f0")
                    pmax_post = _safe_float(self.eac_ppost.get(), "Pmax_post")
                    ccs = critical_cut_angle_approx(Pm_val, pmax_post, Tj_val, f0_val, delta_t)
                    text += (
                        f"\n══ 临界切除角快速估算（§7.6） ══════\n"
                        f"初始平衡角   δ0  = {ccs.delta0_deg:.3f}°\n"
                        f"临界切除角   δcr = {ccs.delta_cr_deg:.3f}°\n"
                        f"临界切除时间 tcr = {ccs.t_cr_s:.4f} s\n"
                        f"当前切除时间 Δt  = {delta_t:.4f} s  "
                        f"({'< tcr OK' if delta_t < ccs.t_cr_s else '>= tcr NG'})\n"
                    )
                    if ccs.margin_pct is not None:
                        text += f"时间裕量 = {ccs.margin_pct:+.1f} %\n"
                    text += f"结论：{ccs.status}\n"
                    text += f"\n说明（冲击法）：\n{summary.notes}\n"
                    text += f"\n说明（临界切除）：\n{ccs.notes}"
                except InputError as ie:
                    text += f"\n临界切除角估算：{ie}\n"
                    text += f"\n说明：\n{summary.notes}"
            else:
                text += (
                    "\n（如需临界切除角快速估算，请同时填写 Pm、T_j 和 f0）\n"
                    f"\n说明：\n{summary.notes}"
                )

            self._set_text(self.imp_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_eac(self) -> None:
        try:
            Pm        = _safe_float(self.eac_pm.get(),    "Pm")
            Pmax_pre  = _safe_float(self.eac_ppre.get(),  "Pmax_pre")
            Pmax_f    = _safe_float(self.eac_pf.get(),    "Pmax_fault")
            Pmax_post = _safe_float(self.eac_ppost.get(), "Pmax_post")
            dt        = _safe_float(self.eac_dt.get(),    "Δt")
            Tj        = _safe_float(self.eac_tj.get(),    "Tj")
            f0        = _safe_float(self.eac_f0.get(),    "f0")

            r = equal_area_criterion(Pm, Pmax_pre, Pmax_f, Pmax_post, dt, Tj, f0)

            # ── 结果文字 ────────────────────────────────────────────────
            stab_str = "[稳定]" if r.stable else "[失稳]（加速面积 > 可用减速面积）"
            text = (
                f"稳定性判断：{stab_str}\n"
                f"裕度 = {r.margin_pct:+.2f} %\n"
                f"\n── 关键角度 ──────────────────────\n"
                f"故障前平衡角 δ0  = {r.delta0_deg:.3f}°\n"
                f"故障切除角   δc  = {r.deltac_deg:.3f}°\n"
                f"不稳定平衡角 δu  = {r.deltau_deg:.3f}°\n"
            )
            if r.deltamax_deg is not None:
                text += f"实际最大摆角 δmax= {r.deltamax_deg:.3f}°\n"
            text += (
                f"\n── 等面积 ────────────────────────\n"
                f"加速面积  Aacc       = {r.A_acc:.6f} pu·rad\n"
                f"可用减速面积 Adec    = {r.A_dec_avail:.6f} pu·rad\n"
            )
            if r.A_dec_actual is not None:
                text += f"实际减速面积 Adec_act= {r.A_dec_actual:.6f} pu·rad\n"
            text += (
                f"\n── 极限切除 ──────────────────────\n"
                f"极限切除角 δcr = {r.delta_cr_deg:.3f}°\n"
                f"极限切除时间 tcr = {r.t_cr_s:.4f} s\n"
                f"当前切除时间 Δt  = {dt:.4f} s  "
                f"({'< tcr OK' if dt < r.t_cr_s else '>= tcr NG'})\n"
                f"\n说明：\n{r.notes}"
            )
            self._set_text(self.eac_result, text)

            # ── P-δ 图 ──────────────────────────────────────────────────
            ax = self.eac_ax
            ax.clear()

            delta_deg = np.linspace(0, 200, 1000)
            delta_rad = np.radians(delta_deg)

            Pe_pre   = Pmax_pre  * np.sin(delta_rad)
            Pe_fault = Pmax_f    * np.sin(delta_rad)
            Pe_post  = Pmax_post * np.sin(delta_rad)

            ax.plot(delta_deg, Pe_pre,   "b-",  linewidth=1.8,
                    label=f"故障前  Pmax={Pmax_pre:.3f} pu")
            fault_lbl = (f"故障中  Pmax={Pmax_f:.3f} pu"
                         + ("（三相短路≈0）" if Pmax_f < 1e-9 else ""))
            ax.plot(delta_deg, Pe_fault, "r--", linewidth=1.5, label=fault_lbl)
            ax.plot(delta_deg, Pe_post,  "g-",  linewidth=1.8,
                    label=f"故障后  Pmax={Pmax_post:.3f} pu")
            ax.axhline(Pm, color="k", linewidth=1.4, linestyle=":",
                       label=f"Pm = {Pm:.3f} pu")

            # 加速面积（红色填充）δ0 → δc，曲线为故障中正弦
            d_acc = np.linspace(r.delta0_rad, r.deltac_rad, 500)
            Pe_f_acc = Pmax_f * np.sin(d_acc)
            # 正加速（Pm > Pe_fault）→ 红色；负加速（Pe_fault > Pm）→ 蓝紫色
            ax.fill_between(np.degrees(d_acc), Pm, Pe_f_acc,
                            where=(Pm >= Pe_f_acc),
                            color="tomato", alpha=0.45,
                            label=f"加速面积（+）{r.A_acc:.4f} pu·rad")
            if np.any(Pe_f_acc > Pm):
                neg_area = float(
                    np.trapz(np.maximum(0, Pe_f_acc - Pm), d_acc))
                ax.fill_between(np.degrees(d_acc), Pe_f_acc, Pm,
                                where=(Pe_f_acc > Pm),
                                color="mediumpurple", alpha=0.40,
                                label=f"减速（故障中）{neg_area:.4f} pu·rad")

            # 减速面积（绿色填充）δc → δmax（或 δu）
            d_end = r.deltamax_rad if r.deltamax_rad is not None else r.deltau_rad
            d_dec = np.linspace(r.deltac_rad, d_end, 500)
            Pe_post_dec = Pmax_post * np.sin(d_dec)
            ax.fill_between(np.degrees(d_dec),
                            Pe_post_dec, Pm,
                            where=(Pe_post_dec >= Pm),
                            color="limegreen", alpha=0.45,
                            label=f"减速面积 {r.A_dec_avail:.4f} pu·rad")

            # 关键角度标注
            def _vline(deg: float, color: str, ls: str, label: str) -> None:
                ax.axvline(deg, color=color, linestyle=ls, linewidth=1.2, label=label)

            _vline(r.delta0_deg,  "blue",  "-.",  f"δ0={r.delta0_deg:.1f}°")
            _vline(r.deltac_deg,  "red",   "--",  f"δc={r.deltac_deg:.1f}°")
            _vline(r.deltau_deg,  "green", "-.",  f"δu={r.deltau_deg:.1f}°")
            _vline(r.delta_cr_deg,"purple",":",   f"δcr={r.delta_cr_deg:.1f}°")
            if r.deltamax_deg is not None:
                _vline(r.deltamax_deg, "darkorange", "--",
                       f"δmax={r.deltamax_deg:.1f}°")

            ax.set_xlabel("δ / °")
            ax.set_ylabel("P / pu")
            title_flag = "[稳定]" if r.stable else "[失稳]"
            ax.set_title(
                f"功角曲线  {title_flag}  裕度 {r.margin_pct:+.1f}%  "
                f"tcr={r.t_cr_s:.3f} s"
            )
            ax.set_xlim(0, 200)
            ymax = max(Pmax_pre, Pmax_post, Pm) * 1.18
            ax.set_ylim(-0.08, ymax)
            ax.legend(loc="upper right", fontsize=7.5, ncol=2)
            ax.grid(True, alpha=0.4)
            self.eac_fig.tight_layout()
            self.eac_canvas.draw()

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))



    def _build_short_circuit_tab(self) -> None:
        self._sc_ui_ready = False
        self.sc_tab.columnconfigure(1, weight=1)
        self.sc_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.sc_tab, padding=10)
        right = ttk.Frame(self.sc_tab, padding=10)
        left.grid(row=0, column=0, sticky="nsw")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(left, text="短路电流计算（支持单电源/双电源+线路故障点）", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        self.sc_mode = ttk.Combobox(left, state="readonly", width=18, values=["单电源", "双电源"])
        ttk.Label(left, text="网络模式").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.sc_mode.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        self.sc_mode.set("单电源")

        self.sc_fault_type = ttk.Combobox(left, state="readonly", width=18,
                                          values=["A相接地", "B相接地", "C相接地", "AB两相接地", "BC两相接地", "CA两相接地", "AB两相短路", "BC两相短路", "CA两相短路", "三相接地"])
        ttk.Label(left, text="故障类型").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.sc_fault_type.grid(row=2, column=1, sticky="ew", padx=4, pady=4)
        self.sc_fault_type.set("A相接地")

        self.sc_u = self._add_entry(left, 3, "系统电压 U / kV（线电压）", "110")
        self.sc_ssc = self._add_entry(left, 4, "左侧系统短路容量 S_sc / MVA", "2000")
        self.sc_xr = self._add_entry(left, 5, "左侧系统 X/R 比", "10")
        self.sc_ssc_r = self._add_entry(left, 6, "右侧系统短路容量 S_sc,R / MVA", "2000")
        self.sc_xr_r = self._add_entry(left, 7, "右侧系统 X/R 比", "10")
        self.sc_e_left = self._add_entry(left, 8, "左侧预故障电势 E_L / pu", "1.00")
        self.sc_delta_left = self._add_entry(left, 9, "左侧预故障相角 δL / °", "0.0")
        self.sc_e_right = self._add_entry(left, 10, "右侧预故障电势 E_R / pu", "1.00")
        self.sc_delta_right = self._add_entry(left, 11, "右侧预故障相角 δR / °", "0.0")
        self.sc_fault_pos = self._add_entry(left, 12, "故障点距左侧百分比 / %", "50")
        self.sc_len = self._add_entry(left, 13, "线路长度 / km", "30")
        self.sc_r1 = self._add_entry(left, 14, "线路正序电阻 R1 / (Ω/km)", "0.05")
        self.sc_x1 = self._add_entry(left, 15, "线路正序电抗 X1 / (Ω/km)", "0.40")
        self.sc_r0 = self._add_entry(left, 16, "线路零序电阻 R0 / (Ω/km)", "0.15")
        self.sc_x0 = self._add_entry(left, 17, "线路零序电抗 X0 / (Ω/km)", "1.20")
        self.sc_rf = self._add_entry(left, 18, "过渡电阻 Rf / Ω", "0.0")

        self.sc_neutral_mode = ttk.Combobox(left, state="readonly", width=18,
                                            values=["直接接地", "中性点不接地", "经消弧线圈接地", "经电阻接地"])
        ttk.Label(left, text="左侧中性点方式").grid(row=19, column=0, sticky="w", padx=4, pady=4)
        self.sc_neutral_mode.grid(row=19, column=1, sticky="ew", padx=4, pady=4)
        self.sc_neutral_mode.set("直接接地")

        self.sc_rn = self._add_entry(left, 20, "左侧中性点电阻 Rn,L / Ω", "1.5")
        self.sc_xn = self._add_entry(left, 21, "左侧中性点电抗 Xn,L / Ω", "12.0")

        self.sc_neutral_mode_r = ttk.Combobox(left, state="readonly", width=18,
                                              values=["直接接地", "中性点不接地", "经消弧线圈接地", "经电阻接地"])
        ttk.Label(left, text="右侧中性点方式").grid(row=22, column=0, sticky="w", padx=4, pady=4)
        self.sc_neutral_mode_r.grid(row=22, column=1, sticky="ew", padx=4, pady=4)
        self.sc_neutral_mode_r.set("直接接地")
        self.sc_rn_r = self._add_entry(left, 23, "右侧中性点电阻 Rn,R / Ω", "1.5")
        self.sc_xn_r = self._add_entry(left, 24, "右侧中性点电抗 Xn,R / Ω", "12.0")

        self.sc_mode.bind("<<ComboboxSelected>>", self._on_sc_mode_change)
        self.sc_neutral_mode.bind("<<ComboboxSelected>>", self._on_sc_neutral_mode_change)
        self.sc_neutral_mode_r.bind("<<ComboboxSelected>>", self._on_sc_neutral_mode_change)
        self.sc_len.bind("<FocusOut>", self._on_sc_neutral_mode_change)
        self.sc_r0.bind("<FocusOut>", self._on_sc_neutral_mode_change)
        self.sc_x0.bind("<FocusOut>", self._on_sc_neutral_mode_change)
        self._on_sc_neutral_mode_change()
        self.sc_brk = self._add_entry(left, 25, "断路器额定开断电流 Ik / kA（可留空）", "31.5")
        self.sc_cycles = self._add_entry(left, 26, "仿真周波数（波形）", "10")

        self.sc_vector_labels_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="向量图显示数值标签", variable=self.sc_vector_labels_var, command=self.calculate_short_circuit).grid(
            row=27, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 2)
        )
        ttk.Label(left, text="故障点位置滑条（双电源）").grid(row=28, column=0, sticky="w", padx=4, pady=(2, 2))
        self.sc_fault_slider = ttk.Scale(left, from_=0.0, to=100.0, orient=tk.HORIZONTAL, command=self._on_sc_fault_slider)
        self.sc_fault_slider.grid(row=28, column=1, sticky="ew", padx=4, pady=(2, 2))
        ttk.Button(left, text="计算并绘图", command=self.calculate_short_circuit).grid(
            row=29, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 4)
        )

        self.sc_result = ScrolledText(left, width=58, height=20, wrap=tk.WORD)
        self.sc_result.grid(row=30, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        self.sc_result.configure(state="disabled")
        self.sc_fault_slider.set(50.0)

        ttk.Label(right, text="短路点电流波形", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        self.sc_fig = Figure(figsize=(10.8, 7.0), dpi=100)
        gs = self.sc_fig.add_gridspec(2, 2, width_ratios=[1.7, 1.0], hspace=0.26, wspace=0.18)
        self.sc_ax_phase = self.sc_fig.add_subplot(gs[0, 0])
        self.sc_ax_seq = self.sc_fig.add_subplot(gs[1, 0])
        self.sc_ax_i_vector = self.sc_fig.add_subplot(gs[0, 1], projection="polar")
        self.sc_ax_v_vector = self.sc_fig.add_subplot(gs[1, 1], projection="polar")
        self.sc_ax_phase.set_ylabel("i_abc / A")
        self.sc_ax_seq.set_ylabel("i_012 / A")
        self.sc_ax_seq.set_xlabel("t / s")
        self.sc_ax_phase.grid(True, alpha=0.4)
        self.sc_ax_seq.grid(True, alpha=0.4)
        self._draw_short_circuit_vector_axis(self.sc_ax_i_vector, {}, "故障点电流向量图")
        self._draw_short_circuit_vector_axis(self.sc_ax_v_vector, {}, "故障点电压向量图")

        self.sc_canvas = FigureCanvasTkAgg(self.sc_fig, master=right)
        self.sc_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        self.sc_toolbar = NavigationToolbar2Tk(self.sc_canvas, right, pack_toolbar=False)
        self.sc_toolbar.update()
        self.sc_toolbar.grid(row=2, column=0, sticky="ew")

        self._on_sc_mode_change()
        self._sc_ui_ready = True
        self.calculate_short_circuit()

    def _on_sc_neutral_mode_change(self, _event: object | None = None) -> None:
        """根据线路零序参数给出与量级匹配的中性点参数默认值。"""
        try:
            length = _safe_float(self.sc_len.get(), "线路长度")
            r0 = _safe_float(self.sc_r0.get(), "R0")
            x0 = _safe_float(self.sc_x0.get(), "X0")
            r0_total = max(0.0, r0 * length)
            x0_total = max(0.0, x0 * length)
        except Exception:
            r0_total, x0_total = 4.5, 36.0

        def _defaults(mode: str) -> tuple[float, float]:
            if mode == "直接接地":
                return 0.0, 0.0
            if mode == "中性点不接地":
                return 1e9, 0.0
            if mode == "经消弧线圈接地":
                return 0.0, x0_total / 3.0
            if mode == "经电阻接地":
                return r0_total / 3.0, 0.0
            return 0.0, 0.0

        rn_l, xn_l = _defaults(self.sc_neutral_mode.get().strip())
        rn_r, xn_r = _defaults(self.sc_neutral_mode_r.get().strip())

        self.sc_rn.delete(0, tk.END)
        self.sc_rn.insert(0, f"{rn_l:.6g}")
        self.sc_xn.delete(0, tk.END)
        self.sc_xn.insert(0, f"{xn_l:.6g}")
        self.sc_rn_r.delete(0, tk.END)
        self.sc_rn_r.insert(0, f"{rn_r:.6g}")
        self.sc_xn_r.delete(0, tk.END)
        self.sc_xn_r.insert(0, f"{xn_r:.6g}")

    def _on_sc_fault_slider(self, value: str) -> None:
        if not getattr(self, "_sc_ui_ready", False):
            return
        try:
            v = float(value)
        except Exception:
            return
        self.sc_fault_pos.configure(state="normal")
        self.sc_fault_pos.delete(0, tk.END)
        self.sc_fault_pos.insert(0, f"{v:.2f}")
        if self.sc_mode.get().strip() != "双电源":
            self.sc_fault_pos.configure(state="disabled")
        self.calculate_short_circuit()

    def _on_sc_mode_change(self, _event: object | None = None) -> None:
        is_dual = self.sc_mode.get().strip() == "双电源"
        state = "normal" if is_dual else "disabled"
        dual_entries = (
            self.sc_ssc_r, self.sc_xr_r, self.sc_fault_pos,
            self.sc_e_right, self.sc_delta_right,
            self.sc_rn_r, self.sc_xn_r,
        )
        for entry in dual_entries:
            entry.configure(state=state)
        self.sc_neutral_mode_r.configure(state="readonly" if is_dual else "disabled")
        self.sc_fault_slider.configure(state=state)
        if not is_dual:
            self.sc_fault_pos.configure(state="normal")
            self.sc_fault_pos.delete(0, tk.END)
            self.sc_fault_pos.insert(0, "100")
            self.sc_fault_pos.configure(state="disabled")
            self.sc_fault_slider.set(100.0)

    def _draw_short_circuit_vector_axis(self, ax, vectors: dict[str, complex], title: str, show_labels: bool = True) -> None:
        ax.clear()
        ax.set_theta_zero_location("E")
        ax.set_theta_direction(1)
        ax.set_facecolor("#11161d")
        ax.set_title(title, color="#f5f7fa", fontsize=10, pad=10)
        colors = {
            "A": "#7ec8ff", "B": "#ffe082", "C": "#ff8a80",
            "1": "#66bb6a", "2": "#42a5f5", "0": "#b388ff",
        }
        if not vectors:
            ax.set_ylim(0.0, 1.0)
            ax.grid(color="#5f6f7e", linestyle="-", linewidth=0.8, alpha=0.45)
            ax.set_yticks([0.25, 0.5, 0.75, 1.0])
            ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], color="#aeb8c2", fontsize=8)
            ax.set_thetagrids(np.arange(0, 360, 45), color="#8ea1b4", fontsize=8)
            return
        max_mag = max(1e-6, max(abs(v) for v in vectors.values()))
        radial_max = max_mag * 1.15
        ax.set_ylim(0.0, radial_max)
        rings = np.linspace(radial_max / 4.0, radial_max, 4)
        ax.set_yticks(rings)
        ax.set_yticklabels([f"{tick:.3g}" for tick in rings], color="#aeb8c2", fontsize=8)
        ax.set_thetagrids(np.arange(0, 360, 45), color="#8ea1b4", fontsize=8)
        ax.grid(color="#5f6f7e", linestyle="-", linewidth=0.8, alpha=0.45)
        ax.spines["polar"].set_color("#7c8794")
        ax.spines["polar"].set_linewidth(1.0)
        for name, val in vectors.items():
            theta = math.atan2(val.imag, val.real)
            radius = abs(val)
            color = colors.get(name, "#ffffff")
            ax.annotate(
                "",
                xy=(theta, radius),
                xytext=(theta, 0.0),
                arrowprops=dict(arrowstyle="-|>", color=color, linewidth=2.2, linestyle="-", shrinkA=0, shrinkB=0),
            )
            if show_labels:
                ang = math.degrees(theta)
                ax.text(theta, min(radial_max, radius * 1.07), f"{name}\n{radius:.3g}∠{ang:.1f}°",
                        color=color, fontsize=7, ha="center", va="center")

    def calculate_short_circuit(self) -> None:
        try:
            mode = self.sc_mode.get().strip()
            fault_type = self.sc_fault_type.get().strip()
            neutral_mode = self.sc_neutral_mode.get().strip()
            U = _safe_float(self.sc_u.get(), "U")
            Ssc = _safe_float(self.sc_ssc.get(), "S_sc")
            xr = _safe_float(self.sc_xr.get(), "X/R")
            Ssc_r = _safe_float(self.sc_ssc_r.get(), "S_sc,R")
            xr_r = _safe_float(self.sc_xr_r.get(), "X/R,R")
            e_left = _safe_float(self.sc_e_left.get(), "E_L")
            d_left = _safe_float(self.sc_delta_left.get(), "δL")
            e_right = _safe_float(self.sc_e_right.get(), "E_R")
            d_right = _safe_float(self.sc_delta_right.get(), "δR")
            fault_pos_pct = _safe_float(self.sc_fault_pos.get(), "故障点百分比")
            length = _safe_float(self.sc_len.get(), "线路长度")
            R1 = _safe_float(self.sc_r1.get(), "R1")
            X1 = _safe_float(self.sc_x1.get(), "X1")
            R0 = _safe_float(self.sc_r0.get(), "R0")
            X0 = _safe_float(self.sc_x0.get(), "X0")
            Rf = _safe_float(self.sc_rf.get(), "Rf")
            Rn = _safe_float(self.sc_rn.get(), "Rn")
            Xn = _safe_float(self.sc_xn.get(), "Xn")
            neutral_mode_right = self.sc_neutral_mode_r.get().strip()
            Rn_r = _safe_float(self.sc_rn_r.get(), "Rn,R")
            Xn_r = _safe_float(self.sc_xn_r.get(), "Xn,R")
            cycles = max(1.0, _safe_float(self.sc_cycles.get(), "仿真周波数"))
            brk_txt = self.sc_brk.get().strip()
            brk = _safe_float(brk_txt, "Ik") if brk_txt else None

            r = short_circuit_capacity(U, fault_type, Ssc, xr, length, R1, X1, R0, X0,
                                       neutral_mode, Rn, Xn, Rf, brk,
                                       network_mode=mode, s_sc_right_mva=Ssc_r, xr_sys_right=xr_r,
                                       fault_pos_from_left_pct=fault_pos_pct,
                                       e_left_pu=e_left, e_right_pu=e_right,
                                       delta_left_deg=d_left, delta_right_deg=d_right,
                                       neutral_mode_right=neutral_mode_right,
                                       neutral_rn_right_ohm=Rn_r, neutral_xn_right_ohm=Xn_r)

            def _pa(z: complex) -> str:
                return f"{abs(z):.2f}∠{math.degrees(math.atan2(z.imag, z.real)):.1f}°"

            if r.breaker_ok is None:
                check = "未输入断路器开断电流，未做匹配判断。"
            else:
                check = "匹配：额定开断电流 ≥ 计算开断电流。" if r.breaker_ok else "不匹配：额定开断电流 < 计算开断电流。"

            text = (
                f"══ 复合序网计算结果 ═════════════════════════════\n"
                f"  网络模式：{r.network_mode}\n"
                f"  故障类型：{r.fault_type}，中性点：{r.neutral_mode}\n"
                f"  U = {r.U_kV:.4g} kV，线路长度 = {r.line_len_km:.4g} km，Rf = {r.Rf_ohm:.4g} Ω\n"
                f"  故障点位置（距左侧）= {r.fault_pos_from_left_pct:.3g}%\n"
                f"  Z1 = {r.Z1_ohm.real:.4f}+j{r.Z1_ohm.imag:.4f} Ω\n"
                f"  Z2 = {r.Z2_ohm.real:.4f}+j{r.Z2_ohm.imag:.4f} Ω\n"
                f"  Z0 = {r.Z0_ohm.real:.4f}+j{r.Z0_ohm.imag:.4f} Ω\n"
                f"  Zn = {r.Zn_ohm.real:.4f}+j{r.Zn_ohm.imag:.4f} Ω\n"
                f"  I1 = {_pa(r.I1_A)} A\n"
                f"  I2 = {_pa(r.I2_A)} A\n"
                f"  I0 = {_pa(r.I0_A)} A\n"
                f"  Ia = {_pa(r.Ia_A)} A\n"
                f"  Ib = {_pa(r.Ib_A)} A\n"
                f"  Ic = {_pa(r.Ic_A)} A\n"
                f"  V1 = {_pa(r.V1_V)} V\n"
                f"  V2 = {_pa(r.V2_V)} V\n"
                f"  V0 = {_pa(r.V0_V)} V\n"
                f"  Va = {_pa(r.Va_V)} V\n"
                f"  Vb = {_pa(r.Vb_V)} V\n"
                f"  Vc = {_pa(r.Vc_V)} V\n"
                f"  左侧支路 Ia/Ib/Ic = {_pa(r.Ia_from_left_A)} / {_pa(r.Ib_from_left_A)} / {_pa(r.Ic_from_left_A)} A\n"
                f"  右侧支路 Ia/Ib/Ic = {_pa(r.Ia_from_right_A)} / {_pa(r.Ib_from_right_A)} / {_pa(r.Ic_from_right_A)} A\n"
                f"  左侧开断校核电流 Ibreak,L = {r.I_break_left_kA:.4f} kA\n"
                f"  右侧开断校核电流 Ibreak,R = {r.I_break_right_kA:.4f} kA\n"
                f"  开断校核电流 Ibreak = {r.I_break_kA:.4f} kA\n"
                f"  直流偏置时间常数 τ = {r.tau_dc_s:.6f} s\n"
                f"\n══ 断路器匹配 ═════════════════════════════════════\n"
                f"  {check}\n"
                f"\n说明：{r.notes}"
            )
            self._set_text(self.sc_result, text)

            f = 50.0
            w = 2.0 * math.pi * f
            t_end = cycles / f
            t = np.linspace(0.0, t_end, int(2400 * cycles / 3.0) + 1)

            def iwave(I: complex) -> np.ndarray:
                amp = math.sqrt(2.0) * abs(I)
                phi = math.atan2(I.imag, I.real)
                iac = amp * np.sin(w * t + phi)
                idc = -amp * math.sin(phi) * np.exp(-t / max(r.tau_dc_s, 1e-4))
                return iac + idc

            ia = iwave(r.Ia_A)
            ib = iwave(r.Ib_A)
            ic = iwave(r.Ic_A)
            i1 = iwave(r.I1_A)
            i2 = iwave(r.I2_A)
            i0 = iwave(r.I0_A)

            self.sc_ax_phase.clear()
            self.sc_ax_seq.clear()
            self.sc_ax_phase.plot(t, ia, label="iA", lw=1.2)
            self.sc_ax_phase.plot(t, ib, label="iB", lw=1.2)
            self.sc_ax_phase.plot(t, ic, label="iC", lw=1.2)
            self.sc_ax_phase.set_ylabel("i_abc / A")
            self.sc_ax_phase.grid(True, alpha=0.35)
            self.sc_ax_phase.legend(loc="upper right", ncol=3, fontsize=8)

            self.sc_ax_seq.plot(t, i1, label="i1(正序)", lw=1.2)
            self.sc_ax_seq.plot(t, i2, label="i2(负序)", lw=1.2)
            self.sc_ax_seq.plot(t, i0, label="i0(零序)", lw=1.2)
            self.sc_ax_seq.set_ylabel("i_012 / A")
            self.sc_ax_seq.set_xlabel("t / s")
            self.sc_ax_seq.grid(True, alpha=0.35)
            self.sc_ax_seq.legend(loc="upper right", ncol=3, fontsize=8)

            asym_faults = {"A相接地", "B相接地", "C相接地", "AB两相接地", "BC两相接地", "CA两相接地", "AB两相短路", "BC两相短路", "CA两相短路"}
            show_labels = bool(self.sc_vector_labels_var.get())
            if r.fault_type in asym_faults:
                i_vectors = {"A": r.Ia_A, "B": r.Ib_A, "C": r.Ic_A, "1": r.I1_A, "2": r.I2_A, "0": r.I0_A}
                v_vectors = {"A": r.Va_V, "B": r.Vb_V, "C": r.Vc_V, "1": r.V1_V, "2": r.V2_V, "0": r.V0_V}
                self._draw_short_circuit_vector_axis(self.sc_ax_i_vector, i_vectors, "故障点电流向量图（ABC+012）", show_labels=show_labels)
                self._draw_short_circuit_vector_axis(self.sc_ax_v_vector, v_vectors, "故障点电压向量图（ABC+012）", show_labels=show_labels)
            else:
                self._draw_short_circuit_vector_axis(self.sc_ax_i_vector, {}, "故障点电流向量图（仅不对称故障绘制）", show_labels=show_labels)
                self._draw_short_circuit_vector_axis(self.sc_ax_v_vector, {}, "故障点电压向量图（仅不对称故障绘制）", show_labels=show_labels)

            self.sc_fig.tight_layout()
            self.sc_canvas.draw()

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    # ════════════════════════════════════════════════════════════════════
    # 参数校核与标幺值转换标签页
    # ════════════════════════════════════════════════════════════════════

    def _build_param_tab(self) -> None:
        """构建"参数校核与标幺值转换"标签页（含线路、双绕组变压器、三绕组变压器子页）。"""
        self.param_tab.columnconfigure(0, weight=1)
        self.param_tab.rowconfigure(0, weight=1)

        nb = ttk.Notebook(self.param_tab)
        nb.grid(row=0, column=0, sticky="nsew")
        self.param_notebook = nb
        self.param_notebook.bind("<<NotebookTabChanged>>", self._on_ai_context_changed)

        self._ptab_line = ttk.Frame(nb)
        self._ptab_2wt  = ttk.Frame(nb)
        self._ptab_3wt  = ttk.Frame(nb)
        nb.add(self._ptab_line, text="架空线路")
        nb.add(self._ptab_2wt,  text="两绕组变压器")
        nb.add(self._ptab_3wt,  text="三绕组变压器")

        self._build_line_param_sub()
        self._build_2wt_sub()
        self._build_3wt_sub()

    # ── 架空线路子页 ─────────────────────────────────────────────────────────

    def _build_line_param_sub(self) -> None:
        f = self._ptab_line
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="架空线路参数校核与标幺值转换（π 型等值）",
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4))

        hint = ("典型范围参考（§3.3/3.4）：R₁ 0.005~0.65 Ω/km，"
                "X₁ 0.20~0.42 Ω/km，C₁ 0.008~0.014 μF/km，"
                "Zc 240~420 Ω；超高压取下限，配电取上限。点击“线路参数计算”可由导线几何、土壤与地线数据反算 R₁/X₁/R₀/X₀/C₁/C₀。")
        ttk.Label(f, text=hint, wraplength=620, foreground="#555555").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

        self.lp_r1    = self._add_entry(f,  2, "单位长度电阻 R₁ / (Ω/km)", "0.028")
        self.lp_x1    = self._add_entry(f,  3, "单位长度电抗 X₁ / (Ω/km)", "0.299")
        self.lp_c1    = self._add_entry(f,  4, "单位长度电容 C₁ / (μF/km)", "0.013")
        self.lp_len   = self._add_entry(f,  5, "线路长度 / km", "200")
        self.lp_sbase = self._add_entry(f,  6, "基准容量 Sbase / MVA", "100")
        self.lp_ubase = self._add_entry(f,  7, "基准电压 Ubase / kV（线电压）", "500")

        button_row = ttk.Frame(f)
        button_row.grid(row=8, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)

        ttk.Button(button_row, text="计算并校核", command=self.calculate_line_param).grid(
            row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(button_row, text="线路参数计算", command=self.open_line_geometry_calculator).grid(
            row=0, column=1, sticky="ew", padx=4)
        ttk.Button(button_row, text="典型参数", command=self.show_line_param_reference).grid(
            row=0, column=2, sticky="ew", padx=(4, 0))

        self.lp_result = ScrolledText(f, width=85, height=20, wrap=tk.WORD)
        self.lp_result.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)
        f.rowconfigure(9, weight=1)
        self.lp_result.configure(state="disabled")
        self.calculate_line_param()

    # ── 两绕组变压器子页 ─────────────────────────────────────────────────────

    def _build_2wt_sub(self) -> None:
        f = self._ptab_2wt
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="两绕组变压器参数校核与标幺值转换",
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4))

        hint = ("典型范围（§3.5）：Uk% 4~18%（特高压主变 18~24%），"
                "I₀% 0.1~5%，短路损耗 1~7 kW/MVA，空载损耗 0.1~3 kW/MVA。")
        ttk.Label(f, text=hint, wraplength=620, foreground="#555555").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

        self.tx2_pk    = self._add_entry(f,  2, "短路损耗 Pk / kW", "290")
        self.tx2_uk    = self._add_entry(f,  3, "短路电压 Uk / %", "11.73")
        self.tx2_p0    = self._add_entry(f,  4, "空载损耗 P0 / kW", "51.3")
        self.tx2_i0    = self._add_entry(f,  5, "空载电流 I₀ / %", "0.3")
        self.tx2_sn    = self._add_entry(f,  6, "额定容量 SN / MVA", "20")
        self.tx2_un    = self._add_entry(f,  7, "高压侧额定电压 UN / kV", "35")
        self.tx2_sbase = self._add_entry(f,  8, "基准容量 Sbase / MVA", "100")
        self.tx2_ubase = self._add_entry(f,  9, "基准电压 Ubase / kV（通常 = UN）", "35")

        ttk.Button(f, text="计算并校核", command=self.calculate_2wt).grid(
            row=10, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))

        self.tx2_result = ScrolledText(f, width=85, height=18, wrap=tk.WORD)
        self.tx2_result.grid(row=11, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)
        f.rowconfigure(11, weight=1)
        self.tx2_result.configure(state="disabled")
        self.calculate_2wt()

    # ── 三绕组变压器子页 ─────────────────────────────────────────────────────

    def _build_3wt_sub(self) -> None:
        f = self._ptab_3wt
        f.columnconfigure(1, weight=1)
        f.columnconfigure(3, weight=1)

        ttk.Label(f, text="三绕组变压器参数校核与标幺值转换",
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(8, 4))

        hint = ("输入约定：Pk 为两两短路试验损耗（kW），Uk% 为两两短路电压（%）。"
                "Pk_HL、Uk_HL 若测试是在低压侧额定电流下做的，"
                "程序会自动按 SN_H/SN_L 折算到高压侧额定电流基准。")
        ttk.Label(f, text=hint, wraplength=900, foreground="#555555").grid(
            row=1, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 6))

        row = 2
        self.tx3_pk_hm  = self._add_entry(f, row,   "短路损耗 Pk_HM / kW",    "503.6",  column=0)
        self.tx3_uk_hm  = self._add_entry(f, row,   "Uk_HM / %",              "17.5",   column=2)
        row += 1
        self.tx3_pk_hl  = self._add_entry(f, row,   "短路损耗 Pk_HL / kW",    "129.0",  column=0)
        self.tx3_uk_hl  = self._add_entry(f, row,   "Uk_HL / %",              "11.0",   column=2)
        row += 1
        self.tx3_pk_ml  = self._add_entry(f, row,   "短路损耗 Pk_ML / kW",    "120.7",  column=0)
        self.tx3_uk_ml  = self._add_entry(f, row,   "Uk_ML / %",              "6.0",    column=2)
        row += 1
        self.tx3_p0     = self._add_entry(f, row,   "空载损耗 P0 / kW",       "76.1",   column=0)
        self.tx3_i0     = self._add_entry(f, row,   "空载电流 I₀ / %",        "0.07",   column=2)
        row += 1
        self.tx3_sn_h   = self._add_entry(f, row,   "高压侧额定容量 SN_H / MVA", "180", column=0)
        self.tx3_un_h   = self._add_entry(f, row,   "高压侧额定电压 UN_H / kV",  "220", column=2)
        row += 1
        self.tx3_sn_m   = self._add_entry(f, row,   "中压侧额定容量 SN_M / MVA", "180", column=0)
        self.tx3_sn_l   = self._add_entry(f, row,   "低压侧额定容量 SN_L / MVA", "90",  column=2)
        row += 1
        self.tx3_sbase  = self._add_entry(f, row,   "基准容量 Sbase / MVA",    "100",   column=0)
        self.tx3_ubase  = self._add_entry(f, row,   "基准电压 Ubase / kV",     "220",   column=2)

        row += 1
        ttk.Button(f, text="计算并校核", command=self.calculate_3wt).grid(
            row=row, column=0, columnspan=4, sticky="ew", padx=8, pady=(8, 4))

        row += 1
        self.tx3_result = ScrolledText(f, width=95, height=18, wrap=tk.WORD)
        self.tx3_result.grid(row=row, column=0, columnspan=4, sticky="nsew", padx=8, pady=4)
        f.rowconfigure(row, weight=1)
        self.tx3_result.configure(state="disabled")
        self.calculate_3wt()

    # ── 参数校核计算处理函数 ─────────────────────────────────────────────────

    def show_line_param_reference(self) -> None:
        """弹出架空线路典型参数窗口（按电压等级展示）。"""
        try:
            data = load_line_params_reference()
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))
            return

        win = tk.Toplevel(self)
        win.title("架空线路典型参数")
        win.geometry("980x700")
        win.minsize(860, 560)

        container = ttk.Frame(win, padding=8)
        container.pack(fill="both", expand=True)

        title = data.get("description") or "架空线路典型参数"
        ttk.Label(container, text=title, font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        #ttk.Label(container, text=f"数据来源：{data.get('source_file', '-')}", foreground="#666666").pack(anchor="w", pady=(2, 6))

        text = ScrolledText(container, wrap=tk.NONE, font="TkFixedFont")
        text.pack(fill="both", expand=True)

        lines = []
        for sec in data.get("sections", []):
            voltage = sec.get("voltage_level_kv")
            line_type = sec.get("line_type") or "-"
            sec_title = sec.get("section_title", "未命名分组")
            lines.append(f"\n【{sec_title}】")
            if voltage:
                lines.append(f"电压等级：{voltage} kV    线路类型：{line_type}")
            source_note = sec.get("source_note") or sec.get("note")
            if source_note:
                lines.append(f"说明：{source_note}")

            entries = sec.get("entries", [])
            if not entries:
                lines.append("  （无数据）")
                continue

            lines.append("型号/布置                          R1(Ω/km)   X1(Ω/km)   C1(μF/km)   R0(Ω/km)   X0(Ω/km)   C0(μF/km)")
            lines.append("-" * 112)
            for item in entries:
                model = str(item.get("conductor_model") or "-")
                layout = item.get("layout")
                if layout:
                    model = f"{model} / {layout}"

                def _fmt(v: object) -> str:
                    return "-" if v is None else f"{float(v):.6g}"

                lines.append(
                    f"{model:<34}"
                    f"{_fmt(item.get('R1_ohm_per_km')):>10}"
                    f"{_fmt(item.get('X1_ohm_per_km')):>12}"
                    f"{_fmt(item.get('C1_uF_per_km')):>13}"
                    f"{_fmt(item.get('R0_ohm_per_km')):>12}"
                    f"{_fmt(item.get('X0_ohm_per_km')):>12}"
                    f"{_fmt(item.get('C0_uF_per_km')):>13}"
                )

        text.insert("1.0", "\n".join(lines).lstrip())
        text.configure(state="disabled")

    def open_line_geometry_calculator(self) -> None:
        if self._line_geometry_window is not None:
            try:
                if self._line_geometry_window.winfo_exists():
                    self._line_geometry_window.deiconify()
                    self._line_geometry_window.lift()
                    self._line_geometry_window.focus_force()
                    return
            except Exception:
                self._line_geometry_window = None

        win = tk.Toplevel(self)
        self._line_geometry_window = win
        win.title("线路参数计算")
        win.geometry("1180x780")
        win.minsize(1040, 700)

        def _on_close() -> None:
            self._line_geometry_window = None
            self._line_geometry_entries = {}
            self._line_geometry_ground_widgets = []
            self._line_geometry_has_gw_var = None
            self._line_geometry_bundle_var = None
            self._line_geometry_result = None
            self._line_geometry_fig = None
            self._line_geometry_canvas = None
            self._line_geometry_ax = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_close)

        container = ttk.Frame(win, padding=8)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        left = ttk.Frame(container, padding=6)
        right = ttk.Frame(container, padding=6)
        left.grid(row=0, column=0, sticky="nsw")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(2, weight=2)

        ttk.Label(left, text="线路参数计算（由几何数据反算序参数）",
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 6)
        )
        intro = (
            "输入三相导线横坐标 x、离地高度 h、单分裂导线参数、土壤电阻率，以及是否设置地线。"
            "程序按三段完全换位平均：串联参数用复深度近似，电容/电纳用镜像法电位系数。"
            "地线若启用，则按连续接地导体并经 Kron 消去处理。"
        )
        ttk.Label(left, text=intro, wraplength=430, justify="left", foreground="#555555").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(0, 8)
        )

        self._line_geometry_entries = {}
        self._line_geometry_ground_widgets = []
        self._line_geometry_bundle_var = tk.StringVar(value="4")
        self._line_geometry_has_gw_var = tk.BooleanVar(value=False)

        def add(parent: ttk.Frame, key: str, row: int, label: str, default: str,
                column: int = 0, width: int = 12) -> ttk.Entry:
            entry = self._add_entry(parent, row, label, default, column=column, width=width)
            self._line_geometry_entries[key] = entry
            return entry

        sec0 = ttk.LabelFrame(left, text="1）系统与导线数据", padding=6)
        sec0.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        sec0.columnconfigure(1, weight=1)
        sec0.columnconfigure(3, weight=1)

        add(sec0, "f_hz", 0, "频率 f / Hz", "50", column=0)
        add(sec0, "rho", 0, "土壤电阻率 ρ / (Ω·m)", "100", column=2)
        add(sec0, "phase_r_sub", 1, "单分裂导线电阻 r / (Ω/km)", "0.032", column=0)
        add(sec0, "phase_gmr_sub", 1, "单分裂导线 GMR / m", "0.0115", column=2)
        add(sec0, "phase_radius_sub", 2, "单分裂导线半径 r / m", "0.0159", column=0)
        add(sec0, "bundle_spacing", 2, "分裂间距 d / m（n>1）", "0.45", column=2)

        ttk.Label(sec0, text="分裂根数 n（4 根按正方形近似）").grid(
            row=3, column=0, sticky="w", padx=4, pady=4
        )
        bundle_box = ttk.Combobox(sec0, width=10, state="readonly",
                                  textvariable=self._line_geometry_bundle_var,
                                  values=["1", "2", "3", "4"])
        bundle_box.grid(row=3, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(sec0, text="说明：上述 r / GMR / 半径均指单根子导线数据。",
                  foreground="#666666").grid(
            row=3, column=2, columnspan=2, sticky="w", padx=4, pady=4
        )

        sec1 = ttk.LabelFrame(left, text="2）三相导线几何坐标", padding=6)
        sec1.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        sec1.columnconfigure(1, weight=1)
        sec1.columnconfigure(3, weight=1)

        add(sec1, "xA", 0, "A 相 x / m", "-12", column=0)
        add(sec1, "hA", 0, "A 相 h / m", "20", column=2)
        add(sec1, "xB", 1, "B 相 x / m", "0", column=0)
        add(sec1, "hB", 1, "B 相 h / m", "20", column=2)
        add(sec1, "xC", 2, "C 相 x / m", "12", column=0)
        add(sec1, "hC", 2, "C 相 h / m", "20", column=2)

        sec2 = ttk.LabelFrame(left, text="3）地线（可选）", padding=6)
        sec2.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        sec2.columnconfigure(1, weight=1)
        sec2.columnconfigure(3, weight=1)

        ttk.Checkbutton(sec2, text="启用地线并计及屏蔽影响",
                        variable=self._line_geometry_has_gw_var,
                        command=self._on_line_geometry_ground_toggle).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=4, pady=(0, 4)
        )
        gw_widgets: list[tk.Widget] = []
        gw_widgets.extend([
            add(sec2, "xg", 1, "地线 x / m", "0", column=0),
            add(sec2, "hg", 1, "地线 h / m", "28", column=2),
            add(sec2, "gw_r", 2, "地线电阻 r / (Ω/km)", "0.05", column=0),
            add(sec2, "gw_gmr", 2, "地线 GMR / m", "0.0045", column=2),
            add(sec2, "gw_radius", 3, "地线半径 r / m", "0.005", column=0),
        ])
        ttk.Label(sec2, text="地线按单根连续接地导体处理。",
                  foreground="#666666").grid(
            row=3, column=2, columnspan=2, sticky="w", padx=4, pady=4
        )
        self._line_geometry_ground_widgets = gw_widgets
        self._on_line_geometry_ground_toggle()

        topbar = ttk.Frame(right)
        topbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        topbar.columnconfigure(0, weight=1)
        ttk.Label(topbar, text="计算结果", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(topbar, text="计算", command=self.calculate_line_geometry_popup).grid(
            row=0, column=1, padx=(4, 0)
        )
        ttk.Button(topbar, text="回填正序到本页", command=self._fill_line_geometry_to_line_param).grid(
            row=0, column=2, padx=(4, 0)
        )
        ttk.Button(topbar, text="回填序参数到短路页", command=self._fill_line_geometry_to_short_circuit).grid(
            row=0, column=3, padx=(4, 0)
        )

        plot_frame = ttk.LabelFrame(right, text="导线横截面示意图", padding=4)
        plot_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)
        self._line_geometry_fig = Figure(figsize=(7.2, 4.1), dpi=100)
        self._line_geometry_ax = self._line_geometry_fig.add_subplot(111)
        self._line_geometry_canvas = FigureCanvasTkAgg(self._line_geometry_fig, master=plot_frame)
        self._line_geometry_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        self._line_geometry_result = ScrolledText(right, width=78, height=22, wrap=tk.WORD, font="TkFixedFont")
        self._line_geometry_result.grid(row=2, column=0, sticky="nsew")
        self._line_geometry_result.configure(state="disabled")

        self.calculate_line_geometry_popup()

    def _on_line_geometry_ground_toggle(self) -> None:
        enabled = bool(self._line_geometry_has_gw_var and self._line_geometry_has_gw_var.get())
        self._set_enabled(self._line_geometry_ground_widgets, enabled)

    def _read_line_geometry_inputs(self) -> dict[str, object]:
        if not self._line_geometry_entries:
            raise InputError("线路参数计算窗口尚未初始化。")

        name_map = {
            "f_hz": "频率",
            "rho": "土壤电阻率",
            "phase_r_sub": "单分裂导线电阻",
            "phase_gmr_sub": "单分裂导线 GMR",
            "phase_radius_sub": "单分裂导线半径",
            "bundle_spacing": "分裂间距",
            "xA": "A 相 x",
            "hA": "A 相 h",
            "xB": "B 相 x",
            "hB": "B 相 h",
            "xC": "C 相 x",
            "hC": "C 相 h",
            "xg": "地线 x",
            "hg": "地线 h",
            "gw_r": "地线电阻",
            "gw_gmr": "地线 GMR",
            "gw_radius": "地线半径",
        }

        base_keys = [
            "f_hz", "rho",
            "phase_r_sub", "phase_gmr_sub", "phase_radius_sub", "bundle_spacing",
            "xA", "hA", "xB", "hB", "xC", "hC",
        ]
        vals = {
            key: _safe_float(self._line_geometry_entries[key].get(), name_map.get(key, key))
            for key in base_keys
        }

        if self._line_geometry_bundle_var is None:
            raise InputError("分裂根数控件未初始化。")
        try:
            bundle_count = int(self._line_geometry_bundle_var.get().strip())
        except Exception as exc:
            raise InputError("分裂根数必须为 1、2、3、4。") from exc

        has_ground = bool(self._line_geometry_has_gw_var and self._line_geometry_has_gw_var.get())
        if has_ground:
            for key in ["xg", "hg", "gw_r", "gw_gmr", "gw_radius"]:
                vals[key] = _safe_float(self._line_geometry_entries[key].get(), name_map.get(key, key))

        return {
            "frequency_hz": vals["f_hz"],
            "soil_resistivity_ohm_m": vals["rho"],
            "phase_positions": [(vals["xA"], vals["hA"]), (vals["xB"], vals["hB"]), (vals["xC"], vals["hC"])],
            "phase_resistance_ohm_per_km": vals["phase_r_sub"],
            "phase_gmr_m": vals["phase_gmr_sub"],
            "phase_radius_m": vals["phase_radius_sub"],
            "phase_bundle_count": bundle_count,
            "phase_bundle_spacing_m": vals["bundle_spacing"],
            "has_ground_wire": has_ground,
            "ground_wire_position": (vals["xg"], vals["hg"]) if has_ground else None,
            "ground_wire_resistance_ohm_per_km": vals["gw_r"] if has_ground else 0.0,
            "ground_wire_gmr_m": vals["gw_gmr"] if has_ground else 0.0,
            "ground_wire_radius_m": vals["gw_radius"] if has_ground else 0.0,
        }

    def calculate_line_geometry_popup(self) -> None:
        try:
            if self._line_geometry_result is None:
                raise InputError("线路参数计算结果窗口未初始化。")
            inputs = self._read_line_geometry_inputs()
            result = calculate_overhead_line_sequence(**inputs)
            self._line_geometry_last_result = result

            def fmt_complex(z: complex, unit: str, digits: int = 6) -> str:
                sign = "+" if z.imag >= 0 else "-"
                return f"{z.real:.{digits}f} {sign} j{abs(z.imag):.{digits}f} {unit}"

            mode = "有地线" if result.has_ground_wire else "无地线"
            text = (
                f"计算模型：{mode}，f = {result.frequency_hz:.4g} Hz，ρ = {result.soil_resistivity_ohm_m:.4g} Ω·m\n"
                f"\n── 几何与等效数据 ───────────────────────────\n"
                f"AB 间距 = {result.D_ab_m:.6f} m\n"
                f"BC 间距 = {result.D_bc_m:.6f} m\n"
                f"CA 间距 = {result.D_ca_m:.6f} m\n"
                f"分裂根数 n = {result.phase_bundle_count:d}\n"
                f"等效相导线电阻 = {result.phase_bundle_resistance_ohm_per_km:.6f} Ω/km\n"
                f"等效相导线 GMR = {result.phase_bundle_gmr_m:.6f} m\n"
                f"等效相导线半径 = {result.phase_bundle_radius_m:.6f} m\n"
                f"\n── 每相、每公里的序参数 ───────────────────────\n"
                f"Z1 = {fmt_complex(result.Z1_ohm_per_km, 'Ω/km')}\n"
                f"Z0 = {fmt_complex(result.Z0_ohm_per_km, 'Ω/km')}\n"
                f"Y1 = {fmt_complex(result.Y1_S_per_km, 'S/km', 8)}\n"
                f"Y0 = {fmt_complex(result.Y0_S_per_km, 'S/km', 8)}\n"
                f"C1 = {result.C1_uF_per_km:.6f} μF/km\n"
                f"C0 = {result.C0_uF_per_km:.6f} μF/km\n"
                f"B1 = {result.B1_uS_per_km:.6f} μS/km\n"
                f"B0 = {result.B0_uS_per_km:.6f} μS/km\n"
                f"\n结论：正序参数可直接回填“架空线路”页，零序参数可同步回填“短路电流计算”页。\n"
                f"\n说明：\n{result.notes}"
            )
            self._set_text(self._line_geometry_result, text)
            self._draw_line_geometry_schematic(inputs, result)
        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def _draw_line_geometry_schematic(self, inputs: dict[str, object], result) -> None:
        if self._line_geometry_ax is None or self._line_geometry_canvas is None:
            return
        ax = self._line_geometry_ax
        ax.clear()
        ax.set_facecolor("#f8fafc")
        ax.set_title("按输入几何尺寸等比例绘制", fontsize=11, pad=10)

        phase_positions = list(inputs["phase_positions"])
        has_ground = bool(inputs["has_ground_wire"])
        ground_position = inputs["ground_wire_position"] if has_ground else None
        radius = max(float(inputs["phase_radius_m"]), float(inputs.get("ground_wire_radius_m", 0.0) or 0.0), 0.12)
        all_points = phase_positions + ([ground_position] if ground_position is not None else [])
        xs = [pt[0] for pt in all_points]
        ys = [pt[1] for pt in all_points]
        x_min, x_max = min(xs), max(xs)
        y_max = max(ys)
        x_pad = max(2.0, 0.15 * max(1.0, x_max - x_min), radius * 6.0)
        y_pad = max(2.0, 0.15 * max(1.0, y_max), radius * 8.0)

        ax.axhline(0.0, color="#5b6470", linewidth=2.0, linestyle="-")
        ax.fill_between([x_min - x_pad, x_max + x_pad], -y_pad * 0.22, 0.0, color="#dde6ef", alpha=0.85)
        ax.text(x_min - x_pad * 0.95, 0.35, "地平面", color="#3a4756", fontsize=9, ha="left", va="bottom")

        phase_colors = [("A相导线", "#4f8ef7"), ("B相导线", "#ffb020"), ("C相导线", "#ff6b6b")]
        legend_handles = []
        for (label, color), (x, y) in zip(phase_colors, phase_positions):
            circle = Circle((x, y), radius=radius, facecolor=color, edgecolor="#1f2933", linewidth=1.2, zorder=3)
            ax.add_patch(circle)
            ax.text(x, y + radius * 1.7, label.replace("导线", ""), ha="center", va="bottom", fontsize=9, color=color, fontweight="bold")
            legend_handles.append(Line2D([0], [0], marker="o", linestyle="", markerfacecolor=color, markeredgecolor="#1f2933", markersize=8, label=label))
            self._draw_vertical_dimension(ax, x, y, f"h={y:.2f} m", color=color)

        if ground_position is not None:
            gx, gy = ground_position
            g_radius = max(float(inputs.get("ground_wire_radius_m", 0.0) or 0.0), radius * 0.7)
            circle = Circle((gx, gy), radius=g_radius, facecolor="#6b7280", edgecolor="#1f2933", linewidth=1.2, zorder=3)
            ax.add_patch(circle)
            ax.text(gx, gy + g_radius * 1.7, "地线", ha="center", va="bottom", fontsize=9, color="#374151", fontweight="bold")
            legend_handles.append(Line2D([0], [0], marker="o", linestyle="", markerfacecolor="#6b7280", markeredgecolor="#1f2933", markersize=8, label="地线"))
            self._draw_vertical_dimension(ax, gx, gy, f"h={gy:.2f} m", color="#4b5563", x_offset=max(radius * 2.0, 0.8))

        xa, ya = phase_positions[0]
        xb, yb = phase_positions[1]
        xc, yc = phase_positions[2]
        self._draw_dimension_line(ax, (xa, ya), (xb, yb), f"AB={result.D_ab_m:.2f} m", "#2563eb")
        self._draw_dimension_line(ax, (xb, yb), (xc, yc), f"BC={result.D_bc_m:.2f} m", "#d97706")
        self._draw_dimension_line(ax, (xa, ya), (xc, yc), f"CA={result.D_ca_m:.2f} m", "#dc2626", text_offset=1.2)

        ax.set_xlim(x_min - x_pad, x_max + x_pad)
        ax.set_ylim(-y_pad * 0.22, y_max + y_pad)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.35)
        ax.set_xlabel("横坐标 x / m")
        ax.set_ylabel("高度 h / m")
        ax.legend(handles=legend_handles, loc="upper right", frameon=True, fontsize=9)
        self._line_geometry_fig.tight_layout()
        self._line_geometry_canvas.draw()

    @staticmethod
    def _draw_vertical_dimension(ax, x: float, y: float, label: str, color: str, x_offset: float = 0.0) -> None:
        x_dim = x + x_offset
        ax.annotate("", xy=(x_dim, y), xytext=(x_dim, 0.0), arrowprops=dict(arrowstyle="<->", color=color, linewidth=1.1))
        ax.plot([x, x_dim], [y, y], color=color, linewidth=0.9, linestyle=":")
        ax.text(x_dim + 0.18, y / 2.0, label, color=color, fontsize=8.5, va="center", ha="left",
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.75))

    @staticmethod
    def _draw_dimension_line(ax, p1: tuple[float, float], p2: tuple[float, float], label: str, color: str, text_offset: float = 0.7) -> None:
        x1, y1 = p1
        x2, y2 = p2
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="<->", color=color, linewidth=1.2))
        mx = (x1 + x2) / 2.0
        my = (y1 + y2) / 2.0
        dx = x2 - x1
        dy = y2 - y1
        length = max((dx ** 2 + dy ** 2) ** 0.5, 1e-9)
        nx = -dy / length
        ny = dx / length
        ax.text(
            mx + nx * text_offset,
            my + ny * text_offset,
            label,
            color=color,
            fontsize=8.5,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.8),
        )

    @staticmethod
    def _replace_entry(entry: ttk.Entry, value: float, fmt: str = ".6g") -> None:
        entry.delete(0, tk.END)
        entry.insert(0, format(value, fmt))

    def _fill_line_geometry_to_line_param(self) -> None:
        result = self._line_geometry_last_result
        if result is None:
            messagebox.showwarning("尚未计算", "请先在“线路参数计算”窗口中完成计算。")
            return
        self._replace_entry(self.lp_r1, result.Z1_ohm_per_km.real)
        self._replace_entry(self.lp_x1, result.Z1_ohm_per_km.imag)
        self._replace_entry(self.lp_c1, result.C1_uF_per_km)
        self.calculate_line_param()

    def _fill_line_geometry_to_short_circuit(self) -> None:
        result = self._line_geometry_last_result
        if result is None:
            messagebox.showwarning("尚未计算", "请先在“线路参数计算”窗口中完成计算。")
            return
        self._replace_entry(self.sc_r1, result.Z1_ohm_per_km.real)
        self._replace_entry(self.sc_x1, result.Z1_ohm_per_km.imag)
        self._replace_entry(self.sc_r0, result.Z0_ohm_per_km.real)
        self._replace_entry(self.sc_x0, result.Z0_ohm_per_km.imag)
        self._on_sc_neutral_mode_change()

    def calculate_line_param(self) -> None:
        try:
            R1    = _safe_float(self.lp_r1.get(),    "R₁")
            X1    = _safe_float(self.lp_x1.get(),    "X₁")
            C1    = _safe_float(self.lp_c1.get(),    "C₁")
            length = _safe_float(self.lp_len.get(),  "线路长度")
            Sbase = _safe_float(self.lp_sbase.get(), "Sbase")
            Ubase = _safe_float(self.lp_ubase.get(), "Ubase")

            r = convert_line_to_pu(R1, X1, C1, length, Sbase, Ubase)

            text = (
                f"══ 有名值（π型等值，折算后）══════════════════════\n"
                f"  总电阻  R  = {r.R_total_ohm:.6f} Ω\n"
                f"  总电抗  X  = {r.X_total_ohm:.6f} Ω\n"
                f"  对地电纳半值 B/2 = {r.B_half_S:.8f} S\n"
                f"  波阻抗  Zc = {r.Zc_ohm:.4f} Ω\n"
                f"\n══ 标幺值（Sbase={Sbase:.4g} MVA，Ubase={Ubase:.4g} kV）══════\n"
                f"  基准阻抗 Zbase = {r.Zbase_ohm:.4f} Ω，  "
                f"基准导纳 Ybase = {r.Ybase_S:.8f} S\n"
                f"  R_pu   = {r.R_pu:.8f}  pu\n"
                f"  X_pu   = {r.X_pu:.8f}  pu\n"
                f"  B/2_pu = {r.B_half_pu:.8f}  pu\n"
                f"\n══ 参数校核 ═══════════════════════════════════════\n"
                + _format_warnings(r.warnings)
            )
            self._set_text(self.lp_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_2wt(self) -> None:
        try:
            Pk    = _safe_float(self.tx2_pk.get(),    "Pk")
            Uk    = _safe_float(self.tx2_uk.get(),    "Uk%")
            P0    = _safe_float(self.tx2_p0.get(),    "P0")
            I0    = _safe_float(self.tx2_i0.get(),    "I0%")
            SN    = _safe_float(self.tx2_sn.get(),    "SN")
            UN    = _safe_float(self.tx2_un.get(),    "UN")
            Sbase = _safe_float(self.tx2_sbase.get(), "Sbase")
            Ubase = _safe_float(self.tx2_ubase.get(), "Ubase")

            r = convert_2wt_to_pu(Pk, Uk, P0, I0, SN, UN, Sbase, Ubase)

            text = (
                f"══ 有名值（折算到高压侧 {UN:.4g} kV）══════════════════\n"
                f"  短路电阻   Rk  = {r.Rk_ohm:.6f}  Ω\n"
                f"  短路电抗   Xk  = {r.Xk_ohm:.6f}  Ω\n"
                f"  励磁电导   G₀  = {r.G0_S:.2e}  S\n"
                f"  励磁电纳   B₀  = {r.B0_S:.2e}  S\n"
                f"\n══ 标幺值（Sbase={Sbase:.4g} MVA，Ubase={Ubase:.4g} kV）══════\n"
                f"  基准阻抗 Zbase = {r.Zbase_ohm:.4f} Ω\n"
                f"  Rk_pu  = {r.Rk_pu:.8f}  pu\n"
                f"  Xk_pu  = {r.Xk_pu:.8f}  pu\n"
                f"  G₀_pu  = {r.G0_pu:.8f}  pu\n"
                f"  B₀_pu  = {r.B0_pu:.8f}  pu\n"
                f"  （反算 Uk% ≈ {r.Uk_pct_check:.4f}%，输入 {Uk:.4f}%）\n"
                f"\n══ 参数校核 ═══════════════════════════════════════\n"
                + _format_warnings(r.warnings)
            )
            self._set_text(self.tx2_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def calculate_3wt(self) -> None:
        try:
            Pk_HM  = _safe_float(self.tx3_pk_hm.get(),  "Pk_HM")
            Pk_HL  = _safe_float(self.tx3_pk_hl.get(),  "Pk_HL")
            Pk_ML  = _safe_float(self.tx3_pk_ml.get(),  "Pk_ML")
            Uk_HM  = _safe_float(self.tx3_uk_hm.get(),  "Uk_HM%")
            Uk_HL  = _safe_float(self.tx3_uk_hl.get(),  "Uk_HL%")
            Uk_ML  = _safe_float(self.tx3_uk_ml.get(),  "Uk_ML%")
            P0     = _safe_float(self.tx3_p0.get(),     "P0")
            I0     = _safe_float(self.tx3_i0.get(),     "I0%")
            SN_H   = _safe_float(self.tx3_sn_h.get(),   "SN_H")
            SN_M   = _safe_float(self.tx3_sn_m.get(),   "SN_M")
            SN_L   = _safe_float(self.tx3_sn_l.get(),   "SN_L")
            UN_H   = _safe_float(self.tx3_un_h.get(),   "UN_H")
            Sbase  = _safe_float(self.tx3_sbase.get(),  "Sbase")
            Ubase  = _safe_float(self.tx3_ubase.get(),  "Ubase")

            r = convert_3wt_to_pu(
                Pk_HM, Pk_HL, Pk_ML,
                Uk_HM, Uk_HL, Uk_ML,
                P0, I0,
                SN_H, SN_M, SN_L, UN_H,
                Sbase, Ubase)

            SN_base = SN_H
            text = (
                f"══ 折算参考容量 SN_base = {SN_base:.4g} MVA，折算基压 {UN_H:.4g} kV ══════\n"
                f"\n── 有名值（T型等值，折算到高压侧）────────────────────\n"
                f"  高压绕组  RH = {r.RH_ohm:.6f} Ω，  XH = {r.XH_ohm:.6f} Ω\n"
                f"  中压绕组  RM = {r.RM_ohm:.6f} Ω，  XM = {r.XM_ohm:.6f} Ω\n"
                f"  低压绕组  RL = {r.RL_ohm:.6f} Ω，  XL = {r.XL_ohm:.6f} Ω\n"
                f"\n── 标幺值（Sbase={Sbase:.4g} MVA，Ubase={Ubase:.4g} kV）─────────────\n"
                f"  基准阻抗 Zbase = {r.Zbase_ohm:.4f} Ω\n"
                f"  高压绕组  RH_pu = {r.RH_pu:.8f}，  XH_pu = {r.XH_pu:.8f}\n"
                f"  中压绕组  RM_pu = {r.RM_pu:.8f}，  XM_pu = {r.XM_pu:.8f}\n"
                f"  低压绕组  RL_pu = {r.RL_pu:.8f}，  XL_pu = {r.XL_pu:.8f}\n"
                f"  励磁电导  G₀_pu = {r.G0_pu:.8f}，  励磁电纳 B₀_pu = {r.B0_pu:.8f}\n"
                f"\n══ 参数校核 ═══════════════════════════════════════\n"
                + _format_warnings(r.warnings)
            )
            self._set_text(self.tx3_result, text)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))


    def _build_loop_closure_tab(self) -> None:
        self.loop_tab.columnconfigure(1, weight=1)
        self.loop_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.loop_tab, padding=10)
        right = ttk.Frame(self.loop_tab, padding=10)
        left.grid(row=0, column=0, sticky="nsw")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(3, weight=2)

        basic = ttk.LabelFrame(left, text="合环近似参数", padding=8)
        basic.pack(fill="x", expand=False, pady=(0, 8))
        basic.columnconfigure(1, weight=1)
        basic.columnconfigure(3, weight=1)

        self.loop_n = self._add_entry(basic, 0, "连接点数量 N", "7", column=0)
        ttk.Label(basic, text="合环点编号").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.loop_closure = ttk.Combobox(basic, state="readonly", width=10)
        self.loop_closure.grid(row=0, column=3, sticky="ew", padx=4, pady=4)
        self.loop_closure.bind("<<ComboboxSelected>>", self._refresh_loop_closure_indicator)

        self.loop_u1 = self._add_entry(basic, 1, "U1 / kV（线电压）", "10", column=0)
        self.loop_u2 = self._add_entry(basic, 1, "U2 / kV（线电压）", "10", column=2)
        self.loop_angle = self._add_entry(basic, 2, "两侧相角差 φ / °", "14", column=0)
        self.loop_freq = self._add_entry(basic, 2, "系统频率 / Hz", "50", column=2)
        self.loop_r = self._add_entry(basic, 3, "回路电阻 RΣ / Ω", "1.13", column=0)
        self.loop_x = self._add_entry(basic, 3, "回路电抗 XΣ / Ω", "4.20", column=2)
        self.loop_total_len = self._add_entry(basic, 4, "总线路长度 / km", "11", column=0)
        self.loop_pf = self._add_entry(basic, 4, "统一功率因数 cosφ", "0.99", column=2)

        ttk.Label(basic, text="功率因数类型").grid(row=5, column=0, sticky="w", padx=4, pady=4)
        self.loop_pf_mode = ttk.Combobox(basic, state="readonly", values=["滞后", "超前"], width=10)
        self.loop_pf_mode.grid(row=5, column=1, sticky="ew", padx=4, pady=4)
        self.loop_pf_mode.set("滞后")
        self.loop_ampacity = self._add_entry(basic, 5, "额定载流量 / A", "442", column=2)
        self.loop_overload = self._add_entry(basic, 6, "短时过载系数 K", "1.5", column=0)
        self.loop_tclose = self._add_entry(basic, 6, "合环时刻 / s", "0.10", column=2)
        self.loop_tend = self._add_entry(basic, 7, "波形结束时刻 / s", "0.30", column=0)

        tools = ttk.Frame(basic)
        tools.grid(row=8, column=0, columnspan=4, sticky="ew", padx=4, pady=(6, 2))
        ttk.Button(tools, text="按 N 重建表格", command=self._rebuild_loop_closure_rows).pack(side="left", padx=(0, 6))
        ttk.Button(tools, text="加载默认值", command=self._apply_loop_closure_appendix_defaults).pack(side="left", padx=(0, 6))
        ttk.Button(tools, text="计算并绘图", command=self.calculate_loop_closure).pack(side="left")

        hint = (
            "输入约定：每个连接点填写净线电流（A）。正值表示负荷，负值表示分布式电源回送，0 表示空点。"
            " 合环点必须对应空点。线段比例默认均匀分布；若输入自定义比例，则按 N+1 个线段比例自动归一。"
        )
        ttk.Label(left, text=hint, justify="left", wraplength=430).pack(fill="x", pady=(0, 6))

        table_box = ttk.LabelFrame(left, text="连接点表", padding=6)
        table_box.pack(fill="both", expand=True, pady=(0, 8))

        self.loop_table_canvas = tk.Canvas(table_box, height=265, highlightthickness=0)
        self.loop_table_canvas.pack(side="left", fill="both", expand=True)
        table_scroll = ttk.Scrollbar(table_box, orient="vertical", command=self.loop_table_canvas.yview)
        table_scroll.pack(side="right", fill="y")
        self.loop_table_canvas.configure(yscrollcommand=table_scroll.set)

        self.loop_table_frame = ttk.Frame(self.loop_table_canvas)
        self._loop_table_window = self.loop_table_canvas.create_window((0, 0), window=self.loop_table_frame, anchor="nw")
        self.loop_table_frame.bind("<Configure>", lambda e: self.loop_table_canvas.configure(scrollregion=self.loop_table_canvas.bbox("all")))
        self.loop_table_canvas.bind("<Configure>", lambda e: self.loop_table_canvas.itemconfigure(self._loop_table_window, width=e.width))

        ratio_box = ttk.LabelFrame(left, text="线段比例（N+1 段）", padding=6)
        ratio_box.pack(fill="x", expand=False)
        self.loop_ratio_frame = ttk.Frame(ratio_box)
        self.loop_ratio_frame.pack(fill="x", expand=True)

        self.loop_node_label_entries: list[ttk.Entry] = []
        self.loop_node_current_entries: list[ttk.Entry] = []
        self.loop_node_indicator_labels: list[ttk.Label] = []
        self.loop_ratio_entries: list[ttk.Entry] = []
        self._last_loop_result = None

        ttk.Label(right, text="计算结果", font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.loop_result = ScrolledText(right, width=82, height=18, wrap=tk.WORD, font="TkFixedFont")
        self.loop_result.grid(row=1, column=0, sticky="nsew")
        self.loop_result.configure(state="disabled")

        plot_nb = ttk.Notebook(right)
        plot_nb.grid(row=3, column=0, sticky="nsew", pady=(10, 0))

        profile_page = ttk.Frame(plot_nb, padding=4)
        wave_page = ttk.Frame(plot_nb, padding=4)
        plot_nb.add(profile_page, text="点位图与稳态电流")
        plot_nb.add(wave_page, text="冲击暂态电流")
        profile_page.columnconfigure(0, weight=1)
        profile_page.rowconfigure(0, weight=1)
        wave_page.columnconfigure(0, weight=1)
        wave_page.rowconfigure(0, weight=1)

        self.loop_profile_fig = Figure(figsize=(7.4, 3.4), dpi=100)
        self.loop_profile_ax = self.loop_profile_fig.add_subplot(111)
        self.loop_profile_canvas = FigureCanvasTkAgg(self.loop_profile_fig, master=profile_page)
        self.loop_profile_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.loop_profile_toolbar = NavigationToolbar2Tk(self.loop_profile_canvas, profile_page, pack_toolbar=False)
        self.loop_profile_toolbar.update()
        self.loop_profile_toolbar.grid(row=1, column=0, sticky="ew")

        self.loop_wave_fig = Figure(figsize=(7.4, 6.0), dpi=100)
        self.loop_wave_ax1 = self.loop_wave_fig.add_subplot(311)
        self.loop_wave_ax2 = self.loop_wave_fig.add_subplot(312)
        self.loop_wave_ax3 = self.loop_wave_fig.add_subplot(313)
        self.loop_wave_canvas = FigureCanvasTkAgg(self.loop_wave_fig, master=wave_page)
        self.loop_wave_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.loop_wave_toolbar = NavigationToolbar2Tk(self.loop_wave_canvas, wave_page, pack_toolbar=False)
        self.loop_wave_toolbar.update()
        self.loop_wave_toolbar.grid(row=1, column=0, sticky="ew")

        self._rebuild_loop_closure_rows()
        self._apply_loop_closure_appendix_defaults()

    def _refresh_loop_closure_indicator(self, _event: object | None = None) -> None:
        try:
            closure = int(self.loop_closure.get())
        except Exception:
            return
        for idx, label in enumerate(self.loop_node_indicator_labels, start=1):
            if idx == closure:
                label.configure(text="◉ 合环点")
            else:
                label.configure(text="")

    def _rebuild_loop_closure_rows(self) -> None:
        try:
            n = int(round(_safe_float(self.loop_n.get(), "连接点数量 N")))
            if n < 1:
                raise InputError("连接点数量 N 必须为正整数。")
        except Exception as exc:
            messagebox.showerror("输入错误", str(exc))
            return

        old_labels = [entry.get() for entry in self.loop_node_label_entries]
        old_currents = [entry.get() for entry in self.loop_node_current_entries]
        old_ratios = [entry.get() for entry in self.loop_ratio_entries]
        try:
            old_closure = int(self.loop_closure.get())
        except Exception:
            old_closure = min(max(1, n // 2 + 1), n)

        for child in self.loop_table_frame.winfo_children():
            child.destroy()
        for child in self.loop_ratio_frame.winfo_children():
            child.destroy()

        self.loop_node_label_entries = []
        self.loop_node_current_entries = []
        self.loop_node_indicator_labels = []
        self.loop_ratio_entries = []

        ttk.Label(self.loop_table_frame, text="编号", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, sticky="w", padx=3, pady=2)
        ttk.Label(self.loop_table_frame, text="标签", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=1, sticky="w", padx=3, pady=2)
        ttk.Label(self.loop_table_frame, text="净电流 / A", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=2, sticky="w", padx=3, pady=2)
        ttk.Label(self.loop_table_frame, text="说明", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=3, sticky="w", padx=3, pady=2)

        for i in range(n):
            ttk.Label(self.loop_table_frame, text=str(i + 1)).grid(row=i + 1, column=0, sticky="w", padx=3, pady=2)
            label_entry = ttk.Entry(self.loop_table_frame, width=10)
            label_entry.grid(row=i + 1, column=1, sticky="ew", padx=3, pady=2)
            label_entry.insert(0, old_labels[i] if i < len(old_labels) else f"点{i + 1}")

            current_entry = ttk.Entry(self.loop_table_frame, width=12)
            current_entry.grid(row=i + 1, column=2, sticky="ew", padx=3, pady=2)
            current_entry.insert(0, old_currents[i] if i < len(old_currents) else "0")

            note_lbl = ttk.Label(self.loop_table_frame, text="")
            note_lbl.grid(row=i + 1, column=3, sticky="w", padx=3, pady=2)

            self.loop_node_label_entries.append(label_entry)
            self.loop_node_current_entries.append(current_entry)
            self.loop_node_indicator_labels.append(note_lbl)

        closure_values = [str(i) for i in range(1, n + 1)]
        self.loop_closure.configure(values=closure_values)
        self.loop_closure.set(str(min(max(1, old_closure), n)))
        self._refresh_loop_closure_indicator()

        ttk.Label(self.loop_ratio_frame, text="段号", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, sticky="w", padx=3, pady=2)
        ttk.Label(self.loop_ratio_frame, text="比例", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=1, sticky="w", padx=3, pady=2)
        for idx in range(n + 1):
            r = idx + 1
            row = 1 + idx // 4
            col = (idx % 4) * 2
            ttk.Label(self.loop_ratio_frame, text=f"r{r}").grid(row=row, column=col, sticky="w", padx=3, pady=2)
            entry = ttk.Entry(self.loop_ratio_frame, width=8)
            entry.grid(row=row, column=col + 1, sticky="w", padx=3, pady=2)
            entry.insert(0, old_ratios[idx] if idx < len(old_ratios) else "1")
            self.loop_ratio_entries.append(entry)

    def _apply_loop_closure_appendix_defaults(self) -> None:
        defaults = {
            self.loop_n: "7",
            self.loop_u1: "10",
            self.loop_u2: "10",
            self.loop_angle: "14",
            self.loop_freq: "50",
            self.loop_r: "1.13",
            self.loop_x: "4.20",
            self.loop_total_len: "11",
            self.loop_pf: "0.99",
            self.loop_ampacity: "442",
            self.loop_overload: "1.5",
            self.loop_tclose: "0.10",
            self.loop_tend: "0.30",
        }
        for widget, value in defaults.items():
            widget.delete(0, tk.END)
            widget.insert(0, value)

        self.loop_pf_mode.set("滞后")
        self._rebuild_loop_closure_rows()
        self.loop_closure.set("4")
        self._refresh_loop_closure_indicator()

        labels = ["A", "B", "C", "联络点", "D", "E", "F"]
        injections = [79.35, 117.40, 116.60, 0.0, 136.69, 58.81, 158.66]
        for entry, label in zip(self.loop_node_label_entries, labels):
            entry.delete(0, tk.END)
            entry.insert(0, label)
        for entry, value in zip(self.loop_node_current_entries, injections):
            entry.delete(0, tk.END)
            entry.insert(0, f"{value:.2f}")
        for entry in self.loop_ratio_entries:
            entry.delete(0, tk.END)
            entry.insert(0, "1")

        self.calculate_loop_closure()

    def _read_loop_closure_inputs(self):
        n = int(round(_safe_float(self.loop_n.get(), "连接点数量 N")))
        if n < 1:
            raise InputError("连接点数量 N 必须为正整数。")
        if len(self.loop_node_current_entries) != n or len(self.loop_ratio_entries) != n + 1:
            raise InputError("连接点表或线段比例与当前 N 不一致，请先点击“按 N 重建表格”。")

        closure = int(self.loop_closure.get())
        node_labels = [entry.get().strip() or f"点{i}" for i, entry in enumerate(self.loop_node_label_entries, start=1)]
        node_currents = [_safe_float(entry.get(), f"连接点 {i} 净电流") for i, entry in enumerate(self.loop_node_current_entries, start=1)]
        ratios = [_safe_float(entry.get(), f"线段比例 r{i}") for i, entry in enumerate(self.loop_ratio_entries, start=1)]

        ampacity_text = self.loop_ampacity.get().strip()
        ampacity = None if ampacity_text == "" else _safe_float(ampacity_text, "额定载流量")

        result = loop_closure_analysis(
            u1_kv_ll=_safe_float(self.loop_u1.get(), "U1"),
            u2_kv_ll=_safe_float(self.loop_u2.get(), "U2"),
            angle_deg=_safe_float(self.loop_angle.get(), "两侧相角差 φ"),
            r_loop_ohm=_safe_float(self.loop_r.get(), "回路电阻 RΣ"),
            x_loop_ohm=_safe_float(self.loop_x.get(), "回路电抗 XΣ"),
            frequency_hz=_safe_float(self.loop_freq.get(), "系统频率"),
            closure_node_index=closure,
            node_injections_A=node_currents,
            node_labels=node_labels,
            power_factor=_safe_float(self.loop_pf.get(), "统一功率因数 cosφ"),
            pf_mode=self.loop_pf_mode.get().strip() or "滞后",
            total_length_km=_safe_float(self.loop_total_len.get(), "总线路长度"),
            segment_ratios=ratios,
            ampacity_A=ampacity,
            overload_factor=_safe_float(self.loop_overload.get(), "短时过载系数 K"),
            close_time_s=_safe_float(self.loop_tclose.get(), "合环时刻"),
            t_end_s=_safe_float(self.loop_tend.get(), "波形结束时刻"),
            n_samples=2600,
        )
        return result

    def _plot_loop_closure_profile(self, result) -> None:
        ax = self.loop_profile_ax
        ax.clear()

        lengths = np.asarray(result.segment_lengths_km, dtype=float)
        if float(np.sum(lengths)) > 0.0:
            x = np.concatenate(([0.0], np.cumsum(lengths) / float(np.sum(lengths))))
        else:
            x = np.linspace(0.0, 1.0, len(result.node_labels) + 2)

        ax.plot(x, np.zeros_like(x), linewidth=2.0)
        ax.plot([x[0], x[-1]], [0, 0], "s", markersize=6)
        ax.text(x[0], 0.14, "左端", ha="center", fontsize=9)
        ax.text(x[-1], 0.14, "右端", ha="center", fontsize=9)

        closure_idx = result.closure_node_index
        for i, (label, inj) in enumerate(zip(result.node_labels, result.node_injections_A), start=1):
            xi = x[i]
            if i == closure_idx:
                ax.plot(xi, 0, marker="o", markersize=9, markerfacecolor="white", markeredgewidth=1.4)
                ax.text(xi, 0.24, f"{label}\n合环点", ha="center", fontsize=9)
            else:
                ax.plot(xi, 0, "o", markersize=4)
                ax.text(xi, 0.12, label, ha="center", fontsize=9)
                if abs(inj) > 1e-9:
                    y2 = -0.23 if inj >= 0 else 0.23
                    ax.annotate("", xy=(xi, y2), xytext=(xi, 0.0), arrowprops=dict(arrowstyle="->", linewidth=1.0))
                    va = "top" if inj >= 0 else "bottom"
                    ytxt = y2 - 0.03 if inj >= 0 else y2 + 0.03
                    ax.text(xi, ytxt, f"{inj:+.1f} A", ha="center", va=va, fontsize=8)

        for seg in result.segment_results:
            xm = (x[seg.index - 1] + x[seg.index]) / 2.0
            color = "#c00000" if result.overload_limit_A is not None and seg.post_magnitude_A > result.overload_limit_A + 1e-9 else "black"
            ax.text(xm, 0.30, f"{seg.post_magnitude_A:.1f}", ha="center", va="center", fontsize=8, color=color)
            ax.text(xm, -0.30, f"{seg.pre_magnitude_A:.1f}", ha="center", va="center", fontsize=8)

        ax.text(0.01, 0.96, "上：合环后稳态电流 A；下：合环前电流 A", transform=ax.transAxes, ha="left", va="top", fontsize=9)
        ax.text(0.99, 0.96, f"I_loop = {abs(result.steady_loop_current_A):.1f} A", transform=ax.transAxes, ha="right", va="top", fontsize=9)
        ax.set_title("配电网合环点位示意与各段电流")
        ax.set_xlim(-0.03, 1.03)
        ax.set_ylim(-0.45, 0.45)
        ax.axis("off")
        self.loop_profile_fig.tight_layout()
        self.loop_profile_canvas.draw()

    def _plot_loop_closure_waveforms(self, result) -> None:
        t = result.waveforms.t_s
        close_time = _safe_float(self.loop_tclose.get(), "合环时刻")

        ax1, ax2, ax3 = self.loop_wave_ax1, self.loop_wave_ax2, self.loop_wave_ax3
        for ax in (ax1, ax2, ax3):
            ax.clear()
            ax.axvline(close_time, linestyle=":", linewidth=1.0)
            ax.grid(True)
            ax.set_ylabel("i / A")

        ax1.plot(t, result.waveforms.loop_a_A, linewidth=1.2)
        ax1.set_title("合环环流（A 相瞬时值）")

        ax2.plot(t, result.waveforms.left_a_A, linewidth=1.0, label="A")
        ax2.plot(t, result.waveforms.left_b_A, linewidth=1.0, label="B")
        ax2.plot(t, result.waveforms.left_c_A, linewidth=1.0, label="C")
        ax2.set_title("左侧线路总电流（三相瞬时值）")
        ax2.legend(loc="upper right", ncol=3, fontsize=8)

        ax3.plot(t, result.waveforms.right_a_A, linewidth=1.0, label="A")
        ax3.plot(t, result.waveforms.right_b_A, linewidth=1.0, label="B")
        ax3.plot(t, result.waveforms.right_c_A, linewidth=1.0, label="C")
        ax3.set_title("右侧线路总电流（三相瞬时值）")
        ax3.legend(loc="upper right", ncol=3, fontsize=8)
        ax3.set_xlabel("t / s")

        self.loop_wave_fig.tight_layout()
        self.loop_wave_canvas.draw()

    def calculate_loop_closure(self) -> None:
        try:
            result = self._read_loop_closure_inputs()
            self._last_loop_result = result

            wf = result.waveforms
            loop_peak = float(np.max(np.abs(np.concatenate([wf.loop_a_A, wf.loop_b_A, wf.loop_c_A]))))
            left_peak = float(np.max(np.abs(np.concatenate([wf.left_a_A, wf.left_b_A, wf.left_c_A]))))
            right_peak = float(np.max(np.abs(np.concatenate([wf.right_a_A, wf.right_b_A, wf.right_c_A]))))

            overload_text = "未输入载流量上限。"
            if result.overload_limit_A is not None:
                overload_text = f"允许稳态载流上限 = {result.overload_limit_A:.2f} A"

            if result.overloaded_segments:
                conclusion = f"存在 {len(result.overloaded_segments)} 段超过稳态允许载流量。"
            else:
                conclusion = "按当前输入，上述各段稳态电流均未超过允许载流量。"

            text = (
                f"══ 配电网合环近似分析 ══════════════════════\n"
                f"连接点数量 N = {len(result.node_labels)}，合环点 = {result.node_labels[result.closure_node_index - 1]}（编号 {result.closure_node_index}）\n"
                f"U1 = {_safe_float(self.loop_u1.get(), 'U1'):.4g} kV，U2 = {_safe_float(self.loop_u2.get(), 'U2'):.4g} kV，φ = {_safe_float(self.loop_angle.get(), 'φ'):.4g}°\n"
                f"ΔU = {result.line_to_line_delta_kV:.4f} kV（合环点两侧线电压矢量差）\n"
                f"ZΣ = {result.loop_impedance_ohm.real:.4f} + j{result.loop_impedance_ohm.imag:.4f} Ω，|ZΣ| = {abs(result.loop_impedance_ohm):.4f} Ω，φz = {result.loop_impedance_angle_deg:.3f}°\n"
                f"I_loop = {_format_polar_complex(result.steady_loop_current_A, 'A')}\n"
                f"τ = {result.tau_s:.6f} s，2τ = {result.two_tau_s:.6f} s\n"
                f"左端合环前/后 = {abs(result.pre_left_source_A):.2f} / {abs(result.post_left_source_A):.2f} A\n"
                f"右端合环前/后 = {abs(result.pre_right_source_A):.2f} / {abs(result.post_right_source_A):.2f} A\n"
                f"瞬时峰值：环流 {loop_peak:.2f} A，左侧总电流 {left_peak:.2f} A，右侧总电流 {right_peak:.2f} A\n"
                f"{overload_text}\n"
                f"结论：{conclusion}\n"
                f"\n── 各段稳态电流 ───────────────────────────────\n"
                f"段号  区间                         长度/km    合环前/A    合环后/A    相角/°   状态\n"
                f"{'-' * 86}\n"
            )

            for seg in result.segment_results:
                interval = f"{seg.from_label}->{seg.to_label}"
                status = "超限" if result.overload_limit_A is not None and seg.post_magnitude_A > result.overload_limit_A + 1e-9 else "正常"
                text += (
                    f"{seg.index:>2d}    {interval:<26} {seg.length_km:>8.3f}  {seg.pre_magnitude_A:>10.2f}  "
                    f"{seg.post_magnitude_A:>10.2f}  {seg.post_angle_deg:>8.2f}  {status}\n"
                )

            text += "\n说明：\n" + result.notes
            self._set_text(self.loop_result, text)
            self._plot_loop_closure_profile(result)
            self._plot_loop_closure_waveforms(result)

        except Exception as exc:
            messagebox.showerror("计算错误", str(exc))

    def _build_comtrade_tab(self) -> None:
        self._comtrade_record = None
        self._comtrade_popup = None
        self._comtrade_popup_canvas = None
        self._comtrade_popup_fig = None
        self._sequence_channel_vars: dict[str, tk.StringVar] = {}
        self._sequence_result_text = None
        self._sequence_numeric_text = None
        self._sequence_numeric_table = None
        self._sequence_fig = None
        self._sequence_canvas = None
        self._sequence_axes = ()
        self._sequence_chart_notebook = None
        self._sequence_tab_defs = ()
        self._sequence_cache: dict[tuple[str, tuple[int, int, int], float], dict[str, np.ndarray]] = {}
        self._comtrade_overlay_mode = tk.StringVar(value="stacked")
        self._comtrade_default_window_s = 0.12
        self._comtrade_vertical_zoom = 1.0
        self._comtrade_visible_count = 6
        self._comtrade_channel_scroll = 0
        self._comtrade_cursor_positions: dict[str, float | None] = {"T1": None, "T2": None}
        self._comtrade_is_syncing_view = False
        self._comtrade_xlimit_callback_registered = False

        self.comtrade_tab.columnconfigure(1, weight=1)
        self.comtrade_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.comtrade_tab, padding=10)
        right = ttk.Frame(self.comtrade_tab, padding=10)
        left.grid(row=0, column=0, sticky="nsw")
        right.grid(row=0, column=1, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.columnconfigure(1, weight=1)
        left.columnconfigure(2, weight=1)
        left.columnconfigure(3, weight=1)
        left.rowconfigure(9, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        ttk.Label(left, text="录波曲线（COMTRADE / Yokogawa WVF/WDF）", font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        self.comtrade_path_var = tk.StringVar(value="")
        ttk.Entry(left, textvariable=self.comtrade_path_var, width=42).grid(row=2, column=0, columnspan=3, sticky="ew", padx=(0, 4), pady=2)
        ttk.Button(left, text="选择录波", command=self._browse_comtrade_cfg).grid(row=2, column=3, sticky="ew", pady=2)
        ttk.Button(left, text="加载录波", command=self._load_comtrade_file).grid(row=3, column=0, sticky="ew", pady=(4, 4), padx=(0, 4))
        ttk.Button(left, text="序量分析", command=self._open_sequence_analysis_window).grid(row=3, column=1, sticky="ew", pady=(4, 4), padx=(0, 4))
        ttk.Button(left, text="多通道同图", command=self._open_comtrade_overlay_window).grid(row=3, column=2, columnspan=2, sticky="ew", pady=(4, 4))

        ttk.Label(left, text="通道选择（Ctrl/Shift 多选）").grid(row=4, column=0, columnspan=4, sticky="w", pady=(4, 2))
        self.comtrade_channel_list = tk.Listbox(left, selectmode=tk.EXTENDED, width=42, height=12, exportselection=False)
        self.comtrade_channel_list.grid(row=5, column=0, columnspan=4, sticky="ew")
        self.comtrade_channel_list.bind("<<ListboxSelect>>", lambda _e: self._refresh_comtrade_plot())

        ttk.Label(left, text="起始时间 / s").grid(row=6, column=0, sticky="w", pady=(8, 2))
        self.comtrade_start_entry = ttk.Entry(left, width=12)
        self.comtrade_start_entry.grid(row=6, column=1, sticky="ew", pady=(8, 2), padx=(0, 4))
        ttk.Label(left, text="结束时间 / s").grid(row=6, column=2, sticky="w", pady=(8, 2))
        self.comtrade_end_entry = ttk.Entry(left, width=12)
        self.comtrade_end_entry.grid(row=6, column=3, sticky="ew", pady=(8, 2))

        ttk.Label(left, text="窗口宽度 / s").grid(row=7, column=0, sticky="w", pady=(6, 2))
        self.comtrade_window_entry = ttk.Entry(left, width=12)
        self.comtrade_window_entry.grid(row=7, column=1, sticky="ew", pady=(6, 2), padx=(0, 4))
        self.comtrade_window_entry.insert(0, "0.12")
        ttk.Button(left, text="应用时间窗", command=self._apply_comtrade_window).grid(row=7, column=2, sticky="ew", pady=(6, 2), padx=(0, 4))
        ttk.Button(left, text="恢复初始状态", command=self._reset_comtrade_view).grid(row=7, column=3, sticky="ew", pady=(6, 2))

        ttk.Label(left, text="基波频率 / Hz").grid(row=8, column=0, sticky="w", pady=(6, 2))
        self.comtrade_fund_entry = ttk.Entry(left, width=12)
        self.comtrade_fund_entry.grid(row=8, column=1, sticky="ew", pady=(6, 2), padx=(0, 4))
        self.comtrade_fund_entry.insert(0, "50")
        ttk.Button(left, text="分析选中通道", command=self._analyze_comtrade_selection).grid(row=8, column=2, sticky="ew", pady=(6, 2), padx=(0, 4))
        ttk.Button(left, text="全选通道", command=self._select_all_comtrade_channels).grid(row=8, column=3, sticky="ew", pady=(6, 2))

        self.comtrade_analysis_host = ttk.Frame(left)
        self.comtrade_analysis_host.grid(row=9, column=0, columnspan=4, sticky="nsew", pady=(8, 0))
        self.comtrade_analysis_host.columnconfigure(0, weight=1)
        self.comtrade_analysis_host.rowconfigure(0, weight=1)

        self.comtrade_overview_frame = ttk.Frame(self.comtrade_analysis_host)
        self.comtrade_overview_frame.grid(row=0, column=0, sticky="nsew")
        self.comtrade_overview_frame.columnconfigure(0, weight=1)
        self.comtrade_overview_frame.rowconfigure(0, weight=1)
        self.comtrade_info = ScrolledText(self.comtrade_overview_frame, width=54, height=24, wrap=tk.WORD, font="TkFixedFont")
        self.comtrade_info.grid(row=0, column=0, sticky="nsew")
        self.comtrade_info.configure(state="disabled")

        self.comtrade_sequence_frame = ttk.Frame(self.comtrade_analysis_host)
        self.comtrade_sequence_frame.columnconfigure(0, weight=1)
        self.comtrade_sequence_frame.rowconfigure(2, weight=1)
        self.comtrade_sequence_frame.rowconfigure(4, weight=1)
        self.comtrade_sequence_frame.grid(row=0, column=0, sticky="nsew")
        self.comtrade_sequence_frame.grid_remove()
        self._build_embedded_sequence_panel()

        ttk.Label(right, text="录波浏览区", font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.comtrade_time_label = ttk.Label(right, text="未加载文件")
        self.comtrade_time_label.grid(row=1, column=0, sticky="w", pady=(0, 2))
        self.comtrade_cursor_label = tk.Text(right, height=4, wrap=tk.WORD)
        self.comtrade_cursor_label.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        self.comtrade_cursor_label.insert("1.0", "光标：左键放置 T1，右键放置 T2。")
        self.comtrade_cursor_label.configure(state="disabled")

        self.comtrade_fig = Figure(figsize=(9.0, 6.2), dpi=100, facecolor="#101010")
        self.comtrade_ax = self.comtrade_fig.add_subplot(111)
        self._style_comtrade_axis(self.comtrade_ax)
        plot_host = ttk.Frame(right)
        plot_host.grid(row=3, column=0, sticky="nsew")
        plot_host.columnconfigure(0, weight=1)
        plot_host.rowconfigure(0, weight=1)
        self.comtrade_canvas = FigureCanvasTkAgg(self.comtrade_fig, master=plot_host)
        self.comtrade_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.comtrade_channel_scrollbar = tk.Scale(plot_host, from_=0, to=0, orient=tk.VERTICAL, showvalue=0, command=lambda _v: self._on_comtrade_vertical_scroll(), highlightthickness=0, length=480)
        self.comtrade_channel_scrollbar.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.comtrade_toolbar = NavigationToolbar2Tk(self.comtrade_canvas, right, pack_toolbar=False)
        self.comtrade_toolbar.update()
        self.comtrade_toolbar.grid(row=4, column=0, sticky="ew")

        slider_frame = ttk.Frame(right)
        slider_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        slider_frame.columnconfigure(0, weight=1)
        ttk.Label(slider_frame, text="时间拖动").grid(row=0, column=0, sticky="w")
        zoom_bar = ttk.Frame(slider_frame)
        zoom_bar.grid(row=0, column=1, sticky="e")
        ttk.Button(zoom_bar, text="纵向放大", command=lambda: self._zoom_comtrade_vertical(1.2)).pack(side="left", padx=(0, 4))
        ttk.Button(zoom_bar, text="纵向缩小", command=lambda: self._zoom_comtrade_vertical(1 / 1.2)).pack(side="left", padx=(0, 8))
        ttk.Button(zoom_bar, text="横向放大", command=lambda: self._zoom_comtrade_horizontal(1 / 1.25)).pack(side="left", padx=(0, 4))
        ttk.Button(zoom_bar, text="横向缩小", command=lambda: self._zoom_comtrade_horizontal(1.25)).pack(side="left")
        self.comtrade_scroll = tk.Scale(slider_frame, from_=0, to=1000, orient=tk.HORIZONTAL, showvalue=0, command=lambda _v: self._refresh_comtrade_plot(from_scroll=True), highlightthickness=0)
        self.comtrade_scroll.grid(row=1, column=0, columnspan=2, sticky="ew")

        self._set_text(self.comtrade_info, "未加载录波文件。")
        self.comtrade_ax.callbacks.connect("xlim_changed", self._on_comtrade_axis_xlim_changed)
        self.comtrade_canvas.mpl_connect("button_press_event", self._on_comtrade_mouse_click)
        self._comtrade_xlimit_callback_registered = True
        self.comtrade_canvas.draw()

    def _style_comtrade_axis(self, ax) -> None:
        ax.set_facecolor("#050505")
        ax.grid(True, color="#005f00", alpha=0.9, linewidth=0.7)
        ax.tick_params(colors="#d8d8d8")
        for spine in ax.spines.values():
            spine.set_color("#9a9a9a")
        ax.xaxis.label.set_color("#d8d8d8")
        ax.yaxis.label.set_color("#d8d8d8")
        ax.title.set_color("#f0f0f0")

    def _browse_comtrade_cfg(self) -> None:
        filename = filedialog.askopenfilename(
            title="选择录波文件",
            filetypes=[
                ("录波文件", "*.cfg *.wdf *.wvf *.hdr"),
                ("COMTRADE CFG", "*.cfg"),
                ("Yokogawa WDF", "*.wdf"),
                ("Yokogawa WVF", "*.wvf"),
                ("Yokogawa HDR", "*.hdr"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            self.comtrade_path_var.set(filename)

    def _default_comtrade_window(self, duration: float) -> float:
        if duration <= 0.0:
            return self._comtrade_default_window_s
        return min(max(duration * 0.1, 0.02), min(max(duration, 0.02), 0.20))

    def _set_comtrade_time_entries(self, start_s: float, end_s: float) -> None:
        self.comtrade_start_entry.delete(0, tk.END)
        self.comtrade_start_entry.insert(0, f"{start_s:.6g}")
        self.comtrade_end_entry.delete(0, tk.END)
        self.comtrade_end_entry.insert(0, f"{end_s:.6g}")
        self.comtrade_window_entry.delete(0, tk.END)
        self.comtrade_window_entry.insert(0, f"{max(0.0, end_s - start_s):.6g}")

    def _load_comtrade_file(self) -> None:
        try:
            cfg_path = self.comtrade_path_var.get().strip()
            if not cfg_path:
                raise InputError("请先选择录波文件。")
            self._comtrade_record = parse_waveform_file(cfg_path)
            self._populate_comtrade_channels()
            self._reset_comtrade_view()
            self._set_text(self.comtrade_info, self._format_comtrade_overview())
            self._refresh_sequence_analysis_window()
        except Exception as exc:
            messagebox.showerror("录波加载失败", str(exc))

    def _populate_comtrade_channels(self) -> None:
        record = self._comtrade_record
        self.comtrade_channel_list.delete(0, tk.END)
        if record is None:
            return
        for idx, ch in enumerate(record.analog_channels):
            self.comtrade_channel_list.insert(tk.END, f"{idx+1:02d} | {ch.name} | {ch.phase or '-'} | {ch.unit or '-'}")

    def _select_all_comtrade_channels(self) -> None:
        if self._comtrade_record is None:
            return
        self.comtrade_channel_list.selection_clear(0, tk.END)
        if self._comtrade_record.analog_channels:
            self.comtrade_channel_list.selection_set(0, tk.END)
        self._comtrade_channel_scroll = 0
        self._show_comtrade_overview_panel()
        self._refresh_comtrade_plot()

    def _reset_comtrade_view(self) -> None:
        record = self._comtrade_record
        if record is None:
            return
        self._select_all_comtrade_channels()
        self._comtrade_vertical_zoom = 1.0
        self._comtrade_channel_scroll = 0
        self._comtrade_cursor_positions = {"T1": None, "T2": None}
        default_window = self._default_comtrade_window(record.duration_s)
        self._set_comtrade_time_entries(float(record.time_s[0]), float(record.time_s[0]) + default_window)
        self._comtrade_is_syncing_view = True
        self.comtrade_scroll.set(0)
        self._comtrade_is_syncing_view = False
        self._refresh_comtrade_plot()

    def _format_comtrade_overview(self) -> str:
        record = self._comtrade_record
        if record is None:
            return "未加载录波文件。"
        sample_rate = estimate_sampling_rate(record)
        text = (
            f"══ 录波概览 ═══════════════════════\n"
            f"站名：{record.station_name or '-'}\n设备：{record.device_id or '-'}\n版本：{record.revision}\n"
            f"文件类型：{record.file_type}\n模拟量通道：{len(record.analog_channels)}\n数字量通道：{len(record.digital_channel_names)}\n"
            f"采样率：{sample_rate:.3f} Hz\n工频：{record.frequency_hz:.3f} Hz\n时长：{record.duration_s:.6f} s\n"
            f"文件：{record.cfg_path.name} / {record.dat_path.name}"
        )
        return text

    def _current_comtrade_window(self) -> tuple[float, float]:
        record = self._comtrade_record
        if record is None or record.time_s.size == 0:
            return 0.0, 0.0
        total = max(record.duration_s, 0.0)
        try:
            width = max(1e-4, _safe_float(self.comtrade_window_entry.get(), "窗口宽度"))
        except Exception:
            width = self._default_comtrade_window(total)
        width = min(width, max(total, width))
        if total <= width + 1e-12:
            return float(record.time_s[0]), float(record.time_s[-1])
        start = float(record.time_s[0]) + (float(self.comtrade_scroll.get()) / 1000.0) * (total - width)
        end = min(float(record.time_s[-1]), start + width)
        return start, end

    def _sample_for_plot(self, time_s: np.ndarray, values: np.ndarray, max_points: int = 12000) -> tuple[np.ndarray, np.ndarray]:
        if time_s.size <= max_points:
            return time_s, values
        step = max(1, int(np.ceil(time_s.size / max_points)))
        return time_s[::step], values[::step]

    def _current_visible_comtrade_indices(self, selection: list[int]) -> list[int]:
        if len(selection) <= self._comtrade_visible_count:
            return selection
        max_start = max(0, len(selection) - self._comtrade_visible_count)
        start = min(max(0, self._comtrade_channel_scroll), max_start)
        return selection[start:start + self._comtrade_visible_count]

    def _sync_comtrade_vertical_scrollbar(self, total_selected: int) -> None:
        max_start = max(0, total_selected - self._comtrade_visible_count)
        self.comtrade_channel_scrollbar.configure(from_=max_start, to=0 if max_start > 0 else 0)
        self.comtrade_channel_scroll = min(max(0, self._comtrade_channel_scroll), max_start)
        self.comtrade_channel_scrollbar.set(self.comtrade_channel_scroll)

    def _on_comtrade_vertical_scroll(self) -> None:
        try:
            self._comtrade_channel_scroll = int(round(float(self.comtrade_channel_scrollbar.get())))
        except Exception:
            self._comtrade_channel_scroll = 0
        self._refresh_comtrade_plot()

    def _nearest_comtrade_index(self, x_value: float) -> int | None:
        record = self._comtrade_record
        if record is None or record.time_s.size == 0:
            return None
        idx = int(np.clip(np.searchsorted(record.time_s, x_value), 0, record.time_s.size - 1))
        if idx > 0 and abs(record.time_s[idx - 1] - x_value) <= abs(record.time_s[idx] - x_value):
            idx -= 1
        return idx

    def _current_comtrade_cursor_index(self, key: str) -> int | None:
        record = self._comtrade_record
        frac = self._comtrade_cursor_positions.get(key)
        if record is None or frac is None:
            return None
        start_s, end_s = self._current_comtrade_window()
        x = start_s + frac * max(end_s - start_s, 0.0)
        return self._nearest_comtrade_index(x)

    def _current_comtrade_cursor_x(self, key: str) -> float | None:
        frac = self._comtrade_cursor_positions.get(key)
        if frac is None:
            return None
        start_s, end_s = self._current_comtrade_window()
        return start_s + frac * max(end_s - start_s, 0.0)

    def _update_comtrade_cursor_label(self) -> None:
        record = self._comtrade_record
        if record is None:
            self.comtrade_cursor_label.configure(state="normal")
            self.comtrade_cursor_label.delete("1.0", tk.END)
            self.comtrade_cursor_label.insert("1.0", "光标：左键放置 T1，右键放置 T2。")
            self.comtrade_cursor_label.configure(state="disabled")
            return
        selection = self._selected_comtrade_indices() if self._comtrade_record is not None else []
        lines = []
        for key in ("T1", "T2"):
            idx = self._current_comtrade_cursor_index(key)
            if idx is None:
                lines.append(f"{key}: 未设置")
                continue
            time_s = float(record.time_s[idx])
            value_parts = []
            for ch_idx in selection:
                ch = record.analog_channels[ch_idx]
                value_parts.append(f"{ch.name}={record.analog_values[idx, ch_idx]:.5g}{ch.unit or ''}")
            lines.append(f"{key}: t={time_s:.6f}s, 点号={idx + 1}")
            if value_parts:
                chunk = 4
                for pos in range(0, len(value_parts), chunk):
                    prefix = "    " if pos == 0 else "    ↳ "
                    lines.append(prefix + "；".join(value_parts[pos:pos + chunk]))
        idx1 = self._current_comtrade_cursor_index("T1")
        idx2 = self._current_comtrade_cursor_index("T2")
        if idx1 is not None and idx2 is not None:
            dt = float(record.time_s[idx2] - record.time_s[idx1])
            ds = idx2 - idx1
            lines.append(f"Δt = {dt:.6f} s，ΔN = {ds} 点")
        else:
            lines.append("提示：左键定位 T1，右键定位 T2；可用于故障前后对比和时间差测量。")
        self.comtrade_cursor_label.configure(state="normal")
        self.comtrade_cursor_label.delete("1.0", tk.END)
        self.comtrade_cursor_label.insert("1.0", "\n".join(lines))
        self.comtrade_cursor_label.configure(state="disabled")

    def _on_comtrade_mouse_click(self, event) -> None:
        if event.inaxes is not self.comtrade_ax or event.xdata is None:
            return
        x0, x1 = self.comtrade_ax.get_xlim()
        span = max(x1 - x0, 1e-12)
        frac = min(1.0, max(0.0, (float(event.xdata) - x0) / span))
        if event.button == 1:
            self._comtrade_cursor_positions["T1"] = frac
        elif event.button == 3:
            self._comtrade_cursor_positions["T2"] = frac
        else:
            return
        self._update_comtrade_cursor_label()
        self._refresh_comtrade_plot()
        self._refresh_sequence_analysis_window()

    def _zoom_comtrade_vertical(self, factor: float) -> None:
        self._comtrade_vertical_zoom = min(6.0, max(0.25, self._comtrade_vertical_zoom * factor))
        self._refresh_comtrade_plot()

    def _zoom_comtrade_horizontal(self, factor: float) -> None:
        record = self._comtrade_record
        if record is None:
            return
        start_s, end_s = self._current_comtrade_window()
        center = 0.5 * (start_s + end_s)
        total = max(record.duration_s, 1e-4)
        current_width = max(1e-4, end_s - start_s)
        new_width = min(total, max(1e-4, current_width * factor))
        data_min = float(record.time_s[0])
        data_max = float(record.time_s[-1])
        new_start = max(data_min, min(center - new_width / 2.0, data_max - new_width))
        if total <= new_width + 1e-12:
            slider = 0.0
        else:
            slider = (new_start - data_min) / max(total - new_width, 1e-12) * 1000.0
        self._comtrade_is_syncing_view = True
        self.comtrade_window_entry.delete(0, tk.END)
        self.comtrade_window_entry.insert(0, f"{new_width:.6g}")
        self.comtrade_scroll.set(max(0.0, min(1000.0, slider)))
        self._comtrade_is_syncing_view = False
        self._refresh_comtrade_plot()

    def _apply_comtrade_window(self) -> None:
        record = self._comtrade_record
        if record is None:
            return
        start_txt = self.comtrade_start_entry.get().strip()
        end_txt = self.comtrade_end_entry.get().strip()
        if start_txt and end_txt:
            start_s = max(float(record.time_s[0]), _safe_float(start_txt, "起始时间"))
            end_s = min(float(record.time_s[-1]), _safe_float(end_txt, "结束时间"))
            if end_s <= start_s:
                raise InputError("结束时间必须大于起始时间。")
            total = max(record.duration_s, 1e-12)
            width = end_s - start_s
            slider = 0.0 if total <= width + 1e-12 else (start_s - float(record.time_s[0])) / max(total - width, 1e-12) * 1000.0
            self._comtrade_is_syncing_view = True
            self.comtrade_window_entry.delete(0, tk.END)
            self.comtrade_window_entry.insert(0, f"{width:.6g}")
            self.comtrade_scroll.set(max(0.0, min(1000.0, slider)))
            self._comtrade_is_syncing_view = False
        self._refresh_comtrade_plot()

    def _on_comtrade_axis_xlim_changed(self, ax) -> None:
        record = self._comtrade_record
        if record is None or self._comtrade_is_syncing_view:
            return
        xmin, xmax = ax.get_xlim()
        data_min = float(record.time_s[0])
        data_max = float(record.time_s[-1])
        total = max(record.duration_s, 0.0)
        if not np.isfinite([xmin, xmax]).all() or total <= 0.0:
            return
        width = max(1e-4, min(abs(xmax - xmin), total))
        center = 0.5 * (xmin + xmax)
        start = max(data_min, min(center - width / 2.0, data_max - width))
        if abs(width - total) < 1e-12:
            slider = 0.0
        else:
            slider = (start - data_min) / max(total - width, 1e-12) * 1000.0
        slider = max(0.0, min(1000.0, slider))
        self._comtrade_is_syncing_view = True
        self.comtrade_window_entry.delete(0, tk.END)
        self.comtrade_window_entry.insert(0, f"{width:.6g}")
        self.comtrade_scroll.set(slider)
        self._comtrade_is_syncing_view = False
        self._set_comtrade_time_entries(start, start + width)
        self.comtrade_time_label.configure(text=f"当前时间窗：{start:.6f} s ~ {start + width:.6f} s")

    def _refresh_comtrade_plot(self, from_scroll: bool = False) -> None:
        record = self._comtrade_record
        ax = self.comtrade_ax
        ax.clear()
        self._style_comtrade_axis(ax)
        if record is None or record.analog_values.size == 0:
            ax.set_title("请先加载 COMTRADE 录波")
            ax.set_xlabel("t / s")
            self.comtrade_canvas.draw()
            return
        selection = list(self.comtrade_channel_list.curselection())
        if not selection:
            selection = list(range(record.analog_values.shape[1]))
        self._sync_comtrade_vertical_scrollbar(len(selection))
        visible_selection = self._current_visible_comtrade_indices(selection)
        start_s, end_s = self._current_comtrade_window()
        colors = ["#f5e663", "#00ff00", "#ff4040", "#e0e0e0", "#00ffff", "#ff7f00", "#adff2f", "#ff66cc", "#4db6ff", "#ffb3e6"]
        band_gap = 1.55
        base_offset = (len(visible_selection) - 1) * band_gap

        for pos, ch_idx in enumerate(visible_selection):
            raw_time, raw_values = self._sample_for_plot(record.time_s, record.analog_values[:, ch_idx])
            scale = float(np.max(np.abs(raw_values))) or 1.0
            offset = base_offset - pos * band_gap
            y_norm = raw_values / scale * (0.92 * self._comtrade_vertical_zoom) + offset
            color = colors[pos % len(colors)]
            ax.plot(raw_time, y_norm, color=color, linewidth=1.0)
            ax.axhline(offset + 0.98, color="#0c8f0c", linewidth=0.6, alpha=0.8)
            ax.axhline(offset - 0.98, color="#0c8f0c", linewidth=0.6, alpha=0.8)
            ax.text(0.01, offset + 1.05, record.analog_channels[ch_idx].name, transform=ax.get_yaxis_transform(), color=color, fontsize=9, ha="left", va="bottom")

        for key, color in (("T1", "#00ffff"), ("T2", "#ff7f00")):
            frac = self._comtrade_cursor_positions.get(key)
            if frac is None:
                continue
            draw_x = start_s + frac * max(end_s - start_s, 0.0)
            ax.axvline(draw_x, color=color, linewidth=1.1, linestyle="--")
            ax.text(draw_x, base_offset + 1.18, key, color=color, fontsize=9, ha="center", va="bottom", bbox=dict(facecolor="#101010", edgecolor=color, boxstyle="round,pad=0.2"))

        lower = -1.2
        upper = base_offset + 1.35
        ax.set_xlim(start_s, end_s)
        ax.set_ylim(lower, upper)
        ax.set_xlabel("t / s")
        ax.set_yticks([])
        ax.set_title("录波曲线浏览")
        shown_text = f"显示通道：{visible_selection[0] + 1}-{visible_selection[-1] + 1}" if visible_selection else "显示通道：无"
        self._set_comtrade_time_entries(start_s, end_s)
        self.comtrade_time_label.configure(text=f"当前时间窗：{start_s:.6f} s ~ {end_s:.6f} s，共 {len(record.time_s)} 点，{shown_text}")
        self._update_comtrade_cursor_label()
        self._comtrade_is_syncing_view = True
        self.comtrade_fig.subplots_adjust(left=0.06, right=0.98, top=0.93, bottom=0.10)
        self.comtrade_canvas.draw()
        self._comtrade_is_syncing_view = False
        self._refresh_sequence_analysis_window()
        if self._comtrade_popup is not None and self._comtrade_popup.winfo_exists() and not from_scroll:
            self._draw_comtrade_overlay()

    def _selected_comtrade_indices(self) -> list[int]:
        if self._comtrade_record is None:
            raise InputError("请先加载录波文件。")
        selection = list(self.comtrade_channel_list.curselection())
        if not selection:
            return list(range(len(self._comtrade_record.analog_channels)))
        return selection

    def _analyze_comtrade_selection(self) -> None:
        try:
            record = self._comtrade_record
            if record is None:
                raise InputError("请先加载录波文件。")
            selection = self._selected_comtrade_indices()
            start_s, end_s = self._current_comtrade_window()
            idx = self._slice_time_window(record.time_s, start_s, end_s)
            sample_rate = estimate_sampling_rate(record)
            fundamental = _safe_float(self.comtrade_fund_entry.get(), "基波频率")
            lines = [self._format_comtrade_overview(), "", f"══ 当前窗口分析（{start_s:.6f}s ~ {end_s:.6f}s）══"]
            primary = selection[0]
            ch = record.analog_channels[primary]
            summary = fourier_summary(record.analog_values[idx, primary], sample_rate, fundamental_hz=fundamental, max_order=10)
            lines.append(f"傅里叶分析通道：{ch.name} ({ch.unit or '-'})")
            lines.append(f"DC = {summary.dc:.6g}，THD = {summary.thd_percent:.3f}%")
            lines.append("阶次   频率/Hz   幅值(pk)    RMS       相角/°")
            lines.append("-" * 48)
            for item in summary.harmonics[:8]:
                lines.append(f"{item.order:>2d}   {item.frequency_hz:>8.3f}   {item.amplitude:>9.5g}   {item.rms:>8.5g}   {item.phase_deg:>8.2f}")
            try:
                prony = prony_like_summary(record.analog_values[idx, primary], sample_rate)
                lines.append("")
                lines.append(f"Prony 类估计：主振荡频率 {prony.dominant_frequency_hz:.4f} Hz，阻尼比 {prony.damping_ratio_percent:.3f}%，时间常数 {prony.decay_time_constant_s:.5g} s")
            except Exception as exc:
                lines.append(f"Prony 类估计：{exc}")
            if len(selection) >= 3:
                a, b, c = selection[:3]
                seq = sequence_components(record.analog_values[idx, a], record.analog_values[idx, b], record.analog_values[idx, c])
                lines.append("")
                lines.append(f"序分量（按前三个选中通道 RMS 估计）：正序={seq.positive:.5g}，负序={seq.negative:.5g}，零序={seq.zero:.5g}，不平衡度={seq.unbalance_percent:.3f}%")
            else:
                lines.append("")
                lines.append("序分量提取：请选择至少 3 个相量/电流同类通道。")
            self._set_text(self.comtrade_info, "\n".join(lines))
        except Exception as exc:
            messagebox.showerror("录波分析失败", str(exc))

    def _build_embedded_sequence_panel(self) -> None:
        top = ttk.Frame(self.comtrade_sequence_frame)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)
        self._sequence_channel_vars = {key: tk.StringVar(value="未设置") for key in ["Ua", "Ub", "Uc", "Ia", "Ib", "Ic"]}
        self._sequence_comboboxes: list[ttk.Combobox] = []

        for box_idx, (title, prefix) in enumerate((("三相电压通道", "U"), ("三相电流通道", "I"))):
            lf = ttk.LabelFrame(top, text=title, padding=4)
            lf.grid(row=0, column=box_idx, sticky="nsew", padx=(0, 6) if box_idx == 0 else 0)
            for ridx, phase in enumerate(("a", "b", "c")):
                show_key = f"{prefix}{phase}"
                ttk.Label(lf, text=show_key).grid(row=ridx, column=0, sticky="w", padx=2, pady=2)
                cmb = ttk.Combobox(lf, textvariable=self._sequence_channel_vars[show_key], values=["未设置"], state="readonly", width=24)
                cmb.grid(row=ridx, column=1, sticky="ew", padx=2, pady=2)
                cmb.bind("<<ComboboxSelected>>", lambda _e: self._refresh_sequence_analysis_window())
                self._sequence_comboboxes.append(cmb)
            lf.columnconfigure(1, weight=1)

        btn_row = ttk.Frame(self.comtrade_sequence_frame)
        btn_row.grid(row=1, column=0, sticky="ew", pady=(6, 4))
        ttk.Button(btn_row, text="应用配置", command=self._refresh_sequence_analysis_window).pack(side="left")
        ttk.Button(btn_row, text="返回概览", command=self._show_comtrade_overview_panel).pack(side="left", padx=(6, 0))

        self._sequence_result_text = ScrolledText(self.comtrade_sequence_frame, width=54, height=12, wrap=tk.WORD, font="TkFixedFont")
        self._sequence_result_text.grid(row=2, column=0, sticky="nsew")
        self._sequence_result_text.configure(state="disabled")

        chart_nb = ttk.Notebook(self.comtrade_sequence_frame)
        chart_nb.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        self._sequence_tab_defs = (
            ("电压相量", "voltage_phase"),
            ("电流相量", "current_phase"),
            ("V 序分量", "voltage_seq"),
            ("I 序分量", "current_seq"),
        )
        for tab_text, key in self._sequence_tab_defs:
            frame = ttk.Frame(chart_nb)
            chart_nb.add(frame, text=tab_text)
        chart_host = ttk.Frame(self.comtrade_sequence_frame)
        chart_host.grid(row=4, column=0, sticky="nsew")
        chart_host.columnconfigure(0, weight=0)
        chart_host.columnconfigure(1, weight=1)
        chart_host.rowconfigure(0, weight=1)

        table_frame = ttk.Frame(chart_host)
        table_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 8))
        columns = ("name", "mag", "ang", "real", "imag")
        table = ttk.Treeview(table_frame, columns=columns, show="headings", height=7)
        headers = {"name": "名称", "mag": "幅值", "ang": "相角/°", "real": "实部", "imag": "虚部"}
        widths = {"name": 64, "mag": 90, "ang": 90, "real": 88, "imag": 88}
        for key in columns:
            table.heading(key, text=headers[key])
            table.column(key, width=widths[key], anchor="center", stretch=False)
        table.grid(row=0, column=0, sticky="nsew")
        unit_label = ttk.Label(table_frame, text="单位：-", foreground="#555555")
        unit_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._sequence_numeric_table = table
        self._sequence_numeric_text = unit_label

        plot_frame = ttk.Frame(chart_host)
        plot_frame.grid(row=0, column=1, sticky="nsew")
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)
        self._sequence_fig = Figure(figsize=(4.8, 4.8), dpi=100, facecolor="#101418")
        ax_seq = self._sequence_fig.add_subplot(111, projection="polar")
        self._sequence_axes = (ax_seq,)
        self._sequence_canvas = FigureCanvasTkAgg(self._sequence_fig, master=plot_frame)
        self._sequence_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self._sequence_chart_notebook = chart_nb
        self._sequence_chart_notebook.bind("<<NotebookTabChanged>>", lambda _e: self._refresh_sequence_analysis_window())

    def _show_comtrade_overview_panel(self) -> None:
        self.comtrade_sequence_frame.grid_remove()
        self.comtrade_overview_frame.grid()

    def _show_comtrade_sequence_panel(self) -> None:
        options = self._sequence_channel_options()
        for cmb in self._sequence_comboboxes:
            cmb.configure(values=options)
        self.comtrade_overview_frame.grid_remove()
        self.comtrade_sequence_frame.grid()
        self._refresh_sequence_analysis_window()

    def _sequence_channel_options(self) -> list[str]:
        record = self._comtrade_record
        options = ["未设置"]
        if record is None:
            return options
        for idx, ch in enumerate(record.analog_channels):
            options.append(f"{idx}:{ch.name} [{ch.phase or '-'}] {ch.unit or ''}".strip())
        return options

    def _parse_sequence_channel_selection(self, value: str) -> int | None:
        value = value.strip()
        if not value or value == "未设置":
            return None
        return int(value.split(":", 1)[0])

    def _open_sequence_analysis_window(self) -> None:
        self._show_comtrade_sequence_panel()

    def _read_sequence_group(self, labels: tuple[str, str, str]) -> tuple[int, int, int] | None:
        indices = [self._parse_sequence_channel_selection(self._sequence_channel_vars[key].get()) for key in labels]
        return tuple(indices) if all(idx is not None for idx in indices) else None

    def _format_sequence_complex(self, value: complex, unit: str) -> str:
        mag = abs(value)
        ang = math.degrees(math.atan2(value.imag, value.real))
        return f"{mag:.5g} ∠ {ang:+.2f}° {unit}"

    def _build_sequence_cache(self, group_key: str, indices: tuple[int, int, int], sample_rate: float, fundamental: float) -> dict[str, np.ndarray]:
        cache_key = (group_key, indices, round(fundamental, 6))
        if cache_key in self._sequence_cache:
            return self._sequence_cache[cache_key]
        record = self._comtrade_record
        if record is None:
            raise InputError("未加载录波文件。")
        n = max(8, int(round(sample_rate / max(fundamental, 1e-9))))
        basis = np.exp(-1j * 2.0 * np.pi * fundamental * np.arange(n, dtype=float) / sample_rate)[::-1]
        scale = 2.0 / n / math.sqrt(2.0)

        def _phasor_track(signal: np.ndarray) -> np.ndarray:
            return np.convolve(np.asarray(signal, dtype=float), basis, mode="same") * scale

        pa = _phasor_track(record.analog_values[:, indices[0]])
        pb = _phasor_track(record.analog_values[:, indices[1]])
        pc = _phasor_track(record.analog_values[:, indices[2]])
        alpha = complex(-0.5, math.sqrt(3.0) / 2.0)
        zero = (pa + pb + pc) / 3.0
        positive = (pa + alpha * pb + (alpha ** 2) * pc) / 3.0
        negative = (pa + (alpha ** 2) * pb + alpha * pc) / 3.0
        result = {
            "a": pa,
            "b": pb,
            "c": pc,
            "zero": zero,
            "positive": positive,
            "negative": negative,
        }
        self._sequence_cache[cache_key] = result
        return result

    def _draw_sequence_phasor_axis(self, ax, vectors: dict[str, complex], title: str) -> None:
        ax.clear()
        ax.set_theta_zero_location("E")
        ax.set_theta_direction(1)
        ax.set_facecolor("#11161d")
        colors = {
            "Ua": "#7ec8ff", "Ub": "#ffe082", "Uc": "#ff8a80",
            "Ia": "#4dd0e1", "Ib": "#ffd54f", "Ic": "#ffab91",
            "V0": "#b388ff", "V1": "#66bb6a", "V2": "#42a5f5",
            "I0": "#f06292", "I1": "#26c6da", "I2": "#ffb74d",
        }
        max_mag = max(1.0, max(abs(v) for v in vectors.values())) if vectors else 1.0
        radial_max = max_mag * 1.15
        rings = np.linspace(radial_max / 4.0, radial_max, 4)
        ax.set_ylim(0.0, radial_max)
        ax.set_yticks(rings)
        ax.set_yticklabels([f"{tick:.3g}" for tick in rings], color="#aeb8c2", fontsize=8)
        ax.set_rlabel_position(22.5)
        ax.set_thetagrids(
            np.arange(0, 360, 45),
            labels=["0°", "45°", "90°", "135°", "180°", "-135°", "-90°", "-45°"],
            fontsize=8,
            color="#8ea1b4",
        )
        ax.grid(color="#5f6f7e", linestyle="-", linewidth=0.8, alpha=0.45)
        ax.spines["polar"].set_color("#7c8794")
        ax.spines["polar"].set_linewidth(1.0)
        for name, val in vectors.items():
            theta = math.atan2(val.imag, val.real)
            radius = abs(val)
            color = colors.get(name, "#ffffff")
            ax.annotate(
                "",
                xy=(theta, radius),
                xytext=(theta, 0.0),
                arrowprops=dict(arrowstyle="-|>", color=color, linewidth=2.2, linestyle="-", shrinkA=0, shrinkB=0),
            )
        ax.set_title("")

    def _active_sequence_tab_key(self) -> str:
        notebook = getattr(self, "_sequence_chart_notebook", None)
        tab_defs = getattr(self, "_sequence_tab_defs", ())
        if notebook is None or not tab_defs:
            return "voltage_phase"
        current = notebook.index(notebook.select())
        return tab_defs[current][1]

    def _update_sequence_numeric_table(self, vectors: dict[str, complex], unit: str) -> None:
        if self._sequence_numeric_table is None or self._sequence_numeric_text is None:
            return
        for item in self._sequence_numeric_table.get_children():
            self._sequence_numeric_table.delete(item)
        for name, value in vectors.items():
            mag = abs(value)
            ang = math.degrees(math.atan2(value.imag, value.real))
            self._sequence_numeric_table.insert(
                "",
                tk.END,
                values=(name, f"{mag:.5g}", f"{ang:.2f}", f"{value.real:.5g}", f"{value.imag:.5g}"),
            )
        self._sequence_numeric_text.configure(text=f"单位：{unit or '-'}")

    def _refresh_sequence_analysis_window(self) -> None:
        if self._sequence_result_text is None or self._sequence_fig is None or self._sequence_canvas is None or self._sequence_numeric_text is None:
            return
        record = self._comtrade_record
        if record is None:
            self._set_text(self._sequence_result_text, "未加载录波文件。")
            self._update_sequence_numeric_table({}, "-")
            for ax in self._sequence_axes:
                ax.clear()
            self._sequence_canvas.draw()
            return
        t1 = self._current_comtrade_cursor_index("T1")
        if t1 is None:
            self._set_text(self._sequence_result_text, "请先在主窗口左键设置 T1 光标，再进行序量分析。")
            self._update_sequence_numeric_table({}, "-")
            for ax in self._sequence_axes:
                ax.clear()
                ax.set_title("等待 T1 光标")
            self._sequence_canvas.draw()
            return
        sample_rate = estimate_sampling_rate(record)
        fundamental = _safe_float(self.comtrade_fund_entry.get(), "基波频率")
        lines = [f"T1 点号 = {t1 + 1}", f"T1 时间 = {record.time_s[t1]:.6f} s", ""]
        voltage_group = self._read_sequence_group(("Ua", "Ub", "Uc"))
        current_group = self._read_sequence_group(("Ia", "Ib", "Ic"))
        tab_vectors = {"voltage_phase": {}, "current_phase": {}, "voltage_seq": {}, "current_seq": {}}
        titles = {
            "voltage_phase": "电压相量",
            "current_phase": "电流相量",
            "voltage_seq": "V 序分量",
            "current_seq": "I 序分量",
        }
        tab_units = {"voltage_phase": "", "current_phase": "", "voltage_seq": "", "current_seq": ""}
        if voltage_group is not None:
            vcache = self._build_sequence_cache("V", voltage_group, sample_rate, fundamental)
            tab_vectors["voltage_phase"] = {
                "Ua": complex(vcache["a"][t1]),
                "Ub": complex(vcache["b"][t1]),
                "Uc": complex(vcache["c"][t1]),
            }
            tab_vectors["voltage_seq"] = {
                "V0": complex(vcache["zero"][t1]),
                "V1": complex(vcache["positive"][t1]),
                "V2": complex(vcache["negative"][t1]),
            }
            unit = record.analog_channels[voltage_group[0]].unit or "pu"
            tab_units["voltage_phase"] = unit
            tab_units["voltage_seq"] = unit
            lines.append("【电压序分量】")
            lines.append(f"V0: {self._format_sequence_complex(tab_vectors['voltage_seq']['V0'], unit)}")
            lines.append(f"V1: {self._format_sequence_complex(tab_vectors['voltage_seq']['V1'], unit)}")
            lines.append(f"V2: {self._format_sequence_complex(tab_vectors['voltage_seq']['V2'], unit)}")
            lines.append("")
        if current_group is not None:
            icache = self._build_sequence_cache("I", current_group, sample_rate, fundamental)
            tab_vectors["current_phase"] = {
                "Ia": complex(icache["a"][t1]),
                "Ib": complex(icache["b"][t1]),
                "Ic": complex(icache["c"][t1]),
            }
            tab_vectors["current_seq"] = {
                "I0": complex(icache["zero"][t1]),
                "I1": complex(icache["positive"][t1]),
                "I2": complex(icache["negative"][t1]),
            }
            unit = record.analog_channels[current_group[0]].unit or "A"
            tab_units["current_phase"] = unit
            tab_units["current_seq"] = unit
            lines.append("【电流序分量】")
            lines.append(f"I0: {self._format_sequence_complex(tab_vectors['current_seq']['I0'], unit)}")
            lines.append(f"I1: {self._format_sequence_complex(tab_vectors['current_seq']['I1'], unit)}")
            lines.append(f"I2: {self._format_sequence_complex(tab_vectors['current_seq']['I2'], unit)}")
        if not any(tab_vectors.values()):
            self._set_text(self._sequence_result_text, "请在序量分析窗口中至少完整设置一组三相电压或三相电流通道。")
            self._update_sequence_numeric_table({}, "-")
            ax = self._sequence_axes[0]
            ax.clear()
            ax.set_title(f"{titles[self._active_sequence_tab_key()]}\n（未配置）", color="#f5f7fa", pad=16, fontsize=11)
            self._sequence_canvas.draw()
            return
        active_key = self._active_sequence_tab_key()
        ax = self._sequence_axes[0]
        if tab_vectors[active_key]:
            self._draw_sequence_phasor_axis(ax, tab_vectors[active_key], titles[active_key])
            self._update_sequence_numeric_table(tab_vectors[active_key], tab_units[active_key] or "-")
        else:
            ax.clear()
            ax.set_title(f"{titles[active_key]}\n（未配置）", color="#f5f7fa", pad=16, fontsize=11)
            self._update_sequence_numeric_table({}, "-")
        self._set_text(self._sequence_result_text, "\n".join(lines).strip())
        self._sequence_fig.subplots_adjust(left=0.03, right=0.97, top=0.97, bottom=0.03)
        self._sequence_canvas.draw()

    def _toggle_comtrade_overlay_mode(self) -> None:
        self._comtrade_overlay_mode.set("overlay" if self._comtrade_overlay_mode.get() == "stacked" else "stacked")
        self._draw_comtrade_overlay()

    def _open_comtrade_overlay_window(self) -> None:
        try:
            self._selected_comtrade_indices()
        except Exception as exc:
            messagebox.showwarning("无法绘图", str(exc))
            return
        if self._comtrade_popup is not None and self._comtrade_popup.winfo_exists():
            self._comtrade_popup.deiconify()
            self._comtrade_popup.lift()
            self._draw_comtrade_overlay()
            return
        win = tk.Toplevel(self)
        self._comtrade_popup = win
        win.geometry("1220x840")
        win.rowconfigure(1, weight=1)
        win.columnconfigure(0, weight=1)

        tool = ttk.Frame(win, padding=6)
        tool.grid(row=0, column=0, sticky="ew")
        ttk.Label(tool, text="显示风格").pack(side="left")
        ttk.Label(tool, textvariable=self._comtrade_overlay_mode).pack(side="left", padx=(6, 12))
        ttk.Button(tool, text="一键切换风格", command=self._toggle_comtrade_overlay_mode).pack(side="left")

        frame = ttk.Frame(win, padding=6)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self._comtrade_popup_fig = Figure(figsize=(10.8, 7.4), dpi=100)
        self._comtrade_popup_canvas = FigureCanvasTkAgg(self._comtrade_popup_fig, master=frame)
        self._comtrade_popup_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        toolbar = NavigationToolbar2Tk(self._comtrade_popup_canvas, frame, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="ew")
        self._draw_comtrade_overlay()

    def _draw_comtrade_overlay(self) -> None:
        record = self._comtrade_record
        if record is None or self._comtrade_popup_fig is None or self._comtrade_popup_canvas is None:
            return
        selection = self._selected_comtrade_indices()
        start_s, end_s = self._current_comtrade_window()
        idx = self._slice_time_window(record.time_s, start_s, end_s)
        t = record.time_s[idx]
        mode = self._comtrade_overlay_mode.get()
        self._comtrade_popup_fig.clear()
        colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b", "#e377c2"]

        if mode == "overlay":
            ax = self._comtrade_popup_fig.add_subplot(111)
            legend_labels = []
            for pos, ch_idx in enumerate(selection):
                ch = record.analog_channels[ch_idx]
                y = record.analog_values[idx, ch_idx]
                ax.plot(t, y, linewidth=1.2, color=colors[pos % len(colors)], label=ch.name)
                legend_labels.append(ch.name)
            ax.grid(True, linestyle="--", alpha=0.35)
            ax.set_title("多通道同图 / MATLAB 单轴叠加风格")
            ax.set_xlabel("t / s")
            ax.set_ylabel("幅值")
            ax.legend(loc="upper right", fontsize=8, frameon=True, title="通道 / 线形")
            self._comtrade_popup.title("录波曲线 - 多通道同图（MATLAB 单轴叠加风格）")
        else:
            axes = []
            for pos, ch_idx in enumerate(selection, start=1):
                axes.append(self._comtrade_popup_fig.add_subplot(len(selection), 1, pos, sharex=axes[0] if axes else None))
            for ax, ch_idx, color in zip(axes, selection, colors * 10):
                ch = record.analog_channels[ch_idx]
                ax.plot(t, record.analog_values[idx, ch_idx], linewidth=1.1, color=color, label=ch.name)
                ax.grid(True, linestyle='--', alpha=0.35)
                ax.legend(loc='upper right', fontsize=8)
                ax.set_ylabel(ch.unit or '值')
            axes[0].set_title('多通道同图 / MATLAB 学术论文风格（分轴堆叠）')
            axes[-1].set_xlabel('t / s')
            self._comtrade_popup.title("录波曲线 - 多通道同图（MATLAB 学术风格）")

        self._comtrade_popup_fig.tight_layout()
        self._comtrade_popup_canvas.draw()


def main() -> None:
    app = ApproximationToolGUI()
    app.mainloop()


__all__ = ["ApproximationToolGUI", "main", "_detect_key_conclusion_lines", "_notebook_style_spec"]
