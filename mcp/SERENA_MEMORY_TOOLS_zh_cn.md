# Serena Memory 尾读与写入检查

[English](SERENA_MEMORY_TOOLS.md) | [简体中文](SERENA_MEMORY_TOOLS_zh_cn.md)

本文档负责两个只读 Memory 工具的输入、后端绑定、返回值和限制，不替代 Serena 访问策略及 Skill 对完整内容保全与归档的要求。

## 工具

两个工具属于 `workflow` profile，直接接收参数，不使用 `payload` envelope。它们只在本地读取文件并匹配字符串，不调用模型/API，不写入 Memory、目录或工作流状态。

| 工具 | 必需参数 | 结果 |
| --- | --- | --- |
| `serena_memory_tail_read` | `memory_path`、`tail_lines` | 有界尾部文本、规范身份及行数/范围证据。 |
| `serena_memory_write_check` | `memory_path`、`changed_content`、`tail_lines` | 精简的 `success`/原因及窗口证据，不回显预期文本或尾部全文。 |

`memory_path` 是最多4096字符的非空白字符串。`tail_lines` 是0到10000的严格整数，不接受布尔值、负数或数字字符串。0表示只请求行数元数据，内容为空。所选尾部和 `changed_content` 各最多64000字符；尾部超限时明确失败，不静默截断。`changed_content` 不得为空。

例如，在获准追加 Memory 后：

```json
{"memory_path":"mem:plans/PLAN-example","tail_lines":12}
```

快速字面检查该追加内容：

```json
{"memory_path":"mem:plans/PLAN-example","changed_content":"Validation passed.\nNext: review.","tail_lines":12}
```

第二个操作只调用一次相同尾读实现，再检查 `changed_content` 是否为返回文本的字面子串。匹配区分大小写，不使用正则或额外归一化。

## 使用 uv tool Serena 的默认安装

已有通过 `uv tool` 安装的 Serena，且目标项目已配置时，运行仓库的正常安装器：

```sh
bash /absolute/path/to/token-io-decoupling/scripts/install-codex-mcp.sh \
  --serena-project-root /absolute/path/to/your-project
```

脚本安装/更新此 MCP 并运行 `setup codex`。Setup 发现 `<uv tool dir>/serena-agent/bin/python`，探测读取后端，然后仅在 workflow profile 的 `start-mcp-server --profile workflow` 参数后保存：

```text
--serena-project-root /absolute/path/to/your-project --serena-python /resolved/Serena-env/bin/python
```

保存真实虚拟环境解释器路径，不把最后的符号链接解析到基础 Python。可用 `--serena-python /absolute/Serena-env/bin/python` 覆盖发现结果。已有安装也可直接运行 `token-io-decoupling setup codex --serena-project-root /absolute/path/to/your-project`，无需自编 factory 或手改配置。未提供新绑定参数时保留可识别的已有绑定；改变项目/解释器要求 `--replace`。Dry-run 延后发现/探测并显示解释器占位。

Setup 后重新加载 workflow MCP 服务。`SERENA_HOME` 只转发名称、不保存值；Serena 使用自定义 home 时，应让 Codex 环境提供相同值。项目须显式指定，不从安装源码或当前目录推断。新注册省略全部绑定参数时保留旧的未配置模式。

Serena 与此 MCP 的固定依赖版本不同，因此后端使用已有 Serena Python 环境运行固定本地 helper，仅交换有界的能力/尾读/写入检查 JSON。MCP 环境不导入或安装 Serena。helper 安全读取已有 `serena_config.yml`、`project.yml` 和可选 `project.local.yml`，遵守配置数据目录与合并后的正则策略，不调用会迁移/保存的配置加载器，不执行激活命令、Agent、LSP、模型或 API。必需 YAML 须为普通非符号链接文件，配置/Memory 目录须已存在；缺失或不支持时返回不可用，不初始化或迁移。

### 高级嵌入与工厂

兼容的可信嵌入方仍可用已有真实 Manager 提供 `create_server(serena_memory_service=SerenaMemoryReadService(manager, project_root))`；启动器也可导入运维方维护的无参工厂：

```sh
token-io-decoupling start-mcp-server --profile workflow \
  --serena-memory-factory operator_memory:build_reader
```

该 callable 必须返回绑定到目标 Manager/项目的 `token_io_decoupling_workflow.serena_memory.SerenaMemoryReadService`。此高级嵌入的兼容性和初始化由运维方负责。工厂选项加载可信代码，与隔离项目/Python 参数对互斥，不接受在工具参数、`setup` 或 `skills` 命令中传入。两种模式均不发现另一进程的活动项目，也不初始化 Memory 根目录。

未配置任何后端时，两工具仍可发现，但返回 `unavailable`，不导入 Serena 或探测 Memory 路径。使用前检查 `workflow_capabilities` 的 `serena_memory_reads`、`serena_memory_binding` 及 `capability_details.configuration.serena_memory_reads` 字段。这与 `--task-plan-factory` 独立，配置其中一个不会自动配置另一个。

## 名称、路径和访问策略

接受的输入包括 `notes/design`、`notes/design.md`、`mem:notes/design`、`mem:global/notes/design` 等 Serena 逻辑名；对应的已有文件路径可使用绝对地址，或相对于显式绑定项目根的地址。文件路径必须能映射回 Manager 实际配置的项目/全局 Memory 根内。自定义数据目录取自该 Manager，不硬编码假设 `.serena/memories`。

映射后应用 Serena 名称规范化和 ignored-memory 策略，包括 Serena 正则 `fullmatch` 语义。被忽略的 Memory 不可读；只读 Memory 可以读取，因为工具不执行写入。传入路径不会使任意项目文件变得可读。读取器拒绝路径穿越、根目录外路径、符号链接及非普通文件；符号链接限制比 Serena 一般路径行为更严格。解析时不调用会创建缺失目录的帮助方法。

读取器使用 Manager 的 encoding、有界流式读取及受保护文件描述符。文件缺失、绑定不可访问或变化、缺少安全打开能力、解码失败、输出超限或读取期间检测到变化时，明确返回非成功结果，不返回部分内容。这些检查不提供针对其他写者的全局锁或原子比较交换。

## 解释结果

尾读成功后返回 `content`、`total_lines`、`returned_lines`、`start_line`、`end_line`、`ends_with_newline` 及规范 Memory/路径身份。以 LF（包括 CRLF）分行，返回文本保留解码后的行分隔符与尾换行。非空行范围从1计数；最后一行即使没有换行也计为一行，末尾换行后不虚增一行；空文件和零行请求返回零行，起止边界为 `null`。使用这些字段前先检查 `status` 和 `reason`。

Write Check 的 `success: true` 仅说明预期文本存在于当前观察到的尾部。写入前已存在的文本也可能匹配；正确改动位于窗口之外，或窗口比预期文本短，也可能匹配失败。读取器不可用表示尚未核验，不证明先前写入失败。结果不证明新写入确实发生、语义正确、前文未变、历史完整或并发安全。

仅在适用 owner 允许时，用这些工具进行有界回忆和补充检查。它们不能替代必需的完整存储内容比对、revision 冲突协调或归档等同性检查。

## 跟踪追加行

读取后记录 `total_lines` 和行边界状态。只有独立证据已确认旧前缀未变、且仅追加完整新行时，总行数之差才可用于选择新增尾部。对未换行的最后一行继续追加可能不增加行数；中间修改、删除或重写也可能使计数不变或产生误导。仅凭计数不能建立纯追加前提，也不能还原一般 diff。

## 本地集成检查

常规 MCP 测试覆盖服务、直接参数 wire schema、后端/工厂及 profile 工具清单。在 `mcp/` 开发环境中，独立离线 smoke 可复用已有 uv tool Serena 而不更新它：

```sh
uv run --no-sync python tests/support/serena_installer_smoke.py \
  --serena-python "$(uv tool dir)/serena-agent/bin/python"
```

smoke 选择临时 `SERENA_HOME`，只创建临时项目/Memory fixtures，使用固定 helper 和真实 Manager，再核验配置/数据快照未变；不启动模型、不修改用户配置、不访问用户 Memory，也不安装 Serena。普通 pytest 不收集该脚本。[有序最终检查](DEVELOPMENT_zh_cn.md#codex-sdk-最终查看)另提供显式真实安装器检查，位于普通检查及临时安装通过之后、最终零轮次 SDK 查看之前。

## 相关文档

- [MCP 开发指南](DEVELOPMENT_zh_cn.md) — 安装、profiles和必需最终检查。
- [任务计划 Memory 生命周期](../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md) — 完整保全和归档要求的权威规则。
