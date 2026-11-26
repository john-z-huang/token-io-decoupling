# 2026-11-18 · Hook DSL、阶段归并与路线目录调整

## Hook 合同迁移

- 16 份执行合同和 Hooks 目录页迁到 `docs/rules/hooks/`，采用有序块及稳定 ID。执行合同和目录页各有 YAML 模板。编译器用 `rule_include` 生成运行时片段引用，来源对照根据合同的来源表生成 YAML 和 Markdown。 [合同模板](../docs/rules/templates/hooks/hook-contract.yaml) · [目录模板](../docs/rules/templates/hooks/hook-directory.yaml) · [来源对照](../docs/rules/hooks/SOURCE_COVERAGE.yaml)

## 阶段检查点归并

- 两条 Coding 路线绑定七个阶段的 Hook。原模块的 50 个检查点及八张阶段流程图并入对应 Hook，旧模块 YAML 和 Markdown 目录及旧片段移除。路线步骤聚焦阶段交接和继续条件，保留两条路线的检查点 ID、顺序、路线图、前置返回映射和 Mode 边界。 [路线目录](../docs/rules/coding-workflows/README.yaml) · [验证 Hook](../docs/rules/hooks/verification.yaml)
- v5 运行时索引以 `hook-<ID>` 发布阶段检查点，Pi 只读取适用合同和当前检查点正文。旧模块 ID 仍可查询对应检查点。定位脚本按新 YAML 路径返回块位置，路线步骤同时返回 `hook_entry`。入口上下文读取当前路线的 Mode 边界。 [运行时目录](../archive/pi-coding-workflow/extensions/coding-workflow/catalog.ts) · [检查点定位](../scripts/workflow_checkpoint_lookup.py)

## 路线目录与依赖方向

- 路线 YAML 位于 `docs/rules/coding-workflows/`，Markdown 阅读版位于 `docs/skill/coding-workflows/`，两处目录与各自的 `hooks/` 同级。模板、导出路径、入口链接及校验脚本使用新路径。 [单代理路线](../docs/rules/coding-workflows/coding-single-agent.yaml) · [多代理路线](../docs/rules/coding-workflows/coding-multi-agent.yaml)
- 文档顺序为基础概念 → 工作流概念 → 检查点 → Hooks → Coding 路线。YAML 编译与 Markdown 校验共用层级规则，拒绝指向右侧层级的引用。校验覆盖文档及目录链接、流程图别名和 Hook 执行引用。Hook 来源对照按这一方向记录规则，路线绑定在路线索引中查阅。 [维护规范](../docs/project/DOCUMENTATION_STANDARDS.md#skill-文档依赖顺序)

## 验证

- **PASS** · 105 份 Coding DSL、17 份 Hook 源文档及 1 份来源对照通过结构检查，715 个编译产物通过一致性检查。336 个 Hook 注入场景和 1,132 条本地链接检查通过。
- **PASS** · 147 项扩展测试、62 项 Python 测试、60 项 MCP 测试及 Pi 1.5.2 类型和加载检查通过。反例覆盖五层目录的十种反向组合。
- **SKIPPED** · 使用真实模型、子代理、Memory 和外部 API 的端到端会话。
