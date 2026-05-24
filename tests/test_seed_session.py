from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ECROOM_VECTOR_BACKEND", "memory")

from evolving_creative_room.llm import ChatMessage, LLMResponse
from evolving_creative_room.memory.store import MemoryRecord, MemoryStore
from evolving_creative_room.models import FeedbackSignal
import evolving_creative_room.orchestration.runner as runner_module
from evolving_creative_room.orchestration import CreativeRoomRunner


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
            assets = runner.assets_view()["assets"]
            self.assertTrue(any(item.get("post_id") == draft["post_id"] and item.get("source") == "published" for item in assets))
            deleted = runner.delete_post(draft["post_id"])
            self.assertTrue(deleted["deleted"])
            self.assertFalse(any(item["post_id"] == draft["post_id"] for item in runner.published_posts_view()["posts"]))
            self.assertFalse(any(item.get("post_id") == draft["post_id"] for item in runner.assets_view()["assets"]))

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
            self.assertTrue(proposal["validation_plan"])
            self.assertTrue(proposal["predicted_metric"])

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
            self.assertTrue(any((Path(tmp) / "evaluations").glob("ab_*.json")))

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

    def test_persona_memory_requires_user_confirmation(self) -> None:
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

            candidate = next(item for item in runner.session_view(second.session_id)["learning"]["candidates"] if item["kind"] == "preference")
            runner.apply_learning(str(candidate["candidate_id"]), "preference")
            confirmed_l3 = runner.memory.list_records(layer="L3", project_id="global")
            self.assertTrue(any("喜欢自然一点" in str(item.get("content", "")) for item in confirmed_l3))

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

    def test_learning_candidates_are_scoped_before_becoming_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段小红书体验笔记，避免硬广。",
                user_preferences=["以后默认语气轻一点"],
            )
            view = runner.session_view(state.session_id)
            candidates = view["learning"]["candidates"]
            self.assertTrue(candidates)
            preference = next(item for item in candidates if item["kind"] == "preference")
            self.assertEqual(preference["suggested_scope"], "global")

            result = runner.apply_learning(str(preference["candidate_id"]), "global")

            self.assertEqual(result["candidate"]["status"], "global_active")
            global_hits = runner.memory.search_records("轻一点", project_id="default")
            self.assertTrue(any("偏好：" in str(item.get("content", "")) for item in global_hits))

    def test_project_learning_and_metrics_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段微博宣发，要求不要夸张承诺。",
            )
            candidate = next(item for item in runner.session_view(state.session_id)["learning"]["candidates"] if item["kind"] in {"project_rule", "platform_rule"})

            runner.apply_learning(str(candidate["candidate_id"]), "project")

            hits = runner.memory.search_records("夸张承诺 微博", project_id=state.project_id)
            self.assertTrue(any("项目规则" in str(item.get("content", "")) for item in hits))
            summary = runner.observability_view()["product_metrics"]
            self.assertGreater(summary["counts"].get("session_finalized", 0), 0)
            self.assertGreater(summary["counts"].get("learning_confirmed", 0), 0)

    def test_saved_preferences_can_be_listed_and_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色文案。",
                user_preferences=["以后默认不要模板腔"],
            )
            candidate = next(item for item in runner.session_view(state.session_id)["learning"]["candidates"] if item["kind"] == "preference")
            runner.apply_learning(str(candidate["candidate_id"]), "preference")

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

            result = runner.delete_session(state.session_id, mode="revoke_memory")

            self.assertGreater(result["revoked_learning_count"], 0)
            candidates = runner.learning.list(session_id=state.session_id)
            self.assertTrue(all(item["status"] == "revoked" for item in candidates))

    def test_learning_candidates_preserve_negation_and_skip_ephemeral(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段微博角色登场文案，要求不要夸张承诺，这次语气冷一点。",
            )

            candidates = runner.session_view(state.session_id)["learning"]["candidates"]
            contents = [str(item.get("content", "")) for item in candidates]

            self.assertTrue(any("不要夸张承诺" in content for content in contents))
            self.assertFalse(any(content.strip() == "夸张承诺" for content in contents))
            self.assertFalse(any("这次语气冷一点" in content or content.strip() == "冷一点" for content in contents))

    def test_platform_candidates_are_readable_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段小红书活动笔记，要求小红书不要硬广。",
            )

            candidates = runner.session_view(state.session_id)["learning"]["candidates"]
            platform_candidates = [item for item in candidates if item["kind"] == "platform_rule"]
            self.assertTrue(platform_candidates)
            self.assertTrue(any("小红书" in str(item.get("content", "")) for item in platform_candidates))
            self.assertFalse(any(str(item.get("content", "")).startswith("平台规范线索：") for item in platform_candidates))

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

    def test_delete_session_keeps_confirmed_preferences_by_default_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CreativeRoomRunner(Path(tmp), llm=FakeLLM())
            state = runner.run_seed_session(
                request="帮我写一段角色文案。",
                user_preferences=["以后默认不要模板腔"],
            )
            candidate = next(item for item in runner.session_view(state.session_id)["learning"]["candidates"] if item["kind"] == "preference")
            runner.apply_learning(str(candidate["candidate_id"]), "preference")

            result = runner.delete_session(state.session_id, mode="revoke_memory")

            self.assertTrue(result["deleted"])
            preferences = runner.preferences_view()["preferences"]
            self.assertTrue(any("不要模板腔" in str(item.get("display_content", "")) for item in preferences))


if __name__ == "__main__":
    unittest.main()
