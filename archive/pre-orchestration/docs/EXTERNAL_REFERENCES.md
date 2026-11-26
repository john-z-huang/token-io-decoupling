# 外部参考资料

本索引供维护 Skill 指令和配套脚本时查阅。执行任务时从相应的规则源文件读取指令。

| 来源 | URL | 对应文档 | 开发用途与边界 |
| --- | --- | --- | --- |
| Pi 官方文档 | https://github.com/earendil-works/pi | [Pi 宿主适配](../rules/references/hosts/pi.yaml) | 核对 Skill 发现、按需加载及宿主提供的能力。 |
| Codex 官方文档 | https://learn.chatgpt.com/docs/build-skills | [Codex 宿主适配](../rules/references/hosts/codex.yaml) | 核对项目 Scope 的 Skill 安装与发现。 |
| Serena Memory 发现与读取 | https://raw.githubusercontent.com/oraios/serena/main/docs/02-usage/045_memories.md | [项目 Memory](../rules/references/coding/layer-01-fundamental-concepts/session-runtime/project-memory.yaml)、[任务计划生命周期](../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml) | 核对按名称发现和读取 Memory，以及回读所需的内容。 |
| Serena Memory 维护门槛 | https://raw.githubusercontent.com/oraios/serena/main/src/serena/resources/memory_maintenance.md | [项目 Memory](../rules/references/coding/layer-01-fundamental-concepts/session-runtime/project-memory.yaml)、[任务计划生命周期](../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml) | 区分可复用项目知识、任务计划和 Worker 记录的维护要求。 |
| Git canonical 共同目录 | https://git-scm.com/docs/git-rev-parse | [任务计划生命周期](../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml) | 核对 checkout、共同目录解析和本机仓库身份。 |
| Git linked-worktree 仓库布局 | https://git-scm.com/docs/gitrepository-layout | [任务计划生命周期](../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml) | 核对 commondir 共享及主仓库与各 worktree 管理目录的区别。 |
| uv 本地依赖缓存 | https://docs.astral.sh/uv/concepts/cache/ | [安装与更新](../INSTALL.md) | 核对 Skill 编译器的依赖缓存与离线构建条件。 |
| OpenAI Decisions 创建接口 | https://developers.openai.com/api/reference/resources/decisions/methods/create | [Decisions 建议](../rules/references/coding/layer-01-fundamental-concepts/execution-planning/decisions-advisory.yaml)、[运行环境与模型支持](../rules/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support.yaml) | 核对可选决策能力的选项格式、输出和拒绝边界。 |
| Serena MemoryManager 实现 | https://github.com/oraios/serena/blob/main/src/serena/memories/memory_manager.py | [任务计划生命周期](../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml) | 核对 Memory 路径、忽略与只读策略、保存和移动行为。 |
| Serena Memory API 实现 | https://github.com/oraios/serena/blob/main/src/serena/repl/api/mem_api.py | [任务计划生命周期](../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml)、[项目 Memory](../rules/references/coding/layer-01-fundamental-concepts/session-runtime/project-memory.yaml) | 核对全文读取、写入回执、`max_chars` 和重命名引用的行为。 |
| OpenAI Structured Outputs | https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses | [工作流路由建议](../rules/references/coding/layer-01-fundamental-concepts/execution-planning/workflow-routing-advice.yaml) | 核对可选建议的结构化响应格式。 |
