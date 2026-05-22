# 资料驱动 1.0

围绕链接、素材、平台规范或项目资料进行检索、整理和生成。

## Trigger

用户提供链接、资料、参考作品、平台规则、禁用词或需要事实依据。

## Workflow

1. 识别链接、平台、实体名、作品名和规则线索。
2. 导入或召回资料库、记忆库和平台规范。
3. 区分确定事实、用户设定、参考风格和待验证信息。
4. 生成内容时只使用已确认或明确标注为参考的信息。

## Tool Contract

- url.import
- memory.search(hybrid)
- knowledge.search(hybrid)
- norm.review

## Output Contract

- 来源摘要
- 可用素材
- 生成内容
- 风险或不确定项

## Failure Policy

- 资料无法访问时保留 URL 线索，并降低事实置信度。
