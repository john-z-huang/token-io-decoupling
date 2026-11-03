# 运行时指令编译器契约

[English](compiler-contract.md) | [简体中文](compiler-contract_zh_cn.md)

本参考负责开发编译器的输入、来源、验证和发布契约。固定 manifest 和版本化资源包含当前已审核的映射。后续映射变更须经 Root 批准后才能发布。

## 版本与来源单元

Manifest 格式为 `token-io-runtime-instructions-manifest/v1`；资源格式为 `token-io-runtime-instructions/v1`，整数 `compiler_version` 为 1、policy contract 为 2、旧 context-index 为 1。未知版本必须失败。Entry 使用 `(tool_id, node_id, stage_id, locale)` 作键；不同 tool 或 node 可使用相同 stage。

每组双语 SourceUnit 将稳定 ID 绑定到仓库相对 Markdown 路径、唯一标题、原始来源 SHA-256 和提取段落 SHA-256。Runtime entry 选择来源单元，并为动作及每个分支的触发、动作、通过和失败提供精确来源引文选择器；引文 occurrence 从零开始。SourceUnit 是来源材料，不伪造可调用分支。真实项目分支还要绑定原样的 `legacy_branch` 值；项目门禁逐 node 和语言核对全部合法分支覆盖。

`legacy_bindings.fragments` 与 `legacy_bindings.owners` 将稳定旧 ID 映射到规范单元。多个显式别名可以指向相同的双语路径和标题；重复 ID 或未解释的重复来源选择器必须失败。真实项目门禁核对全部 17 个 node、44 个 fragment、8 个 owner、3 个可选绑定、默认 fragment、原合法分支和实际索引依赖图。产物保留已验证的 registry node 元数据、索引默认项与 fragment 依赖、owner 路径、可选绑定及其来源哈希，供未来消费者使用；本阶段不切换产品 loader。

[节点和分支映射](node-mapping_zh_cn.md)为稳定的 context 节点记录有源的触发、动作、通过和失败条件。它映射既有权威，绝不将只读查询变成效果；每个适用闭包仍须携带原政策材料及来源记录。

每个可调用的 `rules_get_context` entry 都必须独立覆盖所属 node 的全部原合法分支与默认项；不得跨 entry 拼凑分支。`owner_views` 单独将五个旧 delegation policy owner 的两种语言绑定到显式来源根。这些 view 不是可调用工具，不伪造动作或分支。每个 view 预计算完整依赖闭包、来源记录和内容哈希，并与 entry 使用相同的版本、来源哈希、预算、provider 段和内部回指检查。Owner 或 entry 必须显式包含必需的定义根；编译器绝不自动补齐。

## 引用与语义依赖

每条摘录中的实际 Markdown 链接必须使用原始 token 与 occurrence 恰好分类一次。`required` 与 `conditional` 链接进入完整执行闭包；条件链接还包含稳定条件 ID 和精确来源触发语。`navigation` 仅定位材料，不进入闭包。`internal_already_included` 是定义回指，其目标和 `included_in` 单元必须已经位于最终 entry 闭包。导航可以成环；必需边和条件边不可成环，不能折叠或静默重新分类。

独立的 `semantic_dependencies` 数组表示没有对应 Markdown 链接的执行依赖。Markdown 来源边使用 `provenance.kind: markdown_quote` 和其自身 SourceUnit 中的精确选择器；条件边还需在同一单元提供 `condition_id` 与触发选择器。旧索引边使用 `provenance.kind: legacy_index_dependency`、实际 fragment ID、固定索引 SHA-256 和准确的 `/fragments/<index>/dependencies/<index>` JSON pointer。编译器对照实际索引核验 pointer 与别名绑定，不为仅由 JSON 声明的依赖伪造 Markdown 链接或引文。两类边均进入闭包、循环检测、来源记录、哈希和预算检查。

本地 Markdown 目标相对于来源解析，目标必须存在，锚点必须有效且位于固定根目录内。符号链接遍历、路径越界、缺失目标、无效锚点以及目标单元的来源路径或段落不匹配均失败。外链只作为数据，不发起请求。无法可靠判定的标题锚点可以拒绝，不得猜测。独占一行的语言切换仅在本地路径分别为英文文件和对应 `_zh_cn.md` 镜像时豁免。

## 完整性与预算

规范 JSON 使用 UTF-8、对象键排序、紧凑分隔符，不含时间戳、重复键或非有限数字。真实 manifest 固定 `mcp/rule-registry.json`、`mcp/rule-context-index.json` 及实际 `owner_paths.py` 映射源的 SHA-256。Owner 赋值只作字面量解析，不执行该文件。项目门禁验证真实 registry 与 index 结构，不将合成测试数据当作可发布的项目元数据。

每个 entry 哈希绑定其身份、格式与版本、三个旧来源哈希、相关别名、完整传递来源单元、引文、分支和来源记录。资源还包含自身规范哈希。限制为每个产物 8 MiB、最多 512 条按语言区分的来源单元记录，以及每个 entry 完整闭包最多 262,144 个 Unicode 字符；manifest 可降低但不可提高限制。超限时报告 required 与 allowed，且不得生成不完整但标为 complete 的产物。

Layer-01 来源单元进入 entry 闭包时，同一闭包还必须包含同一文档、同一语言的 Codex CLI / ChatGPT Desktop 优化段，包括声明没有特别优化的段落。较窄的有源定义仍保持原范围；此要求不强制加入完整通用规范。Claude 专属段落保留为文档兼容背景，不由此 MCP Server 消费。

## CLI 与固定发布

使用 `token-io-decoupling-dev --project-root /absolute/repository/root` 启动本地 Codex CLI MCP Server。启动时检查开发标记和固定输入，并固定根目录的规范路径与目录身份。未提供该参数时仅注册 `dev_capabilities`。编译工具调用无参数，不能选择根目录、输入、输出、模型或权限。固定 manifest 为 `mcp-project-dev/compiler-manifest.v1.json`；唯一编译输出为 `mcp-project-dev/generated/runtime-instructions.v1.json`。

`compile_runtime_instructions` 可以替换既有输出，因而标为 destructive。替换时 `output_baseline_sha256` 必须与现有已验证产物的 `canonical_sha256` 相符，而不是文件原始字节哈希。提供基线时，即使内容相同的 no-op 也必须匹配，且不能借此创建缺失文件。没有基线时，仅允许独占创建或字节完全相同的 no-op。发布使用有界 no-follow 读取、自有独占临时文件、fsync，以及原子替换或禁止覆盖的创建；失败保留原产物。`check_runtime_instructions_freshness` 仅读取、不写入，返回 `fresh`、`stale`、`missing` 或 `failed`。

工具不调用 OpenAI、网络、Git/GitHub、聊天或 Memory。Server 只直接支持本地 Codex CLI，不增加运行环境判断或其他 Agent 适配器。审核清单 `mcp-project-dev/legacy-mapping-review.v1.json` 和 `mcp-project-dev/compiler-manifest.review.v1.json` 是非发布审核证据。发布更新后的资源前，Root 须审核分类、provider 段范围和 entry 分支的后续变化，并确认图无环且完整闭包预算满足限制。
