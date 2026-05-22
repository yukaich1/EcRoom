# 发布适配 1.0

把内容改成能面向具体平台或场景发布的版本。

## Trigger

用户希望内容发到微博、小红书、公众号、B站、活动页或其他发布场景。

## Workflow

1. 识别目标平台、受众、发布目的和必须保留的信息。
2. 召回平台表达习惯、风险边界和用户历史偏好。
3. 生成一个主版本和必要的平台变体，不把规则解释写进正文。
4. 输出平台差异、发布前风险和可继续修改点。

## Tool Contract

- memory.search(platform,preference)
- knowledge.search(norm,platform)
- norm.review

## Output Contract

- 发布版本
- 平台差异
- 风险提醒

## Failure Policy

- 平台不明确时生成通用版，并标注可适配方向。
