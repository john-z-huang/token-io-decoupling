# Coding Runtime Contract

本模块是 Coding Flow 在“运行时无关调度架构”与具体 Code Agent 产品、模型族和执行参数之间的边界。Coding 架构只定义职责与上下文 ownership；本模块负责说明所选 Runtime 如何把这些职责映射到真实 Session，而不把厂商或模型名称写回 Core。

角色与 Session 语义来自 [`session-model_zh_cn.md`](session-model_zh_cn.md)；共享 dispatch、Contract、反馈和证据规则来自 [`../shared-protocols_zh_cn.md`](../shared-protocols_zh_cn.md)。

## Runtime 组成

一个 active Coding runtime 由两个彼此独立的部署关注点组成：

- **Host Adapter**：描述当前 Code Agent 产品如何提供持久指令、独立 Agent/Session 创建与复用、显式运行参数选择、文件系统/沙箱 capability 和上下文传输。
- **Model Profile**：声明哪些具体模型/运行配置可以承担各 Coding 角色、不同任务类型使用什么执行参数、定向升级策略，以及所需绑定不可用时如何处理。

Host Adapter 回答“**这个产品怎么实例化工作**”；Model Profile 回答“**哪个 Runtime 应承担这项职责**”。Flow 规则不得把两者混为一谈或相互推断。

已登记的部署文件通过 [`../runtime/index_zh_cn.md`](../runtime/index_zh_cn.md) 选择。只加载当前环境匹配的 Host Adapter 与 Model Profile，不预加载全部 Runtime 文档。

## Runtime 身份与 capability 解析

在需要依赖 Session 拓扑或显式模型/运行参数的实质性 Coding 执行前：

1. 根据当前运行环境实际暴露的事实识别 Host，不根据仓库名称、提示词措辞或猜测判断；
2. 选择匹配的已登记 Host Adapter；
3. 选择与该 Host 和目标部署兼容的 Model Profile；
4. 在宿主能够提供时，通过 Host 获取当前 Session 的模型/Runtime 身份以及相关参数 capability；
5. 按所选 Profile 的角色 eligibility 与 unavailable 规则执行。

不得仅因为某个模型“通常会写代码”，就静默认定当前 Session 满足某个角色。角色 eligibility 属于部署策略：某个模型即使技术上能够承担一项职责，active Profile 也可能为了保持 Token I/O 边界而明确要求把该职责放在另一 Session。

若当前环境没有匹配的已登记 Host Adapter/Profile 组合，不得自行发明产品专属操作，也不得静默套用其他厂商的模型绑定。依赖 Runtime 的 Coding 执行应停止，直到存在兼容部署。仍可使用 Runtime 无关的 Semantic Contract 与规划概念做分析，但这不等于已经实现物理 Token I/O 隔离或获得受支持的 Runtime 映射。

## Session 映射算法

解析 active runtime 后，按 `session-model_zh_cn.md` 定义的逻辑职责进行映射：

1. **确认输入侧 eligibility**：当前父 Session 必须满足 active Profile 对 Input-side Reasoning 职责的要求；不满足时执行 Profile 的 unavailable 规则，不得静默重新分类当前 Session。
2. **优先复用兼容的同一 Session**：如果 active Profile 明确声明当前 Session 同时可以承担 Input-side Reasoning 与 Primary Output，Host 能在该 Session 满足当前任务要求的运行参数，且不存在独立结构性收益，则使用 **Single-Session Coding Mode**。
3. **需要时进入正常双 Session**：如果当前 Session 可以承担输入侧推理，但 active Profile 不允许它承担 Primary Output，则通过 Host Adapter 创建或复用满足 Profile 的 Primary Output 模型绑定与参数要求的独立 Session。
4. **双角色均兼容时也只有具体理由才能拆分**：fresh verification、真正并行、上下文容量恢复、明确隔离，或 Profile 明确定义的定向升级，才可以在当前 Session 已具备双角色 eligibility 时仍创建额外 Session。
5. **无法满足时阻塞，不静默替换**：所需独立 Session、模型绑定或运行参数无法满足时，遵循 active Profile 的阻塞/只读降级规则；不得把高体量执行静默移回一个 Profile 未授权承担该角色的 Session。

仓库规模、长输出、build/test 工作或笼统的“任务复杂”本身不会改变上述映射。

## 按需验证、文档与 Git 操作映射

输入侧 Reasoning Agent 决定改动的实质程度、风险或用户明确要求是否使独立最终验证具有具体收益。选择 **Change Verification** 后，Host 必须在 Primary Output 到达实现 checkpoint 后，按照 active Profile 为该角色创建一个全新的独立 Session。verifier 接收最终状态和已批准的验证输入，不得继承 Primary Output 的实现历史，也不得静默变成修复 Worker。

验证完成后如有文档或代码注释工作，或需要任何非简单仓库 Git 工作，输入侧 Agent 可以选择 **Documentation/Comments & Git Operations**，并使用 Profile 指定的辅助物化绑定与 effort 档位创建独立 Session。文档 slice 只有在 verifier 通过（或输入侧 Agent 明确将任务分类为行为保持不变并跳过独立验证）后才能放行，且写入 capability 必须限制在获准的文档/注释范围内。Git slice 可以在需要同步、分支/worktree 准备、历史整合、冲突处理或其他仓库 Git 工作的阶段放行，并必须设置准确的 Git 范围与 capability 边界。

不存在独立的交付角色或交付 Worker：提交、推送、远端和 Issue/PR 交付都属于 Documentation/Comments & Git Operations 的 Git slice。只有在父 Agent 具有明确的用户/任务授权且 Host 能够强制实施所需边界时，该 Agent 才能检查或修改 Git 元数据和远端状态。仅当使用已批准内容完成明确获准的操作时才允许冲突解决编辑；若需要新的语义或产品决策，应返回父级与 Primary Output。如果 active Runtime 无法提供所需隔离或受支持的 Worker，应遵循其 unavailable 规则并阻塞；不得静默自行授权、扩大文档范围或替换为任意模型。

在 Single-Session Coding Mode 中，双角色 eligibility 只覆盖 Input-side Reasoning 与 Primary Output 的实现，不授权当前 Session 对已选择 fresh verifier 的实质性最终改动自行验证，也不让当前 Session 充当 Documentation/Comments & Git Operations Agent 或执行非简单 Git 工作。如果无法创建所选独立绑定或满足所需参数，应遵循 active Profile 的 unavailable 规则，不得静默退回 Primary Output 自我验证、让输入侧承担长篇物化或由输入侧执行 Git 操作。

## Runtime 参数 ownership

Coding Core 文档有意不定义厂商专属参数名称或具体模型档位。Model Profile 可以对任务分类并映射到宿主支持的参数；Host Adapter 则描述在该产品中如何请求这些参数。

当 Host 无法暴露 active Profile 要求的参数时，以 Profile 的 unavailable 规则为准；不得把“缺少控制项”解释成可以任意使用宿主默认值。

## 定向升级

Model Profile 可以为某个已经反复失败、来回振荡或明确阻塞的具体任务定义严格收窄的 escalation runtime。这是普通 Session 映射的例外，不是把所有 Worker 升档或默认拆分 Session 的理由。

升级需要替换现有独立 Worker 时，条件允许应通过 [`context-exchange_zh_cn.md`](context-exchange_zh_cn.md) 保留可复用状态。阻塞解决后，恢复 Profile 的正常角色绑定与任务参数。

## 可移植性边界

新增 Code Agent 产品时，正常应通过新增 Host Adapter 和兼容 Model Profile 接入，而不修改：

- Input-side Reasoning、Primary Output、Change Verification 与 Documentation/Comments & Git Operations 角色定义；
- Context Firewall 语义；
- Semantic Contract 与 Decision Checkpoint；
- Primary Execution Session Affinity 与按需 Worker 生命周期；
- Context Exchange ownership；
- 实现反馈、独立改动验证与语义验收边界；
- 文档/注释专属物化与非简单 Git 操作边界。

只有新环境暴露出无法通过 Runtime Contract 表达的真实架构要求时，才修改 Core。不得为了部署方便在 Core 文档中加入 `if <product>` 或 `if <model>` 分支。
