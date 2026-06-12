"""Forecast GUI mixin for PowerTool. / PowerTool 预测功能 GUI mixin。

This module holds the day-ahead load, renewable, solar-helper, and annual-load
forecasting pages.  It is intentionally separate from ``power_tool_gui.py`` so
the main window remains responsible for application assembly while forecast UI
changes stay localized.
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from power_tool_common import InputError, _safe_float
from power_tool_i18n import logic_text, translate_text
from power_tool_forecast import (
    AnnualLoadForecastConfig,
    ForecastConfig,
    annual_seasonal_shapes_for_year,
    builtin_dataset_info,
    classify_climate_block,
    export_annual_load_forecast_csv,
    export_annual_load_forecast_json,
    export_forecast_result_csv,
    export_forecast_result_json,
    forecast_algorithm_label,
    forecast_annual_load,
    forecast_day_ahead,
    format_annual_load_forecast_summary,
    format_forecast_summary,
    list_builtin_datasets,
    list_forecast_algorithms,
    load_annual_load_sample,
    load_builtin_forecast_dataset,
    load_forecast_builtin_config,
    load_forecast_csv,
    load_future_weather_csv,
    solar_day_profile,
    solar_irradiance_on_panel,
    solar_position,
    NANJING_ALTITUDE_M,
    NANJING_LATITUDE,
    NANJING_LONGITUDE,
)


def _format_utc_offset(hours: int) -> str:
    sign = "+" if hours >= 0 else "-"
    return f"UTC{sign}{abs(hours):02d}:00"


def _format_clock(dt: datetime | None) -> str:
    return "--" if dt is None else f"{dt:%H:%M}"


def _format_decimal_hours(hours: float) -> str:
    h = int(math.floor(hours))
    m = int(round((hours - h) * 60.0))
    if m >= 60:
        h += 1
        m -= 60
    return f"{h:02d}:{m:02d}"


def _weather_label_to_code(label: str) -> str:
    value = str(label).strip()
    mapping = {
        "晴空": "clear",
        "少云": "partly_cloudy",
        "多云": "cloudy",
        "阴天": "overcast",
        "雨雪": "rain_snow",
        "雾霾": "haze",
        "Clear sky": "clear",
        "Clear": "clear",
        "Partly cloudy": "partly_cloudy",
        "Cloudy": "cloudy",
        "Overcast": "overcast",
        "Rain / snow": "rain_snow",
        "Rain/Snow": "rain_snow",
        "Haze": "haze",
        "clear": "clear",
        "partly_cloudy": "partly_cloudy",
        "cloudy": "cloudy",
        "overcast": "overcast",
        "rain_snow": "rain_snow",
        "haze": "haze",
    }
    return mapping.get(value, mapping.get(value.lower(), value or "clear"))


class ForecastGuiMixin:
    def _build_annual_load_forecast_tab(self) -> None:
        dataset = load_annual_load_sample()
        defaults = dataset.get("default_inputs", {}) if isinstance(dataset.get("default_inputs", {}), dict) else {}
        tab = self.annual_load_forecast_tab
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)
        left = ttk.Frame(tab, padding=16, style="Card.TFrame")
        right = ttk.Frame(tab, padding=16, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 6), pady=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=8)
        left.columnconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(3, weight=1)

        ttk.Label(left, text="年度负荷预测", style="PageTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            left,
            text="面向电网规划的 5–20 年年度电量、最大负荷与分季节典型负荷形态预测；不包含空间负荷预测。",
            style="Muted.TLabel", justify="left", wraplength=420,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 10))

        region = str(dataset.get("region", "规划区域"))
        source = str(dataset.get("source", "内置年度负荷规划样例"))
        lat_entry = self._add_entry(left, 2, "纬度 / °", f"{float(dataset.get('latitude', NANJING_LATITUDE)):.4f}", width=16)
        lon_entry = self._add_entry(left, 3, "经度 / °", f"{float(dataset.get('longitude', NANJING_LONGITUDE)):.4f}", width=16)
        climate_var = tk.StringVar(value=str(dataset.get("climate_block", "")))
        ttk.Label(left, text="气候板块", style="Form.TLabel").grid(row=4, column=0, sticky="w", padx=4, pady=4)
        climate_entry = ttk.Entry(left, textvariable=climate_var, width=26, style="Input.TEntry")
        climate_entry.grid(row=4, column=1, sticky="ew", padx=4, pady=4)
        horizon_entry = self._add_entry(left, 5, "预测年限（5-20）", str(defaults.get("horizon_years", 10)), width=16)
        algorithm_var = tk.StringVar(value="综合法")
        ttk.Label(left, text="预测方法", style="Form.TLabel").grid(row=6, column=0, sticky="w", padx=4, pady=4)
        algorithm_box = ttk.Combobox(left, textvariable=algorithm_var, values=["综合法", "趋势外推法", "弹性系数法"], state="readonly", width=18, style="Input.TCombobox")
        algorithm_box.grid(row=6, column=1, sticky="ew", padx=4, pady=4)
        gdp_entry = self._add_entry(left, 7, "GDP 年增长 / %", str(defaults.get("gdp_growth_pct", 5.0)), width=16)
        pop_entry = self._add_entry(left, 8, "人口年增长 / %", str(defaults.get("population_growth_pct", 1.0)), width=16)
        primary_entry = self._add_entry(left, 9, "第一产业增长 / %", str(defaults.get("primary_growth_pct", 2.0)), width=16)
        secondary_entry = self._add_entry(left, 10, "第二产业增长 / %", str(defaults.get("secondary_growth_pct", 4.0)), width=16)
        tertiary_entry = self._add_entry(left, 11, "第三产业增长 / %", str(defaults.get("tertiary_growth_pct", 6.0)), width=16)
        coincidence_entry = self._add_entry(left, 12, "负荷同时率", str(defaults.get("coincidence_factor", 0.92)), width=16)
        dual_carbon_entry = self._add_entry(left, 13, "双碳政策修正 / %", str(defaults.get("dual_carbon_factor_pct", -0.8)), width=16)
        electrification_entry = self._add_entry(left, 14, "再电气化修正 / %", str(defaults.get("electrification_factor_pct", 1.6)), width=16)
        annual_button_row = ttk.Frame(left, style="Card.TFrame")
        annual_button_row.grid(row=15, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        for col in range(3):
            annual_button_row.columnconfigure(col, weight=1)
        ttk.Button(annual_button_row, text="年度预测", style="Accent.TButton", command=self._run_annual_load_forecast).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(annual_button_row, text="导出JSON", command=lambda: self._export_annual_load_forecast_result("json")).grid(row=0, column=1, sticky="ew", padx=(4, 4))
        ttk.Button(annual_button_row, text="导出CSV", command=lambda: self._export_annual_load_forecast_result("csv")).grid(row=0, column=2, sticky="ew", padx=(4, 0))
        ttk.Label(left, text=f"数据集：{region}\n{source}", style="Card.TLabel", justify="left", wraplength=420).grid(row=16, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        ttk.Label(right, text="年度负荷预测结果", style="PageTitle.TLabel").grid(row=0, column=0, sticky="w")
        result_text = ScrolledText(right, width=94, height=12, wrap=tk.NONE, font="TkFixedFont")
        result_text.grid(row=1, column=0, sticky="nsew", pady=(6, 8))
        self._style_text_widget(result_text)
        result_text.insert("1.0", "请填写规划输入后点击“年度预测”。")
        result_text.configure(state="disabled")

        view_book = ttk.Notebook(right)
        view_book.grid(row=3, column=0, sticky="nsew")
        curve_tab = ttk.Frame(view_book, style="Card.TFrame")
        shape_tab = ttk.Frame(view_book, style="Card.TFrame")
        view_book.add(curve_tab, text="年度趋势")
        view_book.add(shape_tab, text="分季节典型形态")
        for child in (curve_tab, shape_tab):
            child.columnconfigure(0, weight=1)
            child.rowconfigure(1, weight=1)

        fig = Figure(figsize=(8.8, 5.4), dpi=100)
        ax_energy = fig.add_subplot(211)
        ax_peak = fig.add_subplot(212, sharex=ax_energy)
        canvas = FigureCanvasTkAgg(fig, master=curve_tab)
        toolbar = NavigationToolbar2Tk(canvas, curve_tab, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=0, column=0, sticky="ew")
        canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        shape_fig = Figure(figsize=(8.8, 3.8), dpi=100)
        shape_ax = shape_fig.add_subplot(111)
        shape_canvas = FigureCanvasTkAgg(shape_fig, master=shape_tab)
        shape_toolbar = NavigationToolbar2Tk(shape_canvas, shape_tab, pack_toolbar=False)
        shape_toolbar.update()
        shape_toolbar.grid(row=0, column=0, sticky="ew")
        shape_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        shape_control = ttk.Frame(shape_tab, style="Card.TFrame")
        shape_control.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        shape_control.columnconfigure(1, weight=1)
        shape_year_var = tk.StringVar(value="典型形态年份：预测后可拖动选择")
        ttk.Label(shape_control, textvariable=shape_year_var, style="Form.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
        shape_year_slider = ttk.Scale(shape_control, from_=0, to=1, orient="horizontal", command=self._on_annual_shape_year_slider)
        shape_year_slider.grid(row=0, column=1, sticky="ew", padx=(0, 0), pady=2)
        canvas.draw()
        shape_canvas.draw()

        self._annual_forecast_widgets = {
            "region": region,
            "dataset": dataset,
            "lat_entry": lat_entry,
            "lon_entry": lon_entry,
            "climate_var": climate_var,
            "horizon_entry": horizon_entry,
            "algorithm_var": algorithm_var,
            "gdp_entry": gdp_entry,
            "pop_entry": pop_entry,
            "primary_entry": primary_entry,
            "secondary_entry": secondary_entry,
            "tertiary_entry": tertiary_entry,
            "coincidence_entry": coincidence_entry,
            "dual_carbon_entry": dual_carbon_entry,
            "electrification_entry": electrification_entry,
            "result_text": result_text,
            "fig": fig,
            "ax_energy": ax_energy,
            "ax_peak": ax_peak,
            "canvas": canvas,
            "shape_fig": shape_fig,
            "shape_ax": shape_ax,
            "shape_canvas": shape_canvas,
            "shape_year_var": shape_year_var,
            "shape_year_slider": shape_year_slider,
            "shape_slider_updating": False,
            "shape_lines": {},
            "shape_ylim": None,
            "last_result": None,
        }

    def _run_annual_load_forecast(self) -> None:
        widgets = self._annual_forecast_widgets
        try:
            config = AnnualLoadForecastConfig(
                horizon_years=int(_safe_float(widgets["horizon_entry"].get(), "预测年限")),  # type: ignore[index,union-attr]
                latitude=_safe_float(widgets["lat_entry"].get(), "纬度"),  # type: ignore[index,union-attr]
                longitude=_safe_float(widgets["lon_entry"].get(), "经度"),  # type: ignore[index,union-attr]
                climate_block=logic_text(str(widgets["climate_var"].get()).strip(), getattr(self, "language", "zh")),  # type: ignore[index,union-attr]
                algorithm=logic_text(str(widgets["algorithm_var"].get()), getattr(self, "language", "zh")),  # type: ignore[index,union-attr]
                gdp_growth_pct=_safe_float(widgets["gdp_entry"].get(), "GDP 年增长"),  # type: ignore[index,union-attr]
                population_growth_pct=_safe_float(widgets["pop_entry"].get(), "人口年增长"),  # type: ignore[index,union-attr]
                primary_growth_pct=_safe_float(widgets["primary_entry"].get(), "第一产业增长"),  # type: ignore[index,union-attr]
                secondary_growth_pct=_safe_float(widgets["secondary_entry"].get(), "第二产业增长"),  # type: ignore[index,union-attr]
                tertiary_growth_pct=_safe_float(widgets["tertiary_entry"].get(), "第三产业增长"),  # type: ignore[index,union-attr]
                coincidence_factor=_safe_float(widgets["coincidence_entry"].get(), "负荷同时率"),  # type: ignore[index,union-attr]
                dual_carbon_factor_pct=_safe_float(widgets["dual_carbon_entry"].get(), "双碳政策修正"),  # type: ignore[index,union-attr]
                electrification_factor_pct=_safe_float(widgets["electrification_entry"].get(), "再电气化修正"),  # type: ignore[index,union-attr]
            )
            result = forecast_annual_load(widgets["dataset"], config)  # type: ignore[arg-type]
            widgets["last_result"] = result
            self._set_text(widgets["result_text"], translate_text(format_annual_load_forecast_summary(result), getattr(self, "language", "zh")))  # type: ignore[arg-type]
            self._plot_annual_load_forecast(result)
        except Exception as exc:
            messagebox.showerror("年度负荷预测错误", str(exc))

    def _export_annual_load_forecast_result(self, fmt: str) -> None:
        widgets = self._annual_forecast_widgets
        result = widgets.get("last_result")
        if result is None:
            messagebox.showinfo("尚无结果", "请先执行年度预测，再导出结果。")
            return
        suffix = ".json" if fmt == "json" else ".csv"
        filename = filedialog.asksaveasfilename(
            title="导出年度负荷预测结果",
            defaultextension=suffix,
            filetypes=[("JSON", "*.json")] if fmt == "json" else [("CSV", "*.csv")],
            initialfile=f"annual_load_forecast_{datetime.now():%Y%m%d_%H%M%S}{suffix}",
        )
        if not filename:
            return
        try:
            if fmt == "json":
                export_annual_load_forecast_json(result, filename)
            else:
                export_annual_load_forecast_csv(result, filename)
            messagebox.showinfo("导出完成", f"年度负荷预测结果已导出：{filename}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def _plot_annual_load_forecast(self, result) -> None:
        widgets = self._annual_forecast_widgets
        years = [row.year for row in result.years]
        energy = [row.energy_gwh for row in result.years]
        peak = [row.max_load_mw for row in result.years]
        ax_energy = widgets["ax_energy"]
        ax_peak = widgets["ax_peak"]
        ax_energy.clear()
        ax_peak.clear()
        ax_energy.plot(years, energy, marker="o", color="#1f77b4", label="用电量/GWh")
        ax_energy.fill_between(years, [row.p10_energy_gwh for row in result.years], [row.p90_energy_gwh for row in result.years], color="#1f77b4", alpha=0.12)
        ax_energy.set_title("年度用电量预测")
        ax_energy.set_xlabel("Year")
        ax_energy.set_ylabel("GWh", color="#1f77b4")
        ax_energy.grid(True, alpha=0.3)
        ax_energy.legend(loc="upper left")

        ax_peak.plot(years, peak, marker="s", color="#d62728", label="最大负荷/MW")
        ax_peak.fill_between(years, [row.p10_max_load_mw for row in result.years], [row.p90_max_load_mw for row in result.years], color="#d62728", alpha=0.10)
        ax_peak.set_title("年度最大负荷预测")
        ax_peak.set_xlabel("Year")
        ax_peak.set_ylabel("MW", color="#d62728")
        ax_peak.grid(True, alpha=0.3)
        ax_peak.legend(loc="upper left")
        widgets["fig"].tight_layout()
        widgets["canvas"].draw()

        base_year = int(result.base_year)
        final_year = int(result.years[-1].year)
        slider = widgets["shape_year_slider"]
        widgets["shape_slider_updating"] = True
        slider.configure(from_=base_year, to=final_year)
        slider.set(base_year)
        widgets["shape_slider_updating"] = False
        self._update_annual_shape_plot(base_year, reset_lines=True)

    def _on_annual_shape_year_slider(self, value: str) -> None:
        widgets = self._annual_forecast_widgets
        if widgets.get("shape_slider_updating"):
            return
        result = widgets.get("last_result")
        if result is None:
            return
        try:
            selected_year = int(round(float(value)))
        except (TypeError, ValueError):
            return
        self._update_annual_shape_plot(selected_year, reset_lines=False)

    def _update_annual_shape_plot(self, selected_year: int, reset_lines: bool = False) -> None:
        widgets = self._annual_forecast_widgets
        result = widgets.get("last_result")
        if result is None:
            return
        base_year = int(result.base_year)
        final_year = int(result.years[-1].year)
        selected_year = max(base_year, min(final_year, int(selected_year)))
        widgets["shape_year_var"].set(translate_text(f"典型形态年份：{selected_year}（{base_year}–{final_year}）", getattr(self, "language", "zh")))
        shapes = annual_seasonal_shapes_for_year(result, selected_year)
        shape_ax = widgets["shape_ax"]
        hours = list(range(24))
        lines = widgets.get("shape_lines") or {}
        if reset_lines or not lines:
            shape_ax.clear()
            lines = {}
            for shape in shapes:
                (line,) = shape_ax.plot(hours, shape.values_mw, marker="o", linewidth=1.8, label=shape.season)
                lines[shape.season] = line
            shape_ax.set_xlabel("Hour")
            shape_ax.set_ylabel("MW")
            shape_ax.set_xticks(range(0, 24, 2))
            shape_ax.grid(True, alpha=0.3)
            shape_ax.legend(loc="best")
            lower_shapes = annual_seasonal_shapes_for_year(result, base_year)
            upper_shapes = annual_seasonal_shapes_for_year(result, final_year)
            all_values = [value for shape in (*lower_shapes, *upper_shapes) for value in shape.values_mw]
            if all_values:
                ymin = min(all_values) * 0.94
                ymax = max(all_values) * 1.06
                widgets["shape_ylim"] = (ymin, ymax)
                shape_ax.set_ylim(ymin, ymax)
            widgets["shape_lines"] = lines
        else:
            for shape in shapes:
                line = lines.get(shape.season)
                if line is not None:
                    line.set_ydata(shape.values_mw)
        if widgets.get("shape_ylim") is not None:
            shape_ax.set_ylim(*widgets["shape_ylim"])
        shape_ax.set_title(f"{selected_year} 年分季节典型负荷形态")
        widgets["shape_fig"].tight_layout()
        widgets["shape_canvas"].draw_idle()

    def _build_load_forecast_tab(self) -> None:
        self._build_day_ahead_forecast_tab(self.load_forecast_tab, "load")

    def _build_renewable_forecast_tab(self) -> None:
        self._build_day_ahead_forecast_tab(self.renewable_forecast_tab, "renewable")

    def _build_day_ahead_forecast_tab(self, tab: ttk.Frame, kind: str) -> None:
        title = "负荷日前预测" if kind == "load" else "新能源日前预测"
        target_label = "预测负荷 / MW" if kind == "load" else "预测新能源出力 / MW"
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)
        left = ttk.Frame(tab, padding=16, style="Card.TFrame")
        right = ttk.Frame(tab, padding=16, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 6), pady=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=8)
        left.columnconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(3, weight=1)

        ttk.Label(left, text=title, style="PageTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            left,
            text="面向调度员的日前预测：内置 JSON 已配置算法库、地区模板、节假日和特殊事件；支持 24 点/96 点输出、人工选择算法和综合方案。",
            style="Muted.TLabel", justify="left", wraplength=420,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 10))

        dataset_names = [info.name for info in list_builtin_datasets(kind)]
        dataset_var = tk.StringVar(value=dataset_names[0] if dataset_names else "")
        custom_path_var = tk.StringVar(value="")
        future_weather_path_var = tk.StringVar(value="")
        date_var = tk.StringVar(value="2025-06-22")
        lat_entry = self._add_entry(left, 3, "纬度 / °", f"{NANJING_LATITUDE:.4f}", width=16)
        lon_entry = self._add_entry(left, 4, "经度 / °", f"{NANJING_LONGITUDE:.4f}", width=16)
        alt_entry = self._add_entry(left, 5, "海拔 / m（平原可填 0）", f"{NANJING_ALTITUDE_M:.0f}", width=16)
        date_entry = ttk.Entry(left, textvariable=date_var, width=16, style="Input.TEntry")
        ttk.Label(left, text="预测日期（YYYY-MM-DD）", style="Form.TLabel").grid(row=6, column=0, sticky="w", padx=4, pady=4)
        date_entry.grid(row=6, column=1, sticky="ew", padx=4, pady=4)
        holiday_var = tk.StringVar(value="CN")
        ttk.Label(left, text="节假日国家/地区", style="Form.TLabel").grid(row=7, column=0, sticky="w", padx=4, pady=4)
        holiday_box = ttk.Combobox(left, textvariable=holiday_var, values=["US", "CN"], state="readonly", width=18, style="Input.TCombobox")
        holiday_box.grid(row=7, column=1, sticky="ew", padx=4, pady=4)
        next_row = 8

        interval_var = tk.StringVar(value="15")
        ttk.Label(left, text="时段间隔 / min（1-30）", style="Form.TLabel").grid(row=next_row, column=0, sticky="w", padx=4, pady=4)
        interval_box = ttk.Combobox(left, textvariable=interval_var, values=["1", "5", "10", "15", "30"], state="normal", width=18, style="Input.TCombobox")
        interval_box.grid(row=next_row, column=1, sticky="ew", padx=4, pady=4)
        next_row += 1

        algorithm_infos = list_forecast_algorithms(kind)
        algorithm_labels = [f"{info.label} ({info.code})" for info in algorithm_infos]
        algorithm_by_label = {f"{info.label} ({info.code})": info.code for info in algorithm_infos}
        forecast_defaults = load_forecast_builtin_config().get("defaults", {})
        default_alg = str(forecast_defaults.get("algorithm", "adaptive_ensemble")) if isinstance(forecast_defaults, dict) else "adaptive_ensemble"
        default_alg_label = next((label for label in algorithm_labels if label.endswith(f"({default_alg})")), algorithm_labels[0] if algorithm_labels else default_alg)
        algorithm_var = tk.StringVar(value=default_alg_label)
        ttk.Label(left, text="预测算法", style="Form.TLabel").grid(row=next_row, column=0, sticky="w", padx=4, pady=4)
        algorithm_box = ttk.Combobox(left, textvariable=algorithm_var, values=algorithm_labels, state="readonly", width=26, style="Input.TCombobox")
        algorithm_box.grid(row=next_row, column=1, sticky="ew", padx=4, pady=4)
        next_row += 1

        capacity_entry = None
        resource_var = tk.StringVar(value="solar")
        solar_time_var = tk.StringVar(value="12:00")
        weather_var = tk.StringVar(value="晴空")
        cloud_entry = None
        irr_adjust_entry = None
        tilt_entry = None
        pv_azimuth_entry = None
        albedo_entry = None
        temp_coeff_entry = None
        if kind == "renewable":
            capacity_entry = self._add_entry(left, next_row, "装机容量上限 / MW", "23000", width=16)
            next_row += 1
            ttk.Label(left, text="新能源类型", style="Form.TLabel").grid(row=next_row, column=0, sticky="w", padx=4, pady=4)
            resource_box = ttk.Combobox(left, textvariable=resource_var, values=["solar", "wind"], state="readonly", width=18, style="Input.TCombobox")
            resource_box.grid(row=next_row, column=1, sticky="ew", padx=4, pady=4)
            next_row += 1
            ttk.Label(left, text="天气场景", style="Form.TLabel").grid(row=next_row, column=0, sticky="w", padx=4, pady=4)
            weather_box = ttk.Combobox(left, textvariable=weather_var, values=["晴空", "少云", "多云", "阴天", "雨雪", "雾霾"], state="readonly", width=18, style="Input.TCombobox")
            weather_box.grid(row=next_row, column=1, sticky="ew", padx=4, pady=4)
            next_row += 1
            cloud_entry = self._add_entry(left, next_row, "云量 / %", "0", width=16)
            next_row += 1
            irr_adjust_entry = self._add_entry(left, next_row, "辐照人工系数", "1.00", width=16)
            next_row += 1
            tilt_entry = self._add_entry(left, next_row, "组件倾角 / °", "30", width=16)
            next_row += 1
            pv_azimuth_entry = self._add_entry(left, next_row, "组件方位角 / °", "180", width=16)
            next_row += 1
            albedo_entry = self._add_entry(left, next_row, "地表反照率", "0.20", width=16)
            next_row += 1
            temp_coeff_entry = self._add_entry(left, next_row, "组件温度系数 %/℃", "-0.35", width=16)
            next_row += 1

        ttk.Label(left, text="训练数据集", style="Form.TLabel").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        dataset_box = ttk.Combobox(left, textvariable=dataset_var, values=dataset_names, state="readonly", width=26, style="Input.TCombobox")
        dataset_box.grid(row=2, column=1, sticky="ew", padx=4, pady=4)
        button_row = ttk.Frame(left, style="Card.TFrame")
        button_row.grid(row=next_row, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        for col in range(5):
            button_row.columnconfigure(col, weight=1)
        ttk.Button(button_row, text="导入训练CSV", command=lambda: self._import_forecast_csv(kind)).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(button_row, text="导入未来天气CSV", command=lambda: self._import_future_weather_csv(kind)).grid(row=0, column=1, sticky="ew", padx=(3, 3))
        ttk.Button(button_row, text="预测", style="Accent.TButton", command=lambda: self._run_day_ahead_forecast(kind)).grid(row=0, column=2, sticky="ew", padx=(3, 3))
        ttk.Button(button_row, text="导出JSON", command=lambda: self._export_forecast_result(kind, "json")).grid(row=0, column=3, sticky="ew", padx=(3, 3))
        ttk.Button(button_row, text="导出CSV", command=lambda: self._export_forecast_result(kind, "csv")).grid(row=0, column=4, sticky="ew", padx=(3, 0))

        info_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=info_var, style="Card.TLabel", justify="left", wraplength=420).grid(row=next_row + 1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        ttk.Label(right, text=f"{title}结果", style="PageTitle.TLabel").grid(row=0, column=0, sticky="w")
        result_text = ScrolledText(right, width=94, height=14, wrap=tk.NONE, font="TkFixedFont")
        result_text.grid(row=1, column=0, sticky="nsew", pady=(6, 8))
        self._style_text_widget(result_text)
        result_text.insert("1.0", "请选择数据集、算法和时段间隔，然后点击“预测”。")
        result_text.configure(state="disabled")

        view_book = ttk.Notebook(right)
        view_book.grid(row=3, column=0, sticky="nsew")
        curve_tab = ttk.Frame(view_book, style="Card.TFrame")
        table_tab = ttk.Frame(view_book, style="Card.TFrame")
        metric_tab = ttk.Frame(view_book, style="Card.TFrame")
        solar_tab = None
        view_book.add(curve_tab, text="曲线")
        view_book.add(table_tab, text="24/96点明细")
        view_book.add(metric_tab, text="算法与日特性")
        if kind == "renewable":
            solar_tab = ttk.Frame(view_book, style="Card.TFrame")
            view_book.add(solar_tab, text="太阳角度/轨迹")
        curve_tab.columnconfigure(0, weight=1)
        curve_tab.rowconfigure(1, weight=1)
        table_tab.columnconfigure(0, weight=1)
        table_tab.rowconfigure(0, weight=1)
        metric_tab.columnconfigure(0, weight=1)
        metric_tab.rowconfigure(0, weight=1)
        if solar_tab is not None:
            solar_tab.columnconfigure(0, weight=1)
            solar_tab.rowconfigure(1, weight=1)

        fig = Figure(figsize=(8.8, 3.8), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_title(target_label)
        ax.set_xlabel("Hour")
        ax.set_ylabel("MW")
        ax.grid(True)
        canvas = FigureCanvasTkAgg(fig, master=curve_tab)
        toolbar = NavigationToolbar2Tk(canvas, curve_tab, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=0, column=0, sticky="ew")
        canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        canvas.draw()

        if kind == "renewable":
            detail_columns = ("time", "p10", "value", "p90", "temp", "ghi", "poa", "sun_alt", "sun_az", "incidence", "weather", "pv_factor", "wind", "drivers")
        else:
            detail_columns = ("time", "p10", "value", "p90", "temp", "ghi", "wind", "drivers")
        detail_tree = ttk.Treeview(table_tab, columns=detail_columns, show="headings", height=14)
        detail_headers = {
            "time": "时间", "p10": "P10/MW", "value": "预测/MW", "p90": "P90/MW", "temp": "温度℃", "ghi": "GHI",
            "poa": "POA", "sun_alt": "太阳高°", "sun_az": "方位°", "incidence": "入射°", "weather": "天气系数", "pv_factor": "PV修正",
            "wind": "风速", "drivers": "调度提示"
        }
        detail_widths = {"time": 145, "p10": 80, "value": 90, "p90": 80, "temp": 70, "ghi": 70, "poa": 70, "sun_alt": 78, "sun_az": 70, "incidence": 70, "weather": 80, "pv_factor": 70, "wind": 70, "drivers": 520}
        for col in detail_columns:
            detail_tree.heading(col, text=detail_headers[col])
            detail_tree.column(col, width=detail_widths[col], anchor="w" if col in {"time", "drivers"} else "e")
        detail_tree.grid(row=0, column=0, sticky="nsew")
        detail_scroll_y = ttk.Scrollbar(table_tab, orient="vertical", command=detail_tree.yview)
        detail_scroll_x = ttk.Scrollbar(table_tab, orient="horizontal", command=detail_tree.xview)
        detail_tree.configure(yscrollcommand=detail_scroll_y.set, xscrollcommand=detail_scroll_x.set)
        detail_scroll_y.grid(row=0, column=1, sticky="ns")
        detail_scroll_x.grid(row=1, column=0, sticky="ew")

        metric_text = ScrolledText(metric_tab, width=86, height=12, wrap=tk.NONE, font="TkFixedFont")
        metric_text.grid(row=0, column=0, sticky="nsew")
        self._style_text_widget(metric_text)
        metric_text.insert("1.0", "预测完成后显示算法权重、留出校验误差、峰谷差、负荷率/容量因子等信息。")
        metric_text.configure(state="disabled")

        solar_result_text = None
        solar_fig = None
        solar_canvas = None
        solar_axes = None
        solar_time_slider = None
        solar_time_note_var = None
        solar_time_entry = None
        if solar_tab is not None:
            solar_tab.rowconfigure(0, weight=0)
            solar_tab.rowconfigure(1, weight=0)
            solar_tab.rowconfigure(2, weight=1)
            solar_tab.rowconfigure(3, weight=0)
            solar_result_text = ScrolledText(solar_tab, width=94, height=6, wrap=tk.WORD, font="TkFixedFont")
            solar_result_text.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
            self._style_text_widget(solar_result_text)
            solar_result_text.insert("1.0", "太阳角度、天气修正 GHI 与组件 POA 将自动联动到新能源预测。可在下方拖拽日照区间滑条，或直接在右侧曲线区拖拽当前时刻。")
            solar_result_text.configure(state="disabled")

            solar_fig = Figure(figsize=(9.4, 5.0), dpi=100)
            solar_ax_polar = solar_fig.add_subplot(121, projection="polar")
            solar_ax_curve = solar_fig.add_subplot(122)
            solar_canvas = FigureCanvasTkAgg(solar_fig, master=solar_tab)
            solar_toolbar = NavigationToolbar2Tk(solar_canvas, solar_tab, pack_toolbar=False)
            solar_toolbar.update()
            solar_toolbar.grid(row=1, column=0, sticky="ew")
            solar_canvas.get_tk_widget().grid(row=2, column=0, sticky="nsew")
            solar_axes = (solar_ax_polar, solar_ax_curve)

            solar_control = ttk.Frame(solar_tab, style="Card.TFrame")
            solar_control.grid(row=3, column=0, sticky="ew", pady=(6, 0))
            solar_control.columnconfigure(2, weight=1)
            ttk.Label(solar_control, text="分析时刻", style="Form.TLabel").grid(row=0, column=0, sticky="e", padx=(0, 4), pady=2)
            solar_time_entry = ttk.Entry(solar_control, textvariable=solar_time_var, width=8, style="Input.TEntry")
            solar_time_entry.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=2)
            solar_time_slider = ttk.Scale(solar_control, from_=0, to=1440, orient="horizontal", command=self._on_solar_time_slider)
            solar_time_slider.grid(row=0, column=2, sticky="ew", padx=(0, 8), pady=2)
            ttk.Button(solar_control, text="刷新太阳图", command=self._run_renewable_solar_helper).grid(row=0, column=3, sticky="e", padx=(0, 0), pady=2)
            solar_time_note_var = tk.StringVar(value="日照区间生成后，可拖拽滑条；也可在太阳高度曲线区域拖拽选择当前时刻。")
            ttk.Label(solar_control, textvariable=solar_time_note_var, style="Muted.TLabel", justify="right").grid(row=1, column=0, columnspan=4, sticky="e", pady=(0, 2))

            solar_canvas.mpl_connect("button_press_event", self._on_solar_plot_button_press)
            solar_canvas.mpl_connect("motion_notify_event", self._on_solar_plot_motion)
            solar_canvas.mpl_connect("button_release_event", self._on_solar_plot_button_release)
            solar_canvas.draw()

        self._forecast_widgets[kind] = {
            "dataset_var": dataset_var,
            "custom_path_var": custom_path_var,
            "future_weather_path_var": future_weather_path_var,
            "date_var": date_var,
            "lat_entry": lat_entry,
            "lon_entry": lon_entry,
            "alt_entry": alt_entry,
            "holiday_var": holiday_var,
            "capacity_entry": capacity_entry,
            "resource_var": resource_var,
            "solar_time_var": solar_time_var,
            "weather_var": weather_var,
            "cloud_entry": cloud_entry,
            "irr_adjust_entry": irr_adjust_entry,
            "tilt_entry": tilt_entry,
            "pv_azimuth_entry": pv_azimuth_entry,
            "albedo_entry": albedo_entry,
            "temp_coeff_entry": temp_coeff_entry,
            "interval_var": interval_var,
            "algorithm_var": algorithm_var,
            "algorithm_by_label": algorithm_by_label,
            "info_var": info_var,
            "result_text": result_text,
            "metric_text": metric_text,
            "detail_tree": detail_tree,
            "fig": fig,
            "ax": ax,
            "canvas": canvas,
            "solar_result_text": solar_result_text,
            "solar_fig": solar_fig,
            "solar_canvas": solar_canvas,
            "solar_axes": solar_axes,
            "solar_time_entry": solar_time_entry,
            "solar_time_slider": solar_time_slider,
            "solar_time_note_var": solar_time_note_var,
            "solar_slider_updating": False,
            "solar_slider_after_id": None,
            "solar_plot_dragging": False,
            "solar_curve_axes": (),
            "solar_time_bounds_min": (0.0, 1440.0),
            "info_base_text": "",
            "last_result": None,
            "last_solar_profile": None,
        }
        dataset_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_forecast_dataset_defaults(kind))
        algorithm_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_forecast_algorithm_hint(kind))
        self._apply_forecast_dataset_defaults(kind, update_location=False)
        self._apply_forecast_algorithm_hint(kind)
        if kind == "renewable":
            self._run_renewable_solar_helper(silent=True)

    def _apply_forecast_dataset_defaults(self, kind: str, update_location: bool = True) -> None:
        widgets = self._forecast_widgets.get(kind)
        if not widgets:
            return
        dataset_name = widgets["dataset_var"].get()  # type: ignore[union-attr]
        if not dataset_name or str(dataset_name).startswith("CSV:"):
            return
        info = builtin_dataset_info(str(dataset_name))
        if update_location:
            for key, value in (("lat_entry", info.latitude), ("lon_entry", info.longitude), ("alt_entry", info.altitude_m)):
                entry = widgets[key]
                entry.delete(0, tk.END)  # type: ignore[attr-defined]
                entry.insert(0, f"{value:.5g}")  # type: ignore[attr-defined]
        if info.region.lower().startswith("china") or "China" in info.region or not update_location:
            widgets["holiday_var"].set("CN")  # type: ignore[union-attr]
        if update_location:
            climate = classify_climate_block(info.latitude, info.longitude, info.altitude_m)
        else:
            climate = classify_climate_block(
                _safe_float(widgets["lat_entry"].get(), "纬度"),  # type: ignore[attr-defined]
                _safe_float(widgets["lon_entry"].get(), "经度"),  # type: ignore[attr-defined]
                _safe_float(widgets["alt_entry"].get(), "海拔"),  # type: ignore[attr-defined]
            )
        resource_hint = "\n提示：新能源预测只对所选风电或光伏资源独立建模。" if kind == "renewable" else ""
        info_base = f"{info.region}\n来源：{info.source}\n自动气候板块：{climate}{resource_hint}\n{info.notes}"
        widgets["info_base_text"] = info_base
        widgets["info_var"].set(translate_text(info_base, getattr(self, "language", "zh")))  # type: ignore[union-attr]
        self._apply_forecast_algorithm_hint(kind)
        if kind == "renewable":
            self._run_renewable_solar_helper(silent=True)

    def _forecast_algorithm_code_from_label(self, label: str, algorithm_by_label: object) -> str:
        if not isinstance(algorithm_by_label, dict):
            return "adaptive_ensemble"
        candidates = [str(label), logic_text(str(label), getattr(self, "language", "zh"))]
        for candidate in candidates:
            code = algorithm_by_label.get(candidate)
            if code:
                return str(code)
        for candidate in candidates:
            for _display_label, code in algorithm_by_label.items():
                if candidate.endswith(f"({code})"):
                    return str(code)
        return "adaptive_ensemble"

    def _apply_forecast_algorithm_hint(self, kind: str) -> None:
        widgets = self._forecast_widgets.get(kind)
        if not widgets:
            return
        label = widgets["algorithm_var"].get()  # type: ignore[union-attr]
        code = self._forecast_algorithm_code_from_label(str(label), widgets.get("algorithm_by_label", {}))
        info_base = str(widgets.get("info_base_text") or widgets["info_var"].get())  # type: ignore[union-attr]
        for info in list_forecast_algorithms(kind):
            if info.code == code:
                base = info_base.split("\n算法：", 1)[0]
                lang = getattr(self, "language", "zh")
                if lang == "en":
                    short = f"\nAlgorithm: {translate_text(info.label, lang)}. {translate_text(info.description, lang)}"
                    widgets["info_var"].set(translate_text(base, lang) + short)  # type: ignore[union-attr]
                else:
                    short = f"\n算法：{info.label}。{info.description}"
                    widgets["info_var"].set(base + short)  # type: ignore[union-attr]
                break

    def _import_forecast_csv(self, kind: str) -> None:
        widgets = self._forecast_widgets.get(kind)
        if not widgets:
            return
        filename = filedialog.askopenfilename(title="选择预测训练CSV", filetypes=[("CSV", "*.csv"), ("All files", "*.*")])
        if not filename:
            return
        widgets["custom_path_var"].set(filename)  # type: ignore[union-attr]
        widgets["dataset_var"].set(f"CSV: {Path(filename).name}")  # type: ignore[union-attr]
        info_base = "已选择外部训练 CSV。支持 timestamp/load_mw/demand_mw/solar_mw/wind_mw/renewable_mw/temperature_c/ghi_wm2/wind_speed_mps，以及中文 日期/时刻/统调负荷/气温、Baidu KDD Tmstamp/Wspd/Patv 等表头。"
        widgets["info_base_text"] = info_base
        widgets["info_var"].set(translate_text(info_base, getattr(self, "language", "zh")))  # type: ignore[union-attr]
        self._apply_forecast_algorithm_hint(kind)

    def _import_future_weather_csv(self, kind: str) -> None:
        widgets = self._forecast_widgets.get(kind)
        if not widgets:
            return
        filename = filedialog.askopenfilename(title="选择未来天气预报CSV", filetypes=[("CSV", "*.csv"), ("All files", "*.*")])
        if not filename:
            return
        try:
            rows = load_future_weather_csv(filename)
        except Exception as exc:
            messagebox.showerror("天气CSV导入失败", str(exc))
            return
        widgets["future_weather_path_var"].set(filename)  # type: ignore[union-attr]
        fields = sorted({key for row in rows for key in row.keys() if key != "timestamp"})
        first_ts = rows[0]["timestamp"]
        last_ts = rows[-1]["timestamp"]
        info_base = (
            f"已选择未来天气 CSV：{Path(filename).name}。\n"
            f"记录数：{len(rows)}；时间范围：{first_ts:%Y-%m-%d %H:%M}—{last_ts:%Y-%m-%d %H:%M}；字段：{', '.join(fields)}。\n"
            "预测时同时间戳温度/GHI/风速/云量将优先覆盖或修正历史同刻推断值；小时级天气会对 1–30 分钟预测点插值。"
        )
        widgets["info_base_text"] = info_base
        widgets["info_var"].set(translate_text(info_base, getattr(self, "language", "zh")))  # type: ignore[union-attr]
        self._apply_forecast_algorithm_hint(kind)

    def _run_day_ahead_forecast(self, kind: str) -> None:
        widgets = self._forecast_widgets[kind]
        try:
            dataset_name = widgets["dataset_var"].get()  # type: ignore[union-attr]
            if str(dataset_name).startswith("CSV:"):
                rows = load_forecast_csv(widgets["custom_path_var"].get(), kind)  # type: ignore[union-attr]
            else:
                rows = load_builtin_forecast_dataset(str(dataset_name))
            target = datetime.strptime(widgets["date_var"].get().strip(), "%Y-%m-%d").date()  # type: ignore[union-attr]
            future_weather_path = widgets["future_weather_path_var"].get().strip()  # type: ignore[union-attr]
            future_weather_rows = tuple(load_future_weather_csv(future_weather_path)) if future_weather_path else None
            capacity_entry = widgets.get("capacity_entry")
            capacity = None if capacity_entry is None else _safe_float(capacity_entry.get(), "装机容量上限")  # type: ignore[attr-defined]
            interval_minutes = int(_safe_float(widgets["interval_var"].get(), "时段间隔"))  # type: ignore[union-attr]
            if interval_minutes < 1 or interval_minutes > 30:
                raise InputError("时段间隔需为 1 到 30 分钟之间的整数。")
            algorithm_label = widgets["algorithm_var"].get()  # type: ignore[union-attr]
            algorithm = self._forecast_algorithm_code_from_label(str(algorithm_label), widgets.get("algorithm_by_label", {}))
            weather_condition = _weather_label_to_code(widgets["weather_var"].get()) if kind == "renewable" else "clear"  # type: ignore[union-attr]
            cloud = _safe_float(widgets["cloud_entry"].get(), "云量") if kind == "renewable" and widgets.get("cloud_entry") is not None else 0.0  # type: ignore[attr-defined]
            irr_adjust = _safe_float(widgets["irr_adjust_entry"].get(), "辐照人工系数") if kind == "renewable" and widgets.get("irr_adjust_entry") is not None else 1.0  # type: ignore[attr-defined]
            tilt = _safe_float(widgets["tilt_entry"].get(), "组件倾角") if kind == "renewable" and widgets.get("tilt_entry") is not None else 30.0  # type: ignore[attr-defined]
            pv_azimuth = _safe_float(widgets["pv_azimuth_entry"].get(), "组件方位角") if kind == "renewable" and widgets.get("pv_azimuth_entry") is not None else 180.0  # type: ignore[attr-defined]
            albedo = _safe_float(widgets["albedo_entry"].get(), "地表反照率") if kind == "renewable" and widgets.get("albedo_entry") is not None else 0.20  # type: ignore[attr-defined]
            temp_coeff = _safe_float(widgets["temp_coeff_entry"].get(), "组件温度系数") if kind == "renewable" and widgets.get("temp_coeff_entry") is not None else -0.35  # type: ignore[attr-defined]
            config = ForecastConfig(
                kind=kind,
                target_date=target,
                latitude=_safe_float(widgets["lat_entry"].get(), "纬度"),  # type: ignore[attr-defined]
                longitude=_safe_float(widgets["lon_entry"].get(), "经度"),  # type: ignore[attr-defined]
                altitude_m=_safe_float(widgets["alt_entry"].get(), "海拔"),  # type: ignore[attr-defined]
                holiday_country=widgets["holiday_var"].get(),  # type: ignore[union-attr]
                renewable_capacity_mw=capacity,
                renewable_resource=widgets["resource_var"].get(),  # type: ignore[union-attr]
                algorithm=str(algorithm),
                interval_minutes=interval_minutes,
                horizon_hours=24,
                weather_condition=weather_condition,
                cloud_cover_pct=cloud,
                irradiance_adjustment=irr_adjust,
                pv_tilt_deg=tilt,
                pv_azimuth_deg=pv_azimuth,
                pv_albedo=albedo,
                pv_temp_coeff_pct_per_c=temp_coeff,
                future_weather_rows=future_weather_rows,
                future_weather_source=Path(future_weather_path).name if future_weather_path else "",
            )
            result = forecast_day_ahead(rows, config)
            widgets["last_result"] = result
            self._set_text(widgets["result_text"], translate_text(format_forecast_summary(result), getattr(self, "language", "zh")))  # type: ignore[arg-type]
            self._plot_day_ahead_forecast(kind, result)
            self._fill_forecast_detail_table(kind, result)
            self._fill_forecast_metric_text(kind, result)
            if kind == "renewable":
                self._run_renewable_solar_helper(silent=True)
        except Exception as exc:
            messagebox.showerror("预测失败", str(exc))

    @staticmethod
    def _day_minutes(dt: datetime | None) -> float:
        if dt is None:
            return 0.0
        return dt.hour * 60.0 + dt.minute + dt.second / 60.0

    @staticmethod
    def _minutes_to_hhmm(minutes: float) -> str:
        minutes_i = int(round(float(minutes))) % (24 * 60)
        return f"{minutes_i // 60:02d}:{minutes_i % 60:02d}"

    def _update_solar_time_controls(self, profile, analysis_ts: datetime) -> None:
        widgets = self._forecast_widgets.get("renewable")
        if not widgets:
            return
        if profile.sunrise is not None and profile.sunset is not None:
            lower = max(0.0, self._day_minutes(profile.sunrise))
            upper = min(24.0 * 60.0, self._day_minutes(profile.sunset))
            if upper <= lower:
                lower, upper = 0.0, 24.0 * 60.0
            note = f"日照区间：{_format_clock(profile.sunrise)}—{_format_clock(profile.sunset)}；拖拽滑条或曲线区选择当前时刻。"
        else:
            lower, upper = 0.0, 24.0 * 60.0
            note = "当天无常规日出/日落区间；滑条按 00:00—24:00 显示。"
        widgets["solar_time_bounds_min"] = (lower, upper)
        slider = widgets.get("solar_time_slider")
        if slider is not None:
            widgets["solar_slider_updating"] = True
            try:
                slider.configure(from_=lower, to=upper)  # type: ignore[attr-defined]
                current = self._day_minutes(analysis_ts)
                slider.set(min(max(current, lower), upper))  # type: ignore[attr-defined]
            finally:
                widgets["solar_slider_updating"] = False
        note_var = widgets.get("solar_time_note_var")
        if note_var is not None:
            note_var.set(translate_text(note, getattr(self, "language", "zh")))  # type: ignore[attr-defined]

    def _set_renewable_solar_time_from_minutes(self, minutes: float, redraw: bool = True) -> None:
        widgets = self._forecast_widgets.get("renewable")
        if not widgets:
            return
        lower, upper = widgets.get("solar_time_bounds_min", (0.0, 24.0 * 60.0))
        minutes = min(max(float(minutes), float(lower)), float(upper))
        widgets["solar_time_var"].set(self._minutes_to_hhmm(minutes))  # type: ignore[union-attr]
        if not redraw:
            return

        # Keep the solar helper responsive while the user is dragging.  The
        # previous debounce waited until pointer/slider events paused before
        # recomputing, which made the marker lag behind the cursor.  Cancel any
        # older delayed refresh and recompute immediately for the current event.
        after_id = widgets.get("solar_slider_after_id")
        if after_id is not None:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
            widgets["solar_slider_after_id"] = None
        self._run_renewable_solar_helper(silent=True)

    def _on_solar_time_slider(self, value: str) -> None:
        widgets = self._forecast_widgets.get("renewable")
        if not widgets or widgets.get("solar_slider_updating"):
            return
        try:
            minutes = float(value)
        except (TypeError, ValueError):
            return
        self._set_renewable_solar_time_from_minutes(minutes, redraw=True)

    def _solar_event_minutes(self, event) -> float | None:
        widgets = self._forecast_widgets.get("renewable")
        if not widgets or event.xdata is None:
            return None
        axes = tuple(widgets.get("solar_curve_axes", ()))
        if axes and event.inaxes not in axes:
            return None
        lower, upper = widgets.get("solar_time_bounds_min", (0.0, 24.0 * 60.0))
        return min(max(float(event.xdata) * 60.0, float(lower)), float(upper))

    def _on_solar_plot_button_press(self, event) -> None:
        if getattr(event, "button", None) != 1:
            return
        minutes = self._solar_event_minutes(event)
        if minutes is None:
            return
        widgets = self._forecast_widgets.get("renewable")
        if widgets is not None:
            widgets["solar_plot_dragging"] = True
        self._set_renewable_solar_time_from_minutes(minutes, redraw=True)

    def _on_solar_plot_motion(self, event) -> None:
        widgets = self._forecast_widgets.get("renewable")
        if not widgets or not widgets.get("solar_plot_dragging"):
            return
        minutes = self._solar_event_minutes(event)
        if minutes is None:
            return
        self._set_renewable_solar_time_from_minutes(minutes, redraw=True)

    def _on_solar_plot_button_release(self, event) -> None:
        widgets = self._forecast_widgets.get("renewable")
        if not widgets:
            return
        widgets["solar_plot_dragging"] = False
        minutes = self._solar_event_minutes(event)
        if minutes is not None:
            self._set_renewable_solar_time_from_minutes(minutes, redraw=True)

    def _run_renewable_solar_helper(self, silent: bool = False) -> None:
        widgets = self._forecast_widgets.get("renewable")
        if not widgets:
            return
        try:
            target_date = datetime.strptime(widgets["date_var"].get().strip(), "%Y-%m-%d").date()  # type: ignore[union-attr]
            time_text = widgets.get("solar_time_var").get().strip() or "12:00"  # type: ignore[union-attr]
            try:
                analysis_ts = datetime.strptime(f"{target_date.isoformat()} {time_text}", "%Y-%m-%d %H:%M")
            except ValueError:
                analysis_ts = datetime.strptime(f"{target_date.isoformat()} {time_text}", "%Y-%m-%d %H")
            latitude = _safe_float(widgets["lat_entry"].get(), "纬度")  # type: ignore[attr-defined]
            longitude = _safe_float(widgets["lon_entry"].get(), "经度")  # type: ignore[attr-defined]
            weather_condition = _weather_label_to_code(widgets["weather_var"].get())  # type: ignore[union-attr]
            cloud = _safe_float(widgets["cloud_entry"].get(), "云量") if widgets.get("cloud_entry") is not None else 0.0  # type: ignore[attr-defined]
            irr_adjust = _safe_float(widgets["irr_adjust_entry"].get(), "辐照人工系数") if widgets.get("irr_adjust_entry") is not None else 1.0  # type: ignore[attr-defined]
            tilt = _safe_float(widgets["tilt_entry"].get(), "组件倾角") if widgets.get("tilt_entry") is not None else 30.0  # type: ignore[attr-defined]
            pv_azimuth = _safe_float(widgets["pv_azimuth_entry"].get(), "组件方位角") if widgets.get("pv_azimuth_entry") is not None else 180.0  # type: ignore[attr-defined]
            albedo = _safe_float(widgets["albedo_entry"].get(), "地表反照率") if widgets.get("albedo_entry") is not None else 0.20  # type: ignore[attr-defined]
            temp_coeff = _safe_float(widgets["temp_coeff_entry"].get(), "组件温度系数") if widgets.get("temp_coeff_entry") is not None else -0.35  # type: ignore[attr-defined]
            temp = 25.0
            pos = solar_position(analysis_ts, latitude, longitude)
            irr = solar_irradiance_on_panel(
                analysis_ts, latitude, longitude, temp,
                weather_condition, cloud, irr_adjust,
                tilt, pv_azimuth, albedo, temp_coeff,
            )
            profile = solar_day_profile(target_date, latitude, longitude, pos.timezone_offset_hours, step_minutes=10)
            self._update_solar_time_controls(profile, analysis_ts)
            irradiance_profile = tuple(
                solar_irradiance_on_panel(
                    p.timestamp, latitude, longitude, temp,
                    weather_condition, cloud, irr_adjust,
                    tilt, pv_azimuth, albedo, temp_coeff,
                )
                for p in profile.points
            )
            widgets["last_solar_profile"] = (pos, profile, irr, irradiance_profile)

            direction_labels_zh = [
                "正北", "东北偏北", "东北", "东北偏东", "正东", "东南偏东", "东南", "东南偏南",
                "正南", "西南偏南", "西南", "西南偏西", "正西", "西北偏西", "西北", "西北偏北",
            ]
            direction_labels_en = [
                "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
            ]
            direction_labels = direction_labels_en if getattr(self, "language", "zh") == "en" else direction_labels_zh
            direction = direction_labels[int(((pos.azimuth_deg % 360.0) + 11.25) // 22.5) % 16]
            visibility = "太阳位于地平线上方" if pos.altitude_deg > 0.0 else "太阳位于地平线以下"
            lines = [
                "══ 太阳角度与光伏修正辅助分析 ═══════════════",
                f"位置：纬度 {latitude:.4f}°，经度 {longitude:.4f}°；自动采用标准时区 {_format_utc_offset(pos.timezone_offset_hours)}（标准经线 {profile.standard_meridian_deg:.1f}°）",
                f"分析时刻：{analysis_ts:%Y-%m-%d %H:%M}（标准时） / 对应太阳时 {_format_decimal_hours(pos.local_solar_time_hours % 24.0)}",
                f"当前太阳高度角：{pos.altitude_deg:.2f}°   天顶角：{pos.zenith_deg:.2f}°   方位角：{pos.azimuth_deg:.2f}°（{direction}）",
                f"晴空水平 GHI：{pos.clear_sky_ghi_wm2:.0f} W/m2；天气修正后 GHI：{irr.corrected_ghi_wm2:.0f} W/m2；倾斜面 POA：{irr.poa_wm2:.0f} W/m2",
                f"直射水平：{irr.direct_horizontal_wm2:.0f} W/m2；散射水平：{irr.diffuse_horizontal_wm2:.0f} W/m2；入射角：{irr.incidence_angle_deg:.2f}°",
                f"天气：{widgets['weather_var'].get()}，云量={cloud:.0f}%，辐照人工系数={irr_adjust:.2f}，天气系数={irr.weather_factor:.2f}",  # type: ignore[index]
                f"组件：倾角={tilt:.1f}°，方位角={pv_azimuth:.1f}°，地表反照率={albedo:.2f}，温度系数={temp_coeff:.3f}%/℃，相对功率修正={irr.pv_power_factor:.3f}",
                f"太阳赤纬：{pos.declination_deg:.2f}°   时差方程：{pos.equation_of_time_min:+.2f} min   时角：{pos.hour_angle_deg:+.2f}°   状态：{visibility}",
                "",
                "当日太阳轨迹摘要：",
                f"  日出：{_format_clock(profile.sunrise)}    太阳正午：{_format_clock(profile.solar_noon)}    日落：{_format_clock(profile.sunset)}",
                f"  正午太阳高度角：{profile.solar_noon_altitude_deg:.2f}°    白昼长度：{profile.daylight_hours:.2f} h",
                "说明：方位角采用 0°=正北、90°=正东、180°=正南、270°=正西；可在下方滑条或右侧曲线区拖拽当前时刻，POA 已用于新能源预测。",
            ]
            if widgets.get("solar_result_text") is not None:
                self._set_text(widgets["solar_result_text"], translate_text("\n".join(lines), getattr(self, "language", "zh")))  # type: ignore[arg-type]
            self._plot_renewable_solar_helper(pos, profile, irradiance_profile)
        except Exception as exc:
            if not silent:
                messagebox.showerror("太阳角度分析失败", str(exc))

    def _plot_renewable_solar_helper(self, pos, profile, irradiance_profile=()) -> None:
        widgets = self._forecast_widgets.get("renewable")
        if not widgets or widgets.get("solar_fig") is None or widgets.get("solar_canvas") is None:
            return
        fig = widgets["solar_fig"]
        fig.clear()
        ax_polar = fig.add_subplot(121, projection="polar")
        ax_curve = fig.add_subplot(122)
        fig.subplots_adjust(left=0.06, right=0.88, top=0.84, bottom=0.18, wspace=0.42)

        daylight_points = [p for p in profile.points if p.altitude_deg >= 0.0]
        if daylight_points:
            theta = np.radians([p.azimuth_deg for p in daylight_points])
            radius = [90.0 - p.altitude_deg for p in daylight_points]
            ax_polar.plot(theta, radius, color="#f39c12", linewidth=2.2, label="太阳轨迹")
            ax_polar.fill(theta, radius, color="#f7dc6f", alpha=0.25)
        current_r = min(90.0, max(0.0, 90.0 - max(pos.altitude_deg, 0.0)))
        ax_polar.scatter([math.radians(pos.azimuth_deg)], [current_r], s=85, color="#d35400", zorder=5, label="当前时刻")
        ax_polar.set_theta_zero_location("N")
        ax_polar.set_theta_direction(-1)
        ax_polar.set_ylim(0, 90)
        ax_polar.set_rticks([0, 30, 60, 90])
        ax_polar.set_yticklabels(["90°", "60°", "30°", "0°"])
        ax_polar.set_rlabel_position(135)
        compass_labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"] if getattr(self, "language", "zh") == "en" else ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
        ax_polar.set_thetagrids(range(0, 360, 45), labels=compass_labels)
        ax_polar.grid(True, alpha=0.35)
        ax_polar.set_title("太阳穹顶轨迹图\n（中心=天顶，外圈=地平线）", fontsize=11)
        if daylight_points:
            ax_polar.legend(loc="lower left", fontsize=8)

        midnight = datetime.combine(profile.target_date, datetime.min.time())
        x_hours = [(p.timestamp - midnight).total_seconds() / 3600.0 for p in profile.points]
        altitudes = [p.altitude_deg for p in profile.points]
        clear_ghis = [p.clear_sky_ghi_wm2 for p in profile.points]
        if irradiance_profile:
            corrected_ghis = [irr.corrected_ghi_wm2 for irr in irradiance_profile]
            poas = [irr.poa_wm2 for irr in irradiance_profile]
        else:
            corrected_ghis = clear_ghis
            poas = clear_ghis

        alt_line = ax_curve.plot(x_hours, altitudes, color="#1f77b4", linewidth=2.0, label="高度角 / °")[0]
        ax_curve.fill_between(x_hours, altitudes, [0.0] * len(altitudes), where=np.array(altitudes) > 0.0, color="#cfe2f3", alpha=0.55)
        ax_curve.axhline(0.0, color="#7f8c8d", linewidth=1.0, linestyle="--")
        ax_curve.set_xlim(0, 24)
        ax_curve.set_xticks(range(0, 25, 2))
        ax_curve.set_xlabel("标准时 / h")
        ax_curve.set_ylabel("太阳高度角 / °")
        ax_curve.set_ylim(min(-15.0, min(altitudes) - 2.0), max(90.0, max(altitudes) + 3.0))
        ax_curve.grid(True, alpha=0.3)

        ax_ghi = ax_curve.twinx()
        clear_line = ax_ghi.plot(x_hours, clear_ghis, color="#f39c12", linewidth=1.4, linestyle="--", label="晴空 GHI / W/m2")[0]
        corr_line = ax_ghi.plot(x_hours, corrected_ghis, color="#e67e22", linewidth=1.8, label="天气修正 GHI / W/m2")[0]
        poa_line = ax_ghi.plot(x_hours, poas, color="#c0392b", linewidth=2.0, label="组件 POA / W/m2")[0]
        ax_ghi.fill_between(x_hours, poas, [0.0] * len(poas), color="#fdebd0", alpha=0.28)
        ax_ghi.set_ylabel("辐照度 / W/m2")
        all_irrad = clear_ghis + corrected_ghis + poas
        ax_ghi.set_ylim(0, max(1000.0, max(all_irrad) * 1.12 if all_irrad else 1000.0))

        line_positions = [
            (profile.sunrise, "日出", "#27ae60"),
            (profile.solar_noon, "正午", "#8e44ad"),
            (profile.sunset, "日落", "#c0392b"),
            (pos.timestamp, "当前", "#d35400"),
        ]
        for dt, label, color in line_positions:
            if dt is None:
                continue
            hour = (dt - midnight).total_seconds() / 3600.0
            if 0.0 <= hour <= 24.0:
                ax_curve.axvline(hour, color=color, linestyle=":" if label != "当前" else "-.", linewidth=1.2, alpha=0.9)
                if label == "当前":
                    y_top = ax_curve.get_ylim()[1]
                    ax_curve.text(hour, y_top - 4.0, f"{label}\n{dt:%H:%M}", ha="center", va="top", fontsize=8, color=color,
                                  bbox=dict(boxstyle="round,pad=0.18", fc="white", ec=color, alpha=0.82))

        ax_curve.set_title(
            f"{profile.target_date:%Y-%m-%d} 全天太阳高度、天气修正 GHI 与组件 POA\n"
            f"正午 {profile.solar_noon:%H:%M}，当前 {pos.timestamp:%H:%M}"
        )
        lines = [alt_line, clear_line, corr_line, poa_line]
        ax_curve.legend(lines, [line.get_label() for line in lines], loc="upper left", fontsize=8)

        widgets["solar_axes"] = (ax_polar, ax_curve, ax_ghi)
        widgets["solar_curve_axes"] = (ax_curve, ax_ghi)
        widgets["solar_canvas"].draw_idle()  # type: ignore[attr-defined]

    def _fill_forecast_detail_table(self, kind: str, result) -> None:
        widgets = self._forecast_widgets[kind]
        tree = widgets["detail_tree"]
        for item in tree.get_children():  # type: ignore[attr-defined]
            tree.delete(item)  # type: ignore[attr-defined]
        for p in result.points:
            if kind == "renewable":
                values = (
                    f"{p.timestamp:%Y-%m-%d %H:%M}",
                    f"{p.p10_mw:.1f}",
                    f"{p.value_mw:.1f}",
                    f"{p.p90_mw:.1f}",
                    f"{p.temperature_c:.1f}",
                    f"{p.ghi_wm2:.0f}",
                    f"{p.poa_wm2:.0f}",
                    f"{p.solar_altitude_deg:.1f}",
                    f"{p.solar_azimuth_deg:.0f}",
                    f"{p.incidence_angle_deg:.1f}",
                    f"{p.weather_factor:.2f}",
                    f"{p.pv_power_factor:.2f}",
                    f"{p.wind_speed_mps:.1f}",
                    translate_text(p.drivers, getattr(self, "language", "zh")),
                )
            else:
                values = (
                    f"{p.timestamp:%Y-%m-%d %H:%M}",
                    f"{p.p10_mw:.1f}",
                    f"{p.value_mw:.1f}",
                    f"{p.p90_mw:.1f}",
                    f"{p.temperature_c:.1f}",
                    f"{p.ghi_wm2:.0f}",
                    f"{p.wind_speed_mps:.1f}",
                    translate_text(p.drivers, getattr(self, "language", "zh")),
                )
            tree.insert("", "end", values=values)  # type: ignore[attr-defined]

    def _fill_forecast_metric_text(self, kind: str, result) -> None:
        lines = ["══ 算法校验与日特性 ══════════════════════", f"最终模型：{result.model_name}", f"气候板块：{result.climate_block}", ""]
        if result.algorithm_metrics:
            lines.append("算法                     权重      MAE/MW    RMSE/MW   MAPE/%   状态")
            for m in result.algorithm_metrics:
                mae = "-" if not math.isfinite(m.mae_mw) else f"{m.mae_mw:.2f}"
                rmse = "-" if not math.isfinite(m.rmse_mw) else f"{m.rmse_mw:.2f}"
                mape = "-" if not math.isfinite(m.mape_pct) else f"{m.mape_pct:.2f}"
                status = "可用" if m.available else "不可用"
                if m.note:
                    status += f"；{m.note}"
                lines.append(f"{m.label:<22} {m.weight:7.3f}  {mae:>8}  {rmse:>8}  {mape:>7}  {status}")
            lines.append("")
        lines.append("日特性：")
        for name, value in result.daily_stats:
            if "率" in name or "因子" in name:
                lines.append(f"  {name}: {value:.4f}")
            else:
                lines.append(f"  {name}: {value:.2f}")
        self._set_text(self._forecast_widgets[kind]["metric_text"], translate_text("\n".join(lines), getattr(self, "language", "zh")))  # type: ignore[arg-type]

    def _export_forecast_result(self, kind: str, fmt: str) -> None:
        widgets = self._forecast_widgets.get(kind)
        if not widgets:
            return
        result = widgets.get("last_result")
        if result is None:
            messagebox.showinfo("尚无结果", "请先执行预测，再导出结果。")
            return
        suffix = ".json" if fmt == "json" else ".csv"
        filename = filedialog.asksaveasfilename(
            title="导出预测结果",
            defaultextension=suffix,
            filetypes=[("JSON", "*.json")] if fmt == "json" else [("CSV", "*.csv")],
            initialfile=f"{kind}_forecast_{datetime.now():%Y%m%d_%H%M%S}{suffix}",
        )
        if not filename:
            return
        try:
            if fmt == "json":
                export_forecast_result_json(result, filename)
            else:
                export_forecast_result_csv(result, filename)
            messagebox.showinfo("导出完成", f"预测结果已导出：{filename}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def _plot_day_ahead_forecast(self, kind: str, result) -> None:
        widgets = self._forecast_widgets[kind]
        fig = widgets["fig"]
        fig.clear()
        ax = fig.add_subplot(111)
        fig.subplots_adjust(left=0.08, right=0.88, top=0.86, bottom=0.16)
        widgets["ax"] = ax
        x = [p.timestamp.hour + p.timestamp.minute / 60.0 for p in result.points]
        values = [p.value_mw for p in result.points]
        p10 = [p.p10_mw for p in result.points]
        p90 = [p.p90_mw for p in result.points]
        color = "#1f77b4" if kind == "load" else "#2ca02c"
        ax.fill_between(x, p10, p90, color=color, alpha=0.18, label="P10-P90")
        ax.plot(x, values, marker="o", markersize=3.2, color=color, linewidth=1.8, label="Forecast MW")
        ax.set_title("负荷日前预测" if kind == "load" else "新能源日前预测（联动太阳几何/天气/POA）")
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("MW")
        ticks = list(range(0, 25, 2))
        ax.set_xticks(ticks)
        ax.set_xlim(0, 24)
        ax.grid(True, alpha=0.35)
        if kind == "renewable" and any(getattr(p, "poa_wm2", 0.0) > 0.0 for p in result.points):
            ax2 = ax.twinx()
            poa = [p.poa_wm2 for p in result.points]
            ghi = [p.ghi_wm2 for p in result.points]
            ax2.plot(x, poa, color="#c0392b", linestyle="--", linewidth=1.5, label="POA W/m2")
            ax2.plot(x, ghi, color="#f39c12", linestyle=":", linewidth=1.3, label="GHI W/m2")
            ax2.set_ylabel("Irradiance / W/m2")
            ax2.set_ylim(0, max(1000.0, max(poa + ghi) * 1.1))
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=8)
        else:
            ax.legend(loc="best")
        widgets["canvas"].draw()  # type: ignore[attr-defined]


__all__ = ["ForecastGuiMixin"]
