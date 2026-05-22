# 方案实验 1.0

为同一目标生成多种可比较方向，用于标题、开头、卖点和创意路线探索。

## Trigger

用户需要多个标题、多个开头、多种风格方向或想比较不同创作路线。

## Workflow

1. 抽取核心承诺、情绪、冲突、信息差和平台限制。
2. 生成风格差异明显的候选，而不是同义改写。
3. 按吸引力、准确度、风险和用户偏好筛选。
4. 推荐可继续打磨的方向。

## Tool Contract

- memory.search(preference,platform)
- critic.rank

## Output Contract

- 候选方案
- 差异说明
- 推荐方案

## Failure Policy

- 候选过于相似时重新按不同策略生成。
