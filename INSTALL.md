# 安装与更新 Skill

准备 `uv` 和 Python 3.11 或更高版本，从本仓库根目录运行命令。

## 首次安装与更新

```bash
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --install-skill'
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --update-skill'
```

默认安装路径为 `~/.agents/skills/token-io-decoupling/`。`--install-skill` 用于首次安装，目标已存在时拒绝覆盖。`--update-skill` 更新受管理的安装，目标不存在时也可首次安装。更新时使用首次安装时的目录和名称。

## 选择安装目录

| 参数 | 安装根目录 |
| --- | --- |
| `--skills-dir <目录>` | 指定的 Skill 根目录。支持绝对路径、相对路径和 `~`。 |
| `--project-root <绝对目录>` | 现有项目下的 `.agents/skills`。 |

两个目录参数只能选一个。相对路径以运行命令时的工作目录为准。可用 `--name` 指定由小写字母、数字和连字符组成的名称，作为安装根目录下的子目录。

```bash
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --install-skill --skills-dir "$1"' _ '/absolute/path/to/my skills'
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --update-skill --skills-dir "$1"' _ '/absolute/path/to/my skills'
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --install-skill --project-root "$1"' _ '/absolute/path/to/project'
```

安装内容包括 `SKILL.md`、Hooks、工作流及 `references/` 下的任务编排规则。主代理与子代理的角色规则位于 `references/roles/`。选择当前运行环境能够发现或显式加载的目录。主代理在当前会话核验可用的子代理能力，再按角色职责规划和派发任务。

## 安装保护

更新前校验安装标记及文件指纹，保护未知目录、本地修改、符号链接、Git 元数据和作为安装目标的 Git checkout。发布失败且无法自动恢复时，命令会报告原安装的备份路径。
