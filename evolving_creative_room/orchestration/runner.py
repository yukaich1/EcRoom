from __future__ import annotations

from pathlib import Path
import base64
import binascii
import json
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
from evolving_creative_room.evaluation import DEFAULT_EVAL_CASES, EvaluationStore, compare_eval_runs, new_eval_run, score_state
from evolving_creative_room.evolution.manifest import HarnessEvolver
from evolving_creative_room.knowledge import KnowledgeBase
from evolving_creative_room.learning import LearningStore
from evolving_creative_room.llm import ChatMessage, LLMClient, LLMError, OpenAICompatibleClient, client_from_env
from evolving_creative_room.memory.store import MemoryRecord, MemoryStore
from evolving_creative_room.metrics import MetricStore
from evolving_creative_room.observability import CallLogStore, ObservedLLMClient
from evolving_creative_room.projects import ProjectStore
from evolving_creative_room.settings import PROVIDER_DEFAULTS, UserSettingsStore
from evolving_creative_room.skills import SKILLS, get_skill, write_skill_packages
from evolving_creative_room.sources import import_public_page
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
        self.skill_package_paths = write_skill_packages(self.project_root / "harness" / "skills")
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
    ) -> CreativeState:
        intent = CreativeIntent(raw_request=request, user_preferences=user_preferences or [])
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
        self.memory.render_short_term_canvas(state)
        self.memory.capture_l0(state)
        self.memory.extract_l1(state)
        self.memory.upsert_l2_scene(state)
        memory_policy = self._memory_policy()
        candidates = self.learning.suggest_from_state(
            state,
            min_confidence=float(memory_policy.get("min_confidence", 0.35)),
            limit=int(memory_policy.get("candidate_limit", 3)),
        )
        self.metrics.record(
            "session_finalized",
            session_id=state.session_id,
            project_id=state.project_id,
            metadata={"draft_count": len(state.drafts), "feedback_count": len(state.human_feedback)},
        )
        if state.drafts:
            self.metrics.record("session_success", session_id=state.session_id, project_id=state.project_id)
        if candidates:
            self.metrics.record(
                "learning_candidate_created",
                value=float(len(candidates)),
                session_id=state.session_id,
                project_id=state.project_id,
            )

        if self._harness_settings().get("auto_propose", True):
            manifest = self.evolver.propose(state)
            manifest.write(self.workspace / "evolution" / f"{manifest.manifest_id}.json")

    def latest_manifest(self, session_id: str) -> dict[str, object] | None:
        manifests = []
        for path in (self.workspace / "evolution").glob("manifest_*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("session_id") == session_id:
                manifests.append((path.stat().st_mtime, data))
        if not manifests:
            return None
        return sorted(manifests, key=lambda item: item[0], reverse=True)[0][1]

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
        return {
            "state": state_to_dict(state),
            "session": session_meta,
            "manifest": self.latest_manifest(session_id),
            "memory": self.memory.list_records(limit=40, project_id=state.project_id),
            "learning": {"candidates": self.learning.list(session_id=session_id)},
            "workflow_trace": self._workflow_trace(state),
            "agent_events": self._agent_events_view(state),
            "shared_context": self._shared_context_view(state),
            "canvas": canvas_path.read_text(encoding="utf-8") if canvas_path.exists() else "",
        }

    def workflow_preview(self, request: str, preferences: list[str] | None = None, project_id: str = "default") -> dict[str, object]:
        intent = CreativeIntent(raw_request=request, user_preferences=preferences or [])
        state = CreativeState(intent=intent, project_id=project_id)
        self._apply_skill_context(state)
        self.intent_agent.run(state)
        query = " ".join([request, *(preferences or [])])
        platforms = _detect_platforms(query)
        urls = _detect_urls(query)
        agents = [AgentRole.INTENT_INTERPRETER, AgentRole.RESEARCHER, *[agent.role for agent in self._select_agents(state)], AgentRole.MEMORY_CURATOR]
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
                "skills": state.intent.project_context.get("skills", []),
                "constraints": state.intent.constraints,
            },
        }

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
        return {"asset": _asset_from_state(state, title=str(session.get("title") or "")), "manifest": self.latest_manifest(asset_id)}

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
        path.write_bytes(content)
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

    def apply_evolution(self, session_id: str, proposal_id: str, reviewer_note: str = "") -> dict[str, object]:
        manifest = self.latest_manifest(session_id)
        if not manifest:
            raise ValueError(f"No manifest for session: {session_id}")
        return self.evolver.apply_proposal(
            project_root=self.project_root,
            manifest=manifest,
            proposal_id=proposal_id,
            reviewer_note=reviewer_note,
        )

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
        metadata: dict[str, object] = {"mode": "dry_run"}
        if proposal:
            candidate_note = "候选 harness 修改：" + str(proposal.get("proposed_change", ""))
            metadata.update(
                {
                    "proposal_id": proposal.get("proposal_id", ""),
                    "target_component": proposal.get("target_component", ""),
                    "predicted_metric": proposal.get("predicted_metric", ""),
                }
            )
        else:
            candidate_note = "候选 harness 修改：强化资料召回、平台规范检查和用户偏好记忆。"
            metadata["proposal_id"] = ""

        baseline = self._run_cases(DEFAULT_EVAL_CASES, kind="ab_baseline", metadata=metadata)
        candidate = self._run_cases(
            DEFAULT_EVAL_CASES,
            kind="ab_candidate",
            extra_preferences=[candidate_note],
            metadata=metadata,
        )
        self.evaluations.write(baseline)
        self.evaluations.write(candidate)
        comparison = compare_eval_runs(baseline, candidate)
        comparison["metadata"] = metadata
        path = self.workspace / "evaluations" / f"ab_{candidate.run_id}.json"
        path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
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

    def complete_session(self, session_id: str, completed: bool, work_category: str = "") -> dict[str, object]:
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
    ):
        results = []
        for case in cases:
            preferences = [*case.preferences, *(extra_preferences or [])]
            state = self.run_seed_session(case.request, user_preferences=preferences)
            result = score_state(state, case.expected_signals)
            result.case_name = case.name
            results.append(result)
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

    def _read_collected_assets(self, project_id: str | None = None) -> list[dict[str, object]]:
        if not self.collected_assets_path.exists():
            return []
        data = json.loads(self.collected_assets_path.read_text(encoding="utf-8"))
        assets = data if isinstance(data, list) else []
        if project_id:
            assets = [item for item in assets if item.get("project_id", "default") in {project_id, "global"}]
        return assets

    def _write_collected_assets(self, assets: list[dict[str, object]]) -> None:
        self.collected_assets_path.write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding="utf-8")

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
        self.published_posts_path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")

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
        skill_ids = []
        for preference in state.intent.user_preferences:
            match = re.search(r"使用技能[:：]\s*([a-zA-Z0-9_\-\u4e00-\u9fff]+)", preference)
            if not match:
                continue
            raw = match.group(1).strip()
            skill = get_skill(raw) or next((item for item in SKILLS.values() if item.name == raw), None)
            if skill:
                skill_ids.append(skill.skill_id)
                if skill.skill_id not in state.intent.project_context.setdefault("skills", []):
                    state.intent.project_context["skills"].append(skill.skill_id)
                state.intent.constraints.extend(item for item in skill.constraints if item not in state.intent.constraints)
                state.intent.evaluation_criteria.extend(item for item in skill.evaluation if item not in state.intent.evaluation_criteria)
                state.facts.append(f"技能包：{skill.name} {skill.version} - {skill.workflow_hint}")
                state.facts.append("技能触发：" + skill.trigger)
                state.facts.append("技能输入规格：" + "；".join(skill.input_contract))
                state.facts.append("技能流程：" + " -> ".join(skill.workflow_steps))
                state.facts.append("技能工具契约：" + "；".join(skill.tool_contract or ["无需外部工具"]))
                state.facts.append("技能输出契约：" + "；".join(skill.output_contract))
                state.facts.append("技能失败处理：" + "；".join(skill.failure_policy or ["按通用创作流程处理"]))
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
        if skill_ids:
            state.add_message(AgentRole.ORCHESTRATOR, "Skills: " + ", ".join(skill_ids))

    def _infer_feedback_signal(self, note: str, edited_text: str | None = None) -> FeedbackSignal:
        text = f"{note} {edited_text or ''}"
        if any(term in text for term in ["可以了", "就这样", "采纳", "确认", "发布", "定稿"]):
            return FeedbackSignal.ACCEPT
        if any(term in text for term in ["方向不对", "重来", "完全不对", "不要这个方向"]):
            return FeedbackSignal.REJECT
        return FeedbackSignal.EDIT

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
        skill_ids = state.intent.project_context.get("skills", [])
        skill_tags = []
        if isinstance(skill_ids, list):
            for skill_id in skill_ids:
                skill = get_skill(str(skill_id))
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
            skill = get_skill(str(skill_id))
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
    return ["角色", "世界观", "剧情", "社媒", "小红书", "微博", "公众号", "活动", "游戏", "品牌", "改稿", "标题"]


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
