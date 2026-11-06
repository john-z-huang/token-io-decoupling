# 项目 Memory 文件尾读与写入检查

[English](SERENA_MEMORY_TOOLS.md) | [简体中文](SERENA_MEMORY_TOOLS_zh_cn.md)

本文档负责两个只读 Memory 工具的输入、本地路径规则、返回值和限制。它们使用 Python 标准库读取当前项目文件，不依赖 Serena-Agent、MemoryManager、独立的 Serena Python 环境、Shell 命令或 helper 进程。

## 工具

两个工具由 `token-io-decoupling-tools` 可执行程序暴露，直接接收参数。

| 工具 | 参数 | 结果 |
| --- | --- | --- |
| `serena_memory_tail_read` | `memory_path`、`tail_lines` | 有界文件尾部及行数/范围信息。 |
| `serena_memory_write_check` | `memory_path`、`changed_content`、`tail_lines` | 预期文本是否出现在该尾部；未匹配时说明原因。 |

从目标项目根目录启动 Codex。MCP 进程在启动时捕获工作目录作为项目根，只读取该目录下的 `.serena/memories/`。它不会搜索父级或兄弟目录。Memory 目录和所请求的文件必须已存在；缺失时返回非成功结果，不创建任何内容。

`tail_lines` 必须是 0 到 10000 的整数。设为 0 时返回空内容，但仍可返回行数。所选尾部和 `changed_content` 各最多 64000 字符；`changed_content` 必须非空。

## Memory 名称

`memory_path` 可以带可选的 `mem:` 前缀。前缀后的内容是 `.serena/memories/` 内的相对名称，支持子目录。名称没有 `.md` 后缀时，工具会补上该后缀。

示例：

```text
plans/PLAN-example
mem:plans/PLAN-example.md
```

拒绝绝对路径、盘符路径、反斜杠、越界路径、所有符号链接，以及全局或外部 Memory 引用。子目录之间使用 `/`。`mem:` 前缀不会选择其他项目或存储区域。

## 读取与检查

工具使用 Python 标准库处理本地文件和路径。UTF-8 文本流迭代保留 LF、CRLF 或 CR 行尾及文件末尾终止符。行数按 Python 文本流迭代计算，尾随终止符后不会虚增一行。结果包含 `total_lines`、`returned_lines` 和返回范围。目录或文件缺失、路径无效或越界、内容不可读时，返回非成功结果。工具不创建 Memory 目录或文件，也不调用 Shell 命令或子进程。

`serena_memory_write_check` 只执行一次相同的尾读，并检查 `changed_content` 是否为返回文本中区分大小写的字面子串。它返回精简匹配元数据，不回显完整尾部或预期文本。它不会写入文件。匹配只表示观察到的尾部包含该文本，不能证明发生了新的写入，也不能证明此后文件未改变。

Windows 运行尚未经过独立验证。

## 相关文档

- [MCP 开发指南](DEVELOPMENT_zh_cn.md) — 安装和 workspace 工具。
- [MCP 可执行程序与注册指南](TOOLS_REGISTRATION_zh_cn.md) — 当前可执行程序清单和 Codex 注册。
- [任务计划 Memory 生命周期](../../../../../instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md) — 内容保全和归档要求。
