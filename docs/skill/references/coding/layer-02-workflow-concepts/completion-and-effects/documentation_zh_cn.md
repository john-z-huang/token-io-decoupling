# 文档检查点

[English](documentation.md) | [简体中文](documentation_zh_cn.md)

## 动作

1. 确认获批准的文档路径、读者、目的和来源证据。
2. 只修改获批准的 Markdown 或注释范围。两种语言都维护时，保持英文和简体中文镜像同步。
3. 仓库文档、代码注释或项目 Memory 笔记发生变化时，推进 documentation epoch，并对该变更运行适用检查；其中包括在相关时运行 Markdown、链接、空白、多语言和范围检查。
4. 记录文档变更是否影响可执行内容、Contract 或验收条件。按当前 epoch 要求重新验证受影响维度；documentation epoch 变化本身不要求重跑无关的产品行为测试。
5. 不得以文档为名加入新行为、策略、范围或 Git 影响，并报告无法运行的检查。
6. 获批输出包含可复用 Agent 项目知识，或用户明确要求的跨会话笔记时，通过[项目 Memory 与代码结构能力](../../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools_zh_cn.md)写入，保留既有名称和子目录意图，并确认写入成功结果。未请求此类输出时，记录 `Not applicable` 及原因。能力不可用或写入失败时，报告失败，并将该请求输出保持为未完成。权威仓库文档和代码注释仍写入获准的仓库文件路径，并遵循上文已有的镜像、epoch、检查及返回规则。

## 通过条件

获批文档准确描述适用的已验证状态，当前 documentation epoch 已明确，适用检查通过或已明确报告不可用，所有获批输出中包含的可复用 Agent 项目知识，以及用户明确请求的每条跨会话笔记，均已成功保存并确认写入结果；当前工作流路线已处置任何需要重新验证的内容影响。

## 边界

本检查点不替代实现验证，不授权产品决策，也不授权 Git 影响。

## 相关概念

- [Coding Content Memo](../../layer-01-fundamental-concepts/context-exchange/content-memo_zh_cn.md) — 定位可复用 memo 内容契约归属。
- [Coding Content Memo Lifecycle](../../layer-01-fundamental-concepts/context-exchange/content-memo-lifecycle_zh_cn.md) — 定位 memo 生命周期归属。
- [Coding Execution Control](../../layer-01-fundamental-concepts/execution-control/execution-control_zh_cn.md) — 定位获准文档范围归属。
- [项目 Memory 与代码结构能力](../../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools_zh_cn.md) — 定位可复用项目知识的读取和写入能力。
