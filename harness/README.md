# Harness 工作区

这个目录是 Evolving Creative Room 的可编辑 harness 基底。

它遵循 Agentic Harness Engineering 的核心原则：模型外部的工作系统应该拆成明确、可审阅、可 diff、可回滚的文件，避免藏在黑盒 prompt 或代码分支里。

未来 `HarnessEvolver` 可以基于失败案例和用户反馈，对这里的文件提出修改建议。但生产环境中的修改应该经过人工确认和评测验证。

## 可编辑组件类型

```text
system_prompt.md                 全局行为契约
agents/*.md                      agent 角色规则
rubrics/*.md                     质量评价标准
memory/*.md                      记忆抽取和检索策略
workflows/*.md                   协作流程
norms/*.md                       平台、体裁、项目规范策略
```

## 非目标

- 不在这里存储模型凭证或 API key。
- 避免把某个用户的私人偏好硬编码进全局 harness。
- 不让平台规则覆盖用户偏好，也不让用户偏好伪装成平台规则。
- 不允许 evolver 静默修改原始 trace、评测记录或证据文件。
