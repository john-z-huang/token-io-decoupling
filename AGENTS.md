# Repository multilingual documentation rules

These rules apply to every Agent or contributor that creates, edits, renames, moves, or deletes documentation in this repository.

## Canonical language layout

- English is the default documentation language.
- Simplified Chinese mirrors use the `_zh_cn` suffix immediately before `.md`.
- Canonical English examples: `README.md`, `SKILL.md`, `references/coding-flow.md`.
- Simplified Chinese examples: `README_zh_cn.md`, `SKILL_zh_cn.md`, `references/coding-flow_zh_cn.md`.
- `AGENTS.md` is the repository instruction entry point. `AGENTS_zh_cn.md` is its Simplified Chinese semantic mirror.
- Configuration, code, generated files, and non-Markdown assets do not require language mirrors unless a task explicitly adds such a requirement.
- `agents/openai.yaml` is a deliberate exception: user-facing description text must contain both English and Simplified Chinese in the same scalar value, separated by ` | `, with English first.

## Pairing requirements

When a maintained Markdown document belongs to the bilingual documentation set:

1. Keep an English canonical file and a Simplified Chinese `_zh_cn.md` mirror.
2. If one side is added, renamed, moved, or deleted, make the corresponding change to the other side in the same change set.
3. When semantic content changes on one side, update the other side in the same pull request unless the task explicitly documents why synchronization is temporarily impossible.
4. Preserve behavior, constraints, architecture, examples, and acceptance semantics across both languages. Translation may be idiomatic; meaning must remain equivalent.
5. Do not silently add requirements to only one language version.

## Same-language reference isolation

- English Markdown must link to English Markdown when a bilingual target exists.
- Simplified Chinese Markdown must link to the corresponding `_zh_cn.md` target when a bilingual target exists.
- Language-switch links are the only intended cross-language Markdown links.
- English runtime instructions in `SKILL.md` must load only English files under `references/`.
- Simplified Chinese runtime instructions in `SKILL_zh_cn.md` must load only `_zh_cn.md` files under `references/`.
- English reference documents must not load or depend on Chinese reference documents, and Chinese reference documents must not load or depend on English reference documents.

## Language-switch links

For a bilingual document pair intended for direct human reading, keep a visible language switch near the top when practical:

```md
[English](example.md) | [简体中文](example_zh_cn.md)
```

The exact relative path may differ by directory. Do not use this exception for runtime dependency links.

## `agents/openai.yaml` bilingual text

For user-facing descriptive text in `agents/openai.yaml`:

- Keep one YAML field rather than creating language-specific YAML files.
- Put English first and Simplified Chinese second.
- Separate the two descriptions with exactly ` | `.
- Keep both sides semantically equivalent.
- Example: `"English description | 中文描述"`.

## Adding a new documentation file

Before adding a new Markdown document, decide whether it is:

- **Bilingual product/Skill documentation**: create both English and `_zh_cn.md` files and follow all rules above.
- **Repository operational metadata**: follow the tool/platform-required filename. If a bilingual mirror is useful and supported, add one without changing the required canonical filename.
- **Generated/vendor/external material**: do not manufacture a translation unless the task requires it.

If classification is unclear, prefer the bilingual product/Skill-documentation path.

## Required validation

Before completing a documentation change, run:

```bash
python3 scripts/check-multilingual-docs.py
```

A change is not complete while this validator reports an error. If the validator and these rules disagree, fix the validator and documentation together rather than bypassing the check.

## Pull-request review checklist

For every change that touches bilingual documentation, verify that:

- English canonical filenames remain unsuffixed.
- Simplified Chinese filenames use `_zh_cn.md`.
- Both language versions are present where required.
- Same-language links remain isolated except for explicit language-switch links.
- `SKILL.md` loads only English references.
- `SKILL_zh_cn.md` loads only Simplified Chinese references.
- Semantic changes are synchronized across the pair.
- `agents/openai.yaml` keeps bilingual descriptive text in the form `English | 中文`.
- `python3 scripts/check-multilingual-docs.py` passes.
