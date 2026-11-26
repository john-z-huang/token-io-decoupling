# 2026-11-18 参考目录合并与 Skill 构建

## 参考目录导航

- 将 `docs/rules/references` 下 13 份目录索引的正文和条目顺序并入同级 `README.yaml`，统一从分类或所有者章节进入直属规则和子目录。直属子目录链接改用 `README.yaml`。Layer-03 的索引列表发布为 `layer-03-readme#owners`。 [Layer-01 目录](../docs/rules/references/coding/layer-01-fundamental-concepts/README.yaml) · [Layer-03 目录](../docs/rules/references/coding/layer-03-workflow-checkpoints/README.yaml)
- 更新 Coding 入口、Hook 来源对照、DSL 模板和 README 导航检查。Schema 拒绝参考目录的 `INDEX.md` 输出路径。构建清理带原 DSL 生成标记的旧参考目录 `INDEX.md`，`--check` 以只读方式报告陈旧产物。 [Coding 入口](../docs/rules/workflows/coding.yaml)

## Skill 生成与运行时

- 将 Skill 入口、Coding 选择器和注册元数据集中在 `docs/rules`。执行 `npm run build:skill` 可生成完整阅读版和注册元数据。`docs/skill` 由 Git 忽略，Pi 打包和 MCP 构建会生成所需文件。两份项目说明迁至 `docs/project`，以手写 Markdown 维护。 [Pi Extension 使用说明](../docs/project/PI_EXTENSION.md) · [工作流架构](../docs/project/WORKFLOW_ARCHITECTURE.md)
- TS 工作流运行时直接为原始 YAML 建立快照索引，按 ID 读取当前路线、Hook 和检查点正文。移除先前生成的运行时清单和文本片段。两条路线的检查点 ID、分支和返回逻辑沿用现有合同。 [YAML 读取工具](../archive/pi-coding-workflow/extensions/coding-workflow/reference-data.ts)

## 验证

- 对照原始 YAML 逐份核对 13 份索引的正文与顺序。参考目录合并后导出得到 116 个文件，覆盖 93 份 Hook 来源、1,107 个本地链接和 336 个注入场景。

## 路线目录补充

- 将独立索引中的两条路线与七个阶段的八份 Hook 入口按原顺序合并到 `coding-workflows/README.yaml`。在目录中通过 `routes` 和 `section-01` 读取对应章节。Coding 选择器和维护文档指向统一入口。 [路线目录](../docs/rules/coding-workflows/README.yaml)
- 路线目录采用同一个 `directory-guide` 模板，移除 `directory-index` 类型和模板。构建生成路线 `README.md`，并清理带原生成标记的旧路线索引。合并后共生成 115 个 Skill 文件。
- 扩展现有 Pi 运行时测试。在仅使用原始 YAML 的隔离目录中，单代理和多代理模式都通过 `coding_checkpoint` 的 `rules` 动作读取 `layer-04-readme` 的 `routes` 和 `section-01`。测试核对两条路线和八份 Hook 入口的链接顺序，并逐次比较查询前后的工作流快照与会话记录。专项用例和 `npm test` 全部 147 项测试通过。 [运行时测试](../archive/pi-coding-workflow/extension-tests/runtime.test.mjs)
