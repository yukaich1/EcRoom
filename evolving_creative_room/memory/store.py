from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from evolving_creative_room.models import CreativeState, new_id, state_from_dict, state_to_dict, utc_now_iso
from evolving_creative_room.memory.vector_index import VectorIndex


@dataclass(slots=True)
class MemoryRecord:
    layer: str
    content: str
    project_id: str = "default"
    evidence_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    status: str = "active"
    confidence: float = 0.7
    record_id: str = field(default_factory=lambda: new_id("mem"))
    created_at: str = field(default_factory=utc_now_iso)


class MemoryStore:
    """本地文件记忆库，方便检查、diff 和回溯证据。"""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.records_dir = self.root / "memory"
        self.refs_dir = self.root / "refs"
        self.sessions_meta_path = self.root / "session_meta.json"
        self.vector = VectorIndex(self.root / "vector", "ecroom_memory")
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.refs_dir.mkdir(parents=True, exist_ok=True)

    def capture_l0(self, state: CreativeState) -> MemoryRecord:
        evidence_path = self.save_state(state)
        record = MemoryRecord(
            layer="L0",
            content=f"原始创作会话已保存：refs/{evidence_path.name}",
            project_id=state.project_id,
            evidence_ids=[state.session_id],
            tags=["raw", "session"],
        )
        self.append(record)
        return record

    def save_state(self, state: CreativeState) -> Path:
        evidence_path = self.refs_dir / f"{state.session_id}.json"
        evidence_path.write_text(
            json.dumps(state_to_dict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._touch_session_meta(state.session_id, state.intent.raw_request)
        return evidence_path

    def load_state(self, session_id: str) -> CreativeState:
        path = self.refs_dir / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        return state_from_dict(json.loads(path.read_text(encoding="utf-8")))

    def extract_l1(self, state: CreativeState) -> list[MemoryRecord]:
        records: list[MemoryRecord] = []
        records.append(
            MemoryRecord(
                layer="L1",
                content=f"创作需求：{state.intent.raw_request}",
                project_id=state.project_id,
                evidence_ids=[state.session_id],
                tags=["request"],
                status="evidence",
            )
        )
        for preference in state.intent.user_preferences:
            records.append(
                MemoryRecord(
                    layer="L1",
                    content=f"用户偏好：{preference}",
                    project_id=state.project_id,
                    evidence_ids=[state.session_id],
                    tags=["preference"],
                    status="evidence",
                )
            )
        for constraint in state.intent.constraints:
            records.append(
                MemoryRecord(
                    layer="L1",
                    content=f"创作约束：{constraint}",
                    project_id=state.project_id,
                    evidence_ids=[state.session_id],
                    tags=["constraint"],
                    status="evidence",
                )
            )
        for warning in state.warnings:
            records.append(
                MemoryRecord(
                    layer="L1",
                    content=f"规范或风险规则：{warning}",
                    project_id=state.project_id,
                    evidence_ids=[state.session_id],
                    tags=["norm"],
                    status="evidence",
                )
            )
        for feedback in state.human_feedback:
            if feedback.note:
                records.append(
                    MemoryRecord(
                        layer="L1",
                        content=f"用户反馈：{feedback.note}",
                        project_id=state.project_id,
                        evidence_ids=[state.session_id, feedback.feedback_id],
                        tags=["feedback", feedback.signal.value],
                        status="evidence",
                    )
                )
            if feedback.edited_text:
                records.append(
                    MemoryRecord(
                        layer="L1",
                        content="用户提供了直接改写版本，应优先作为风格证据。",
                        project_id=state.project_id,
                        evidence_ids=[state.session_id, feedback.feedback_id],
                        tags=["feedback", "edit"],
                        status="evidence",
                    )
                )
        self.extend(records)
        return records

    def upsert_l2_scene(self, state: CreativeState) -> MemoryRecord:
        platforms = [
            str(fact).split("“", 1)[1].split("”", 1)[0]
            for fact in state.facts
            if str(fact).startswith("平台规范线索：") and "“" in str(fact) and "”" in str(fact)
        ]
        platform_note = f"；涉及平台={', '.join(dict.fromkeys(platforms))}" if platforms else ""
        content = f"内容创作上下文：目标={state.intent.goal}；评价标准={', '.join(state.intent.evaluation_criteria)}{platform_note}"
        record = MemoryRecord(
            layer="L2",
            content=content,
            project_id=state.project_id,
            evidence_ids=[state.session_id],
            tags=["context", "creative"],
        )
        self.append_unique(record)
        return record

    def update_l3_persona(self, state: CreativeState) -> MemoryRecord | None:
        stable_preferences = self._stable_preferences(state)
        if not stable_preferences:
            return None
        content = "稳定用户偏好：" + "；".join(stable_preferences)
        record = MemoryRecord(
            layer="L3",
            content=content,
            project_id=state.project_id,
            evidence_ids=[state.session_id],
            tags=["persona", "stable_preference"],
            confidence=0.86,
        )
        self.append_unique(record)
        return record

    def _stable_preferences(self, state: CreativeState) -> list[str]:
        counts: dict[str, int] = {}
        labels: dict[str, str] = {}
        evidence: dict[str, set[str]] = {}
        for record in self.list_records(layer="L1", limit=1000, project_id=state.project_id, include_rejected=False):
            tags = record.get("tags", []) or []
            if "preference" not in tags:
                continue
            content = str(record.get("content", ""))
            if content.startswith("用户偏好："):
                label = content.removeprefix("用户偏好：").strip()
            else:
                label = content.strip()
            if not label:
                continue
            key = _normalize_memory_content(label)
            labels.setdefault(key, label)
            counts[key] = counts.get(key, 0) + 1
            evidence.setdefault(key, set()).update(str(item) for item in record.get("evidence_ids", []) or [])

        explicit = {_normalize_memory_content(item) for item in state.intent.user_preferences if _looks_long_term(item)}
        stable = []
        for key, count in counts.items():
            if len(evidence.get(key, set())) >= 2 or key in explicit:
                stable.append(labels[key])
        return stable[:8]

    def append(self, record: MemoryRecord) -> None:
        path = self.records_dir / f"{record.layer}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        self._index_record(record)

    def append_unique(self, record: MemoryRecord) -> bool:
        normalized = _normalize_memory_content(record.content)
        for existing in self.list_records(layer=record.layer, limit=1000, project_id=record.project_id, include_rejected=False):
            if _normalize_memory_content(str(existing.get("content", ""))) == normalized:
                return False
        self.append(record)
        return True

    def extend(self, records: Iterable[MemoryRecord]) -> None:
        for record in records:
            self.append(record)

    def list_records(
        self,
        layer: str | None = None,
        limit: int = 80,
        project_id: str | None = None,
        include_rejected: bool = True,
    ) -> list[dict[str, object]]:
        files = [self.records_dir / f"{layer}.jsonl"] if layer else sorted(self.records_dir.glob("L*.jsonl"))
        records: list[dict[str, object]] = []
        for path in files:
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    if project_id and record.get("project_id", "default") not in {project_id, "global"}:
                        continue
                    if not include_rejected and record.get("status") in {"rejected", "revoked", "deleted"}:
                        continue
                    records.append(record)
        records.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return records[:limit]

    def search_records(self, query: str, limit: int = 12, project_id: str | None = None) -> list[dict[str, object]]:
        terms = _terms(query)
        all_records = [
            record
            for record in self.list_records(limit=500, project_id=project_id, include_rejected=False)
            if record.get("status", "active") not in {"candidate", "evidence"}
        ]
        if not terms:
            return all_records[:limit]
        by_id: dict[str, tuple[float, dict[str, object]]] = {}
        lexical_scores = _bm25_scores(
            terms,
            all_records,
            lambda record: f"{record.get('content', '')} {' '.join(record.get('tags', []) or [])}",
        )
        for record, lexical_score in lexical_scores:
            text = f"{record.get('content', '')} {' '.join(record.get('tags', []) or [])}".lower()
            exact_score = float(sum(1.5 if term in text else 0 for term in terms))
            score = lexical_score + exact_score
            if score:
                layer = str(record.get("layer", ""))
                if layer == "L3":
                    score += 2
                elif layer == "L2":
                    score += 1
                by_id[str(record.get("record_id"))] = (score, record)

        vector_hits = self.vector.query(query, limit=max(limit * 2, 12), where={"project_id": project_id} if project_id else None)
        records_by_id = {str(record.get("record_id")): record for record in all_records}
        for hit in vector_hits:
            record = records_by_id.get(str(hit.get("record_id")))
            if not record:
                continue
            score = max(float(hit.get("vector_score", 0.0)) * 4.0, 0.0)
            existing = by_id.get(str(record.get("record_id")))
            by_id[str(record.get("record_id"))] = ((existing[0] if existing else 0.0) + score, record)

        ranked = sorted(by_id.values(), key=lambda item: item[0], reverse=True)
        return [record for _, record in ranked[:limit]]

    def review_record(self, record_id: str, status: str) -> bool:
        changed = False
        for path in self.records_dir.glob("L*.jsonl"):
            rows = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("record_id") == record_id:
                    data["status"] = status
                    changed = True
                rows.append(data)
            if changed:
                path.write_text(
                    "\n".join(json.dumps(item, ensure_ascii=False) for item in rows) + ("\n" if rows else ""),
                    encoding="utf-8",
                )
        return changed

    def revoke_records_for_session(self, session_id: str, *, status: str = "revoked", include_confirmed: bool = False) -> int:
        changed_count = 0
        for path in self.records_dir.glob("L*.jsonl"):
            rows = []
            changed_path = False
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                evidence = [str(item) for item in data.get("evidence_ids", []) or []]
                tags = [str(item) for item in data.get("tags", []) or []]
                if "confirmed" in tags and not include_confirmed:
                    rows.append(data)
                    continue
                if session_id in evidence and data.get("status") not in {"rejected", "revoked", "deleted"}:
                    data["status"] = status
                    data["revoked_by_session"] = session_id
                    data["updated_at"] = utc_now_iso()
                    changed_count += 1
                    changed_path = True
                rows.append(data)
            if changed_path:
                path.write_text(
                    "\n".join(json.dumps(item, ensure_ascii=False) for item in rows) + ("\n" if rows else ""),
                    encoding="utf-8",
                )
        return changed_count

    def list_sessions(self, *, include_completed: bool = False) -> list[dict[str, object]]:
        meta = self._read_session_meta()
        sessions: list[dict[str, object]] = []
        for path in sorted(self.refs_dir.glob("session_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = json.loads(path.read_text(encoding="utf-8"))
            item_meta = meta.get(data["session_id"], {})
            if item_meta.get("deleted"):
                continue
            if item_meta.get("completed") and not include_completed:
                continue
            sessions.append(
                {
                    "session_id": data["session_id"],
                    "project_id": data.get("project_id", "default"),
                    "title": item_meta.get("title") or _session_title(data["intent"]["raw_request"]),
                    "pinned": bool(item_meta.get("pinned", False)),
                    "completed": bool(item_meta.get("completed", False)),
                    "completed_at": item_meta.get("completed_at", ""),
                    "archive": item_meta.get("archive", ""),
                    "work_category": item_meta.get("work_category", ""),
                    "asset_deleted": bool(item_meta.get("asset_deleted", False)),
                    "raw_request": data["intent"]["raw_request"],
                    "goal": data["intent"].get("goal", ""),
                    "medium": data["intent"].get("medium", ""),
                    "draft_count": len(data.get("drafts", [])),
                    "feedback_count": len(data.get("human_feedback", [])),
                    "updated_at": item_meta.get("updated_at_ts", path.stat().st_mtime),
                }
            )
        sessions.sort(key=lambda item: (bool(item.get("pinned")), float(item.get("updated_at", 0))), reverse=True)
        return sessions

    def update_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        pinned: bool | None = None,
        completed: bool | None = None,
        archive: str | None = None,
        work_category: str | None = None,
    ) -> dict[str, object]:
        self.load_state(session_id)
        meta = self._read_session_meta()
        item = meta.setdefault(session_id, {})
        if title is not None and title.strip():
            item["title"] = title.strip()
        if pinned is not None:
            item["pinned"] = bool(pinned)
        if completed is not None:
            item["completed"] = bool(completed)
            if completed:
                item["completed_at"] = utc_now_iso()
                item["archive"] = archive or item.get("archive") or "works"
                if work_category is not None and work_category.strip():
                    item["work_category"] = work_category.strip()
            else:
                item.pop("completed_at", None)
                item.pop("archive", None)
        item["updated_at"] = utc_now_iso()
        item["updated_at_ts"] = self._session_path(session_id).stat().st_mtime
        self._write_session_meta(meta)
        return {"session_id": session_id, **item}

    def hide_asset(self, session_id: str) -> dict[str, object]:
        self.load_state(session_id)
        meta = self._read_session_meta()
        item = meta.setdefault(session_id, {})
        if item.get("deleted"):
            raise FileNotFoundError(f"Session not found: {session_id}")
        item["asset_deleted"] = True
        item["asset_deleted_at"] = utc_now_iso()
        item["updated_at"] = utc_now_iso()
        item["updated_at_ts"] = self._session_path(session_id).stat().st_mtime
        self._write_session_meta(meta)
        return {"deleted": True, "asset_id": session_id, "source": "session"}

    def delete_session(self, session_id: str, *, mode: str = "revoke_memory") -> dict[str, object]:
        self.load_state(session_id)
        if mode not in {"history", "revoke_memory", "full"}:
            raise ValueError(f"Unknown delete mode: {mode}")
        meta = self._read_session_meta()
        item = meta.setdefault(session_id, {})
        item["deleted"] = True
        item["delete_mode"] = mode
        item["updated_at"] = utc_now_iso()
        item["updated_at_ts"] = self._session_path(session_id).stat().st_mtime
        self._write_session_meta(meta)
        revoked_count = self.revoke_records_for_session(session_id, include_confirmed=(mode == "full")) if mode in {"revoke_memory", "full"} else 0
        removed_ref = False
        if mode == "full":
            path = self._session_path(session_id)
            if path.exists():
                path.unlink()
                removed_ref = True
        return {
            "deleted": True,
            "session_id": session_id,
            "mode": mode,
            "revoked_memory_count": revoked_count,
            "removed_session_file": removed_ref,
        }

    def render_short_term_canvas(self, state: CreativeState) -> str:
        draft_nodes = "\n".join(
            f'    {draft.version_id}["{draft.author.value}: {draft.version_id}"]'
            for draft in state.drafts
        )
        comment_nodes = "\n".join(
            f'    {comment.comment_id}["{comment.agent.value}: {comment.severity}"]'
            for comment in state.comments
        )
        edges = []
        for draft in state.drafts:
            edges.append(f"    intent --> {draft.version_id}")
            if draft.parent_version_id:
                edges.append(f"    {draft.parent_version_id} --> {draft.version_id}")
        for comment in state.comments:
            edges.append(f"    {comment.target_id} --> {comment.comment_id}")
        body = "\n".join(
            [
                "graph TD",
                f'    intent["CreativeIntent: {state.intent.goal or "open"}"]',
                draft_nodes,
                comment_nodes,
                *edges,
            ]
        )
        canvas_path = self.root / "short_term_canvas.mmd"
        canvas_path.write_text(body, encoding="utf-8")
        return body

    def _session_path(self, session_id: str) -> Path:
        return self.refs_dir / f"{session_id}.json"

    def _touch_session_meta(self, session_id: str, raw_request: str) -> None:
        meta = self._read_session_meta()
        item = meta.setdefault(
            session_id,
            {
                "title": _session_title(raw_request),
                "pinned": False,
                "deleted": False,
                "created_at": utc_now_iso(),
            },
        )
        item["updated_at"] = utc_now_iso()
        item["updated_at_ts"] = self._session_path(session_id).stat().st_mtime if self._session_path(session_id).exists() else 0
        self._write_session_meta(meta)

    def _read_session_meta(self) -> dict[str, dict[str, object]]:
        if not self.sessions_meta_path.exists():
            return {}
        data = json.loads(self.sessions_meta_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def _write_session_meta(self, meta: dict[str, dict[str, object]]) -> None:
        self.sessions_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def _index_record(self, record: MemoryRecord) -> None:
        self.vector.upsert(
            record_id=record.record_id,
            document=record.content,
            metadata={
                "layer": record.layer,
                "project_id": record.project_id,
                "tags": record.tags,
                "status": record.status,
                "confidence": record.confidence,
            },
        )


def _terms(query: str) -> list[str]:
    normalized = query.lower().replace("；", " ").replace("，", " ").replace(",", " ")
    terms = [item for item in re.split(r"[\s。！？、,.!?;；:：()（）\[\]【】]+", normalized) if item]
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    terms.extend(cjk[index : index + 2] for index in range(max(len(cjk) - 1, 0)))
    return list(dict.fromkeys(term for term in terms if term))


def _bm25_scores(
    terms: list[str],
    records: list[dict[str, object]],
    text_fn,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[tuple[dict[str, object], float]]:
    tokenized = [_terms(text_fn(record)) for record in records]
    if not tokenized:
        return []
    avg_len = sum(len(tokens) for tokens in tokenized) / max(len(tokenized), 1)
    doc_freq: dict[str, int] = {}
    for tokens in tokenized:
        unique = set(tokens)
        for term in terms:
            if term in unique:
                doc_freq[term] = doc_freq.get(term, 0) + 1
    scored = []
    total_docs = len(records)
    for record, tokens in zip(records, tokenized):
        if not tokens:
            continue
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        score = 0.0
        doc_len = len(tokens)
        for term in terms:
            freq = counts.get(term, 0)
            if not freq:
                continue
            df = doc_freq.get(term, 0)
            idf = max(0.1, math.log(1 + (total_docs - df + 0.5) / (df + 0.5)))
            denom = freq + k1 * (1 - b + b * doc_len / max(avg_len, 1))
            score += idf * (freq * (k1 + 1)) / denom
        if score:
            scored.append((record, score))
    return scored


def _session_title(raw_request: str) -> str:
    title = re.sub(r"\s+", " ", raw_request).strip()
    return title[:24] + ("..." if len(title) > 24 else "")


def _normalize_memory_content(content: str) -> str:
    return re.sub(r"\s+", "", content).lower()


def _looks_long_term(text: str) -> bool:
    return any(term in text for term in ["以后", "长期", "一直", "总是", "记住", "我的风格", "个人偏好"])
