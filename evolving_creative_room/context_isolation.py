from __future__ import annotations

from evolving_creative_room.models import CreativeState


def memory_available_for_session(record: dict[str, object], state: CreativeState) -> bool:
    """Return whether a memory record may affect the current conversation."""
    status = str(record.get("status", "active"))
    if status in {"candidate", "evidence", "rejected", "revoked", "deleted"}:
        return False

    tags = _string_set(record.get("tags", []))
    evidence_ids = _string_set(record.get("evidence_ids", []))
    if state.session_id in evidence_ids or f"session:{state.session_id}" in tags:
        return True
    if "confirmed" in tags:
        return True
    if not evidence_ids and "session" not in tags:
        return True
    return False


def knowledge_available_for_session(record: dict[str, object], state: CreativeState) -> bool:
    """Return whether a knowledge record may affect the current conversation."""
    tags = _string_set(record.get("tags", []))
    session_tags = {tag for tag in tags if tag.startswith("session:")}
    current_session_tag = f"session:{state.session_id}"
    if current_session_tag in session_tags:
        return True
    if session_tags:
        return False
    if "user_source" in tags and "confirmed" not in tags:
        return False
    return True


def filter_memory_for_session(records: list[dict[str, object]], state: CreativeState, *, limit: int) -> list[dict[str, object]]:
    return [record for record in records if memory_available_for_session(record, state)][:limit]


def filter_knowledge_for_session(records: list[dict[str, object]], state: CreativeState, *, limit: int) -> list[dict[str, object]]:
    return [record for record in records if knowledge_available_for_session(record, state)][:limit]


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value if str(item)}
