# 2026-11-18 · Coding 路线迁移到 YAML DSL

## 范围与结构

- 两条 Layer-04 Coding 路线和八个模块由 YAML DSL 维护。源文件在 `docs/rules/` 下镜像 `docs/skill/` 的目录与文件名，原试点的验证 Epoch 规则也已移入对应的 Layer-02 目录。 [单代理路线](../docs/rules/coding-workflows/coding-single-agent.yaml) · [多代理路线](../docs/rules/coding-workflows/coding-multi-agent.yaml) · [维护说明](../docs/project/DOCUMENTATION_STANDARDS.md#参考规则-dsl)
- `route_step` 记录路线项 ID、阶段和对应模块。Pi 核对 `SM01`–`SM07`、`MM01`–`MM07` 及八个模块的 50 个检查点 ID 和顺序。分支、回返和重验仍沿用现有引擎。11 份 Markdown 保留原路径、规则正文、Mermaid 和链接顺序。对照时移除生成注释及其紧随的空行，差异仅为多代理路线在返回表格后补了一个空行。 [DSL Schema](../docs/rules/reference.schema.json) · [工作流目录](../archive/pi-coding-workflow/extensions/coding-workflow/catalog.ts)

## 运行时读取

- 编译器从 YAML 生成索引及 79 个规则片段，并从 Hook 合同生成 16 份执行正文。运行时从索引定位当前检查点和适用 Hook，只在需要时读取对应片段并核对 Hash。Entry Hook 读取锁定路线的 Mode 边界，Verification Hook 读取 Epoch 动作，引用从 Hook 单向指向 DSL。 [编译器](../scripts/compile-reference-dsl.py) · [运行时加载器](../archive/pi-coding-workflow/extensions/coding-workflow/reference-data.ts)
- 已迁移规则在上下文中通过 `coding-rule:` 引用。`coding_checkpoint` 的 `rules` 动作按 ID 返回单个片段，或列出目标文档的片段标题。规则查询不推进检查点，也不改写会话状态。Markdown 导出供阅读、离线核验及手动回退；TS 启动和渲染使用编译资源。未迁移规则的指纹在构建时记录，继续参与快照兼容校验。 [Pi 扩展用法](../docs/project/PI_EXTENSION.md) · [Hook 来源与引用](../docs/skill/hooks/README.md#来源整合与链接基准)

## 验证

- **PASS** · 107 个生成产物一致。11 份导出文档的正文、顺序和链接对照通过。编译器拒绝 Hook 指向其他 Hook 的执行引用以及 DSL 指回 Hook 的执行引用。
- **PASS** · 仅安装编译资源的测试副本可以启动和渲染两条路线，查询当前检查点和路线返回片段。文件读取检查确认启动只读取规则索引，渲染按需读取当前规则与 Hook 正文。Serena YAML LSP 在新目录索引并定位了 `MM04` 和 `DE08`。
- **PASS** · 147 项扩展测试、336 个 Hook 场景、674 次本地链接检查、61 项文档测试、Pi 1.5.2 类型与加载检查均通过。Pi 打包清单包含全部运行时资源，4 个 MCP wheel 离线构建成功。
- **SKIPPED** · 真实 Pi 模型、子代理、Memory 后端和 API 的端到端会话。
