# 深度改稿 1.0

基于用户反馈对已有内容进行结构、风格和表达层面的改写。

## Trigger

用户贴出草稿、要求去 AI 味、变自然、改标题、改第二段或继续修改。

## Workflow

1. 识别用户要求保留、删除、替换、增强的部分。
2. 判断反馈属于本次需求、项目规则还是长期偏好候选。
3. 删除模板句、空泛连接词和不自然表达。
4. 输出完整改后版本，并记录可复用的改稿经验。

## Tool Contract

- memory.search(feedback,style)
- memory.write(candidate_preference)
- critic.review

## Output Contract

- 改后完整版本
- 简短修改依据
- 候选记忆

## Failure Policy

- 反馈矛盾时优先保留用户明确指定的信息。
