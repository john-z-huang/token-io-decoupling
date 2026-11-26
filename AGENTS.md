# 仓库指令

## 项目范围与权威资料

- 本仓库维护开发任务编排 Skill。Skill 根据用户指令组织主代理和子代理的执行、交接、恢复与验收。项目入口为 [README.md](README.md)。
- `rules/` 中的 YAML DSL 是 Skill 指令的唯一维护来源，主代理与子代理的角色规则位于 `rules/references/roles/`，配套脚本位于 `scripts/`。`skill/` 中的 Markdown 是纳入 GitHub 仓库版本控制的生成产物。
- 文档维护规范见 [`docs/DOCUMENTATION_STANDARDS.md`](docs/DOCUMENTATION_STANDARDS.md)，本地更新见 [`INSTALL.md`](INSTALL.md)。
- `archive/` 保存历史资料，默认构建、安装和验证均跳过该目录。

## Skill 安装

- 安装或更新前核对实际目标。默认使用 `~/.agents/skills/`，也可指定 Skill 根目录或项目目录。安装器在根目录下按 Skill 名称发布。

## 工作流

- [单代理路线](rules/workflows/coding-single-agent.yaml)和[多代理路线](rules/workflows/coding-multi-agent.yaml)说明阶段与交接，[Hook 合同](rules/hooks/README.yaml)说明触发条件、所需证据和通过条件。
- 主代理根据用户指令和任务需求选择路线、按需安排角色并核对结果。操作须符合适用的 Hook 条件和用户授权。

## 修改与验证

- 在开发过程中，Code Agent 从 `rules/` 读取和修改指令。避免打开、搜索或审阅 `skill/` 下的 Markdown 正文及内容差异。通过编译命令更新产物，通过命令退出状态和文件路径核对结果。
- 修改 `rules/` 中的指令或影响生成结果的编译逻辑后，从仓库根目录依次运行生成和校验命令。

  ```bash
  /bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py'
  /bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --check'
  ```

- 提交规则变更时，将对应的 `skill/` 产物新增、更新和删除放在同一提交。GitHub Actions 在推送和拉取请求时校验提交中的产物与 DSL 一致，合并前须通过 `Check generated Skill`。规则移动或删除时，按[文档维护规范](docs/DOCUMENTATION_STANDARDS.md#修改与验证)通过编译器处理退役产物。
- 维护中的文档使用简体中文和现有文件名；不新增英文副本或旧式语言后缀镜像。本地 Markdown 链接须指向存在的当前文件，移动或重命名时同步更新引用。
- 按文档规范选择验证，分别报告结构检查和语义验收的实际结果。
- 用隔离的临时安装验证 Skill 更新。实际用户目录或宿主配置仅按对应授权修改。

## 安全与 Git

- 保留可信身份绑定、授权、路径校验和外发检查；工具可用或配置存在不等于获得授权。不得输出凭据或将未核实的会话/请求元数据当作身份。
- 保留无关工作区内容和未跟踪文件；只暂存当前任务明确涉及的路径。提交、推送及其他 Git 副作用须有明确授权，不绕过正常检查或 hooks。
