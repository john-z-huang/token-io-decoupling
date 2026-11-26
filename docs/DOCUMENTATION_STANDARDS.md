# 文档标准与维护规范

维护中的文档使用简体中文，保留现有文件名。技术术语、字段名和命令沿用原写法。本地链接指向实际存在的文件或目录，移动源文件时同步更新使用方。历史快照随原始内容保存，默认构建、安装与验证都跳过 `archive/`。

## 规则源与生成产物

| 源文件 | 内容 |
| --- | --- |
| [Skill 入口](../rules/SKILL.yaml) | 任务编排范围、选路和按需阅读入口 |
| [工作流目录](../rules/workflows/README.yaml) | 单代理与多代理路线、各阶段的 Hook |
| [Hook 目录](../rules/hooks/README.yaml) | 触发条件、输入与证据、执行和交接要求 |
| [开发任务编排参考](../rules/references/README.yaml) | 角色与通用规则，以及规划、委派、执行和验证的专题索引 |
| [主代理职责](../rules/references/roles/main-agent.yaml) | 决策与授权边界、任务组织和最终验收 |
| [子代理角色目录](../rules/references/delegation/delegation-policy.yaml) | 四类角色的职责、派发条件和交接证据 |

`scripts/compile-reference-dsl.py` 从 `rules/` 下的 YAML 源文件生成 `skill/` 中的 Skill 入口和规则阅读版。其中主代理与四类子代理的角色规则由 `rules/references/roles/` 生成到 `skill/references/roles/`。生成的 Markdown 纳入版本控制，与对应的规则变更一并提交。发布到本地管理目录见[安装与更新](../INSTALL.md)。

YAML 使用[规则 Schema](../rules/reference.schema.json)。`markdown_path` 指定输出位置，`blocks` 中的稳定 ID 用于引用和检查点查找。源规则使用相对 `.yaml` 路径和可选的 `#块ID`。编译器核对目标文档及片段，并生成相对的 Markdown 链接和标题锚点。

阶段规则分别维护在 `rules/references/` 下的 `planning/`、`delegation/`、`execution/` 和 `verification/`，由相关 Hook 按需引用。

路线总图用实线标出默认推进条件，用虚线标出回退、跳转和恢复分支。工作流目录维护共用的 `hook-flowcharts` 片段，两条路线编译时在总图下展开片段。每个 Hook 子图按合同章节 ID 声明节点，例如 `TRIGGER`、`INPUTS`、`RECHECK`，并用 `EXECUTION_1` 等节点对应执行要求的编号。增删合同或编号执行要求时同步更新子图。总图和子图中的节点与连线分别写在单独行，跨文档的总图节点使用具名引用。结构校验检查合同覆盖与连线，语义验收核对触发、阻断和恢复分支。

每张图用 `START(["开始"])` 和 `END(["结束"])` 标出本轮流程的边界。所有适用的入口从「开始」分出，完成、受阻、跳过及转交等出口统一连到「结束」。新的触发事件从「开始」进入重新核验。结构校验要求每个节点从「开始」可达，且可汇入「结束」。

## 修改与验证

按 [AGENTS.md](../AGENTS.md#修改与验证) 在 DSL 中审阅和修改指令，并通过命令生成和校验 Markdown。删除规则或变更 `markdown_path` 导致旧产物退役时，先用 `--check` 确认修改前的产物与 DSL 一致，再用 `shasum -a 256` 获取旧产物指纹。将相对 `skill/` 的旧路径和指纹登记到[退役产物清单](../scripts/retired-skill-sha256.json)，编译器在生成时移除指纹匹配的旧产物。

从仓库根目录运行。用 `--template` 查看工作流目录、路线、Hook 目录和合同的模板。用 `--locate-checkpoint` 查询源文件位置和块 ID。新增专题参考规则时，可参考对应目录中的现有文件，例如[任务约定](../rules/references/planning/contract.yaml)或[证据时效](../rules/references/verification/verification-epoch.yaml)。

```bash
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --template workflow-route'
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --template hook-contract'
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --locate-checkpoint MM03 --show'
```

结构检查、生成结果检查和文档链接检查分别运行。

```bash
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --check-structure'
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py'
/bin/bash -c 'uv run --locked --script scripts/compile-reference-dsl.py --check'
/bin/bash -c 'uv run --no-project -- python scripts/check-doc-layer-links.py'
/bin/bash -c 'uv run --no-project --with jsonschema==4.26.0 --with ruamel.yaml==0.19.1 -- python -m unittest discover -s tests'
/bin/bash -c 'git diff --check'
```

修改编排规则时，用与改动对应的场景核对语义。例如，比较明确禁止委派、简单任务和适合委派的任务如何选路。修改委派规则时，同时检查已有角色实例的复用、替换条件和推理强度限制。修改发布内容时，在隔离临时目录验证安装和更新。分别记录检查结果和实际验证过的行为。
