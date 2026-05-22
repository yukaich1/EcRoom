from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(slots=True)
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: dict[str, object] = field(default_factory=dict)
    raw: dict[str, object] = field(default_factory=dict)


class LLMClient(Protocol):
    provider: str
    model: str

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 900,
    ) -> LLMResponse:
        """Return a single assistant message."""


class LLMError(RuntimeError):
    pass


def load_env_file(path: Path | str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class OpenAICompatibleClient:
    """Small chat-completions client for Mistral, OpenAI-compatible DeepSeek, and OpenAI."""

    def __init__(
        self,
        *,
        provider: str,
        api_key: str,
        model: str,
        base_url: str,
        timeout: int = 60,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 900,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMError(f"{self.provider} HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"{self.provider} request failed: {exc.reason}") from exc

        content = _extract_chat_content(raw)
        return LLMResponse(
            content=content,
            provider=self.provider,
            model=str(raw.get("model", self.model)),
            usage=dict(raw.get("usage") or {}),
            raw=raw,
        )


def client_from_env() -> LLMClient | None:
    load_env_file()
    provider = os.getenv("ECR_LLM_PROVIDER", "").strip().lower()
    if not provider:
        return None

    if provider == "mistral":
        api_key = os.getenv("MISTRAL_API_KEY", "").strip()
        if not api_key:
            raise LLMError("ECR_LLM_PROVIDER=mistral 时需要设置 MISTRAL_API_KEY。")
        return OpenAICompatibleClient(
            provider="mistral",
            api_key=api_key,
            model=os.getenv("ECR_LLM_MODEL", "mistral-small-latest"),
            base_url=os.getenv("ECR_LLM_BASE_URL", "https://api.mistral.ai/v1"),
        )

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise LLMError("ECR_LLM_PROVIDER=openai 时需要设置 OPENAI_API_KEY。")
        return OpenAICompatibleClient(
            provider="openai",
            api_key=api_key,
            model=os.getenv("ECR_LLM_MODEL", "gpt-4.1-mini"),
            base_url=os.getenv("ECR_LLM_BASE_URL", "https://api.openai.com/v1"),
        )

    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise LLMError("ECR_LLM_PROVIDER=deepseek 时需要设置 DEEPSEEK_API_KEY。")
        return OpenAICompatibleClient(
            provider="deepseek",
            api_key=api_key,
            model=os.getenv("ECR_LLM_MODEL", "deepseek-v4-pro"),
            base_url=os.getenv("ECR_LLM_BASE_URL", "https://api.deepseek.com"),
        )

    raise LLMError(f"未知 LLM provider: {provider}")


def _extract_chat_content(raw: dict[str, object]) -> str:
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMError("模型响应缺少 choices。")
    first = choices[0]
    if not isinstance(first, dict):
        raise LLMError("模型响应 choices 格式不正确。")
    message = first.get("message")
    if not isinstance(message, dict):
        raise LLMError("模型响应缺少 message。")
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "\n".join(parts).strip()
    raise LLMError("模型响应缺少文本内容。")
