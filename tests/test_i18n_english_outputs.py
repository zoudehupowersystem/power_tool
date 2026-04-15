"""Regression tests for English-runtime translation of user-facing result text. / 英文运行时用户可见结果文本的回归测试。"""

from __future__ import annotations

import textwrap
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from power_tool_i18n import display_text, translate_text


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _assert_fully_english(text: str) -> None:
    translated = translate_text(text, "en")
    assert not _contains_cjk(translated), translated


def test_line_parameter_and_geometry_notes_are_fully_translated() -> None:
    sample = textwrap.dedent(
        """
        Notes:
        假设: 单回Overhead Line, 三相conductor型号一致并按三段完全换位平均; 串联参数用复深度近似计及soil resistivity, 大地回路Resistance/Reactance已包含在序阻抗内; 对地capacitance/Susceptance采用镜像法电位系数矩阵, 介质电导与土壤介电损耗未计. CurrentCalculate未考虑shield wire屏蔽效应. 四分裂conductor按正方形排列近似.
        ══ Physical-unit values (π equivalent, converted)══════════════════════
         Total resistance R = 1.601686 Ω
         Total reactance X = 54.595000 Ω
         Half shunt susceptance to ground B/2 = 0.00042202 S
         Surge impedance Zc = 254.3286 Ω

        ══ Per-Unit(Sbase=100 MVA, Ubase=500 kV)══════
         基准阻抗 Zbase = 2500.0000 Ω, 基准Admittance Ybase = 0.00040000 S
         R_pu = 0.00064067 pu
         X_pu = 0.02183800 pu
         B/2_pu = 1.05504891 pu

        ══ Parameter Validation ═══════════════════════════════════════
        ✓ 所有参数均在合理范围内.
        """
    ).strip()
    translated = translate_text(sample, "en")
    assert "Assumptions:" in translated
    assert "single-circuit overhead line" in translated
    assert "Base impedance Zbase" in translated
    assert "Base admittance Ybase" in translated
    assert "All parameters are within reasonable ranges" in translated
    assert not _contains_cjk(translated), translated


def test_loop_closure_report_is_fully_translated() -> None:
    sample = textwrap.dedent(
        """
        ══ Approximate loop-closure analysis for distribution systems ══════════════════════
        Number of connection points N = 7, Closure point = Tie point(No. 4)
        U1 = 10 kV, U2 = 10 kV, φ = 14°
        ΔU = 2.4374 kV(Line-voltage phasor difference across the closure point)
        ZΣ = 1.1300 + j4.2000 Ω, |ZΣ| = 4.3494 Ω, φz = 74.941°
        I_loop = 323.55 ∠ +22.06° A
        τ = 0.011831 s, 2τ = 0.023662 s
        Left endloop closure前/后 = 313.35 / 166.04 A
        Right endloop closure前/后 = 354.16 / 670.99 A
        Instantaneous peak: loop current 647.90 A, left-side total current 508.82 A, right-side total current 1130.26 A
        Allowed steady-state ampacity limit = 663.00 A
        Conclusion:There are 1 sections whose steady-state current exceeds the allowed ampacity.

        ── Steady-state currents of all sections ───────────────────────────────
        Section No. range 长度/km loop closure前/A loop closure后/A Angle/° Status
        --------------------------------------------------------------------------------------
         1 Left end->A 1.375 313.35 166.04 -86.43 Normal
         8 F->Right end 1.375 354.16 670.99 13.61 Over limit

        Notes:
        本模块是Distribution Loop-Closure的工程近似工具: 各connection point以净线Current表示, 正Value表示负荷, 负Value表示分布式电源回送; loop closure前默认同侧connection point具有统一功率因数. loop closure暂态采用单一 R-L 回路叠加法, 适loop closure流, Current分布与保护配合的快速判断, 不等价于 PSCAD/EMTP 或 Simulink 的详细电磁暂态仿真. 统一功率因数按 0.9900(Lagging)处理.
        """
    ).strip()
    translated = translate_text(sample, "en")
    assert "Left-end current before/after closure" in translated
    assert "Right-end current before/after closure" in translated
    assert "Section No." in translated and "Before closure/A" in translated
    assert "engineering approximation tool for distribution loop closure" in translated
    assert "The uniform power factor is taken as 0.9900 (Lagging)." in translated
    assert not _contains_cjk(translated), translated


def test_smib_report_and_notes_are_fully_translated() -> None:
    sample = textwrap.dedent(
        """
        Configuration: Sixth-order Generator + AVR + PSS
        State dimension:12
        Stability:Stable(max Re(λ) = -0.738609 1/s)

        ── 平衡点(以infinite bus为angle参考)────────────────
        V∞ = 0.900810 pu
        Vt = 1.000000 ∠ 28.342914° pu
        P + jQ = 0.900000 + j0.436002 pu
        δ0 = 70.144213°
        pm0 = 0.903000 pu, vf0 = 2.420702 pu
        id0 = 0.924917 pu, iq0 = 0.380298 pu
        vd0 = 0.666549 pu, vq0 = 0.745461 pu
        Xline,eq = 0.325175 pu, Xnet = 0.475175 pu
        reference-angle shift = +0.000000°

        ── Least-damped mode ───────────────────────────────────
        λ_dom = -1.812534 + j7.222931 1/s
        f_dom = 1.149565 Hz, ζ = 24.340 %
        Dominant participating states:e'q 38.3%, e''q 23.0%, x_ll1 13.7%, ω 13.6%

        ── Mode table(仅列 Im(λ) ≥ 0 的independent modes)──────────────
        No. eigenvalue λ / (1/s) f / Hz ζ / % 类型
        ----------------------------------------------------------------------
         1 -0.738609 0.0000 - real root
         5 -1.812534 + j7.222931 1.1496 24.340 Oscillation

        Notes:
        模型采用 Kundur 示例 13.2 对应的六阶同步机, AVR III 与 PSS II 结构.网络按 xT + (xline1 ∥ xline2) 的 SMIB equivalent处理, 并在平衡点处对非线性 ODE 进行中心差分数Value线性化.eigenvalue以 1/s 给出, damping ratio按 -σ/|λ| Calculate; 参与因子用于识别主导Status.
        """
    ).strip()
    translated = translate_text(sample, "en")
    assert "Operating point (with the infinite bus as the angle reference)" in translated
    assert "Mode table (only independent modes with Im(λ) ≥ 0)" in translated
    assert "Type" in translated
    assert "The model uses the sixth-order synchronous generator from Kundur Example 13.2" in translated
    assert "participation factors are used to identify the dominant states" in translated
    assert not _contains_cjk(translated), translated




def test_natural_power_result_and_notes_are_fully_translated() -> None:
    sample = textwrap.dedent(
        """
        波阻抗 Z_c = 250.000000 Ω
        自然功率 P_N = 1000.000000 MW
        线路无功估算 ΔQ_L = -122.400000 Mvar
        运行区间判断：总体发无功（净容性）

        Notes:
        该estimated最适用于RatedVoltage附近, 无损或低损, 无复杂串并联补偿的超高压长Line. 实际Voltage偏离RatedValue时, Line充电Reactive Power应按 V² 修正.
        """
    ).strip()
    translated = translate_text(sample, "en")
    assert "Surge impedance Z_c" in translated
    assert "Natural power P_N" in translated
    assert "Estimated line reactive power ΔQ_L" in translated
    assert "Net reactive injection (net capacitive)" in translated
    assert "This estimate is most suitable for EHV/UHV long lines operating near rated voltage" in translated
    assert "the line charging reactive power should be corrected in proportion to V²" in translated
    assert not _contains_cjk(translated), translated

def test_stability_voltage_electromechanical_and_frequency_reports_are_fully_translated() -> None:
    sample = textwrap.dedent(
        """
        Stability assessment:[Stable]
        margin = +363.42 %

        ── 关键angle ──────────────────────
        Pre-fault equilibrium angle δ0 = 33.056°
        Fault-clearing angle δc = 46.016°
        Unstable equilibrium angle δu = 146.944°
        Actual maximum swing angle δmax= 69.894°

        ── 等面积 ────────────────────────
        Accelerating area Aacc = 0.203575 pu·rad
        Available decelerating area Adec = 0.943410 pu·rad
        Actual decelerating area Adec_act= 0.203575 pu·rad

        ── 极限clearing ──────────────────────
        Critical clearing angle δcr = 75.755°
        Critical clearing time tcr = 0.2179 s
        Current clearing time Δt = 0.1200 s (< tcr OK)

        Notes:
        Critical clearing angle由闭式公式Calculate(需 Pmax_post ≠ Pmax_fault); Critical clearing time由 RK4 数Valueintegral摆动方程得到.margin = (Available decelerating area − Accelerating area) / Accelerating area × 100 %.本模型为单机无穷大, 忽略阻尼, mechanical power恒定的经典假设.

        sinφ = 0.312250
        Maximum transferable active power P_L,max = 1.131168 pu
        Converted physical-unit value = 113.116793 MW
        receiving-endminimum voltage(相对送terminal voltage归一化)V_min/U_g = 0.617272 pu
        receiving-endminimum voltage(与 U_g 同一基准)V_min = 0.617272 pu

        Notes:
        适用前提: 二节点equivalent, 送terminal voltage刚性, 忽略Resistance, 负荷功率因数近似恒定. 若System存在显著Resistance, 分接头动作, 复杂Reactive Power补偿或多节点耦合, 应改用power flow/连续power flow/QV-PV analysis.

        Initial power angle δ0 = 23.132396 °
        Synchronizing torque coefficient K_s = 1.872639 pu/rad (as defined by the approximation used in this article)
        Natural angular frequency ω_n = 8.085013 rad/s
        electromechanical oscillation frequency f_n = 1.286770 Hz

        Notes:
        该公式给出的是Small-Signal主导机电模态Frequency的近似Value. 阻尼, 参与因子以及互联System模态耦合仍需eigenvalueanalysis或时域仿真.

        damping type: Underdamped
        α = 0.175000 1/s
        Ω = 0.315238 rad/s
        初始Frequency变化率 RoCoF = -0.010000 pu/s = -0.500000 Hz/s
        steady-state frequency deviation Δf∞ = -0.015385 pu = -0.769231 Hz
        Time of the frequency minimum t_m = 5.233937 s
        minimum frequency deviation Δf_min = -0.025118 pu = -1.255906 Hz
        minimum frequency f_min = 48.744094 Hz

        Notes:
        Underdamped: 存在典型"先下后回"的FrequencyMinimum point. minimum-point time采用 atan2 形式, 避免普通 arctan 造成象限选错.
        """
    ).strip()
    translated = translate_text(sample, "en")
    assert "Key angles" in translated
    assert "Equal-area quantities" in translated
    assert "Critical clearing" in translated
    assert "Minimum receiving-end voltage (normalized to the sending-end voltage)" in translated
    assert "This formula gives an approximate value of the dominant electromechanical modal frequency" in translated
    assert "Initial frequency rate of change RoCoF" in translated
    assert "Underdamped: a typical frequency nadir exists" in translated
    assert not _contains_cjk(translated), translated


def test_residual_widget_labels_display_in_english() -> None:
    labels = {
        "AVR 传递函数结构图": "AVR transfer-function block diagram",
        "PSS 传递函数结构图": "PSS transfer-function block diagram",
        "单分裂导线电阻": "Single-subconductor resistance",
        "分裂间距": "Bundle spacing",
        "额定载流量": "Rated ampacity",
        "合环点编号": "Closure point No.",
        "系统频率 / Hz": "System frequency / Hz",
    }
    for source, expected in labels.items():
        assert display_text(source, "en") == expected
