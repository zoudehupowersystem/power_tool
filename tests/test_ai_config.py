from __future__ import annotations

import json
from pathlib import Path

from power_tool_ai import (
    DEFAULT_OVERVIEW_PROMPT,
    PowerToolAIConfig,
    _ask_ollama,
    _extract_ollama_text,
    api_key_status,
    compose_prompt,
    load_ai_config,
    save_ai_config,
)


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


def test_extract_ollama_text_supports_message_and_response_shapes() -> None:
    assert _extract_ollama_text({"message": {"content": "本地回答"}}) == "本地回答"
    assert _extract_ollama_text({"response": "兼容回答"}) == "兼容回答"


def test_ask_ollama_retries_without_image_when_first_response_is_empty(monkeypatch, tmp_path: Path) -> None:
    import power_tool_ai

    calls: list[tuple[str, str | None]] = []

    def fake_http_json_lines(url: str, payload: dict, headers: dict, timeout: float) -> list[dict]:
        user_message = payload["messages"][1]
        images = user_message.get("images")
        calls.append((user_message["content"], images[0] if images else None))
        if images:
            return [{"message": {"content": ""}, "done": True}]
        return [{"message": {"content": "回退后已有文本回答"}, "done": True}]

    image_path = tmp_path / "capture.png"
    image_path.write_bytes(b"fake-image")
    monkeypatch.setattr(power_tool_ai, "_http_json_lines", fake_http_json_lines)

    content = _ask_ollama(PowerToolAIConfig(), "请分析当前算例", image_path)

    assert content == "回退后已有文本回答"
    assert len(calls) == 2
    assert calls[0][1] is not None
    assert calls[1][1] is None
    assert "未返回可用的图像理解文本" in calls[1][0]


def test_ask_ollama_aggregates_streamed_content(monkeypatch) -> None:
    import power_tool_ai

    seen = {}

    def fake_http_json_lines(url: str, payload: dict, headers: dict, timeout: float) -> list[dict]:
        seen["stream"] = payload.get("stream")
        seen["think"] = payload.get("think")
        return [
            {"message": {"thinking": "先思考"}, "done": False},
            {"message": {"content": "第一段"}, "done": False},
            {"message": {"content": "，第二段"}, "done": True},
        ]

    monkeypatch.setattr(power_tool_ai, "_http_json_lines", fake_http_json_lines)

    assert _ask_ollama(PowerToolAIConfig(), "测试", None) == "第一段，第二段"
    assert seen["stream"] is True
    assert seen["think"] is False


def test_ask_ollama_can_enable_thinking_mode(monkeypatch) -> None:
    import power_tool_ai

    seen = {}

    def fake_http_json_lines(url: str, payload: dict, headers: dict, timeout: float) -> list[dict]:
        seen["think"] = payload.get("think")
        return [{"message": {"content": "思考模式回答"}, "done": True}]

    monkeypatch.setattr(power_tool_ai, "_http_json_lines", fake_http_json_lines)

    assert _ask_ollama(PowerToolAIConfig(), "测试", None, think=True) == "思考模式回答"
    assert seen["think"] is True
