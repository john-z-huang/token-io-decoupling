# 任务计划生命周期工具

[English](TASK_PLAN_TOOLS.md) | [简体中文](TASK_PLAN_TOOLS_zh_cn.md)

本文档负责任务计划三个确定性 MCP 工具的配置和使用。[任务计划生命周期 owner](../references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)仍负责工作流语义；本页描述实现边界，不授予任务授权。

## 配置与发现

`task_plan_update`、`task_plan_complete`、`task_plan_archive` 属于 `workflow` profile 和默认公开清单。它们是 Native 操作，不以 Enhanced 数据库或已验证 Root 绑定作为存储机制。仍须具备既有宿主权限和任务授权。

后端必须显式配置实际已初始化的 Serena `MemoryManager` 及获准项目根目录。`create_server(task_plan_service=...)` 支持嵌入。组件如下：

```python
from token_io_decoupling.server import create_server
from token_io_decoupling_workflow.task_plan_core import SerenaMemoryStore, TaskPlanService


def make_server(project_root, memory_manager):
    # 两个参数均来自宿主已经获准的 Serena 项目。
    store = SerenaMemoryStore(memory_manager, project_root, storage_scope="global")
    return create_server(profile="workflow", task_plan_service=TaskPlanService(store))
```

操作者自己的 launcher 集成可用 `--task-plan-factory module:callable` 加载无参数 callable，返回已配置的 `TaskPlanService`。例如：

```sh
token-io-decoupling start-mcp-server --profile workflow --task-plan-factory trusted_adapter:make_service
```

`trusted_adapter` 是操作者提供并审查的模块，不是内置适配器或工具参数。其环境须已具备兼容 Serena 依赖及获准项目对象。工具包不会安装 Serena、加载/迁移其配置、创建项目、猜测 `.serena` 目录或另开 Memory 存储。不得执行虚构 factory 以获得可用状态。未配置服务返回 `unavailable` 且不检查 Memory 路径；显式配置无效时失败，不静默降级。

## 仓库存储 scope

宿主按嵌入示例选择 `storage_scope="global"` 以共享全局规划。构造器兼容默认值仍为 `"project"`；请求不能选择存储 scope、仓库 ID、Memory 根目录或任意命名空间。全局模式使用实际 manager 已存在的 canonical 全局 Memory 根；项目模式使用其已有项目 Memory 根。两种模式均不初始化或重定向 Serena 配置。

| Scope | 活动逻辑 Memory 名 | 对应物理路径 |
| --- | --- | --- |
| `global` | `global/token-io-decoupling/repos/<repository-id>/plans/PLAN-<plan_id>` | `<actual-global-memory-root>/token-io-decoupling/repos/<repository-id>/plans/PLAN-<plan_id>.md` |
| `project` | `plans/PLAN-<plan_id>` | `<actual-project-memory-root>/plans/PLAN-<plan_id>.md` |

归档名称/路径只将同一仓库 scope 中的 `plans` 换成 `archive-plans`。现有原生 Serena list/read 操作可使用返回的 `memory_name`；全局列表须限定为 `global/token-io-decoupling/repos/<repository-id>/plans` 或其归档 topic。生命周期工具不新增无过滤的 list/read 端点。原始全局列表不是仓库 ACL。

全局仓库 ID 为 `git-v1-` 加上 `b"token-io-decoupling:git-common-dir:v1\0" + os.fsencode(str(canonical_git_common_dir))` 的 SHA-256。服务通过有界本地 Git 查询核对绑定的绝对 checkout 根和 canonical Git common directory。主工作区及 linked worktrees 共享该目录，因此分别配置的服务共享同一规划文件、锁、history、revision 和 replay 身份。独立 clone 与同名不同仓库拥有不同 ID。分支、remote URL、commit 和 checkout basename 不决定 ID。该 ID 是本机身份：搬迁 Git 共同目录会改变 ID，须显式核对旧映射。复用同一共同目录路径会复用 key，因此在该位置新建仓库后，使用前须核对归属/历史。

每个请求的 `project_root` 仍须精确匹配该服务配置的 checkout。绑定主工作区的服务不接受 worktree 路径作为替代；应使用 worktree 自己获准的 manager/root 配置其服务。服务在全局 Memory 效果前重新核验仓库身份。Git/全局根缺失、Git 环境重定向、身份改变、不支持路径或权限拒绝时失败关闭；全局模式绝不回退项目模式。实际全局根必须已存在。中间命名空间/文件符号链接会被拒绝，不作为隐式共享映射跟随。

Capability 和操作回执报告 `storage_scope`、全局模式的 `repository_id` 及准确的带仓库层级映射。全局 history version 2 使用明确 `repository_id` 和可读的 `task-plan-header-v2` / `task-plan-event-v2` JSON 围栏，允许其他绑定 worktree 更新和完全相同逻辑操作的重放，不假装其 `project_root` 未变。项目本地 version 1 仍绑定 checkout 并保留原 v1 framing。其他 worktree 的重试只改变 checkout 绑定；操作 ID 及逻辑记录/证据须相同。变化的操作须用新 ID 和已审阅版本。

全局模式不搜索、移动或改写旧的未分层全局规划、项目本地规划或归档，也不自动转换结构化 version-1 history。访问它们应保留既有后端/映射。另行迁移须确认仓库归属、保留来源全文字节、拒绝碰撞，并在相应授权下核验目标；不得覆盖归档。已核验分层名称中的普通旧 Markdown 仍可通过显式版本接管，并保留其原始字节。项目模式继续适用于非 Git 项目及已有本地用户，但不提供 worktree 共享。

源码修改不会更新正在运行的 MCP 进程。须按开发指南完成获准构建/安装，并通过实际暴露的宿主控制重启，之后才可声称新工具已上线。分别确认协商得到的工具清单和已配置后端状态；包测试本身不证明两者。

## 结构化更新

每个工具使用一个 `payload.request` envelope。提供准确绝对路径 `project_root`，任何 Memory 效果前须匹配配置 checkout。`plan_id` 是有界的小写安全 slug，追加到上述已配置 scope 的活动/归档命名空间。调用者不能选择任意 Memory 路径、仓库 ID 或归档目标。版本是完整存储 UTF-8 字节的 SHA-256。

创建时明确预期版本不存在：

```json
{
  "request": {
    "project_root": "/absolute/authorized/project",
    "plan_id": "example-task",
    "expected_revision": null,
    "request_id": "create-1",
    "records": [
      {"record_id": "goal-1", "kind": "goal", "text": "保留任务历史", "sources": ["user:request-1"]},
      {"record_id": "criterion-1", "kind": "criterion", "text": "原记录仍可追溯", "sources": ["user:request-1"]}
    ]
  }
}
```

把该 JSON 作为 `payload` 参数。后续更新必须使用返回版本，不能使用空字符串或 `null`。对应归档已存在时，不得以相同 ID 新建活动计划。已有旧 Markdown 计划尚无结构化历史时，将原内容作为不透明前缀保留，并以明确当前版本追加类型化记录。服务不会从散文推断目标或标准。版本冲突返回当前状态信息供审阅，不授权盲目重试。

记录包含稳定 `record_id`、`kind`、`text` 和 `sources`。支持目标、约束、需求、事实、决策、进展、标准、验证、blocker、解决记录、结果与限制等类别。替代须指定已有 `supersedes_id` 并提供 `supersedes_reason`，旧记录保持不变。解决记录指定 `resolves_blocker_id`；验证记录须有明确 outcome。准确 enum、边界和允许组合以暴露 schema 为准。

调用者不能提交替换全文、任意 patch 或 regex。服务追加已验证事件，保留完整原字节并检查历史链。更新/完成的 `request_id` 标识准确请求：相同重放不产生效果，复用同一 ID 携带不同内容会被拒绝。新内容须使用新 ID 和当前已审阅版本。

接管旧文档后，其原散文状态属于历史。已验证的最新事件及匹配回执提供当前生命周期状态；不得为显得最新而改写旧文档标题状态。

## 完成与归档

`task_plan_complete` 接收 `project_root`、`plan_id`、当前 `expected_revision`、`request_id`、最终结果/限制 `records`，以及包含 `criterion_id`、`verification_id` 的 `criterion_evidence` 对。每项当前标准须恰好出现一次，并引用仍有效的 `passed` 验证记录。证据缺失、失败、假设、不可用或仍有未解决 blocker 时不能完成。服务追加完成信息，绝不以最终结果替换累积内容。已完成计划拒绝继续更新；完全相同的完成重放仍不产生效果。

这验证的是输入证据结构，不证明其真实性、语义充分性或 Agent 宣布验收的权限；这些判断仍由任务获准 owner 负责。

`task_plan_archive` 仅接收 `project_root`、`plan_id` 和已完成计划的 `expected_revision`。在移动到对应命名空间时保留最终字节，核验目标内容相等及活动名称消失；活动条目存在且目标已占用时拒绝。绝不使用 Serena 会传播引用的重命名操作。重复请求须核实身份、完成状态和准确版本后，才可报告已有匹配归档，不能替换它。

## 保护与恢复边界

适配器使用实际 MemoryManager 对应的规范文件并执行其 ignored/read-only 策略。严格名称和路径检查拒绝路径穿越及命名空间/文件符号链接。POSIX 咨询锁在服务实例之间串行协调参与的生命周期工具调用；锁内通过版本检查、原子写入和完整读回拒绝过时或有损变更。输入/历史过大时失败，不截断或摘要化。

归档使用禁止覆盖的硬链接，再移除源名称，并检查身份和内容。两步之间失败时可能保留两个名称；服务报告需要协调，绝不删除或覆盖已有归档。写入后读回失败时，状态可能已改变。效果不明/需要协调结果须阻塞依赖工作；检查最后确认版本和当前名称，在既有授权下解决后再继续。不得假定回滚或盲目重放变更请求。

原始 Serena 工具、直接文件系统写者及不遵从锁的其他进程都在保护范围外，可以绕过新工具；服务不声称具有全局 CAS 或文件系统 ACL。需要独占强制边界时，宿主须限制其他写入路径。受信任 factory 同样不认证调用者或证明记录真实性。

这些工具不发起 OpenAI 或网络请求。配置和能力检查不证明真实宿主集成；临时存储/注入 manager 测试须与实际安装版 Serena 检查分别报告。锁定检查和测试分类见[开发指南](DEVELOPMENT_zh_cn.md)。真实适配器检查必须使用临时项目，绝不操作用户既有 Memory 或配置。

显式本地集成检查可从 `mcp/` 使用已安装兼容 Serena 环境的绝对 Python 可执行路径运行 `tests/unit_tests/serena_memory_smoke.py`。脚本从当前 checkout 加载仅依赖标准库的任务计划核心，使用实际 `MemoryManager`，仅创建临时项目/数据目录。除了旧内容保留、完成/归档重放、并发和原生策略检查，全局场景还须演练真实临时 Git 仓库/worktrees、按仓库隔离名称及共享 history。它独立于普通 pytest 收集，不安装依赖或加载用户配置。临时 Git fixture 不授予用户仓库历史操作权限。

开发集成已核验安装版 `serena-agent 2.1.0`。其他版本须满足适配器实际接口和路径检查；这不声称兼容每个 Serena 发行版。

## 相关文档

- [任务计划生命周期](../references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)
- [MCP 开发](DEVELOPMENT_zh_cn.md)
- [MCP 目录指令](AGENTS_zh_cn.md)
