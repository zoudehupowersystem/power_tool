"""PowerTool AI 配置、提示词与请求适配。"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_OVERVIEW_PROMPT = (
    "你是 PowerTool AI，是内嵌在 PowerTool 电力系统工程近似计算工具中的问答助手。"
    "该软件用于电力系统分析、设备参数折算、教学演示与方案前期校核，覆盖频率动态、机电振荡、"
    "静态电压稳定、线路自然功率、暂稳评估、SMIB 小扰动、配电网合环、参数校核与标幺值、"
    "短路电流、COMTRADE 录波等模块。回答时请优先结合当前界面截图、当前算例数值、"
    "软件定位与工程近似边界，给出结构化、可执行、面向电力工程人员的中文说明；"
    "如果发现输入不完整、量纲可疑、结果超出近似模型适用范围，要明确提示。"
)


@dataclass
class ProviderSettings:
    mode: str = "ollama"


@dataclass
class APISettings:
    env_key_name: str = "DASHSCOPE_API_KEY"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    default_model: str = "qwen3.5-27b"
    models: list[str] = field(default_factory=lambda: ["qwen3.5-27b", "Qwen3.5-Plus", "qwen3.5-35b-a3b"])
    temperature: float = 0.7
    timeout: float = 600.0


@dataclass
class OllamaSettings:
    host: str = "http://127.0.0.1:11434"
    default_model: str = "qwen3.5:9b"
    models: list[str] = field(default_factory=lambda: ["qwen3.5:9b", "qwen3-vl:8b"])
    timeout: float = 600.0


@dataclass
class PowerToolAIConfig:
    provider: ProviderSettings = field(default_factory=ProviderSettings)
    api: APISettings = field(default_factory=APISettings)
    ollama: OllamaSettings = field(default_factory=OllamaSettings)
    system_prompt: str = DEFAULT_OVERVIEW_PROMPT
    max_tokens: int = 1200


class PowerToolAIError(RuntimeError):
    """AI 交互异常。"""


def _config_path() -> Path:
    return Path(__file__).resolve().with_name("power_tool_ai_config.json")


def _clean_models(values: Any, fallback: list[str]) -> list[str]:
    if isinstance(values, str):
        items = [item.strip() for item in values.replace("\n", ",").split(",") if item.strip()]
        return items or fallback
    if isinstance(values, list):
        items = [str(item).strip() for item in values if str(item).strip()]
        return items or fallback
    return fallback


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _chat_completions_url(base_url: str) -> str:
    base = _normalize_base_url(base_url)
    return base if base.endswith("/chat/completions") else f"{base}/chat/completions"


def _ollama_chat_url(host: str) -> str:
    base = _normalize_base_url(host)
    return base if base.endswith("/api/chat") else f"{base}/api/chat"


def _migrate_legacy_config(raw: dict[str, Any]) -> PowerToolAIConfig:
    provider_mode = str(raw.get("provider", "ollama")) if not isinstance(raw.get("provider"), dict) else str(dict(raw["provider"]).get("mode", "ollama"))
    api_model = str(raw.get("api_model", APISettings().default_model))
    ollama_model = str(raw.get("model", OllamaSettings().default_model))
    return PowerToolAIConfig(
        provider=ProviderSettings(mode=provider_mode),
        api=APISettings(
            env_key_name="DASHSCOPE_API_KEY",
            base_url=str(raw.get("api_url", APISettings().base_url)).removesuffix("/chat/completions"),
            default_model=api_model,
            models=[api_model],
            temperature=float(raw.get("temperature", APISettings().temperature)),
            timeout=float(raw.get("timeout_s", APISettings().timeout)),
        ),
        ollama=OllamaSettings(
            host=str(raw.get("ollama_url", _ollama_chat_url(OllamaSettings().host))).removesuffix("/api/chat"),
            default_model=ollama_model,
            models=[ollama_model],
            timeout=float(raw.get("timeout_s", OllamaSettings().timeout)),
        ),
        system_prompt=str(raw.get("system_prompt", DEFAULT_OVERVIEW_PROMPT)),
        max_tokens=int(raw.get("max_tokens", 1200)),
    )


def load_ai_config() -> PowerToolAIConfig:
    path = _config_path()
    if not path.exists():
        config = PowerToolAIConfig()
        save_ai_config(config)
        return config
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if "api" not in raw or "ollama" not in raw:
        config = _migrate_legacy_config(raw)
        save_ai_config(config)
        return config
    provider_raw = dict(raw.get("provider", {}))
    api_raw = dict(raw.get("api", {}))
    ollama_raw = dict(raw.get("ollama", {}))
    return PowerToolAIConfig(
        provider=ProviderSettings(mode=str(provider_raw.get("mode", "ollama"))),
        api=APISettings(
            env_key_name=str(api_raw.get("env_key_name", "DASHSCOPE_API_KEY")),
            base_url=_normalize_base_url(str(api_raw.get("base_url", APISettings().base_url))),
            default_model=str(api_raw.get("default_model", APISettings().default_model)),
            models=_clean_models(api_raw.get("models"), APISettings().models),
            temperature=float(api_raw.get("temperature", APISettings().temperature)),
            timeout=float(api_raw.get("timeout", APISettings().timeout)),
        ),
        ollama=OllamaSettings(
            host=_normalize_base_url(str(ollama_raw.get("host", OllamaSettings().host))),
            default_model=str(ollama_raw.get("default_model", OllamaSettings().default_model)),
            models=_clean_models(ollama_raw.get("models"), OllamaSettings().models),
            timeout=float(ollama_raw.get("timeout", OllamaSettings().timeout)),
        ),
        system_prompt=str(raw.get("system_prompt", DEFAULT_OVERVIEW_PROMPT)),
        max_tokens=int(raw.get("max_tokens", 1200)),
    )


def save_ai_config(config: PowerToolAIConfig) -> Path:
    path = _config_path()
    with path.open("w", encoding="utf-8") as f:
        json.dump(asdict(config), f, ensure_ascii=False, indent=2)
    return path


def config_path() -> Path:
    return _config_path()


def api_key_status(config: PowerToolAIConfig) -> str:
    name = config.api.env_key_name.strip() or "DASHSCOPE_API_KEY"
    return f"环境变量 {name}: {'已设置' if os.getenv(name) else '未设置'}"


def encode_image_base64(image_path: str | Path) -> str:
    data = Path(image_path).read_bytes()
    return base64.b64encode(data).decode("ascii")


def compose_prompt(question: str, tab_name: str, case_text: str, screenshot_note: str) -> str:
    case_block = case_text.strip() if case_text.strip() else "当前页暂未提取到数值算例。"
    return (
        f"用户问题：\n{question.strip()}\n\n"
        f"当前模块：{tab_name}\n\n"
        f"界面截图说明：{screenshot_note.strip() or '未提供额外说明。'}\n\n"
        f"当前算例数值：\n{case_block}\n\n"
        "请基于上述信息回答，并在必要时：\n"
        "1. 先概括当前模块在 PowerTool 中的用途；\n"
        "2. 结合当前输入判断关键量纲、边界条件与结果趋势；\n"
        "3. 给出下一步操作建议或复核建议；\n"
        "4. 如果截图缺失或数值不足，明确说明你的假设。"
    )


def ask_ai(config: PowerToolAIConfig, question: str, tab_name: str, case_text: str,
           screenshot_note: str, screenshot_path: str | Path | None = None) -> str:
    prompt = compose_prompt(question, tab_name, case_text, screenshot_note)
    if config.provider.mode == "ollama":
        return _ask_ollama(config, prompt, screenshot_path)
    if config.provider.mode == "api":
        return _ask_openai_compatible(config, prompt, screenshot_path)
    raise PowerToolAIError(f"不支持的 AI 提供方式：{config.provider.mode}")


def _http_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_s: float) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PowerToolAIError(f"HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise PowerToolAIError(f"网络请求失败：{exc.reason}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise PowerToolAIError(f"AI 返回了非 JSON 内容：{body[:300]}") from exc


def _ask_ollama(config: PowerToolAIConfig, prompt: str, screenshot_path: str | Path | None) -> str:
    user_message: dict[str, Any] = {"role": "user", "content": prompt}
    if screenshot_path:
        user_message["images"] = [encode_image_base64(screenshot_path)]
    payload = {
        "model": config.ollama.default_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": config.system_prompt},
            user_message,
        ],
        "options": {
            "temperature": 0.2,
            "num_predict": config.max_tokens,
        },
    }
    data = _http_json(_ollama_chat_url(config.ollama.host), payload, {}, config.ollama.timeout)
    message = data.get("message") or {}
    content = str(message.get("content", "")).strip()
    if not content:
        raise PowerToolAIError("Ollama 未返回有效文本内容。")
    return content


def _ask_openai_compatible(config: PowerToolAIConfig, prompt: str, screenshot_path: str | Path | None) -> str:
    env_name = config.api.env_key_name.strip() or "DASHSCOPE_API_KEY"
    api_key = os.getenv(env_name, "").strip()
    if not api_key:
        raise PowerToolAIError(f"当前为 API 模式，但环境变量 {env_name} 未设置。")
    user_content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if screenshot_path:
        image_b64 = encode_image_base64(screenshot_path)
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}})
    payload = {
        "model": config.api.default_model,
        "temperature": config.api.temperature,
        "max_tokens": config.max_tokens,
        "messages": [
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": user_content},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    data = _http_json(_chat_completions_url(config.api.base_url), payload, headers, config.api.timeout)
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise PowerToolAIError("API 未返回 choices 字段。")
    message = dict(choices[0].get("message", {}))
    content = message.get("content", "")
    if isinstance(content, list):
        text_parts = [str(item.get("text", "")) for item in content if isinstance(item, dict)]
        content = "\n".join(part for part in text_parts if part)
    content = str(content).strip()
    if not content:
        raise PowerToolAIError("API 未返回有效文本内容。")
    return content


__all__ = [
    "APISettings",
    "DEFAULT_OVERVIEW_PROMPT",
    "OllamaSettings",
    "PowerToolAIConfig",
    "PowerToolAIError",
    "ProviderSettings",
    "api_key_status",
    "ask_ai",
    "compose_prompt",
    "config_path",
    "load_ai_config",
    "save_ai_config",
]
