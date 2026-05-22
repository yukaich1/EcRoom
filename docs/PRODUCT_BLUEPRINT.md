# Evolving Creative Room 产品级设计方案

这份文档描述 Evolving Creative Room 从本地 MVP 走向产品级项目的完整设计。它不是市场介绍稿，面向后续开发、评测和产品迭代。

## 1. 产品定位

Evolving Creative Room 是一个人机共创型内容工作室。用户给出任意创作需求，系统把它整理成可执行的 Creative Intent，组织多个 agent 完成资料召回、创作策略、草稿、编辑、评审、规范提醒、记忆沉淀和 harness 进化。

它服务的内容范围包括：

- 社媒帖子：小红书、微博、公众号短文、X/LinkedIn 风格内容；
- 长内容：观点稿、产品文案、研究型文章、活动文案；
- 叙事内容：游戏角色、剧情任务、世界观、角色台词；
- 混合任务：角色宣发、品牌人格文案、活动剧情包装。

产品的长期价值来自三点：

- 用户参与创作过程，系统学习人的判断；
- 记忆有证据链，偏好、项目设定、平台规范分开治理；
- harness 能基于失败证据进化，进化过程可审阅、可评测、可回滚。

## 2. 参考项目与吸收方式

### STORM / Co-STORM

借鉴内容：

- 写作前的资料组织；
- 多视角提问；
- 人类可介入的知识探索；
- 动态 mind map 式上下文。

在本项目中的落地：

- `Creative Intent` 承担创作前的意图组织；
- `KnowledgeBase` 保存项目资料、规则、风格样本和 canon；
- `Context Builder` 在每次创作前召回资料和记忆。

### LangChain Social Media Agent

借鉴内容：

- human-in-the-loop；
- 接受、拒绝、编辑、审批；
- 社媒发布前工作流。

在本项目中的落地：

- Web 工作台支持 `accept / reject / edit / style feedback / save as rule`；
- 用户改稿会进入 L0 原始证据和 L1 原子记忆；
- 后续可把发布数据接入反馈链路。

### Azure Contoso Creative Writer

借鉴内容：

- research -> writing -> editing -> evaluation；
- 质量维度和评测意识；
- tracing 和 evaluation 作为工程表面。

在本项目中的落地：

- agent pipeline 包含 Strategist、Draft Writer、Editor、Critic；
- `EvaluationStore` 保存评测运行；
- `CallLogStore` 记录模型调用、耗时和 token。

### Collaborative Document Editing with AI Agents

借鉴内容：

- agent profiles；
- task/comment 协作方式；
- AI agent 在文档空间里留下评论。

在本项目中的落地：

- Web 右侧展示 agent 评论；
- 后续要把评论绑定到草稿段落；
- 评论本身成为记忆和进化证据。

### BookWorld / CreAgentive

借鉴内容：

- 角色、事件、世界观、时间线；
- 创意内容里的连续性检查；
- 叙事原型和知识图谱思路。

在本项目中的落地：

- `canon` 类型资料保存角色、世界观、剧情约束；
- `Canon Keeper` harness 文件约束叙事一致性；
- 混合任务中保留 canon 与平台传播的平衡。

### TencentDB Agent Memory

借鉴内容：

- 短期任务画布；
- L0-L3 分层记忆；
- 证据可回溯；
- hybrid recall 思路。

在本项目中的落地：

- `short_term_canvas.mmd` 保存当前任务结构；
- L0 保存原始 session；
- L1 保存具体偏好、规则、反馈；
- L2 保存场景记忆；
- L3 保存用户画像信号；
- Web 支持搜索、确认、停用记忆。

### Agentic Harness Engineering

借鉴内容：

- component observability；
- experience observability；
- decision observability；
- 修改要有证据、根因、预期收益、回归风险。

在本项目中的落地：

- `harness/` 保存可进化组件；
- evolution manifest 记录提案；
- Web 可人工应用提案；
- 应用后写入 `evolution_applied` 日志；
- 评测集提供进化前后的对比基础。

## 3. 产品模块

### 3.1 Project Space

项目空间用于隔离不同创作项目的资料、记忆和会话。默认项目用于快速试用。正式使用时，每个账号、游戏项目、品牌或内容系列都应建立独立项目。

当前实现：

- `ProjectStore`；
- Web 新建/切换项目；
- session、memory、knowledge 携带 `project_id`。

后续增强：

- 项目归档；
- 项目导入/导出；
- 项目级模型配置；
- 项目成员与权限。

### 3.2 Creative Workspace

创作工作台由三块构成：

- 左侧：项目、会话、模型测试、评测；
- 中间：需求、偏好、草稿、反馈和改稿；
- 右侧：agent 评论、进化提案、记忆、资料库、评测和调用状态。

当前实现保持单页本地应用，方便快速迭代。后续可替换为正式前端，但 API 和数据结构应保持稳定。

### 3.3 Agent Runtime

当前 agent 采用轻量编排：

```text
Intent Interpreter
-> Context Builder
-> Strategist
-> Draft Writer
-> Editor
-> Critic Panel
-> Norm Steward
-> Memory
-> Evolution
```

产品级目标：

- 工作流按 Creative Intent 动态选择 agent；
- 支持 interrupt/resume；
- 支持 agent 分支和版本比较；
- 关键节点支持人工确认；
- agent 输出全部进入 trace。

### 3.4 Memory System

记忆需要可用，也要可治理。

当前实现：

- L0-L3 文件存储；
- 记忆搜索；
- 确认/停用；
- 项目隔离；
- 原始 session 证据。

产品级目标：

- 记忆去重；
- 冲突检测；
- L1 -> L2 -> L3 晋升审批；
- hybrid recall；
- 记忆引用在 UI 中可 drill down 到原始证据；
- 记忆质量指标。

### 3.5 Knowledge and Norms

资料库承担项目知识和平台规范管理。

类型：

- `project`：项目背景和素材；
- `norm`：平台规则和发布边界；
- `style`：风格样本；
- `canon`：角色、世界观、剧情连续性。

产品级要求：

- 每条规范记录来源；
- 平台规则保留抓取日期；
- 规则建议标注置信度；
- 规则和用户口味分开存储；
- 低置信度规则要求人工确认。

### 3.6 Harness Evolution

进化系统不直接“自改代码”，它先产生提案。

提案包含：

- target component；
- failure evidence；
- root cause；
- targeted fix；
- expected improvement；
- regression risk。

当前实现：

- 根据反馈和评论生成 manifest；
- Web 页面人工应用提案；
- 只允许修改 `harness/`；
- 应用后留下日志。

产品级目标：

- 进化前自动跑评测；
- 应用后自动跑回归；
- 同一组件支持版本历史；
- 提案支持 reject / defer；
- 失败模式聚类。

### 3.7 Evaluation and Observability

产品级 agent 系统必须知道自己是否变好了。

当前实现：

- 3 个内置评测任务；
- 每次评测生成 `EvalRun`；
- Web 展示评测记录；
- LLM 调用日志记录 provider、model、耗时、tokens、失败。

产品级目标：

- 增加任务类型覆盖；
- 引入人工评分；
- 引入模型辅助评审；
- 追踪采纳率、人工编辑距离、Norm 误报率、Canon 错误；
- 评测结果绑定 harness 版本。

## 4. 数据结构

核心对象：

- `ProjectRecord`：项目空间；
- `CreativeIntent`：创作任务意图；
- `CreativeState`：一次 session；
- `DraftVersion`：草稿版本；
- `AgentComment`：agent 评论；
- `HumanFeedback`：用户反馈；
- `MemoryRecord`：L0-L3 记忆；
- `KnowledgeRecord`：项目资料和规范；
- `ChangeManifest`：进化提案；
- `EvalRun`：评测运行；
- `LLMCallRecord`：模型调用记录。

存储位置：

```text
.ecr_workspace/
  projects.jsonl
  refs/
  memory/
  knowledge/
  evolution/
  evolution_applied/
  evaluations/
  observability/
```

## 5. 产品化验收标准

本地产品级基线需要满足：

- 能用 Mistral/OpenAI/DeepSeek 任一 provider 运行；
- 能新建项目并隔离资料和记忆；
- 能完成至少三类代表创作任务；
- 用户反馈会写入可搜索记忆；
- 资料库内容会进入下一次创作上下文；
- 进化提案能人工应用到 `harness/`；
- 评测集能跑，并记录平均分；
- LLM 调用有日志；
- 不把 API key 写入仓库；
- 单测覆盖关键闭环。

当前代码已经达到这个本地产品级基线。下一阶段是体验和质量增强：段落级评论、版本 diff、streaming、成本统计、记忆冲突治理和更强评测。
