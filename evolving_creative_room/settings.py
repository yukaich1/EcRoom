from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    "profile": {
        "nickname": "创作者",
        "bio": "正在和 EcRoom 一起打磨内容。",
        "avatar_data": "",
    },
    "llm": {
        "provider": "",
        "model": "",
        "base_url": "",
        "api_keys": {},
    },
    "memory_policy": {
        "candidate_limit": 3,
        "min_confidence": 0.35,
        "complete_only": True,
    },
    "harness": {
        "record_skill_runs": True,
        "auto_propose": True,
        "min_eval_cases": 3,
    },
}

PROVIDER_DEFAULTS = {
    "mistral": {"model": "mistral-small-latest", "base_url": "https://api.mistral.ai/v1"},
    "openai": {"model": "gpt-4.1-mini", "base_url": "https://api.openai.com/v1"},
    "deepseek": {"model": "deepseek-v4-pro", "base_url": "https://api.deepseek.com"},
}


class UserSettingsStore:
    """Local user settings. API keys stay inside the workspace and are never returned to the frontend."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.path = self.root / "user_settings.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return deepcopy(DEFAULT_SETTINGS)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return _merge_defaults(data)

    def public_view(self) -> dict[str, Any]:
        data = self.read()
        llm = data.get("llm", {})
        keys = llm.get("api_keys", {}) if isinstance(llm.get("api_keys"), dict) else {}
        return {
            "profile": data.get("profile", {}),
            "llm": {
                "provider": llm.get("provider", ""),
                "model": llm.get("model", ""),
                "base_url": llm.get("base_url", ""),
                "has_api_key": bool(keys.get(str(llm.get("provider", "")).lower())),
            },
            "providers": PROVIDER_DEFAULTS,
            "memory_policy": data.get("memory_policy", {}),
            "harness": data.get("harness", {}),
        }

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self.read()
        profile = payload.get("profile")
        if isinstance(profile, dict):
            current = data.setdefault("profile", {})
            for key in ("nickname", "bio", "avatar_data"):
                if key in profile:
                    current[key] = str(profile.get(key, "")).strip()

        llm = payload.get("llm")
        if isinstance(llm, dict):
            current_llm = data.setdefault("llm", {})
            provider = str(llm.get("provider", current_llm.get("provider", ""))).strip().lower()
            if provider:
                current_llm["provider"] = provider
            defaults = PROVIDER_DEFAULTS.get(provider, {})
            if "model" in llm:
                current_llm["model"] = str(llm.get("model", "")).strip()
            elif provider and not current_llm.get("model"):
                current_llm["model"] = defaults.get("model", "")
            if "base_url" in llm:
                current_llm["base_url"] = str(llm.get("base_url", "")).strip()
            elif provider and not current_llm.get("base_url"):
                current_llm["base_url"] = defaults.get("base_url", "")

            api_key = str(llm.get("api_key", "")).strip()
            if api_key and provider:
                keys = current_llm.setdefault("api_keys", {})
                keys[provider] = api_key

        memory_policy = payload.get("memory_policy")
        if isinstance(memory_policy, dict):
            current_memory = data.setdefault("memory_policy", {})
            if "candidate_limit" in memory_policy:
                current_memory["candidate_limit"] = _bounded_int(memory_policy.get("candidate_limit"), 1, 8, 3)
            if "min_confidence" in memory_policy:
                current_memory["min_confidence"] = _bounded_float(memory_policy.get("min_confidence"), 0.0, 1.0, 0.35)
            if "complete_only" in memory_policy:
                current_memory["complete_only"] = bool(memory_policy.get("complete_only"))

        harness = payload.get("harness")
        if isinstance(harness, dict):
            current_harness = data.setdefault("harness", {})
            if "record_skill_runs" in harness:
                current_harness["record_skill_runs"] = bool(harness.get("record_skill_runs"))
            if "auto_propose" in harness:
                current_harness["auto_propose"] = bool(harness.get("auto_propose"))
            if "min_eval_cases" in harness:
                current_harness["min_eval_cases"] = _bounded_int(harness.get("min_eval_cases"), 1, 20, 3)

        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.public_view()


def _merge_defaults(data: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(DEFAULT_SETTINGS)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    merged.setdefault("llm", {}).setdefault("api_keys", {})
    return merged


def _bounded_int(value: Any, minimum: int, maximum: int, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, number))


def _bounded_float(value: Any, minimum: float, maximum: float, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return round(max(minimum, min(maximum, number)), 4)
