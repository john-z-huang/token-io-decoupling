# Worker 输出材料化

[English](OUTPUT_MATERIALIZATION.md) | [简体中文](OUTPUT_MATERIALIZATION_zh_cn.md)

本文负责 `materialize_decoupled_output` Worker 工具契约：prepare、inspect、apply 生命周期，可信操作员授权，有界模板，结果解释与恢复边界。[MCP 可执行程序与注册指南](TOOLS_REGISTRATION_zh_cn.md)负责当前可执行程序清单与 Codex 注册；[MCP workspace 开发指南](DEVELOPMENT_zh_cn.md)负责安装和启动 factory 索引。

## 目的与权限

该工具允许符合条件的 Worker 在项目之外准备有界输出产物、检查产物，并通过已配置项目根目录应用明确授权的文件集合。它仅供 Worker 使用，由 `token-io-decoupling-tools` 可执行程序暴露。工具发现、已验证的 Worker 绑定、Worker 状态存储守卫、`WORKER_WRITE` 和 assignment 本身都不能授予项目文件写权限。

每次操作都重新读取已验证的 Worker 材料化上下文及独立的可信操作员授权。上下文必须标识当前 Worker、Root、项目、allocation、角色、输出类别、已释放 slice 和已确认 assignment hash。授权必须有效，并与该绑定、固定项目和产物目录身份、policy 版本、精确路径、操作及允许模板相符。授权变化或撤销、assignment 变化、上下文缺失或安全能力不可用时必须失败关闭。授权来自可信操作员代码，绝不来自请求 payload。

首版只支持 `Primary Output` 角色，输出类别可为 `code_configuration` 或 `skill_instructions`。不支持普通文档、Documentation/Comments & Git Operations 角色及其他角色/类别。每条路径和操作必须同时获已确认 assignment 与独立授权允许。本工具保持 Skill 的职责归属和既有 Worker 输出类别。

操作员通过显式可信启动 factory 配置绝对项目根目录和产物根目录。factory 返回 `OutputMaterializerConfig`，其中包含这两个根目录和 `grant_provider.current_grant()` 方法。Server 使用与现有只读合规工具相同的项目根目录及合规预检服务。缺少 factory、服务、授权、安全目录访问或必要预检时，工具报告不可用；不会猜测路径、创建默认宿主或目录，也不会修改用户配置。产物根目录应保持私有，并在物理上与项目根目录分离。启动时会拒绝词法路径重叠或打开后目录身份相同的根目录，并且逐段验证路径时不跟随符号链接；工具不会识别所有物理别名（例如 OS bind mount），这由操作员负责。

## 请求生命周期

MCP 调用包络为 `{ "payload": { "request": { ... } } }`，由 discriminator 选择三种操作之一：

| 操作 | 请求数据 | 效果 |
| --- | --- | --- |
| `prepare` | `files`，以及可选的 `outbound_data_permitted`（默认 `false`） | 校验权限和模板、渲染候选内容，然后在产物区域保存不可变候选与 manifest；不写项目文件。 |
| `inspect` | `prepared_id`、`expected_manifest_hash`、`file_index`，以及可选的 `offset`（默认 `0`）和 `max_chars`（默认 `2048`） | 重新校验授权和 manifest 后，读取已准备文件的有界范围。 |
| `apply` | `prepared_id`、`expected_manifest_hash` | 重新校验权限、候选完整性、基线和整批预检，再应用符合条件的文件；不重新生成内容，也不调用 Responses。 |

每个已准备文件包含规范化相对叶路径、`operation`（`create` 或 `replace`）、基线（create 使用 `absent`，replace 使用 SHA-256）及一个 version-1 模板。请求路径必须同时获已确认 assignment 和当前授权允许。路径必须精确指定；不支持创建目录、glob、绝对路径、路径穿越或 `.git` 等仓库控制数据。

`prepare` 返回 `status: prepared`、不透明的 `prepared_id`、`manifest_sha256`、逐文件内容 hash/字符数/字节数和最多 256 字符的预览，以及 inspect 说明。`inspect` 返回有界内容片段和分页字段，包括偏移、最大长度、总字符/字节数、hash、下一偏移及文件是否读取完成。调用方必须保留 manifest hash，并在后续 inspect 和 apply 中原样传回。hash 不匹配或产物被篡改时属于冲突，不能当作新鲜输出使用。

## 模板、限制与可选排序

Version 1 支持三种有限模板：

- `literal_text` 接受有界输入文本，并将其原样作为候选内容。
- `json_document` 接受有界 JSON 文本，在规范序列化（`ensure_ascii=false`、键排序、紧凑分隔符并以一个换行符结尾）前拒绝重复对象键和非有限数字，并校验最大嵌套深度为 16、总节点数不超过 4,096。它不是开放式递归 JSON schema。
- `fact_markdown` 接受有界标题 ID/标题，以及事实 ID、标题引用和源文本。由本地代码将这些值渲染为 Markdown。默认保持事实的源顺序。

固定上限为 1–16 个文件、每条路径 512 字符、每个文本字段或渲染文件 131,072 字符、整批渲染候选内容合计 524,288 UTF-8 字节。JSON 嵌套深度最多为 16，总节点最多 4,096 个。Fact Markdown 最多 8 个标题和 64 条事实；单条事实最多 8,192 字符。发出 Responses 请求前会拒绝含换行的标题。Responses 输入预算为 system instructions 与输入文本合计最多 48,000 字符，不含固定 SDK schema 和 JSON framing；输出最多 4,000 tokens。每次检查最多返回 8,192 字符，默认 2,048。渲染后实现还会重新校验大小。这些分别是字符、字节和 token 上限，不是估算值。

对于 `fact_markdown`，操作员授权可以允许 `ordering: "responses"`。该可选分支要求在该次 prepare 请求中设置 `outbound_data_permitted: true`，作为单次调用断言；它不授予文件或网络权限。每次请求都显式读取并使用进程环境中非空的 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`，只使用 `gpt-6-luna` 和 medium reasoning effort，超时为 30 秒且不自动重试。生产配置固定使用 OpenAI client；操作员 factory 不能覆盖 client。模型接收有界的已提供事实，只能返回这些事实 ID 的排序。本地代码会拒绝未知、重复、遗漏或其他无效 ID，并渲染原始文本。模型不能创建散文、代码、文件或权限。缺少配置、拒绝、超时、不完整或格式错误的输出、预算失败都会停止准备且不生成候选；API 错误详情不会返回给工具调用方，也不会回退到自由文本。apply 操作绝不调用 API。工具结果不包含 API usage；usage 缺失不能解释为零。

## Apply 检查与文件系统边界

写入前，apply 要求整个候选文件批次通过现有合规预检，policy version 为 1，且预检使用同一固定项目根目录。`fail`、`unknown`、缺失、过期或不可用的预检都会阻止整批写入，包括所有文件已相同的重放。已安全验证为匹配候选的文件会以 `replace` 和候选 SHA-256 基线投影给预检；待应用文件保留原 manifest 的操作和基线。该投影只是只读预检输入，不改变原始 manifest 或授权中的写入许可。apply 还会重新检查每一条当前授权、assignment、路径许可、候选 hash 和基线。它不会执行或导入目标仓库中的代码。

项目和产物根目录由操作员配置并安全打开。读取会拒绝符号链接、非普通文件或不稳定文件。写入使用同目录临时文件和逐文件原子发布；create 使用禁止覆盖的发布方式，replace 重新核对预期基线并回读结果。必须已存在父目录；apply 不会创建目录。实现不会提升文件权限。

协作锁只会串行化使用同一服务的参与者，不提供对无关写入者的全局 compare-and-swap。最后一次检查之后，外部写入者仍可能发生竞态。多文件批次不具备集合原子性：出错时可能已有部分文件应用。服务不承诺可靠自动回滚。

## 结果与恢复

apply 完成时，持久回执包含版本、prepared ID、manifest hash、批次状态及逐文件状态，可带 `actual_sha256`。逐文件状态为 `applied`、`already_identical`、`conflict`、`not_attempted` 或 `uncertain`；批次状态为 `applied`、`already_identical`、`partial`、`conflict` 或 `uncertain`。预检或完整性门禁也可能返回 `status: blocked`、`reason_code`、当前逐文件分类及预检状态；这不是表明文件已应用的回执。决定后续操作前检查逐文件 hash 与实际状态。

- prepare 结果不确定且未收到 ID/hash 时，不要臆造标识，也不要假定调用具备幂等性。重复 prepare 可能创建新候选，也可能再次调用排序 API。应将结果视为未解决，并由操作员按配置的产物存储流程管理可能的孤立产物；该工具不提供产物列表操作。
- inspect 结果不确定时，先确认 prepared ID 与预期 hash 仍有效，再重复相同的有界读取。
- apply 结果不确定或回执为 partial 时，读取当前文件并与候选、基线及持久回执比较。对同一 manifest，内容匹配候选表示已应用且绝不重写。未记录写入尝试的文件（`not_attempted`）在权限和新鲜预检仍通过时，可以按原始基线继续应用。若先前回执记录为 `applied`、`already_identical` 或 `uncertain`，但当前内容不再是候选，即使恢复成原始基线也必须报告冲突；这可保留用户后续撤回，并处理结果读取不确定时可能已写入的情况。其他内容也属于冲突。绝不覆盖外部变更，也不假设能够回滚。若仍希望再次应用，应基于当前事实审阅并准备新候选。
- 若授权、assignment、预检、根目录身份或 manifest 已变化，应在当前事实下重新准备并审阅候选；不要复用过期批准或 hash。

## 相关文档

- [MCP workspace 开发指南](DEVELOPMENT_zh_cn.md)
- [候选内容合规预检](CANDIDATE_COMPLIANCE_zh_cn.md)
- [MCP 目录指令](AGENTS_zh_cn.md)
