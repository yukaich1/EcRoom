# EcRoom SSD：面向可感知自进化的产品与系统设计

## 1. 设计目标

EcRoom 不应只是一个“能写稿的多智能体系统”。它的核心目标是：在不固化用户创作自由的前提下，让系统能从长期协作中学习上下文、改进专家技能，并用可验证的方式证明改进有效。

产品逻辑是：

```text
用户提出创作需求
  -> 多 Agent 协作生成和改稿
  -> 用户继续反馈或确认完成
  -> 系统只在完成后提出少量可保存偏好
  -> 用户确认后沉淀为记忆
  -> 后续创作按场景召回
  -> 重复失败进入 Agentic Harness 改进闭环
```

这条链路里，创作自由始终排在第一位。系统可以理解用户、利用上下文、提出候选记忆，但不能在用户创作过程中持续打断，也不能把一次性的风格选择固化成用户画像。

本设计围绕三个问题展开：

- 系统到底要优化什么；
- 用户如何感知系统在变好；
- Agentic Harness 和分层记忆如何进入真实工程闭环。

## 2. 北极星指标

### NSM：可复用创作成功率

定义：用户在一次会话中得到可继续使用或保存为资产的内容比例。

计算：

```text
可复用创作成功率 =
  有效完成会话数 / 总创作会话数
```

有效完成会话满足任一条件：

- 用户点击收藏或保存为资产；
- 用户接受最终稿；
- 用户连续反馈后没有出现同类失败信号；
- 用户将某个版本用于后续创作。

这个指标比“生成次数”更重要。EcRoom 的价值不是多生成，而是生成的内容能进入用户的创作流程。

## 3. 分层指标

### 3.1 任务理解指标

目标：系统能准确识别用户这次真正想做什么，而不是把用户固化成某种风格。

指标：

- Intent 完整率：是否抽取出目标、载体、约束、参考、禁用项；
- 临时上下文识别率：是否把“这一次”的风格和参考限制在当前会话；
- 澄清需求率：信息不足时是否给出合理假设，而不是盲目生成。

目标值：

```text
Intent 完整率 >= 85%
临时上下文误固化率 <= 5%
```

### 3.2 记忆召回指标

目标：该召回的记忆能召回，不该召回的记忆不干扰创作。

指标：

- 相关记忆命中率：与当前任务相关的偏好、项目规则、平台规范是否进入上下文；
- 噪声召回率：无关历史是否被召回；
- 证据可追溯率：每条记忆是否能回到原始对话或资料；
- 撤销生效率：删除对话并撤销记忆后，相关记忆是否不再参与召回。

目标值：

```text
相关记忆命中率 >= 80%
噪声召回率 <= 15%
证据可追溯率 = 100%
撤销生效率 = 100%
```

### 3.3 专家技能指标

目标：技能不是标签，而是可复用、可评测、可升级的能力包。

指标：

- 技能选择有效率：用户选择技能后，工作流、工具、输出结构确实发生变化；
- 技能输出达标率：输出是否满足该技能的 output contract；
- 技能失败归因率：失败反馈是否能归因到技能步骤、工具或规范；
- 技能升级通过率：新版本技能通过 A/B dry-run 后再启用。

目标值：

```text
技能选择有效率 >= 90%
技能输出达标率 >= 80%
技能失败归因率 >= 70%
```

### 3.4 自进化指标

目标：系统不是“自动改 prompt”，而是提出可审阅、可验证、可回滚的 harness 改进。

指标：

- 改进提案证据覆盖率：每条提案是否引用原始失败证据；
- 预测指标填写率：每条提案是否声明预计改善什么；
- A/B 验证完成率：提案是否经过 dry-run 或后续任务验证；
- 回滚可用率：每次启用是否能回到旧版本；
- 净提升率：启用后的技能版本是否提升对应评测分。

目标值：

```text
提案证据覆盖率 = 100%
预测指标填写率 = 100%
A/B 验证完成率 >= 80%
净提升率 > 0
```

### 3.5 用户可感知指标

目标：用户能看见系统为什么这么做、学到了什么、下次会怎么变。

指标：

- 完成后学习展示率：用户点击“完成”后，是否展示少量可判断的候选偏好；
- 用户确认率：用户是否确认某条偏好、规则或技能改进；
- 误学习撤销率：用户撤销不正确记忆或技能改进的比例；
- 信任反馈：用户是否觉得系统“理解我但不限制我”。

目标值：

```text
完成后学习展示率 >= 90%
误学习可撤销率 = 100%
```

### 3.6 偏好沉淀指标

目标：Memory Curator 能从对话中提取高质量候选，但不把临时创作要求误存为长期偏好。

指标：

- 候选准确率：展示出的候选中，用户认为值得保存或合理的比例；
- 临时要求误固化率：把“这次、本轮、先这样”识别为长期偏好的比例；
- 否定保真率：包含“不要、避免、禁止、不能”的规则是否完整保留否定；
- 作用域准确率：平台、项目、角色、全局偏好是否被分到正确范围；
- 候选压缩率：一次完成后展示的候选数量是否足够少，避免造成选择压力。

目标值：

```text
候选准确率 >= 75%
临时要求误固化率 <= 5%
否定保真率 = 100%
单次候选数量 <= 5
```

## 4. 系统设计

### 4.1 Context Scope：避免固化用户

EcRoom 的上下文不按“用户是谁”来固化，而按作用域管理。系统要先判断一条信息应该影响哪里，再决定是否保存。

| 作用域 | 含义 | 生命周期 | 默认行为 | 例子 |
| --- | --- | --- | --- | --- |
| Session | 本次创作意图、临时风格、当前参考 | 当前会话 | 会话结束后默认不保存 | 这次写冷一点、这次参考某作品气质 |
| Project | 项目 canon、账号风格、平台规则、系列设定 | 项目内 | 只影响当前项目 | 某角色不能说长句、某账号不做硬广 |
| Global | 用户明确确认的长期工作偏好 | 跨项目 | 默认关闭自动升级，需要确认或高置信度 | 默认不要模板腔、先给可改版本 |
| Rejected | 用户否定或撤销的信息 | 永久排除，除非恢复 | 不参与召回和自进化 | 用户说“不要再记这个” |

原则：

- 用户一次说“这次写冷一点”，不能变成“用户永远喜欢冷感”；
- 用户明确说“以后都这样”或多次确认后，才进入 Global Context；
- 删除对话并撤销记忆后，相关证据不再参与召回和自进化。

### 4.2 Memory Action Model

偏好沉淀不能打断创作。系统可以在后台观察用户需求、反馈和最终稿变化，但这些候选项在会话进行中只留在隔离缓冲区，不进入长期记忆，也不展示给用户。

当用户认为某个版本已经可用，点击创作版本右下角的“完成”后，系统才展示本次会话沉淀出的候选偏好。用户可以撤销完成，撤销后候选区收起，会话回到继续创作状态。

候选记忆的默认状态是 `candidate`。产品层只保留两个动作：

| 用户动作 | 目标状态 | 生效范围 | 语义 |
| --- | --- | --- | --- |
| 设为偏好 | global_active | 跨会话 | 写入可管理的长期偏好，后续创作可被召回 |
| 取消 | ignored | 不保存 | 不进入偏好，不作为负反馈，也不打断创作 |

当前会话里的临时要求天然由对话上下文生效，不需要额外的“本次保留”按钮。这样用户不必在每次生成后做记忆治理，只在确认作品完成时处理真正值得长期保存的内容。

候选项质量规则：

- 保留完整语义，尤其是“不要、禁止、避免、不能”等否定和限制词；
- “这次、本次、当前、先、暂时”这类临时指令默认不推荐为长期偏好，除非用户同时表达“以后、长期、默认、记住”；
- 不把原句截成孤立名词，例如“不要夸张承诺”不能变成“夸张承诺”；
- 合并重复、包含关系和低价值碎片，优先展示用户能判断的完整规则；
- 平台、角色、世界观等线索保留类型字段，但前端统一让用户选择是否设为长期偏好。

### 4.3 Multi-Agent Collaboration

EcRoom 的多智能体不是把写作任务机械拆碎，而是围绕“创作、约束、反馈、记忆”形成协作关系。每个 agent 只承担一类判断，避免一个大 prompt 同时负责理解、检索、写作、规范和记忆。

| Agent | 职责 | 产物 | 不负责 |
| --- | --- | --- | --- |
| Orchestrator | 读取用户输入、技能选择和会话状态，安排本轮工作流 | agent 顺序、共享上下文 | 不直接写稿 |
| Intent Agent | 理解目标、载体、平台、素材、约束和临时要求 | CreativeIntent | 不沉淀长期记忆 |
| Research Agent | 召回资料、平台规则、项目 canon、历史偏好 | facts / sources | 不判断偏好是否长期有效 |
| Strategist | 把需求、资料和规则整理为创作策略 | brief / direction | 不输出最终稿 |
| Writer / Editor | 生成初稿、改稿、回应用户反馈 | draft versions | 不决定长期记忆 |
| Critic / Norm Agent | 检查清晰度、自然度、平台风险、canon 冲突 | comments / warnings | 不替用户决定是否完成 |
| Memory Curator | 观察对话和反馈，提炼候选偏好与规则 | candidate_memory | 不直接写入长期记忆 |

共享状态只保存本轮需要的信息：需求、已召回资料、项目规则、用户反馈、草稿版本、评审意见和候选记忆。Memory Curator 可以读取这些状态，但它不能改变草稿，也不能在用户点击“完成”前把候选推到长期记忆里。

#### 4.3.1 Shared State 设计

多 Agent 不通过自然语言互相“猜”，而是围绕一个共享的 `CreativeState` 工作。每个 agent 只能读写自己负责的字段，避免状态污染。

```text
CreativeState
  session_id
  project_id
  intent: CreativeIntent
  facts: list[str]
  strategy: list[str]
  drafts: list[DraftVersion]
  comments: list[AgentComment]
  human_feedback: list[HumanFeedback]
  warnings: list[str]
  messages: list[AgentMessage]
  memory_candidates: list[LearningCandidate]  // 逻辑字段，可由 LearningStore 持久化
```

字段职责：

| 字段 | 写入者 | 读取者 | 说明 |
| --- | --- | --- | --- |
| `intent` | Intent Agent、Skill Context | 全部 agent | 本轮目标、载体、约束、风格、平台、技能上下文 |
| `facts` | Research Agent、Norm Agent、Skill Context | Strategist、Writer、Critic、Memory Curator | 召回资料、平台规范、项目 canon、技能 contract |
| `strategy` | Strategist | Writer、Editor、Critic | 本轮创作路线，不直接展示为最终稿 |
| `drafts` | Writer、Editor | Critic、Norm Agent、Memory Curator、前端 | 每次生成或改稿的版本链 |
| `comments` | Critic、Norm Agent | Editor、前端、Harness Evolver | 质量和规范检查意见，默认折叠展示 |
| `human_feedback` | Human / Web API | Editor、Memory Curator、Harness Evolver | 用户对具体版本的反馈 |
| `warnings` | Norm Agent、Research Agent | Writer、Editor、前端 | 风险和边界提醒 |
| `messages` | 全部 agent | Trace、Observability、Harness Evolver | 工作流轨迹，不等于用户可见正文 |
| `memory_candidates` | Memory Curator / LearningStore | 前端、MemoryStore | 完成后候选偏好，不直接参与长期召回 |

写入规则：

- Intent Agent 只补全 `intent`，不写长期记忆；
- Research Agent 只写 `facts`，不直接改草稿；
- Writer / Editor 只写 `drafts`，不写偏好候选；
- Critic / Norm Agent 只写 `comments` 和 `warnings`，不替用户否定作品；
- Memory Curator 只写候选，不改 `drafts`，不直接写 L3；
- Harness Evolver 只读轨迹和失败证据，提出可审阅改进，不在用户会话中即时改组件。

#### 4.3.2 Agent 执行协议

每个 agent 的执行需要遵守统一协议：

```text
input:
  state snapshot
  skill package context
  retrieved memory / knowledge
  previous agent outputs

process:
  validate required inputs
  run role-specific steps
  write only owned fields
  emit AgentMessage trace
  emit metric events

output:
  AgentResult {
    role
    summary
    metadata
    changed_fields
    failure_signal?
  }
```

失败处理：

- 缺少必要输入：写入 `comments` 或 `warnings`，继续给出保守版本；
- 检索为空：降低事实置信度，不编造来源；
- 输出不满足 skill contract：由 Critic 标注失败点，并进入 Harness evidence；
- 用户反馈与已有规则冲突：优先使用本轮用户反馈，旧记忆只作为参考；
- agent 失败不能中断整个创作，除非无法生成任何可读内容。

#### 4.3.3 Orchestrator

职责：把用户输入、当前页面、技能选择和历史状态转成一个本轮工作流。

输入：

- 用户输入文本；
- 当前 session 状态；
- 选中的 skill_id；
- 是否为新会话、继续反馈、资产做同款或完成确认；
- 当前项目和资产上下文。

内部步骤：

1. 判断本轮类型：新创作、继续反馈、资产复用、完成确认、标题修改；
2. 创建或加载 `CreativeState`；
3. 注入选中的 Skill Package；
4. 根据技能的 `agent_sequence`、用户输入信号和已有事实选择 agent；
5. 控制顺序执行，并在每个阶段写入 trace；
6. 在生成结束后调用 Memory Curator 观察，但不展示候选；
7. 用户点击完成后，允许前端读取候选。

输出：

- 本轮工作流阶段；
- 更新后的 `CreativeState`；
- 可展示的草稿版本；
- 工作流 trace；
- 候选记忆状态。

#### 4.3.4 Intent Agent

职责：把用户自然语言拆成系统可执行的意图，不做长期记忆判断。

输入：

- 原始需求；
- 用户在输入框中的直接补充；
- 本轮技能参考文字；
- 当前项目和资产上下文。

内部步骤：

1. 抽取目标：发帖、改稿、角色文案、世界观、活动宣传、标题方案等；
2. 抽取载体：微博、小红书、公众号、游戏策划文档、角色小传、短文案等；
3. 抽取对象：角色、平台、活动、产品、世界观设定、参考作品；
4. 抽取约束：必须保留、禁用表达、长度、结构、风格边界；
5. 标记临时词：这次、本轮、先、暂时、这一版；
6. 标记长期词：以后、默认、记住、一直、我的风格；
7. 把技能需要的字段补进 `intent.project_context`。

输出字段：

- `intent.goal`
- `intent.medium`
- `intent.audience`
- `intent.constraints`
- `intent.style`
- `intent.evaluation_criteria`
- `intent.project_context.signals`

失败处理：

- 信息不足时不弹窗打断，先生成“假设 brief”；
- 同时存在多个目标时保留主目标，把次目标放进可选方向；
- 临时词和长期词冲突时，交给 Memory Curator 判断候选，不直接固化。

#### 4.3.5 Research Agent

职责：召回本轮需要的资料、记忆和规范。

输入：

- `intent.raw_request`
- `intent.constraints`
- `intent.user_preferences`
- 技能的 `tool_contract`
- 平台、角色、项目、URL、实体名。

检索策略：

```text
query_builder
  -> exact terms: 平台名、角色名、作品名、禁用词、URL
  -> semantic query: 用户目标 + 风格 + 场景
  -> filters: project_id、layer、status、tags
  -> hybrid retrieve: BM25 + Chroma vector
  -> rerank: exact entity > project canon > confirmed preference > generic memory
```

输出：

- `facts`：可用事实、项目 canon、平台规范、历史偏好；
- `source_refs`：资料来源；
- `warnings`：无法访问链接、资料置信度不足、来源不明确。

失败处理：

- 链接不可访问：保留 URL 线索，禁止编造页面内容；
- 检索为空：记录“无可靠资料”，让 Writer 只基于用户输入生成；
- 召回过多：按平台、项目、确认状态和新鲜度裁剪；
- 召回冲突：标注冲突来源，交给 Strategist 做保守取舍。

#### 4.3.6 Strategist

职责：把需求、资料、规则和技能 contract 整理成创作策略。

输入：

- `intent`
- `facts`
- skill workflow；
- 历史反馈；
- 规范和 canon 警告。

内部步骤：

1. 固定不可变约束；
2. 确认本轮成功标准；
3. 选择正文结构：短帖、长文、角色设定、发布版本、方案矩阵；
4. 选择语气策略；
5. 生成 Writer 需要的 brief；
6. 明确哪些内容不能混进正文，只能作为后台约束。

输出：

- `strategy[]`
- `writer_brief`
- `evaluation_plan`

失败处理：

- 约束冲突时优先用户最新反馈；
- 技能 contract 与用户需求冲突时，用户需求优先，技能降级为参考；
- 平台规则不确定时，采用更保守表达。

#### 4.3.7 Writer / Editor

职责：生成可继续讨论的作品版本，并根据反馈改稿。

Writer 内部步骤：

1. 读取 `writer_brief`；
2. 按 skill output contract 选择结构；
3. 使用 `facts`，但不把后台规则机械写进正文；
4. 输出完整版本；
5. 标注 `rationale`，说明本版为什么这样写。

Editor 内部步骤：

1. 定位用户反馈对应的段落或问题；
2. 区分保留、删除、替换、增强；
3. 先处理用户指定点，再整体润色；
4. 生成新版本，保留 parent_version_id；
5. 不把候选偏好直接写入正文。

输出：

- `DraftVersion.content`
- `DraftVersion.parent_version_id`
- `DraftVersion.rationale`

失败处理：

- 用户反馈模糊：给一个保守改版，不要求用户填表；
- 用户要求和平台规范冲突：优先给安全替代表达；
- 草稿过长：保留核心内容，必要时拆成版本和说明。

#### 4.3.8 Critic / Norm Agent

职责：检查作品是否满足目标、技能 contract、平台规范和项目设定。

Critic 检查项：

- 是否回应用户明确需求；
- 是否有模板感、空泛句、过度解释；
- 是否保留核心信息；
- 是否符合技能输出规格；
- 是否有继续修改空间。

Norm Agent 检查项：

- 平台表达边界；
- 夸张承诺、误导性表达、硬广风险；
- 版权、隐私、事实不确定；
- 角色 canon、世界观一致性；
- 用户禁用词和项目规则。

输出：

- `comments[]`
- `warnings[]`
- `failure_signal`

失败处理：

- 低风险问题折叠展示；
- 高风险问题进入 `warnings`；
- 反复出现的问题进入 Harness evidence。

#### 4.3.9 Agent 通信与前端状态

多 agent 不能像黑盒串联。每个 agent 开始、完成、失败和降级时，都要向会话流写入 `AgentEvent`：

```text
AgentEvent
  event_id
  session_id
  turn_id
  agent_id
  status: queued / running / completed / degraded / failed
  stage_label
  input_refs
  output_refs
  failure_signal
  visible_to_user: true / false
```

前端流式状态来自这些事件，而不是做一个纯视觉动画。展示文案要轻，例如：

| Agent | 用户可见状态 |
| --- | --- |
| Intent Agent | 正在理解需求 |
| Research Agent | 正在查找资料和规则 |
| Strategist | 正在整理创作路线 |
| Writer | 正在生成版本 |
| Editor | 正在根据反馈改稿 |
| Critic / Norm Agent | 正在检查表达和边界 |
| Memory Curator | 已记录可选偏好，完成后可查看 |

并不是每个 agent 都必须展示。短任务只展示关键阶段；复杂任务才展开更多状态。这样用户能感知系统在认真工作，同时不会看到一堆后台日志。

#### 4.3.10 Agent 触发敏感性

Orchestrator 需要根据用户输入触发不同 agent，而不是固定全量跑：

| 用户信号 | 触发重点 |
| --- | --- |
| 提到平台，如小红书、微博、公众号 | Research Agent 查平台规范，Norm Agent 检查发布边界 |
| 提到链接、作品、人物、书名、角色名 | Research Agent 做资料检索，Strategist 标注事实边界 |
| 提到“继续修改、第二段、标题、不要模板” | Editor 前置，Critic 检查反馈响应度 |
| 提到“以后、记住、默认” | Memory Curator 提高长期候选置信度 |
| 提到“这次、先、本轮” | Memory Curator 降低长期候选置信度 |
| 选择某个技能 | Orchestrator 读取对应 Skill Package，调整 agent 顺序和评测 |

触发不是硬编码模板，而是意图解析、实体识别、检索命中和历史反馈共同决定。Agent 的任务计划必须写入 `CreativeState.messages`，便于后续追踪为什么本轮调用了某个 agent。

### 4.4 Memory Curator Agent

Memory Curator 是多智能体中的专职“偏好沉淀官”。它的目标不是从用户话里抓关键词，也不是直接写入用户画像，而是在创作过程中把可能值得沉淀的信息标注出来，等用户确认作品完成后再让用户决定是否保存。

它在每轮对话后都会观察，但不会打扰用户。它读取的信息包括：用户原始需求、后续反馈、直接改稿、平台与资料线索、评审意见、最终草稿与用户点击完成的动作。

处理流程：

```text
用户需求 / 用户反馈
  -> 语义片段拆分
  -> 信号类型识别
  -> 临时性与长期性判断
  -> 作用域推断
  -> 候选规则改写
  -> 重复与碎片合并
  -> 完成后展示
  -> 用户确认后写入记忆
```

Memory Curator 先把用户话语拆成可判断的语义片段。每个片段都要保留完整语义，不能把否定词、范围词和对象切掉。

| 信号类型 | 识别对象 | 候选改写方式 |
| --- | --- | --- |
| 平台信号 | 小红书、微博、B站、公众号、抖音等 | “涉及微博时，优先检查该平台的表达习惯和发布边界。” |
| 平台规范信号 | 不要硬广、避免夸张承诺、标题自然、别像广告 | “发布到小红书时，表达不要太硬广。” |
| 表达偏好 | 克制一点、更自然、不要模板腔、更像真人 | “表达需要更自然，避免明显模板感。” |
| 项目规则 | 角色不能崩、世界观保持一致、某设定不能改 | “该项目后续创作需要保持角色与世界观设定一致。” |
| 临时要求 | 这次冷一点、本轮短一点、先不要复杂 | 只进入当前会话上下文，不推荐为长期偏好 |
| 长期偏好 | 以后默认、记住我喜欢、之后都不要 | 可以作为长期偏好候选展示 |

作用域判断：

- `session`：本次创作里的临时风格、参考、修改要求；
- `project`：角色 canon、系列设定、账号表达边界；
- `platform`：只有相关平台场景才召回的规范和表达习惯；
- `global`：用户明确确认的长期工作偏好。

Memory Curator 必须特别处理几个误学习风险：

- 用户只是指定这次任务，不等于长期偏好；
- 用户只是举例，不等于默认风格；
- 平台名只是发布目标，不等于用户永远写这个平台；
- “不要夸张承诺”必须完整保留，不能沉淀成“夸张承诺”；
- “这次语气冷一点”只影响当前会话，不能变成“用户喜欢冷感”；
- “标题太模板”应归纳成“标题避免模板感”，而不是保存原句情绪。

候选项需要携带结构化字段：

```text
kind: platform_rule / expression_preference / project_rule / canon_rule
scope: session / project / platform / global
content: 用户能读懂的候选偏好
evidence: 来自哪一轮对话或哪条反馈
confidence: 置信度
reason: 为什么系统认为它值得保存
effect: 保存后下次怎样影响创作
```

#### 4.4.1 Memory Curator 内部算法

Memory Curator 的内部实现分为六步。它不依赖单个关键词判断，也不把大模型的一句总结直接当成偏好写入。

第一步是事件切片。系统把一轮用户输入拆成多个 `utterance_span`，每个片段保留原文、轮次、关联草稿版本、用户动作和上下文位置。切片的目标不是越碎越好，而是让每个片段都能单独回答三个问题：用户在评价什么、这件事是否可复用、它应该影响哪里。

```text
utterance_span
  span_id
  session_id
  turn_id
  draft_version_id
  raw_text
  target_object: title / paragraph / tone / platform / character / plot / whole_draft
  polarity: prefer / reject / constrain / temporary / unknown
  temporal_marker: this_time / project / future / always / unknown
```

第二步是信号识别。Curator 会用规则、检索和 LLM 判断共同完成识别：

- 规则负责稳定词：平台名、否定词、时间范围词、以后、默认、记住、这次、先；
- BM25 负责精确命中：角色名、作品名、平台名、禁用词；
- 向量检索负责找相近历史：用户过去是否反复纠正过同类问题；
- LLM 负责语义判断：这句话是在给本轮改稿意见，还是在表达可复用习惯。

第三步是作用域判断。作用域先保守后升级：

```text
默认 scope = session
如果绑定同一项目 canon、角色设定或账号边界 -> project
如果只在某平台发布时成立 -> platform
如果用户明确说以后、默认、记住，或跨项目重复出现 -> global_candidate
```

作用域升级必须有证据。单次“帮我写小红书”只能说明本轮平台，不说明用户长期偏好小红书风格。单次“不要像模板”通常是本轮反馈；如果多个项目都出现同类反馈，才可以生成“表达避免模板感”的长期候选。

第四步是候选改写。改写要把口语反馈变成可执行规则，但不能改掉原意：

| 原始反馈 | 错误候选 | 合格候选 |
| --- | --- | --- |
| 标题太像模板 | 用户喜欢模板标题 | 标题需要减少模板感，保留具体信息 |
| 这次语气冷一点 | 用户喜欢冷感 | 本轮语气偏冷，不作为长期偏好 |
| 不要夸张承诺 | 夸张承诺 | 发布表达避免夸张承诺 |
| 角色别崩 | 用户喜欢角色文案 | 本项目后续创作需要保持角色设定一致 |

第五步是评分和合并。候选进入前端前，需要经过一个可解释评分：

```text
score =
  evidence_strength * 0.30
  + reusability * 0.25
  + scope_confidence * 0.25
  + user_intent_clarity * 0.15
  - interruption_risk * 0.20
```

评分字段含义：

- `evidence_strength`：证据是否来自明确反馈、重复反馈或完成版本；
- `reusability`：这条规则后续是否真的能改善创作；
- `scope_confidence`：作用域是否清楚；
- `user_intent_clarity`：用户是否明确表达“以后、默认、记住”等意图；
- `interruption_risk`：展示它是否会给用户造成负担。

同类候选会合并，而不是堆叠。例如“不要模板腔”“标题别像模板”“第二段自然一点”可以合并为“表达需要更自然，避免明显模板感”，但如果其中一条只针对标题，就不能强行扩大到全文。

第六步是完成后确认。Curator 在用户点击“完成话题”前只更新内部缓冲，不展示偏好确认。完成话题是一次创作的 commit 点，表示用户认为当前版本已经足够可用，系统才可以把这轮对话里的稳定信号整理成候选偏好。完成后最多展示 3 条高价值候选，默认折叠，并放在输入框下方，和“使用技能”一样属于低打扰辅助控件。用户点“设为偏好”后，候选才写入 L1/L2/L3；用户点“取消”后，候选标记为 rejected，不参与召回。

#### 4.4.2 写入与删除策略

用户删除对话时，系统不能简单地把所有长期记忆一起删除。对话、资产、偏好和 harness 证据需要分开处理：

| 数据 | 删除对话后的处理 |
| --- | --- |
| 会话消息与草稿 | 删除或软删除，不再显示在历史里 |
| 未确认候选偏好 | 直接删除 |
| 已确认偏好 | 默认保留，因为它是用户明确保存过的规则 |
| 与该会话绑定的项目规则 | 如果没有被其他资产或项目引用，提示用户可一并清理 |
| Harness 失败证据 | 脱敏后保留聚合指标，不保留正文 |

设置页需要提供“偏好管理”。用户可以看到每条偏好来自哪个会话或项目，也可以单独删除。这样可以避免两个极端：删除一个聊天就把用户认真保存的偏好清掉，或者用户已经不想要某条偏好却找不到入口。

候选项在会话中只作为内部缓冲存在，不参与长期召回。用户点击“完成话题”后，前端只展示高置信、低重复、可读性强的候选项。用户点击“撤销完成状态”后，会话回到工作草稿态，可选偏好盒立即隐藏；已手动保存的偏好不被撤销，因为它们已经是用户明确确认过的数据。用户点击“设为偏好”后，系统再写入 L3 或对应场景记忆；用户点击“取消”后，该候选不再影响后续创作。

Memory Curator 的输出必须能被评测。失败类型包括：临时要求误固化、否定丢失、平台规则归错作用域、候选过多、候选太碎、把技能选择误当成偏好。这些失败会进入 Agentic Harness，成为改进 Memory Curator 自身规则、提示词、eval case 和过滤策略的证据。

### 4.5 Memory：参考 Tencent Agent Memory

采用 L0-L3 分层：

| 层级 | 内容 | 用途 |
| --- | --- | --- |
| L0 | 原始会话、草稿、反馈、资料来源 | 证据回溯 |
| L1 | 原子偏好、规则、禁用项、平台线索 | 精准召回 |
| L2 | 场景记忆，如项目、平台、技能上下文 | 任务组织 |
| L3 | 稳定长期偏好 | 默认个性化 |

L1-L3 不是自动等同于 Session/Project/Global。层级描述“抽象程度”，作用域描述“生效范围”。例如“不要硬广”可以是本次 Session 规则，也可以是某账号 Project 规则，也可以是用户 Global 偏好，必须由证据和用户确认共同决定。

召回策略：

```text
BM25 精确召回 + Chroma 向量召回 + 层级权重 + 证据状态过滤
```

BM25 负责角色名、平台名、禁用词、明确实体；向量召回负责语义相近的偏好和历史经验。状态为 revoked、rejected、deleted 的记忆不进入召回。

## 5. Skills：从按钮变成能力包

当前技能体系应继续从“内容分类”转向“专家能力包”。

### 5.1 交互语义

技能不是长期模式开关，而是“本轮回复的专家路线”。用户在输入框旁选择某个技能后，当前输入框进入该技能路线；再点同一技能即取消；取消时移除系统自动填入的参考提示；提交本轮生成或反馈后，技能选择自动复位。

输入框里自动出现的文字只是一段参考，不代表技能能力本身。真正生效的是后台的 Skill Package：它告诉编排器本轮优先走哪些 agent、召回哪些知识、遵守哪些输出规格、用哪些评测项检查结果。

### 5.2 Skill Package 的内部结构

每个 Skill Package 包含：

```text
skill_id
version
trigger
input_contract
workflow_steps
tool_contract
output_contract
evaluation
examples
failure_policy
change_log
```

每个技能必须具备四层内容，才能称为“封装好的专家能力”：

| 层级 | 作用 | 文件或字段 |
| --- | --- | --- |
| 语义层 | 说明技能解决什么问题、适用和不适用的场景 | `skill.json` 的 trigger、tags、failure_policy |
| 流程层 | 把能力拆成可执行步骤，交给多 agent 协作 | `workflow.md`、workflow_steps、agent_sequence |
| 工具层 | 说明什么时候需要检索、规范检查、对比、评分、引用资料 | tool_contract、knowledge_query、norm_query |
| 评测层 | 判断这次技能有没有真的发挥作用 | eval_cases、output_contract、metric_binding |

这四层不写成硬编码分支，而是作为 harness 组件交给编排器读取。编排器根据 skill_id 注入上下文、选择 agent、约束输出结构，并在最后把结果交给评审 agent 检查。

#### 5.2.1 Skill Package 文件结构

产品级实现中，每个技能是一组可审阅文件，而不是一个按钮文案：

```text
harness/skills/{skill_id}/
  skill.json
  workflow.md
  prompt_fragments.md
  tool_contract.json
  output_schema.json
  eval_cases.json
  examples.jsonl
  failure_policy.md
  changelog.md
```

字段含义：

| 文件 | 作用 |
| --- | --- |
| `skill.json` | 技能元信息、版本、触发条件、agent_sequence、tags |
| `workflow.md` | 人类可读的流程说明，供产品和工程审阅 |
| `prompt_fragments.md` | 注入给各 agent 的短提示片段，不包含整套大 prompt |
| `tool_contract.json` | 需要调用的检索、规范、评分、对比工具及参数约束 |
| `output_schema.json` | 输出结构要求，供 Writer 和 Critic 检查 |
| `eval_cases.json` | 技能评测样例，覆盖成功和失败场景 |
| `examples.jsonl` | 用户输入示例，用于触发、测试和 few-shot |
| `failure_policy.md` | 输入不足、工具失败、约束冲突时如何降级 |
| `changelog.md` | 每次 Harness 改动、指标变化和回滚点 |

#### 5.2.2 技能运行时协议

技能被选择后，只影响本轮，不长期保持。运行时流程：

```text
用户选择 skill_id
  -> 前端标记 selectedSkill
  -> 提交本轮输入
  -> Orchestrator 读取 skill package
  -> skill context 注入 CreativeState
  -> agent_sequence 决定本轮 agent 顺序
  -> tool_contract 决定 Research / Norm / Critic 的工具和检索策略
  -> output_schema 决定 Writer 输出形态
  -> evaluation 决定 Critic 检查项
  -> 本轮结束后 selectedSkill 复位
```

技能不能覆盖用户输入。冲突优先级：

```text
用户本轮明确要求
  > 用户已确认偏好 / 项目规则
  > 平台规范 / 安全边界
  > 技能默认流程
  > 通用写作习惯
```

如果用户选择了“方案实验”，但明确说“只给我一个最终版”，系统应保留方案实验的分析能力，但输出一个最终版，不强行给多个候选。

#### 5.2.3 技能对 Agent 的影响方式

技能通过四种方式影响工作流：

1. Agent 顺序  
   例如“资料驱动”会把 Research Agent 前置，“深度改稿”会跳过 Draft Writer，优先走 Editor。

2. 共享上下文字段  
   技能把 `input_contract`、`workflow_steps`、`output_contract` 写入 `intent.project_context.skill_workflows`，供后续 agent 读取。

3. 工具契约  
   技能声明需要哪些检索或检查能力。例如 `knowledge.search(norm,platform)` 表示 Research Agent 需要优先查平台规范。

4. 评测契约  
   Critic 根据技能的 evaluation 和 output_schema 检查结果。如果输出不合格，记录 skill_contract_fail。

运行时不应出现“技能只是把一句提示塞进输入框”的情况。输入框参考文字只是用户可见的启动语，真正的技能逻辑来自 Skill Package。

#### 5.2.4 技能运行时数据结构

提交本轮输入时，前端只传 `selected_skill_id`，不把技能流程展开塞进用户文本。后端生成一个 `SkillContext`，写入共享状态：

```text
SkillContext
  skill_id
  version
  user_visible_hint
  input_contract
  agent_sequence
  workflow_steps
  tool_contract
  output_schema
  evaluation_plan
  reset_after_turn: true
```

每个 agent 只读取自己需要的部分：

| Agent | 读取内容 | 产出 |
| --- | --- | --- |
| Intent Agent | `input_contract`、用户输入 | 结构化意图和缺失字段 |
| Research Agent | `tool_contract`、实体、平台、链接 | 资料、规范、引用和不确定项 |
| Strategist | `workflow_steps`、召回资料、偏好 | 写作路线和取舍 |
| Writer / Editor | `output_schema`、writer_brief | 正文或改稿版本 |
| Critic / Norm Agent | `evaluation_plan`、output_schema | 质量分、风险和失败信号 |
| Memory Curator | 用户反馈、完成版本、skill_id | 候选偏好，但不把 skill_id 本身当偏好 |

技能运行结束后，系统生成 `SkillRunRecord`：

```text
SkillRunRecord
  run_id
  session_id
  skill_id
  skill_version
  input_summary
  agent_sequence_used
  tool_calls
  output_contract_pass
  critic_scores
  failure_signals
  user_followup_feedback
```

这个记录会进入 Agentic Harness。Harness 看到的是可定位的失败，而不是一句笼统的“效果不好”。例如用户说“你还是没有改第二段”，系统应记录为 `revision_feedback_ignored`，并绑定到 `revision_studio.workflow_steps`，而不是盲目修改全局 prompt。

#### 5.2.5 技能与普通对话的切换

技能只对本轮有效。用户下一轮可能继续用同一技能，也可能完全换任务。切换规则：

- 用户提交后清空 `selected_skill_id`；
- 用户再次点击同一技能时取消选择；
- 取消选择时移除输入框内由系统自动插入的参考提示；
- 用户手写的内容不被删除；
- 如果用户下一轮没有选技能，Orchestrator 按普通创作流程判断；
- 如果用户明确提出“继续按刚才那种方式”，Intent Agent 可以建议沿用上一轮技能，但仍需要作为本轮状态记录。

这样既保留专家能力，又不会把技能变成隐形的长期模式。

### 5.3 六个技能的能力边界

- 创作诊断：把模糊想法整理为 brief；
- 资料驱动：处理来源、链接、规范和事实边界；
- 叙事设定：处理角色、世界观、剧情和 canon；
- 发布适配：面向平台和场景发布；
- 深度改稿：处理已有草稿和用户反馈；
- 方案实验：生成多方向候选并比较。

后续实现时，每个技能都要有明确流程和评测重点：

| 技能 | 核心流程 | 输出规格 | 评测重点 |
| --- | --- | --- | --- |
| 创作诊断 | 识别作品类型、使用场景、对象和限制；把含混要求拆成目标、素材、语气、边界、可选方向 | brief、关键判断、可选方向、下一步建议 | 需求拆解完整率、假设是否清楚、方向是否互相区分 |
| 资料驱动 | 识别链接、实体、平台、资料片段；召回本地知识与规范；区分事实、判断和不确定信息 | 可用信息摘要、创作版本、事实边界说明 | 资料命中率、事实一致性、未确认信息是否被标注 |
| 叙事设定 | 抽取角色核心、关系、冲突、世界规则；召回项目 canon；生成前建立设定约束表 | 设定锚点、正文或方案、canon 检查 | 角色一致性、世界观一致性、可扩展钩子质量 |
| 发布适配 | 识别平台、发布对象、长度、标题、禁用表达；召回平台规范；检查夸张承诺、硬广和风险边界 | 标题/开头、正文、平台注意点 | 平台适配度、自然度、规范风险降低 |
| 深度改稿 | 对齐反馈，定位明确段落；区分必须改、可保留、需重写；先局部后整体 | 改后完整版本、简短修改说明 | 反馈响应度、信息保留率、模板感降低 |
| 方案实验 | 固定共同目标和不可变约束；设计多个差异方向；生成可用样稿；按同一标准比较 | 方向矩阵、多个候选版本、选择建议 | 候选差异度、可用性、比较是否具体 |

#### 5.3.1 创作诊断：creative_brief

适用场景：用户只有模糊想法，或者需求混杂，还不适合直接写最终稿。

输入 contract：

- 原始想法；
- 可选平台或使用场景；
- 可选参考材料；
- 禁用或必须保留的信息；
- 用户对结果的使用方式。

Agent 流程：

```text
Intent Agent
  -> 抽取目标、受众、载体、约束
Research Agent
  -> 轻量召回相关项目记忆和偏好，不做重资料检索
Strategist
  -> 形成 brief、风险假设和路线
Critic
  -> 检查 brief 是否可执行
Memory Curator
  -> 只记录候选，不展示
```

输出结构：

```text
创作 brief
  - 目标
  - 使用场景
  - 必须保留
  - 不能做
  - 当前假设
可选方向 2-3 个
下一步建议
```

关键技术点：

- Intent Agent 要标记“未知字段”，但不强迫用户补全；
- Strategist 要把未知字段写成假设；
- Critic 检查每个方向是否真的可执行；
- Memory Curator 不把“这次先这样”沉淀为偏好。

失败降级：

- 用户输入太短：输出最小 brief 和 2 个方向；
- 目标冲突：列出冲突点，给保守主方向；
- 没有平台：按泛用内容处理。

#### 5.3.2 资料驱动：source_grounded

适用场景：用户提供链接、规则、资料片段、参考作品、平台要求或事实边界。

输入 contract：

- 链接或资料文本；
- 用户希望使用的部分；
- 目标内容类型；
- 引用边界和不能改动的信息。

Agent 流程：

```text
Intent Agent
  -> 识别 URL、实体、平台、资料片段
Research Agent
  -> url.import / knowledge.search / memory.search
Norm Agent
  -> 检查资料使用和平台风险
Strategist
  -> 区分事实、设定、参考风格和待验证信息
Writer
  -> 基于资料生成，不编造来源
Critic
  -> 检查事实一致性和引用边界
Memory Curator
  -> 提取可保存的平台规则或项目资料线索
```

工具契约：

```json
{
  "required": ["knowledge.search", "memory.search"],
  "optional": ["url.import", "norm.review"],
  "query_fields": ["url", "platform", "entity", "project_id", "rule_terms"],
  "failure_mode": "source_unavailable_then_mark_uncertain"
}
```

输出结构：

```text
可用信息摘要
不确定或不能确认的信息
创作版本
事实边界说明
```

关键技术点：

- Research Agent 必须给每条资料标注来源；
- Writer 只能使用用户提供或检索确认的信息；
- Norm Agent 需要识别版权、平台规范和夸张承诺；
- 如果资料无法访问，草稿必须降低事实确定性。

#### 5.3.3 叙事设定：narrative_canon

适用场景：角色、世界观、剧情、势力、游戏任务、人物小传、角色宣发。

输入 contract：

- 角色或世界观素材；
- 不可改设定；
- 目标用途；
- 参考风格；
- 是否需要外部传播版本。

Agent 流程：

```text
Intent Agent
  -> 抽取角色、世界规则、冲突、口吻、目标用途
Research Agent
  -> 召回项目 canon、角色记忆、历史设定
Strategist
  -> 建立设定约束表和可发挥空间
Writer
  -> 生成角色/世界观正文
Editor
  -> 按发布或策划语境整理
Critic / Norm Agent
  -> 检查 canon、时间线、口吻和平台风险
Memory Curator
  -> 提取项目规则或角色 canon 候选
```

内部结构：

```text
设定约束表
  - 不可改：角色身份、世界规则、关键关系
  - 可发挥：语气、场景、传播角度
  - 风险：撞设定、复刻参考、时间线冲突
```

输出结构：

```text
设定内核
正文版本
可传播短版
canon 检查
```

关键技术点：

- 参考作品只能作为结构或气质参考，不能复刻表达；
- 用户说“像某角色”时，系统需要转成抽象特征；
- 项目 canon 候选默认 project scope，不是 global 偏好；
- 多次提到同一角色规则时，Memory Curator 可以提高候选置信度。

#### 5.3.4 发布适配：publish_ready

适用场景：微博、小红书、公众号、B站、活动页、短视频口播、宣发文案。

输入 contract：

- 原始内容或想法；
- 目标平台；
- 发布目的；
- 目标受众；
- 禁用表达；
- 是否需要多平台版本。

Agent 流程：

```text
Intent Agent
  -> 识别平台、发布目的、受众、长度和禁用项
Research Agent
  -> 召回平台规范、历史偏好、已确认平台规则
Norm Agent
  -> 先建立风险边界
Strategist
  -> 决定平台化结构和表达策略
Writer
  -> 生成发布版本或平台变体
Editor
  -> 去掉后台规则感，让正文自然
Critic / Norm Agent
  -> 复查平台贴合度和风险
Memory Curator
  -> 提取平台规则候选
```

平台适配不等于写平台规则说明。平台规则只能作为后台约束，正文要像用户真的会发布的内容。

输出结构：

```text
发布版本
可选标题/开头
平台差异
发布前注意点
```

关键技术点：

- 微博：短表达、转发语境、避免过度承诺和无关蹭热点；
- 小红书：真实体验感、少硬广、标题自然；
- 公众号：结构清晰、信息密度更高；
- 多平台需求要分版本，不把所有平台风格混成一个平均稿。

失败降级：

- 平台不明确：生成泛用版，并提示可继续适配；
- 平台规范无资料：使用通用安全边界；
- 用户要求违反规范：给安全替代表达。

#### 5.3.5 深度改稿：revision_studio

适用场景：用户贴草稿、要求去 AI 味、改标题、改第二段、继续修改、保留核心信息。

输入 contract：

- 原稿；
- 用户反馈；
- 保留项；
- 删除项；
- 目标风格；
- 禁用表达。

Agent 流程：

```text
Intent Agent
  -> 识别反馈对象：标题、段落、语气、结构、信息缺失
Research Agent
  -> 召回相关偏好、项目规则、上一版草稿
Editor
  -> 定位局部问题，先局部后整体
Critic
  -> 检查是否回应反馈
Norm Agent
  -> 检查改稿是否引入新风险
Memory Curator
  -> 从反馈中提炼候选偏好
```

编辑策略：

```text
feedback_map
  keep: 用户明确要保留的内容
  remove: 用户明确否定的内容
  rewrite: 用户要求改变的段落或风格
  infer: 用户没有明说但可合理优化的部分
```

输出结构：

```text
改后完整版本
简短修改说明
```

关键技术点：

- 不输出碎片修补，要给完整新版本；
- 修改说明要短，不能压过正文；
- 用户说“第二段更自然”，Editor 必须定位第二段；
- Memory Curator 应区分“这版第二段更自然”与“以后默认自然表达”。

#### 5.3.6 方案实验：variant_lab

适用场景：标题、开头、卖点、传播角度、多个创意路线。

输入 contract：

- 核心内容；
- 候选数量；
- 比较维度；
- 禁用方向；
- 平台或使用场景。

Agent 流程：

```text
Intent Agent
  -> 抽取共同目标和不可变约束
Strategist
  -> 设计差异维度：情绪、视角、冲突、信息差、平台语气
Writer / Variant Writer
  -> 生成多个真正不同的候选
Critic
  -> 按统一标准打分和排序
Norm Agent
  -> 检查标题党、夸张承诺、误导风险
Memory Curator
  -> 只记录用户确认喜欢的方向，不记录所有候选
```

输出结构：

```text
方向矩阵
候选版本 3-5 个
比较说明
推荐继续打磨方向
```

关键技术点：

- 候选之间不能只是同义换词；
- 每个候选要对应一个明确策略；
- 比较维度必须固定，不能每个候选用不同标准；
- 用户选择或反馈某个方向后，Memory Curator 才考虑候选偏好。

失败降级：

- 用户要求只要一个版本：保留内部比较，输出一个推荐版本；
- 候选太相似：Critic 标记 `variant_similarity_fail`，要求重生成；
- 候选过多：限制为 3-5 个，避免选择负担。

### 5.4 技能如何参与多 Agent 协作

技能进入工作流后，不替代多 agent，而是改变多 agent 的顺序和关注点：

```text
Skill Package
  -> Orchestrator 读取 input/output contract
  -> Intent Agent 提取该技能需要的字段
  -> Research Agent 按 tool_contract 检索资料或规范
  -> Specialist Agent 按 workflow_steps 生成中间结果
  -> Writer/Editor 产出版本
  -> Critic/Norm Agent 按 evaluation 检查
  -> Memory Curator 只沉淀用户确认后的稳定偏好
```

技能失败时，系统不直接“调大模型重试”。它需要记录失败发生在哪个环节：输入不足、资料未召回、流程步骤缺失、输出 contract 不达标，还是评测标准不合适。只有这样，Agentic Harness 才能提出可验证的技能升级。

技能升级不是直接改大 prompt，而是修改某个 Skill Package：

- 增加 workflow step；
- 调整 tool contract；
- 增加失败样例；
- 增加 eval case；
- 更新 output contract；
- 回滚到旧版本。

### 5.5 Skill Contract 评测

每次技能运行后都要生成一条 skill episode：

```text
skill_episode
  session_id
  skill_id
  version
  input_hash
  agent_sequence
  tools_used
  output_contract_pass
  evaluation_scores
  failure_signals
  user_feedback_after_output
```

评测分为三层：

| 层级 | 检查内容 | 例子 |
| --- | --- | --- |
| Schema Check | 是否满足输出结构 | 方案实验是否有候选和比较说明 |
| Quality Check | 是否达到技能目标 | 深度改稿是否真正回应第二段反馈 |
| User Feedback Check | 用户后续反馈是否说明技能失败 | 用户说“还是像模板” |

失败信号会绑定到具体组件：

- `intent_missing_field`
- `research_no_source`
- `norm_boundary_missed`
- `revision_feedback_ignored`
- `variant_similarity_fail`
- `memory_candidate_bad_scope`

只有当失败信号有证据、可复现、能通过 eval case 验证时，Harness Evolver 才能提出技能升级。

### 5.6 技能与 Memory Curator 的边界

技能可以影响本轮创作路线，但不能直接变成用户偏好。比如用户选择“发布适配”，只说明本轮需要平台化处理，不说明用户以后默认都要平台化表达。

Memory Curator 只从以下信号中提取候选：

- 用户明确说“以后、默认、记住、一直”；
- 用户反复在多个会话中纠正同类问题；
- 用户点击完成后，某条规则与最终稿强相关；
- 用户在反馈中明确表达可复用规则；
- 平台或项目约束具有稳定生效场景。

Memory Curator 不从以下内容中提取长期偏好：

- 技能选择本身；
- 系统自动填入输入框的技能参考文字；
- agent 的内部策略；
- Critic 的单次建议；
- 未被用户确认的草稿方向；
- 明确带有“这次、本轮、先、暂时”的要求。

## 6. Agentic Harness 设计

参考 AHE 的三个 observability：

### 6.1 Component Observability

每个可进化组件必须文件化、版本化、可回滚：

```text
harness/
  agents/
  skills/
  prompts/
  evals/
  policies/
```

每个组件有：

- owner；
- version；
- change log；
- linked eval cases；
- rollback target。

Memory Curator 也必须作为 harness 组件管理，而不是写死在业务代码里。它需要有独立的：

- extraction policy：如何拆分用户话语、保留否定和判断临时性；
- scope policy：如何区分 session、project、platform、global；
- candidate filter：如何过滤碎片、重复、低价值候选；
- rewrite policy：如何把口语反馈改写成用户能确认的规则；
- eval cases：覆盖误固化、否定丢失、平台识别、项目 canon、技能误存等失败样例。

### 6.2 Experience Observability

原始轨迹不能直接塞给 evolver，需要压缩成可消费证据：

```text
raw session -> failure signals -> skill episode -> evolution evidence
```

证据类型：

- 用户反馈：太模板、方向不对、平台不对；
- 评审失败：规范风险、canon 冲突、输出不符合 contract；
- 检索失败：该召回的资料没有召回；
- 记忆失败：临时要求被当成长期偏好、否定词丢失、平台规则归错范围；
- 交互失败：用户反复纠正同一问题。

### 6.3 Decision Observability

每次 harness 改动必须声明预测：

```text
如果升级 revision_studio v1.0 -> v1.1，
预计 “反馈响应度” 提升，
同类“没有按反馈改”失败减少。
```

提案字段：

- target_component；
- evidence_ids；
- root_cause；
- proposed_change；
- predicted_metric；
- validation_plan；
- risk；
- rollback_plan。

Memory Curator 的提案示例：

```text
target_component: memory_curator.scope_policy
evidence_ids: session_xxx / feedback_xxx
root_cause: “这次”类临时词没有阻止长期候选生成
proposed_change: 在 scope policy 中加入临时性优先规则，并补充 eval case
predicted_metric: 临时上下文误固化率下降
validation_plan: 跑 memory_curator eval cases，对比候选准确率和否定保真率
rollback_plan: 回退到上一版 scope policy
```

## 7. 产品可感知设计

### 7.1 从对话完成到作品归档

EcRoom 不是把所有内容都保存成聊天记录。一次创作有两个阶段：

| 阶段 | 产品语义 | 存放位置 | 用户下一步 |
| --- | --- | --- | --- |
| 工作中 | 还在探索、试写、反馈、改稿 | 生成页左侧的近期对话 | 继续对话、重命名、删除 |
| 已完成 | 当前版本已经能作为一件作品使用 | 作品库 / 个人主页作品区 | 查看成品、继续迭代、作为素材复用 |

因此，“完成话题”不是普通聊天里的结束标记，而是把会话转成作品资产的提交动作。用户点击完成后必须有一次二次确认，避免误触把工作中对话移走。

二次确认弹窗需要说明：

- 作品会进入作品库，不再作为近期工作对话展示；
- 原始创作过程仍可从作品详情进入查看；
- 后续可以基于这份作品继续迭代；
- 完成后才会展示可选偏好沉淀。

完成后的数据写入：

```text
session.completed = true
session.completed_at = now
session.archive = "works"
session.work_category = 用户选择或系统推断的作品分类
asset.source = "session"
asset.asset_id = session_id
asset.prompt = 初始关键需求
asset.final_content = 最新版本
asset.iteration_prompt = 基于作品继续迭代时回填到输入框的上下文
```

近期对话列表默认只展示 `completed=false` 的会话。作品库只收录 `completed=true` 的会话资产，以及用户从灵感页收藏的素材。这样用户看到的是“正在做的事”和“已经完成的作品”，而不是一堆混在一起的聊天。

从作品继续迭代时，不直接把用户带回旧会话继续聊天，而是把作品的关键需求、最终版本和用户的新目标一并带到生成入口，开启新的创作链路。旧作品是素材和上下文，不是被反复拖长的聊天线程。

### 7.2 完成后再学习

偏好提示只在用户确认“完成作品”后出现：

- 创作版本右下角提供“完成作品”按钮；
- 点击后弹出二次确认，不直接归档；
- 完成后按钮变为“撤销完成状态”；
- 完成后才在输入框下方展示“可沉淀偏好”小盒；
- 默认折叠，不遮挡正文，也不挤压输入框；
- 用户不处理也可以继续修改。

这里展示的是 Memory Curator 的候选结果，不是系统已经替用户做出的记忆结论。产品表达要轻，不要让用户感觉每句话都被审查或归档。候选区应该像“可保存的工作习惯”，而不是后台日志。这个设计参考成熟对话产品的记忆边界：聊天历史、临时上下文和长期记忆分开管理，长期记忆需要用户能看见、能删除、能关闭或撤回。

完成和撤销的语义：

| 状态 | 含义 | 记忆行为 | 前端表现 |
| --- | --- | --- | --- |
| 工作中 | 用户还在探索、改稿、试方向 | 只更新当前对话上下文和内部候选缓冲 | 不展示偏好盒 |
| 完成作品 | 用户认为当前版本已经可用，并确认归档 | 从内部缓冲生成可选偏好候选 | 进入作品库，输入框下方出现小型折叠盒 |
| 撤销完成状态 | 用户继续修改，刚才的完成判断作废 | 隐藏候选，不新增长期偏好；已确认保存的偏好保持不变 | 回到工作中对话 |

每条候选项必须先说明三件事：

- 它来自哪条证据；
- 它大概属于哪类信息；
- 保存为偏好后，下一次会怎样影响创作。

用户操作只保留两种：

| 动作 | 适用对象 | 结果 |
| --- | --- | --- |
| 设为偏好 | 表达偏好、平台线索、角色规则、常用限制 | 写入可管理的偏好列表 |
| 取消 | 低价值或不确定候选 | 不保存，不打扰用户 |

默认不自动“设为偏好”。系统可以持续更新候选项，但偏好保存需要用户明确动作。设置页提供“偏好”模块，展示已保存条目，并允许删除。

### 7.3 技能改进卡片

当系统发现重复失败时，展示：

```text
问题：最近 3 次深度改稿都被反馈“没有按第二段要求改”
原因：技能流程先整体润色，过晚处理局部反馈
建议：把“定位用户指定段落”加入 workflow step 1
预计改善：反馈响应度
验证方式：A/B dry-run 跑 revision eval cases
```

用户可选择：

- 启用；
- 先对比；
- 暂不启用；
- 删除这条改进建议。

### 7.4 技能版本页

每个技能展示：

- 当前版本；
- 最近改进；
- 适用场景；
- 输入输出规格；
- 评测分；
- 失败案例；
- 回滚按钮。

### 7.4 会话标题、时间与界面偏好

会话标题不是原始输入的截断。系统在创建会话后生成一个短标题，要求：

- 6-14 个中文字符为主；
- 能概括创作任务，不照搬整句需求；
- 用户可以手动修改，修改后以用户标题为准；
- 历史列表和会话页共用同一标题。

会话页左上角显示真实更新时间，不写死“今天”。时间来自会话元信息，规则为：

- 当天显示“今天 HH:mm”；
- 昨天显示“昨天 HH:mm”；
- 更早显示“YYYY/MM/DD HH:mm”。

右上角保留低负担界面控制，不放“资产库”这种重复入口。资产库继续由左侧主导航进入；所有主页面右上角固定使用明暗主题切换按钮。主题属于用户界面偏好，保存在浏览器本地，不参与创作记忆。

### 7.5 设置控制中心

设置不使用抽屉承载。它是独立页面，负责管理用户确实需要直接控制的长期配置。设置页采用“左侧 section，右侧详情页”的结构，避免把模型、偏好和数据说明堆在同一个面板里。

设置页分为三个 section：

| Section | 作用 | 是否影响后端 |
| --- | --- | --- |
| 模型设置 | 服务商、模型、Base URL、API Key 和连接测试 | 影响 LLM Client |
| 偏好记忆 | 已保存偏好、候选展示上限、最低置信度、完成后展示策略 | 影响 Memory Curator 候选筛选 |
| 数据管理 | 解释对话、资产、偏好和系统证据的删除关系 | 影响用户对删除操作的理解 |

个人资料只在个人主页管理，不放入设置页。自进化属于系统内部能力，不提供给用户手动开关；用户能感知的是创作质量、偏好沉淀、技能稳定性和错误修正结果，而不是“是否启用 harness”。偏好记忆必须来自用户在创作完成后的确认。

## 8. 达成路径

### 阶段 1：指标埋点

实现：

- session_success；
- memory_hit；
- memory_noise；
- memory_candidate_created；
- memory_candidate_confirmed；
- memory_candidate_rejected；
- memory_curator_error；
- skill_contract_pass；
- failure_signal；
- evolution_prediction；
- ab_eval_result。

### 阶段 2：Skill Package 文件化

把当前 `skills.py` 拆成：

```text
harness/skills/{skill_id}/skill.json
harness/skills/{skill_id}/workflow.md
harness/skills/{skill_id}/eval_cases.json
harness/skills/{skill_id}/examples.jsonl
```

### 阶段 3：进化提案绑定技能指标

每个提案必须绑定一个指标：

- 反馈响应度；
- 规范适配；
- 角色一致性；
- 资料命中率；
- 偏好候选准确率；
- 临时要求误固化率；
- 输出自然度；
- 可复用成功率。

### 阶段 4：Memory Curator 文件化

把偏好沉淀逻辑从零散规则整理成 harness 组件：

```text
harness/memory_curator/
  extraction_policy.md
  scope_policy.md
  rewrite_policy.md
  filters.json
  eval_cases.json
  changelog.md
```

每次修改 Memory Curator，都必须跑候选准确率、临时要求误固化率、否定保真率和单次候选数量的评测。

### 阶段 5：用户可感知界面

新增：

- 完成后可保存偏好；
- 创作上下文面板；
- 技能版本页；
- 改进建议卡片；
- A/B 对比视图。

## 9. 判定标准

EcRoom 进入下一阶段的标准：

```text
可复用创作成功率 >= 60%
相关记忆命中率 >= 80%
技能输出达标率 >= 80%
候选准确率 >= 75%
临时要求误固化率 <= 5%
提案证据覆盖率 = 100%
A/B 验证完成率 >= 80%
用户可撤销率 = 100%
```

如果这些指标达不到，继续增加 agent 或技能没有意义。应优先改检索、记忆治理、技能 contract 和评测闭环。

## 10. 参考技术

- Agentic Harness Engineering：component / experience / decision observability，要求 harness 组件可编辑、经验可压缩、决策可验证。
- Tencent Agent Memory：L0-L3 分层记忆，通过原始证据、原子记忆、场景归纳和用户画像逐层治理记忆。
