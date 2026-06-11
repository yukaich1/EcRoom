from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from evolving_creative_room.memory.store import MemoryRecord, MemoryStore
from evolving_creative_room.models import CreativeState, new_id, utc_now_iso
from evolving_creative_room.storage import atomic_write_jsonl


@dataclass(slots=True)
class LearningCandidate:
    session_id: str
    project_id: str
    kind: str
    content: str
    suggested_scope: str
    reason: str
    effect: str
    confidence: float = 0.0
    target_object: str = ""
    evidence_strength: float = 0.0
    reusability: float = 0.0
    scope_confidence: float = 0.0
    user_intent_clarity: float = 0.0
    interruption_risk: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    status: str = "candidate"
    candidate_id: str = field(default_factory=lambda: new_id("learn"))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


class LearningStore:
    """管理“本次学到什么”的候选项和作用域确认。"""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.path = self.root / "learning" / "candidates.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def suggest_from_state(self, state: CreativeState, *, min_confidence: float = 0.35, limit: int = 3) -> list[dict[str, object]]:
        candidates: list[LearningCandidate] = []
        for preference in state.intent.user_preferences:
            if preference.startswith("使用技能："):
                continue
            if _is_ephemeral(preference) and not _looks_long_term(preference):
                continue
            candidates.append(
                LearningCandidate(
                    session_id=state.session_id,
                    project_id=state.project_id,
                    kind="preference",
                    content=_clean_label(preference),
                    suggested_scope="global" if _looks_long_term(preference) else "session",
                    reason="来自用户在需求或反馈里表达的写作偏好。",
                    effect="设为偏好后，后续创作会优先参考这条表达倾向；未确认前只影响当前会话。",
                    evidence_ids=[state.session_id],
                    target_object=_target_object(preference),
                )
            )

        for constraint in state.intent.constraints:
            if _is_ephemeral(constraint) and not _looks_long_term(constraint):
                continue
            platforms = _detect_platforms(constraint)
            kind = "platform_rule" if platforms else "project_rule"
            suggested_scope = "global" if platforms else "project"
            candidates.append(
                LearningCandidate(
                    session_id=state.session_id,
                    project_id=state.project_id,
                    kind=kind,
                    content=_clean_label(constraint),
                    suggested_scope=suggested_scope,
                    reason="来自用户给出的平台要求。" if platforms else "来自用户给出的约束、禁用项或项目设定。",
                    effect=(
                        "设为偏好后，后续涉及该平台时会优先参考这条表达边界。"
                        if platforms
                        else "保存为项目规则后，后续同项目创作会自动参考这条规则。"
                    ),
                    evidence_ids=[state.session_id],
                    target_object=_target_object(constraint),
                )
            )

        for fact in state.facts:
            text = str(fact)
            if text.startswith("平台规范线索："):
                platform = _extract_platform_from_fact(text)
                candidates.append(
                    LearningCandidate(
                        session_id=state.session_id,
                        project_id=state.project_id,
                        kind="platform_rule",
                        content=f"涉及{platform}时，优先检查该平台的表达习惯和发布边界。" if platform else _clean_label(text),
                        suggested_scope="global",
                        reason="系统识别到用户提到具体平台。",
                        effect="设为偏好后，后续提到该平台时会提醒规范智能体检查表达习惯和发布边界。",
                        evidence_ids=[state.session_id],
                        target_object="platform",
                    )
                )

        saved = []
        for candidate in _merge_candidates(candidates):
            candidate.content = _compact_learning_content(candidate.content)
            if not candidate.content or not _displayable_candidate(candidate.content):
                continue
            _score_candidate(candidate)
            if candidate.confidence < min_confidence:
                continue
            saved.append(self._upsert(candidate))
        saved.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
        return saved[: max(1, min(5, int(limit)))]

    def list(
        self,
        *,
        session_id: str | None = None,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 80,
    ) -> list[dict[str, object]]:
        rows = self._read_all()
        if session_id:
            rows = [item for item in rows if item.get("session_id") == session_id]
        if project_id:
            rows = [item for item in rows if item.get("project_id", "default") in {project_id, "global"}]
        if status:
            rows = [item for item in rows if item.get("status") == status]
        rows.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return rows[:limit]

    def apply(self, candidate_id: str, action: str, memory: MemoryStore) -> dict[str, object]:
        action_map = {
            "session": "session_active",
            "session_active": "session_active",
            "project": "project_active",
            "project_active": "project_active",
            "global": "global_active",
            "global_active": "global_active",
            "preference": "global_active",
            "cancel": "ignored",
            "ignore": "ignored",
            "ignored": "ignored",
            "reject": "rejected",
            "rejected": "rejected",
        }
        status = action_map.get(action)
        if not status:
            raise ValueError(f"Unknown learning action: {action}")

        rows = self._read_all()
        changed: dict[str, object] | None = None
        for item in rows:
            if item.get("candidate_id") == candidate_id:
                item["status"] = status
                item["updated_at"] = utc_now_iso()
                changed = item
                break
        if not changed:
            raise ValueError(f"Learning candidate not found: {candidate_id}")
        self._write_all(rows)

        memory_record = None
        if status in {"project_active", "global_active", "rejected"}:
            memory_record = self._materialize(changed, status, memory)
        return {"candidate": changed, "memory_record": memory_record}

    def revoke_for_session(self, session_id: str, *, status: str = "revoked") -> int:
        rows = self._read_all()
        count = 0
        for item in rows:
            if item.get("session_id") == session_id and item.get("status") not in {"rejected", "revoked", "ignored"}:
                item["status"] = status
                item["updated_at"] = utc_now_iso()
                count += 1
        if count:
            self._write_all(rows)
        return count

    def _materialize(self, candidate: dict[str, object], status: str, memory: MemoryStore) -> dict[str, object] | None:
        content = str(candidate.get("content", "")).strip()
        if not content:
            return None
        kind = str(candidate.get("kind", "learning"))
        project_id = str(candidate.get("project_id", "default"))
        evidence_ids = [str(item) for item in candidate.get("evidence_ids", []) or []]
        if status == "project_active":
            record = MemoryRecord(
                layer="L2",
                content=f"项目规则：{content}",
                project_id=project_id,
                evidence_ids=evidence_ids,
                tags=[kind, "confirmed", "scope:project"],
                confidence=0.86,
            )
        elif status == "global_active":
            record = MemoryRecord(
                layer="L3",
                content=f"偏好：{content}",
                project_id="global",
                evidence_ids=evidence_ids,
                tags=[kind, "confirmed", "scope:global"],
                confidence=0.9,
            )
        else:
            record = MemoryRecord(
                layer="L3",
                content=f"不再使用的学习判断：{content}",
                project_id="global",
                evidence_ids=evidence_ids,
                tags=[kind, "rejected", "scope:global"],
                status="rejected",
                confidence=1.0,
            )
        memory.append_unique(record)
        return asdict(record)

    def _append(self, candidate: LearningCandidate) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(candidate), ensure_ascii=False) + "\n")

    def _upsert(self, candidate: LearningCandidate) -> dict[str, object]:
        rows = self._read_all()
        key = _candidate_key(asdict(candidate))
        for item in rows:
            if _candidate_key(item) == key and item.get("status") == "candidate":
                item["reason"] = candidate.reason
                item["effect"] = candidate.effect
                item["suggested_scope"] = candidate.suggested_scope
                item["confidence"] = candidate.confidence
                item["target_object"] = candidate.target_object
                item["evidence_strength"] = candidate.evidence_strength
                item["reusability"] = candidate.reusability
                item["scope_confidence"] = candidate.scope_confidence
                item["user_intent_clarity"] = candidate.user_intent_clarity
                item["interruption_risk"] = candidate.interruption_risk
                evidence = list(dict.fromkeys([*(item.get("evidence_ids", []) or []), *candidate.evidence_ids]))
                item["evidence_ids"] = evidence
                item["updated_at"] = utc_now_iso()
                self._write_all(rows)
                return item
        data = asdict(candidate)
        rows.append(data)
        self._write_all(rows)
        return data

    def _exists(self, candidate: LearningCandidate) -> bool:
        key = _candidate_key(asdict(candidate))
        return any(_candidate_key(item) == key for item in self._read_all())

    def _read_all(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _write_all(self, rows: list[dict[str, object]]) -> None:
        atomic_write_jsonl(self.path, rows)


def _merge_candidates(candidates: list[LearningCandidate]) -> list[LearningCandidate]:
    merged: dict[tuple[str, str], LearningCandidate] = {}
    for candidate in candidates:
        key = (candidate.kind, _normalize_candidate(candidate.content))
        existing = merged.get(key)
        if not existing:
            merged[key] = candidate
            continue
        existing.evidence_ids = list(dict.fromkeys([*existing.evidence_ids, *candidate.evidence_ids]))
        if len(candidate.reason) > len(existing.reason):
            existing.reason = candidate.reason
        if candidate.target_object and not existing.target_object:
            existing.target_object = candidate.target_object
    return list(merged.values())


def _score_candidate(candidate: LearningCandidate) -> None:
    text = candidate.content
    candidate.evidence_strength = 0.75 if candidate.evidence_ids else 0.45
    candidate.reusability = 0.8 if candidate.kind in {"platform_rule", "project_rule"} else 0.65
    candidate.scope_confidence = 0.85 if candidate.suggested_scope == "project" else 0.78 if candidate.suggested_scope == "global" else 0.5
    candidate.user_intent_clarity = 0.95 if _looks_long_term(text) else 0.55
    candidate.interruption_risk = 0.15 if len(text) <= 42 else 0.35
    if _is_ephemeral(text) and not _looks_long_term(text):
        candidate.interruption_risk += 0.4
        candidate.scope_confidence -= 0.25
    if candidate.suggested_scope == "global" and not (_looks_long_term(text) or candidate.kind == "platform_rule"):
        candidate.interruption_risk += 0.2
        candidate.scope_confidence -= 0.2
    candidate.confidence = round(
        candidate.evidence_strength * 0.30
        + candidate.reusability * 0.25
        + candidate.scope_confidence * 0.25
        + candidate.user_intent_clarity * 0.15
        - candidate.interruption_risk * 0.20,
        4,
    )


def _target_object(text: str) -> str:
    mapping = {
        "标题": "title",
        "开头": "opening",
        "第二段": "paragraph",
        "段落": "paragraph",
        "语气": "tone",
        "风格": "style",
        "角色": "character",
        "世界观": "worldbuilding",
        "平台": "platform",
        "小红书": "platform",
        "微博": "platform",
    }
    for term, target in mapping.items():
        if term in text:
            return target
    return "whole_draft"


def _normalize_candidate(text: str) -> str:
    value = _clean_label(text)
    value = re.sub(r"^(偏好|规则|要求|约束)[:：]", "", value)
    return re.sub(r"\s+", "", value).lower()


def _candidate_key(item: dict[str, object]) -> str:
    return "|".join(
        [
            str(item.get("session_id", "")),
            str(item.get("kind", "")),
            re.sub(r"\s+", "", str(item.get("content", ""))).lower(),
        ]
    )


def _clean_label(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip(" ，,；;：:")


def _compact_learning_content(text: str, *, max_length: int = 54) -> str:
    value = _clean_label(text)
    value = re.sub(r"^(用户偏好|创作约束|平台规范线索|规范或风险规则|用户反馈)[:：]", "", value).strip()
    value = re.sub(r"^(请|帮我|需要|希望|要求)(?:[，,：:]\s*)?", "", value).strip()
    value = re.sub(r"(可以|能不能|是否|然后|就是|这个|那个)", "", value).strip()
    value = re.sub(r"\s+", " ", value)
    parts = [part.strip() for part in re.split(r"[。！？；;]\s*", value) if part.strip()]
    if parts:
        value = max(parts, key=lambda item: _learning_signal_score(item))
    if len(value) > max_length:
        value = value[: max_length - 1].rstrip(" ，,；;：:") + "…"
    return value


def _learning_signal_score(text: str) -> int:
    score = 0
    for term in ["以后", "默认", "不要", "保持", "必须", "优先", "平台", "角色", "世界观", "风格", "语气", "禁用"]:
        if term in text:
            score += 2
    score += min(len(text), 60) // 12
    return score


def _looks_long_term(text: str) -> bool:
    return any(term in text for term in ["以后", "长期", "一直", "总是", "记住", "我的风格", "默认", "个人偏好"])


def _is_ephemeral(text: str) -> bool:
    return any(term in text for term in ["这次", "本次", "这一版", "这版", "当前", "先", "暂时", "临时"])


def _displayable_candidate(text: str) -> bool:
    value = _clean_label(text)
    if len(value) < 3 or len(value) > 72:
        return False
    if any(term in value for term in ["先写", "这次先", "本次先", "随便", "试一下", "测试"]):
        return False
    if re.fullmatch(r"[\W_]+", value):
        return False
    return True


def _detect_platforms(text: str) -> list[str]:
    platforms = ["小红书", "微博", "抖音", "B站", "哔哩哔哩", "公众号", "知乎", "快手", "视频号", "TikTok", "RedNote"]
    found = []
    lowered = text.lower()
    for platform in platforms:
        if platform in text or platform.lower() in lowered:
            normalized = "B站" if platform == "哔哩哔哩" else platform
            if normalized not in found:
                found.append(normalized)
    return found


def _extract_platform_from_fact(text: str) -> str:
    match = re.search(r"用户提到“([^”]+)”", text)
    if match:
        return match.group(1)
    platforms = _detect_platforms(text)
    return platforms[0] if platforms else ""
