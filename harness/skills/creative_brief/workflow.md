# 创作诊断 1.0

把模糊想法整理成可执行的创作 brief，再决定后续路线。

## Trigger

用户只有一个初步想法、方向很散，或希望先讨论清楚再写。

## Workflow

1. 拆分用户输入中的目标、受众、载体、约束、禁用项和参考材料。
2. 判断哪些信息足够生成，哪些信息需要用假设方式处理。
3. 形成一个可执行 brief，并给出 2-3 条创作路线。
4. 输出前标注本次只在当前会话生效的临时偏好。

## Tool Contract

- memory.search(preference,project)
- knowledge.search(project,style)

## Output Contract

- 创作 brief
- 可选方向
- 下一步建议

## Failure Policy

- 信息不足时先给假设 brief，不强迫用户填表。
