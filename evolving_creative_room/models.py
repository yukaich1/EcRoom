from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentRole(str, Enum):
    HUMAN = "human"
    ORCHESTRATOR = "orchestrator"
    INTENT_INTERPRETER = "intent_interpreter"
    DIALOGUE_PARTNER = "dialogue_partner"
    RESEARCHER = "researcher"
    STRATEGIST = "strategist"
    DRAFT_WRITER = "draft_writer"
    VARIANT_WRITER = "variant_writer"
    EDITOR = "editor"
    CRITIC = "critic"
    NORM_STEWARD = "norm_steward"
    CANON_KEEPER = "canon_keeper"
    STYLE_KEEPER = "style_keeper"
    MEMORY_CURATOR = "memory_curator"
    HARNESS_EVOLVER = "harness_evolver"
    EVALUATOR = "evaluator"
    CONTEXT_BUILDER = "context_builder"


class FeedbackSignal(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    EDIT = "edit"
    CONTINUE = "continue"
    LIKE_STYLE = "like_style"
    DISLIKE_STYLE = "dislike_style"
    SAVE_AS_RULE = "save_as_rule"
    SAVE_AS_PREFERENCE = "save_as_preference"


@dataclass(slots=True)
class SourceRef:
    source_id: str
    kind: str
    uri: str
    note: str = ""


@dataclass(slots=True)
class KnowledgeRecord:
    kind: str
    title: str
    content: str
    project_id: str = "default"
    source: str = ""
    tags: list[str] = field(default_factory=list)
    record_id: str = field(default_factory=lambda: new_id("knowledge"))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class ProjectRecord:
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    project_id: str = field(default_factory=lambda: new_id("project"))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class CreativeIntent:
    raw_request: str
    goal: str = ""
    audience: str = ""
    context: str = ""
    medium: str = ""
    constraints: list[str] = field(default_factory=list)
    style: list[str] = field(default_factory=list)
    evaluation_criteria: list[str] = field(default_factory=list)
    user_preferences: list[str] = field(default_factory=list)
    project_context: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        parts = [
            f"goal={self.goal or 'unknown'}",
            f"audience={self.audience or 'unknown'}",
            f"medium={self.medium or 'open'}",
        ]
        if self.constraints:
            parts.append(f"constraints={'; '.join(self.constraints)}")
        if self.style:
            parts.append(f"style={'; '.join(self.style)}")
        return ", ".join(parts)


@dataclass(slots=True)
class AgentMessage:
    role: AgentRole
    content: str
    message_id: str = field(default_factory=lambda: new_id("msg"))
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DraftVersion:
    content: str
    author: AgentRole
    version_id: str = field(default_factory=lambda: new_id("draft"))
    created_at: str = field(default_factory=utc_now_iso)
    parent_version_id: str | None = None
    rationale: str = ""


@dataclass(slots=True)
class AgentComment:
    agent: AgentRole
    target_id: str
    comment: str
    severity: str = "note"
    evidence: list[SourceRef] = field(default_factory=list)
    comment_id: str = field(default_factory=lambda: new_id("comment"))
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class HumanFeedback:
    signal: FeedbackSignal
    target_id: str
    note: str = ""
    edited_text: str | None = None
    feedback_id: str = field(default_factory=lambda: new_id("feedback"))
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class AgentEvent:
    agent: AgentRole
    status: str
    stage_label: str
    detail: str = ""
    input_refs: list[str] = field(default_factory=list)
    output_refs: list[str] = field(default_factory=list)
    failure_signal: str = ""
    visible_to_user: bool = True
    event_id: str = field(default_factory=lambda: new_id("event"))
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class FailureSignal:
    failure_type: str
    evidence_text: str
    session_id: str = ""
    draft_version_id: str = ""
    skill_id: str = ""
    agent_role: str = ""
    component: str = ""
    severity: str = "medium"
    signal_id: str = field(default_factory=lambda: new_id("fail"))
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class CreativeState:
    intent: CreativeIntent
    project_id: str = "default"
    session_id: str = field(default_factory=lambda: new_id("session"))
    messages: list[AgentMessage] = field(default_factory=list)
    drafts: list[DraftVersion] = field(default_factory=list)
    comments: list[AgentComment] = field(default_factory=list)
    human_feedback: list[HumanFeedback] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    strategy: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    agent_events: list[AgentEvent] = field(default_factory=list)
    failure_signals: list[FailureSignal] = field(default_factory=list)

    def add_message(self, role: AgentRole, content: str, **metadata: Any) -> AgentMessage:
        message = AgentMessage(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        return message

    def add_draft(
        self,
        content: str,
        author: AgentRole,
        rationale: str = "",
        parent_version_id: str | None = None,
    ) -> DraftVersion:
        draft = DraftVersion(
            content=content,
            author=author,
            rationale=rationale,
            parent_version_id=parent_version_id,
        )
        self.drafts.append(draft)
        return draft

    def add_comment(
        self,
        agent: AgentRole,
        target_id: str,
        comment: str,
        severity: str = "note",
        evidence: list[SourceRef] | None = None,
    ) -> AgentComment:
        item = AgentComment(
            agent=agent,
            target_id=target_id,
            comment=comment,
            severity=severity,
            evidence=evidence or [],
        )
        self.comments.append(item)
        return item

    def add_event(
        self,
        agent: AgentRole,
        status: str,
        stage_label: str,
        detail: str = "",
        *,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        failure_signal: str = "",
        visible_to_user: bool = True,
    ) -> AgentEvent:
        event = AgentEvent(
            agent=agent,
            status=status,
            stage_label=stage_label,
            detail=detail,
            input_refs=input_refs or [],
            output_refs=output_refs or [],
            failure_signal=failure_signal,
            visible_to_user=visible_to_user,
        )
        self.agent_events.append(event)
        return event

    def add_failure_signal(
        self,
        failure_type: str,
        evidence_text: str,
        *,
        draft_version_id: str = "",
        skill_id: str = "",
        agent_role: str = "",
        component: str = "",
        severity: str = "medium",
    ) -> FailureSignal:
        normalized = " ".join(str(evidence_text).split())
        for signal in self.failure_signals:
            if signal.failure_type == failure_type and " ".join(signal.evidence_text.split()) == normalized:
                return signal
        item = FailureSignal(
            failure_type=failure_type,
            evidence_text=evidence_text,
            session_id=self.session_id,
            draft_version_id=draft_version_id,
            skill_id=skill_id,
            agent_role=agent_role,
            component=component,
            severity=severity,
        )
        self.failure_signals.append(item)
        return item


def state_to_dict(state: CreativeState) -> dict[str, Any]:
    return {
        "session_id": state.session_id,
        "project_id": state.project_id,
        "intent": {
            "raw_request": state.intent.raw_request,
            "goal": state.intent.goal,
            "audience": state.intent.audience,
            "context": state.intent.context,
            "medium": state.intent.medium,
            "constraints": state.intent.constraints,
            "style": state.intent.style,
            "evaluation_criteria": state.intent.evaluation_criteria,
            "user_preferences": state.intent.user_preferences,
            "project_context": state.intent.project_context,
        },
        "messages": [
            {
                "role": item.role.value,
                "content": item.content,
                "message_id": item.message_id,
                "created_at": item.created_at,
                "metadata": item.metadata,
            }
            for item in state.messages
        ],
        "drafts": [
            {
                "content": item.content,
                "author": item.author.value,
                "version_id": item.version_id,
                "created_at": item.created_at,
                "parent_version_id": item.parent_version_id,
                "rationale": item.rationale,
            }
            for item in state.drafts
        ],
        "comments": [
            {
                "agent": item.agent.value,
                "target_id": item.target_id,
                "comment": item.comment,
                "severity": item.severity,
                "evidence": [
                    {
                        "source_id": ref.source_id,
                        "kind": ref.kind,
                        "uri": ref.uri,
                        "note": ref.note,
                    }
                    for ref in item.evidence
                ],
                "comment_id": item.comment_id,
                "created_at": item.created_at,
            }
            for item in state.comments
        ],
        "human_feedback": [
            {
                "signal": item.signal.value,
                "target_id": item.target_id,
                "note": item.note,
                "edited_text": item.edited_text,
                "feedback_id": item.feedback_id,
                "created_at": item.created_at,
            }
            for item in state.human_feedback
        ],
        "facts": state.facts,
        "strategy": state.strategy,
        "warnings": state.warnings,
        "agent_events": [
            {
                "agent": item.agent.value,
                "status": item.status,
                "stage_label": item.stage_label,
                "detail": item.detail,
                "input_refs": item.input_refs,
                "output_refs": item.output_refs,
                "failure_signal": item.failure_signal,
                "visible_to_user": item.visible_to_user,
                "event_id": item.event_id,
                "created_at": item.created_at,
            }
            for item in state.agent_events
        ],
        "failure_signals": [
            {
                "signal_id": item.signal_id,
                "session_id": item.session_id,
                "draft_version_id": item.draft_version_id,
                "skill_id": item.skill_id,
                "agent_role": item.agent_role,
                "component": item.component,
                "failure_type": item.failure_type,
                "evidence_text": item.evidence_text,
                "severity": item.severity,
                "created_at": item.created_at,
            }
            for item in state.failure_signals
        ],
    }


def state_from_dict(data: dict[str, Any]) -> CreativeState:
    intent = CreativeIntent(**data["intent"])
    state = CreativeState(intent=intent, session_id=data["session_id"], project_id=data.get("project_id", "default"))
    state.messages = [
        AgentMessage(
            role=AgentRole(item["role"]),
            content=item["content"],
            message_id=item["message_id"],
            created_at=item["created_at"],
            metadata=item.get("metadata", {}),
        )
        for item in data.get("messages", [])
    ]
    state.drafts = [
        DraftVersion(
            content=item["content"],
            author=AgentRole(item["author"]),
            version_id=item["version_id"],
            created_at=item["created_at"],
            parent_version_id=item.get("parent_version_id"),
            rationale=item.get("rationale", ""),
        )
        for item in data.get("drafts", [])
    ]
    state.comments = [
        AgentComment(
            agent=AgentRole(item["agent"]),
            target_id=item["target_id"],
            comment=item["comment"],
            severity=item.get("severity", "note"),
            evidence=[
                SourceRef(
                    source_id=ref["source_id"],
                    kind=ref["kind"],
                    uri=ref["uri"],
                    note=ref.get("note", ""),
                )
                for ref in item.get("evidence", [])
            ],
            comment_id=item["comment_id"],
            created_at=item["created_at"],
        )
        for item in data.get("comments", [])
    ]
    state.human_feedback = [
        HumanFeedback(
            signal=FeedbackSignal(item["signal"]),
            target_id=item["target_id"],
            note=item.get("note", ""),
            edited_text=item.get("edited_text"),
            feedback_id=item["feedback_id"],
            created_at=item["created_at"],
        )
        for item in data.get("human_feedback", [])
    ]
    state.facts = list(data.get("facts", []))
    state.strategy = list(data.get("strategy", []))
    state.warnings = list(data.get("warnings", []))
    state.agent_events = [
        AgentEvent(
            agent=AgentRole(item["agent"]),
            status=str(item.get("status", "")),
            stage_label=str(item.get("stage_label", "")),
            detail=str(item.get("detail", "")),
            input_refs=list(item.get("input_refs", []) or []),
            output_refs=list(item.get("output_refs", []) or []),
            failure_signal=str(item.get("failure_signal", "")),
            visible_to_user=bool(item.get("visible_to_user", True)),
            event_id=str(item.get("event_id") or new_id("event")),
            created_at=str(item.get("created_at") or utc_now_iso()),
        )
        for item in data.get("agent_events", [])
    ]
    state.failure_signals = [
        FailureSignal(
            signal_id=str(item.get("signal_id") or new_id("fail")),
            session_id=str(item.get("session_id") or state.session_id),
            draft_version_id=str(item.get("draft_version_id", "")),
            skill_id=str(item.get("skill_id", "")),
            agent_role=str(item.get("agent_role", "")),
            component=str(item.get("component", "")),
            failure_type=str(item.get("failure_type", "")),
            evidence_text=str(item.get("evidence_text", "")),
            severity=str(item.get("severity", "medium")),
            created_at=str(item.get("created_at") or utc_now_iso()),
        )
        for item in data.get("failure_signals", [])
    ]
    return state
