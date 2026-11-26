# 2026-11-18 · Pi Coding Workflow 的按需门禁

## 设计思路

七个 Layer-04 模块提供路线、检查点和恢复位置。执行者选择、写入范围、派发资格和验证新鲜度由各自的当前证据决定。本次以多代理路线由 Root 执行为试点，合并同一决定已经覆盖的回报，保留通用检查点和实际授权门禁。

## 改动

- **Root 分支。** `DE02` 明确提交 `facts.executor=root` 或 `sub_agent`。确认由 Root 执行时，一条有来源的记录覆盖 `DE03`、`DE05`、`DE06` 的 `not_applicable`。从 `DE02` 到 `DE07` 的检查点回报由五项减为两项，仍须在 `DE04` 放行 Slice，再在 `DE07` 审阅结果。
- **委派和恢复。** `DE06` 核对已确认的子代理职责、当前 Slice、派发核验 epoch、每个路径的写入类型及预算。`executor_changed` 只从多代理执行模块返回 `DE02` 重核，保留已占名额和实际效果。`decision_required` 补证后恢复调用方检查点，覆盖工作定义内的返回位置和交付时已完成的归档。`capability_changed` 在原位置复核。
- **验证新鲜度。** `VR06` 仅采用 `VR03` 实际通过的 epoch，中途状态变化时回到 `VR01`。宿主在执行前阻止的 `coding_run` 不推进 epoch。
- **上下文。** 完整注入当前检查点和适用 Hook。后续检查点提供标题及模块原文链接。Root 分支移除委派 Hook，修复与额外审计按相应边界注入。

实现与使用说明见 [状态机](../archive/pi-coding-workflow/extensions/coding-workflow/engine.ts)、[运行时](../archive/pi-coding-workflow/extensions/coding-workflow/runtime.ts) 和 [Pi Extension](../docs/project/PI_EXTENSION.md)。源码与规则摘要更新后，旧会话快照由现有 Hash 校验拦截，需按当前规则重新核验。

## 验证

- **PASS** · 144 项扩展测试，含 Root 分支、重新委派、Slice 影响、精确恢复、归档保全、验证失效及按需注入。Pi 1.5.2 类型与入口加载检查通过。
- **PASS** · 336 种合成 Hook 注入场景。默认上下文峰值从 41,563 降至 31,619 字符，约减少 24%。合成场景以字符计量。
- **PASS** · 文档结构及链接检查、61 项文档测试、4 个离线 wheel 构建。
- **SKIPPED** · 真实 Pi 会话、真实子代理、Memory 后端及 API 端到端验证。
