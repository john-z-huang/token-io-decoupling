# 仓库指令

## 项目范围与权威资料

- 本仓库维护供 Codex 和 Pi Coding Agent 使用的 Hooks Skill，以及编译、验证和本地更新脚本。项目入口为 [README.md](README.md)。
- Skill 指令维护在 `rules/`，配套脚本在 `scripts/`。编译生成的 `skill/` 目录由 Git 忽略。修改入口、Hook、工作流或策略时，先定位对应的源文件。
- 文档维护规范见 [`docs/DOCUMENTATION_STANDARDS.md`](docs/DOCUMENTATION_STANDARDS.md)，本地更新见 [`INSTALL.md`](INSTALL.md)。
- `archive/` 中的资料仅供查阅，默认构建、安装和验证均跳过该目录。

## Skill 安装

- 安装或更新前核对实际目标。默认使用 `~/.agents/skills/`，可显式选择 `~/.pi/agent/skills/`、用户指定的 Skill 根目录或 Codex 项目目录。安装器在根目录下按 Skill 名称发布。
- 两个宿主共用同一规则产物。宿主事实与设置维护在 `rules/references/hosts/`，实际写入和配置修改须各有授权。

## Coding 工作流方向

- [单代理路线](rules/workflows/coding-single-agent.yaml)和[多代理路线](rules/workflows/coding-multi-agent.yaml)定义阶段顺序，[Hook 合同](rules/hooks/README.yaml)说明触发条件、所需证据和通过条件。
- Agent 根据指令和已核实的事实选择适用的 Hook、工具和分支，并按当前证据判断何时推进、复核或停下。操作须符合适用的 Hook 条件和用户授权。

## 修改与验证

- 维护中的文档使用简体中文和现有文件名；不新增英文副本或旧式语言后缀镜像。本地 Markdown 链接须指向存在的当前文件，移动或重命名时同步更新引用。
- 按文档规范选择验证，分别报告结构检查和语义验收的实际结果。
- 用隔离的临时安装验证 Skill 更新。实际用户目录或宿主配置仅按对应授权修改。

## 安全与 Git

- 保留可信身份绑定、授权、路径校验和外发检查；工具可用或配置存在不等于获得授权。不得输出凭据或将未核实的会话/请求元数据当作身份。
- 保留无关工作区内容和未跟踪文件；只暂存当前任务明确涉及的路径。提交、推送及其他 Git 副作用须有明确授权，不绕过正常检查或 hooks。
