# Token I/O Decoupling


提供可独立使用的开发、任务计划和 Memory MCP 工具，以及可选的编译 Coding 工作流。每个工具按自身操作输入调用，不要求工作流节点、模式、检查点、先前工具调用或后续调用。资源校验和宿主授权在当前操作内执行。

## 仅安装 tools

在源码 checkout 根目录安装 tools 分发包及两个共享依赖：

```sh
uv tool install --force --reinstall --managed-python --python 3.14 \
  --with ./mcp/packages/token_io_decoupling_core \
  --with ./mcp/packages/token_io_decoupling_transport \
  ./mcp/packages/token_io_decoupling_tools
"$(uv tool dir --bin)/token-io-decoupling-tools" setup codex
```

只安装和注册 tools，不安装 workflow 包、编译规则或 Coding Skill。重载该 MCP 服务后，可按公开 schema 选择任意工具；`tools_capabilities` 是可选的依赖诊断。本地工具不需要 API 配置；API 操作及计划／物化后端分别报告自身缺失的配置。

Tools 服务提供 41 项操作：33 个上游开发助手、任务计划更新／完成／归档、两个 Memory 查询、候选 preflight、受保护输出物化及诊断。Memory 查询读取服务启动项目的 `.serena/memories`；计划存储另行配置。受保护写入保留身份、独立授权、路径、基线和 preflight 校验。已有资源状态可由任意兼容写入方提供。

## 可选 workflow 与完整安装

独立的 workflow 包提供 11 个事件检查、规则、建议和评估工具。使用相同的两个 `--with` 依赖与 `./mcp/packages/token_io_decoupling_workflow` 单独安装，再通过 uv tool bin 目录中的 `token-io-decoupling-workflow setup codex` 注册。它不导入或安装 tools。

Agent 根据精简的单代理或多代理指令及六类事件 Hook 动态选择执行路径。`workflow_check_event` 提供当前规则、报告结构缺口，并可显式请求模型建议。任务和运行时状态由 Agent 自行保留在上下文中；workflow 不提供状态存储、恢复日志或阶段推进 API。[可选原生 Hook](INSTALL.md#可选-workflow-事件与原生-hook) 提供薄的 Codex 适配入口。

工作流指令只维护简体中文单源，文档使用无语言后缀的文件名。查询保留 `language` 字段作为契约标记，仅接受 `zh_cn`，省略时也使用中文。

需要完整分发包及可选 Coding Skill 时：

```sh
bash scripts/install-codex-mcp.sh --mcp
bash scripts/install-codex-mcp.sh --skills install
```

已有受管 Skill 使用 `--skills update`。脚本无参数运行仅打印帮助；参数组合、预览与恢复见[安装与更新](INSTALL.md)。`--mcp` 注册两个服务；`token-io-decoupling setup codex --server tools` 或 `--server workflow` 可只选择一个。加载 Coding Skill 表示明确采用该工作流；仅使用 tools 的任务不加载它，也不进入其路线。

MCP 继续支持本地 Codex CLI，包括其本地 app-server 路径。其他 Agent 可消费生成的工作流文档，但不因此成为直接 MCP 客户端。指令、哈希和诊断不能授权副作用或证明完成。

## 仓库边界

| 部分 | 职责 |
| --- | --- |
| `mcp/packages/token_io_decoupling_tools` | 独立工具、计划、Memory、preflight 和受保护物化。 |
| `mcp/packages/token_io_decoupling_workflow` | 独立工作流运行时及批准的编译规则资源。 |
| `mcp/packages/token_io_decoupling_core` 与 `token_io_decoupling_transport` | 共享契约、守卫、传输和按服务选择的 setup；不包含工作流资源或服务导入。 |
| `mcp/` 根分发包 | 兼容的完整安装、管理入口及可选 Skill ZIP。 |
| [私有开发 Skill](.agents/skills/token-io-decoupling-dev/SKILL.md) | 仓库指导、测试和发布检查。 |
| `instruction-compiler/` | 私有作者政策与确定性编译。 |

私有开发文件和编译器源不进入产品归档，禁止手工编辑生成资源。参见[安装与迁移](INSTALL.md)。
