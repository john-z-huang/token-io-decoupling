# Coding 子代理消息可见性

[English](delegation-child-message-visibility.md) | [简体中文](delegation-child-message-visibility_zh_cn.md)

本文档仅规定父级会话与子代理之间文本消息的会话可见性和正文证据，不规定消息授权或消息内容范围。

## 通用规范

### 发送前展示，接收后再依赖

父代理或子代理作为发送方时，在调用消息发送工具前，须在当前发送会话中以普通文本展示完整、可安全展示的外发正文，并确认展示文本与实际载荷完全一致。此要求适用于父代理向子代理发送，也适用于子代理向父代理发送。

消息送达后，父级须在主要父级会话中以普通文本展示完整、可安全展示的返回正文，然后才可依赖、概述该内容或采取后续操作。工具调用卡片、活动事件、送达回执、任务状态或“消息已发送”等通知不等同于消息正文。

正文过长时，应拆分为连续编号的部分展示，不得概述或截断；如需遮蔽内容，应明确标记。若运行环境未显示正文，且发送方或父级无法从会话记录中复现完整正文，则不得将该消息用于依赖切片。

### 保留方向与证据

注明每条消息的方向；运行环境提供身份时，同时注明目标或来源子代理。将正文与评论清楚区分。转述、摘要或声称内容已发送/收到，均不能作为消息正文的证据。

## Codex CLI / ChatGPT Desktop 特别优化指令

### 使用当前会话暴露的消息工具

当前 Session 向父代理或子代理暴露并授权使用 `collaboration.send_message` 时，无论调用方是父代理还是子代理，都须在同一发送 Session 中、工具调用前以普通文本展示完整安全外发正文，并确认其与实际载荷一致。父级收到消息后，须在主要父级会话中展示完整安全正文再依赖。工具调用卡片、活动事件、回执和状态不代替正文；无法从会话记录中复现完整正文时，阻塞依赖切片。

## Claude Code CLI / Claude Desktop 特别优化指令

### 使用已暴露的 SendMessage

Anthropic 的 [Agent Teams 文档](https://code.claude.com/docs/en/agent-teams)将 `SendMessage` 说明为代理间发送消息的工具。当前 Session 向父代理或子代理暴露并授权使用该工具时，发送方无论是父代理还是子代理，都须先在自己的会话中以普通文本展示完整安全外发正文，再调用工具，并确认展示文本与实际载荷一致。父级收到消息后，须在主要父级会话中展示完整安全正文再依赖。当前路径未暴露 `SendMessage` 时，不适用此工具调用前检查；仍须遵循通用的返回正文可见性要求。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位新子代理提示的创建边界。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位已放行切片和后续派发要求。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子代理状态及返回处理。
