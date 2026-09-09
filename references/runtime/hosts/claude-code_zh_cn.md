# Claude Code Host Adapter

本文件描述当前 Anthropic Coding 部署在 Claude Code 中使用的宿主机制，不负责 Coding 角色定义或具体模型策略。角色映射由 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md) 解析，具体 Anthropic 模型绑定由选中的 Model Profile 定义。

本 Adapter 基于当前 Claude Code 官方文档编写。用于本次开发的仓库环境没有安装 `claude` CLI，因此当前集成属于“官方文档能力已核对”，而不是“已在本环境完成真实 CLI 冒烟测试”。不得把这一限制改写成已经完成实测的声明。

## Host 身份

只有当前运行中的 Code Agent 环境确实是 Claude Code 时才使用本 Adapter。不得仅根据仓库里存在 `CLAUDE.md`、`.claude/` 目录、Skill 安装路径或 prompt 中提到 Claude Code 就推断 Host 身份。

当 Claude Code 能暴露当前模型、effort、provider、organization 限制、subagent task 状态或实际 subagent runtime 时，应使用这些事实做 Runtime 解析。交互式 Claude Code 中，`/status`、`/model`、`/effort` 与 `/tasks` 都可以作为检查有效配置的宿主界面。若关键 identity/capability 无法确认，应把该不确定性反馈给 Coding Runtime Contract，而不是猜测。

## Skill 安装与持久 bootstrap

个人安装推荐只维护一份 canonical Skill，统一放在 `~/.agents/skills/token-io-decoupling/`。不要仅因为 Claude Code 原生个人发现目录是 `~/.claude/skills/`，就再维护一份 Claude 专属副本。

Claude Code 支持 symlinked Skill directory，因此推荐本地映射为：

```bash
mkdir -p ~/.claude/skills
ln -s ~/.agents/skills/token-io-decoupling ~/.claude/skills/token-io-decoupling
```

这样 Claude Code 看到的发现入口仍是 `~/.claude/skills/token-io-decoupling/SKILL.md`，但唯一事实来源是 `~/.agents/skills/token-io-decoupling/`。链接已经存在时，应更新或修复链接，而不是把 Skill tree 同时复制到两个目录。

项目级 Skill 仍保留在 `.claude/skills/<skill-name>/SKILL.md`。它们具有仓库/版本控制作用域，因此不应机械重定向到个人共享目录。

继续使用标准 `SKILL.md` 入口，不为 Claude Code 复制一份 Core 指令。

如果希望本地 Claude Code 的每个 Coding Session 都稳定加载本 Skill，应使用 Claude Code 的持久指令机制，而不是在每次任务 prompt 中复制完整 Skill。用户级 bootstrap 可放在 `~/.claude/CLAUDE.md`；项目规则应放在 `./CLAUDE.md` 或 `./.claude/CLAUDE.md`。bootstrap 应保持简短，只负责指向已安装 Skill，由 Skill 自己完成 Flow 与 Runtime 路由。

Claude Code 原生读取的是 `CLAUDE.md` 而不是 `AGENTS.md`。当一个项目需要同时服务多个 Code Agent 时，可以由 `CLAUDE.md` import 已有 `AGENTS.md`，但不得把完整 Token I/O Decoupling policy 同时复制进两个文件形成双重事实来源。

Claude Code cloud session 不读取本机个人目录下的 `~/.claude/skills/`，也不会读取本地 `~/.agents/skills/`；云端环境应使用仓库中的 `.claude/skills/`、受支持的 synced skill，或该 cloud session 实际能够加载的其他部署方式。

## 独立执行映射

当 active Model Profile 要求独立 Primary Output、verifier、辅助 Worker、轻量模型层 Worker 或定向 escalation runtime 时，使用具有独立上下文的 Claude Code subagent。

需要 sticky Primary Execution Session 时，应使用可恢复的 custom subagent 或可恢复的 general-purpose 路径，而不是 built-in Explore / Plan：

- 普通 custom/general-purpose subagent 的首次调用会得到新的独立 context；
- 可恢复 subagent 完成后会返回 agent ID；Session Affinity 适用时，后续工作应 resume/message 同一个 agent，而不是重新创建新的实例；
- built-in Explore 与 Plan 是 one-shot，不返回可 resume 的 agent ID，因此可以执行有界只读调查，但不能充当长期 Primary Execution Session；
- 普通 subagent 不会自动继承父会话完整历史，也不会自动继承父会话已经调用过的 Skills。父级应按 Core 规则只传递必要 task / Contract 信息；Worker 的执行若依赖本 Skill 的细则，应在自身上下文中加载相应 Skill reference。

兼容的 Single-Session Coding Mode 只是在同一 Session 内切换逻辑职责，不应因此创建新的实质 Primary Output subagent。但当 active Profile 明确声明某个有界任务适合低成本模型层时，独立轻量 Worker 仍可因为 model-tiering 的实际收益而成立。

## Model 选择与轻量 Haiku Worker

Claude Code custom subagent 支持在单次调用或 frontmatter 中显式指定 `model`，因此可以实现 Model Profile 定义的 Sonnet/Haiku 执行层。Adapter 只负责这些控制项“如何请求”；准确 model ID 与任务 eligibility 仍属于 Model Profile。

Profile 明确绑定 Runtime 时，应显式请求对应参数，而不是依赖 subagent 的 inherited model。对于长期复用的 custom subagent，也可以把同类要求写进 subagent definition，但本 Skill 不强制要求仓库额外提交 Claude Code 专属 agent 文件。

### One-shot 只读 exploration

**不得**假设 Claude Code built-in Explore 永远是 Haiku 成本层。当前 Claude Code 版本中的 built-in Explore 会继承主会话模型（再受产品文档描述的 cap/override 行为影响）。因此：

- 当“不要求 exploration 必须处于 Haiku 成本层”时，可以继续使用 built-in Explore 做有界 one-shot 只读调查；
- 当 active Anthropic Profile 明确要求 exploration 留在 Haiku 层时，应使用显式 Haiku model 的 custom/user/project `Explore` 定义，或其他显式 Haiku custom subagent；
- 名为 `Explore` 的 custom subagent 会覆盖 built-in Explore，并保持自己的 `model` 字段；
- 需要连续上下文的重复轻量执行，应优先使用可 resume 的 custom/general-purpose Haiku subagent，而不是反复调用 one-shot Explore。

这样可以把成本策略保留为显式 Profile 行为，而不是依赖可能随 Claude Code 版本变化的 built-in 默认值。

## Effort 选择

Claude Code custom subagent 在所选模型支持 Claude Code effort 时可以使用 `effort` override。Adapter 只负责 effort 如何请求；Model Profile 决定所选模型是否应使用 effort。

不得假设每个 Anthropic 模型都拥有相同 effort surface。当前 Claude Code effort 支持包括 Sonnet 5，但不包括 Haiku 4.5。因此 Haiku-tier Worker 不能仅因为 subagent schema 存在 `effort` 字段，就继承 Sonnet 的 `high`/`xhigh`/`max` 策略。若 Profile 判断任务需要超过 Haiku 层能力的推理，应直接 reroute 到 Sonnet。

组织级 effort cap 可能把 Sonnet 请求档位向下 clamp。若 Profile 要求的 level 没有真实生效，应把该事实反馈给 Profile，而不是只根据请求值判断成功。

## Runtime substitution 与 fallback

Claude Code 可能因为 organization `availableModels`、provider 行为、配置的 fallback chain 或其他 Runtime 限制替换/切换 subagent model。因此“dispatch 成功”不等于 Profile 已满足：

1. 请求 Profile 规定的 model 与该模型真实支持的 effort；
2. Claude Code 能暴露实际 subagent Runtime 时检查真实生效值，例如 task/result 界面；
3. 如果实际 Runtime 不符合所选 Profile execution tier，则把它视为 capability mismatch，并按 Profile unavailable/rerouting rule 处理。

不得把 Claude Code automatic substitution 或 fallback chain 当成本 Skill 可以静默放宽 Model Profile 的授权。

## Foreground、background 与工具能力

Claude Code subagent 可以在 foreground 或 background 运行。background subagent 的内置工具集合会比 foreground 更窄。应根据已批准阶段真正需要的工具选择执行方式；如果 background 的工具收缩会影响正确执行，就不能仅为了并行而转成 background。

Token I/O Decoupling 架构不要求 Agent Teams、cross-session messaging、dynamic workflows、hooks 或其他 Claude Code 专属编排层才能工作。Host 可以拥有这些能力，但本 Adapter 的基础运行路径必须保持在普通 Skill + subagent 调度之上。

## 文件系统与 worktree 映射

Claude Code custom subagent 支持 `isolation: worktree`，可以为 subagent 创建独立 repo worktree。当 Core 工作流需要独立代码工作副本，或真正并行写入需要物理隔离时，可以使用这一能力。

`isolation: worktree` 只增强工作副本隔离，并不自动满足 Context Exchange 的全部 capability 要求。仍须遵循 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md)：

- 每个 Worker 只能 ownership 自己的 code worktree 与 Context Exchange 子目录；
- 跨 Worker context 应尽量以宿主能够支持的最窄范围暴露；
- 只有当前 Claude Code sandbox/permission 真实强制执行时，才可以宣称 path-level RO/DENY 隔离；
- 无法安全提供 targeted RO 时，先使用 Core 定义的机械复制 fallback，再考虑父级重新生成中转文本。

Claude Code 会对 worktree-isolated subagent 额外执行命令/路径检查，但 Adapter 仍然只能描述当前版本与配置真实提供的保证。

## 委派边界

Primary Output 或辅助 subagent 继续遵守 Core delegation boundary：即使 Claude Code 暴露 `Agent` 工具，也不得因为工具存在就递归构造新的执行层级。fresh verifier、并行 Worker、Haiku auxiliary 与 targeted escalation 仍由父级高价值决策 Agent 统一调度。

如果 subagent 需要完整 Token I/O Decoupling Skill 才能可靠执行职责，应优先在该 subagent 内加载/调用 Skill，或使用会预加载该 Skill 的 custom subagent 配置。不要让父 Agent 每次派发都重新生成完整 Skill 文本。

## 采用检查

安装或修改 Skill / Claude Code Runtime 配置后，使用新的 Coding Session 做一个小型、无破坏性的检查：

1. 个人安装时确认 `~/.agents/skills/token-io-decoupling/` 共享源存在，且 Claude Code 能发现 symlinked personal entry；
2. 确认 Skill 可发现，Coding Flow 能加载 Runtime Registry；
3. 确认因为真实 Host 是 Claude Code 而选择了本 Adapter；
4. 确认 active Model Profile 会按任务类别请求预期的 Sonnet 或 Haiku Runtime；
5. 选择实质双 Session 模式时，确认 Primary Output subagent 的实际 Sonnet model/effort 符合 Profile，而不是 substituted Runtime；
6. 选择 Haiku-tier auxiliary 时，确认实际 model 是 Profile 绑定的 Haiku，且没有套用不受支持的 Sonnet-style effort 假设；
7. Session Affinity 适用时，确认后续相关工作 resume 同一个 Primary Execution subagent；
8. 确认 Coding Core 文档仍保持 vendor-neutral。

若当前环境无法完成其中某项检查，应明确标记该 capability 尚未验证，不得把部署描述成已完整 smoke-tested。

## 官方能力来源

本 Adapter 使用的 Claude Code 行为来自官方 Skills、custom subagents、model configuration、settings 与 `CLAUDE.md` memory/instructions 文档。因为这些产品机制可能变化，未来应在对应机制变化时更新本 Adapter，而不是把 Claude Code 专属变化搬进 Coding Core。