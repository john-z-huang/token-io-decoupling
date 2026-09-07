# Multilingual documentation rules | 多语言文档规则

This file is the single source of truth for multilingual documentation maintenance in this repository.

本文档是本仓库多语言文档维护规则的唯一事实来源。

## Canonical language layout | Canonical 语言布局

- English is the default documentation language. / 英文是默认文档语言。
- Simplified Chinese mirrors use the `_zh_cn` suffix immediately before `.md`. / 简体中文镜像在 `.md` 前使用 `_zh_cn` 后缀。
- Canonical English examples: `README.md`, `SKILL.md`, `references/coding-flow.md`. / 英文 canonical 示例：`README.md`、`SKILL.md`、`references/coding-flow.md`。
- Simplified Chinese examples: `README_zh_cn.md`, `SKILL_zh_cn.md`, `references/coding-flow_zh_cn.md`. / 简体中文示例：`README_zh_cn.md`、`SKILL_zh_cn.md`、`references/coding-flow_zh_cn.md`。
- `AGENTS.md` is the repository instruction entry point; `AGENTS_zh_cn.md` is its Simplified Chinese semantic mirror. Both should point here rather than duplicate these rules. / `AGENTS.md` 是仓库指令入口，`AGENTS_zh_cn.md` 是其简体中文语义镜像；两者应引用本文档，不再重复维护这些规则。
- Configuration, code, generated files, and non-Markdown assets do not require language mirrors unless a task explicitly requires them. / 配置、代码、生成文件和非 Markdown 资源默认不要求语言镜像，除非任务明确提出要求。
- `agents/openai.yaml` is a deliberate exception: user-facing description text must contain both English and Simplified Chinese in the same scalar value, separated by ` | `, with English first. / `agents/openai.yaml` 是明确例外：面向用户的描述文本必须在同一个标量值中同时包含英文和简体中文，英文在前、中文在后，并使用 ` | ` 分隔。

## Pairing requirements | 成对维护要求

When a maintained Markdown document belongs to the bilingual documentation set: / 当 Markdown 文档属于双语文档集合时：

1. Keep an English canonical file and a Simplified Chinese `_zh_cn.md` mirror. / 同时维护英文 canonical 文件和简体中文 `_zh_cn.md` 镜像。
2. If one side is added, renamed, moved, or deleted, make the corresponding change to the other side in the same change set. / 一侧新增、重命名、移动或删除时，必须在同一变更中对另一侧进行对应操作。
3. When semantic content changes on one side, update the other side in the same pull request unless the task explicitly documents why synchronization is temporarily impossible. / 一侧发生语义变更时，应在同一个 Pull Request 中同步另一侧；只有任务明确记录暂时无法同步的原因时才允许例外。
4. Preserve behavior, constraints, architecture, examples, and acceptance semantics across both languages. Translation may be idiomatic; meaning must remain equivalent. / 两种语言中的行为、约束、架构、示例和验收语义必须保持一致。翻译可以自然表达，但含义不能发生变化。
5. Do not silently add requirements to only one language version. / 不得只在某一种语言版本中静默新增规则或要求。

## Same-language reference isolation | 同语言引用隔离

- English Markdown must link to English Markdown when a bilingual target exists. / 当目标存在双语版本时，英文 Markdown 只能链接英文 Markdown。
- Simplified Chinese Markdown must link to the corresponding `_zh_cn.md` target when a bilingual target exists. / 简体中文 Markdown 只能链接对应的 `_zh_cn.md` 文件。
- Language-switch links are the only intended cross-language Markdown links. / 语言切换链接是预期存在的唯一跨语言 Markdown 链接。
- English runtime instructions in `SKILL.md` must load only English files under `references/`. / 英文运行入口 `SKILL.md` 只能加载 `references/` 下的英文文件。
- Simplified Chinese runtime instructions in `SKILL_zh_cn.md` must load only `_zh_cn.md` files under `references/`. / 简体中文运行入口 `SKILL_zh_cn.md` 只能加载 `references/` 下的 `_zh_cn.md` 文件。
- English reference documents must not load or depend on Chinese reference documents, and Chinese reference documents must not load or depend on English reference documents. / 英文 reference 不得加载或依赖中文 reference；中文 reference 不得加载或依赖英文 reference。

## Language-switch links | 语言切换链接

For a bilingual document pair intended for direct human reading, keep a visible language switch near the top when practical. / 面向用户直接阅读的双语文档，在条件允许时应在顶部附近提供明显的语言切换入口。

```md
[English](example.md) | [简体中文](example_zh_cn.md)
```

The exact relative path may differ by directory. Do not use this exception for runtime dependency links. / 具体相对路径可根据目录调整。该跨语言例外不能用于运行时依赖引用。

## `agents/openai.yaml` bilingual text | `agents/openai.yaml` 双语文本

- Keep one YAML field rather than creating language-specific YAML files. / 保留单个 YAML 字段，不创建语言专用 YAML 文件。
- Put English first and Simplified Chinese second. / 英文在前，简体中文在后。
- Separate the two descriptions with exactly ` | `. / 两种语言之间必须使用准确的 ` | ` 分隔。
- Keep both sides semantically equivalent. / 两侧语义保持一致。
- Example: `"English description | 中文描述"`. / 示例：`"English description | 中文描述"`。

## Adding a new documentation file | 新增文档

Before adding a new Markdown document, classify it first. / 新增 Markdown 文档前，先判断它属于哪一类。

- **Bilingual product/Skill documentation**: create both English and `_zh_cn.md` files and follow all rules above. / **双语产品 / Skill 文档**：同时创建英文文件和 `_zh_cn.md` 文件，并遵守以上全部规则。
- **Repository operational metadata**: follow the tool/platform-required filename. If a bilingual mirror is useful and supported, add one without changing the required canonical filename. / **仓库运行或平台元数据**：保留工具或平台要求的 canonical 文件名；如果支持且有意义，可以增加语言镜像，但不能改变平台要求的入口文件名。
- **Generated/vendor/external material**: do not manufacture a translation unless the task requires it. / **生成内容、vendor 内容或外部材料**：除非任务明确要求，否则不要人为补充翻译。

If classification is unclear, prefer the bilingual product/Skill-documentation path. / 如果无法明确分类，优先按双语产品 / Skill 文档处理。

## Required validation | 必须执行的校验

Before completing a documentation change, run: / 文档变更完成前运行：

```bash
python3 scripts/check-multilingual-docs.py
```

A change is not complete while this validator reports an error. The repository CI also runs this validator for relevant pull requests and pushes to `main`. If the validator and these rules disagree, fix the validator and documentation together rather than bypassing the check. / 只要校验器仍报告错误，该文档变更就不能视为完成。仓库 CI 也会在相关 Pull Request 和 `main` push 中运行该校验。如果校验器与本规则不一致，应同时修复校验器和文档，而不是绕过检查。

## Pull-request review checklist | Pull Request 审查清单

For every change that touches bilingual documentation, verify that: / 任何涉及双语文档的变更都要确认：

- English canonical filenames remain unsuffixed. / 英文 canonical 文件名保持无语言后缀。
- Simplified Chinese filenames use `_zh_cn.md`. / 简体中文文件统一使用 `_zh_cn.md`。
- Both language versions are present where required. / 需要成对维护的文档两种语言均存在。
- Same-language links remain isolated except for explicit language-switch links. / 除语言切换链接外，同语言引用保持隔离。
- `SKILL.md` loads only English references. / `SKILL.md` 只加载英文 reference。
- `SKILL_zh_cn.md` loads only Simplified Chinese references. / `SKILL_zh_cn.md` 只加载简体中文 reference。
- Semantic changes are synchronized across the pair. / 语义变更已同步到两种语言。
- `agents/openai.yaml` keeps bilingual descriptive text in the form `English | 中文`. / `agents/openai.yaml` 的描述文本保持 `English | 中文` 形式。
- `python3 scripts/check-multilingual-docs.py` passes. / `python3 scripts/check-multilingual-docs.py` 校验通过。
