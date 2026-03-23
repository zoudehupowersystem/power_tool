from __future__ import annotations

import json
from pathlib import Path

from power_tool_ai import DEFAULT_OVERVIEW_PROMPT, PowerToolAIConfig, api_key_status, compose_prompt, load_ai_config, save_ai_config


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


def test_save_ai_config_uses_nested_provider_api_ollama_shape(tmp_path: Path, monkeypatch) -> None:
    import power_tool_ai

    monkeypatch.setattr(power_tool_ai, "_config_path", lambda: tmp_path / "power_tool_ai_config.json")
    path = save_ai_config(PowerToolAIConfig())
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["provider"]["mode"] == "ollama"
    assert data["api"]["env_key_name"] == "DASHSCOPE_API_KEY"
    assert data["ollama"]["default_model"] == "qwen3.5:9b"
    assert data["system_prompt"] == DEFAULT_OVERVIEW_PROMPT
    assert "api_key" not in data


def test_load_ai_config_reads_nested_shape(tmp_path: Path, monkeypatch) -> None:
    import power_tool_ai

    path = tmp_path / "power_tool_ai_config.json"
    path.write_text(
        json.dumps(
            {
                "provider": {"mode": "api"},
                "api": {
                    "env_key_name": "CUSTOM_KEY",
                    "base_url": "https://example.com/v1",
                    "default_model": "demo-model",
                    "models": ["demo-model", "demo-vl"],
                    "temperature": 0.5,
                    "timeout": 120,
                },
                "ollama": {
                    "host": "http://localhost:11434",
                    "default_model": "qwen3.5:14b",
                    "models": ["qwen3.5:14b"],
                    "timeout": 60,
                },
                "system_prompt": "nested prompt",
                "max_tokens": 256,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(power_tool_ai, "_config_path", lambda: path)
    config = load_ai_config()
    assert config.provider.mode == "api"
    assert config.api.env_key_name == "CUSTOM_KEY"
    assert config.api.base_url == "https://example.com/v1"
    assert config.api.default_model == "demo-model"
    assert config.ollama.default_model == "qwen3.5:14b"
    assert config.system_prompt == "nested prompt"
    assert config.max_tokens == 256


def test_api_key_status_reads_environment_variable(monkeypatch) -> None:
    config = PowerToolAIConfig()
    monkeypatch.setenv("DASHSCOPE_API_KEY", "secret")
    assert api_key_status(config).endswith("已设置")
