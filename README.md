# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` is an Agent orchestration Skill that separates high-value semantic decisions from high-volume state consumption and output materialization.

It provides two independent flows: **Coding** for repository and development work, and **Multimodal** for GUI/browser, video, image, and other visual-state work. Start with [`SKILL.md`](SKILL.md); it routes each task to the references required for its current stage.

## Documentation

- [`SKILL.md`](SKILL.md): primary routing entry point.
- [`BEST_PRACTICES.md`](BEST_PRACTICES.md): optional current Codex/OpenAI usage guide.
- [`references/`](references/): detailed Flow, Coding, Runtime, Host, and Profile documents.
- [`MULTI_LINGUAL.md`](MULTI_LINGUAL.md): bilingual documentation rules.
