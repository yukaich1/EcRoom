# 写职业文本 1.0.0

生成邮件、公告、汇报、方案、申请、邀约等职业场景文本。

## Trigger

用户要求邮件、汇报、公告、方案、会议纪要、拒绝、道歉或商务沟通。

## Pipeline

1. intake
2. interpretation
3. relationship_modeling
4. planning
5. production
6. quality_gate
7. feedback_bridge
8. telemetry

## Tool Contract

- memory.search(preference,project)
- risk.review

## Output Contract

- ready_to_send_text
- optional_variants
- risk_notes

## Quality Gates

- objective_fit
- tone_fit
- risk_boundary
- action_clarity

## Failure Policy

- 关系不明时采用礼貌、中性、低风险语气。
