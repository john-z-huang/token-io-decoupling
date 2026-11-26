# 2026-11-18 · 参考规则 DSL 全量迁移与检查点查询

## 全量迁移与运行时引用

- 接续[两条 Coding 路线的迁移](2026-11-18-coding-reference-dsl.md)，将剩余 105 份参考文档迁移为 YAML。现有 116 份源文件位于 `docs/rules/references/`，按原 Markdown 路径组织，包含 113 份 Coding、2 份 Multimodal 和 1 份共享协议。DSL 是参考规则的维护源。 [文档维护规范](../docs/project/DOCUMENTATION_STANDARDS.md#参考规则-dsl)
- DSL 之间用相对 `.yaml` 路径和稳定的块 ID 引用。编译器在导出时校验文件和块，再生成对应的 Markdown 路径和标题锚点。两条路线与八个模块的检查点 ID、分支和返回规则沿用现有定义。116 份 Markdown 与迁移前基线 `87c6427` 比较，移除生成说明后正文逐字节一致。 [编译器](../scripts/compile-reference-dsl.py)
- 编译得到 116 份阅读版、581 个规则片段、16 份 Hook 正文，以及 1 份 v4 索引。Pi 通过索引把 YAML 引用解析到相应的 `coding-rule:` 片段，并以索引中的章节锚点解析手写 Hook 里的 Markdown 引用。运行时从编译资源按需读取，Hook 的执行引用指向规则 owner。扩展测试覆盖只有编译资源时跨文档读取片段的路径。 [运行时目录](../archive/pi-coding-workflow/extensions/coding-workflow/catalog.ts) · [索引加载器](../archive/pi-coding-workflow/extensions/coding-workflow/reference-data.ts)

## Coding 模板与检查点定位

- 113 份 Coding DSL 声明 `document_type`。目录说明、目录索引、基础概念、工作流概念、检查点、路线和模块各有一份模板。新增文档用 `--template` 输出示例，`--check-structure` 校验文件位置、块类型与顺序、必需片段、路线阶段及既有检查点顺序。导出时执行同一套校验。 [类型与模板](../docs/project/DOCUMENTATION_STANDARDS.md#coding-dsl-类型与模板)
- `--locate-checkpoint` 从当前 YAML 源文件返回文件、YAML LSP 节点路径和行号。`--from` 指定图节点所在文档，`--show` 输出选中的块，路线步骤还返回被调用模块的入口。两条路线和验证修复模块用 `flowchart_references` 声明显式跨文件引用。结构校验核对图节点及目标文件和块的存在。 [查询用法](../docs/project/DOCUMENTATION_STANDARDS.md#从流程图定位检查点) · [定位实现](../scripts/workflow_checkpoint_lookup.py)

## 验证

- **PASS** · 113 份 Coding DSL 的模板校验和 714 个生成产物的一致性检查。116 份 Markdown 与迁移前基线的正文对照一致。路线图、检查点归属、文档层级和 Hook 链接检查通过。
- **PASS** · 147 项扩展测试和 61 项 Python 文档测试。编号检查点、路线步骤、模块入口、Layer-03 决策和 Layer-02 规则动作共 5 个节点，通过本地 Serena YAML LSP 的精确路径读取验证。
- **PASS** · 反例检查覆盖结构错位、缺少已发布片段、流程图别名缺少声明、目标 YAML 或块缺失，以及引用与本地编号冲突。
- **SKIPPED** · 真实 Pi 模型、子代理、Memory 后端和 API 的端到端会话。
