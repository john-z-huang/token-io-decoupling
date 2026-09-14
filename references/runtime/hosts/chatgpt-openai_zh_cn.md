# ChatGPT 普通聊天 + OpenAI Coding 部署

本文件登记 **ChatGPT 普通聊天环境**中的 OpenAI Coding 部署。这里的 ChatGPT 指用户在 ChatGPT 产品中进行的普通对话会话，**明确不包括 ChatGPT Work**。不得把 Work 的 cloud computer、长任务执行、跨应用工作流或其他 Work 专属能力推断为普通聊天可用。

本部署同时覆盖两个部署关注点：

- **Host Adapter**：普通 ChatGPT 聊天如何暴露当前会话、工具/连接器、文件或代码执行能力，以及是否存在独立执行上下文。
- **Model Profile**：在当前聊天实际可确认和可控制的范围内，OpenAI Runtime 如何承担 Coding 角色。

Coding 角色定义、checkpoint、Context Firewall、验证边界和 Context Exchange 仍由 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md)、[`../../coding/session-model_zh_cn.md`](../../coding/session-model_zh_cn.md) 及其他 Core 文档负责。本文件不修改这些语义。

## Host 身份与范围

只有当前宿主确实是 ChatGPT 的普通聊天环境时才使用本部署。以下情况不得使用本 Host Adapter：

- ChatGPT Work；
- Codex CLI / Codex app；
- Claude Code、Qwen Code 或其他 Code Agent；
- 仅因为提示词、仓库文档或 Skill 安装路径中出现 `ChatGPT` 字样。

Host 识别必须以当前产品环境实际暴露的事实为准。

## Capability-first 原则

ChatGPT 普通聊天的能力可能因产品版本、账号配置、会话类型和已连接工具而变化，因此本部署不把某项工具或执行能力视为产品名称天然保证。

每个 task conversation 开始时，只根据当前会话真实暴露的 capability 解析 Runtime，包括：

- 当前模型身份是否可确认；
- 是否能显式选择或控制后续执行模型；
- 是否能创建真正独立、具有独立上下文 ownership 的执行 Session；
- 是否有代码执行、文件系统、仓库或连接器工具；
- 工具是否支持当前任务所需的读写、验证与交付操作；
- 是否存在可证明的隔离边界，而不仅是同一会话中的逻辑步骤。

没有暴露的 capability 一律视为不可用，不得通过产品知识、历史会话或对未来功能的猜测补齐。

## 普通聊天不是 ChatGPT Work

本部署必须在文档和运行时判断中保持这一边界：

- 不使用 Work 的 cloud computer 或长任务执行能力作为普通聊天的 capability 证据；
- 不把 Work 中可能存在的多步骤执行、应用导航或持续工作空间映射为普通聊天的 Session；
- 用户要求使用 Work 时，应切换到独立的 Work 部署设计，而不是扩张本 Adapter 的含义。

## 角色映射

### Input-side Reasoning

由当前 ChatGPT 父会话承担高价值语义分析、问题定义、方案选择、授权边界、checkpoint 和最终验收 ownership。

### Primary Output

若当前普通聊天明确暴露了可创建独立执行 Session、并且能够满足当前 Model Profile 所要求的模型与参数控制，则可把 Primary Output 映射到该独立执行上下文。

如果没有这种能力，Primary Output 可以由当前会话承担逻辑职责，但此时只是 **Single-Session responsibility isolation**：

- 保留批准范围、输出边界、checkpoint 与 handoff；
- 不声称创建了独立 Worker；
- 不声称把 output token 转移到了另一个模型或 Session；
- 不把同一会话中的分阶段思考描述成 Token I/O decoupling 的完整经济收益。

### Change Verification

实质性功能改动的独立最终验证仍需要 Core 定义的独立性。如果当前普通聊天没有暴露真正独立的 verifier Session 或等价隔离执行上下文，则：

- 当前会话可以执行临时反馈检查、测试命令或证据收集；
- 这些结果不能被标记为独立 Change Verification；
- 不得因为同一会话重新阅读 diff 或“切换角色”就声称形成独立验证证据；
- 需要独立验证而 Host 不具备能力时，按 unavailable handling 明确报告该边界。

### Documentation/Comments & Git Operations

普通聊天可以在用户授权且工具 capability 足够时执行文档、代码注释及 Git/GitHub 交付职责。若这些操作通过 GitHub、Google Drive 或其他连接器完成，连接器只是工具通道，不构成独立 Agent/Session。

任何写操作仍必须遵守项目自身开发流程、用户授权和连接器权限；工具存在不等于自动授权。

## 工具与连接器映射

ChatGPT 普通聊天可能暴露 GitHub、Google Drive、代码执行、文件处理或其他工具。它们可以作为当前角色执行工作的 capability，但必须遵守以下规则：

1. 工具调用属于发起调用的当前 Session 上下文；除非宿主明确证明存在独立上下文，否则不能把一次工具调用计作子 Agent。
2. 连接器返回的大体量结果应按 Core 的 Evidence-on-Demand 与 Context Exchange 原则压缩和按需传递。
3. 工具权限不足、缺少写能力或缺少文件系统隔离时，不得通过其他未授权通道绕过。
4. 同一连接器可以被多个逻辑职责使用，但角色切换本身不会产生新的验证独立性。

## 验证与执行环境限制

ChatGPT 普通聊天不应被视为具有 Codex CLI 或普通本地开发环境那样的通用 shell / Python 执行环境。即使某个具体聊天暴露了受控代码执行工具，也只能使用该会话实际提供的能力，不能据此假定仓库脚本、Python、shell、Git CLI 或完整项目依赖可用。

因此，当仓库开发流程要求运行 `python3 scripts/...`、shell 检查、测试套件、lint、build 或其他本地验证命令，而当前普通聊天没有暴露相应执行环境时：

- 不得声称已经运行或通过这些验证；
- 不得把 GitHub/Drive 等连接器的文件读写能力当作 shell、Python 或测试执行能力；
- 可以检查 diff、文档结构和连接器可获得的静态证据，但这些证据不能替代要求实际执行的验证脚本；
- 在 PR、Issue 或最终交付说明中应明确记录“由于 ChatGPT 普通聊天 Host 缺少所需执行环境，相关验证未运行”，并把需要执行的命令留给具备本地/CI/Code Agent 环境的一方运行；
- 如果任务验收标准强制要求这些命令实际通过，则当前 Host 只能完成可支持的修改与静态检查，不能把任务标记为完成验证。

不得为了获得 shell、Python 或 cloud computer 而把 ChatGPT Work 的能力引入本 Adapter；Work 仍属于明确排除的独立 Host。

## Model Profile

本部署不硬编码“普通 ChatGPT 必然运行某个模型”。模型绑定只使用当前会话能够明确确认的事实。

- **Input-side Reasoning**：当前用户选择并由宿主实际运行的 ChatGPT 模型承担。
- **Primary Output / auxiliary Worker**：只有宿主暴露独立执行上下文并允许明确选择目标 OpenAI 模型时，才允许登记具体模型绑定并执行模型分层。
- **Reasoning effort**：只有宿主明确暴露对应控制项时才应用；没有暴露时记录为 host-managed，而不是猜测具体档位。
- 不得仅因为当前父会话是高能力模型，就宣称另一个便宜模型已经承担输出工作。

因此，在没有独立模型路由能力的普通聊天中，本部署主要提供 **Core compatibility / responsibility isolation**，而不是宣称实现完整的跨模型 Token I/O 解耦。

## Session 与 Context ownership

当前普通聊天只有一个可确认 Session 时：

- 使用同一 Session 承担多个逻辑职责；
- 每个职责仍遵守批准范围、Return conditions、Unreleased boundary 和 checkpoint；
- 使用摘要、文件或稳定证据引用减少不必要的原始上下文重复；
- 不制造虚构的 worker ID、session ID、独立模型身份或独立 verdict。

只有宿主实际提供独立执行上下文时，才应用 Core 的多 Session topology 和 Context Exchange 隔离规则。

## Dispatch Preview

只有发生真实独立执行上下文派发时，才把动作描述为 dispatch/delegation，并按共享 Dispatch Preview 规则给出简短可见说明。

同一 ChatGPT 会话内的职责切换应描述为阶段或 slice 切换，不得使用“已创建子 Agent”“已委派给 Luna”等会误导用户认为存在真实独立 Session 的措辞。

## Unavailable handling

出现以下情况时必须降级或阻塞，而不是虚构 capability：

- 无法确认当前模型：使用 host-managed model 表述，不声称具体模型绑定。
- 无法创建独立 Session：进入 Single-Session responsibility isolation；需要独立性的 Change Verification 不得伪造通过。
- 无法显式选择 Worker 模型：不得声称完成跨模型输出转移。
- 缺少 shell / Python / 项目执行环境：不得声称运行仓库验证脚本、测试、lint 或 build；明确记录未运行的验证及原因。
- 缺少仓库/文件写能力：只返回计划、patch 建议或其他当前工具真实支持的产物。
- 缺少用户授权：停止对应写操作。

如果任务的验收标准强制要求独立 verifier、明确的低成本 Worker、真实 Session 隔离或必须实际运行的仓库验证，而普通聊天无法提供这些 capability，应明确说明当前 Host 不满足该 Runtime 要求。

## 验证状态

本部署登记的是 **ChatGPT 普通聊天的受限/能力驱动映射**。已确认的设计目标是：在没有独立子 Agent 能力时保持 Coding Core 的职责与边界，同时拒绝伪造多 Session 或跨模型收益。

在普通 ChatGPT 聊天真正暴露并执行独立 Session 创建、模型路由与隔离验证之前，不得把这些路径标记为已验证。普通聊天缺少所需 shell / Python / 项目执行环境时，仓库验证脚本与测试同样必须保持“未运行”状态，不能根据静态检查推断通过。ChatGPT Work 的任何真实使用也不能作为本部署的验证证据。
