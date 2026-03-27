"""本地 Agent：支持配置化模型后端、多步技能调用与时间/深度约束。"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from power_tool_skill import execute_skill_request, format_skill_catalog


DEFAULT_CONFIG_PATH = Path("local_agent_config.json")
DEFAULT_CONFIG: dict[str, Any] = {
    "provider": {
        "mode": "ollama",
        "base_url": "http://127.0.0.1:11434",
        "model": "qwen3.5:9b",
        "api_key_env": "OPENAI_API_KEY",
        "temperature": 0.2,
        "timeout_s": 180,
    },
    "agent": {
        "max_steps": 8,
        "max_duration_s": 240,
        "reasoning_depth": "deep",
    },
    "tool_policy": {
        "allow_install_packages": False,
        "preferred_packages": ["pandapower"],
    },
    "bootstrap": {
        "install_pandapower_on_first_run": False,
        "marker_file": ".powertool_bootstrap_done.json",
    },
    "pip": {
        "index_mode": "default",
        "index_url": "https://mirrors.aliyun.com/pypi/simple",
        "trusted_host": "mirrors.aliyun.com",
        "extra_pip_args": [],
    },
}


SYSTEM_TEMPLATE = """
你是 PowerTool Agent，任务是把用户问题拆解成一个或多个技能调用，再给出工程结论。

你可以使用以下技能：
{catalog}

策略约束：
- 推理深度：{reasoning_depth}
- 最多步骤：{max_steps}
- 最长总耗时：{max_duration_s} 秒
- 允许安装依赖：{allow_install_packages}
- 首选依赖包：{preferred_packages}

你必须始终返回 JSON，且只能是以下两种形态之一：
1) 调用技能
{{
  "action": "call_skill",
  "skill": "技能名",
  "args": {{ ... }},
  "reason": "为什么调用"
}}

2) 结束并回复用户
{{
  "action": "final",
  "summary": "给用户的最终回复（中文）"
}}

规则：
- 可进行多步技能调用；每次收到技能结果后再决定下一步。
- 对复杂任务要组合多个技能，必要时可先安装依赖再继续。
- 若问题涉及系统潮流/电压分布/线路负载率，优先使用 pandapower_power_flow。
- 若用户提供 pandapower 模型文件，先用 parse_pandapower_model 提取设备与拓扑，再决定后续分析步骤。
- 如果信息不足，先调用最关键技能并在最终答案说明假设。
- 绝对不要输出 JSON 之外的额外文本。
""".strip()


@dataclass
class AgentState:
    user_query: str
    history: list[dict[str, Any]] = field(default_factory=list)
    step: int = 0


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_agent_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    cfg = DEFAULT_CONFIG
    cfg_path = Path(path)
    if cfg_path.exists():
        user_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(user_cfg, dict):
            raise ValueError("local_agent_config.json 顶层必须是对象")
        cfg = _merge_dict(DEFAULT_CONFIG, user_cfg)
    return cfg


def _inject_pip_source(args: dict[str, Any], pip_cfg: dict[str, Any]) -> dict[str, Any]:
    merged = dict(args)
    mode = str(pip_cfg.get("index_mode", "default")).lower()
    if mode == "aliyun":
        merged.setdefault("index_url", str(pip_cfg.get("index_url", "https://mirrors.aliyun.com/pypi/simple")))
        merged.setdefault("trusted_host", str(pip_cfg.get("trusted_host", "mirrors.aliyun.com")))
    elif mode == "custom":
        if pip_cfg.get("index_url"):
            merged.setdefault("index_url", str(pip_cfg["index_url"]))
        if pip_cfg.get("trusted_host"):
            merged.setdefault("trusted_host", str(pip_cfg["trusted_host"]))
    merged.setdefault("extra_pip_args", list(pip_cfg.get("extra_pip_args", [])))
    return merged


def maybe_bootstrap_dependencies(config: dict[str, Any]) -> dict[str, Any]:
    bootstrap_cfg = dict(config.get("bootstrap", {}))
    if not bool(bootstrap_cfg.get("install_pandapower_on_first_run", False)):
        return {"ok": True, "skipped": True, "reason": "bootstrap disabled"}

    marker_file = Path(str(bootstrap_cfg.get("marker_file", ".powertool_bootstrap_done.json")))
    if marker_file.exists():
        return {"ok": True, "skipped": True, "reason": "already bootstrapped", "marker_file": str(marker_file)}

    pip_cfg = dict(config.get("pip", {}))
    install_args = _inject_pip_source(
        {
            "packages": ["pandapower"],
            "allow_install": True,
            "preferred_packages": ["pandapower"],
        },
        pip_cfg,
    )
    payload = {
        "skill": "install_python_packages",
        "args": install_args,
    }
    result = execute_skill_request(payload)
    if not result.get("ok"):
        return {"ok": False, "error": f"bootstrap 失败: {result.get('error', 'unknown error')}"}

    marker_file.write_text(
        json.dumps({"bootstrapped": True, "packages": ["pandapower"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"ok": True, "skipped": False, "marker_file": str(marker_file)}


def _extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\\s*", "", raw)
        raw = re.sub(r"\\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if not m:
            raise ValueError(f"模型输出不是有效 JSON: {text[:200]}")
        data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("模型输出 JSON 顶层必须是对象")
    return data


def _chat_ollama(messages: list[dict[str, str]], provider_cfg: dict[str, Any]) -> str:
    url = str(provider_cfg.get("base_url", "http://127.0.0.1:11434")).rstrip("/") + "/api/chat"
    payload = {
        "model": provider_cfg.get("model", "qwen3.5:9b"),
        "messages": messages,
        "stream": False,
        "options": {"temperature": float(provider_cfg.get("temperature", 0.2))},
    }
    timeout = float(provider_cfg.get("timeout_s", 180.0))
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return str(data["message"]["content"])


def _chat_openai_compatible(messages: list[dict[str, str]], provider_cfg: dict[str, Any]) -> str:
    base_url = str(provider_cfg.get("base_url", "https://api.openai.com/v1")).rstrip("/")
    url = base_url + "/chat/completions"
    api_key_env = str(provider_cfg.get("api_key_env", "OPENAI_API_KEY"))
    api_key = os.environ.get(api_key_env, "")
    if not api_key:
        raise ValueError(f"缺少 API key 环境变量: {api_key_env}")

    payload = {
        "model": provider_cfg.get("model", "gpt-4o-mini"),
        "messages": messages,
        "temperature": float(provider_cfg.get("temperature", 0.2)),
    }
    timeout = float(provider_cfg.get("timeout_s", 180.0))
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return str(data["choices"][0]["message"]["content"])


def _chat(messages: list[dict[str, str]], provider_cfg: dict[str, Any]) -> str:
    mode = str(provider_cfg.get("mode", "ollama")).lower()
    if mode == "ollama":
        return _chat_ollama(messages, provider_cfg)
    if mode in {"api", "openai_compatible"}:
        return _chat_openai_compatible(messages, provider_cfg)
    raise ValueError(f"不支持的 provider.mode: {mode}")


def _build_messages(state: AgentState, config: dict[str, Any]) -> list[dict[str, str]]:
    catalog = format_skill_catalog()
    agent_cfg = config["agent"]
    policy_cfg = config["tool_policy"]
    system = SYSTEM_TEMPLATE.format(
        catalog=catalog,
        reasoning_depth=str(agent_cfg.get("reasoning_depth", "deep")),
        max_steps=int(agent_cfg.get("max_steps", 8)),
        max_duration_s=float(agent_cfg.get("max_duration_s", 240)),
        allow_install_packages=bool(policy_cfg.get("allow_install_packages", False)),
        preferred_packages=", ".join(policy_cfg.get("preferred_packages", ["pandapower"])),
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    messages.append({"role": "user", "content": state.user_query})
    for item in state.history:
        if item["type"] == "thought":
            messages.append({"role": "assistant", "content": item["content"]})
        elif item["type"] == "tool":
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "技能执行结果如下（JSON）：\n"
                        + json.dumps(item["content"], ensure_ascii=False)
                        + "\n请继续输出下一步 JSON 动作。"
                    ),
                }
            )
    return messages


def run_agent_once(user_query: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_agent_config()
    provider_cfg = dict(cfg.get("provider", {}))
    agent_cfg = dict(cfg.get("agent", {}))
    policy_cfg = dict(cfg.get("tool_policy", {}))
    pip_cfg = dict(cfg.get("pip", {}))

    max_steps = int(agent_cfg.get("max_steps", 8))
    max_duration_s = float(agent_cfg.get("max_duration_s", 240.0))

    state = AgentState(user_query=user_query)
    started = time.monotonic()

    for _ in range(max_steps):
        if time.monotonic() - started > max_duration_s:
            return {
                "ok": False,
                "steps": state.step,
                "error": f"超过最长执行时间 {max_duration_s}s，未产生 final 响应",
                "trace": state.history,
            }

        state.step += 1
        messages = _build_messages(state, cfg)
        content = _chat(messages=messages, provider_cfg=provider_cfg)
        action = _extract_json(content)
        state.history.append({"type": "thought", "content": json.dumps(action, ensure_ascii=False)})

        if action.get("action") == "final":
            summary = str(action.get("summary", ""))
            return {
                "ok": True,
                "steps": state.step,
                "summary": summary,
                "trace": state.history,
            }

        if action.get("action") != "call_skill":
            return {
                "ok": False,
                "steps": state.step,
                "error": f"未知 action: {action.get('action')}",
                "trace": state.history,
            }

        skill = str(action.get("skill", ""))
        args = dict(action.get("args", {}))
        if skill == "install_python_packages":
            args.setdefault("allow_install", bool(policy_cfg.get("allow_install_packages", False)))
            args.setdefault("preferred_packages", list(policy_cfg.get("preferred_packages", ["pandapower"])))
            args = _inject_pip_source(args, pip_cfg)

        tool_result = execute_skill_request({"skill": skill, "args": args})
        state.history.append({"type": "tool", "content": tool_result})

    return {
        "ok": False,
        "steps": state.step,
        "error": f"超过最大步数 {max_steps}，未产生 final 响应",
        "trace": state.history,
    }


def repl(config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    cfg = load_agent_config(config_path)
    bootstrap = maybe_bootstrap_dependencies(cfg)
    if not bootstrap.get("ok"):
        print("依赖初始化失败：")
        print(json.dumps(bootstrap, ensure_ascii=False, indent=2))
        return

    provider = cfg["provider"]
    mode = str(provider.get("mode", "ollama"))
    model = str(provider.get("model", ""))

    print("PowerTool Agent 已启动。输入 quit 退出。")
    print(f"provider={mode} model={model}")
    while True:
        query = input("\n你> ").strip()
        if query.lower() in {"quit", "exit"}:
            print("再见。")
            break
        if not query:
            continue
        result = run_agent_once(query, config=cfg)
        if result.get("ok"):
            print("\nAgent> " + str(result.get("summary", "")))
            print(f"[steps={result['steps']}]")
        else:
            print("\nAgent 执行失败:")
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    repl()
