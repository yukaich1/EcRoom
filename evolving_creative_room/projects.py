from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from evolving_creative_room.models import ProjectRecord, utc_now_iso


class ProjectStore:
    """本地项目空间。"""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.path = self.root / "projects.jsonl"
        self.root.mkdir(parents=True, exist_ok=True)
        self.ensure_default()

    def ensure_default(self) -> None:
        if self.path.exists() and self.path.read_text(encoding="utf-8").strip():
            return
        self._append(
            ProjectRecord(
                project_id="default",
                name="默认项目",
                description="未归类的创作会话、记忆和资料。",
                tags=["default"],
            )
        )

    def create(self, name: str, description: str = "", tags: list[str] | None = None) -> ProjectRecord:
        record = ProjectRecord(name=name.strip(), description=description.strip(), tags=tags or [])
        self._append(record)
        return record

    def list(self) -> list[dict[str, object]]:
        records = self._read_all()
        records.sort(key=lambda item: str(item.get("updated_at", item.get("created_at", ""))), reverse=True)
        return records

    def get(self, project_id: str) -> dict[str, object]:
        for record in self._read_all():
            if record.get("project_id") == project_id:
                return record
        raise KeyError(project_id)

    def touch(self, project_id: str) -> None:
        records = self._read_all()
        changed = False
        for record in records:
            if record.get("project_id") == project_id:
                record["updated_at"] = utc_now_iso()
                changed = True
        if changed:
            self._write_all(records)

    def _append(self, record: ProjectRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def _read_all(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def _write_all(self, records: list[dict[str, object]]) -> None:
        self.path.write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + ("\n" if records else ""),
            encoding="utf-8",
        )
