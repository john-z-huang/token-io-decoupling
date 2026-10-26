# 增强规则上下文

[English](enhanced-rule-context.md) | [简体中文](enhanced-rule-context_zh_cn.md)

本模块负责有界加载当前注册的规则节点及其映射的 owner 标题；不负责底层规则，也不授权工作或证明身份、权限。

## 通用规范

### 选择并核验当前规则上下文

仅使用稳定节点映射定位既有权威 owner 路径和准确标题。每个检查点只加载当前所需节点；不得扫描仓库，也不得把返回摘录视为递归加载了所有链接 owner。判断还需要其他直接链接 owner 时，应单独读取其权威文档，并核验版本和语言均为当前值。必需 owner 不可访问时，阻塞依赖该内容的判断，不得推断其正文。

每次请求都必须从同一来源、同一语言读取注册表和 owner 标题。每次读取当前映射及标题，并将 Hash 绑定到节点结构、语言和正文。普通文字修改会在下一次读取时生效。受支持节点 ID、事实、证据、分支或其他程序校验结构发生变化时，必须配套更新兼容实现和测试；拒绝不受支持的结构，不得用旧契约解释。

已安装包使用构建生成的只读 owner 摘录。源码开发必须由调用方显式配置仓库根目录；不得根据已安装包位置推断 checkout。修改源码 Markdown 不会更改已安装包快照。不得混用不同来源的注册表和 owner 正文，也不得把英文映射与中文正文混合。

公共规则上下文读取为只读，可用于 Native 路线；它不能证明可信宿主身份、操作守卫、Enhanced 状态可用性或授权。若完整所需标题的来源、语言和 Hash 已核验，该标题本身可作为已读取内容。它不能证明未返回的其他章节或直接链接 owner 已读取；其含义仍以映射 owner 为权威。

不需要选择规则上下文时，记录带理由的 `Not applicable`，仍须直接阅读必需的权威 owner。若有界加载失败但权威 owner 可访问，则改为直接使用该 owner 并记录限制。映射不兼容或必需权威内容无法取得时，只阻塞依赖该内容的判断。

## Codex CLI / ChatGPT Desktop 特别优化指令

公共 `rules_get_context` 接口可返回当前注册节点的上下文，无需打开 Root 或 Worker 状态。只请求所选节点，并核验其 owner、语言和 Hash。公共读取成功不能证明受保护状态或真实宿主绑定可用。源码开发须显式指定仓库根目录；已安装运行时读取打包快照。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的规则上下文优化。遵循通用规范，并通过当前 Session 实际暴露的能力获取当前权威 owner 内容。

## 相关概念

- [增强状态存储](enhanced-state-store_zh_cn.md) — 定位独立的受保护状态与身份边界。
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位 output-class 节点映射的模式选择 owner。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Slice 与 Control 节点归属。
