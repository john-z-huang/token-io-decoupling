# MCP 开发指南

[English](DEVELOPMENT.md) | [简体中文](DEVELOPMENT_zh_cn.md)

本指南负责可选 Python 子系统的本地开发与包检查。工作流政策仍由 [Skill 入口](../SKILL_zh_cn.md)及其链接的 owner 维护；[架构契约](../ENHANCED_ARCHITECTURE_zh_cn.md)说明组件边界。

## 环境与检查

在 `mcp/` 中运行以下命令。项目声明 Python 3.11 或更新版本，并提交依赖锁文件。使用 uv 托管的解释器和锁定的开发依赖：

```sh
uv sync --managed-python --locked --group dev
uv run --managed-python --locked -- pytest
uv run --managed-python --locked -- ruff check .
uv run --managed-python --locked -- ruff format --check .
uv run --managed-python --locked -- ty check
```

如需把虚拟环境放在 checkout 外，运行这些命令前将 `UV_PROJECT_ENVIRONMENT` 设置为临时目录的绝对路径。测试使用临时数据库与模拟绑定，不证明操作系统隔离或实际宿主客户端兼容性。测试套件不需要 API 密钥或真实 API 请求。

仓库文档检查独立执行。请从仓库根目录运行[仓库指令](../AGENTS_zh_cn.md)要求的检查，包括既有工作流路线图与上下文交换回归测试。

## 构建与规则资源

在 `mcp/` 中构建 wheel 和源码分发包，输出到临时目录：

```sh
uv build --managed-python . --out-dir /tmp/token-io-mcp-dist
```

构建 Hook 从注册表及其引用的 Markdown owner 生成只读规则资源。这些生成摘录是包资源，不是第二份手工维护的政策正文。源码分发包携带自身的规则来源，使后续 wheel 构建不会借用无关的相邻 checkout。构建产物测试使用脱离原仓库的源码分发包，并检查双语规则及迁移资源。

在 checkout 中测试规则编辑时，构造 `RuleLoader` 并明确传入仓库根目录。默认加载器读取已安装的包资源。更新这些资源需要重新构建并安装分发包；编辑其他 checkout 不会更新已安装的 wheel。

迁移模块属于有版本的包资源。保留已发布文件，Schema 变化新增迁移。除新建数据库外，还要运行升级和恢复测试；仅验证初始化不能证明历史兼容性。
