# 安装与更新 Skill

准备 `uv` 和 Python 3.11 或更高版本，从本仓库根目录运行命令。

## 首次安装与更新

```bash
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --install-skill' _
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --update-skill' _
```

安装和更新默认使用 `~/.agents/skills/`。`--install-skill` 用于首次安装，目标已存在时拒绝覆盖。`--update-skill` 更新受管理的安装，目标不存在时也可首次安装。更新时使用与首次安装相同的目录和名称。之前安装在 `~/.pi/agent/skills/` 的 Skill 用 `--update-skill --host pi` 更新。

## 选择安装目录

| 参数 | 安装根目录 |
| --- | --- |
| `--host codex`（默认） | `~/.agents/skills` |
| `--host pi` | `~/.pi/agent/skills` |
| `--skills-dir <目录>` | 指定的目录，优先于 `--host` 的默认值。支持绝对路径、相对路径和 `~`。 |
| `--host codex --project-root <绝对目录>` | 现有项目下的 `.agents/skills`。与 `--skills-dir` 只能选一个。 |

默认安装路径为 `~/.agents/skills/token-io-decoupling/`。可用 `--name` 指定小写字母、数字和连字符组成的名称，作为安装根目录下的子目录。相对路径以运行命令时的工作目录为准。

```bash
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --install-skill --host pi' _
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --install-skill --skills-dir "$1"' _ '/absolute/path/to/my skills'
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --update-skill --skills-dir "$1"' _ '/absolute/path/to/my skills'
```

Codex 从目标项目新开会话后，可用 `$token-io-decoupling` 显式调用。Pi 可执行 `/reload` 或新开会话。选用自定义目录时，宿主需要能够发现或显式加载该路径。

## 安装保护

安装内容包括 `SKILL.md`、Hooks、路线和宿主适配。更新前校验安装标记及文件指纹，保护未知目录、本地修改、符号链接、Git 元数据和作为安装目标的 Git checkout。发布失败且无法自动恢复时，命令会报告原安装的备份路径。
