# 写长文/方案 1.0.0

为文章、长帖、方案、说明或报告型内容建立结构并生成首稿。

## Trigger

用户要求文章、长帖、方案、报告、演讲稿或需要多段结构的内容。

## Pipeline

1. intake
2. interpretation
3. planning
4. production
5. quality_gate
6. feedback_bridge
7. telemetry

## Tool Contract

- knowledge.search(project)
- memory.search(preference,project)
- structure.review

## Output Contract

- outline
- longform_draft
- section_edit_handles

## Quality Gates

- structure_integrity
- argument_flow
- naturalness
- continuation_ready

## Failure Policy

- 目标过宽时先生成结构化提纲和首段样稿。
