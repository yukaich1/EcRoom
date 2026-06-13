from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from evolving_creative_room.memory.vector_index import VectorIndex
from evolving_creative_room.memory.store import _bm25_scores
from evolving_creative_room.models import KnowledgeRecord, utc_now_iso
from evolving_creative_room.storage import atomic_write_jsonl


class KnowledgeBase:
    """本地资料和规范库。"""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.path = self.root / "knowledge" / "records.jsonl"
        self.vector = VectorIndex(self.root / "vector", "ecroom_knowledge")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(
        self,
        *,
        kind: str,
        title: str,
        content: str,
        project_id: str = "default",
        source: str = "",
        tags: list[str] | None = None,
    ) -> KnowledgeRecord:
        record = KnowledgeRecord(
            kind=kind,
            title=title.strip(),
            content=content.strip(),
            project_id=project_id,
            source=source.strip(),
            tags=tags or [],
        )
        self._append(record)
        self._index_record(record)
        return record

    def list(self, limit: int = 80, kind: str | None = None, project_id: str | None = None) -> list[dict[str, object]]:
        records = self._read_all()
        if kind:
            records = [item for item in records if item.get("kind") == kind]
        if project_id:
            records = [item for item in records if item.get("project_id", "default") in {project_id, "global"}]
        records.sort(key=lambda item: str(item.get("updated_at", item.get("created_at", ""))), reverse=True)
        return records[:limit]

    def search(self, query: str, limit: int = 10, kind: str | None = None, project_id: str | None = None) -> list[dict[str, object]]:
        terms = _terms(query)
        records = self.list(limit=500, kind=kind, project_id=project_id)
        scored_by_id: dict[str, tuple[float, dict[str, object]]] = {}
        lexical_scores = _bm25_scores(
            terms,
            records,
            lambda record: " ".join(
                [
                    str(record.get("kind", "")),
                    str(record.get("title", "")),
                    str(record.get("content", "")),
                    str(record.get("source", "")),
                    " ".join(record.get("tags", []) or []),
                ]
            ),
        )
        for record, lexical_score in lexical_scores:
            haystack = " ".join(
                [
                    str(record.get("kind", "")),
                    str(record.get("title", "")),
                    str(record.get("content", "")),
                    " ".join(record.get("tags", []) or []),
                ]
            ).lower()
            score = lexical_score + float(sum(1.5 if term in haystack else 0 for term in terms))
            if score:
                if record.get("kind") == "norm":
                    score += 1
                scored_by_id[str(record.get("record_id"))] = (score, record)
        where = {"project_id": project_id} if project_id else None
        for hit in self.vector.query(query, limit=max(limit * 2, 10), where=where):
            record = next((item for item in records if item.get("record_id") == hit.get("record_id")), None)
            if not record:
                continue
            if kind and record.get("kind") != kind:
                continue
            score = max(float(hit.get("vector_score", 0.0)) * 4.0, 0.0)
            existing = scored_by_id.get(str(record.get("record_id")))
            scored_by_id[str(record.get("record_id"))] = ((existing[0] if existing else 0.0) + score, record)
        scored = sorted(scored_by_id.values(), key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def update(self, record_id: str, **fields: object) -> bool:
        rows = self._read_all()
        changed = False
        for row in rows:
            if row.get("record_id") == record_id:
                for key in ["kind", "title", "content", "source", "tags"]:
                    if key in fields:
                        row[key] = fields[key]
                row["updated_at"] = utc_now_iso()
                changed = True
        if changed:
            self._write_all(rows)
            for row in rows:
                if row.get("record_id") == record_id:
                    self._index_dict(row)
        return changed

    def delete_records_for_session(self, session_id: str) -> int:
        session_tag = f"session:{session_id}"
        rows = self._read_all()
        kept = []
        removed = 0
        for row in rows:
            tags = [str(item) for item in row.get("tags", []) or []]
            if session_tag in tags:
                removed += 1
                continue
            kept.append(row)
        if removed:
            self._write_all(kept)
            self.rebuild_index()
        return removed

    def rebuild_index(self) -> dict[str, object]:
        count = 0
        for record in self._read_all():
            if not isinstance(record, dict):
                continue
            self._index_dict(record)
            count += 1
        return {"records_indexed": count, "backend": self.vector.backend, "available": self.vector.available, "error": self.vector.error}

    def _append(self, record: KnowledgeRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def _read_all(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records

    def _write_all(self, records: list[dict[str, object]]) -> None:
        atomic_write_jsonl(self.path, records)

    def _index_record(self, record: KnowledgeRecord) -> None:
        self._index_dict(asdict(record))

    def _index_dict(self, record: dict[str, object]) -> None:
        document = " ".join([str(record.get("kind", "")), str(record.get("title", "")), str(record.get("content", "")), str(record.get("source", ""))])
        self.vector.upsert(
            record_id=str(record.get("record_id", "")),
            document=document,
            metadata={
                "kind": str(record.get("kind", "")),
                "project_id": str(record.get("project_id", "default")),
                "tags": record.get("tags", []),
                "source": str(record.get("source", "")),
            },
        )


def _terms(query: str) -> list[str]:
    normalized = query.lower().replace("；", " ").replace("，", " ").replace(",", " ")
    terms = [item for item in re.split(r"[\s。！？、,.!?;；:：()（）\[\]【】]+", normalized) if item]
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    terms.extend(cjk[index : index + 2] for index in range(max(len(cjk) - 1, 0)))
    return list(dict.fromkeys(term for term in terms if term))
