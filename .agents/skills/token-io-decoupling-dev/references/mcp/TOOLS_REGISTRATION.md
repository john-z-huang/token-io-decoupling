# 独立 MCP 服务与 Codex 注册


Tools 与 workflow 可分别安装、注册和运行。[开发指南](DEVELOPMENT.md)负责检查与最终检验。各操作消费当前输入和资源状态，不要求工作流节点、先前工具或后续工具调用。

## 分发包与清单

| 分发包／可执行入口 | 固定清单 |
| --- | --- |
| `token-io-decoupling-tools` | 41 项操作：33 个上游助手、三个任务计划操作、两个 Memory 查询、候选 preflight、受保护输出物化及可选 tools_capabilities。 |
| `token-io-decoupling-workflow` | 11 个编译规则、导航、建议和结构评估工具。 |
| `token-io-decoupling` | 可选完整安装的管理命令，自身不提供 MCP 运行时。 |

两个运行时只依赖共享 core/transport，不依赖对方。编译资源和规则加载器属于 workflow；core 和 transport 不含规则。Tools 的运行时、CLI、schema 和 metadata 不加载 workflow 或 Coding Skill；workflow 不初始化或探测 tools 后端。

## 代码结构与注册模板

各运行时的 `server.py` 构造 Server 和已配置服务，再调用自身 `tool.py` 中的 `register_tools`。`token_io_decoupling_tools/tool.py` 定义全部 41 个工具，包含上游业务 callback、任务计划、Memory、preflight 和物化；`token_io_decoupling_workflow/tool.py` 独立定义 11 个工作流工具。

每项操作都使用 `token_io_decoupling_transport/tool.py` 中的同一个 `ToolDefinition` 模板。`ToolRegistrar.register_all` 检查完整固定清单，并通过唯一的 SDK `server.tool(...)` 调用注册。平铺签名、payload 信封、参数说明、annotation、结构化输出设置及操作授权检查均由定义数据表达。共享 transport 不导入任一运行时。参数校验错误脱敏位于 `token_io_decoupling_transport/server.py`；tools 不导入上游 Server，也不调用上游注册函数。

添加操作时，在所属模块实现业务逻辑，在所属 `tool.py` 添加定义，更新固定清单和本地说明，再验证公开契约。例如：

```python
ToolDefinition(
    name="task_plan_update",
    callback=lambda payload: task_plan_service.update(payload.request.model_dump(mode="json")),
    payload_type=TaskPlanUpdatePayload,
)
```

原生 callback 保留已有平铺参数；payload callback 保留已有信封。可选的调用者上下文和角色检查只用于自身需要这些约束的操作，不增加工作流前置条件。

## 按服务选择 setup

每个运行时分发包拥有自己的 console script，不安装管理包也可注册自身：

```sh
/absolute/path/to/token-io-decoupling-tools setup codex
/absolute/path/to/token-io-decoupling-workflow setup codex
```

可选管理命令接受 `setup codex --server tools|workflow|both`，默认为 `both`。追加 `--dry-run` 只读取配置并预检所选配置段，不发现工具或写入。实际 setup 只解析所选分发包的入口 metadata 与可执行路径，检查准确工具清单，原子更新所选注册项。未选和无关配置段、已有启用／禁用状态、审批、超时、cwd 及额外环境名称均保留。所选配置无效或检测到并发变化时拒绝覆盖。

完整 `uv tool install` 需通过 `--with-executables-from token-io-decoupling-workflow --with-executables-from token-io-decoupling-tools` 暴露依赖拥有的脚本；单独安装运行时则直接暴露自己的入口。参见[安装指南](../../../../../INSTALL.md)。

## 操作与配置边界

Tools 复用固定版本 dev-workflow-standards-tools 的 schema、annotation、callback 和输入审核，共享 transport 保留相同的参数错误脱敏。公开工具说明由本地操作契约提供，不附加上游服务的工作流指令与调用顺序。不要求先调用诊断、路由或内容生成工具。

任务计划和 Memory 仅由 tools 提供。`--task-plan-factory`、`--compliance-factory` 和 `--output-materializer-factory` 属于 tools 启动选项；操作者代码从 token_io_decoupling_tools 导入相关类型。Workflow 拒绝迁移后的旧选项。Wire payload 及现有计划／Memory 数据保留；重载旧安装时更新 factory 导入和 enabled_tools/disabled_tools 筛选。

当前资源检查保留在各操作内：版本保护计划更新；完成／归档校验已有计划状态；物化校验已有 prepared artifact、可信逐次身份与分配、独立操作者授权、固定路径、基线、新鲜 preflight 及写入时权限。已有资源不证明先前工具调用或工作流放行。缺少物化配置时仍不可用。

本地工具不需要 API 配置。API 操作使用必需的非空进程 OPENAI_API_KEY 与 OPENAI_BASE_URL、固定模型和外发审核；缺配置只影响依赖它的操作。Setup 仅转发变量名，不转发值；tools 另转发 OPENAI_TIMEOUT_MAX_RETRIES。发现和哈希不授予权限。

## 验证

测试验证清单互斥、拒绝 sibling/admin 导入、真实独立 wheel 安装、直接 stdio 调用、单服务注册、配置保留、脱敏和受保护写入拒绝。归档测试覆盖五个分发包、core 不含规则资源、批准的 workflow/Skill 批次及独立重建。按顺序的[最终检验](DEVELOPMENT.md#codex-app-server-最终查看)执行全部适用检查，在临时 uv 目录构建安装当前完整 wheel 集合，再用新的只读 Codex CLI 检验，模型 turn 为零，不修改真实用户配置。
