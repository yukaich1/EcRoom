# 写视频脚本 1.0.0

生成适合 AI 视频、真人拍摄、口播或混合制作的视频生产脚本。

## Trigger

用户要求短视频、AI 视频、分镜、口播、产品视频、教程、广告或短剧脚本。

## Pipeline

1. intake
2. interpretation
3. production_mode
4. shot_planning
5. production
6. quality_gate
7. feedback_bridge
8. telemetry

## Tool Contract

- knowledge.search(project)
- shot_feasibility.review
- risk.review

## Output Contract

- creative_concept
- beat_sheet
- shot_table
- ai_prompts
- live_action_notes
- subtitles

## Quality Gates

- video_feasibility
- shot_clarity
- production_fit
- naturalness

## Failure Policy

- 未说明生产方式时默认 hybrid，并控制输出长度。
