# 2026-11-18 · Pi 参考规则 YAML DSL 试点

## 设计与范围

验证与修复模块和验证 Epoch 规则改用 YAML 维护。`blocks` 按列表顺序组织章节、检查点及正文，每个块以稳定 ID 为键。`section` 和 `checkpoint` 负责导出标题与编号，`markdown` 保留表格、Mermaid、链接和规则正文。标记为 `expose: true` 的章节和每个检查点可独立读取。 [DSL Schema](../docs/rules/reference.schema.json) · [维护说明](../docs/project/DOCUMENTATION_STANDARDS.md#参考规则-dsl)

## 改动

- 编译器生成原路径上的两份 Markdown、轻量索引和八个独立片段。两份 Markdown 均只插入了生成说明注释及紧随的空行，移除这两行后与迁移前逐字一致。`--check` 核对生成结果和源文件是否同步。 [验证与修复模块](../docs/skill/hooks/verification.md#有序模块清单) · [验证 Epoch 规则](../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-epoch.md)
- Pi 从索引取得验证模块的检查点顺序和标题，注入时读取当前正文。Verification Hook 从同一索引读取 Epoch `actions`，两份参考规则无需反向引用 Hook。片段首次读取时校验 Hash，失配会阻断依赖操作。工作流快照继续绑定目录 Hash，恢复旧快照时按现有规则重新核验。 [运行时读取](../archive/pi-coding-workflow/extensions/coding-workflow/reference-data.ts) · [Verification Hook](../docs/skill/hooks/verification.md)
- 本地 Serena 项目配置启用了 `yaml`。新 Serena 会话用 `get_symbols_overview` 查询了 `blocks` 层级，再用 `find_symbol` 定位了 `VR03` 和 `actions`。项目忽略 `.serena/`，此设置仅保存在本地。 [验证模块 YAML](../docs/rules/hooks/verification.yaml) · [验证 Epoch YAML](../docs/rules/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-epoch.yaml)

## 验证

- **PASS** · DSL 生成一致性与 Markdown 逐字对照。扩展测试在渲染 `VR03` 上下文时记录了文件读取，仅打开其正文和 Epoch `actions` 两个片段。另验证篡改片段会被 Hash 校验拒绝。
- **PASS** · 146 项 Pi 扩展测试、336 个 Hook 注入场景、61 项文档测试和 21 项 MCP 测试。Pi 1.5.2 类型、入口加载及打包清单检查通过。离线构建 4 个 MCP wheel，包内 `verification_impact` 摘录与 DSL 动作片段一致。
- **SKIPPED** · 真实模型、子代理和 Memory 后端的端到端会话。
