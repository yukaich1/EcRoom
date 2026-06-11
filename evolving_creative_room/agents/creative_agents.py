from __future__ import annotations

import re

from evolving_creative_room.agents.base import AgentResult
from evolving_creative_room.llm import ChatMessage, LLMClient, LLMError
from evolving_creative_room.models import AgentRole, CreativeState
from evolving_creative_room.naturalness import evaluate_naturalness


class IntentInterpreter:
    role = AgentRole.INTENT_INTERPRETER

    def run(self, state: CreativeState) -> AgentResult:
        text = state.intent.raw_request
        lowered = text.lower()

        if not state.intent.goal:
            state.intent.goal = _infer_goal(text)
        if not state.intent.medium:
            state.intent.medium = _infer_medium(text)
        if not state.intent.audience:
            state.intent.audience = _infer_audience(text)

        if "微博" in text or "weibo" in lowered:
            _append_unique(state.intent.constraints, "适合微博的短表达和转发语境")
        if "小红书" in text or "rednote" in lowered or "xiaohongshu" in lowered:
            _append_unique(state.intent.constraints, "适合生活方式平台的真实分享语气")
        if any(word in text for word in ["角色", "剧情", "世界观", "任务", "npc", "NPC"]):
            _append_unique(state.intent.constraints, "保持角色、世界观和剧情状态一致")
            _append_unique(state.intent.evaluation_criteria, "设定一致性")
        if any(word in text for word in ["宣传", "发布", "种草", "营销"]):
            _append_unique(state.intent.evaluation_criteria, "传播吸引力")
        _append_unique(state.intent.evaluation_criteria, "清晰度")
        _append_unique(state.intent.evaluation_criteria, "用户风格贴合度")

        state.add_message(self.role, f"Interpreted intent: {state.intent.summary()}")
        return AgentResult(self.role, "Creative intent interpreted.")


class Strategist:
    role = AgentRole.STRATEGIST

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    def run(self, state: CreativeState) -> AgentResult:
        if self.llm:
            result = _try_llm_strategy(self.llm, state)
            if result:
                state.strategy.extend(item for item in result if item not in state.strategy)
                state.add_message(self.role, "\n".join(result), llm_provider=self.llm.provider, llm_model=self.llm.model)
                return AgentResult(self.role, "LLM creative strategy created.", {"strategy_count": len(result)})

        intent = state.intent
        strategy = [
            "先确认创作目标，再选择表达形态，而不是套固定模板。",
            "用一个主版本承载核心表达，再生成少量风格变体供用户判断。",
            "把平台规范、项目设定、用户偏好拆成不同约束，避免互相污染。",
        ]
        if "角色" in intent.raw_request or "世界观" in intent.raw_request:
            strategy.append("先写角色/设定内核，再改写成面向外部传播的版本。")
        if "微博" in intent.raw_request or "小红书" in intent.raw_request:
            strategy.append("保留社交平台的第一眼钩子，但避免过度营销腔。")
        state.strategy.extend(item for item in strategy if item not in state.strategy)
        state.add_message(self.role, "\n".join(strategy))
        return AgentResult(self.role, "Creative strategy created.", {"strategy_count": len(strategy)})


class DraftWriter:
    role = AgentRole.DRAFT_WRITER

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    def run(self, state: CreativeState) -> AgentResult:
        if self.llm:
            result = _try_llm_draft(self.llm, state)
            if result:
                version = state.add_draft(result, self.role, rationale=f"LLM draft from {self.llm.provider}/{self.llm.model}.")
                state.add_message(
                    self.role,
                    f"Created LLM draft {version.version_id}.",
                    llm_provider=self.llm.provider,
                    llm_model=self.llm.model,
                )
                return AgentResult(self.role, f"LLM draft {version.version_id} created.")

        intent = state.intent
        draft = (
            f"创作方向：{intent.goal or intent.raw_request}\n\n"
            f"这版先把重点放在“{intent.summary()}”上。"
            "内容应该像一个懂项目语境的人在和目标受众说话，"
            "既保留表达的温度，也把关键卖点、角色张力或观点锋芒放在前面。\n\n"
            "初稿：\n"
            f"{_seed_opening(intent.raw_request)}\n"
            "如果这是对外发布稿，它需要一个更有记忆点的开头；"
            "如果这是叙事/角色文案，它需要让角色动机和世界状态先站稳。"
        )
        version = state.add_draft(draft, self.role, rationale="First structured seed draft.")
        state.add_message(self.role, f"Created draft {version.version_id}.")
        return AgentResult(self.role, f"Draft {version.version_id} created.")


class EditorAgent:
    role = AgentRole.EDITOR

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    def run(self, state: CreativeState) -> AgentResult:
        if not state.drafts:
            return AgentResult(self.role, "No draft to edit.")
        last = state.drafts[-1]
        if self.llm:
            result = _try_llm_edit(self.llm, state, last.content)
            if result:
                cleaned = _extract_final_copy(result)
                version = state.add_draft(
                    cleaned,
                    self.role,
                    rationale=f"LLM edit from {self.llm.provider}/{self.llm.model}.",
                    parent_version_id=last.version_id,
                )
                if cleaned != result:
                    state.add_comment(
                        self.role,
                        version.version_id,
                        "已将编辑过程说明从正文中移出，只保留可继续打磨的正文。",
                        severity="quality",
                    )
                state.add_message(
                    self.role,
                    f"Edited draft {last.version_id} into {version.version_id} with LLM.",
                    llm_provider=self.llm.provider,
                    llm_model=self.llm.model,
                )
                return AgentResult(self.role, f"LLM edited draft {version.version_id}.")
        edited = _local_edit(last.content, state)
        version = state.add_draft(
            edited,
            self.role,
            rationale="Local process-note cleanup and conservative revision.",
            parent_version_id=last.version_id,
        )
        state.add_comment(
            self.role,
            version.version_id,
            "本轮只做保守返修：移出过程说明，保留原始意图和可继续修改的正文。",
            severity="quality",
        )
        state.add_message(self.role, f"Edited draft {last.version_id} into {version.version_id}.")
        return AgentResult(self.role, f"Edited draft {version.version_id}.")


class CriticPanel:
    role = AgentRole.CRITIC

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    def run(self, state: CreativeState) -> AgentResult:
        if not state.drafts:
            return AgentResult(self.role, "No draft to critique.")
        draft = state.drafts[-1]
        if self.llm:
            comments = _try_llm_critique(self.llm, state, draft.content)
            if comments:
                for comment in comments:
                    state.add_comment(self.role, draft.version_id, comment)
                _add_naturalness_comment(state, draft.version_id, draft.content)
                state.add_message(
                    self.role,
                    f"Added {len(comments)} LLM critique comments for {draft.version_id}.",
                    llm_provider=self.llm.provider,
                    llm_model=self.llm.model,
                )
                return AgentResult(self.role, "LLM critique comments added.")

        criteria = state.intent.evaluation_criteria or ["清晰度", "风格贴合度"]
        for criterion in criteria:
            state.add_comment(
                self.role,
                draft.version_id,
                f"按“{criterion}”检查：当前版本还需要用户反馈来确定取舍。",
            )
        _add_naturalness_comment(state, draft.version_id, draft.content)
        state.add_message(self.role, f"Critiqued {draft.version_id} with {len(criteria)} criteria.")
        return AgentResult(self.role, "Critique comments added.")


class ResearchAgent:
    role = AgentRole.RESEARCHER

    def __init__(self, memory=None, knowledge=None) -> None:
        self.memory = memory
        self.knowledge = knowledge

    def run(self, state: CreativeState) -> AgentResult:
        query = " ".join([state.intent.raw_request, *state.intent.constraints, *state.intent.user_preferences])
        hits = []
        if self.memory:
            hits.extend(f"memory:{item.get('content', '')}" for item in self.memory.search_records(query, limit=4, project_id=state.project_id))
        if self.knowledge:
            hits.extend(f"knowledge:{item.get('title', '')} - {item.get('content', '')}" for item in self.knowledge.search(query, limit=4, project_id=state.project_id))
        selected = []
        for hit in hits:
            if hit and hit not in state.facts:
                state.facts.append(hit)
                selected.append(hit)
        state.add_message(self.role, f"检索并整理 {len(selected)} 条素材/记忆。")
        return AgentResult(self.role, "Research context prepared.", {"hit_count": len(selected)})


class MemoryCuratorAgent:
    role = AgentRole.MEMORY_CURATOR

    def run(self, state: CreativeState) -> AgentResult:
        signals = []
        if state.intent.user_preferences:
            signals.append(f"偏好信号 {len(state.intent.user_preferences)} 条")
        if state.intent.constraints:
            signals.append(f"规则/约束 {len(state.intent.constraints)} 条")
        if state.human_feedback:
            signals.append(f"反馈 {len(state.human_feedback)} 条")
        summary = "；".join(signals) if signals else "暂无强记忆信号"
        state.add_message(self.role, f"记忆整理计划：{summary}。")
        return AgentResult(self.role, "Memory signals reviewed.", {"signal_summary": summary})


class NormSteward:
    role = AgentRole.NORM_STEWARD

    def run(self, state: CreativeState) -> AgentResult:
        if not state.drafts:
            return AgentResult(self.role, "No draft to review for norms.")

        draft = state.drafts[-1]
        rules = []
        request = state.intent.raw_request
        if "微博" in request:
            rules.append("微博语境：避免蹭无关热搜、虚假信息、过度营销和侵犯权益内容。")
        if "小红书" in request:
            rules.append("小红书语境：强调真实分享，商业利益相关需要清楚表达。")
        if any(term in request for term in ["游戏", "角色", "剧情", "世界观", "NPC", "npc"]):
            rules.append("叙事语境：角色口吻、世界观事实、剧情时间线应保持一致。")
        if not rules:
            rules.append("通用规范：检查事实、版权、隐私、歧视、低俗、夸大承诺等风险。")
        for fact in state.facts:
            if fact.startswith("norm") or "规范" in fact or "规则" in fact:
                rules.append(f"资料库提示：{fact}")

        for rule in rules:
            state.add_comment(self.role, draft.version_id, rule, severity="norm")
        state.warnings.extend(rule for rule in rules if rule not in state.warnings)
        state.add_message(self.role, f"Norm review added {len(rules)} rules.")
        return AgentResult(self.role, "Norm guidance added.", {"rule_count": len(rules)})


def _infer_goal(text: str) -> str:
    if "宣传" in text:
        return "宣传与传播"
    if "角色" in text:
        return "角色塑造"
    if "世界观" in text:
        return "世界观表达"
    if "发帖" in text or "发布" in text:
        return "平台发布"
    return "内容共创"


def _infer_medium(text: str) -> str:
    return "泛用内容创作"


def _infer_audience(text: str) -> str:
    match = re.search(r"给(.{1,12}?)(看|用|发|写)", text)
    if match:
        return match.group(1)
    if "玩家" in text:
        return "玩家"
    if "粉丝" in text:
        return "粉丝"
    return "待澄清受众"


def _append_unique(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _extract_final_copy(text: str) -> str:
    value = text.strip()
    if not value:
        return value
    lines = [line.rstrip() for line in value.splitlines()]
    section_starts = []
    stop_terms = ("变更说明", "修改说明", "待讨论方向", "请确认", "具体调整如下", "说明：")
    copy_terms = ("编辑版", "修订版", "正文", "最终稿")
    for index, line in enumerate(lines):
        stripped = line.strip(" *#：:")
        if any(term in stripped for term in copy_terms):
            section_starts.append(index + 1)
    for start in section_starts:
        collected = []
        for line in lines[start:]:
            stripped = line.strip()
            header = stripped.strip(" *#：:")
            if any(term in header for term in stop_terms):
                break
            if stripped in {"---", "```"}:
                continue
            collected.append(line)
        candidate = "\n".join(collected).strip().strip("\"“”")
        if len(candidate) >= 8:
            return candidate

    kept = []
    skip = False
    for line in lines:
        stripped = line.strip()
        header = stripped.strip(" *#：:")
        if any(term in header for term in stop_terms):
            skip = True
            continue
        if skip:
            continue
        if stripped.startswith("以下是") or stripped in {"---", "```"}:
            continue
        kept.append(line)
    candidate = "\n".join(kept).strip().strip("\"“”")
    return candidate or value


def _local_edit(text: str, state: CreativeState) -> str:
    cleaned = _extract_final_copy(text)
    cleaned = re.sub(r"创作方向：.*?(?:\n\n|$)", "", cleaned, flags=re.S).strip()
    cleaned = re.sub(r"初稿：\s*", "", cleaned).strip()
    cleaned = re.sub(r"如果这是.*", "", cleaned).strip()
    if len(cleaned) >= 20:
        return cleaned
    return _seed_opening(state.intent.raw_request)


def _add_naturalness_comment(state: CreativeState, draft_id: str, draft: str) -> None:
    profile = evaluate_naturalness(
        draft,
        request=state.intent.raw_request,
        feedback=[item.note for item in state.human_feedback if item.note],
        platforms=_detect_platforms(state.intent.raw_request),
    )
    state.add_comment(
        AgentRole.CRITIC,
        draft_id,
        f"自然度诊断：{profile.score:.2f}。{'；'.join(profile.notes)}",
        severity="quality",
    )


def _detect_platforms(text: str) -> list[str]:
    platforms = ["微博", "小红书", "公众号", "B站", "抖音"]
    return [platform for platform in platforms if platform in text]


def _seed_opening(request: str) -> str:
    if any(word in request for word in ["角色", "剧情", "世界观"]):
        return "他第一次出现时，世界并没有为他让路，但所有人都意识到，旧秩序开始松动了。"
    if "小红书" in request:
        return "这不是那种一眼就很用力的推荐，更像是我真的用过之后，想留下的一点经验。"
    if "微博" in request:
        return "一句话说清楚：真正值得记住的，不是设定本身，而是它带来的情绪。"
    return "先把真正想表达的东西放在前面，再决定它应该长成什么形式。"


def _system_prompt() -> str:
    return (
        "你在 EcRoom 中工作。用户是创意总监和共同作者。"
        "你要先尊重 Creative Intent，再生成可讨论、可修改的内容。"
        "输出用中文，避免空泛套话。"
    )


def _intent_brief(state: CreativeState) -> str:
    intent = state.intent
    return (
        f"原始需求：{intent.raw_request}\n"
        f"目标：{intent.goal}\n"
        f"受众：{intent.audience}\n"
        f"载体：{intent.medium}\n"
        f"约束：{'；'.join(intent.constraints) or '暂无'}\n"
        f"风格：{'；'.join(intent.style) or '暂无'}\n"
        f"评价标准：{'；'.join(intent.evaluation_criteria) or '暂无'}\n"
        f"用户偏好：{'；'.join(intent.user_preferences) or '暂无'}\n"
        f"召回上下文：{'；'.join(state.facts[:8]) or '暂无'}"
    )


def _safe_chat(llm: LLMClient, messages: list[ChatMessage], *, max_tokens: int = 900) -> str | None:
    try:
        return llm.chat(messages, max_tokens=max_tokens).content
    except LLMError:
        return None


def _try_llm_strategy(llm: LLMClient, state: CreativeState) -> list[str] | None:
    content = _safe_chat(
        llm,
        [
            ChatMessage("system", _system_prompt()),
            ChatMessage(
                "user",
                _intent_brief(state)
                + "\n\n请给出 3-5 条创作策略。每条一行，直接写策略，不要编号解释。",
            ),
        ],
        max_tokens=500,
    )
    if not content:
        return None
    return [line.strip(" -1234567890.、") for line in content.splitlines() if line.strip()][:5]


def _try_llm_draft(llm: LLMClient, state: CreativeState) -> str | None:
    return _safe_chat(
        llm,
        [
            ChatMessage("system", _system_prompt()),
            ChatMessage(
                "user",
                _intent_brief(state)
                + "\n\n请写一版可继续讨论的初稿。保留创作感，不要写成说明文。"
                "如果任务同时包含角色/世界观和平台传播，请自然融合两者。",
            ),
        ],
        max_tokens=1200,
    )


def _try_llm_edit(llm: LLMClient, state: CreativeState, draft: str) -> str | None:
    return _safe_chat(
        llm,
        [
            ChatMessage("system", _system_prompt()),
            ChatMessage(
                "user",
                _intent_brief(state)
                + "\n\n下面是上一版草稿，请做一次编辑。保留有效部分，删掉模板感，增强自然度和可用性。\n\n"
                + draft,
            ),
        ],
        max_tokens=1200,
    )


def _try_llm_critique(llm: LLMClient, state: CreativeState, draft: str) -> list[str] | None:
    content = _safe_chat(
        llm,
        [
            ChatMessage("system", _system_prompt()),
            ChatMessage(
                "user",
                _intent_brief(state)
                + "\n\n请评审下面草稿。输出 3-5 条具体修改建议，每条一行，不要泛泛打分。\n\n"
                + draft,
            ),
        ],
        max_tokens=700,
    )
    if not content:
        return None
    return [line.strip(" -1234567890.、") for line in content.splitlines() if line.strip()][:5]
