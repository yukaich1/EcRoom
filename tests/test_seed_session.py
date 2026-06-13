from __future__ import annotations

import os
import json
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ECROOM_VECTOR_BACKEND", "memory")

from evolving_creative_room.llm import ChatMessage, LLMResponse
from evolving_creative_room.memory.store import MemoryRecord, MemoryStore
from evolving_creative_room.models import FeedbackSignal
from evolving_creative_room.naturalness import evaluate_naturalness
import evolving_creative_room.orchestration.runner as runner_module
from evolving_creative_room.orchestration import CreativeRoomRunner
from evolving_creative_room.storage import atomic_write_json, atomic_write_jsonl, atomic_write_text


class FakeLLM:
    provider = "fake"
    model = "fake-model"

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 900,
    ) -> LLMResponse:
        prompt = messages[-1].content
        if "3-5 条创作策略" in prompt:
            return LLMResponse("先保留角色张力\n再改成可传播版本\n最后检查平台语气", self.provider, self.model)
        if "请写一版" in prompt:
            return LLMResponse("这是由 fake LLM 写出的角色登场草稿。", self.provider, self.model)
        if "请做一次编辑" in prompt:
            return LLMResponse("这是由 fake LLM 编辑后的角色登场草稿。", self.provider, self.model)
        if "请评审" in prompt:
            return LLMResponse("开头更自然\n角色动机可以更清楚\n微博版本需要更短", self.provider, self.model)
        return LLMResponse("ok", self.provider, self.model)


class FakeProcessLLM(FakeLLM):
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 900,
    ) -> LLMResponse:
        prompt = messages[-1].content
        if "3-5 条创作策略" in prompt:
            return LLMResponse("先保留角色张力\n再检查微博语气", self.provider, self.model)
        if "请写一版" in prompt:
            return LLMResponse("命锁响了一声，她在旧城醒来。", self.provider, self.model)
        if "请做一次编辑" in prompt:
            return LLMResponse(
                "以下是基于你的原始需求和初稿的编辑版本。具体调整如下：\n\n"
                "编辑版：命锁响了一声，她在旧城醒来。\n\n"
                "变更说明：减少模板感。\n\n"
                "待讨论方向：请确认偏好。",
                self.provider,
                self.model,
            )
        if "请评审" in prompt:
            return LLMResponse("需要去掉过程说明", self.provider, self.model)
        return LLMResponse("ok", self.provider, self.model)


class FakeTemplateLLM(FakeLLM):
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 900,
    ) -> LLMResponse:
        prompt = messages[-1].content
        if "3-5 条创作策略" in prompt:
            return LLMResponse("先保留角色张力\n再检查平台语气", self.provider, self.model)
        if "请写一版" in prompt or "请做一次编辑" in prompt:
            return LLMResponse("重磅来袭，全新体验不容错过。让我们一起敬请期待这场精彩纷呈的角色登场。", self.provider, self.model)
        if "请评审" in prompt:
            return LLMResponse("模板感偏强\n需要减少固定营销表达", self.provider, self.model)
        return LLMResponse("ok", self.provider, self.model)


class FakeContinuationLLM(FakeLLM):
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 900,
    ) -> LLMResponse:
        prompt = messages[-1].content
        if "只输出续写部分" in prompt:
            return LLMResponse("技术提示：镜头继续向上，补完天空粒子和收束字幕。", self.provider, self.model)
        return super().chat(messages, temperature=temperature, max_tokens=max_tokens)


class SeedSessionTests(unittest.TestCase):
    def test_seed_session_writes_memory_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一个角色宣传微博，不要太模板。",
                user_preferences=["喜欢自然一点"],
                feedback_note="这版还是太像 AI 文案。",
            )

            self.assertTrue(state.drafts)
            self.assertTrue(state.comments)
            self.assertTrue((Path(tmp) / "short_term_canvas.mmd").exists())
            self.assertTrue((Path(tmp) / "memory" / "L0.jsonl").exists())
            self.assertTrue((Path(tmp) / "memory" / "L1.jsonl").exists())
            self.assertTrue(any((Path(tmp) / "evolution").glob("*.json")))
            session_view = runner.session_view(state.session_id)
            self.assertTrue(session_view["session"]["title"])
            self.assertNotEqual(session_view["session"]["title"], state.intent.raw_request)

    def test_feedback_updates_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一个游戏角色登场文案。",
                user_preferences=["不要太中二"],
            )
            updated = runner.record_feedback(
                state.session_id,
                signal=FeedbackSignal.EDIT,
                note="这版可以更自然。",
                edited_text="他推门进来时没有自我介绍，只把染血的徽章放在桌上。",
            )

            self.assertEqual(updated.session_id, state.session_id)
            self.assertGreaterEqual(len(updated.human_feedback), 1)
            self.assertTrue(any(draft.author.value == "human" for draft in updated.drafts))
            self.assertEqual(updated.drafts[-1].author.value, "editor")
            loaded = runner.memory.load_state(state.session_id)
            self.assertEqual(loaded.drafts[-1].content, updated.drafts[-1].content)

    def test_continue_feedback_appends_instead_of_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeContinuationLLM())
            state = runner.run_seed_session(
                request="写一个视频脚本。",
                user_preferences=[],
            )
            state.drafts[-1].content = "动作：\n扫帚低空平稳滑行。\n**技"
            runner.memory.save_state(state)

            updated = runner.record_feedback(
                state.session_id,
                signal=FeedbackSignal.EDIT,
                note="请继续输出",
            )

            self.assertEqual(updated.human_feedback[-1].signal, FeedbackSignal.CONTINUE)
            self.assertIn("扫帚低空平稳滑行", updated.drafts[-1].content)
            self.assertIn("技术提示：镜头继续向上", updated.drafts[-1].content)
            self.assertNotIn("**技\n\n技术提示", updated.drafts[-1].content)

    def test_feedback_does_not_sediment_skill_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一个游戏角色登场文案。",
                user_preferences=[],
            )

            updated = runner.record_feedback(
                state.session_id,
                signal=FeedbackSignal.EDIT,
                note="希望使用技能：publish_ready，但这一版先把第一段改短。",
            )

            self.assertNotIn("使用技能：publish_ready", updated.intent.user_preferences)
            self.assertNotIn("使用技能：publish_ready", updated.intent.constraints)
            self.assertFalse(any("使用技能：publish_ready" in fact for fact in updated.facts))
            self.assertEqual(updated.intent.project_context.get("skills", []), [])

    def test_runner_uses_llm_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一个游戏角色登场微博。",
                user_preferences=["自然一点"],
            )

            self.assertEqual(runner.llm_info()["provider"], "fake")
            self.assertIn("fake LLM", state.drafts[-1].content)
            self.assertTrue(any(message.metadata.get("llm_provider") == "fake" for message in state.messages))

    def test_knowledge_memory_evaluation_and_evolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as project:
            harness_target = Path(project) / "harness" / "agents"
            harness_target.mkdir(parents=True)
            (harness_target / "draft_writer.md").write_text("# Draft Writer\n", encoding="utf-8")

            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            runner.project_root = Path(project)
            runner.add_knowledge(
                kind="norm",
                title="微博宣发边界",
                content="微博宣发需要短表达，避免夸张承诺。",
                tags=["微博", "宣发"],
            )
            state = runner.run_seed_session(
                request="帮我写一个微博角色宣发文案，不要太模板。",
                feedback_note="这版太像 AI 文案。",
            )

            self.assertTrue(runner.knowledge_view(query="微博")["records"])
            self.assertTrue(runner.memory_view(query="模板")["records"])

            manifest = runner.latest_manifest(state.session_id)
            proposal_id = manifest["proposals"][0]["proposal_id"]
            result = runner.apply_evolution(state.session_id, proposal_id, "测试应用。")
            self.assertEqual(result["proposal_id"], proposal_id)
            self.assertIn("Evolution Amendment", (harness_target / "draft_writer.md").read_text(encoding="utf-8"))

            eval_result = runner.run_evaluation_suite()
            self.assertIn("average_score", eval_result)
            self.assertTrue(runner.evaluation_view()["runs"])

    def test_collected_assets_enter_asset_library(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            asset = runner.collect_asset(
                {
                    "source_id": "seed_test",
                    "title": "收藏的灵感",
                    "prompt": "请写一段可复用的提示词。",
                    "final_content": "这是收藏后的示例输出。",
                    "category": "short",
                    "skills": ["revision_studio"],
                    "image": "/assets/inspiration/writing.jpg",
                }
            )

            assets = runner.assets_view()["assets"]
            self.assertTrue(any(item["asset_id"] == asset["asset_id"] for item in assets))
            detail = runner.asset_view(asset["asset_id"])
            self.assertEqual(detail["asset"]["prompt"], "请写一段可复用的提示词。")
            self.assertEqual(detail["asset"]["image"], "/assets/inspiration/writing.jpg")
            self.assertIsNone(detail["manifest"])

    def test_publish_flow_uses_manual_tags_and_media_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(request="写一段潮汐城市设定，最后发布到主页。")
            runner.complete_session(state.session_id, True)

            draft = runner.create_publish_draft(state.session_id)
            self.assertEqual(draft["tags"], [])
            self.assertEqual(draft["status"], "draft")
            updated = runner.update_post(
                draft["post_id"],
                {
                    "title": "潮汐城市",
                    "body": "这座城市由潮汐钟控制。",
                    "tags": ["世界观", "世界观", " 自定义标签 ", ""],
                    "cover_data_url": "data:image/png;base64,aGVsbG8=",
                    "status": "published",
                },
            )

            self.assertEqual(updated["tags"], ["世界观", "自定义标签"])
            self.assertEqual(updated["status"], "published")
            self.assertTrue(str(updated["cover_url"]).startswith("/media/"))
            self.assertTrue((Path(tmp) / "published_posts.json").exists())
            self.assertTrue(list((Path(tmp) / "media").glob("media_*.png")))
            posts = runner.published_posts_view()["posts"]
            self.assertTrue(any(item["post_id"] == draft["post_id"] for item in posts))
            self.assertEqual(runner.published_posts_view()["default_tags"], [])
            self.assertEqual(runner.post_view(draft["post_id"])["default_tags"], [])
            assets = runner.assets_view()["assets"]
            self.assertTrue(any(item.get("post_id") == draft["post_id"] and item.get("source") == "published" for item in assets))
            deleted = runner.delete_post(draft["post_id"])
            self.assertTrue(deleted["deleted"])
            self.assertFalse(any(item["post_id"] == draft["post_id"] for item in runner.published_posts_view()["posts"]))
            self.assertFalse(any(item.get("post_id") == draft["post_id"] for item in runner.assets_view()["assets"]))

    def test_delete_created_asset_hides_asset_without_revoking_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(request="帮我写一段魔女角色文案。", user_preferences=["冷一点"])
            runner.complete_session(state.session_id, True)
            before_records = runner.memory.list_records(limit=200, project_id="default")

            self.assertTrue(any(item["asset_id"] == state.session_id for item in runner.assets_view()["assets"]))
            deleted = runner.delete_asset(state.session_id)

            self.assertTrue(deleted["deleted"])
            self.assertFalse(any(item["asset_id"] == state.session_id for item in runner.assets_view()["assets"]))
            self.assertEqual(runner.memory.load_state(state.session_id).session_id, state.session_id)
            after_records = runner.memory.list_records(limit=200, project_id="default")
            self.assertEqual(len(after_records), len(before_records))
            session = next(item for item in runner.memory.list_sessions(include_completed=True) if item["session_id"] == state.session_id)
            self.assertTrue(session["asset_deleted"])

    def test_liked_inspiration_can_later_be_collected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            liked = runner.like_asset(
                {
                    "source_id": "seed_like",
                    "title": "赞过的灵感",
                    "prompt": "先喜欢，稍后再收藏。",
                    "final_content": "这是一条被点赞的内容。",
                    "liked": True,
                }
            )

            self.assertTrue(liked["liked"])
            self.assertFalse(liked["collected"])
            collected = runner.collect_asset(
                {
                    "source_id": "seed_like",
                    "title": "赞过的灵感",
                    "prompt": "先喜欢，稍后再收藏。",
                    "final_content": "这是一条被点赞的内容。",
                    "liked": True,
                }
            )
            self.assertEqual(collected["asset_id"], liked["asset_id"])
            self.assertTrue(collected["liked"])
            self.assertTrue(collected["collected"])
            uncollected = runner.uncollect_asset(
                {
                    "source_id": "seed_like",
                    "title": "赞过的灵感",
                    "prompt": "先喜欢，稍后再收藏。",
                    "final_content": "这是一条被点赞的内容。",
                    "liked": True,
                }
            )
            self.assertEqual(uncollected["asset_id"], liked["asset_id"])
            self.assertTrue(uncollected["liked"])
            self.assertFalse(uncollected["collected"])

    def test_profile_avatar_setting_is_public_without_exposing_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            view = runner.update_settings(
                {
                    "profile": {
                        "nickname": "咖啡师",
                        "bio": "写短句。",
                        "avatar_data": "data:image/png;base64,avatar",
                    },
                    "llm": {
                        "provider": "mistral",
                        "api_key": "secret-key",
                    },
                }
            )

            self.assertEqual(view["profile"]["nickname"], "咖啡师")
            self.assertEqual(view["profile"]["avatar_data"], "data:image/png;base64,avatar")
            self.assertTrue(view["llm"]["has_api_key"])
            self.assertNotIn("api_keys", view["llm"])

    def test_product_settings_control_memory_and_harness_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            view = runner.update_settings(
                {
                    "memory_policy": {"candidate_limit": 1, "min_confidence": 0.9, "complete_only": True},
                    "harness": {"record_skill_runs": False, "auto_propose": False, "min_eval_cases": 5},
                }
            )

            self.assertEqual(view["memory_policy"]["candidate_limit"], 1)
            self.assertEqual(view["harness"]["min_eval_cases"], 5)
            state = runner.run_seed_session(
                request="帮我写一段小红书体验笔记，要求不要硬广。",
                user_preferences=["使用技能：publish_ready", "以后默认自然一点"],
            )

            self.assertFalse(runner.observability_view()["skill_runs"])
            self.assertIsNone(runner.latest_manifest(state.session_id))
            self.assertFalse(runner.session_view(state.session_id)["learning"]["candidates"])

    def test_selected_skill_adds_reusable_workflow_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我把同一段内容改成小红书和微博两个版本。",
                user_preferences=["使用技能：publish_ready"],
            )

            workflows = state.intent.project_context.get("skill_workflows", {})
            self.assertIn("publish_ready", state.intent.project_context.get("skills", []))
            self.assertIn("publish_ready", workflows)
            self.assertEqual(workflows["publish_ready"]["package_kind"], "publishing")
            self.assertTrue(workflows["publish_ready"]["workflow_steps"])
            self.assertTrue(workflows["publish_ready"]["tool_contract"])
            self.assertTrue(workflows["publish_ready"]["input_contract"])
            self.assertTrue(any("技能流程" in fact for fact in state.facts))
            candidates = runner.session_view(state.session_id)["learning"]["candidates"]
            self.assertFalse(any(item["kind"] == "skill_route" for item in candidates))

    def test_harness_skill_files_are_runtime_source_and_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as project:
            skill_dir = Path(project) / "harness" / "skills" / "publish_ready"
            skill_dir.mkdir(parents=True, exist_ok=True)
            spec_path = skill_dir / "skill.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "skill_id": "publish_ready",
                        "name": "发布适配",
                        "description": "自定义发布适配。",
                        "workflow_hint": "自定义 harness 流程。",
                        "trigger": "发布任务。",
                        "version": "9.9",
                        "package_kind": "custom_publish",
                        "agent_sequence": ["intent_interpreter"],
                        "workflow_steps": ["JSON 流程会被 workflow.md 覆盖。"],
                        "tool_contract": ["custom.tool"],
                        "input_contract": ["custom input"],
                        "output_contract": ["custom output"],
                        "constraints": [],
                        "evaluation": ["custom eval"],
                        "examples": ["自定义例子"],
                        "failure_policy": ["custom failure"],
                        "tags": ["publishing"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (skill_dir / "workflow.md").write_text(
                "# 发布适配 9.9\n\n"
                "## Workflow\n\n"
                "1. 自定义流程，不应被启动覆盖。\n\n"
                "## Tool Contract\n\n"
                "- custom.workflow.tool\n\n"
                "## Output Contract\n\n"
                "- custom workflow output\n\n"
                "## Failure Policy\n\n"
                "- custom workflow failure\n",
                encoding="utf-8",
            )
            runner_module.seed_missing_skill_packages(Path(project) / "harness" / "skills")
            self.assertIn("9.9", spec_path.read_text(encoding="utf-8"))

            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            runner.project_root = Path(project)
            runner.skills = runner_module.load_skill_packages(Path(project) / "harness" / "skills")
            state = runner.run_seed_session(
                request="帮我把内容改成微博版本。",
                user_preferences=["使用技能：publish_ready"],
            )

            workflow = state.intent.project_context["skill_workflows"]["publish_ready"]
            self.assertEqual(workflow["version"], "9.9")
            self.assertEqual(workflow["package_kind"], "custom_publish")
            self.assertIn("自定义流程", workflow["workflow_steps"][0])
            self.assertEqual(workflow["tool_contract"], ["custom.workflow.tool"])

    def test_memory_vector_hybrid_retrieval_and_agent_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp))
            store.append(
                MemoryRecord(
                    layer="L2",
                    content="小红书平台表达需要真实体验感，避免硬广。",
                    tags=["platform", "norm", "小红书"],
                )
            )
            hits = store.search_records("真实分享平台", project_id="default")
            self.assertTrue(any("小红书" in str(item.get("content", "")) for item in hits))

            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session("帮我写一篇小红书体验笔记。")
            roles = [message.role.value for message in state.messages]
            self.assertIn("researcher", roles)
            self.assertIn("memory_curator", roles)

    def test_hybrid_retrieval_prioritizes_exact_entities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp))
            store.append(MemoryRecord(layer="L2", content="角色设定：伊蕾娜是旅行魔女，应保持聪慧、轻快和旁观者视角。", tags=["角色", "伊蕾娜"]))
            store.append(MemoryRecord(layer="L2", content="角色设定：冷峻骑士适合短句和压迫感。", tags=["角色"]))

            hits = store.search_records("伊蕾娜 角色文案", project_id="default")

            self.assertTrue(hits)
            self.assertIn("伊蕾娜", str(hits[0].get("content", "")))

    def test_evolution_manifest_contains_validation_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一个角色宣传微博，不要太模板。",
                feedback_note="这版太模板，AI 味太重。",
            )
            manifest = runner.latest_manifest(state.session_id)
            proposal = manifest["proposals"][0]
            self.assertIn("proposed_change", proposal)
            self.assertNotIn("targeted_fix", proposal)
            self.assertTrue(proposal["validation_plan"])
            self.assertTrue(proposal["predicted_metric"])
            self.assertTrue(state.failure_signals)
            self.assertTrue(any(item.failure_type == "template_style" for item in state.failure_signals))

    def test_naturalness_profile_is_diagnostic_not_rewrite_template(self) -> None:
        template = "创作方向：角色宣传。初稿：这将带来全新体验，让我们一起敬请期待精彩纷呈的内容。"
        plain = "他没有介绍自己，只把旧徽章放在桌上。雨声停了一秒，门外的人也停住了。"

        template_profile = evaluate_naturalness(template)
        plain_profile = evaluate_naturalness(plain)

        self.assertLess(template_profile.score, plain_profile.score)
        self.assertIn("over_explained", template_profile.signals)
        self.assertTrue(template_profile.notes)

    def test_naturalness_comment_and_failure_signal_join_runtime_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeProcessLLM())
            state = runner.run_seed_session("帮我写一个角色宣传微博，不要太模板。")

            self.assertTrue(any("自然度诊断" in comment.comment for comment in state.comments))
            self.assertTrue(any("过程说明" in comment.comment for comment in state.comments))
            self.assertNotIn("变更说明", state.drafts[-1].content)
            self.assertNotIn("待讨论方向", state.drafts[-1].content)

    def test_quality_repair_pass_runs_once_for_template_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeTemplateLLM())
            state = runner.run_seed_session("帮我写一个角色宣传微博，不要太模板。")

            self.assertTrue(state.intent.project_context.get("quality_repair_done"))
            self.assertEqual(sum(1 for event in state.agent_events if event.stage_label == "质量返修" and event.status == "running"), 1)
            self.assertTrue(any(item.failure_type == "template_style" for item in state.failure_signals))
            manifest = runner.latest_manifest(state.session_id)
            self.assertTrue(
                any(
                    proposal["target_component"] in {"harness/agents/draft_writer.md", "harness/rubrics/creative_quality.md"}
                    for proposal in manifest["proposals"]
                )
            )

    def test_import_knowledge_url_records_source_without_search_account(self) -> None:
        original = runner_module.import_public_page
        runner_module.import_public_page = lambda url: {
            "title": "平台规范页面",
            "content": "发布内容需要真实、清晰，避免夸张承诺。",
            "source": url,
        }
        try:
            with tempfile.TemporaryDirectory() as tmp:
                runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
                record = runner.import_knowledge_url(url="https://example.com/rules", kind="norm", tags=["平台规范"])
                self.assertEqual(record["source"], "https://example.com/rules")
                self.assertTrue(runner.knowledge_view(query="夸张承诺")["records"])
        finally:
            runner_module.import_public_page = original

    def test_ab_evaluation_compares_candidate_harness_without_applying_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一个角色宣传微博，不要太模板。",
                feedback_note="这版太模板，AI 味太重。",
            )
            manifest = runner.latest_manifest(state.session_id)
            proposal_id = manifest["proposals"][0]["proposal_id"]
            comparison = runner.run_ab_evaluation(session_id=state.session_id, proposal_id=proposal_id)
            self.assertIn("baseline_average", comparison)
            self.assertIn("candidate_average", comparison)
            self.assertEqual(comparison["metadata"]["proposal_id"], proposal_id)
            self.assertTrue(comparison["metadata"]["proposed_change"])
            self.assertEqual(comparison["metadata"]["baseline_harness_version"], "active")
            self.assertEqual(comparison["metadata"]["candidate_harness_version"], "candidate")
            self.assertIn("candidate_harness_path", comparison["metadata"])
            self.assertTrue(all("naturalness_delta" in item for item in comparison["cases"]))
            self.assertIn(comparison["readiness"], {"applicable", "needs_review", "blocked"})
            self.assertTrue(comparison["readiness_reasons"])
            self.assertTrue(any((Path(tmp) / "evaluations").glob("ab_*.json")))

    def test_ignore_evolution_updates_manifest_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一个角色宣传微博，不要太模板。",
                feedback_note="这版太模板，AI 味太重。",
            )
            manifest = runner.latest_manifest(state.session_id)
            proposal_id = manifest["proposals"][0]["proposal_id"]

            result = runner.ignore_evolution(state.session_id, proposal_id, "这条暂时不采用。")
            updated = runner.latest_manifest(state.session_id)

            self.assertEqual(result["status"], "ignored")
            proposal = next(item for item in updated["proposals"] if item["proposal_id"] == proposal_id)
            self.assertEqual(proposal["status"], "ignored")
            self.assertIn("reviewed_at", proposal)

    def test_project_space_and_observability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            project = runner.create_project("游戏项目", "角色和宣发内容")
            project_id = project["project_id"]
            runner.add_knowledge(
                kind="canon",
                title="角色边界",
                content="角色说话要短，不解释自己的动机。",
                project_id=project_id,
                tags=["角色"],
            )
            state = runner.run_seed_session(
                request="帮我写一个角色登场微博。",
                user_preferences=["短句"],
                project_id=project_id,
            )

            self.assertEqual(state.project_id, project_id)
            self.assertTrue(any("角色边界" in fact for fact in state.facts))
            self.assertTrue(runner.knowledge_view(query="角色", project_id=project_id)["records"])
            self.assertTrue(runner.memory_view(query="角色", project_id=project_id)["records"])
            self.assertGreater(runner.observability_view()["summary"]["total_calls"], 0)

    def test_persona_memory_is_not_auto_confirmed_from_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            first = runner.run_seed_session(
                request="帮我写一段角色文案。",
                user_preferences=["喜欢自然一点"],
            )
            first_l3 = runner.memory.list_records(layer="L3", project_id=first.project_id)
            self.assertFalse(any("喜欢自然一点" in str(item.get("content", "")) for item in first_l3))

            second = runner.run_seed_session(
                request="再帮我写一个角色登场文案。",
                user_preferences=["喜欢自然一点"],
            )
            second_l3 = runner.memory.list_records(layer="L3", project_id=second.project_id)
            self.assertFalse(any("喜欢自然一点" in str(item.get("content", "")) for item in second_l3))

            self.assertFalse(runner.session_view(second.session_id)["learning"]["candidates"])
            runner.complete_session(second.session_id, True)
            self.assertFalse(runner.session_view(second.session_id)["learning"]["candidates"])
            confirmed_l3 = runner.memory.list_records(layer="L3", project_id="global")
            self.assertFalse(any("喜欢自然一点" in str(item.get("content", "")) for item in confirmed_l3))

    def test_delete_session_can_revoke_memory_influence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色文案。",
                user_preferences=["喜欢非常冷峻的句子"],
            )
            before = runner.memory.search_records("冷峻", project_id=state.project_id)
            self.assertTrue(before)

            result = runner.delete_session(state.session_id, mode="revoke_memory")

            self.assertTrue(result["deleted"])
            self.assertGreater(result["revoked_memory_count"], 0)
            after = runner.memory.search_records("冷峻", project_id=state.project_id)
            self.assertFalse(any(state.session_id in (item.get("evidence_ids") or []) for item in after))
            self.assertFalse(any(item["session_id"] == state.session_id for item in runner.memory.list_sessions()))

    def test_delete_session_history_only_keeps_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色文案。",
                user_preferences=["喜欢像档案一样克制"],
            )

            result = runner.delete_session(state.session_id, mode="history")

            self.assertEqual(result["revoked_memory_count"], 0)
            hits = runner.memory.search_records("档案 克制", project_id=state.project_id)
            self.assertTrue(any(state.session_id in (item.get("evidence_ids") or []) for item in hits))

    def test_completion_does_not_auto_create_user_learning_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段小红书体验笔记，避免硬广。",
                user_preferences=["以后默认语气轻一点"],
            )
            view = runner.session_view(state.session_id)
            self.assertFalse(view["learning"]["candidates"])
            runner.complete_session(state.session_id, True)
            view = runner.session_view(state.session_id)
            self.assertFalse(view["learning"]["candidates"])
            global_hits = runner.memory.search_records("轻一点", project_id="default")
            self.assertFalse(any("偏好：" in str(item.get("content", "")) for item in global_hits))

    def test_unconfirmed_session_memory_does_not_cross_conversation_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            first = runner.run_seed_session(request="帮我写一个角色设定。")
            runner.memory.append(
                MemoryRecord(
                    layer="L2",
                    content="本话题临时设定：银蓝钥匙只属于第一条对话。",
                    project_id=first.project_id,
                    evidence_ids=[first.session_id],
                    tags=["context", "creative"],
                )
            )

            second = runner.run_seed_session(request="请围绕银蓝钥匙写一个新角色设定。")

            self.assertFalse(any("第一条对话" in str(fact) for fact in second.facts))

            runner.memory.append(
                MemoryRecord(
                    layer="L2",
                    content="项目规则：银蓝钥匙是可跨对话复用的项目设定。",
                    project_id=first.project_id,
                    evidence_ids=[first.session_id],
                    tags=["project_rule", "confirmed", "scope:project"],
                )
            )

            third = runner.run_seed_session(request="请围绕银蓝钥匙写一个新角色设定。")

            self.assertTrue(any("可跨对话复用" in str(fact) for fact in third.facts))

    def test_user_source_knowledge_is_scoped_to_importing_conversation(self) -> None:
        original = runner_module.import_public_page
        runner_module.import_public_page = lambda url: {
            "title": "临时资料",
            "content": "独有月纹设定只属于导入它的那一次对话。",
            "source": url,
        }
        try:
            with tempfile.TemporaryDirectory() as tmp:
                runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
                first = runner.run_seed_session(request="参考 https://example.com/private-note 写一段角色文案。")
                imported = runner.knowledge_view(query="独有月纹设定")["records"]
                self.assertTrue(any(f"session:{first.session_id}" in (item.get("tags") or []) for item in imported))

                second = runner.run_seed_session(request="独有月纹设定可以用于这个新话题吗？")

                self.assertFalse(any("独有月纹设定" in str(fact) for fact in second.facts))
        finally:
            runner_module.import_public_page = original

    def test_completion_records_session_metrics_without_project_learning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段微博宣发，要求不要夸张承诺。",
            )
            runner.complete_session(state.session_id, True)

            hits = runner.memory.search_records("夸张承诺 微博", project_id=state.project_id)
            self.assertFalse(any("项目规则" in str(item.get("content", "")) for item in hits))
            summary = runner.observability_view()["product_metrics"]
            self.assertGreater(summary["counts"].get("session_finalized", 0), 0)
            self.assertEqual(summary["counts"].get("learning_confirmed", 0), 0)

    def test_project_rules_are_not_auto_suggested_on_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写角色文案，要求不要改掉角色的沉默设定。",
            )
            runner.complete_session(state.session_id, True)
            candidates = runner.session_view(state.session_id)["learning"]["candidates"]
            self.assertFalse(candidates)

    def test_saved_preferences_can_be_listed_and_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色文案。",
                user_preferences=["以后默认不要模板腔"],
            )
            runner.memory.append(
                MemoryRecord(
                    layer="L3",
                    content="偏好：以后默认不要模板腔",
                    project_id="global",
                    evidence_ids=[state.session_id],
                    tags=["preference", "confirmed", "scope:global"],
                )
            )

            preferences = runner.preferences_view()["preferences"]
            self.assertTrue(any("不要模板腔" in str(item.get("display_content", "")) for item in preferences))
            record_id = str(preferences[0]["record_id"])
            deleted = runner.delete_preference(record_id)

            self.assertTrue(deleted["changed"])
            remaining = runner.preferences_view()["preferences"]
            self.assertFalse(any(item["record_id"] == record_id for item in remaining))

    def test_delete_session_revokes_learning_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色文案。",
                user_preferences=["喜欢低温一点的表达"],
            )
            runner.complete_session(state.session_id, True)

            result = runner.delete_session(state.session_id, mode="revoke_memory")

            self.assertEqual(result["revoked_learning_count"], 0)
            candidates = runner.learning.list(session_id=state.session_id)
            self.assertTrue(all(item["status"] == "revoked" for item in candidates))

    def test_completion_skips_negation_learning_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段微博角色登场文案，要求不要夸张承诺，这次语气冷一点。",
            )
            self.assertFalse(runner.session_view(state.session_id)["learning"]["candidates"])
            runner.complete_session(state.session_id, True)

            candidates = runner.session_view(state.session_id)["learning"]["candidates"]
            self.assertFalse(candidates)

    def test_completion_does_not_create_platform_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段小红书活动笔记，要求小红书不要硬广。",
            )
            runner.complete_session(state.session_id, True)

            candidates = runner.session_view(state.session_id)["learning"]["candidates"]
            platform_candidates = [item for item in candidates if item["kind"] == "platform_rule"]
            self.assertFalse(platform_candidates)

    def test_session_completion_can_be_toggled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(request="帮我写一段角色文案，要求不要夸张承诺。")

            completed = runner.complete_session(state.session_id, True)
            view = runner.session_view(state.session_id)
            self.assertTrue(completed["completed"])
            self.assertTrue(view["session"]["completed"])
            self.assertTrue(view["session"]["completed_at"])

            runner.complete_session(state.session_id, False)
            view = runner.session_view(state.session_id)
            self.assertFalse(view["session"]["completed"])
            self.assertFalse(view["session"]["completed_at"])

    def test_completion_review_only_returns_workflow_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色宣发文案，要求不要模板腔。",
                user_preferences=["以后默认保持角色冷面克制"],
            )
            runner.complete_session(state.session_id, True)

            review_items = runner.session_view(state.session_id)["review"]["items"]
            source_types = {item["source_type"] for item in review_items}
            self.assertIn("assistant_workflow", source_types)
            self.assertNotIn("memory", source_types)
            self.assertTrue(all(item["status"] == "pending" for item in review_items))

    def test_review_accept_and_skip_use_workflow_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色文案，要求不要模板腔。",
                user_preferences=["以后默认保持角色冷面克制"],
            )
            runner.complete_session(state.session_id, True)
            view = runner.session_view(state.session_id)
            workflow_item = next(item for item in view["review"]["items"] if item["source_type"] == "assistant_workflow")

            blocked = runner.accept_review_item(state.session_id, workflow_item["item_id"])

            self.assertEqual(blocked["status"], "blocked")
            updated = runner.session_view(state.session_id)["review"]["items"]
            self.assertFalse(any(item["item_id"] == workflow_item["item_id"] for item in updated))

    def test_agent_events_and_skill_runs_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我把角色登场文案改成微博版本。",
                user_preferences=["使用技能：publish_ready"],
            )

            view = runner.session_view(state.session_id)
            self.assertTrue(view["agent_events"])
            self.assertTrue(any(item["status"] == "completed" and item["role"] == "draft_writer" for item in view["agent_events"]))

            observability = runner.observability_view()
            self.assertTrue(observability["skill_runs"])
            skill_run = observability["skill_runs"][0]
            self.assertEqual(skill_run["skill_id"], "publish_ready")
            self.assertIn("agent_sequence_used", skill_run)
            self.assertIn("critic_scores", skill_run)

    def test_capability_eval_cases_cover_launch_readiness(self) -> None:
        root = Path(__file__).resolve().parents[1] / "harness" / "capabilities"
        for path in root.glob("*/eval_cases.json"):
            cases = json.loads(path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(cases), 7, path)
            case_types = {case.get("case_type") for case in cases}
            self.assertIn("happy_path", case_types)
            self.assertIn("scope_safety", case_types)
            self.assertIn("chinese_naturalness", case_types)

    def test_workspace_doctor_and_rebuild_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            runner.run_seed_session(
                request="帮我写一个可发布的短文。",
                capability_id="idea_to_draft",
            )

            doctor = runner.data_doctor()
            self.assertIn(doctor["status"], {"pass", "warn"})
            self.assertGreaterEqual(doctor["summary"]["sessions"], 1)

            rebuilt = runner.rebuild_indexes()
            self.assertGreaterEqual(rebuilt["memory"]["records_indexed"], 1)
            self.assertIn("doctor", rebuilt)

    def test_skill_composition_deduplicates_and_suppresses_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="把这段文案改自然一点，同时不要跑偏成多个方案。",
                user_preferences=[
                    "使用技能：revision_studio",
                    "使用技能：revision_studio",
                    "使用技能：variant_lab",
                ],
            )

            skills = state.intent.project_context.get("skills", [])
            plan = state.intent.project_context.get("skill_plan", {})
            self.assertEqual(skills, ["revision_studio"])
            self.assertEqual(plan.get("primary"), "revision_studio")
            self.assertIn("variant_lab", plan.get("suppressed", []))
            self.assertEqual(sum(1 for fact in state.facts if fact.startswith("技能包：深度改稿")), 1)

    def test_delete_session_keeps_confirmed_preferences_by_default_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色文案。",
                user_preferences=["以后默认不要模板腔"],
            )
            runner.memory.append(
                MemoryRecord(
                    layer="L3",
                    content="偏好：以后默认不要模板腔",
                    project_id="global",
                    evidence_ids=[state.session_id],
                    tags=["preference", "confirmed", "scope:global"],
                )
            )

            result = runner.delete_session(state.session_id, mode="revoke_memory")

            self.assertTrue(result["deleted"])
            preferences = runner.preferences_view()["preferences"]
            self.assertTrue(any("不要模板腔" in str(item.get("display_content", "")) for item in preferences))

    def test_reopen_completed_session_does_not_revoke_absent_learning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色文案。",
                user_preferences=["以后默认保持冷淡克制的角色语气"],
            )
            runner.complete_session(state.session_id, True)

            result = runner.complete_session(state.session_id, False, revoke_learning_on_reopen=True)

            self.assertEqual(result["revoked_learning_count"], 0)
            self.assertEqual(result["revoked_confirmed_learning_count"], 0)
            preferences = runner.preferences_view()["preferences"]
            self.assertFalse(any("冷淡克制" in str(item.get("display_content", "")) for item in preferences))

    def test_completion_learning_candidates_are_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段视频脚本。",
                user_preferences=[
                    "以后默认涉及B站视频脚本时，优先输出分镜、画面、旁白、节奏、镜头运动、字幕节奏，并避免把平台规则直接写进正文里造成观感很生硬"
                ],
            )
            runner.complete_session(state.session_id, True)

            candidates = runner.session_view(state.session_id)["learning"]["candidates"]
            self.assertFalse(candidates)

    def test_atomic_storage_helpers_preserve_json_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_path = root / "data.json"
            jsonl_path = root / "records.jsonl"
            text_path = root / "note.txt"

            atomic_write_json(json_path, {"title": "作品", "items": [1, 2]})
            atomic_write_jsonl(jsonl_path, [{"id": "a"}, {"id": "b"}])
            atomic_write_text(text_path, "hello")

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["title"], "作品")
            self.assertEqual([json.loads(line)["id"] for line in jsonl_path.read_text(encoding="utf-8").splitlines()], ["a", "b"])
            self.assertEqual(text_path.read_text(encoding="utf-8"), "hello")


if __name__ == "__main__":
    unittest.main()
