# 工作流迁移与校验资料

本文记录历史迁移边界。当前行为以 [路线目录](../../../../rules/workflows/README.yaml)、[Hook 合同](../../../../rules/hooks/README.yaml)和对应的参考规则为准。

- 两条 Coding 路线保留七个主阶段及阶段间顺序，阶段检查点和通过条件由对应 Hook 维护；Layer-03 负责当次任务的判断，不重新定义 Layer-01/02 政策。
- 触发补证、修复或验证失效时，依据当前合同返回受影响的检查点，不按历史编号继续，也不重放已完成的效果。

## 归档清单与历史测试

| 清单 | 校验脚本 | 测试 |
| --- | --- | --- |
| [Coding 文档迁移清单](coding-document-migration.json) | [文档迁移校验](../../scripts/check_coding_document_migration.py)核对迁移目标、退役状态及 README 导航 | [文档迁移测试](../../tests/test_coding_document_migration.py) |
| [工作流模块迁移清单](workflow-module-migration.json) | [路线图校验原版](../../scripts/check-layer-04-workflow-maps.py)与[模块合同原版](../../scripts/workflow_module_contracts.py)核对旧步骤投影、Hook 检查点及 owner 链接 | [路线图测试原版](../../tests/test_check_layer_04_workflow_maps.py) |

上述脚本与测试需要归档基线生成的 Skill 阅读版。现行文档验证见[维护规范](../../../../docs/DOCUMENTATION_STANDARDS.md)。[历史优化测量](../../mcp/benchmarks/)随 MCP Server 保存。
