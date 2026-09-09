# Qwen Code Host Adapter

本文描述 Qwen Code 部署中的 Host 专属机制。它不负责定义 Coding 角色，也不负责具体 Alibaba Qwen 模型策略。角色映射由 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md) 解析；具体模型绑定和 effort 策略由所选 Model Profile 定义。

## Host 身份

只有实际运行环境确实是 Qwen Code 时才使用本 Adapter。不得仅因为出现 Qwen 模型名、Alibaba Cloud 凭证、仓库文件或 `QWEN.md` 就推断 Host 是 Qwen Code。

当 Qwen Code 能暴露当前模型、provider、effort、Session 或 subagent 配置时，应使用这些事实完成 Runtime 解析。若某项必要 capability 无法确认，应把事实返回给 Coding Runtime Contract，而不是猜测。

## Agent Skills 与持久指令

个人安装推荐只维护一份 canonical Skill，统一放在 `~/.agents/skills/token-io-decoupling/`。

Qwen Code 原生发现 `~/.qwen/skills/` 下的个人 Skills 与 `.qwen/skills/` 下的项目 Skills。当前 Qwen Code 还支持通过 `skills.directories` 增加额外 Skill 扫描根目录，因此本项目推荐直接把共享目录加入扫描范围，而不是再复制一份到 `~/.qwen/skills/`：

```json
{
  "skills": {
    "directories": ["~/.agents/skills"]
  }
}
```

Qwen Code 会递归扫描这些额外目录中的 `SKILL.md`。默认 Skill 目录对同名 Skill 具有更高优先级，因此如果希望共享源成为唯一事实来源，就不要在 `~/.qwen/skills/` 中留下旧的同名 `token-io-decoupling` 副本。

项目级 Skill 仍保留在 `.qwen/skills/<skill-name>/SKILL.md`。它们具有仓库/版本控制作用域，因此不应机械重定向到个人共享目录。

若部署需要每次新 run 都能获得本 Skill 的关键约束，应使用 Qwen Code 的持久指令机制，而不是复制完整 Skill。`~/.qwen/QWEN.md` 提供用户级指令，项目根目录 `QWEN.md` 提供团队共享项目指令，`.qwen/QWEN.local.md` 提供项目内个人指令。Qwen Code 还会读取已有 `AGENTS.md`，因此已经采用这一可移植指令文件的仓库无需再维护一份重复的 QWEN 专属副本。

持久 bootstrap 应保持很短：只指向已安装的 `token-io-decoupling` Skill，让 `SKILL.md` 自己路由到所需 references。不要把完整 Coding Flow 复制进 `QWEN.md`。

## 独立 subagent 映射

当 active Model Profile 需要独立 Primary Output、verifier、辅助 Worker 或 escalation Session 时，优先使用 regular named/general-purpose Qwen Code subagent，而不是 fork；只有确实需要继承父级上下文时才使用 fork。

regular subagent 适合作为 Coding Runtime 边界，因为它们：

- 使用与父 conversation 分离的独立 context；
- 可使用具体 model ID、`fast` 或 provider-qualified selector 显式选择模型；
- 可限制工具访问；
- 父级必须立即消费结果时可前台运行，独立工作时可后台运行；
- retained state 支持续接时，可以继续接收相关后续任务。

fork subagent 会继承父 conversation，因此不能提供同等的 Context Firewall 语义。它适合有界并行调查，但不应默认承担 sticky Primary Execution Session。fork 还与父级共享 working directory，当前也不提供 worktree isolation。

## Primary Execution Session 续接

对于负责相关 Primary Output 工作的后台 regular subagent，应优先保持 Session affinity，而不是启动重复 Worker：

1. 使用 `list_agents` 找到现有可寻址 agent 及其 `task_id`；
2. 使用 `send_message` 发送相关后续工作；
3. 若出现 `resume_blocked_reason`，或 retained state 实际不可用，应把它视为 capability failure，而不是假定旧上下文仍然存在；
4. 只有续接不可用，或者 Core 规则确实要求 fresh Session 时，才启动替代 Worker。

已完成的后台 agent 可能继续复用 resident runtime，也可能从 retained transcript 恢复。Adapter 不得声称比 Qwen Code 实际报告更强的持久性。

## 模型选择

Qwen Code subagent 可以使用：

- `inherit`，或省略 model 字段，从而复用主 Session 模型；
- `fast`，通过配置的 `fastModel` 解析；
- 具体 model ID；
- 多 provider 部署中的显式 `authType:model-id` selector。

对于要求精确 Primary Output 绑定的 Model Profile，应优先使用具体 model ID，或者使用能够确认最终解析结果的 `fastModel` 配置。不得把 `fast` 本身当成模型身份：如果 `fastModel` 缺失或无效，Qwen Code 可能回退到 inherit，从而违反 Profile。

Qwen Code 也支持 model grade，但 grade 只是部署层间接映射，并不能证明实际模型身份。若 Profile 要求精确绑定，应确认最终解析模型，而不是只相信语义 grade 名称。

## Reasoning-effort 控制

Qwen Code 通过 Session/provider 配置暴露 reasoning intensity，包括 `/effort` 控制和 provider `generationConfig.reasoning` 设置。对于 Alibaba Cloud Model Studio / DashScope 的 Qwen3.8 模型，provider 最终会把所选 effort 映射到 Qwen 支持的 reasoning 参数。

需要明确区分的是：subagent `model` 配置与 reasoning effort 不是同一个控制面。regular subagent 定义可以直接绑定模型，但任务级 effort 可能依赖 active Session/provider 配置，而不是单独的 subagent frontmatter 字段。

因此：

- 通过该 Session/provider 实际可用的最强 Qwen Code 控制请求 Profile 所需 effort；
- Qwen Code 能暴露实际生效值时应确认 effective effort；
- 除非当前配置确实支持，否则不得声称每个独立 subagent 都有隔离的 effort 开关；
- 如果无法保证独立 Worker 的 effort 控制，则精确模型绑定仍是硬约束；对 effort-sensitive dispatch 应遵循 Profile 的 degraded/unavailable 规则，而不是虚构某个档位已经生效。

## Worktree 与文件系统映射

Qwen Code regular subagent 支持通过 `working_dir` 绑定当前仓库中已经存在的 linked git worktree。这与 Coding Context Exchange 可以直接对应：

- 需要隔离代码改动时，将 Worker 绑定到父级预先分配的既有 worktree；
- Context Exchange 写入仅限父级分配的 context 子目录；
- 有条件时使用工具/权限限制实现访问控制；
- 不得把 git worktree 本身描述成权限边界。

Qwen Code 还可以提供其他产品专属 isolation 模式，但 Token I/O Decoupling 不要求 Agent Team、Arena、Herdr 等 Qwen 专属调度系统。可移植 Runtime Contract 仍然负责定义拓扑语义。

## Runtime/provider 配置

Alibaba Qwen 部署通常通过 Qwen Code 的 model-provider 配置连接 Alibaba Cloud Model Studio / DashScope。凭证必须留在 Skill 文本、仓库文档、prompt 和提交的 provider 配置之外。

对 Qwen3.8 系列，provider-level reasoning 配置应避免同时发送冲突控制，例如同时设置 `reasoning_effort` 与 `thinking_budget`。优先使用一种有效机制，并确认 provider 实际采用的值。

某些 Alibaba Cloud API 模式下，Qwen3.8 默认会保留历史 reasoning。由于 retained `reasoning_content` 会计入输入 token 和费用，不得把隐藏 reasoning 重复复制或手工拼接到普通 content。应让 Host/provider 按支持的 conversation 格式管理。

## 生命周期与验证

正常交互 Session 中，Qwen Code 会监控默认个人/项目 Skill 目录，并在短暂延迟后刷新变更。通过 `skills.directories` 配置的额外目录属于 Skill discovery 范围；修改该设置后应验证发现结果，如果当前 mode/version 不会 live-refresh 新扫描根目录，则重启 Qwen Code。bare mode 也可能需要重启。

采用个人共享源时，应确认 `~/.agents/skills/token-io-decoupling/SKILL.md` 存在、`skills.directories` 已包含 `~/.agents/skills`，并确认 `~/.qwen/skills/` 下没有更高优先级的旧同名副本遮蔽共享源。

持久指令发生变化后，应在 fresh Session 或明确恢复且可检查加载 context 的 Session 中验证。

本 Adapter 基于当前 Qwen Code 与 Alibaba Cloud 公开 capability 文档。在本仓库部署完成真实 Qwen Code CLI smoke test 之前，Runtime Registry 应准确标注其验证状态，而不能称为本地已验证。
