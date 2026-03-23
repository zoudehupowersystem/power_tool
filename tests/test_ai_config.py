from __future__ import annotations

import json
from pathlib import Path

from power_tool_ai import DEFAULT_OVERVIEW_PROMPT, PowerToolAIConfig, compose_prompt, save_ai_config


def test_compose_prompt_includes_question_tab_case_and_note() -> None:
    prompt = compose_prompt(
        question="这个频率跌落是否危险？",
        tab_name="频率动态",
        case_text="额定频率 f0 / Hz: 50\n功率缺额 ΔP_OL0 / pu: 0.08",
        screenshot_note="已自动截取当前软件界面：ui_capture.png",
    )
    assert "用户问题" in prompt
    assert "频率动态" in prompt
    assert "功率缺额 ΔP_OL0 / pu" in prompt
    assert "ui_capture.png" in prompt


def test_save_ai_config_writes_default_overview_prompt(tmp_path: Path, monkeypatch) -> None:
    import power_tool_ai

    monkeypatch.setattr(power_tool_ai, "_config_path", lambda: tmp_path / "power_tool_ai_config.json")
    path = save_ai_config(PowerToolAIConfig())
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["provider"] == "ollama"
    assert data["model"] == "qwen3.5:9b"
    assert data["system_prompt"] == DEFAULT_OVERVIEW_PROMPT
