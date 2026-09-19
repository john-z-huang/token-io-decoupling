# 运行环境检查点

[English](environment.md) | [简体中文](environment_zh_cn.md)

## 动作

1. 读取当前系统、开发者和应用上下文中的明确运行元数据。如果元数据直接指出本地 Codex、ChatGPT Work 或标准 ChatGPT，则将其作为主要事实。
2. 使用当前已暴露的可调用工具清单、工作区根目录、权限配置、沙箱信息和其他任务元数据作为辅助证据。不能仅凭本地 Shell、worktree、模型名称或工具特征唯一确定运行环境。
3. 当前任务授权时，只检查本地进程或环境信息中暴露的非敏感运行元数据；不得输出或持久化凭据、令牌。
4. 不得使用浏览器、GUI 导航、截图或页面视觉内容来识别运行环境。
5. 将运行环境归类到且只能归类到一条支持分支：
   - **本地 Codex**：任务暴露本地文件系统/Shell 或 worktree 能力以及 Codex Agent 工具。
   - **ChatGPT Work**：任务暴露 Work Session、连接器或文件能力，但不代表拥有本地执行能力。
   - **标准 ChatGPT**：除非明确暴露，否则不假设拥有本地执行或独立 Session 能力。
6. 如果运行环境不属于任何分支，将运行环境标记为不受支持，并停止依赖该环境的工作。
7. 如果证据仍不足以唯一判断运行环境，停止依赖该环境的工作，并将以下原问题返回给用户：`无法根据当前元数据确定当前运行环境。请在下一条指令中明确说明当前运行环境是“本地 Codex”“ChatGPT Work”还是“标准 ChatGPT”，然后继续。`

## 通过条件

真实运行环境已根据明确元数据唯一分类，或用户已提供兜底说明。

## 边界

本检查点不选择执行模式，不将模型绑定到角色，不授权委派，不实现修改，也不声称已经执行未观察到的操作。

## 相关概念

- [Coding Session Model](../layer-01-fundamental-concepts/session-model_zh_cn.md) — 定位 Session 拓扑归属。
- [Coding Context Exchange 工作区边界](../layer-01-fundamental-concepts/context-exchange-workspace-boundary_zh_cn.md) — 定位文件系统和 worktree 能力归属。
- [Coding Delegation Mode Confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md) — 定位模式门禁能力消费者。
