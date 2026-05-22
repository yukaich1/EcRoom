from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from evolving_creative_room.models import new_id, utc_now_iso


@dataclass(slots=True)
class MetricEvent:
    name: str
    value: float = 1.0
    session_id: str = ""
    project_id: str = "default"
    metadata: dict[str, object] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: new_id("metric"))
    created_at: str = field(default_factory=utc_now_iso)


class MetricStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.path = self.root / "observability" / "metrics.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        name: str,
        *,
        value: float = 1.0,
        session_id: str = "",
        project_id: str = "default",
        metadata: dict[str, object] | None = None,
    ) -> MetricEvent:
        event = MetricEvent(
            name=name,
            value=value,
            session_id=session_id,
            project_id=project_id,
            metadata=metadata or {},
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return event

    def list(self, limit: int = 200) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        rows = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return rows[:limit]

    def summary(self) -> dict[str, object]:
        rows = self.list(limit=2000)
        counts: dict[str, float] = {}
        for row in rows:
            name = str(row.get("name", "unknown"))
            counts[name] = counts.get(name, 0.0) + float(row.get("value", 1) or 0)

        finalized = counts.get("session_finalized", 0.0)
        success = counts.get("session_success", 0.0)
        return {
            "total_events": len(rows),
            "counts": counts,
            "reusable_success_rate": round(success / finalized, 4) if finalized else 0,
            "learning_confirmation_rate": _rate(
                counts.get("learning_confirmed", 0.0),
                counts.get("learning_candidate_created", 0.0),
            ),
        }


def _rate(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0
    return round(numerator / denominator, 4)
