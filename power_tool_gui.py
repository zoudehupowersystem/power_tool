"""Tkinter GUI application entrypoint.

The large GUI is split into focused mixin modules while this file keeps the
public ``ApproximationToolGUI`` import path stable. / GUI 已拆分为若干专用
mixin 模块，本文件保留外部稳定入口。
"""

from __future__ import annotations

from power_tool_gui_common import *
from power_tool_gui_common import CommonGuiMixin
from power_tool_gui_comtrade import ComtradeGuiMixin
from power_tool_gui_dynamics import DynamicsGuiMixin
from power_tool_gui_forecast import ForecastGuiMixin
from power_tool_gui_loop import LoopClosureGuiMixin
from power_tool_gui_network_params import NetworkAndParameterGuiMixin


class ApproximationToolGUI(
    CommonGuiMixin,
    DynamicsGuiMixin,
    NetworkAndParameterGuiMixin,
    LoopClosureGuiMixin,
    ForecastGuiMixin,
    ComtradeGuiMixin,
    tk.Tk,
):
    def __init__(self, language: str = "zh") -> None:
        super().__init__()
        self.language = normalize_language(language)
        set_active_language(self.language)
        if self.language == "en":
            install_runtime_hooks()
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
        self.load_forecast_tab = ttk.Frame(notebook)
        self.renewable_forecast_tab = ttk.Frame(notebook)
        self.annual_load_forecast_tab = ttk.Frame(notebook)
        self.comtrade_tab = ttk.Frame(notebook)

        notebook.add(self.comtrade_tab, text="录波曲线")
        notebook.add(self.freq_tab, text="频率动态")
        notebook.add(self.osc_tab, text="机电振荡")
        notebook.add(self.volt_tab, text="电压无功分析")
        notebook.add(self.impact_tab, text="暂稳评估")
        notebook.add(self.smib_tab, text="小扰动分析")
        notebook.add(self.loop_tab, text="配电网合环分析")
        notebook.add(self.param_tab, text="参数校核与标幺值")
        notebook.add(self.sc_tab, text="短路电流计算")
        notebook.add(self.load_forecast_tab, text="日前负荷预测")
        notebook.add(self.renewable_forecast_tab, text="新能源预测")
        notebook.add(self.annual_load_forecast_tab, text="年度负荷预测")

        self._line_geometry_window: tk.Toplevel | None = None
        self._line_geometry_entries: dict[str, ttk.Entry] = {}
        self._line_geometry_ground_widgets: list[tk.Widget] = []
        self._line_geometry_has_gw_var: tk.BooleanVar | None = None
        self._line_geometry_bundle_var: tk.StringVar | None = None
        self._line_geometry_result: ScrolledText | None = None
        self._line_geometry_last_result = None
        self._line_geometry_notebook = None
        self._line_geometry_fig = None
        self._line_geometry_canvas = None
        self._line_geometry_ax = None
        self._cable_geometry_entries: dict[str, ttk.Entry] = {}
        self._cable_geometry_arrangement_var: tk.StringVar | None = None
        self._cable_geometry_sheath_var: tk.BooleanVar | None = None
        self._cable_geometry_bonding_var: tk.StringVar | None = None
        self._cable_geometry_return_var: tk.StringVar | None = None
        self._cable_geometry_return_override_var: tk.BooleanVar | None = None
        self._cable_geometry_return_widgets: list[tk.Widget] = []
        self._cable_geometry_sheath_widgets: list[tk.Widget] = []

        self._build_frequency_tab()
        self._build_oscillation_tab()
        self._build_voltage_tab()
        self._build_impact_tab()
        self._build_smib_tab()
        self._build_loop_closure_tab()
        self._build_param_tab()
        self._build_short_circuit_tab()
        self._forecast_widgets: dict[str, dict[str, object]] = {}
        self._build_load_forecast_tab()
        self._build_renewable_forecast_tab()
        self._annual_forecast_widgets: dict[str, object] = {}
        self._build_annual_load_forecast_tab()
        self._build_comtrade_tab()
        self._build_ai_sidebar()
        self._hide_tab_muted_explanations()
        self._apply_global_aesthetics()
        self._apply_language()
        self.main_notebook.bind("<<NotebookTabChanged>>", self._on_ai_context_changed)



def _wrap_english_refresh(method_name: str) -> None:
    """Wrap selected GUI update methods so English text variables are re-translated after dynamic updates. / 包装部分 GUI 更新方法，确保英文界面在动态更新后再次翻译文本变量。"""
    original = getattr(ApproximationToolGUI, method_name)

    def wrapped(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if getattr(self, "language", "zh") == "en":
            try:
                self._apply_language()
            except Exception:
                pass
        return result

    setattr(ApproximationToolGUI, method_name, wrapped)


for _method_name in (
    "calculate_frequency",
    "calculate_oscillation",
    "calculate_voltage",
    "calculate_line",
    "calculate_avc_strategy",
    "calculate_impact",
    "calculate_eac",
    "calculate_smib",
    "calculate_type1_avr_pss",
    "calculate_loop_closure",
    "calculate_short_circuit",
    "open_line_geometry_calculator",
    "calculate_line_geometry_popup",
    "_refresh_comtrade_plot",
    "_refresh_sequence_analysis_window",
):
    _wrap_english_refresh(_method_name)


def main(language: str = "zh") -> None:
    app = ApproximationToolGUI(language=language)
    app.mainloop()


__all__ = ["ApproximationToolGUI", "main", "_detect_key_conclusion_lines", "_manual_filename", "_notebook_style_spec"]
