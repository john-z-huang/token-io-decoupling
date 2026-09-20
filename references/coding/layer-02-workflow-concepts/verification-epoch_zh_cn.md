# 验证 Epoch 检查点

[English](verification-epoch.md) | [简体中文](verification-epoch_zh_cn.md)

本检查点负责按验证覆盖状态维度处理 epoch 失效。后续修改只推进其改变了验证覆盖范围的维度；未受影响维度的早期证据仍然有效。不定义检查内容、独立 Session、结果分类或修复。

## 动作

1. 跟踪三个维度：implementation/content、documentation 和 Git metadata。
2. 当实现、配置、测试或其他被产品验证覆盖的内容发生变化时，推进 implementation/content epoch；该内容的早期产品验证失效。
3. 当维护中的文档或注释发生变化时，推进 documentation epoch，并运行适用的 Markdown、链接、空白、多语言和范围检查。如果变化改动了可执行内容、Contract 或验收条件，还必须同时视为 implementation/content 变化，返回实现 Verification。
4. 当 commit、branch、index 或 history 状态发生变化时，推进 Git metadata epoch。仅 Git metadata 操作不会推进 implementation/content 或 documentation epoch。但 Git 状态仍须经过 Git 检查点确认 staged 或 committed content 与最新验证指纹一致；内容发生差异或包含未验证内容时，返回对应的 Verification epoch。
5. 不得将受影响维度的早期 epoch 证据用于当前状态；必须完成新 epoch 所需的检查或 Verification。

## 通过条件

最新的 implementation/content、documentation 和 Git metadata 适用 epoch 已明确，各自所需的检查或 Verification 已排队或完成，且没有任何受影响维度依赖过期证据。

## 边界

本检查点不捕获指纹，不选择检查，不定义独立验证，不分类结果，不授权修复，不写文档，也不产生 Git 影响。

## 相关概念

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位实质性状态边界归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary_zh_cn.md) — 定位最终状态证据访问。
- [Coding Child Reuse and Replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement_zh_cn.md) — 定位修复 epoch 复用归属。
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位依赖路线放行条件。
