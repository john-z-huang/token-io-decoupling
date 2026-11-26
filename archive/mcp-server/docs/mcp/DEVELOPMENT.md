# MCP 开发指南

本页记录旧服务的开发和测试流程。 [归档说明](../../README.md)

服务面向 Pi Coding Agent，仅提供 `token-io-decoupling-tools` 一个可执行程序。无参数启动 stdio；`--help`、`--version` 为诊断入口，`skills install` / `skills update` 管理 Skill。

## 安装与更新

构建安装、更新 Skill 快照和重载 Pi 的步骤统一维护在 [安装与使用](../../INSTALL.md)。

### 在 Pi 中注册

仅注册 `token-io-decoupling-tools`，使用 stdio，默认不传启动参数。通过 `uv tool dir --bin` 找到该程序的绝对路径，并登记到 Pi 实际使用的 MCP 配置。安装脚本不会替用户修改配置；需要读取项目 Memory 时，请核对 MCP 进程的[实际启动目录](SERENA_MEMORY_TOOLS.md#工具)。

## 工具边界

34 个工具的权威清单为 `mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/server_tools.py`。其中 29 项来自固定版本的上游开发工具；其余是规则上下文、合规预检、两项 Serena Memory 只读工具和输出材料化。本服务不注册 Codex 专用会话事实与会话决策工具，也不提供工作流调度、检查点执行或任务计划管理；见 [工作流架构](../WORKFLOW_ARCHITECTURE.md)。

### 调用方上下文

标准 stdio 启动、工具发现、规则查询和 Memory 尾读都不能认证调用方或授予写入权限。可选的候选预检和输出材料化由可信操作员分别通过 `--compliance-factory` 与 `--output-materializer-factory` 配置，详见[预检契约](CANDIDATE_COMPLIANCE.md)和[写入契约](OUTPUT_MATERIALIZATION.md)。配置 factory 不等于完成身份绑定；受保护写入仍要求可信 `BindingProvider`、当前任务分配和独立操作授权。

只有可信集成显式启用调用方匹配并注入 `BindingProvider` 时，才检查请求元数据的 `threadId` 是否等于已验证会话 ID。`sessionId`、自报角色和其他请求字段不能选择身份或权限；不能用 Pi 会话 ID 伪装可信绑定。

## 包结构与验证

`core` 保存基础契约与只读规则资源；`transport` 提供统一注册机制；`tools` 保存通用服务与按服务器绑定的 callback；根分发包保存唯一 CLI、服务组装、集中工具定义和 Skill 安装器。

### 固定工具模板与集中注册

所有工具使用 `token_io_decoupling_transport.registration.ToolDefinition` 模板，由 `mcp/src/token_io_decoupling/tool_registry.py` 中的 `tool_definitions()` 集中声明，`register_tools()` 先校验完整清单，再逐项调用唯一的 `ToolRegistrar.register()`。`server.py` 只负责组装服务；业务模块不调用 MCP 装饰器，上游依赖只提供业务 callback 和说明元数据，不再通过其 `register_*` 注册工具。

初始化响应只携带 Pi 服务共用的调用边界。单项工具的参数、返回值和副作用以实际发现的元数据为准。服务器在 SDK 调用边界统一屏蔽参数校验错误中的输入值。

新增或调整工具时，统一使用以下模板（字段按既有调用契约选择）：

```python
ToolDefinition(
    name="tool_name",
    callback=callback,
    description="工具的用途、输入、输出与安全边界说明",
    annotations=annotations,
    parameter_descriptions=parameter_descriptions,
    payload_type=None,
    enhanced=False,
    role=None,
    structured_output=None,
)
```

- 平铺参数工具：`payload_type=None`，从 callback 的类型签名保留参数、默认值和校验；`parameter_descriptions` 如提供，必须与全部参数名严格对应。Memory 工具保留严格类型约束与只读 annotations。
- payload 工具：设置 Pydantic `payload_type`，保持 `payload` envelope 和 JSON 校验。受保护材料化必须设置 `enhanced=True, role="worker"`，保留可信请求上下文、角色和授权检查；普通平铺工具不引入该绑定机制。
- `structured_output=None` 保持 SDK 自动推断，现有本地工具使用 `False`。模板统一不意味着改变现有 wire 格式、返回值或错误脱敏规则。
- 清单必须与 `core/server_tools.py` 完全一致；未知名称、重复定义和清单漂移会报错，不允许静默过滤。调整公开清单属于接口变更，不能只改注册文件绕过契约。
- `tests/unit_tests/test_tool_registry.py` 将 34 项完整发现元数据与改前 fixture 比对，并检查注册失败、参数说明和多服务器配置隔离。不要为让测试通过而盲目重生成 fixture；有意接口变更应单独审阅。

在仓库根目录开始。先生成源码规则查询和测试所需的 `skill/`，避免在依赖已缓存、`uv sync` 未重新构建包时缺少产物。

```sh
uv run --locked --script scripts/compile-reference-dsl.py
cd mcp
uv sync --group dev
uv run pytest tests/unit_tests tests/mock_api_tests
uv run ruff check src packages tests
uv build --all-packages --wheel
```

从仓库构建 MCP 包时，构建钩子先从 `rules/` 生成 Skill 文档和规则摘录。独立源码分发包携带构建所需的快照。

普通测试不运行真实 API。可选模型请求须另行获得授权，并由 MCP 进程读取 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`；不得记录凭据或擅自外发内容。
