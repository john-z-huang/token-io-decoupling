# Complete Route Index

[English](INDEX.md) | [简体中文](INDEX_zh_cn.md)

- [Single-Agent Coding](coding-single-agent.md)
- [Multi-Agent Coding](coding-multi-agent.md)

## Reusable modules

Routes compose these modules in order and own all cross-module sequencing and continuation. A module may be entered when its declared work and effects are covered by existing user authorization and its entry prerequisites pass; no additional module-name authorization is required. A module does not call sibling modules.

- [Entry Readiness](modules/entry-readiness.md)
- [Session Readiness](modules/session-readiness.md)
- [Work Definition](modules/work-definition.md)
- [Single-Agent Execution](modules/single-execution.md)
- [Delegated Execution](modules/delegated-execution.md)
- [Verification and Repair](modules/verification-repair.md)
- [Documentation](modules/documentation.md)
- [Delivery and Acceptance](modules/delivery-acceptance.md)
