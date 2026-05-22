from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from evolving_creative_room.llm import ChatMessage, LLMClient, LLMError, LLMResponse
from evolving_creative_room.models import new_id, utc_now_iso


@dataclass(slots=True)
class LLMCallRecord:
    provider: str
    model: str
    success: bool
    duration_ms: int
    prompt_chars: int
    completion_chars: int = 0
    usage: dict[str, object] = field(default_factory=dict)
    error: str = ""
    call_id: str = field(default_factory=lambda: new_id("call"))
    created_at: str = field(default_factory=utc_now_iso)


class CallLogStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.path = self.root / "observability" / "llm_calls.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: LLMCallRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def list(self, limit: int = 80) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        rows.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return rows[:limit]

    def summary(self) -> dict[str, object]:
        rows = self.list(limit=1000)
        total = len(rows)
        success = sum(1 for row in rows if row.get("success"))
        prompt_tokens = sum(int((row.get("usage") or {}).get("prompt_tokens", 0) or 0) for row in rows)
        completion_tokens = sum(int((row.get("usage") or {}).get("completion_tokens", 0) or 0) for row in rows)
        return {
            "total_calls": total,
            "success_calls": success,
            "failure_calls": total - success,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }


class ObservedLLMClient:
    """给 LLM client 增加本地调用日志。"""

    def __init__(self, inner: LLMClient, store: CallLogStore) -> None:
        self.inner = inner
        self.store = store
        self.provider = inner.provider
        self.model = inner.model

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 900,
    ) -> LLMResponse:
        started = time.perf_counter()
        prompt_chars = sum(len(item.content) for item in messages)
        try:
            response = self.inner.chat(messages, temperature=temperature, max_tokens=max_tokens)
            self.store.append(
                LLMCallRecord(
                    provider=response.provider,
                    model=response.model,
                    success=True,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    prompt_chars=prompt_chars,
                    completion_chars=len(response.content),
                    usage=response.usage,
                )
            )
            return response
        except LLMError as exc:
            self.store.append(
                LLMCallRecord(
                    provider=self.provider,
                    model=self.model,
                    success=False,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    prompt_chars=prompt_chars,
                    error=str(exc),
                )
            )
            raise
