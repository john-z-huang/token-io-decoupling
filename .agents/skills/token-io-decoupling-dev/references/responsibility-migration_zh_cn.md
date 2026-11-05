# 产品与开发职责映射

[English](responsibility-migration.md) | [简体中文](responsibility-migration_zh_cn.md)

本参考文档记录当前产品归属和计划中的开发侧迁移，不声称未来阶段已经交付。入口见[开发 Skill](../SKILL_zh_cn.md)；其 MCP Server 目前只提供能力发现。

## 职责与分阶段路径清单

| 关注点及当前路径 | 职责与目标位置 | 阶段和边界 |
| --- | --- | --- |
| 产品 Skill 和参考 Markdown 中的规范策略内容 | 保留为产品侧策略来源 | 源文本继续具有权威性；开发工具可以验证或派生产物，但不能静默替换策略。 |
| 映射注册表：`mcp/rule-registry.json`、`mcp/rule-context-index.json` 和 `mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/owner_paths.py` | 映射归属迁入 `mcp-project-dev`；产品运行时消费生成的资源 | #193 定义编译器契约和映射模型。#196 将运行时打包改为消费派生资源。稳定通用 ID 和运行时契约仍归产品侧。 |
| 运行时资源构建钩子：`mcp/packages/token_io_decoupling_core/hatch_build.py` 和 `mcp/hatch_build.py` | 产品打包继续负责随包发布运行时资源；开发项目负责编译产物 | #196 集成生成资源，并从产品包中移除仅供开发使用的附件。 |
| 项目专用检查：`mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/compliance_preflight.py` 和 `mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/compliance_core.py` | 双语、文档层级、结构及项目专用合规检查迁至 `mcp-project-dev` | #194 迁移项目专用检查。通用的 `generic_project` 安全路径与基线执行仍归产品侧，并继续守护运行时操作。 |
| 输出物化支持：`mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/output_materialization.py`、`mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/materialization_templates.py` 和 `mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/materialization_models.py` | Skill 指令维护迁至开发工具；运行时 Worker 授权和应用仍归产品侧 | #194 将开发 Skill 维护分支与产品 Worker 路径分开。开发侧写入不会扩大权限；应复用产品安全基础，不复制或削弱相关策略。 |
| Worker 实现：`mcp/packages/token_io_decoupling_worker/src/token_io_decoupling_worker/tools.py` | 产品 Worker 的 `code_configuration` 保留可信根目录和精确路径检查、基线/覆盖验证、任务绑定、独立操作员授权及产物哈希检查，以及 prepare → inspect → fresh preflight → exact apply → receipt/readback 全流程 | 保留在产品侧。迁移 Skill 指令维护不迁移或绕过此运行时操作。 |
| 下方列出的现有项目验证器和辅助工具 | 迁至 `.agents/skills/token-io-decoupling-dev/scripts/` | #195 迁移脚本入口并更新调用方；#192 不移动任何脚本。 |
| CI、测试、`AGENTS.md`、`MULTI_LINGUAL.md`、根目录定位、`.agents` 发现和快照调用 | 将开发专用检查迁移或重定向至 `mcp-project-dev`，同时保留产品运行时契约和面向用户说明的产品归属 | #195。保留产品用户侧安装/配置脚本，包括 `scripts/install-codex-mcp.sh` 和 `scripts/configure-codex-mcp-env.py`。 |
| 产品包资源附件 | 产品包只包含运行时消费的资源 | #196 在验证新运行时资源路径后移除开发专用附件。 |
| 隔离打包及运行时回归 | 两个项目各自保留依赖边界和测试 | #197 验证独立安装、产品无反向依赖，以及拆分后的回归行为。 |

计划迁入开发 Skill 脚本目录的 11 个现有验证器和辅助工具：

- `check-multilingual-docs.py`
- `check-doc-layer-links.py`
- `check-layer-01-sections.py`
- `check-layer-02-04-provider-neutrality.py`
- `check-layer-04-workflow-maps.py`
- `check-workflow-checkpoints.py`
- `check-context-exchange.py`
- `check_coding_document_migration.py`
- `markdown_discovery.py`
- `workflow_module_contracts.py`
- `compliance_core_loader.py`

## 单向依赖与权限边界

开发项目是面向本地 Codex CLI 的独立 MCP Server。目前骨架没有产品包依赖，并将编译器、项目合规检查和物化能力报告为不可用。后续阶段确有需要时，开发代码可以窄范围依赖产品核心；产品运行时包绝不能导入或依赖 `mcp-project-dev`。

规范策略、稳定 ID、运行时状态、权限和通用安全检查继续归产品侧。开发侧编译、检查和 Skill 维护写入不会创建产品权限，也不能削弱运行时守卫。所有阶段均须保留冻结迁移来源和历史基准。安装和 Codex 配置仍属于产品/用户侧工作。

## 当前 #192 边界

#192 新增独立项目、真实且只读的 `dev_capabilities` 发现工具和本职责映射。不实现编译器或合规检查，不移动脚本或 CI，不切换运行时加载器，不迁移 Worker 的 `code_configuration` 路径，也不声称未来开发写入能力已可用。
