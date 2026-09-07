# Token I/O Decoupling

`token-io-decoupling` 是一个面向支持 Agent Skills 的开发型 code agent 的调度 Skill。它把传统单模型同时承担的“输入侧理解/推理”和“输出侧执行/物化”拆成两个角色，使高价值语义推理与高体量项目读写可以由不同模型承担。

## 设计目标

- 让输入侧 Agent 聚焦用户意图、业务语义、架构决策、Semantic Contract 与语义验收。
- 让输出侧 Agent 处理高体量项目探索、原始工具输出、代码/文档/配置物化、调试修复和机械验证。
- 避免大型 diff、测试日志、文件树等低决策密度原始内容直接污染高级父模型上下文。
- 复用 Primary 输出侧 Agent，减少重复项目探索，并尽量维持缓存友好的稳定上下文前缀。
- 通过“完整相关上下文 + 简短 Semantic Contract”降低父 Agent 为重新描述既有背景而产生大量输出的需要。
- 采用事件驱动汇报、Evidence-on-Demand 和分层验收，避免把输出侧工作日志重新灌回输入侧上下文。
- 在每次派发前显示受严格长度约束的 Dispatch Preview，让父会话能够看出 Output Agent 收到的任务，同时避免复制长 prompt 或完整上下文。

## 当前 OpenAI Profile

当前具体运行策略为：

- 输入侧：当前高级父模型，典型为 GPT-5.6 Sol；
- 输出侧：`gpt-5.6-luna`；
- 实现、长输出和其他实质性物化任务使用 `reasoning_effort=xhigh`；
- Luna 不递归委派；模型身份或必要参数不可满足时不静默 fallback。

该 Profile 是当前部署策略，不是架构本身。未来模型变化时，应优先调整 Profile，而保持 Input-side / Output-side 的职责边界稳定。

## 核心机制

### Context Firewall

可能产生大量项目原始状态的命令和工具输出默认由输出侧 Agent 摄入并压缩；输入侧 Agent只接收做决策所需的事实。严格有界的小型元数据查询可以直接执行。

### Primary Output Agent

同一连续工作流优先维持一个 Primary Luna，后续探索、实现、测试和修复默认复用。只有独立验证、上下文失效/膨胀、必要并行或明确隔离收益时才新建 Agent。

### Semantic Contract

输入侧 Agent 负责目标、约束、架构决策和验收标准；复杂任务把宿主可安全共享的完整相关上下文交给输出侧 Agent，同时用简短 Contract 固化最终有效决定。后续变化优先使用增量 amendment。

### Dispatch Preview

Input Agent 在每次实际向 Output Agent 派发新任务或增量指令前，先在父会话显示一条极简摘要。默认 1–3 行、目标约 80 tokens 以内，明显接近 120 tokens 时继续压缩；只保留任务、必要范围、关键约束和必要运行参数，不复制完整 Semantic Contract、完整上下文或实际长 prompt。复用 Primary Agent 时只显示本次新增 delta。

### 两级规划

输入侧做语义级规划与重大决策；输出侧根据项目实际状态自行完成执行级规划、实现、调试和修复。会改变已批准目标、架构、约束或验收标准的新事实必须升级回输入侧。

### Verification Boundary

输出侧做构建、测试、lint、diff、日志等机械验证并压缩结论；输入侧做语义验收。需要进一步确认时采用 Evidence-on-Demand，而不是默认重新读取全部原始证据。

### Cache-Aware Context Stability

优先采用 `stable prefix + small delta`：复用 Primary Agent、只追加新目标和决策变化，不反复重写已有背景。缓存是否实际命中由宿主实现决定，本 Skill 不把缓存收益作为保证。

## 文件

- `SKILL.md`：完整运行规则。
- `agents/openai.yaml`：OpenAI Agent Skill 展示与隐式调用配置。

## 开发流程

本项目的修改遵循 `dev-workflow-standards`：使用合规工作分支、中文提交与文档、开放 Issue 关联、通过 Pull Request 合并，并避免任何 Code Agent 署名或生成声明。
