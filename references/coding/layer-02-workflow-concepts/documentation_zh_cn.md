# 文档检查点

[English](documentation.md) | [简体中文](documentation_zh_cn.md)

## 动作

1. 确认获批准的文档路径、读者、目的和来源证据。
2. 只修改获批准的 Markdown 或注释范围。两种语言都维护时，保持英文和简体中文镜像同步。
3. 文档或注释发生变化后，推进 documentation epoch，并运行适用的 Markdown、链接、空白、多语言和范围检查。
4. 如果文档或注释变化改动了可执行内容、Contract 或验收条件，返回相关的实现和 Verification 检查点。否则，documentation epoch 变化本身不要求重跑无关的产品行为测试。
5. 不得以文档为名加入新行为、策略、范围或 Git 影响，并报告无法运行的检查。

## 通过条件

获批准的文档准确描述适用的已验证状态，当前 documentation epoch 已明确，适用检查通过或已明确报告不可用，且任何影响内容的变化都已返回实现 Verification。

## 边界

本检查点不替代实现验证，不授权产品决策，也不授权 Git 影响。

## 相关概念

- [Coding Content Memo](../layer-01-fundamental-concepts/content-memo_zh_cn.md) — 定位可复用 memo 内容契约归属。
- [Coding Content Memo Lifecycle](../layer-01-fundamental-concepts/content-memo-lifecycle_zh_cn.md) — 定位 memo 生命周期归属。
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位获准文档范围归属。
