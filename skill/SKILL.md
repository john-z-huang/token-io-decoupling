---
name: token-io-decoupling
description: "根据用户指令自动拆解 Coding 任务、选择单代理或多代理路线、动态编排主代理与子代理并应用相应 Hooks。"
---

# Token I/O Decoupling

按用户当前指令规划任务、选择主代理与子代理的分工，并按实际进展应用工作流和 Hooks。

## 开始

先读[主代理职责](references/roles/main-agent.md)，通过[入口 Hook](hooks/entry.md)提取目标、约束、交付物和验收条件，然后使用[路线选择器](workflows/coding.md)。

- 用户明确要求不创建或不使用子代理时，走[单代理路线](workflows/coding-single-agent.md)。其余情况按[选路规则](references/planning/task-planning.md#根据用户要求选路)处理明确的委派要求和实际分工收益。
- [多代理路线](workflows/coding-multi-agent.md)按任务动态选择角色、模型和推理强度，优先复用同角色实例。任何新建或替换的子代理均禁止使用 Ultra 推理强度。

按[Hook 目录](hooks/README.md)读取当前动作的合同，从[编排参考目录](references/README.md)按需查阅阶段规则。各角色和任务沿用用户授权与当前权限。涉及委派时，按[委派能力](references/delegation/delegation-policy.md#委派能力)核对实际可用的操作。
