# Coding 子代理消息可见性

[English](delegation-child-message-visibility.md) | [简体中文](delegation-child-message-visibility_zh_cn.md)

本文档仅规定父级会话与子代理之间文本消息的会话可见性和正文证据，不规定消息授权或消息内容范围。

## 通用规范

### 按配置展示；依赖前取得完整正文

按[会话审计可见性](../session-runtime/session-audit-visibility_zh_cn.md)预设执行。Worker 必须在自身会话中完整展示安全的入站和出站正文。Root 消息按预设展示预览、摘要或全文；要求全文时，发送前须完整展示安全正文并确认与载荷完全一致。Worker 已完整可见的最终结果就是出站副本，不得重复打印。

收到消息后，Root 在依赖前必须取得并完整阅读实际返回正文；再按预设在主要会话中展示完整安全正文或摘要。工具调用卡片、活动事件、送达回执、任务状态或“消息已发送”等通知不等同于消息正文，不能代替正文。

按职责或预设要求完整展示时，过长正文可拆分为连续编号的部分展示，不得概述或截断；如需遮蔽内容，应明确标记。若运行环境未显示实际正文，且无法从会话记录复现，则不得将该消息用于依赖工作。

### 保留方向与证据

注明每条消息的方向；运行环境提供身份时，同时注明目标或来源子代理。将正文与评论清楚区分。转述、摘要或声称内容已发送/收到，均不能作为消息正文的证据。

## Codex CLI / ChatGPT Desktop 特别优化指令

### 使用当前会话暴露的消息工具

当前 Session 暴露并授权使用 `collaboration.send_message` 时，按已配置预设执行。Worker 保持安全收发正文完整可见；Root 出站全文必须匹配载荷。Root 始终完整读取实际返回正文后再依赖，展示内容由预设决定。无法从会话记录复现实际正文时，阻塞依赖工作。可见副本不证明原始传输字节。

## Claude Code CLI / Claude Desktop 特别优化指令

### 使用已暴露的 SendMessage

Anthropic 的 [Agent Teams 文档](https://code.claude.com/docs/en/agent-teams)将 `SendMessage` 说明为代理间发送消息的工具。当前 Session 暴露并授权使用时，遵循通用配置预设。Worker 保留安全收发正文完整可见性；Root 在依赖前完整读取实际返回正文，展示方式按预设执行。可见副本不证明原始传输字节。若未暴露 `SendMessage`，不得假设其存在；仍须满足通用证据要求。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位新子代理提示的创建边界。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位已放行切片和后续派发要求。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子代理状态及返回处理。
- [Coding Session 审计可见性](../session-runtime/session-audit-visibility_zh_cn.md) — 定位会话可见性预设及优先级。
