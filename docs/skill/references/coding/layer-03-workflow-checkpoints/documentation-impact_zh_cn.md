# 文档影响

[English](documentation-impact.md) | [简体中文](documentation-impact_zh_cn.md)

本检查点负责文档/内容变更后的路线级影响分类和返回路由。


## 触发与输入

Documentation 或获批内容变更后，判断 implementation/content、documentation 或 Contract 证据是否改变。应用[Documentation](../layer-02-workflow-concepts/completion-and-effects/documentation_zh_cn.md)和[Verification Epoch](../layer-02-workflow-concepts/verification-and-repair/verification-epoch_zh_cn.md)。

## 决策与结果

1. 记录变更前后指纹，并分类每个受影响维度：实现/内容、文档、Git 元数据或多个维度。为每项分类附上证据。
2. 列出必需检查、仍可复用的证据，以及每个未变维度未变化的理由。无变化结果应带指纹证据并记录为 `Not applicable`。
3. 重新核验变更维度。若内容改变行为、Contract 或验收，将证据返回实现/内容 Verification；若仅文档变化，返回文档检查及未变维度理由。
4. 向路线调度返回分类、指纹、检查、复用理由和 Verification 处置结果。

## 失败边界

影响未知、必需检查缺失或证据过期时阻塞 Acceptance。保留受影响/不受影响维度判断及输出授权范围；变更 epoch 后不得复用旧证据。

## 相关概念

- [Documentation](../layer-02-workflow-concepts/completion-and-effects/documentation_zh_cn.md)
