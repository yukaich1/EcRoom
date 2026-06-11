from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CapabilityPackage:
    capability_id: str
    user_visible_label: str
    short_description: str
    workflow_hint: str
    trigger: str
    version: str = "1.0.0"
    package_kind: str = "workflow"
    agent_sequence: list[str] = field(default_factory=list)
    pipeline: list[str] = field(default_factory=list)
    tool_contract: list[str] = field(default_factory=list)
    input_contract: list[str] = field(default_factory=list)
    output_contract: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    quality_gates: list[str] = field(default_factory=list)
    entry_examples: list[str] = field(default_factory=list)
    failure_policy: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @property
    def skill_id(self) -> str:
        return self.capability_id

    @property
    def name(self) -> str:
        return self.user_visible_label

    @property
    def description(self) -> str:
        return self.short_description

    @property
    def workflow_steps(self) -> list[str]:
        return self.pipeline

    @property
    def evaluation(self) -> list[str]:
        return self.quality_gates

    @property
    def examples(self) -> list[str]:
        return self.entry_examples


CAPABILITIES: dict[str, CapabilityPackage] = {
    "idea_to_draft": CapabilityPackage(
        capability_id="idea_to_draft",
        user_visible_label="把想法写成稿",
        short_description="把短想法、观点或灵感整理成自然、可继续修改的首稿。",
        workflow_hint="先判断表达目的和读者，再选择一个稳妥角度生成自然首稿。",
        trigger="用户有碎片想法、观点、朋友圈/帖子/短文需求，尚未形成完整文本。",
        package_kind="initial_creation",
        agent_sequence=["intent_interpreter", "strategist", "draft_writer", "critic_panel"],
        pipeline=["intake", "interpretation", "planning", "production", "quality_gate", "feedback_bridge", "telemetry"],
        tool_contract=["memory.search(preference,project)", "naturalness.review"],
        input_contract=["raw_request", "optional audience", "optional tone", "must_keep", "must_avoid"],
        output_contract=["primary_draft", "optional_openings", "edit_handles"],
        constraints=["不默认加平台标签、emoji 或标题党结构。", "输入很短时输出短而完整，不虚胖扩写。"],
        quality_gates=["intent_fit", "naturalness", "scope_safety", "continuation_ready"],
        entry_examples=["我有个观点，帮我写成一段自然的帖子。"],
        failure_policy=["输入不足时生成一个小稿和两个可继续方向。"],
        tags=["idea", "shortform", "draft"],
    ),
    "longform_builder": CapabilityPackage(
        capability_id="longform_builder",
        user_visible_label="写长文/方案",
        short_description="为文章、长帖、方案、说明或报告型内容建立结构并生成首稿。",
        workflow_hint="先建立论点、段落功能和推进顺序，再写可按段继续修改的长内容。",
        trigger="用户要求文章、长帖、方案、报告、演讲稿或需要多段结构的内容。",
        package_kind="initial_creation",
        agent_sequence=["intent_interpreter", "researcher", "strategist", "draft_writer", "critic_panel"],
        pipeline=["intake", "interpretation", "planning", "production", "quality_gate", "feedback_bridge", "telemetry"],
        tool_contract=["knowledge.search(project)", "memory.search(preference,project)", "structure.review"],
        input_contract=["raw_request", "topic", "audience", "length", "materials", "constraints"],
        output_contract=["outline", "longform_draft", "section_edit_handles"],
        constraints=["不套固定总分总模板。", "资料不足时标明缺口，不编造证据。"],
        quality_gates=["structure_integrity", "argument_flow", "naturalness", "continuation_ready"],
        entry_examples=["帮我写一篇关于这个产品思路的长文。"],
        failure_policy=["目标过宽时先生成结构化提纲和首段样稿。"],
        tags=["longform", "article", "plan"],
    ),
    "knowledge_grounded": CapabilityPackage(
        capability_id="knowledge_grounded",
        user_visible_label="根据资料写",
        short_description="基于用户提供的资料、链接或项目知识进行有边界的创作。",
        workflow_hint="先处理来源和事实边界，再把可靠信息转化为内容。",
        trigger="用户提供资料、链接、规范、引用或要求内容有事实依据。",
        package_kind="research",
        agent_sequence=["intent_interpreter", "researcher", "norm_steward", "strategist", "draft_writer", "critic_panel"],
        pipeline=["intake", "interpretation", "source_processing", "planning", "production", "quality_gate", "feedback_bridge", "telemetry"],
        tool_contract=["url.import", "knowledge.search(hybrid)", "memory.search(project)", "source_boundary.review"],
        input_contract=["raw_request", "sources", "target_output", "source_boundary"],
        output_contract=["source_summary", "grounded_draft", "missing_info", "risk_notes"],
        constraints=["区分事实、推断和缺失信息。", "不把资料外内容写成确定事实。"],
        quality_gates=["evidence_use", "fact_boundary", "critical_fact_errors", "naturalness"],
        entry_examples=["根据这几段资料写一版说明文。"],
        failure_policy=["资料不可访问时保留线索并降低事实置信度。"],
        tags=["source", "research", "grounded"],
    ),
    "professional_writer": CapabilityPackage(
        capability_id="professional_writer",
        user_visible_label="写职业文本",
        short_description="生成邮件、公告、汇报、方案、申请、邀约等职业场景文本。",
        workflow_hint="先判断关系、目的、风险和语气，再输出可直接使用的版本。",
        trigger="用户要求邮件、汇报、公告、方案、会议纪要、拒绝、道歉或商务沟通。",
        package_kind="professional",
        agent_sequence=["intent_interpreter", "strategist", "draft_writer", "norm_steward", "critic_panel"],
        pipeline=["intake", "interpretation", "relationship_modeling", "planning", "production", "quality_gate", "feedback_bridge", "telemetry"],
        tool_contract=["memory.search(preference,project)", "risk.review"],
        input_contract=["raw_request", "recipient", "objective", "tone", "required_points"],
        output_contract=["ready_to_send_text", "optional_variants", "risk_notes"],
        constraints=["不夸张承诺。", "不输出不合关系的冒犯或过度亲密语气。"],
        quality_gates=["objective_fit", "tone_fit", "risk_boundary", "action_clarity"],
        entry_examples=["帮我写一封委婉但明确的拒绝邮件。"],
        failure_policy=["关系不明时采用礼貌、中性、低风险语气。"],
        tags=["email", "business", "work"],
    ),
    "story_world": CapabilityPackage(
        capability_id="story_world",
        user_visible_label="写故事/设定",
        short_description="处理角色、世界观、剧情、场景和台词等通用叙事创作。",
        workflow_hint="先区分 canon、临时设定和可发挥空间，再生成可扩展文本。",
        trigger="用户要求角色设定、世界观、剧情、故事片段、台词、短剧或虚构项目资料。",
        package_kind="narrative",
        agent_sequence=["intent_interpreter", "researcher", "strategist", "draft_writer", "critic_panel", "norm_steward"],
        pipeline=["intake", "interpretation", "canon_check", "planning", "production", "quality_gate", "feedback_bridge", "telemetry"],
        tool_contract=["knowledge.search(project,canon)", "memory.search(project,style)", "continuity.review"],
        input_contract=["raw_request", "characters", "world_rules", "narrative_goal", "must_keep"],
        output_contract=["story_or_setting_draft", "canon_notes", "continuation_hooks", "edit_handles"],
        constraints=["参考作品只抽象节奏和风格，不复刻桥段。", "canon 只在明确作用域内生效。"],
        quality_gates=["canon_consistency", "character_motivation", "conflict_clarity", "naturalness"],
        entry_examples=["写一个城市设定和三个可继续扩展的剧情钩子。"],
        failure_policy=["设定冲突时先保守生成，并记录 continuity_risk。"],
        tags=["story", "worldbuilding", "character"],
    ),
    "video_script": CapabilityPackage(
        capability_id="video_script",
        user_visible_label="写视频脚本",
        short_description="生成适合 AI 视频、真人拍摄、口播或混合制作的视频生产脚本。",
        workflow_hint="先判断生产方式，再输出分镜、口播、字幕、AI prompt 或拍摄备注。",
        trigger="用户要求短视频、AI 视频、分镜、口播、产品视频、教程、广告或短剧脚本。",
        package_kind="video",
        agent_sequence=["intent_interpreter", "researcher", "strategist", "draft_writer", "critic_panel", "norm_steward"],
        pipeline=["intake", "interpretation", "production_mode", "shot_planning", "production", "quality_gate", "feedback_bridge", "telemetry"],
        tool_contract=["knowledge.search(project)", "shot_feasibility.review", "risk.review"],
        input_contract=["raw_request", "duration", "aspect_ratio", "production_mode", "materials", "constraints"],
        output_contract=["creative_concept", "beat_sheet", "shot_table", "ai_prompts", "live_action_notes", "subtitles"],
        constraints=["30 秒视频不能塞入过多复杂镜头。", "AI prompt 不同时要求冲突动作。"],
        quality_gates=["video_feasibility", "shot_clarity", "production_fit", "naturalness"],
        entry_examples=["帮我做一个 30 秒 AI 视频脚本，能直接给视频工具使用。"],
        failure_policy=["未说明生产方式时默认 hybrid，并控制输出长度。"],
        tags=["video", "script", "shot"],
    ),
}


CAPABILITY_ALIASES = {
    "creative_brief": "idea_to_draft",
    "source_grounded": "knowledge_grounded",
    "narrative_canon": "story_world",
    "publish_ready": "professional_writer",
    "revision_studio": "idea_to_draft",
    "variant_lab": "idea_to_draft",
    "创作诊断": "idea_to_draft",
    "资料驱动": "knowledge_grounded",
    "叙事设定": "story_world",
    "发布适配": "professional_writer",
    "深度改稿": "idea_to_draft",
    "方案实验": "idea_to_draft",
    "想法成稿": "idea_to_draft",
    "长文构建": "longform_builder",
    "资料创作": "knowledge_grounded",
    "职业写作": "professional_writer",
    "叙事创作": "story_world",
    "视频脚本": "video_script",
}


def get_capability(capability_id: str) -> CapabilityPackage | None:
    key = capability_id.strip()
    return CAPABILITIES.get(key) or CAPABILITIES.get(CAPABILITY_ALIASES.get(key, ""))


def load_capability_packages(root: Path | str) -> dict[str, CapabilityPackage]:
    root = Path(root)
    loaded: dict[str, CapabilityPackage] = {}
    field_names = {item.name for item in fields(CapabilityPackage)}
    if root.exists():
        for spec_path in sorted(root.glob("*/capability.json")):
            try:
                data = json.loads(spec_path.read_text(encoding="utf-8"))
                data.update(_workflow_overrides(spec_path.with_name("workflow.md")))
                values = {key: value for key, value in data.items() if key in field_names}
                package = CapabilityPackage(**values)
            except Exception:
                continue
            loaded[package.capability_id] = package
    return loaded or dict(CAPABILITIES)


def seed_missing_capability_packages(root: Path | str) -> list[Path]:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for package in CAPABILITIES.values():
        package_dir = root / package.capability_id
        package_dir.mkdir(parents=True, exist_ok=True)
        spec = asdict(package)
        spec["schema_version"] = "capability_spec.v1"
        spec["component"] = f"capabilities/{package.capability_id}"
        spec["owner"] = "capability_registry"
        spec["rollback_target"] = package.version
        files = {
            package_dir / "capability.json": json.dumps(spec, ensure_ascii=False, indent=2),
            package_dir / "workflow.md": _workflow_doc(package),
            package_dir / "schemas.json": json.dumps(_schemas(package), ensure_ascii=False, indent=2),
            package_dir / "eval_cases.json": json.dumps(_eval_cases(package), ensure_ascii=False, indent=2),
            package_dir / "examples.jsonl": "\n".join(
                json.dumps({"input": item, "capability_id": package.capability_id}, ensure_ascii=False) for item in package.entry_examples
            )
            + ("\n" if package.entry_examples else ""),
        }
        for path, content in files.items():
            if path.exists():
                continue
            path.write_text(content, encoding="utf-8")
            written.append(path)
    return written


def capabilities_view(packages: dict[str, CapabilityPackage]) -> list[dict[str, object]]:
    return [
        {
            "capability_id": package.capability_id,
            "label": package.user_visible_label,
            "description": package.short_description,
            "examples": package.entry_examples,
            "tags": package.tags,
        }
        for package in packages.values()
    ]


def _workflow_doc(package: CapabilityPackage) -> str:
    lines = [
        f"# {package.user_visible_label} {package.version}",
        "",
        package.short_description,
        "",
        "## Trigger",
        "",
        package.trigger,
        "",
        "## Pipeline",
        "",
    ]
    lines.extend(f"{index}. {step}" for index, step in enumerate(package.pipeline, 1))
    lines.extend(["", "## Tool Contract", ""])
    lines.extend(f"- {item}" for item in package.tool_contract)
    lines.extend(["", "## Output Contract", ""])
    lines.extend(f"- {item}" for item in package.output_contract)
    lines.extend(["", "## Quality Gates", ""])
    lines.extend(f"- {item}" for item in package.quality_gates)
    lines.extend(["", "## Failure Policy", ""])
    lines.extend(f"- {item}" for item in package.failure_policy)
    lines.append("")
    return "\n".join(lines)


def _schemas(package: CapabilityPackage) -> dict[str, object]:
    return {
        "input_contract": package.input_contract,
        "output_contract": package.output_contract,
        "quality_gates": package.quality_gates,
        "feedback_bridge": {"edit_handles_required": True},
    }


def _eval_cases(package: CapabilityPackage) -> list[dict[str, object]]:
    first = package.entry_examples[0] if package.entry_examples else package.trigger
    cases = [
        (
            "happy_path",
            first,
            ["contract_pass", "naturalness", "continuation_ready"],
            ["visible_internal_trace", "template_style"],
        ),
        (
            "sparse_input",
            "我只有一个很粗略的想法，帮我先写一个可继续修改的版本。",
            ["fallback_usable", "intent_fit", "naturalness"],
            ["over_expansion", "forced_form", "visible_internal_trace"],
        ),
        (
            "constraint_heavy",
            "请保留核心信息，但不要夸张、不要硬广、不要替我新增没有依据的承诺。",
            ["constraint_following", "negation_preserved", "scope_safety"],
            ["negation_loss", "unsupported_claim", "scope_overreach"],
        ),
        (
            "feedback_bridge",
            "先给首版，后续我可能会要求改第二段、缩短、换语气或保留某个设定。",
            ["edit_handles_present", "continuation_ready", "targetable_output"],
            ["dead_end_output", "missing_edit_handles"],
        ),
        (
            "quality_failure",
            "请生成一版，但要能检查是否太模板、太空泛或不符合任务边界。",
            ["quality_gate_triggered", "failure_signal_recorded"],
            ["quality_issue_ignored", "process_notes_in_body"],
        ),
        (
            "scope_safety",
            "这次先写得冷一点，但不要记成我以后都喜欢这种风格。",
            ["temporary_context_detected", "scope_safety"],
            ["global_memory_created", "scope_overreach"],
        ),
        (
            "chinese_naturalness",
            "请用中文自然表达，像真人创作者写的，不要像翻译腔或模板说明。",
            ["naturalness", "chinese_readability"],
            ["translationese", "generic_language", "template_style"],
        ),
    ]
    return [
        {
            "case_id": f"{package.capability_id}_{suffix}",
            "case_type": suffix,
            "input": text,
            "must_check": list(dict.fromkeys([*checks, *package.quality_gates])),
            "output_contract": package.output_contract,
            "forbidden_failures": forbidden,
        }
        for suffix, text, checks, forbidden in cases
    ]


def _workflow_overrides(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    sections = _markdown_sections(path.read_text(encoding="utf-8"))
    mapping = {
        "pipeline": "pipeline",
        "tool contract": "tool_contract",
        "output contract": "output_contract",
        "quality gates": "quality_gates",
        "failure policy": "failure_policy",
    }
    overrides: dict[str, list[str]] = {}
    for section_name, field_name in mapping.items():
        values = sections.get(section_name, [])
        if values:
            overrides[field_name] = values
    return overrides


def _markdown_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections.setdefault(current, [])
            continue
        if not current:
            continue
        if line[0].isdigit() and ". " in line[:4]:
            sections.setdefault(current, []).append(line.split(". ", 1)[1].strip())
        elif line.startswith("- "):
            sections.setdefault(current, []).append(line[2:].strip())
    return sections
