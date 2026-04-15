from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from power_tool_gui import ApproximationToolGUI, _detect_key_conclusion_lines, _manual_filename, _notebook_style_spec


def test_key_conclusion_line_detection() -> None:
    text = """推导过程：略
运行区间判断：总体发无功（净容性）
说明：这不是关键结论
稳定性判断：[稳定]
  匹配：额定开断电流 ≥ 计算开断电流。
"""
    assert _detect_key_conclusion_lines(text) == [2, 4, 5]


def test_notebook_style_spec_uses_same_padding_for_selected_and_unselected() -> None:
    spec = _notebook_style_spec()
    padding_map = dict(spec["map"]["padding"])
    background_map = dict(spec["map"]["background"])
    assert padding_map["selected"] == (16, 8)
    assert padding_map["!selected"] == (16, 8)
    assert background_map["selected"] == "#173f7a"


class _FakeEntry:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class _FakeLabel:
    def __init__(self, text: str) -> None:
        self._text = text

    def cget(self, key: str) -> str:
        assert key == "text"
        return self._text


class _FakeNotebook:
    def __init__(self, current: str) -> None:
        self.current = current

    def select(self) -> str:
        return self.current

    def tab(self, selected: str, option: str) -> str:
        assert option == "text"
        return selected


class _FakeText:
    def __init__(self, text: str) -> None:
        self.text = text
        self.state = "normal"

    def delete(self, _start: str, _end: str) -> None:
        self.text = ""

    def insert(self, _index: str, text: str) -> None:
        self.text += text

    def configure(self, **kwargs: str) -> None:
        if "state" in kwargs:
            self.state = kwargs["state"]


class _FakeVar:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def set(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


class _SummaryDummy:
    def __init__(self) -> None:
        self.current_tab = "频率动态"
        self.current_param_tab = "架空线路"
        self.param_notebook = _FakeNotebook(self.current_param_tab)
        self.current_vr_tab = "静态电压稳定"
        self._vr_notebook = _FakeNotebook(self.current_vr_tab)
        self.smib_config = _FakeEntry("Kundur")
        self.smib_entries = {"Xd'": _FakeEntry("0.3"), "H": _FakeEntry("6")}
        self.comtrade_time_label = _FakeLabel("-0.1 s ~ 0.2 s")
        self._comtrade_cfg_path = "demo.cfg"
        entries = {
            "freq_f0": "50", "freq_dp": "0.08", "freq_ts": "8", "freq_tg": "5", "freq_kd": "1.2", "freq_kg": "4.0", "freq_tend": "30", "freq_kp_agc": "0.12", "freq_ki_agc": "0.01",
            "osc_eq": "1.12", "osc_u": "1.0", "osc_x": "0.55", "osc_p0": "0.8", "osc_tj": "9", "osc_f0": "50",
            "volt_ug": "1.0", "volt_x": "0.32", "volt_pf": "0.95", "volt_sbase": "100",
            "line_u": "500", "line_zc": "250", "line_l": "", "line_c": "", "line_p": "900", "line_qn": "1.1", "line_len": "300",
            "avc_vh": "226", "avc_p": "160", "avc_q": "45", "avc_tap_now": "0",
            "imp_dp": "0.2", "imp_dt": "0.1", "imp_fd": "2.0", "imp_pmax": "1.8", "imp_pcur": "0.9", "eac_pm": "0.85", "eac_ppre": "2.1", "eac_pf": "0.7", "eac_ppost": "1.9", "eac_dt": "0.12",
            "loop_n": "7", "loop_u1": "10", "loop_u2": "10", "loop_angle": "14", "loop_freq": "50",
            "lp_ubase": "110", "lp_sbase": "100", "lp_len": "30", "lp_r1": "0.05", "lp_x1": "0.40", "lp_c1": "0.012",
            "tx2_sbase": "100", "tx2_sn": "63", "tx2_un": "110", "tx2_uk": "10.5", "tx2_pk": "180", "tx2_i0": "0.8", "tx2_p0": "45", "tx2_ubase": "110",
            "tx3_sbase": "100", "tx3_ubase": "220", "tx3_sn_h": "180", "tx3_un_h": "220", "tx3_sn_m": "180", "tx3_sn_l": "90", "tx3_uk_hm": "12", "tx3_uk_hl": "18", "tx3_uk_ml": "7",
            "sag_span": "400", "sag_h_left": "35", "sag_h_right": "38", "sag_mass": "1.35", "sag_href": "25", "sag_ambient": "25",
            "sc_u": "110", "sc_len": "30", "sc_r1": "0.05", "sc_x1": "0.40", "sc_r0": "0.15", "sc_x0": "1.20", "sc_rn": "0", "sc_rf": "0.0",
            "sc_delta_right": "0.0", "sc_fault_pos": "50",
        }
        for name, value in entries.items():
            setattr(self, name, _FakeEntry(value))
        self.sag_driver_var = _FakeVar("temperature")
        self.sag_temp_scale_var = _FakeVar("60")
        self.sag_current_scale_var = _FakeVar("500")

    def _current_tab_name(self) -> str:
        return self.current_tab


def test_tab_numeric_summary_covers_every_main_tab_and_param_subtab() -> None:
    dummy = _SummaryDummy()
    cases = {
        "频率动态": "额定频率 f0 / Hz: 50",
        "机电振荡": "内电势 E'_q / pu: 1.12",
        "电压无功分析": "送端电压 U_g / pu: 1.0",
        "暂稳评估": "冲击法 ΔPa / pu: 0.2",
        "小扰动分析（SMIB）": "模型配置: Kundur",
        "配电网合环分析": "连接点数量 N: 7",
        "短路电流计算": "系统电压 / kV: 110",
        "录波曲线": "当前录波文件: demo.cfg",
    }
    for tab_name, expected in cases.items():
        dummy.current_tab = tab_name
        summary = ApproximationToolGUI._tab_numeric_summary(dummy)
        assert expected in summary

    dummy.current_tab = "电压无功分析"
    dummy._vr_notebook.current = "线路自然功率与无功"
    assert "线路额定电压 U / kV: 500" in ApproximationToolGUI._tab_numeric_summary(dummy)
    dummy._vr_notebook.current = "AVC策略模拟"
    assert "高压侧当前电压 / kV: 226" in ApproximationToolGUI._tab_numeric_summary(dummy)

    dummy.current_tab = "参数校核与标幺值"
    for subtab, expected in {
        "架空线路": "参数页子标签: 架空线路",
        "导线弧垂": "档距 l / m: 400",
        "两绕组变压器": "额定容量 SN / MVA: 63",
        "三绕组变压器": "Uk_HL / %: 18",
    }.items():
        dummy.param_notebook.current = subtab
        summary = ApproximationToolGUI._tab_numeric_summary(dummy)
        assert expected in summary


def test_on_ai_context_changed_clears_question_and_answer_immediately() -> None:
    dummy = type("Dummy", (), {})()
    dummy.ai_question = _FakeText("旧问题")
    dummy.ai_answer = _FakeText("旧回答")
    dummy.ai_status_var = _FakeVar()
    dummy._ai_status_summary = lambda: "状态已刷新"
    dummy._clear_ai_context = lambda: ApproximationToolGUI._clear_ai_context(dummy)

    ApproximationToolGUI._on_ai_context_changed(dummy)

    assert dummy.ai_question.text == ""
    assert dummy.ai_answer.text == ""
    assert dummy.ai_answer.state == "disabled"
    assert dummy.ai_status_var.value == "状态已刷新"


def test_manual_doc_path_matches_current_tab_and_subtab() -> None:
    dummy = type("Dummy", (), {})()
    dummy.language = "zh"
    dummy._current_tab_name = lambda: "电压无功分析"
    dummy._vr_notebook = _FakeNotebook("AVC策略模拟")
    dummy.param_notebook = _FakeNotebook("架空线路")
    dummy._manual_doc_dir = lambda: ApproximationToolGUI._manual_doc_dir(dummy)
    dummy._current_manual_basename = lambda: ApproximationToolGUI._current_manual_basename(dummy)
    path = ApproximationToolGUI._manual_doc_path(dummy)
    assert path.name == "PowerTool_Voltage_Reactive_AVC_Strategy_Simulation_zh.md"

    dummy.language = "en"
    path_en = ApproximationToolGUI._manual_doc_path(dummy)
    assert path_en.name == "PowerTool_Voltage_Reactive_AVC_Strategy_Simulation.md"


def test_manual_doc_path_matches_new_conductor_sag_subtab() -> None:
    dummy = type("Dummy", (), {})()
    dummy.language = "en"
    dummy._current_tab_name = lambda: "Parameter Validation & Per-Unit"
    dummy.param_notebook = _FakeNotebook("Conductor Sag")
    dummy._vr_notebook = _FakeNotebook("Static Voltage Stability")
    dummy._manual_doc_dir = lambda: ApproximationToolGUI._manual_doc_dir(dummy)
    dummy._current_manual_basename = lambda: ApproximationToolGUI._current_manual_basename(dummy)
    path = ApproximationToolGUI._manual_doc_path(dummy)
    assert path.name == "PowerTool_Parameter_Validation_Conductor_Sag.md"


def test_manual_catalog_contains_conductor_sag_manual_in_both_languages() -> None:
    dummy = type("Dummy", (), {})()
    dummy._manual_doc_dir = lambda: ApproximationToolGUI._manual_doc_dir(dummy)

    dummy.language = "en"
    catalog_en = ApproximationToolGUI._manual_catalog(dummy)
    names_en = {path.name for _title, path in catalog_en}
    assert "PowerTool_Parameter_Validation_Conductor_Sag.md" in names_en

    dummy.language = "zh"
    catalog_zh = ApproximationToolGUI._manual_catalog(dummy)
    names_zh = {path.name for _title, path in catalog_zh}
    assert "PowerTool_Parameter_Validation_Conductor_Sag_zh.md" in names_zh


def test_manual_catalog_uses_app_named_bilingual_files() -> None:
    dummy = type("Dummy", (), {})()
    dummy.language = "en"
    dummy._manual_doc_dir = lambda: ApproximationToolGUI._manual_doc_dir(dummy)
    catalog = ApproximationToolGUI._manual_catalog(dummy)
    assert any(title == "PowerTool Manual Overview" for title, _ in catalog)
    assert all(path.name.startswith("PowerTool_") for _title, path in catalog)
    assert all(path.exists() for _title, path in catalog)

    dummy.language = "zh"
    catalog_zh = ApproximationToolGUI._manual_catalog(dummy)
    assert all(path.name.endswith("_zh.md") for _title, path in catalog_zh)
    assert _manual_filename("PowerTool_Overview", "en") == "PowerTool_Overview.md"
    assert _manual_filename("PowerTool_Overview", "zh") == "PowerTool_Overview_zh.md"


def test_estimate_nonperiodic_components_returns_decay_parameters() -> None:
    fs = 2000.0
    t = np.arange(0.0, 0.2, 1.0 / fs)
    signal = 1.2 + 2.5 * np.exp(-t / 0.05) + 0.1 * np.sin(2 * np.pi * 50 * t)
    dc_const, dc_decay, tau = ApproximationToolGUI._estimate_nonperiodic_components(signal, fs)
    assert 0.9 < dc_const < 1.7
    assert 2.0 < abs(dc_decay) < 3.0
    assert 0.02 < tau < 0.10
