from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CreativeSkill:
    skill_id: str
    name: str
    description: str
    workflow_hint: str
    trigger: str
    version: str = "1.0"
    package_kind: str = "workflow"
    agent_sequence: list[str] = field(default_factory=list)
    workflow_steps: list[str] = field(default_factory=list)
    tool_contract: list[str] = field(default_factory=list)
    input_contract: list[str] = field(default_factory=list)
    output_contract: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    evaluation: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    failure_policy: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


SKILLS: dict[str, CreativeSkill] = {
    "creative_brief": CreativeSkill(
        skill_id="creative_brief",
        name="创作诊断",
        description="把模糊想法整理成可执行的创作 brief，再决定后续路线。",
        workflow_hint="先追踪目标、受众、使用场景、限制和成功标准，再组织下一步创作。",
        trigger="用户只有一个初步想法、方向很散，或希望先讨论清楚再写。",
        version="1.0",
        package_kind="planning",
        agent_sequence=["intent_interpreter", "researcher", "strategist", "critic_panel"],
        workflow_steps=[
            "拆分用户输入中的目标、受众、载体、约束、禁用项和参考材料。",
            "判断哪些信息足够生成，哪些信息需要用假设方式处理。",
            "形成一个可执行 brief，并给出 2-3 条创作路线。",
            "输出前标注本次只在当前会话生效的临时偏好。",
        ],
        tool_contract=["memory.search(preference,project)", "knowledge.search(project,style)"],
        input_contract=["原始想法", "可选平台或使用场景", "可选参考材料", "禁用或必须保留的信息"],
        output_contract=["创作 brief", "可选方向", "下一步建议"],
        constraints=["不把临时创作倾向固化为长期用户画像。"],
        evaluation=["需求清晰度", "约束完整度", "下一步可执行性"],
        examples=["我有一个游戏活动点子，但还没想清楚怎么写。"],
        failure_policy=["信息不足时先给假设 brief，不强迫用户填表。"],
        tags=["planning", "brief"],
    ),
    "source_grounded": CreativeSkill(
        skill_id="source_grounded",
        name="资料驱动",
        description="围绕链接、素材、平台规范或项目资料进行检索、整理和生成。",
        workflow_hint="先处理来源和证据，再把可靠信息转化为创作内容。",
        trigger="用户提供链接、资料、参考作品、平台规则、禁用词或需要事实依据。",
        version="1.0",
        package_kind="research",
        agent_sequence=["intent_interpreter", "researcher", "norm_steward", "strategist", "draft_writer", "critic_panel"],
        workflow_steps=[
            "识别链接、平台、实体名、作品名和规则线索。",
            "导入或召回资料库、记忆库和平台规范。",
            "区分确定事实、用户设定、参考风格和待验证信息。",
            "生成内容时只使用已确认或明确标注为参考的信息。",
        ],
        tool_contract=["url.import", "memory.search(hybrid)", "knowledge.search(hybrid)", "norm.review"],
        input_contract=["链接或资料文本", "要使用的部分", "目标内容类型", "引用边界"],
        output_contract=["来源摘要", "可用素材", "生成内容", "风险或不确定项"],
        constraints=["不把参考作品当作可复制内容，不编造来源。"],
        evaluation=["素材命中率", "事实谨慎度", "引用边界", "规范安全"],
        examples=["参考这篇规则和这个角色设定，帮我写一版发布文案。"],
        failure_policy=["资料无法访问时保留 URL 线索，并降低事实置信度。"],
        tags=["research", "norm", "source"],
    ),
    "narrative_canon": CreativeSkill(
        skill_id="narrative_canon",
        name="叙事设定",
        description="处理角色、世界观、剧情、势力和 canon 一致性。",
        workflow_hint="先锁定不可变设定，再生成能继续扩展的叙事文本。",
        trigger="用户要求角色登场、人物小传、世界观、任务剧情、势力冲突或游戏宣发。",
        version="1.0",
        package_kind="domain",
        agent_sequence=["intent_interpreter", "researcher", "strategist", "draft_writer", "critic_panel", "norm_steward"],
        workflow_steps=[
            "抽取角色身份、欲望、冲突、口吻、世界观事实和不可改动设定。",
            "区分 canon、临时设定、参考风格和可发挥空白。",
            "生成角色/世界观正文，并保留可传播短版或剧情钩子。",
            "检查角色动机、时间线、设定边界和平台传播语气。",
        ],
        tool_contract=["memory.search(character,canon)", "knowledge.search(project,canon)", "consistency.check"],
        input_contract=["角色或世界观素材", "不可改动设定", "目标用途", "参考风格"],
        output_contract=["设定内核", "正文版本", "可传播短版", "一致性提醒"],
        constraints=["参考对象只能作为风格和结构参考，不能直接复刻表达。"],
        evaluation=["角色辨识度", "设定一致性", "情绪张力", "可扩展性"],
        examples=["写一个参考伊蕾娜气质的旅行魔女，但设定必须是原创。"],
        failure_policy=["设定冲突时优先指出冲突，再给出保守版本。"],
        tags=["character", "worldbuilding", "canon"],
    ),
    "publish_ready": CreativeSkill(
        skill_id="publish_ready",
        name="发布适配",
        description="把内容改成能面向具体平台或场景发布的版本。",
        workflow_hint="先保留核心信息，再针对平台语气、长度、标题、节奏和风险做适配。",
        trigger="用户希望内容发到微博、小红书、公众号、B站、活动页或其他发布场景。",
        version="1.0",
        package_kind="publishing",
        agent_sequence=["intent_interpreter", "researcher", "norm_steward", "strategist", "draft_writer", "editor", "critic_panel"],
        workflow_steps=[
            "识别目标平台、受众、发布目的和必须保留的信息。",
            "召回平台表达习惯、风险边界和用户历史偏好。",
            "生成一个主版本和必要的平台变体，不把规则解释写进正文。",
            "输出平台差异、发布前风险和可继续修改点。",
        ],
        tool_contract=["memory.search(platform,preference)", "knowledge.search(norm,platform)", "norm.review"],
        input_contract=["原始内容或想法", "目标平台", "发布目的", "禁用表达"],
        output_contract=["发布版本", "平台差异", "风险提醒"],
        constraints=["平台规范作为后台约束，正文仍要自然。"],
        evaluation=["平台贴合度", "核心信息保留", "自然度", "规范安全"],
        examples=["同一个角色内容，分别改成微博和小红书版本。"],
        failure_policy=["平台不明确时生成通用版，并标注可适配方向。"],
        tags=["platform", "norm", "publishing"],
    ),
    "revision_studio": CreativeSkill(
        skill_id="revision_studio",
        name="深度改稿",
        description="基于用户反馈对已有内容进行结构、风格和表达层面的改写。",
        workflow_hint="先理解用户真正不满意的地方，再保留有效信息做完整新版本。",
        trigger="用户贴出草稿、要求去 AI 味、变自然、改标题、改第二段或继续修改。",
        version="1.0",
        package_kind="revision",
        agent_sequence=["intent_interpreter", "researcher", "editor", "critic_panel", "memory_curator"],
        workflow_steps=[
            "识别用户要求保留、删除、替换、增强的部分。",
            "判断反馈属于本次需求、项目规则还是长期偏好候选。",
            "删除模板句、空泛连接词和不自然表达。",
            "输出完整改后版本，并记录可复用的改稿经验。",
        ],
        tool_contract=["memory.search(feedback,style)", "memory.write(candidate_preference)", "critic.review"],
        input_contract=["原稿", "用户反馈", "保留项", "禁用项"],
        output_contract=["改后完整版本", "简短修改依据", "候选记忆"],
        constraints=["不随意扩写无关内容，不把一次反馈永久固化。"],
        evaluation=["反馈响应度", "自然度", "信息保留", "用户风格贴合度"],
        examples=["标题太像模板，第二段更自然一点，别改掉核心设定。"],
        failure_policy=["反馈矛盾时优先保留用户明确指定的信息。"],
        tags=["revision", "style", "feedback"],
    ),
    "variant_lab": CreativeSkill(
        skill_id="variant_lab",
        name="方案实验",
        description="为同一目标生成多种可比较方向，用于标题、开头、卖点和创意路线探索。",
        workflow_hint="先拆出评价维度，再生成少量差异明显的候选方案。",
        trigger="用户需要多个标题、多个开头、多种风格方向或想比较不同创作路线。",
        version="1.0",
        package_kind="exploration",
        agent_sequence=["intent_interpreter", "strategist", "draft_writer", "critic_panel"],
        workflow_steps=[
            "抽取核心承诺、情绪、冲突、信息差和平台限制。",
            "生成风格差异明显的候选，而不是同义改写。",
            "按吸引力、准确度、风险和用户偏好筛选。",
            "推荐可继续打磨的方向。",
        ],
        tool_contract=["memory.search(preference,platform)", "critic.rank"],
        input_contract=["核心内容", "候选数量", "比较维度", "禁用方向"],
        output_contract=["候选方案", "差异说明", "推荐方案"],
        constraints=["候选必须真实区分方向，不制造标题党。"],
        evaluation=["方向差异", "第一眼吸引力", "准确度", "不过度营销"],
        examples=["给我 8 个不同方向的标题，不要只是换词。"],
        failure_policy=["候选过于相似时重新按不同策略生成。"],
        tags=["variant", "hook", "exploration"],
    ),
}


SKILL_ALIASES = {
    "platform_adapt": "publish_ready",
    "平台适配": "publish_ready",
    "character_copy": "narrative_canon",
    "角色文案": "narrative_canon",
    "worldbuilding": "narrative_canon",
    "世界观企划": "narrative_canon",
    "polish": "revision_studio",
    "改稿精修": "revision_studio",
    "title_hooks": "variant_lab",
    "标题钩子": "variant_lab",
    "norm_check": "source_grounded",
    "规范检查": "source_grounded",
}


def get_skill(skill_id: str) -> CreativeSkill | None:
    key = skill_id.strip()
    return SKILLS.get(key) or SKILLS.get(SKILL_ALIASES.get(key, ""))


def write_skill_packages(root: Path | str) -> list[Path]:
    """把内置技能同步为 Agentic Harness 可审阅的文件包。"""

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for skill in SKILLS.values():
        skill_dir = root / skill.skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        spec = asdict(skill)
        spec["component"] = f"skills/{skill.skill_id}"
        spec["owner"] = "skill_orchestrator"
        spec["rollback_target"] = skill.version
        spec_path = skill_dir / "skill.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(spec_path)

        workflow_path = skill_dir / "workflow.md"
        workflow_path.write_text(_workflow_doc(skill), encoding="utf-8")
        written.append(workflow_path)

        eval_path = skill_dir / "eval_cases.json"
        eval_path.write_text(
            json.dumps(
                [
                    {
                        "case_id": f"{skill.skill_id}_contract",
                        "input": skill.examples[0] if skill.examples else skill.trigger,
                        "must_check": skill.evaluation,
                        "output_contract": skill.output_contract,
                    }
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        written.append(eval_path)

        examples_path = skill_dir / "examples.jsonl"
        examples_path.write_text(
            "\n".join(json.dumps({"input": item, "skill_id": skill.skill_id}, ensure_ascii=False) for item in skill.examples)
            + ("\n" if skill.examples else ""),
            encoding="utf-8",
        )
        written.append(examples_path)
    return written


def _workflow_doc(skill: CreativeSkill) -> str:
    lines = [
        f"# {skill.name} {skill.version}",
        "",
        skill.description,
        "",
        "## Trigger",
        "",
        skill.trigger,
        "",
        "## Workflow",
        "",
    ]
    lines.extend(f"{index}. {step}" for index, step in enumerate(skill.workflow_steps, 1))
    lines.extend(["", "## Tool Contract", ""])
    lines.extend(f"- {item}" for item in skill.tool_contract)
    lines.extend(["", "## Output Contract", ""])
    lines.extend(f"- {item}" for item in skill.output_contract)
    lines.extend(["", "## Failure Policy", ""])
    lines.extend(f"- {item}" for item in skill.failure_policy)
    lines.append("")
    return "\n".join(lines)
