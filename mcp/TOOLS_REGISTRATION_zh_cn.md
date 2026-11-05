# 两个 MCP 程序与 Codex 注册

[English](TOOLS_REGISTRATION.md) | [简体中文](TOOLS_REGISTRATION_zh_cn.md)

本文负责两个独立 MCP 可执行程序的工具清单和 Codex 注册。[开发指南](DEVELOPMENT_zh_cn.md)负责构建、安装和最终检查；工作流 owner 保留策略权威，受保护工具保留其操作专属授权检查。

## 两个独立可执行程序

MCP 运行时由两个分别安装的可执行程序组成。每个程序都不需要启动参数，即可启动 stdio MCP Server：

| 可执行程序与 Codex 注册名 | 清单 |
| --- | --- |
| `token-io-decoupling-workflow` | 保持不变的 17 个能力、规则、规划、路由与评估工具。 |
| `token-io-decoupling-tools` | 共 34 个工具：33 个开发工作流工具和 `materialize_decoupled_output`。 |

管理命令 `token-io-decoupling` 不是 MCP 运行时，负责 setup、Skill 安装和环境变量转发修复。它的 `setup codex` 命令会解析、核验并注册当前两个 MCP 可执行程序。它只操作这两个注册表，不会识别或迁移其他注册。用户也可使用绝对可执行文件路径分别注册：

```sh
codex mcp add token-io-decoupling-workflow -- /absolute/path/to/token-io-decoupling-workflow
codex mcp add token-io-decoupling-tools -- /absolute/path/to/token-io-decoupling-tools
```

## 清单与操作边界

固定工具清单由[工具清单文件](packages/token_io_decoupling_core/src/token_io_decoupling_core/server_tools.py)负责。tools 可执行程序依赖 `dev-workflow-standards-tools`，来源固定为[其源仓库](https://github.com/john-z-huang/dev-workflow-standards/tree/ba5ecc95d9f9da77aca22c17e712d6c8d2a05987/mcp-server)提交 `ba5ecc95d9f9da77aca22c17e712d6c8d2a05987` 的 `mcp-server` 子目录。构建和安装必须解析该固定依赖及其封装资源，无需相邻开发 checkout 或绝对本地依赖路径。更新依赖时，必须按固定清单审阅工具签名、注解、描述和参数校验错误脱敏。

工具发现不授予权限。33 个开发工具保留各自的仓库根、副作用、API 输入和写入授权检查。`materialize_decoupled_output` 是唯一单独受守卫的输出操作；它需要可信启动时注入的授权 provider、当前逐次调用 Worker 绑定、独立授权、固定根目录和当前预检。若无可信 provider 和授权，该工具不可用。详见 [Worker 输出材料化](OUTPUT_MATERIALIZATION_zh_cn.md)。

开发工具保留各自的仓库根验证、副作用注解、API 输入审核和写入授权要求。tools 可执行程序复用其已发布的 schema、注解、描述与参数校验错误脱敏。开发工具可用不能证明身份，也不授权 Git/GitHub 副作用。API 操作要求进程中非空的 `OPENAI_API_KEY` 与 `OPENAI_BASE_URL`，显式使用固定 `gpt-6-luna`，不回退到默认凭据、地址或其他模型。

tools 可执行程序转发 API 和代理变量名以及 `OPENAI_TIMEOUT_MAX_RETRIES`，不写入变量值。Setup 为两个可执行程序使用空参数列表，保留两个目标注册表中的其他设置，并保留无关配置项。两个 MCP 进程保留各自的配置与能力要求。

## Setup 安全与幂等性

`token-io-decoupling setup codex --dry-run` 会读取配置并仅预检当前两个目标表，但不启动 MCP 子进程，也不写入。真实 setup 会解析已安装的 workflow 和 tools 可执行程序，核验其当前清单，并仅更新这两个目标表，且使用空参数列表。它保留目标表中的其他设置及所有无关配置项。它不会检查、分类、删除或迁移其他注册；旧安装的一次性清理由维护命令之外的交付操作负责。当前目标表格式错误、包含不支持的传输字段、受支持设置的类型无效或环境变量来源冲突时会失败关闭，且没有覆盖选项。这些检查只核验 setup 使用的设置，不表示会检测更广泛的策略冲突。

Setup 以原子方式写入常规配置文件，保留文件权限模式，在替换前检查文件是否已改变，并拒绝会导致无关内容被静默移动的不支持 TOML 布局。避免并发配置写入：输入检查不是全局锁。两个目标注册均正确时，重复成功运行不会产生变更。失败时按最后确认的状态报告。

## 验证

测试会将两个清单与预期 manifest 比较，并使用临时配置覆盖角色拒绝、外部 schema 和注解、脱敏、目标与无关配置保留、setup 预览及安全冲突处理。安装版 stdio 检查覆盖两个可执行程序及其精确清单。有序[最终检查](DEVELOPMENT_zh_cn.md#codex-sdk-最终查看)仅在全部普通检查通过后运行，构建并安装当前产物，再使用全新 Codex CLI 实例对两个可执行程序进行有界只读检查。它不执行模型轮，也不修改真实用户配置。

注册两个可执行程序本身不能证明已测量的 Token 节省；两个工具清单仍然可用。

## 相关概念

- [MCP 开发指南](DEVELOPMENT_zh_cn.md)
- [Codex 调用方匹配](CODEX_CALLER_CONTEXT_zh_cn.md)
- [Worker 输出材料化](OUTPUT_MATERIALIZATION_zh_cn.md)
