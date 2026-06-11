# 根据资料写 1.0.0

基于用户提供的资料、链接或项目知识进行有边界的创作。

## Trigger

用户提供资料、链接、规范、引用或要求内容有事实依据。

## Pipeline

1. intake
2. interpretation
3. source_processing
4. planning
5. production
6. quality_gate
7. feedback_bridge
8. telemetry

## Tool Contract

- url.import
- knowledge.search(hybrid)
- memory.search(project)
- source_boundary.review

## Output Contract

- source_summary
- grounded_draft
- missing_info
- risk_notes

## Quality Gates

- evidence_use
- fact_boundary
- critical_fact_errors
- naturalness

## Failure Policy

- 资料不可访问时保留线索并降低事实置信度。
