# 产品设计

EcRoom 是一个内容共创工作室。用户输入任意创作需求，系统组织多个 agent 召回资料和记忆、选择合适的技能流程、生成草稿、吸收反馈，并把有价值的偏好、规则和失败经验沉淀下来。

完整产品级蓝图见 [PRODUCT_BLUEPRINT.md](PRODUCT_BLUEPRINT.md)。本文件保留当前实现状态和日常开发入口。

## 目标

当前目标是做成一个能持续使用的创作房间：

- 能输入任意内容需求，不要求用户先选择固定模板；
- 能在生成页用对话式流程持续改稿；
- 能保存用户的接受、拒绝、改写和偏好反馈；
- 能把一次协作写成可追溯、可检索的分层记忆；
- 能根据失败信号生成带验证计划的 harness 进化提案；
- 能通过统一 provider 层接入 Mistral、OpenAI 和 DeepSeek；
- 能维护资料/规范库，并在创作前用向量检索召回相关内容；
- 能人工应用进化提案；
- 能运行一组内置评测任务。

产品不要求用户先选择固定模板。技能只是系统的工作倾向，真正的需求仍然由用户自然输入。

## 大模型接入

模型接入放在 `llm.py`。产品代码不直接依赖某一家 SDK，agent 只调用统一的 chat 接口。

当前支持：

| Provider | 默认模型 | Key |
| --- | --- | --- |
| Mistral | `mistral-small-latest` | `MISTRAL_API_KEY` |
| OpenAI | `gpt-4.1-mini` | `OPENAI_API_KEY` |
| DeepSeek | `deepseek-v4-pro` | `DEEPSEEK_API_KEY` |

运行时通过 `.env` 中的 `ECR_LLM_PROVIDER` 选择 provider，通过 `ECR_LLM_MODEL` 覆盖模型。没有配置 provider 时，系统使用本地 stub。

这层设计保证可换模型。后续再补 tool calls、JSON mode、重试、限流和更细的成本统计。

## 产品形态

当前 UI 分成几条清楚的路径：

- 灵感页：展示可复用的创作素材，用户可以喜欢、收藏、应用；
- 生成页：展示创作输入、流式生成、对话历史和持续反馈；
- 资产库：保存用户创作过或收藏过的素材，可筛选“创作”和“收藏”；
- 个人页：管理头像、昵称、简介和已发布内容；
- 设置页：配置模型 provider、模型名和 API key。

创作历史只出现在生成页。记忆不作为一堆“记忆块”暴露给普通用户，而是在后台影响下一次创作；需要调试时再通过开发入口查看。

## 核心对象

### Creative Intent

用户的输入会被整理成 Creative Intent：

```text
目标 + 受众 + 语境 + 载体 + 约束 + 风格 + 评价标准 + 用户偏好
```

这个对象让系统能处理混合任务。例如“角色登场文案，也要能发微博宣传”会同时触发角色一致性、社媒表达和传播吸引力几个约束。

### Session

一次创作会话包含：

- 原始需求；
- intent 解析结果；
- agent messages；
- draft versions；
- agent comments；
- human feedback；
- memory records；
- evolution manifest。

### Harness

`harness/` 目录保存系统的可编辑工作规则。未来 evolver 修改系统时，目标放在这些文件上，避免隐性 prompt 散落在代码里。

### Knowledge

资料库保存四类内容：

- project：项目背景、需求、素材；
- norm：平台规则、发布边界、合规说明；
- style：用户或品牌风格样本；
- canon：世界观、角色、剧情连续性。

创作开始前，系统会用用户需求检索资料库和记忆，把命中的内容放进当前 session 的上下文。默认检索后端是 Chroma，接口边界保留在 `memory/vector_index.py`，方便切换到 Tencent Cloud VectorDB。

## Agent 分工

当前产品会先解析 intent，再根据任务选择工作流。基础流程如下：

```text
Intent Interpreter
-> Research Agent
-> Strategist
-> Draft Writer
-> Editor
-> Critic Panel
-> Norm Steward
-> Human Feedback
-> Memory
-> Harness Evolution
```

几个角色的重点：

- **Intent Interpreter**：把用户输入拆成目标、受众、载体和约束；
- **Research Agent**：从记忆库和资料库召回偏好、平台规则、项目设定和风格样本；
- **Strategist**：决定表达策略和取舍；
- **Draft Writer**：给出第一版可讨论草稿；
- **Editor**：推动草稿进入下一轮；
- **Critic Panel**：从质量维度提出修改意见；
- **Norm Steward**：提醒平台、体裁和项目规则；
- **Memory Curator**：把反馈沉淀成记忆；
- **Harness Evolver**：基于失败证据提出规则或流程修改。

技能会影响 agent 调度和上下文。例如选择“角色文案”，系统会更重视角色内核、台词、人物小传和传播短版；选择“规范检查”，系统会优先召回平台规则和用户规定。输入框里的技能句子只是起步参考，不代表技能的全部能力。

## 记忆设计

记忆分成四层：

| 层级 | 内容 |
| --- | --- |
| L0 | 原始会话、草稿、评论、反馈和来源证据 |
| L1 | 小而具体的偏好、约束和规则 |
| L2 | 反复出现的创作场景，例如某账号风格或某游戏项目 |
| L3 | 稳定的用户创作画像 |

记忆的原则很简单：能少总结就少总结，能引用证据就引用证据。系统说“用户不喜欢某种标题”时，应该能回到当时的反馈。

实现上同时保留两种形态：

- 结构化文件：保存 L0-L3、证据 id、标签、置信度和状态，方便审计；
- 混合检索：用 BM25 风格关键词召回命中明确实体、平台和禁用词，用 Chroma 向量索引召回语义相似的用户偏好、平台规范、项目 canon 和风格样本，再合并排序。

这接近 Tencent Agent Memory 的工作方式：短期 canvas 保留当前会话，L0 保存原始证据，L1 抽取原子偏好和规则，L2 形成场景记忆，L3 才沉淀稳定画像。系统不会因为用户一句话就立刻永久化人格判断，重复出现或明确表达的偏好才会上升到 L3。

没有 Tencent VectorDB 账号时，Chroma 是当前最稳的产品选择。`VectorIndex` 已经把后端隔开，`ECROOM_VECTOR_BACKEND=tencent` 会进入 Tencent adapter；账号、SDK 和实例参数准备好后，再把 adapter 中的具体 SDK 调用补齐即可。

## 进化设计

进化提案采用 AHE 的思路。每条提案都要写清楚：

- 修改哪个组件；
- 来自哪些失败证据；
- 判断的根因；
- 打算怎么改；
- 预计改善什么；
- 可能带来什么副作用。

系统默认只生成提案。用户在 Web 页面点击“应用提案”后，提案会以 amendment 的形式追加到目标 `harness/` 文件，并留下应用记录。

每条提案还包含 `validation_plan` 和 `predicted_metric`。这让系统不是只会“改自己”，还要说明之后怎样判断这次修改有没有变好。

## 评测

内置评测集覆盖三类代表任务：

- 社媒与角色混合；
- 小红书生活分享；
- 世界观说明。

评测会真实跑一轮创作流程，然后用基础可用性指标打分。它不能替代人工判断，但可以在 harness 修改前后提供一条稳定参照线。

A/B dry-run 用同一组 eval case 对比“当前 harness”和“候选 harness 修改”。候选侧不会改文件，只把提案作为额外工作规则注入 session，跑完后输出平均分差异、case 级差异和判断。这样在没有线上实验平台的情况下，也能先把自进化做成可验证流程。

## 资料采集

规范和资料来源分两层：

- 手动录入：用户直接把平台规则、项目 canon、风格样本写进资料库；
- URL 导入：系统抓取公开网页标题、正文摘要和来源链接，保存成 knowledge record。

URL 导入不依赖搜索 API 或第三方账号。它解决的是“把我已经找到的资料变成系统可召回的资料”。如果后面接入搜索 API，Research Agent 可以把搜索结果先转成同样的 knowledge record，再走同一套向量检索。

## 借鉴来源

几个项目构成了这个产品的基本盘：

- STORM / Co-STORM：研究、提纲、知识组织和人机讨论；
- LangChain Social Media Agent：human-in-the-loop 的接受、拒绝和编辑；
- Azure Contoso Creative Writer：研究、写作、编辑、评估流水线；
- Collaborative Document Editing with AI Agents：agent profiles、tasks、comments；
- BookWorld / CreAgentive：角色、世界观和叙事连续性；
- TencentDB Agent Memory：短期 canvas、L0-L3 记忆和证据回溯；
- Agentic Harness Engineering：可观察、可验证、可回滚的 harness 进化。

## 接下来

短期优先级：

1. 用 Mistral 跑更多真实创作任务，整理失败样本；
2. 把评测指标从启发式升级为更细的人工/模型混合评审；
3. 增加版本 diff 和段落级 agent 评论；
4. 把模型调用指标做成更完整的成本和质量面板；
5. 为 Tencent Cloud VectorDB 增加正式 adapter；
6. 增加段落级版本 diff 和人工评审集。
