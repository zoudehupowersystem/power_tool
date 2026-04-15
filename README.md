[中文说明 / README_zh.md](README_zh.md)

# power_tool

A lightweight desktop tool for approximate calculations in power-system engineering.

## Overview

`power_tool` consolidates engineering approximation models, parameter conversion utilities, result interpretation, and plotting into a single desktop application. It is designed for fast checks, scheme comparison, teaching demonstrations, and preliminary engineering validation.

It is not a full power-flow solver, a large-scale eigenanalysis platform, an EMT simulator, or a replacement for formal protection coordination and stability studies. Its role is to provide directionally correct, order-of-magnitude reliable, and easy-to-explain engineering results with relatively small input sets.

The project now provides both Chinese and English GUI entries with functional parity:

- Chinese GUI entry: `python power_tool.py`
- English GUI entry: `python power_tool_en.py`

## Main capabilities

The current GUI includes the following major modules:

1. Frequency dynamics
2. Electromechanical oscillation
3. Static voltage stability
4. Natural power and reactive power of transmission lines
5. Transient stability assessment
6. Small-signal analysis for SMIB systems
7. Distribution-network loop-closure analysis
8. Parameter validation and per-unit conversion
9. Short-circuit current calculation
10. COMTRADE waveform analysis

Within **Parameter Validation & Per-Unit**, the secondary notebook now contains four subpages: **Overhead Line**, **Conductor Sag**, **Two-Winding Transformer**, and **Three-Winding Transformer**. The conductor-sag page adds interactive single-span catenary analysis, including conductor temperature/current sliders and a live visual sketch of the span geometry and sag state.

The application also includes a fixed `PowerTool AI` side panel. The AI configuration is stored in `power_tool_ai_config.json`. At runtime the tool can switch between a local `ollama` backend and an API-compatible backend. When a user asks a question, the application attempts to capture the current GUI, collects the numerical summary of the active tab, and sends the combined context to the configured model.

The AI sidebar also provides a built-in manual browser. The manuals are now stored under `manuals/` with app-name-based filenames: English manuals use `PowerTool_*.md`, and Chinese manuals use `PowerTool_*_zh.md`. Clicking **Manual** opens the current-page manual and allows the user to switch to any other manual in the catalog.

## Scope and intended use

This tool is suitable for:

- fast engineering estimates during early-stage studies,
- parameter checking and nameplate-to-per-unit conversion,
- small-signal SMIB studies with modal interpretation,
- approximate operational studies such as distribution loop closure.

It is not intended to replace:

- full-network power-flow studies,
- detailed transient-stability or EMT simulation,
- large-scale eigenvalue analysis platforms,
- formal relay setting or wide-area control approval workflows.

## Repository structure

```text
power_tool/
├── power_tool.py                    # Chinese GUI entry and compatibility export layer
├── power_tool_en.py                 # English GUI entry and compatibility export layer
├── power_tool_gui.py                # Tkinter GUI, plotting, and presentation layer
├── power_tool_common.py             # Shared types, validation helpers, JSON loading
├── power_tool_approximations.py     # Approximate models for frequency, oscillation, voltage stability, natural power
├── power_tool_params.py             # Parameter validation and per-unit conversion for lines/transformers
├── power_tool_sag.py                # Single-span conductor-sag and simplified thermal-coupling analysis
├── power_tool_line_geometry.py      # Sequence-parameter calculation from conductor geometry
├── power_tool_loop_closure.py       # Approximate loop-closure analysis kernel
├── power_tool_faults.py             # Short-circuit calculation kernel
├── power_tool_stability.py          # Impact method, critical clearing estimate, equal-area criterion
├── power_tool_smib.py               # SMIB small-signal analysis kernel
├── power_tool_avc.py                # AVC strategy simulation
├── power_tool_comtrade.py           # COMTRADE parsing and waveform analysis
├── line_params_reference.json       # Reference database of typical overhead-line parameters
├── Approximate_Constants_and_Approximate_Formulas_in_Power_Systems.md    # English technical note
├── Approximate_Constants_and_Approximate_Formulas_in_Power_Systems_zh.md # Chinese technical note
├── README.md                        # English documentation
└── README_zh.md                     # Chinese documentation
```

## Environment and installation

Recommended Python version: 3.10 or newer.

Required packages:

- `numpy`
- `matplotlib`
- `tkinter` (usually included with standard Python distributions)

Example setup:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install numpy matplotlib
```

## Launching the GUI

Launch the Chinese GUI:

```bash
python power_tool.py
```

Launch the English GUI:

```bash
python power_tool_en.py
```

You can also launch the GUI module directly; by default it starts in Chinese:

```bash
python power_tool_gui.py
```

## Tests

Run the test suite with:

```bash
python -m pytest -q
```

Using `python -m pytest -q` is preferred because it keeps the import path consistent across environments.

## Notes on bilingual support

The English and Chinese GUIs are intended to remain functionally identical. The implementation keeps the computational kernels unchanged and adds bilingual presentation support at the GUI layer, including translated labels, prompts, titles, message boxes, and documentation entry points.

Code comments and docstrings in the maintained Python modules are written in bilingual English/Chinese form.

## Using the project as a calculation library

The computational kernels can be imported directly from the dedicated modules, for example:

- `power_tool_approximations.py`
- `power_tool_stability.py`
- `power_tool_smib.py`
- `power_tool_params.py`
- `power_tool_faults.py`
- `power_tool_loop_closure.py`

The compatibility entry layers `power_tool.py` and `power_tool_en.py` also re-export the major symbols, but direct module imports are preferable for long-term maintainability.

## Additional documentation

`README_zh.md` remains the more detailed user manual and includes the full Chinese walkthrough of the GUI pages, input fields, plots, engineering assumptions, and example workflows.

## Technical note

The repository also includes a bilingual technical note on engineering constants and approximation formulas:

- Chinese version: `Approximate_Constants_and_Approximate_Formulas_in_Power_Systems_zh.md`
- English version: `Approximate_Constants_and_Approximate_Formulas_in_Power_Systems.md`
