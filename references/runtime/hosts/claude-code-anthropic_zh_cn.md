# Claude Code + Anthropic Coding 部署

本文件是 Claude Code + Anthropic 模型族的已登记 Coding 部署文档，覆盖这一产品/provider 组合的两个部署关注点：

- **宿主机制**：Claude Code 如何提供持久指令、独立 subagent 执行、模型与 effort 选择、文件系统/沙箱 capability 和上下文传输。
- **模型策略**：哪些 Anthropic 执行层可以承担各 Coding 角色、不同任务类型使用什么控制项、substitution 如何处理，以及所需绑定不可用时如何处理。

本文件不负责 Coding 角色定义或 Session 语义。角色映射由 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md) 与 [`../../coding/session-model_zh_cn.md`](../../coding/session-model_zh_cn.md) 解析。

本文件描述的宿主机制以 Claude Code 官方 Skills、custom subagents、model configuration、settings 与 `CLAUDE.md` memory/instructions 文档为依据；下方采用检查记录了真实使用已经覆盖和尚未覆盖的能力。

本部署面向 Claude Code + Anthropic API 模型族。其他 Claude Code provider 可能以不同方式解析 alias，或拥有不同模型可用性；除非实际 runtime 满足下述绑定，否则不得直接复用。

## Host 身份

只有当前运行中的 Code Agent 环境确实是 Claude Code 时才使用本部署。不得仅根据仓库里存在 `CLAUDE.md`、`.claude/` 目录、Skill 安装路径或 prompt 中提到 Claude Code 就推断 Host 身份。

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

## 角色绑定与执行层

启动 Coding Flow 时，先通过上述宿主界面确认当前 Session 的实际 model identity，再应用这些绑定：

- **Input-side Reasoning**：当前高级 Claude 父 Session 负责高价值语义决策。本部署假设主 Session 已选择适合高级推理的 Claude runtime；不得仅因为 Haiku-class 或其他轻量 runtime 也能写代码，就允许其自动承担 input-side responsibility。
- **实质 Primary Output**：要求使用的 Anthropic 执行模型为 **`claude-sonnet`**。
- **Change Verification**：选择该角色时，为该 task conversation 启动一个全新的独立 `claude-sonnet` Session 进行最终改动结果验证，然后复用该 verifier 执行后续验证 slice。每个新的最终状态 fingerprint/epoch 都必须独立重新评估；此前结论不能作为证据。只有确实存在独立隔离需求时才创建额外 verifier Session，例如不兼容的环境/快照、不同的权限或安全域，或明确要求的独立审计。
- **Documentation/Comments & Git Operations**：选择该角色时，使用独立的 `claude-sonnet` Session 负责获准的验证后文档/代码注释物化，以及所有非简单仓库 Git 操作。它负责同步、分支/worktree 操作、暂存、提交、历史整合、reset/clean/stash、冲突处理、标签、远端、推送和适用的 Issue/PR 交付；只有极小的只读 Git 元数据查询可以留在该角色之外。
- **Context Bootstrap/Refresh**：选择该职责时，使用独立或可复用的 **`claude-sonnet`** Worker 进行有界事实与 policy-routing capsule 物化，默认使用 `effort=medium`。确定性的 metadata/source-hash 或增量 refresh capsule 工作在仍可机械验证时，可以改用 **`claude-haiku`**；必须留在 Sonnet 上时使用 `effort=low`。语义解释仍由 Input-side Reasoning 负责。
- **轻量 Output / 辅助 Worker**：严格有界、低语义风险、易机械验证的工作，在独立 Worker 具有明确 model-tiering 收益时，应优先使用 **`claude-haiku`**。
- **Dual-role eligibility**：当前 Session 能明确确认自身为 `claude-sonnet`，并且宿主能在同一 Session 满足当前任务要求的 Sonnet effort 时，本部署声明该 Session 同时适配 Input-side Reasoning 与实质 Primary Output。通用 Runtime 因此进入 **Single-Session Coding Mode**，除非存在独立结构性拆分理由。
- **正常双 Session 映射**：当前高级父 Session 不是 `claude-sonnet` 时，父 Session 只承担输入侧推理职责，并创建/复用独立 `claude-sonnet` Primary Output subagent 承担实质执行。

本绑定有意使用 provider 的层级 alias `claude-sonnet` 与 `claude-haiku`，而不是固定版本 ID。Claude Code 会把每个 alias 解析为宿主当前提供的最新模型版本，因此本部署无需修改本文件即可跟随产品当前的各层模型。这也意味着本部署承诺的是**层级**保证——实质执行落在 Sonnet 层、轻量执行落在 Haiku 层——而不是某个具体版本。应在 Coding Flow 启动时记录每个 alias 实际解析到的版本，并在版本变化后重新执行采用检查。

Single-Session Coding Mode 描述的是**实质 Primary Execution Session**，不是禁止有价值的辅助模型分层。当前 Sonnet 层 Session 直接完成源代码/项目探索、实现、调试、临时聚焦检查和实现输出，不为了维持双角色形式再把普通工作委派给另一个 Sonnet Session。它不承担非简单 Git 操作，也不会取消验证与交付角色：对实质性功能改动，输入侧 Agent 仍会启动一个全新的独立 Change Verification Session，并在同一个 task conversation 的后续验证 epoch 中复用它；需要文档或非简单 Git 工作时，还可创建独立的 Documentation/Comments & Git Operations Session。

处于 Single-Session Coding Mode 的 Session 只有在本轮初始选定的独立验证、验证后的文档/注释或非简单 Git 操作隔离、真正并行、当前上下文明显失效/膨胀、存在明确独立隔离收益，**或有界 Haiku model tiering** 时才允许创建额外 Agent。仓库规模、长输出、build/test 工作或笼统“任务复杂”本身，不是把实质 Primary Output 再拆成另一个 Sonnet Session 的理由。

## 独立执行映射

本部署需要独立 Primary Output、verifier、辅助 Worker、轻量模型层 Worker 或定向 escalation runtime 时，使用具有独立上下文的 Claude Code subagent。

需要 sticky Primary Execution Session 时，应使用可恢复的 custom subagent 或可恢复的 general-purpose 路径，而不是 built-in Explore / Plan：

- 普通 custom/general-purpose subagent 的首次调用会得到新的独立 context；
- 可恢复 subagent 完成后会返回 agent ID；Session Affinity 适用时，后续工作应 resume/message 同一个 agent，而不是重新创建新的实例；
- 创建 subagent 时，在指令正文中以可读文本写明本次指定的模型绑定——层级 alias，宿主已经解析出具体版本时一并写明——以及 effort 档位，即使也通过宿主控制项设置了这些值；不得要求 subagent 从工具参数或自身运行时身份推断本次指定。复用已明确写过相同指定的 subagent 时，不要机械重复；指定发生变化或先前指令缺失、不明确时再写明；
- built-in Explore 与 Plan 是 one-shot，不返回可 resume 的 agent ID，因此可以执行有界只读调查，但不能充当长期 Primary Execution Session；
- 普通 subagent 不会自动继承父会话完整历史，也不会自动继承父会话已经调用过的 Skills。父级应按 Core 规则只传递必要 task / Contract 信息；Worker 的执行若依赖本 Skill 的细则，应在自身上下文中加载相应 Skill reference。

当前 Claude Code 环境若无法创建所需的独立 subagent context、无法选择所需模型，或不能满足所需运行参数，应把该 capability failure 交给下方 unavailable 规则处理，而不是自行换模型。

## 模型路由与轻量 Worker

本部署**先选择模型层**，随后只应用该层真实支持的控制项。custom subagent 支持在单次调用或 frontmatter 中显式指定 `model`，因此应显式请求绑定的层级，而不是依赖 subagent 的 inherited model。对于长期复用的 custom subagent，也可以把同类要求写进 subagent definition，但本 Skill 不强制要求仓库额外提交 Claude Code 专属 agent 文件。

Claude Code 的宿主界面、task list 或工具结果可能已经显示等价的派发信息；是否还需要额外用户可见预览由共享 `Dispatch Preview` 规则决定，本部署不创建第二套产品专属反馈协议。

### 路由到 Haiku

当任务严格有界、语义风险低且易机械验证时，优先使用 `claude-haiku`。适合的工作包括：

- 有界 repo / file / symbol exploration 与事实 inventory，前提是不负责决定架构或产品语义；
- 运行已经选定的 build/test/lint/formatter/type-check，收集失败并把原始日志压缩成事实；
- 文件/路径元数据收集、精确搜索/提取、确定性格式整理、字面替换、generated-table update 及类似机械变换；
- 当目标语义已经由 Semantic Contract 固定时，做小范围文档/注释同步；
- 已经明确行为和预期 assertion 的简单单元测试物化；
- 对彼此独立的问题进行并行只读调查，结果由父级或 Sonnet 执行路径做机械/语义检查。

Haiku 是**有界执行器和证据 Worker**，不是更便宜的通用 Primary Output。不得让其承担 Semantic Contract、架构/产品判断、跨模块实现、非平凡调试、复杂测试设计、public API/schema/migration/permission 变更、安全敏感修改，或正确执行明显依赖大量自主判断的任务。

如果某个任务最初符合 Haiku 层，但执行中发现会改变目标、架构、兼容性、风险或 Acceptance 的歧义，应停止当前方向并把压缩事实返回父级。父级完成 Contract amendment 后，再决定下一阶段是否切换到 Sonnet。

### 路由到 Sonnet

一般 feature implementation、非平凡 refactor/debug、跨模块修改、复杂 test/verification logic、已批准 migration、兼容性敏感工作、安全敏感工作，以及其他需要较多实现判断的实质 Primary Output 使用 `claude-sonnet`。

无法明确确认任务是否真的低风险且易机械验证时，应优先使用 Sonnet，而不是扩张 Haiku 边界。

### One-shot 只读 exploration

**不得**假设 Claude Code built-in Explore 永远是 Haiku 成本层。当前 Claude Code 版本中的 built-in Explore 会继承主会话模型（再受产品文档描述的 cap/override 行为影响）。因此：

- 当“不要求 exploration 必须处于 Haiku 成本层”时，可以继续使用 built-in Explore 做有界 one-shot 只读调查；
- 当本部署要求 exploration 留在 Haiku 层时，应使用显式 Haiku model 的 custom/user/project `Explore` 定义，或其他显式 Haiku custom subagent；
- 名为 `Explore` 的 custom subagent 会覆盖 built-in Explore，并保持自己的 `model` 字段；
- 需要连续上下文的重复轻量执行，应优先使用可 resume 的 custom/general-purpose Haiku subagent，而不是反复调用 one-shot Explore。

这样可以把成本策略保留为显式部署行为，而不是依赖可能随 Claude Code 版本变化的 built-in 默认值。

## Effort 选择

Claude Code custom subagent 在所选模型支持 Claude Code effort 时可以使用 `effort` override，effort 请求如何生效由宿主负责。只有在任务已经路由到某个层级、且该层级真实暴露 effort 之后，才应用 effort。

在 Sonnet 层，本部署使用 `low`、`medium`、`high`，这三档也是本部署使用的全部档位。按任务实际难度选择档位：

- **`low`**：简单的文档修改和简单的代码编写——语义已经确定的文档/注释同步，以及推理深度需求很小的小范围明确代码修改。
- **`medium`**：一般开发。这是常规 feature implementation、一般 refactor/debug 和实现反馈测试代码的默认档位。
- **`high`**：困难任务——跨模块修改、非平凡调试、兼容性或安全敏感工作、已批准 migration、复杂 test/verification logic，以及已经在 `medium` 档位受阻的任务。这是本部署使用的最高档位；`high` 无法解决的任务属于需要上报的 Runtime 或语义阻塞，而不是去寻求更强设置的理由。

角色归属：

- **实质 Primary Output**：一般开发使用 `medium`；已放行任务属于简单文档修改或简单代码编写时使用 `low`；任务确实困难时使用 `high`。这一档位阶梯不会把问题定义、架构选择、未解决的语义权衡或验收 ownership 转移给 Primary Output；输出很长或项目规模很大本身不能作为升档理由。
- **Change Verification**：选择的 verifier 默认使用 `high`，因为它需要针对最终变更状态独立选择并解释整体检查。它只负责验证证据，不负责修复、架构决策或语义验收。
- **Documentation/Comments & Git Operations**：文档/注释物化使用 `low`；非简单仓库 Git 操作使用 `medium`，因为它属于常规操作而不是简单编辑。其文档写入范围排除功能与测试；其 Git 范围限制为明确放行的仓库/worktree/ref/remote 操作。不得用来弥补验证失败或自行做未经批准的产品决策。
- **其他辅助 Sonnet Worker**：默认使用 `medium`；只有具体任务确实困难时才升到 `high`，只有属于简单文档修改或简单代码编写时才降到 `low`。

组织级 effort cap 可能把 Sonnet 请求档位向下 clamp。若要求的档位没有真实生效，应按 unavailable 规则处理，而不是只根据请求值判断成功。

Effort 名称只是宿主/Runtime 控制项，不是跨模型通用的能力单位；相同名称在不同模型上的标定不能直接等价比较。

## Haiku 推理控制边界

**不得**把 Sonnet 的 `low`/`medium`/`high` 规则机械复制给 Haiku。当前产品中 Haiku 层没有 effort surface，因此本部署主要通过**任务 eligibility + 模型选择**控制 Haiku 的成本与能力边界，不虚构 Haiku effort tier。Haiku-tier Worker 不能仅因为 subagent schema 存在 `effort` 字段，就继承 Sonnet 的档位。由于层级 alias 会跟随宿主当前版本，应把该 effort surface 当作需要重新确认的宿主 capability，而不是层级的永久属性：即使未来某个 Haiku 层版本支持 effort，本部署也不会在没有显式修订的情况下授权把 Sonnet 的档位复制过去。

Haiku 层与 Sonnet 层在 Anthropic API 层的 thinking 语义也不同。本部署不要求固定 thinking budget，也不人为定义 Haiku 对应的 effort 等价物。一个有界任务如果需要明显更强推理，应改路由到 Sonnet，而不是在 Haiku 上模拟 Sonnet effort。

## Runtime substitution 与 fallback

Claude Code 可能因为 organization `availableModels`、provider 限制、配置的 fallback chain 或 runtime availability 替换/切换所请求的 subagent model。这个宿主行为**不是**本部署授权的 fallback，因此“dispatch 成功”本身不足以证明部署绑定已满足。

由于本部署绑定的是层级 alias 而不是固定版本，需要区分两类不同事件：

- **层级内版本漂移**：`claude-sonnet` 或 `claude-haiku` 解析到同一层级的更新版本。这是 alias 的预期行为，不属于 substitution；继续执行并记录新版本。
- **层级不匹配**：Sonnet 层的请求被 Haiku 层、Opus 层、其他层级或未知模型承接。这属于 capability mismatch，按下方 unavailable 规则处理。

每个独立且受绑定的 Worker 都必须：

1. 请求其角色要求的层级 alias（`claude-sonnet` 或 `claude-haiku`），并且只在本部署确实为该层定义了 effort 档位时才请求 effort；
2. Claude Code 能暴露实际 subagent Runtime 时检查真实生效值，例如 task/result 界面，并记录每个 alias 解析到的具体版本；
3. 实际 Runtime 与绑定的执行层不匹配时，不得静默把该 Worker 重新解释为“仍符合部署绑定”；
4. Sonnet effort 被 clamp 到低于任务要求的档位时，按下方 unavailable 规则处理。

“工具调用没有报错”本身不足以证明请求的 Runtime 已真实生效，尤其在 non-interactive/background 场景中 clamp/substitution 可能不明显。

不得把 Claude Code automatic substitution 或 fallback chain 当成本 Skill 可以静默放宽这些绑定的授权。

## Foreground、background 与工具能力

Claude Code subagent 可以在 foreground 或 background 运行。background subagent 的内置工具集合会比 foreground 更窄。应根据已批准阶段真正需要的工具选择执行方式；如果 background 的工具收缩会影响正确执行，就不能仅为了并行而转成 background。

Token I/O Decoupling 架构不要求 Agent Teams、cross-session messaging、dynamic workflows、hooks 或其他 Claude Code 专属编排层才能工作。Host 可以拥有这些能力，但本部署的基础运行路径必须保持在普通 Skill + subagent 调度之上。

## 文件系统与 worktree 映射

多个 Agent 处理同一个开发需求时，默认复用该 task 的 primary Git worktree。独立 Agent/Session、全新的 verifier、Worker 专属 Context Exchange 目录，或者 `isolation: worktree` 这一能力本身，都不要求额外 worktree。遵循 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md) 中的验证与明确隔离例外；并发写入发生冲突时，优先分配互不重叠的路径范围或按依赖顺序执行 slice。

Claude Code custom subagent 支持 `isolation: worktree`，可以为 subagent 创建独立 repo worktree。只有确有隔离需求时才使用它，例如不兼容的快照/环境、无法重定向或隔离的验证写入、不同的权限/安全边界要求提供单独限定的文件系统视图，或明确要求隔离的审计。

`isolation: worktree` 只增强工作副本隔离，并不自动满足 Context Exchange 的全部 capability 要求。仍须遵循 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md)：

- 宿主支持路径级限制时，每个 Worker 的 RW 范围只覆盖共享 primary worktree 中明确列出的变更路径和自己的 Context Exchange 子目录；verifier 对固定最终状态保持 RO，只有其获准 slice 明确授权的验证脚本/测试路径可以 RW；
- 跨 Worker context 应尽量以宿主能够支持的最窄范围暴露；
- 只有当前 Claude Code sandbox/permission 真实强制执行时，才可以宣称 path-level RO/DENY 隔离；
- 无法安全提供 targeted RO 时，先使用 Core 定义的机械复制 fallback，再考虑父级重新生成中转文本。

Claude Code 会对 worktree-isolated subagent 额外执行命令/路径检查，但本部署仍然只能描述当前版本与配置真实提供的保证。

## 委派边界

Primary Output 或辅助 subagent 继续遵守 Core delegation boundary：即使 Claude Code 暴露 `Agent` 工具，也不得因为工具存在就递归构造新的执行层级。fresh verifier、并行 Worker、Haiku auxiliary 与 targeted escalation 仍由父级高价值决策 Agent 统一调度。

如果 subagent 需要完整 Token I/O Decoupling Skill 才能可靠执行职责，应优先在该 subagent 内加载/调用 Skill，或使用会预加载该 Skill 的 custom subagent 配置。不要让父 Agent 每次派发都重新生成完整 Skill 文本。

## Unavailable handling

- 不得把实质 Primary Output `claude-sonnet` 静默替换成 Opus、Fable、Haiku 层模型或 inherited parent model。alias 解析到同一 Sonnet 层的更新版本属于预期行为，不是 substitution；解析到其他层级才是。
- 不得把 Haiku-tier Worker 静默换成 Sonnet 后仍宣称“低成本层成功执行”。Haiku 不可用时，父级可以在明确认识到低成本层不可用后，主动把这个有界任务 reroute 到 Sonnet；这属于显式策略选择，不是接受 Host fallback。
- 需要独立实质 Primary Output 但无法选择或确认 `claude-sonnet` 时，停止对应实质 Coding 或验证工作并简短报告 Runtime 阻塞。不得因为 verifier 绑定不可用就让 Primary Output 自行验证实质性改动。
- Sonnet 所需 effort 因 provider/组织 cap 无法真实应用时，停止受影响的实质任务，不得假设请求值已经生效。
- Haiku-eligible 任务无法使用绑定的 Haiku 层时，可以在不违反 Context Firewall / role policy 的前提下留在当前已授权 Session，显式 reroute 到 Sonnet，或报告 capability/cost-tier mismatch；不得把未知 substituted model 当成等价 Haiku。
- 不得因为 Claude Code inherited/substituted 一个高级父模型，就把高体量实质项目状态工作重新放回父 Session。Token I/O 分离仍是有意部署策略。

## 采用检查

安装或修改 Skill / Claude Code Runtime 配置后，使用新的 Coding Session 做一个小型、无破坏性的检查：

1. 个人安装时确认 `~/.agents/skills/token-io-decoupling/` 共享源存在，且 Claude Code 能发现 symlinked personal entry；
2. 确认 Skill 可发现，Coding Flow 能加载 Runtime Registry；
3. 确认因为真实 Host 是 Claude Code 而选择了本部署文档；
4. 确认本部署会按任务类别请求预期的 Sonnet 或 Haiku 层；
5. 选择实质双 Session 模式时，确认 Primary Output subagent 实际运行在绑定的 Sonnet 层/effort 上，而不是 substituted Runtime，并记录该层级 alias 解析到的具体版本；
6. 选择 Haiku-tier auxiliary 时，确认实际 model 属于绑定的 Haiku 层，且没有套用不受支持的 Sonnet-style effort 假设；
7. Session Affinity 适用时，确认后续相关工作 resume 同一个 Primary Execution subagent；
8. 确认 Coding Core 文档仍保持 vendor-neutral。

本部署在真实使用中已经覆盖：Skill 发现与 Runtime 解析、Host 身份解析、Sonnet 层 Single-Session Coding Mode，以及 Coding Core 保持 vendor-neutral。依赖 Haiku-tier 辅助派发或正常双 Session Primary Output 派发的检查尚未执行：这些 capability 应标记为未验证，而不是按已验证假设处理，也不得把整个部署描述成已完整 smoke-tested。

## 官方能力来源

本部署使用的 Claude Code 行为来自官方 Skills、custom subagents、model configuration、settings 与 `CLAUDE.md` memory/instructions 文档。因为这些产品机制可能变化，未来应在对应机制变化时更新本文件，而不是把 Claude Code 专属变化搬进 Coding Core。
