# Coding 路线选择

先通过[入口 Hook](../hooks/entry.md)确认用户目标、限制、交付物和验收条件。按[选路规则](../references/planning/task-planning.md#根据用户要求选路)在[单代理路线](coding-single-agent.md)和[多代理路线](coding-multi-agent.md)之间选择。

多代理路线依据[规划 Hook](../hooks/planning.md)与[委派 Hook](../hooks/delegation.md)安排角色和派发时间。必要能力缺失或新约束影响在途委派时，按[恢复 Hook](../hooks/recovery.md)处理。用户指令、任务依赖或可用能力变化时，按[计划调整规则](../references/planning/task-planning.md#按新证据调整计划)重查受影响的判断。

[完整路线目录](README.md) · [Hook 触发目录](../hooks/README.md)
