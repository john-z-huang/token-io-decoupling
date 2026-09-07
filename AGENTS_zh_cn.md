# 仓库多语言文档规则

这些规则适用于在本仓库中创建、修改、重命名、移动或删除文档的所有 Agent 和贡献者。

## Canonical 语言布局

- 英文是默认文档语言。
- 简体中文镜像在 `.md` 前使用 `_zh_cn` 后缀。
- 英文 canonical 示例：`README.md`、`SKILL.md`、`references/coding-flow.md`。
- 简体中文示例：`README_zh_cn.md`、`SKILL_zh_cn.md`、`references/coding-flow_zh_cn.md`。
- `AGENTS.md` 是仓库指令入口；`AGENTS_zh_cn.md` 是它的简体中文语义镜像。
- 配置、代码、生成文件和非 Markdown 资源默认不要求语言镜像，除非任务明确提出该要求。

## 成对维护要求

当 Markdown 文档属于双语文档集合时：

1. 同时维护英文 canonical 文件和简体中文 `_zh_cn.md` 镜像。
2. 一侧新增、重命名、移动或删除时，必须在同一变更中对另一侧进行对应操作。
3. 一侧发生语义变更时，应在同一个 Pull Request 中同步另一侧；只有任务明确记录暂时无法同步的原因时才允许例外。
4. 两种语言中的行为、约束、架构、示例和验收语义必须保持一致。翻译可以自然表达，但含义不能发生变化。
5. 不得只在某一种语言版本中静默新增规则或要求。

## 同语言引用隔离

- 当目标存在双语版本时，英文 Markdown 只能链接英文 Markdown。
- 简体中文 Markdown 只能链接对应的 `_zh_cn.md` 文件。
- 语言切换链接是预期存在的唯一跨语言 Markdown 链接。
- 英文运行入口 `SKILL.md` 只能加载 `references/` 下的英文文件。
- 简体中文运行入口 `SKILL_zh_cn.md` 只能加载 `references/` 下的 `_zh_cn.md` 文件。
- 英文 reference 不得加载或依赖中文 reference；中文 reference 不得加载或依赖英文 reference。

## 语言切换链接

面向用户直接阅读的双语文档，在条件允许时应在顶部附近提供明显的语言切换入口：

```md
[English](example.md) | [简体中文](example_zh_cn.md)
```

具体相对路径可根据目录调整。该跨语言例外不能用于运行时依赖引用。

## 新增文档时

新增 Markdown 文档前，先判断它属于哪一类：

- **双语产品 / Skill 文档**：同时创建英文文件和 `_zh_cn.md` 文件，并遵守以上全部规则。
- **仓库运行或平台元数据**：保留工具或平台要求的 canonical 文件名；如果支持且有意义，可以增加语言镜像，但不能改变平台要求的入口文件名。
- **生成内容、vendor 内容或外部材料**：除非任务明确要求，否则不要人为补充翻译。

如果无法明确分类，优先按双语产品 / Skill 文档处理。

## 必须执行的校验

文档变更完成前运行：

```bash
python3 scripts/check-multilingual-docs.py
```

只要校验器仍报告错误，该文档变更就不能视为完成。如果校验器与本规则不一致，应同时修复校验器和文档，而不是绕过检查。

## Pull Request 审查清单

任何涉及双语文档的变更都要确认：

- 英文 canonical 文件名保持无语言后缀。
- 简体中文文件统一使用 `_zh_cn.md`。
- 需要成对维护的文档两种语言均存在。
- 除语言切换链接外，同语言引用保持隔离。
- `SKILL.md` 只加载英文 reference。
- `SKILL_zh_cn.md` 只加载简体中文 reference。
- 语义变更已同步到两种语言。
- `python3 scripts/check-multilingual-docs.py` 校验通过。
