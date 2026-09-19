# Coding Agent 委派控制

本文档单独定义 Coding 关于根指令模式确认、子 Agent 和 Session 创建、职责分配、数量锁定、复用、替换、例外和委派限制的决策。其他模块不包含这些事项的独立决策规则。

## 权威与范围

**根父 Agent** 是负责当前根用户指令 Input-side Reasoning 的 Agent。只有根父级可以应用本政策、记录状态、发布 Dispatch，以及创建或管理子 Agent 或 Session。Worker 不会因为自己的 task、thread、角色、进度或发现而成为编排父级，也不会因此获得权限。

本政策服从更高优先级的用户、权限、安全、产品、运行环境、能力、仓库和安全限制。所需能力或授权不可用时，应阻塞请求的路线；绝不能默默改变模式或子 Agent 数量。

## 委派状态记录

模式和数量属于任务状态，不通过编辑本文档保存。第一次 Dispatch 前，根父级必须在任务控制记录中记录一个状态对象：

```text
owner: <根父级身份>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode: Single-Agent Coding | Multi-Agent Coding
child_count: 0 | <正整数>
allocations: [{agent, role, interaction_slice, scope, mutations, return_conditions, lifecycle}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<能力名称>]
```

任务面板或等价的运行时控制记录是规范位置。Worker 只能读取 Dispatch 中明确下发的相关状态，不能推断或修改根记录。如果运行时不能持久化或返回这份记录，该路线即被阻塞。

放行后，Worker 通过父级提供的 Dispatch Preview 进入。它不重新打开根用户模式或数量门禁，也不能修改控制记录。父级必须在 Dispatch 中包含 Worker 身份、职责、Interaction Slice、获准路径/修改、返回条件和当前 epoch。

## 根指令模式确认门禁

每个新的根用户指令到达后，根父级必须在实质性任务工作前完成以下事项：

1. 在足以形成有用建议的层次分析任务。
2. 建议采用**单代理 Coding**或**多代理 Coding**，并给出简短理由。
3. 询问用户选择其中一种模式，并等待明确选择。

根指令中写明的模式只能作为建议依据，不能替代确认问题。用户确认模式前，根父级不得创建、fork、handoff、消息联系或以其他方式管理 Agent 或 Session，不得发布 Dispatch，也不得开始实质性侦察、实现、验证、文档或 Git 工作。为形成问题所需的强制指令加载和能力检查可以执行。Worker 反馈和普通的继续请求不是新的根用户指令，不会重新打开门禁。

根父级必须将确认的模式记录为当前根指令范围内的状态。新的根用户指令会重新开始模式门禁，即使它继续处理同一个项目或任务。含糊、附条件或没有回答模式的问题都不能放行执行；应简洁地再次询问。

## 单代理 Coding

用户明确确认单代理 Coding 后：

- 所有任务工作保留在当前 Session，包括 Input-side Reasoning、Primary Output、文档、Git 工作和允许的验证。
- 不得创建、fork、handoff、消息联系、替换或以其他方式管理子 Agent 或额外 Session。结构收益、实质性修改判定、验证需求、文档/Git 需求、bootstrap、上下文恢复或运行环境便利性都不能作为例外。
- 对实质性修改，仍保留独立验证这一语义要求，但不得自动创建 verifier。当前 Session 执行允许的检查；无法提供独立验证时，必须如实报告不可用。

后续根用户指令明确要求创建子 Agent 或额外 Session 作为例外时，会重新开始新的模式门禁。只有用户明确确认最终模式，并且在选择多代理 Coding 时进一步确认正整数子 Agent 数量后，该例外才可执行。Worker 或当前 Agent 不得从“需要更多审查”“并行处理”或“寻求帮助”等请求自行推断例外权限。

## 多代理 Coding 与数量确认

用户明确确认多代理 Coding 后，根父级必须分析任务，建议准确的正整数子 Agent 数量，询问用户确认并等待。在第二道门禁期间不得创建任何子 Agent 或 Session。该数量表示当前根指令的全部子 Agent 预算，不是每个阶段或每个职责的数量。

用户确认正整数后：

- 在第一次 Dispatch 前记录并锁定数量。
- 在满足更高优先级能力、授权、权限、安全、产品、运行环境、仓库和安全限制的前提下，创建恰好该数量的子 Agent。如果环境无法安全创建请求的数量，必须停止并报告阻塞；不能默默创建更少或更多。
- 只能在锁定数量内分配职责。Primary Output、Change Verification、Documentation/Comments & Git Operations、Context Bootstrap/Refresh 以及其他辅助职责，只要分配给独立子 Agent，就各自消耗一个子 Agent 名额。
- 不得因为修改具有实质性、验证有用或必需、出现文档或 Git 工作、bootstrap 或上下文恢复有帮助、发现结构收益，或现有 Worker 提出请求而追加子 Agent 或额外 Session。
- 后续 slice 只能在当前工作流授权的范围内复用已经创建并分配的子 Agent 或 Session。复用不会创建新名额，也不得扩大已分配范围。
- 替换、fork、handoff 到新的子 Agent 或增加 verifier 都属于本政策下的新建子 Agent，不是自动复用或例外。锁定数量已经创建后，当前根指令禁止这些动作；必须由后续根指令重新通过模式和数量门禁。

### 必需的子 Agent 创建路径

创建子 Agent 是创建一个真实的委派 Agent，而不是打开一个平级聊天或普通 task。根父级必须使用运行环境提供的 **MultiAgentV1** 或 **MultiAgentV2** spawn 方法。不得使用 `create_thread`、`fork_thread`、`handoff_thread` 或其他普通聊天/线程创建 API 来伪造子 Agent。这些 API 只有在另有明确授权的用户任务或 Session 用途中才能使用，绝不能替代子 Agent 创建。

创建出的子 Agent 必须是完整的委派单元：具有独立的子 Agent 身份、由父级控制的返回路径、已发布的职责和 Interaction Slice、获授权的范围与修改、返回条件，以及执行该 slice 所需的上下文。只有在运行时暴露真实 spawn 操作、子 Agent 身份、父级控制的发送/返回路径、有界等待和生命周期状态时，才满足 MultiAgentV1/MultiAgentV2 能力 Contract。如果其中任何能力不可用或无法核验，根父级必须停止并报告阻塞能力；不得退回使用聊天方式创建的子 Agent。

如果锁定的分配中没有独立 verifier、文档/Git Worker、bootstrap Worker、恢复 Worker 或其他所需职责，根父级应在安全且获准时让当前或已分配的 Agent 在其授权范围内承担，或者报告该职责/能力不可用。已分配的独立验证必须保持独立；不能通过给同一 Session 的检查改名来模拟。如果缺少该职责使验收无法完成，应报告阻塞限制，而不是绕过数量锁定。

### 辅助职责分配

只有在复用收益可能超过建立成本时，才能分配 Context Bootstrap/Refresh：预计至少有两个相互独立的下游 Worker；某个 fresh Worker 原本需要广泛探索并加载三个或更多路由 policy module；或相关 source set 大约超过 20k 原始字符 / 5k token-equivalents。Single-Agent 工作、一个小型 Worker、本地或仅文档的快路径、已知只涉及一两个文件，以及预期复用不超过建立成本的情况都应跳过。上述条件是本政策中的路由启发式，不代表已测量的 billed、cached、quota、latency 或质量节省。分配后，Bootstrap 职责只能在锁定的分配内复用或刷新，不能因此产生新的名额。

## Dispatch 与生命周期边界

只有在模式确认完成，并且多代理 Coding 的数量确认和锁定完成后，根父级才能发布 Dispatch Preview 和创建获准的子 Agent。Dispatch Preview 只是已获授权 slice 的精简摘要，不能替代任一项用户确认。

每个子 Agent 只能接收根父级授权的角色和 slice。子 Agent 必须保持非递归：不得创建、fork、handoff、消息联系、替换或协调其他 Agent 或 Session。Worker 的发现、checkpoint 和请求只能通过父级控制的通道返回，不能改变模式或数量。

本工作流的子 Agent 生命周期必须保持可见和持久。根父级不得关闭、shutdown、归档、删除或以其他方式将已创建的子 Agent 从当前任务面板移除。子 Agent 只有在返回最终结果和证据后才能进入终态**已完成**；不得主动设置或留下关闭/ shutdown 状态。子 Agent 处于 pending 或 running 时，只能等待或发送已授权的后续输入。如果发生错误或中断，应复用同一个子 Agent 执行获授权的修复，或报告阻塞；不得把关闭它作为清理动作。如果运行环境无法让已完成的子 Agent 以打开且可见的 Agent 状态保留，则所需生命周期能力不可用，该路线必须阻塞。

根父级至少记录：门禁状态、确认的模式、适用时确认并锁定的数量、子 Agent 到职责的分配，以及不可用能力或阻塞要求。这些记录是控制状态，不是超过数量的授权。

## 重新进入与更高优先级限制

新的根指令实质性改变委派请求时，必须重新打开模式门禁；多代理 Coding 还必须在改变子 Agent 拓扑前重新确认数量。不得在不再次询问的情况下把之前的模式或数量沿用到新的根指令。

本政策不授权外部影响、仓库修改、Git 操作、凭据、网络访问，也不允许绕过运行环境限制。当前 Coding 工作流和仓库指令仍然负责这些边界。
