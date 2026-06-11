from __future__ import annotations

from pathlib import Path
import base64
import binascii
import json
import shutil
from dataclasses import asdict
import re
from typing import Any

from evolving_creative_room.agents import (
    CriticPanel,
    DraftWriter,
    EditorAgent,
    IntentInterpreter,
    MemoryCuratorAgent,
    NormSteward,
    ResearchAgent,
    Strategist,
)
from evolving_creative_room.capabilities import (
    CAPABILITY_ALIASES,
    capabilities_view,
    get_capability,
    load_capability_packages,
    seed_missing_capability_packages,
)
from evolving_creative_room.data_health import WorkspaceDoctor
from evolving_creative_room.evaluation import DEFAULT_EVAL_CASES, EvaluationStore, compare_eval_runs, new_eval_run, score_state
from evolving_creative_room.evolution.manifest import HarnessEvolver
from evolving_creative_room.knowledge import KnowledgeBase
from evolving_creative_room.learning import LearningStore
from evolving_creative_room.llm import ChatMessage, LLMClient, LLMError, OpenAICompatibleClient, client_from_env
from evolving_creative_room.memory.store import MemoryRecord, MemoryStore
from evolving_creative_room.metrics import MetricStore
from evolving_creative_room.naturalness import evaluate_naturalness
from evolving_creative_room.observability import CallLogStore, ObservedLLMClient
from evolving_creative_room.projects import ProjectStore
from evolving_creative_room.settings import PROVIDER_DEFAULTS, UserSettingsStore
from evolving_creative_room.skills import SKILL_ALIASES, get_skill, load_skill_packages, seed_missing_skill_packages
from evolving_creative_room.sources import import_public_page
from evolving_creative_room.storage import atomic_write_bytes, atomic_write_json
from evolving_creative_room.models import AgentRole, CreativeIntent, CreativeState, FeedbackSignal, HumanFeedback, new_id, state_to_dict, utc_now_iso


class CreativeRoomRunner:
    """创作房间的本地编排器。"""

    def __init__(self, workspace: Path | str, llm: LLMClient | None = None):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.project_root = Path(__file__).resolve().parents[2]
        self.projects = ProjectStore(self.workspace)
        self.memory = MemoryStore(self.workspace)
        self.knowledge = KnowledgeBase(self.workspace)
        self.learning = LearningStore(self.workspace)
        self.settings = UserSettingsStore(self.workspace)
        self.evaluations = EvaluationStore(self.workspace)
        self.metrics = MetricStore(self.workspace)
        self.call_logs = CallLogStore(self.workspace)
        self.skill_runs_path = self.workspace / "observability" / "skill_runs.jsonl"
        self.skill_runs_path.parent.mkdir(parents=True, exist_ok=True)
        self.collected_assets_path = self.workspace / "collected_assets.json"
        self.published_posts_path = self.workspace / "published_posts.json"
        self.media_dir = self.workspace / "media"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.evolver = HarnessEvolver()
        self.capability_package_paths = seed_missing_capability_packages(self.project_root / "harness" / "capabilities")
        self.capabilities = load_capability_packages(self.project_root / "harness" / "capabilities")
        self.skill_package_paths = seed_missing_skill_packages(self.project_root / "harness" / "skills")
        self.skills = load_skill_packages(self.project_root / "harness" / "skills")
        self.llm_error: str | None = None
        if llm:
            self.llm = ObservedLLMClient(llm, self.call_logs)
        else:
            self.llm = self._load_llm()
        self.intent_agent = IntentInterpreter()

    def run_seed_session(
        self,
        request: str,
        user_preferences: list[str] | None = None,
        feedback_note: str | None = None,
        project_id: str = "default",
        capability_id: str = "",
    ) -> CreativeState:
        intent = CreativeIntent(raw_request=request, user_preferences=user_preferences or [])
        if capability_id:
            intent.project_context["requested_capability_id"] = capability_id
        state = CreativeState(intent=intent, project_id=project_id)
        self.projects.touch(project_id)
        self._apply_skill_context(state)
        self._absorb_context_signals(state, request, evidence_ids=[state.session_id])
        self._run_agent(state, self.intent_agent)
        self._build_context(state)
        self._run_agent(state, ResearchAgent(self.memory, self.knowledge))
        agents = self._select_agents(state)
        skill_run_started = self._start_skill_runs(state, agents)
        state.add_message(
            AgentRole.ORCHESTRATOR,
            "Workflow: " + " -> ".join(agent.role.value for agent in agents),
        )
        for agent in agents:
            self._run_agent(state, agent)

        self._maybe_run_quality_repair_pass(state)
        self._run_agent(state, MemoryCuratorAgent())
        self._finish_skill_runs(state, skill_run_started)

        if feedback_note:
            self._append_feedback(state, FeedbackSignal.EDIT, feedback_note)

        self.finalize(state)
        self.memory.update_session(state.session_id, title=self._suggest_session_title(state))
        return state

    def record_feedback(
        self,
        session_id: str,
        signal: FeedbackSignal,
        note: str = "",
        edited_text: str | None = None,
    ) -> CreativeState:
        state = self.memory.load_state(session_id)
        inferred_signal = self._infer_feedback_signal(note, edited_text) if signal == FeedbackSignal.EDIT else signal
        feedback = self._append_feedback(state, inferred_signal, note, edited_text)
        self._record_failure_signals(state)
        self._absorb_context_signals(state, " ".join([note, edited_text or ""]), evidence_ids=[state.session_id, feedback.feedback_id])
        parent_id = state.drafts[-1].version_id if state.drafts else None
        base_text = state.drafts[-1].content if state.drafts else ""
        if edited_text:
            human_version = state.add_draft(
                edited_text,
                AgentRole.HUMAN,
                rationale="用户直接改写后保存的版本。",
                parent_version_id=parent_id,
            )
            parent_id = human_version.version_id
            base_text = edited_text
        else:
            state.add_message(AgentRole.HUMAN, f"Feedback recorded: {feedback.signal.value}. {feedback.note}")
        if self._revise_from_feedback(state, feedback=feedback, base_text=base_text, parent_version_id=parent_id):
            agents = [CriticPanel(self.llm), NormSteward(), MemoryCuratorAgent()]
            skill_run_started = self._start_skill_runs(state, agents)
            for agent in agents:
                self._run_agent(state, agent)
            self._finish_skill_runs(state, skill_run_started, feedback_id=feedback.feedback_id)
        self.finalize(state)
        return state

    def finalize(self, state: CreativeState) -> None:
        self._record_failure_signals(state)
        self.memory.render_short_term_canvas(state)
        self.memory.capture_l0(state)
        self.memory.extract_l1(state)
        self.memory.upsert_l2_scene(state)
        self.metrics.record(
            "session_finalized",
            session_id=state.session_id,
            project_id=state.project_id,
            metadata={"draft_count": len(state.drafts), "feedback_count": len(state.human_feedback)},
        )
        if state.drafts:
            self.metrics.record("session_success", session_id=state.session_id, project_id=state.project_id)

        if self._harness_settings().get("auto_propose", True):
            manifest = self.evolver.propose(state)
            manifest.write(self.workspace / "evolution" / f"{manifest.manifest_id}.json")

    def latest_manifest(self, session_id: str) -> dict[str, object] | None:
        latest = self._latest_manifest_entry(session_id)
        if not latest:
            return None
        return latest[1]

    def llm_info(self) -> dict[str, object]:
        if self.llm:
            return {"enabled": True, "provider": self.llm.provider, "model": self.llm.model}
        return {"enabled": False, "error": self.llm_error}

    def settings_view(self) -> dict[str, object]:
        view = self.settings.public_view()
        view["runtime_llm"] = self.llm_info()
        return view

    def update_settings(self, payload: dict[str, object]) -> dict[str, object]:
        view = self.settings.update(payload)
        self.llm = self._load_llm()
        view["runtime_llm"] = self.llm_info()
        return view

    def session_view(self, session_id: str) -> dict[str, object]:
        state = self.memory.load_state(session_id)
        canvas_path = self.workspace / "short_term_canvas.mmd"
        session_meta = next((item for item in self.memory.list_sessions(include_completed=True) if item.get("session_id") == session_id), {})
        completed = bool(session_meta.get("completed"))
        learning_candidates = self.learning.list(session_id=session_id) if completed else []
        manifest = self.latest_manifest(session_id)
        return {
            "state": state_to_dict(state),
            "session": session_meta,
            "manifest": manifest,
            "memory": self.memory.list_records(limit=40, project_id=state.project_id),
            "learning": {"candidates": learning_candidates},
            "review": {"items": self._review_items(session_id, learning_candidates=learning_candidates, manifest=manifest) if completed else []},
            "workflow_trace": self._workflow_trace(state),
            "agent_events": self._agent_events_view(state),
            "shared_context": self._shared_context_view(state),
            "canvas": canvas_path.read_text(encoding="utf-8") if canvas_path.exists() else "",
        }

    def workflow_preview(
        self,
        request: str,
        preferences: list[str] | None = None,
        project_id: str = "default",
        capability_id: str = "",
    ) -> dict[str, object]:
        intent = CreativeIntent(raw_request=request, user_preferences=preferences or [])
        if capability_id:
            intent.project_context["requested_capability_id"] = capability_id
        state = CreativeState(intent=intent, project_id=project_id)
        self._apply_skill_context(state)
        self.intent_agent.run(state)
        query = " ".join([request, *(preferences or [])])
        platforms = _detect_platforms(query)
        urls = _detect_urls(query)
        agents = [AgentRole.INTENT_INTERPRETER, AgentRole.RESEARCHER, *[agent.role for agent in self._select_agents(state)]]
        stages = []
        for role in agents:
            stages.append(
                {
                    "role": role.value,
                    "name": _agent_display_name(role),
                    "detail": _agent_stage_detail(role, platforms=platforms, urls=urls),
                }
            )
        return {
            "stages": stages,
            "signals": {
                "platforms": platforms,
                "urls": urls,
                "capabilities": state.intent.project_context.get("capabilities", []),
                "skills": state.intent.project_context.get("skills", []),
                "constraints": state.intent.constraints,
            },
        }

    def capabilities_view(self) -> dict[str, object]:
        return {"capabilities": capabilities_view(self.capabilities)}

    def project_view(self) -> dict[str, object]:
        return {"projects": self.projects.list()}

    def create_project(self, name: str, description: str = "", tags: list[str] | None = None) -> dict[str, object]:
        return asdict(self.projects.create(name=name, description=description, tags=tags))

    def add_knowledge(
        self,
        *,
        kind: str,
        title: str,
        content: str,
        project_id: str = "default",
        source: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        return asdict(self.knowledge.add(kind=kind, title=title, content=content, project_id=project_id, source=source, tags=tags))

    def import_knowledge_url(
        self,
        *,
        url: str,
        kind: str = "norm",
        project_id: str = "default",
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        page = import_public_page(url)
        record = self.knowledge.add(
            kind=kind,
            title=page["title"],
            content=page["content"],
            project_id=project_id,
            source=page["source"],
            tags=tags or ["source", "imported"],
        )
        return asdict(record)

    def knowledge_view(self, query: str = "", kind: str | None = None, project_id: str = "default") -> dict[str, object]:
        if query.strip():
            records = self.knowledge.search(query, kind=kind, project_id=project_id)
        else:
            records = self.knowledge.list(kind=kind, project_id=project_id)
        return {"records": records}

    def memory_view(self, query: str = "", project_id: str = "default") -> dict[str, object]:
        records = self.memory.search_records(query, project_id=project_id) if query.strip() else self.memory.list_records(limit=80, project_id=project_id)
        return {"records": records}

    def preferences_view(self) -> dict[str, object]:
        records = []
        for record in self.memory.list_records(layer="L3", limit=200, project_id="global", include_rejected=False):
            content = str(record.get("content", ""))
            tags = record.get("tags", []) or []
            if content.startswith("偏好：") or content.startswith("长期工作偏好：") or "scope:global" in tags:
                item = dict(record)
                item["display_content"] = content.removeprefix("偏好：").removeprefix("长期工作偏好：")
                records.append(item)
        return {"preferences": records}

    def delete_preference(self, record_id: str) -> dict[str, object]:
        changed = self.memory.review_record(record_id, "deleted")
        if changed:
            self.metrics.record("preference_deleted", metadata={"record_id": record_id})
        return {"changed": changed, "record_id": record_id}

    def assets_view(self, project_id: str = "default") -> dict[str, object]:
        assets = self._read_collected_assets(project_id=project_id)
        for post in self._read_published_posts():
            if post.get("status") != "published":
                continue
            if project_id and post.get("project_id", "default") not in {project_id, "global"}:
                continue
            assets.append(_asset_from_post(post))
        for session in self.memory.list_sessions(include_completed=True):
            if not session.get("completed"):
                continue
            if session.get("asset_deleted"):
                continue
            if project_id and session.get("project_id", "default") != project_id:
                continue
            try:
                state = self.memory.load_state(str(session["session_id"]))
            except FileNotFoundError:
                continue
            assets.append(_asset_from_state(state, title=str(session.get("title") or "")))
        return {"assets": assets}

    def asset_view(self, asset_id: str) -> dict[str, object]:
        try:
            state = self.memory.load_state(asset_id)
        except FileNotFoundError:
            asset = next((item for item in self._read_collected_assets() if item.get("asset_id") == asset_id), None)
            if not asset:
                raise
            return {"asset": asset, "manifest": None}
        session = next((item for item in self.memory.list_sessions(include_completed=True) if item.get("session_id") == asset_id), {})
        if session.get("asset_deleted"):
            raise FileNotFoundError(f"Asset not found: {asset_id}")
        return {"asset": _asset_from_state(state, title=str(session.get("title") or "")), "manifest": self.latest_manifest(asset_id)}

    def delete_asset(self, asset_id: str) -> dict[str, object]:
        if not asset_id:
            raise ValueError("missing_asset_id")
        post = next((item for item in self._read_published_posts() if item.get("post_id") == asset_id), None)
        if post:
            result = self.delete_post(asset_id)
            result["source"] = "published"
            return result
        result = self.memory.hide_asset(asset_id)
        self.metrics.record("asset_deleted", metadata={"asset_id": asset_id, "source": result.get("source", "session")})
        return result

    def publish_defaults(self, work_id: str) -> dict[str, object]:
        asset = self._work_asset(work_id)
        return {
            "work_id": work_id,
            "title": str(asset.get("title") or "未命名作品"),
            "body": str(asset.get("final_content") or ""),
            "cover_url": str(asset.get("image") or asset.get("cover_url") or ""),
            "default_tags": default_publish_tags(),
        }

    def create_publish_draft(self, work_id: str) -> dict[str, object]:
        asset = self._work_asset(work_id)
        posts = self._read_published_posts()
        existing = next((post for post in posts if post.get("work_id") == work_id and post.get("status") == "draft"), None)
        if existing:
            return existing
        now = utc_now_iso()
        post = {
            "post_id": new_id("post"),
            "work_id": work_id,
            "session_id": str(asset.get("session_id") or work_id),
            "project_id": str(asset.get("project_id") or "default"),
            "title": str(asset.get("title") or "未命名作品"),
            "body": str(asset.get("final_content") or ""),
            "tags": [],
            "cover_media_id": "",
            "cover_url": str(asset.get("image") or asset.get("cover_url") or ""),
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "published_at": "",
        }
        posts.insert(0, post)
        self._write_published_posts(posts)
        return post

    def delete_post(self, post_id: str) -> dict[str, object]:
        posts = self._read_published_posts()
        kept = [post for post in posts if post.get("post_id") != post_id]
        if len(kept) == len(posts):
            raise FileNotFoundError(f"Post not found: {post_id}")
        self._write_published_posts(kept)
        self.metrics.record("post_deleted", metadata={"post_id": post_id})
        return {"deleted": True, "post_id": post_id}

    def published_posts_view(self, *, include_drafts: bool = False, project_id: str = "default") -> dict[str, object]:
        posts = self._read_published_posts()
        visible = [
            post
            for post in posts
            if (include_drafts or post.get("status") == "published") and post.get("project_id", project_id) in {project_id, "global"}
        ]
        return {"posts": visible, "default_tags": default_publish_tags()}

    def post_view(self, post_id: str) -> dict[str, object]:
        post = next((item for item in self._read_published_posts() if item.get("post_id") == post_id), None)
        if not post:
            raise FileNotFoundError(f"Post not found: {post_id}")
        return {"post": post, "default_tags": default_publish_tags()}

    def update_post(self, post_id: str, payload: dict[str, object]) -> dict[str, object]:
        posts = self._read_published_posts()
        post = next((item for item in posts if item.get("post_id") == post_id), None)
        if not post:
            raise FileNotFoundError(f"Post not found: {post_id}")
        status = str(payload.get("status") or post.get("status") or "draft").strip()
        if status not in {"draft", "published"}:
            status = "draft"
        post["title"] = str(payload.get("title", post.get("title", ""))).strip() or "未命名作品"
        post["body"] = str(payload.get("body", post.get("body", ""))).strip()
        post["tags"] = normalize_publish_tags(payload.get("tags"))
        post["status"] = status
        cover_url = str(payload.get("cover_url", "")).strip()
        if cover_url:
            post["cover_url"] = cover_url
        media_payload = str(payload.get("cover_data_url", "")).strip()
        if media_payload:
            media = self.save_media_data_url(media_payload, source="uploaded")
            post["cover_media_id"] = media["media_id"]
            post["cover_url"] = media["public_url"]
        post["updated_at"] = utc_now_iso()
        if status == "published" and not post.get("published_at"):
            post["published_at"] = post["updated_at"]
            self.metrics.record(
                "post_published",
                session_id=str(post.get("session_id", "")),
                metadata={"post_id": post_id, "tag_count": len(post.get("tags", []))},
            )
        self._write_published_posts(posts)
        return post

    def save_media_data_url(self, data_url: str, *, source: str = "uploaded") -> dict[str, object]:
        match = re.match(r"^data:(image/(png|jpeg|jpg|webp));base64,(.+)$", data_url, flags=re.I | re.S)
        if not match:
            raise ValueError("只支持 png、jpg、webp 图片。")
        mime_type = match.group(1).lower().replace("image/jpg", "image/jpeg")
        extension = "jpg" if mime_type == "image/jpeg" else mime_type.rsplit("/", 1)[-1]
        try:
            content = base64.b64decode(match.group(3), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("图片数据无法解析。") from exc
        if len(content) > 4 * 1024 * 1024:
            raise ValueError("图片不能超过 4MB。")
        media_id = new_id("media")
        path = self.media_dir / f"{media_id}.{extension}"
        atomic_write_bytes(path, content)
        return {
            "media_id": media_id,
            "file_path": str(path),
            "public_url": f"/media/{path.name}",
            "mime_type": mime_type,
            "size": len(content),
            "source": source,
            "created_at": utc_now_iso(),
        }

    def collect_asset(self, payload: dict[str, object]) -> dict[str, object]:
        asset = self._upsert_inspiration_asset(payload, collected=True, liked=bool(payload.get("liked", False)))
        self.metrics.record(
            "session_success",
            session_id=str(asset.get("session_id", "")),
            project_id=str(asset.get("project_id", "default")),
            metadata={"source": "asset_collect", "asset_id": asset.get("asset_id", "")},
        )
        return asset

    def uncollect_asset(self, payload: dict[str, object]) -> dict[str, object]:
        return self._upsert_inspiration_asset(payload, collected=False, liked=bool(payload.get("liked", False)))

    def like_asset(self, payload: dict[str, object]) -> dict[str, object]:
        return self._upsert_inspiration_asset(payload, collected=bool(payload.get("collected", False)), liked=bool(payload.get("liked", True)))

    def _upsert_inspiration_asset(self, payload: dict[str, object], *, collected: bool, liked: bool) -> dict[str, object]:
        assets = self._read_collected_assets()
        source_id = str(payload.get("source_id") or payload.get("asset_id") or "").strip()
        existing = next((item for item in assets if source_id and item.get("source_id") == source_id), None)
        now = utc_now_iso()
        asset = existing or {
            "asset_id": new_id("asset"),
            "source": "inspiration",
            "source_id": source_id,
            "created_at": now,
        }
        asset.update(
            {
                "project_id": str(payload.get("project_id", "default")).strip() or "default",
                "title": str(payload.get("title", "未命名资产")).strip() or "未命名资产",
                "prompt": str(payload.get("prompt", "")).strip(),
                "final_content": str(payload.get("final_content", "")).strip(),
                "goal": str(payload.get("goal", "")).strip(),
                "category": str(payload.get("category", "discover")).strip() or "discover",
                "image": str(payload.get("image", "")).strip(),
                "skills": _as_string_list(payload.get("skills")),
                "platforms": _as_string_list(payload.get("platforms")),
                "liked": liked,
                "collected": collected,
                "updated_at": now,
            }
        )
        if existing is None:
            assets.insert(0, asset)
        self._write_collected_assets(assets)
        return asset

    def review_memory(self, record_id: str, status: str) -> dict[str, object]:
        changed = self.memory.review_record(record_id, status)
        return {"changed": changed, "record_id": record_id, "status": status}

    def apply_learning(self, candidate_id: str, action: str) -> dict[str, object]:
        result = self.learning.apply(candidate_id, action, self.memory)
        candidate = result.get("candidate", {})
        status = str(candidate.get("status", ""))
        if status in {"project_active", "global_active"}:
            self.metrics.record(
                "learning_confirmed",
                session_id=str(candidate.get("session_id", "")),
                project_id=str(candidate.get("project_id", "default")),
                metadata={"status": status, "kind": candidate.get("kind", "")},
            )
        elif status in {"ignored", "rejected"}:
            self.metrics.record(
                "learning_rejected",
                session_id=str(candidate.get("session_id", "")),
                project_id=str(candidate.get("project_id", "default")),
                metadata={"status": status, "kind": candidate.get("kind", "")},
            )
        return result

    def accept_review_item(self, session_id: str, item_id: str, *, scope: str = "", reviewer_note: str = "") -> dict[str, object]:
        kind, target_id = self._parse_review_item_id(item_id)
        if kind == "learning":
            candidate = self._find_learning_candidate(target_id, session_id=session_id)
            source_type = self._review_source_type(candidate)
            action = self._learning_action_for_review(candidate, scope=scope)
            result = self.apply_learning(target_id, action)
            return {
                "item_id": item_id,
                "status": "accepted",
                "source_type": source_type,
                "action": action,
                "result": result,
            }
        if kind == "workflow":
            latest = self._latest_ab_for_proposal(target_id)
            if not latest:
                self._update_proposal_status(session_id, target_id, "needs_validation")
                self.metrics.record(
                    "review_item_needs_validation",
                    session_id=session_id,
                    metadata={"proposal_id": target_id},
                )
                return {
                    "item_id": item_id,
                    "status": "blocked",
                    "source_type": "assistant_workflow",
                    "message": "我会先把它作为待验证的改进点保留，证据足够后再应用。",
                }
            result = self.apply_evolution(
                session_id,
                target_id,
                reviewer_note=reviewer_note or "用户在本次复盘中允许调整助理工作方式。",
            )
            return {
                "item_id": item_id,
                "status": "accepted",
                "source_type": "assistant_workflow",
                "result": result,
            }
        raise ValueError(f"Unknown review item type: {kind}")

    def skip_review_item(self, session_id: str, item_id: str, *, reviewer_note: str = "") -> dict[str, object]:
        kind, target_id = self._parse_review_item_id(item_id)
        if kind == "learning":
            result = self.apply_learning(target_id, "ignore")
            return {"item_id": item_id, "status": "skipped", "source_type": "memory", "result": result}
        if kind == "workflow":
            result = self.ignore_evolution(session_id, target_id, reviewer_note=reviewer_note or "用户在本次复盘中选择跳过。")
            return {"item_id": item_id, "status": "skipped", "source_type": "assistant_workflow", "result": result}
        raise ValueError(f"Unknown review item type: {kind}")

    def apply_evolution(self, session_id: str, proposal_id: str, reviewer_note: str = "") -> dict[str, object]:
        manifest = self.latest_manifest(session_id)
        if not manifest:
            raise ValueError(f"No manifest for session: {session_id}")
        gate = self._proposal_apply_gate(proposal_id, reviewer_note=reviewer_note)
        result = self.evolver.apply_proposal(
            project_root=self.project_root,
            manifest=manifest,
            proposal_id=proposal_id,
            reviewer_note=reviewer_note,
        )
        result["validation_gate"] = gate
        self._update_proposal_status(session_id, proposal_id, "applied_pending_validation")
        self.metrics.record(
            "evolution_proposal_applied",
            session_id=session_id,
            metadata={"proposal_id": proposal_id, "gate": gate.get("status", "")},
        )
        return result

    def ignore_evolution(self, session_id: str, proposal_id: str, reviewer_note: str = "") -> dict[str, object]:
        manifest = self._update_proposal_status(session_id, proposal_id, "ignored")
        self.metrics.record(
            "evolution_proposal_ignored",
            session_id=session_id,
            metadata={"proposal_id": proposal_id, "reviewer_note": reviewer_note},
        )
        return {"proposal_id": proposal_id, "status": "ignored", "manifest_id": manifest.get("manifest_id", "")}

    def run_evaluation_suite(self) -> dict[str, object]:
        run = self._run_cases(DEFAULT_EVAL_CASES, kind="single")
        self.evaluations.write(run)
        return {
            "run_id": run.run_id,
            "created_at": run.created_at,
            "kind": run.kind,
            "average_score": run.average_score,
            "results": [asdict(item) for item in run.results],
        }

    def run_ab_evaluation(self, session_id: str | None = None, proposal_id: str | None = None) -> dict[str, object]:
        proposal = self._find_proposal(session_id=session_id, proposal_id=proposal_id)
        candidate_note = ""
        metadata: dict[str, object] = {"mode": "dry_run", "baseline_harness_version": "active", "candidate_harness_version": "candidate"}
        candidate_skill_root: Path | None = None
        if proposal:
            proposed_change = str(proposal.get("proposed_change") or proposal.get("targeted_fix") or "").strip()
            if not proposed_change:
                return {
                    "error": "invalid_candidate",
                    "reason": "候选 harness 修改为空，无法进行有效 A/B dry-run。",
                    "metadata": metadata,
                }
            candidate_note = "候选 harness 修改：" + proposed_change
            metadata.update(
                {
                    "proposal_id": proposal.get("proposal_id", ""),
                    "target_component": proposal.get("target_component", ""),
                    "predicted_metric": proposal.get("predicted_metric", ""),
                    "proposed_change": proposed_change,
                }
            )
            candidate_harness_root = self._materialize_candidate_harness(proposal)
            candidate_skill_root = candidate_harness_root / "skills"
            metadata["candidate_harness_path"] = str(candidate_harness_root)
        else:
            candidate_note = "候选 harness 修改：强化资料召回、平台规范检查和用户偏好记忆。"
            metadata["proposal_id"] = ""

        baseline = self._run_cases(DEFAULT_EVAL_CASES, kind="ab_baseline", metadata=metadata)
        candidate = self._run_cases(
            DEFAULT_EVAL_CASES,
            kind="ab_candidate",
            extra_preferences=[candidate_note],
            metadata=metadata,
            skill_root=candidate_skill_root,
        )
        self.evaluations.write(baseline)
        self.evaluations.write(candidate)
        comparison = compare_eval_runs(baseline, candidate)
        comparison["metadata"] = metadata
        path = self.workspace / "evaluations" / f"ab_{candidate.run_id}.json"
        atomic_write_json(path, comparison)
        return comparison

    def evaluation_view(self) -> dict[str, object]:
        return {"runs": self.evaluations.list()}

    def observability_view(self) -> dict[str, object]:
        return {
            "summary": self.call_logs.summary(),
            "calls": self.call_logs.list(),
            "skill_runs": self._list_skill_runs(),
            "product_metrics": self.metrics.summary(),
            "metric_events": self.metrics.list(limit=120),
        }

    def data_doctor(self) -> dict[str, object]:
        return WorkspaceDoctor(self.workspace).run()

    def rebuild_indexes(self) -> dict[str, object]:
        memory = self.memory.rebuild_index()
        knowledge = self.knowledge.rebuild_index()
        self.metrics.record(
            "workspace_indexes_rebuilt",
            metadata={
                "memory_records_indexed": memory.get("records_indexed", 0),
                "knowledge_records_indexed": knowledge.get("records_indexed", 0),
            },
        )
        return {"memory": memory, "knowledge": knowledge, "doctor": self.data_doctor()}

    def update_session_meta(
        self,
        session_id: str,
        title: str | None = None,
        pinned: bool | None = None,
        completed: bool | None = None,
        archive: str | None = None,
        work_category: str | None = None,
    ) -> dict[str, object]:
        return self.memory.update_session(
            session_id,
            title=title,
            pinned=pinned,
            completed=completed,
            archive=archive,
            work_category=work_category,
        )

    def complete_session(
        self,
        session_id: str,
        completed: bool,
        work_category: str = "",
        revoke_learning_on_reopen: bool = True,
    ) -> dict[str, object]:
        result = self.update_session_meta(
            session_id,
            completed=completed,
            archive="works" if completed else None,
            work_category=work_category,
        )
        if completed:
            state = self.memory.load_state(session_id)
            memory_policy = self._memory_policy()
            candidates = self.learning.suggest_from_state(
                state,
                min_confidence=float(memory_policy.get("min_confidence", 0.35)),
                limit=int(memory_policy.get("candidate_limit", 3)),
            )
            if candidates:
                self.metrics.record(
                    "learning_candidate_created",
                    value=float(len(candidates)),
                    session_id=session_id,
                    project_id=state.project_id,
                    metadata={"source": "completion"},
                )
        else:
            if revoke_learning_on_reopen:
                result["revoked_learning_count"] = self.learning.revoke_for_session(session_id, status="hidden")
                result["revoked_confirmed_learning_count"] = self.memory.revoke_confirmed_learning_for_session(session_id)
            else:
                result["revoked_learning_count"] = 0
                result["revoked_confirmed_learning_count"] = 0
        return result

    def delete_session(self, session_id: str, mode: str = "revoke_memory") -> dict[str, object]:
        result = self.memory.delete_session(session_id, mode=mode)
        if mode in {"revoke_memory", "full"}:
            result["revoked_learning_count"] = self.learning.revoke_for_session(session_id)
        else:
            result["revoked_learning_count"] = 0
        removed_manifests = 0
        if mode == "full":
            for path in (self.workspace / "evolution").glob("manifest_*.json"):
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("session_id") == session_id:
                    path.unlink()
                    removed_manifests += 1
        result["removed_manifests"] = removed_manifests
        return result

    def test_llm(self) -> dict[str, object]:
        if not self.llm:
            return {"ok": False, "message": self.llm_error or "当前使用本地 stub。"}
        try:
            response = self.llm.chat(
                [
                    ChatMessage("system", "你是 EcRoom 的连通性测试。"),
                    ChatMessage("user", "请只回复：连接成功"),
                ],
                max_tokens=20,
                temperature=0.1,
            )
            return {
                "ok": True,
                "provider": response.provider,
                "model": response.model,
                "message": response.content,
                "usage": response.usage,
            }
        except LLMError as exc:
            return {"ok": False, "message": str(exc)}

    def _run_cases(
        self,
        cases: list[object],
        *,
        kind: str,
        extra_preferences: list[str] | None = None,
        metadata: dict[str, object] | None = None,
        skill_root: Path | None = None,
    ):
        results = []
        original_skills = self.skills
        if skill_root:
            self.skills = load_skill_packages(skill_root)
        try:
            for case in cases:
                preferences = [*case.preferences, *(extra_preferences or [])]
                state = self.run_seed_session(case.request, user_preferences=preferences)
                result = score_state(state, case.expected_signals)
                result.case_name = case.name
                results.append(result)
        finally:
            self.skills = original_skills
        return new_eval_run(results, kind=kind, metadata=metadata)

    def _find_proposal(self, session_id: str | None = None, proposal_id: str | None = None) -> dict[str, object] | None:
        manifests = []
        for path in (self.workspace / "evolution").glob("manifest_*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if session_id and data.get("session_id") != session_id:
                continue
            manifests.append((path.stat().st_mtime, data))
        for _, manifest in sorted(manifests, key=lambda item: item[0], reverse=True):
            for proposal in manifest.get("proposals", []):
                if not proposal_id or proposal.get("proposal_id") == proposal_id:
                    return proposal
        return None

    def _review_items(
        self,
        session_id: str,
        *,
        learning_candidates: list[dict[str, object]],
        manifest: dict[str, object] | None,
    ) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        pending_learning = [candidate for candidate in learning_candidates if candidate.get("status") == "candidate"]
        pending_learning.sort(key=lambda item: float(item.get("confidence", 0.0) or 0.0), reverse=True)
        for candidate in pending_learning[:3]:
            if candidate.get("status") != "candidate":
                continue
            item = self._learning_review_item(candidate)
            if item:
                items.append(item)
        workflow_items: list[dict[str, object]] = []
        for proposal in (manifest or {}).get("proposals", []) if isinstance(manifest, dict) else []:
            if not isinstance(proposal, dict):
                continue
            if proposal.get("status", "proposed") not in {"proposed", "pending"}:
                continue
            item = self._workflow_review_item(session_id, proposal)
            if item:
                workflow_items.append(item)
        items.extend(workflow_items[:2])
        return items[:5]

    def _learning_review_item(self, candidate: dict[str, object]) -> dict[str, object] | None:
        candidate_id = str(candidate.get("candidate_id", "")).strip()
        content = str(candidate.get("content", "")).strip()
        if not candidate_id or not content:
            return None
        source_type = self._review_source_type(candidate)
        suggested_scope = self._review_suggested_scope(candidate)
        if source_type == "memory":
            title = "记住这个偏好"
            impact = str(candidate.get("effect") or "以后类似创作会参考这条偏好。")
            accept_label = "保存这条"
        else:
            title = "保存为项目规则"
            impact = str(candidate.get("effect") or "后续同项目或相关平台创作会参考这条规则。")
            accept_label = "保存为项目规则"
        return {
            "item_id": f"review:learning:{candidate_id}",
            "session_id": candidate.get("session_id", ""),
            "source_type": source_type,
            "title": title,
            "suggestion": content,
            "reason": candidate.get("reason", "来自这次创作过程中的稳定信号。"),
            "evidence_summary": self._candidate_evidence_summary(candidate),
            "impact": impact,
            "suggested_scope": suggested_scope,
            "allowed_scopes": self._review_allowed_scopes(candidate),
            "confidence": candidate.get("confidence", 0.0),
            "status": "pending",
            "accept_label": accept_label,
            "skip_label": "跳过",
            "technical_ref": {
                "candidate_id": candidate_id,
                "kind": candidate.get("kind", ""),
                "target_object": candidate.get("target_object", ""),
                "evidence_ids": candidate.get("evidence_ids", []),
            },
        }

    def _workflow_review_item(self, session_id: str, proposal: dict[str, object]) -> dict[str, object] | None:
        proposal_id = str(proposal.get("proposal_id", "")).strip()
        if not proposal_id:
            return None
        root_cause = str(proposal.get("root_cause", ""))
        evidence = proposal.get("failure_evidence", [])
        if "Insufficient feedback evidence" in root_cause:
            return None
        if isinstance(evidence, list) and evidence == ["No strong failure pattern yet."]:
            return None
        title, suggestion, impact, scope = self._workflow_user_copy(proposal)
        evidence_count = len(evidence) if isinstance(evidence, list) else 0
        validation = self._latest_ab_for_proposal(proposal_id)
        status = "pending"
        return {
            "item_id": f"review:workflow:{proposal_id}",
            "session_id": session_id,
            "source_type": "assistant_workflow",
            "title": title,
            "suggestion": suggestion,
            "reason": proposal.get("root_cause", "这次创作暴露出一个可复盘的处理方式问题。"),
            "evidence_summary": f"{evidence_count} 条创作证据" if evidence_count else "证据仍偏少，需要谨慎处理",
            "impact": impact,
            "suggested_scope": scope,
            "allowed_scopes": [scope],
            "confidence": 0.72 if validation else 0.48,
            "status": status,
            "accept_label": "允许这样调整",
            "skip_label": "跳过",
            "needs_validation": not bool(validation),
            "technical_ref": {
                "proposal_id": proposal_id,
                "target_component": proposal.get("target_component", ""),
                "proposed_change": proposal.get("proposed_change") or proposal.get("targeted_fix") or "",
                "risk": proposal.get("risk", ""),
                "validation_plan": proposal.get("validation_plan", ""),
                "rollback_plan": proposal.get("rollback_plan", ""),
                "predicted_metric": proposal.get("predicted_metric", ""),
                "evidence_ids": proposal.get("evidence_ids", []),
            },
        }

    def _review_source_type(self, candidate: dict[str, object]) -> str:
        kind = str(candidate.get("kind", ""))
        if kind in {"project_rule", "platform_rule"}:
            return "project_rule"
        return "memory"

    def _review_suggested_scope(self, candidate: dict[str, object]) -> str:
        kind = str(candidate.get("kind", ""))
        scope = str(candidate.get("suggested_scope", "") or "project")
        if kind == "project_rule":
            return "project"
        if kind == "platform_rule":
            return "platform"
        if scope == "global":
            return "global"
        return "project"

    def _review_allowed_scopes(self, candidate: dict[str, object]) -> list[str]:
        kind = str(candidate.get("kind", ""))
        if kind == "project_rule":
            return ["project"]
        if kind == "platform_rule":
            return ["platform", "project"]
        if str(candidate.get("suggested_scope", "")) == "global":
            return ["global", "project"]
        return ["project", "global"]

    def _learning_action_for_review(self, candidate: dict[str, object], *, scope: str = "") -> str:
        requested = scope.strip()
        if requested in {"global", "project"}:
            return requested
        kind = str(candidate.get("kind", ""))
        if kind == "project_rule":
            return "project"
        if kind == "platform_rule":
            return "global" if self._review_suggested_scope(candidate) == "platform" else "project"
        return "global" if str(candidate.get("suggested_scope", "")) == "global" else "project"

    def _candidate_evidence_summary(self, candidate: dict[str, object]) -> str:
        evidence_ids = candidate.get("evidence_ids", [])
        count = len(evidence_ids) if isinstance(evidence_ids, list) else 0
        confidence = candidate.get("confidence", 0)
        try:
            percent = f"{round(float(confidence) * 100)}%"
        except (TypeError, ValueError):
            percent = "待评估"
        return f"{count or 1} 条本次创作信号，置信度 {percent}"

    def _workflow_user_copy(self, proposal: dict[str, object]) -> tuple[str, str, str, str]:
        target = str(proposal.get("target_component", ""))
        change = str(proposal.get("proposed_change") or proposal.get("targeted_fix") or "")
        lowered = change.lower()
        if "canon" in target or "canon" in lowered:
            return (
                "调整助理工作方式",
                "以后处理角色或世界观内容时，我会先检查设定一致性，再改成适合发布的版本。",
                "类似任务会多一次角色口吻、时间线和不可改动设定检查，减少跑偏。",
                "当前项目和类似叙事任务",
            )
        if "norm" in target or "platform" in lowered:
            return (
                "调整助理工作方式",
                "以后处理平台发布内容时，我会把硬规则、平台习惯和项目要求分开判断。",
                "规范提醒会更精确，减少平台风格覆盖原本创作语气。",
                "对应平台任务",
            )
        if "creative_quality" in target or "naturalness" in lowered or "template" in lowered:
            return (
                "调整助理工作方式",
                "以后我会更主动把过程说明移出正文，只把可用内容留给你。",
                "发布草稿会更干净，但早期头脑风暴仍会保留必要说明。",
                "类似文案改稿任务",
            )
        return (
            "调整助理工作方式",
            user_facing_change(change, str(proposal.get("expected_improvement", ""))),
            str(proposal.get("risk", "会改变类似任务的处理顺序，需要复核。")),
            "当前项目或类似创作任务",
        )

    def _parse_review_item_id(self, item_id: str) -> tuple[str, str]:
        parts = item_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "review":
            raise ValueError(f"Invalid review item id: {item_id}")
        if parts[1] not in {"learning", "workflow"}:
            raise ValueError(f"Unknown review item id type: {parts[1]}")
        return parts[1], parts[2]

    def _find_learning_candidate(self, candidate_id: str, *, session_id: str) -> dict[str, object]:
        for candidate in self.learning.list(session_id=session_id, limit=200):
            if candidate.get("candidate_id") == candidate_id:
                return candidate
        raise ValueError(f"Learning candidate not found: {candidate_id}")

    def _latest_manifest_entry(self, session_id: str) -> tuple[Path, dict[str, object]] | None:
        manifests: list[tuple[float, Path, dict[str, object]]] = []
        for path in (self.workspace / "evolution").glob("manifest_*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("session_id") == session_id:
                manifests.append((path.stat().st_mtime, path, data))
        if not manifests:
            return None
        _, path, data = sorted(manifests, key=lambda item: item[0], reverse=True)[0]
        return path, data

    def _update_proposal_status(self, session_id: str, proposal_id: str, status: str) -> dict[str, object]:
        entry = self._latest_manifest_entry(session_id)
        if not entry:
            raise ValueError(f"No manifest for session: {session_id}")
        path, manifest = entry
        proposals = manifest.get("proposals", [])
        if not isinstance(proposals, list):
            raise ValueError("Manifest proposals are invalid.")
        for proposal in proposals:
            if isinstance(proposal, dict) and proposal.get("proposal_id") == proposal_id:
                proposal["status"] = status
                proposal["reviewed_at"] = utc_now_iso()
                atomic_write_json(path, manifest)
                return manifest
        raise ValueError(f"Proposal not found: {proposal_id}")

    def _proposal_apply_gate(self, proposal_id: str, *, reviewer_note: str = "") -> dict[str, object]:
        latest = self._latest_ab_for_proposal(proposal_id)
        if not latest:
            if reviewer_note.strip():
                return {
                    "status": "manual_review_required",
                    "reason": "未找到 A/B 结果；本次依赖人工说明应用，后续仍需验证。",
                }
            raise ValueError("Applying an evolution proposal requires A/B evaluation or reviewer note.")
        readiness = str(latest.get("readiness") or latest.get("decision") or "")
        if readiness == "blocked" and "override" not in reviewer_note.lower() and "强制" not in reviewer_note:
            raise ValueError("A/B gate blocked this proposal; add an explicit override reviewer note to apply.")
        return {
            "status": readiness or "needs_review",
            "reason": "; ".join(str(item) for item in latest.get("readiness_reasons", []) or []),
            "ab_result": str(latest.get("candidate_run_id", "")),
        }

    def _latest_ab_for_proposal(self, proposal_id: str) -> dict[str, object] | None:
        matches = []
        for path in (self.workspace / "evaluations").glob("ab_*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            metadata = data.get("metadata", {})
            if isinstance(metadata, dict) and metadata.get("proposal_id") == proposal_id:
                matches.append((path.stat().st_mtime, data))
        if not matches:
            return None
        return sorted(matches, key=lambda item: item[0], reverse=True)[0][1]

    def _maybe_run_quality_repair_pass(self, state: CreativeState) -> bool:
        if state.intent.project_context.get("quality_repair_done"):
            return False
        if not state.drafts:
            return False
        self._record_failure_signals(state)
        profile = evaluate_naturalness(
            state.drafts[-1].content,
            request=state.intent.raw_request,
            feedback=[item.note for item in state.human_feedback if item.note],
            platforms=_detect_platforms(state.intent.raw_request),
        )
        repair_signals = {"over_explained", "template_style", "generic_language", "feedback_target_missed", "platform_overfit"}
        failures = {item.failure_type for item in state.failure_signals}
        if profile.score >= 0.78 and not failures.intersection(repair_signals):
            return False
        state.intent.project_context["quality_repair_done"] = True
        state.add_event(
            AgentRole.ORCHESTRATOR,
            "running",
            "质量返修",
            "评审发现自然度或反馈响应风险，触发一次受控返修。",
            input_refs=[state.drafts[-1].version_id],
            failure_signal=",".join(sorted(failures.intersection(repair_signals))) or ",".join(profile.signals),
        )
        state.add_message(AgentRole.ORCHESTRATOR, "Quality repair pass: editor -> critic.")
        self._run_agent(state, EditorAgent(self.llm))
        self._run_agent(state, CriticPanel(self.llm))
        if _detect_platforms(state.intent.raw_request) or any(term in state.intent.raw_request for term in ["角色", "世界观", "剧情", "canon"]):
            self._run_agent(state, NormSteward())
        self._record_failure_signals(state)
        state.add_event(
            AgentRole.ORCHESTRATOR,
            "completed",
            "质量返修",
            "一次受控返修已完成；如仍有问题，只记录信号，不继续循环。",
            output_refs=[state.drafts[-1].version_id],
        )
        self.metrics.record(
            "quality_repair_pass",
            session_id=state.session_id,
            project_id=state.project_id,
            metadata={"naturalness_score": profile.score, "signals": profile.signals},
        )
        return True

    def _materialize_candidate_harness(self, proposal: dict[str, object]) -> Path:
        proposal_id = str(proposal.get("proposal_id") or new_id("candidate"))
        candidate_root = self.workspace / "evaluations" / "candidates" / proposal_id
        candidate_project = candidate_root / "project"
        candidate_harness = candidate_project / "harness"
        if candidate_root.exists():
            shutil.rmtree(candidate_root)
        candidate_harness.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.project_root / "harness", candidate_harness)
        manifest = {
            "manifest_id": f"dry_{proposal_id}",
            "session_id": str(proposal.get("session_id", "")),
            "proposals": [proposal],
        }
        self.evolver.apply_proposal(
            project_root=candidate_project,
            manifest=manifest,
            proposal_id=proposal_id,
            reviewer_note="A/B dry-run candidate copy.",
        )
        return candidate_harness

    def _read_collected_assets(self, project_id: str | None = None) -> list[dict[str, object]]:
        if not self.collected_assets_path.exists():
            return []
        data = json.loads(self.collected_assets_path.read_text(encoding="utf-8"))
        assets = data if isinstance(data, list) else []
        if project_id:
            assets = [item for item in assets if item.get("project_id", "default") in {project_id, "global"}]
        return assets

    def _write_collected_assets(self, assets: list[dict[str, object]]) -> None:
        atomic_write_json(self.collected_assets_path, assets)

    def _work_asset(self, work_id: str) -> dict[str, object]:
        try:
            state = self.memory.load_state(work_id)
        except FileNotFoundError:
            asset = next((item for item in self._read_collected_assets() if item.get("asset_id") == work_id), None)
            if not asset:
                raise
            return asset
        session = next((item for item in self.memory.list_sessions(include_completed=True) if item.get("session_id") == work_id), {})
        return _asset_from_state(state, title=str(session.get("title") or ""))

    def _read_published_posts(self) -> list[dict[str, object]]:
        if not self.published_posts_path.exists():
            return []
        data = json.loads(self.published_posts_path.read_text(encoding="utf-8"))
        posts = data if isinstance(data, list) else []
        return sorted(posts, key=lambda item: str(item.get("updated_at") or item.get("published_at") or ""), reverse=True)

    def _write_published_posts(self, posts: list[dict[str, object]]) -> None:
        atomic_write_json(self.published_posts_path, posts)

    def _append_feedback(
        self,
        state: CreativeState,
        signal: FeedbackSignal,
        note: str = "",
        edited_text: str | None = None,
    ) -> HumanFeedback:
        target = state.drafts[-1].version_id if state.drafts else state.session_id
        feedback = HumanFeedback(
            signal=signal,
            target_id=target,
            note=note,
            edited_text=edited_text,
        )
        state.human_feedback.append(feedback)
        return feedback

    def _revise_from_feedback(
        self,
        state: CreativeState,
        *,
        feedback: HumanFeedback,
        base_text: str,
        parent_version_id: str | None,
    ) -> bool:
        if not base_text.strip():
            return False
        feedback_text = feedback.note or "用户希望继续修改。"
        if self.llm:
            try:
                response = self.llm.chat(
                    [
                        ChatMessage(
                            "system",
                            "你在 EcRoom 里负责根据用户反馈继续改稿。输出完整新版本，不要解释过程。",
                        ),
                        ChatMessage(
                            "user",
                            "原始需求："
                            + state.intent.raw_request
                            + "\n用户偏好："
                            + ("；".join(state.intent.user_preferences) or "暂无")
                            + "\n已沉淀上下文："
                            + ("；".join(state.facts[:10]) or "暂无")
                            + "\n用户反馈："
                            + feedback_text
                            + ("\n用户直接改稿：\n" + feedback.edited_text if feedback.edited_text else "")
                            + "\n\n上一版：\n"
                            + base_text
                            + "\n\n请生成修改后的完整版本。保留有效内容，明显响应用户反馈。",
                        ),
                    ],
                    max_tokens=1300,
                    temperature=0.7,
                )
            except LLMError as exc:
                state.add_message(AgentRole.ORCHESTRATOR, f"LLM revision failed: {exc}")
            else:
                version = state.add_draft(
                    response.content,
                    AgentRole.EDITOR,
                    rationale=f"根据用户反馈由 {response.provider}/{response.model} 生成新版本。",
                    parent_version_id=parent_version_id,
                )
                state.add_message(
                    AgentRole.EDITOR,
                    f"Revised {parent_version_id or state.session_id} into {version.version_id} from user feedback.",
                    llm_provider=response.provider,
                    llm_model=response.model,
                )
                return True

        fallback = (
            base_text
            + "\n\n"
            + "下一版修改方向："
            + feedback_text
            + "\n这条反馈已被记录为后续偏好信号，下一次生成会优先参考。"
        )
        state.add_draft(
            fallback,
            AgentRole.EDITOR,
            rationale="本地模式下根据用户反馈追加修改方向。",
            parent_version_id=parent_version_id,
        )
        state.add_message(AgentRole.EDITOR, "Created local feedback revision.")
        return True

    def _build_context(self, state: CreativeState) -> None:
        query = " ".join([state.intent.raw_request, *state.intent.user_preferences])
        memory_hits = self.memory.search_records(query, limit=6, project_id=state.project_id)
        knowledge_hits = self.knowledge.search(query, limit=8, project_id=state.project_id)

        for item in memory_hits:
            content = str(item.get("content", ""))
            if content and content not in state.facts:
                state.facts.append(f"记忆：{content}")
        for item in knowledge_hits:
            title = str(item.get("title", ""))
            content = str(item.get("content", ""))
            if title or content:
                fact = f"{item.get('kind', 'knowledge')}：{title} - {content[:180]}"
                if fact not in state.facts:
                    state.facts.append(fact)

        if memory_hits or knowledge_hits:
            state.add_message(
                AgentRole.CONTEXT_BUILDER,
                f"召回 {len(memory_hits)} 条记忆、{len(knowledge_hits)} 条资料/规范。",
            )

    def _apply_skill_context(self, state: CreativeState) -> None:
        requested_skills = []
        requested = state.intent.project_context.get("requested_capability_id")
        if requested:
            package = self._get_capability(str(requested))
            if package:
                requested_skills.append(package)
        requested_list = state.intent.project_context.get("requested_capabilities", [])
        if isinstance(requested_list, list):
            for raw in requested_list:
                package = self._get_capability(str(raw))
                if package:
                    requested_skills.append(package)
        for preference in state.intent.user_preferences:
            capability_match = re.search(r"(?:使用能力包|开始方式)[:：]\s*([a-zA-Z0-9_\-\u4e00-\u9fff]+)", preference)
            skill_match = re.search(r"使用技能[:：]\s*([a-zA-Z0-9_\-\u4e00-\u9fff]+)", preference)
            if capability_match:
                raw = capability_match.group(1).strip()
                skill = self._get_capability(raw)
            elif skill_match:
                raw = skill_match.group(1).strip()
                skill = self._get_legacy_skill(raw) or next((item for item in self.skills.values() if item.name == raw), None)
            else:
                continue
            if skill:
                requested_skills.append(skill)
        skill_plan = self._compose_skill_plan(requested_skills)
        for skill in skill_plan["active"]:
            is_capability = bool(getattr(skill, "capability_id", ""))
            if is_capability and skill.skill_id not in state.intent.project_context.setdefault("capabilities", []):
                state.intent.project_context["capabilities"].append(skill.skill_id)
            if skill.skill_id not in state.intent.project_context.setdefault("skills", []):
                state.intent.project_context["skills"].append(skill.skill_id)
            fact_prefix = "能力包" if is_capability else "技能包"
            detail_prefix = "能力包" if is_capability else "技能"
            if f"{fact_prefix}：{skill.name} {skill.version} - {skill.workflow_hint}" not in state.facts:
                state.intent.constraints.extend(item for item in skill.constraints if item not in state.intent.constraints)
                state.intent.evaluation_criteria.extend(item for item in skill.evaluation if item not in state.intent.evaluation_criteria)
                state.facts.append(f"{fact_prefix}：{skill.name} {skill.version} - {skill.workflow_hint}")
                state.facts.append(f"{detail_prefix}触发：" + skill.trigger)
                state.facts.append(f"{detail_prefix}输入规格：" + "；".join(skill.input_contract))
                state.facts.append(f"{detail_prefix}流程：" + " -> ".join(skill.workflow_steps))
                state.facts.append(f"{detail_prefix}工具契约：" + "；".join(skill.tool_contract or ["无需外部工具"]))
                state.facts.append(f"{detail_prefix}输出契约：" + "；".join(skill.output_contract))
                state.facts.append(f"{detail_prefix}失败处理：" + "；".join(skill.failure_policy or ["按通用创作流程处理"]))
                if is_capability:
                    state.intent.project_context.setdefault("capability_workflows", {})[skill.skill_id] = {
                        "name": skill.name,
                        "version": skill.version,
                        "package_kind": skill.package_kind,
                        "agent_sequence": skill.agent_sequence,
                        "workflow_steps": skill.workflow_steps,
                        "tool_contract": skill.tool_contract,
                        "input_contract": skill.input_contract,
                        "output_contract": skill.output_contract,
                        "examples": skill.examples,
                        "failure_policy": skill.failure_policy,
                    }
                state.intent.project_context.setdefault("skill_workflows", {})[skill.skill_id] = {
                    "name": skill.name,
                    "version": skill.version,
                    "package_kind": skill.package_kind,
                    "agent_sequence": skill.agent_sequence,
                    "workflow_steps": skill.workflow_steps,
                    "tool_contract": skill.tool_contract,
                    "input_contract": skill.input_contract,
                    "output_contract": skill.output_contract,
                    "examples": skill.examples,
                    "failure_policy": skill.failure_policy,
                }
        if skill_plan["active"]:
            state.intent.project_context["capability_plan"] = {
                "primary": skill_plan["active"][0].skill_id,
                "supporting": [skill.skill_id for skill in skill_plan["active"][1:]],
                "suppressed": skill_plan["suppressed"],
                "notes": skill_plan["notes"],
            }
            state.intent.project_context["skill_plan"] = {
                "primary": skill_plan["active"][0].skill_id,
                "supporting": [skill.skill_id for skill in skill_plan["active"][1:]],
                "suppressed": skill_plan["suppressed"],
                "notes": skill_plan["notes"],
            }
            message = "Capabilities: " + ", ".join(skill.skill_id for skill in skill_plan["active"])
            if skill_plan["suppressed"]:
                message += " | suppressed: " + ", ".join(skill_plan["suppressed"])
            state.add_message(AgentRole.ORCHESTRATOR, message)

    def _compose_skill_plan(self, requested_skills: list[object]) -> dict[str, object]:
        unique = []
        seen: set[str] = set()
        for skill in requested_skills:
            skill_id = getattr(skill, "skill_id", "")
            if not skill_id or skill_id in seen:
                continue
            seen.add(skill_id)
            unique.append(skill)
        if not unique:
            return {"active": [], "suppressed": [], "notes": []}

        priority = {
            "video_script": 100,
            "knowledge_grounded": 95,
            "story_world": 90,
            "professional_writer": 85,
            "longform_builder": 80,
            "idea_to_draft": 60,
            "revision_studio": 55,
            "publish_ready": 50,
            "narrative_canon": 50,
            "source_grounded": 50,
            "variant_lab": 45,
            "creative_brief": 40,
        }
        unique.sort(key=lambda skill: priority.get(getattr(skill, "skill_id", ""), 50), reverse=True)

        active = []
        suppressed: list[str] = []
        notes: list[str] = []
        active_ids: set[str] = set()
        for skill in unique:
            skill_id = getattr(skill, "skill_id", "")
            if skill_id in {"creative_brief", "idea_to_draft"} and active:
                suppressed.append(skill_id)
                notes.append("idea_to_draft suppressed because a concrete production capability was selected.")
                continue
            if skill_id == "variant_lab" and "revision_studio" in active_ids:
                suppressed.append(skill_id)
                notes.append("variant_lab suppressed during direct revision to avoid drifting away from user feedback.")
                continue
            active.append(skill)
            active_ids.add(skill_id)

        if len(active) > 3:
            for skill in active[3:]:
                suppressed.append(getattr(skill, "skill_id", ""))
            notes.append("Only the top three compatible skills are active to keep workflow readable.")
            active = active[:3]
        return {"active": active, "suppressed": suppressed, "notes": notes}

    def _infer_feedback_signal(self, note: str, edited_text: str | None = None) -> FeedbackSignal:
        text = f"{note} {edited_text or ''}"
        if any(term in text for term in ["可以了", "就这样", "采纳", "确认", "发布", "定稿"]):
            return FeedbackSignal.ACCEPT
        if any(term in text for term in ["方向不对", "重来", "完全不对", "不要这个方向"]):
            return FeedbackSignal.REJECT
        return FeedbackSignal.EDIT

    def _record_failure_signals(self, state: CreativeState) -> None:
        latest_draft_id = state.drafts[-1].version_id if state.drafts else ""
        skills = state.intent.project_context.get("skills", [])
        skill_id = str(skills[0]) if isinstance(skills, list) and skills else ""
        if state.drafts:
            profile = evaluate_naturalness(
                state.drafts[-1].content,
                request=state.intent.raw_request,
                feedback=[item.note for item in state.human_feedback if item.note],
                platforms=_detect_platforms(state.intent.raw_request),
            )
            signal_components = {
                "template_style": ("harness/agents/draft_writer.md", AgentRole.DRAFT_WRITER.value),
                "over_explained": ("harness/agents/draft_writer.md", AgentRole.DRAFT_WRITER.value),
                "repetitive_rhythm": ("harness/skills/revision_studio/workflow.md", AgentRole.EDITOR.value),
                "feedback_target_missed": ("harness/skills/revision_studio/workflow.md", AgentRole.EDITOR.value),
                "platform_overfit": ("harness/skills/publish_ready/workflow.md", AgentRole.NORM_STEWARD.value),
                "generic_language": ("harness/agents/draft_writer.md", AgentRole.DRAFT_WRITER.value),
            }
            for index, signal in enumerate(profile.signals):
                component, agent_role = signal_components.get(signal, ("harness/rubrics/creative_quality.md", AgentRole.CRITIC.value))
                evidence = profile.evidence[index] if index < len(profile.evidence) else "; ".join(profile.notes)
                state.add_failure_signal(
                    signal,
                    evidence,
                    draft_version_id=latest_draft_id,
                    skill_id=skill_id,
                    agent_role=agent_role,
                    component=component,
                    severity="high" if profile.score < 0.65 else "medium",
                )
        for feedback in state.human_feedback:
            text = " ".join([feedback.note or "", feedback.edited_text or ""]).strip()
            if not text:
                continue
            if any(term in text for term in ["太模板", "AI 味", "AI文案", "不像人", "模板感"]):
                state.add_failure_signal(
                    "template_style",
                    text,
                    draft_version_id=feedback.target_id or latest_draft_id,
                    skill_id=skill_id,
                    agent_role=AgentRole.DRAFT_WRITER.value,
                    component="harness/agents/draft_writer.md",
                )
            if any(term in text for term in ["第二段", "没改", "没有按", "没按照", "没回应"]):
                state.add_failure_signal(
                    "feedback_target_missed",
                    text,
                    draft_version_id=feedback.target_id or latest_draft_id,
                    skill_id=skill_id or "revision_studio",
                    agent_role=AgentRole.EDITOR.value,
                    component="harness/skills/revision_studio/workflow.md",
                )
            if any(platform in text for platform in ["微博", "小红书", "公众号"]) and any(term in text for term in ["不像", "不对", "太硬", "硬广"]):
                state.add_failure_signal(
                    "platform_overfit",
                    text,
                    draft_version_id=feedback.target_id or latest_draft_id,
                    skill_id=skill_id or "publish_ready",
                    agent_role=AgentRole.NORM_STEWARD.value,
                    component="harness/skills/publish_ready/workflow.md",
                )
        for comment in state.comments:
            text = comment.comment
            if comment.severity == "norm" and any(term in text for term in ["通用规范", "泛", "规则"]):
                state.add_failure_signal(
                    "norm_generic",
                    text,
                    draft_version_id=comment.target_id,
                    skill_id=skill_id,
                    agent_role=AgentRole.NORM_STEWARD.value,
                    component="harness/agents/norm_steward.md",
                    severity="low",
                )
            if any(term in text for term in ["角色", "世界观", "时间线", "canon"]):
                state.add_failure_signal(
                    "canon_conflict",
                    text,
                    draft_version_id=comment.target_id,
                    skill_id=skill_id or "narrative_canon",
                    agent_role=AgentRole.CANON_KEEPER.value,
                    component="harness/agents/canon_keeper.md",
                    severity="low",
                )

    def _absorb_context_signals(self, state: CreativeState, text: str, evidence_ids: list[str]) -> None:
        if not text.strip():
            return
        for url in _detect_urls(text):
            try:
                record = self.import_knowledge_url(url=url, kind="project", project_id=state.project_id, tags=["url", "user_source"])
            except Exception as exc:
                fact = f"用户提供链接：{url}。自动导入失败：{exc}"
            else:
                fact = f"用户提供链接：{url}。已导入资料库：{record.get('title', '')}"
            if fact not in state.facts:
                state.facts.append(fact)

        for platform in _detect_platforms(text):
            content = f"平台规范线索：用户提到“{platform}”，后续生成应自动召回并遵守该平台的表达习惯和发布边界。"
            if content not in state.facts:
                state.facts.append(content)

        for preference in _extract_user_preferences(text):
            content = f"用户偏好：{preference}"
            if preference not in state.intent.user_preferences:
                state.intent.user_preferences.append(preference)
            if content not in state.facts:
                state.facts.append(content)

        for rule in _extract_user_rules(text):
            content = f"用户自定义规则：{rule}"
            if rule not in state.intent.constraints:
                state.intent.constraints.append(rule)
            if content not in state.facts:
                state.facts.append(content)

    def _select_agents(self, state: CreativeState) -> list[object]:
        skill_ids = state.intent.project_context.get("capabilities") or state.intent.project_context.get("skills", [])
        skill_tags = []
        if isinstance(skill_ids, list):
            for skill_id in skill_ids:
                skill = self._get_skill(str(skill_id))
                if skill:
                    skill_tags.extend(skill.tags)
        agents: list[object] = [Strategist(self.llm)]
        if "revision" not in skill_tags:
            agents.append(DraftWriter(self.llm))
        agents.extend([EditorAgent(self.llm), CriticPanel(self.llm)])
        request = state.intent.raw_request
        needs_norm = "norm" in skill_tags or any(term in request for term in ["微博", "小红书", "公众号", "发布", "宣传", "广告", "角色", "世界观", "游戏"])
        if needs_norm or state.facts:
            agents.append(NormSteward())
        return agents

    def _get_skill(self, skill_id: str):
        key = str(skill_id).strip()
        return self._get_legacy_skill(key) or self._get_capability(key)

    def _get_capability(self, capability_id: str):
        key = str(capability_id).strip()
        alias = CAPABILITY_ALIASES.get(key, "")
        if key in self.capabilities or alias:
            return self.capabilities.get(key) or (self.capabilities.get(alias) if alias else None) or get_capability(key)
        return next((item for item in self.capabilities.values() if item.name == key), None)

    def _get_legacy_skill(self, skill_id: str):
        key = str(skill_id).strip()
        alias = SKILL_ALIASES.get(key, "")
        return self.skills.get(key) or (self.skills.get(alias) if alias else None) or get_skill(key)

    def _workflow_trace(self, state: CreativeState) -> list[dict[str, object]]:
        return [
            {
                "role": message.role.value,
                "name": _agent_display_name(message.role),
                "content": message.content,
                "created_at": message.created_at,
                "metadata": message.metadata,
            }
            for message in state.messages
            if message.role != AgentRole.HUMAN
        ]

    def _agent_events_view(self, state: CreativeState) -> list[dict[str, object]]:
        return [
            {
                "event_id": event.event_id,
                "role": event.agent.value,
                "name": _agent_display_name(event.agent),
                "status": event.status,
                "stage_label": event.stage_label,
                "detail": event.detail,
                "input_refs": event.input_refs,
                "output_refs": event.output_refs,
                "failure_signal": event.failure_signal,
                "created_at": event.created_at,
            }
            for event in state.agent_events
            if event.visible_to_user
        ]

    def _shared_context_view(self, state: CreativeState) -> dict[str, object]:
        return {
            "facts": state.facts[:24],
            "constraints": state.intent.constraints,
            "preferences": state.intent.user_preferences,
            "warnings": state.warnings,
            "skills": state.intent.project_context.get("skills", []),
        }

    def _run_agent(self, state: CreativeState, agent: object):
        role = getattr(agent, "role", AgentRole.ORCHESTRATOR)
        if not isinstance(role, AgentRole):
            role = AgentRole(str(role))
        state.add_event(
            role,
            "running",
            _agent_display_name(role),
            _agent_stage_detail(role, platforms=_detect_platforms(state.intent.raw_request), urls=_detect_urls(state.intent.raw_request)),
        )
        try:
            result = agent.run(state)
        except Exception as exc:
            state.add_event(role, "failed", _agent_display_name(role), str(exc), failure_signal=f"{role.value}_failed")
            raise
        state.add_event(role, "completed", _agent_display_name(role), getattr(result, "summary", "已完成当前阶段。"))
        self.metrics.record(
            "agent_stage_completed",
            session_id=state.session_id,
            project_id=state.project_id,
            metadata={"agent": role.value},
        )
        return result

    def _start_skill_runs(self, state: CreativeState, agents: list[object]) -> list[dict[str, object]]:
        if not self._harness_settings().get("record_skill_runs", True):
            return []
        skill_ids = state.intent.project_context.get("skills", [])
        workflows = state.intent.project_context.get("skill_workflows", {})
        if not isinstance(skill_ids, list) or not isinstance(workflows, dict):
            return []
        started = []
        for skill_id in skill_ids:
            skill = self._get_skill(str(skill_id))
            if not skill:
                continue
            record = {
                "run_id": new_id("skillrun"),
                "session_id": state.session_id,
                "project_id": state.project_id,
                "skill_id": skill.skill_id,
                "skill_version": skill.version,
                "input_summary": state.intent.raw_request[:240],
                "agent_sequence_used": [getattr(agent, "role", AgentRole.ORCHESTRATOR).value for agent in agents],
                "tool_contract": skill.tool_contract,
                "output_contract": skill.output_contract,
                "status": "running",
                "created_at": utc_now_iso(),
            }
            started.append(record)
        return started

    def _finish_skill_runs(self, state: CreativeState, runs: list[dict[str, object]], *, feedback_id: str = "") -> None:
        if not runs:
            return
        failure_signals = [
            event.failure_signal
            for event in state.agent_events
            if event.failure_signal and event.created_at >= str(runs[0].get("created_at", ""))
        ]
        failure_signals.extend(item.failure_type for item in state.failure_signals if item.failure_type not in failure_signals)
        contract_scores = _skill_contract_scores(state)
        for record in runs:
            record.update(
                {
                    "status": "completed",
                    "finished_at": utc_now_iso(),
                    "output_contract_pass": not failure_signals and bool(state.drafts),
                    "critic_scores": contract_scores,
                    "failure_signals": failure_signals,
                    "user_feedback_after_output": feedback_id,
                }
            )
            self._append_skill_run(record)
            self.metrics.record(
                "skill_run_completed",
                session_id=state.session_id,
                project_id=state.project_id,
                metadata={
                    "skill_id": record.get("skill_id", ""),
                    "contract_pass": bool(record.get("output_contract_pass")),
                },
            )

    def _append_skill_run(self, record: dict[str, object]) -> None:
        with self.skill_runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _list_skill_runs(self, limit: int = 80) -> list[dict[str, object]]:
        if not self.skill_runs_path.exists():
            return []
        rows = [json.loads(line) for line in self.skill_runs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return rows[:limit]

    def _memory_policy(self) -> dict[str, object]:
        data = self.settings.read().get("memory_policy", {})
        return data if isinstance(data, dict) else {}

    def _harness_settings(self) -> dict[str, object]:
        data = self.settings.read().get("harness", {})
        return data if isinstance(data, dict) else {}

    def _load_llm(self) -> ObservedLLMClient | None:
        self.llm_error = None
        try:
            client = self._client_from_settings() or client_from_env()
            return ObservedLLMClient(client, self.call_logs) if client else None
        except LLMError as exc:
            self.llm_error = str(exc)
            return None

    def _client_from_settings(self) -> LLMClient | None:
        data = self.settings.read()
        llm = data.get("llm", {})
        if not isinstance(llm, dict):
            return None
        provider = str(llm.get("provider", "")).strip().lower()
        if not provider:
            return None
        keys = llm.get("api_keys", {})
        api_key = str(keys.get(provider, "")).strip() if isinstance(keys, dict) else ""
        if not api_key:
            return None
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        model = str(llm.get("model") or defaults.get("model") or "").strip()
        base_url = str(llm.get("base_url") or defaults.get("base_url") or "").strip()
        if not model or not base_url:
            raise LLMError(f"{provider} 设置缺少 model 或 base_url。")
        return OpenAICompatibleClient(provider=provider, api_key=api_key, model=model, base_url=base_url)

    def _suggest_session_title(self, state: CreativeState) -> str:
        fallback = _asset_title(state.intent.raw_request).rstrip(".")
        if self.llm:
            try:
                response = self.llm.chat(
                    [
                        ChatMessage(
                            "system",
                            "你只负责给创作会话起短标题。输出 6 到 14 个中文字符，不要标点，不要解释。",
                        ),
                        ChatMessage(
                            "user",
                            "原始需求："
                            + state.intent.raw_request
                            + "\n载体："
                            + (state.intent.medium or "未指定")
                            + "\n目标："
                            + (state.intent.goal or "内容创作"),
                        ),
                    ],
                    max_tokens=40,
                    temperature=0.2,
                )
                title = _clean_title(response.content)
                if 4 <= len(title) <= 18 and re.search(r"[\u4e00-\u9fff]", title):
                    return title
            except LLMError:
                pass
        return fallback[:14] or "新的创作"


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


def _detect_urls(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"https?://[^\s，。；;）)]+", text)))


def _agent_display_name(role: AgentRole) -> str:
    names = {
        AgentRole.INTENT_INTERPRETER: "需求理解",
        AgentRole.RESEARCHER: "资料检索",
        AgentRole.STRATEGIST: "创作策略",
        AgentRole.DRAFT_WRITER: "初稿写作",
        AgentRole.EDITOR: "改稿整理",
        AgentRole.CRITIC: "质量评审",
        AgentRole.NORM_STEWARD: "规范检查",
        AgentRole.MEMORY_CURATOR: "记忆沉淀",
        AgentRole.CONTEXT_BUILDER: "上下文召回",
        AgentRole.ORCHESTRATOR: "任务编排",
    }
    return names.get(role, role.value)


def _agent_stage_detail(role: AgentRole, *, platforms: list[str], urls: list[str]) -> str:
    if role == AgentRole.INTENT_INTERPRETER:
        return "提取目标、载体、约束、平台和用户偏好。"
    if role == AgentRole.RESEARCHER:
        details = ["召回记忆和资料库。"]
        if platforms:
            details.append("识别到平台：" + "、".join(platforms) + "，准备召回对应规范。")
        if urls:
            details.append("识别到链接，准备作为素材来源。")
        return "".join(details)
    if role == AgentRole.STRATEGIST:
        return "把用户需求、资料和规则转成创作策略。"
    if role == AgentRole.DRAFT_WRITER:
        return "生成第一版可继续讨论的草稿。"
    if role == AgentRole.EDITOR:
        return "整理表达，减少模板感，保留有效信息。"
    if role == AgentRole.CRITIC:
        return "检查清晰度、风格贴合度和可继续修改的空间。"
    if role == AgentRole.NORM_STEWARD:
        return "检查平台规则、项目设定、版权和发布边界。"
    if role == AgentRole.MEMORY_CURATOR:
        return "判断哪些反馈适合沉淀为偏好、规则或项目记忆。"
    return "处理当前阶段。"


def _extract_user_preferences(text: str) -> list[str]:
    results: list[str] = []
    for clause in _split_signal_clauses(text):
        if _is_skill_instruction(clause):
            continue
        if _is_ephemeral_clause(clause) and not _looks_long_term_clause(clause):
            continue
        if not _has_preference_signal(clause):
            continue
        value = _clean_signal_clause(clause)
        if _valid_signal(value):
            results.append(value)
    return _dedupe_signals(results)[:6]


def _extract_user_rules(text: str) -> list[str]:
    results: list[str] = []
    for clause in _split_signal_clauses(text):
        if _is_skill_instruction(clause):
            continue
        if _is_ephemeral_clause(clause) and not _looks_long_term_clause(clause):
            continue
        if not _has_rule_signal(clause):
            continue
        value = _clean_signal_clause(clause)
        if _valid_signal(value):
            results.append(value)
    return _dedupe_signals(results)[:6]


def _split_signal_clauses(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"[。！？!?；;\n]+", normalized)
    clauses: list[str] = []
    for part in parts:
        part = part.strip(" ，,：:")
        if not part:
            continue
        segments = re.split(r"[，,]+(?=(?:要求|希望|最好|尽量|不要|别|避免|禁止|禁用|不能|必须|需要|标题|正文|第二段|开头|结尾|语气|风格|以后|默认|记住|这次|本次|这版|当前|先|暂时))", part)
        for segment in segments:
            value = segment.strip(" ，,：:")
            if value:
                clauses.append(value)
    return clauses


def _has_preference_signal(clause: str) -> bool:
    preference_terms = ["喜欢", "不喜欢", "偏好", "希望", "尽量", "最好", "语气", "风格", "更自然", "更克制", "更冷", "更温和", "模板腔"]
    return any(term in clause for term in preference_terms)


def _has_rule_signal(clause: str) -> bool:
    rule_terms = ["规则", "规范", "要求", "限制", "边界", "必须", "禁止", "禁用", "避免", "不能", "不要", "别"]
    return any(term in clause for term in rule_terms)


def _is_skill_instruction(clause: str) -> bool:
    return bool(re.search(r"使用技能[:：]\s*[\w\-\u4e00-\u9fff]+", clause))


def _is_ephemeral_clause(clause: str) -> bool:
    return any(term in clause for term in ["这次", "本次", "这一版", "这版", "当前", "先", "暂时", "临时"])


def _looks_long_term_clause(clause: str) -> bool:
    return any(term in clause for term in ["以后", "长期", "一直", "总是", "记住", "我的风格", "默认", "个人偏好"])


def _clean_signal_clause(clause: str) -> str:
    value = re.sub(r"\s+", " ", clause).strip(" ，,；;：:")
    value = re.sub(r"^(请|帮我|麻烦|你需要|需要|要求|可以|同时|并且|另外|紧接着)", "", value).strip(" ，,；;：:")
    return value


def _valid_signal(value: str) -> bool:
    if not (3 <= len(value) <= 80):
        return False
    if re.fullmatch(r"[\W_]+", value):
        return False
    return bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]", value))


def _dedupe_signals(values: list[str]) -> list[str]:
    cleaned = []
    for value in values:
        key = re.sub(r"\s+", "", value).lower()
        if any(key == existing[0] for existing in cleaned):
            continue
        if any(key in existing[0] and len(key) < len(existing[0]) for existing in cleaned):
            continue
        cleaned = [existing for existing in cleaned if not (existing[0] in key and len(existing[0]) < len(key))]
        cleaned.append((key, value))
    return [value for _, value in cleaned]


def _asset_from_state(state: CreativeState, title: str = "") -> dict[str, object]:
    final_draft = state.drafts[-1] if state.drafts else None
    skill_ids = state.intent.project_context.get("skills", [])
    platforms = _detect_platforms(" ".join([state.intent.raw_request, *state.intent.constraints, *state.facts]))
    return {
        "asset_id": state.session_id,
        "session_id": state.session_id,
        "project_id": state.project_id,
        "title": title or _asset_title(state.intent.raw_request),
        "prompt": state.intent.raw_request,
        "final_content": final_draft.content if final_draft else "",
        "iteration_prompt": _iteration_prompt(state, final_draft.content if final_draft else ""),
        "draft_count": len(state.drafts),
        "feedback_count": len(state.human_feedback),
        "goal": state.intent.goal,
        "skills": skill_ids if isinstance(skill_ids, list) else [],
        "platforms": platforms,
        "updated_at": final_draft.created_at if final_draft else "",
    }


def _asset_from_post(post: dict[str, object]) -> dict[str, object]:
    return {
        "asset_id": str(post.get("post_id", "")),
        "post_id": str(post.get("post_id", "")),
        "session_id": str(post.get("session_id", "")),
        "project_id": str(post.get("project_id", "default")),
        "source": "published",
        "title": str(post.get("title", "未命名作品")),
        "prompt": str(post.get("title", "未命名作品")),
        "final_content": str(post.get("body", "")),
        "iteration_prompt": f"基于这篇已发布作品继续迭代。\n\n标题：{post.get('title', '')}\n\n当前作品：\n{post.get('body', '')}\n\n新的修改目标：",
        "goal": "已发布作品",
        "tags": _as_string_list(post.get("tags")),
        "platforms": [],
        "skills": [],
        "image": str(post.get("cover_url", "")),
        "cover_url": str(post.get("cover_url", "")),
        "updated_at": str(post.get("updated_at") or post.get("published_at") or ""),
    }


def _asset_title(prompt: str) -> str:
    text = re.sub(r"\s+", " ", prompt).strip(" ，,。")
    return text[:22] + ("..." if len(text) > 22 else "")


def _iteration_prompt(state: CreativeState, final_content: str) -> str:
    pieces = [
        "基于这份已完成作品继续迭代。",
        "",
        "原始需求：",
        state.intent.raw_request.strip(),
        "",
        "当前作品：",
        final_content.strip(),
        "",
        "新的修改目标：",
    ]
    return "\n".join(pieces).strip()


def default_publish_tags() -> list[str]:
    return []


def normalize_publish_tags(value: object) -> list[str]:
    if isinstance(value, str):
        raw_values = re.split(r"[\s,，、#]+", value)
    elif isinstance(value, list):
        raw_values = [str(item) for item in value]
    else:
        raw_values = []
    tags: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        tag = re.sub(r"\s+", "", str(raw)).strip("#＃")
        if not tag or len(tag) > 16:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
        if len(tags) >= 12:
            break
    return tags


def user_facing_change(change: str, improvement: str = "") -> str:
    pieces = [piece.strip(" 。") for piece in [change, improvement] if piece and piece.strip()]
    if pieces:
        return "。".join(pieces) + "。"
    return "以后遇到类似情况时，我会先检查这次暴露的问题，再继续生成或改稿。"


def _clean_title(value: str) -> str:
    title = re.sub(r"[\r\n]+", " ", value).strip()
    title = re.sub(r"^(标题|会话标题)[:：]\s*", "", title)
    title = title.strip(" \t\"'“”‘’《》【】[]（）()。.!！?？,，、；;：:")
    title = re.sub(r"\s+", "", title)
    return title[:18]


def _skill_contract_scores(state: CreativeState) -> dict[str, object]:
    latest_draft = state.drafts[-1].content if state.drafts else ""
    requested = state.intent.raw_request + " " + " ".join(state.intent.constraints)
    checks = {
        "has_draft": bool(latest_draft.strip()),
        "responded_to_feedback": not state.human_feedback or any(
            _feedback_keyword(feedback.note) and _feedback_keyword(feedback.note) in latest_draft
            for feedback in state.human_feedback
        ),
        "has_norm_review": any(comment.agent == AgentRole.NORM_STEWARD for comment in state.comments),
        "has_critic_review": any(comment.agent == AgentRole.CRITIC for comment in state.comments),
        "platform_sensitive": not _detect_platforms(requested) or any("规范" in warning or "平台" in warning for warning in state.warnings),
    }
    passed = sum(1 for value in checks.values() if value)
    return {"checks": checks, "score": round(passed / max(len(checks), 1), 4)}


def _feedback_keyword(text: str) -> str:
    for term in ["标题", "第二段", "自然", "模板", "冷", "短", "平台", "角色", "世界观"]:
        if term in text:
            return term
    return ""


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
