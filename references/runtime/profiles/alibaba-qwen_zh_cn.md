# Alibaba Qwen Coding Model Profile

本文负责 Qwen Code 部署中的具体 Alibaba Qwen 模型绑定和 reasoning-effort 策略。它属于部署策略，而不是 Token I/O Decoupling 架构本身。Host 专属机制由 [`../hosts/qwen-code_zh_cn.md`](../hosts/qwen-code_zh_cn.md) 提供；通用 Session 语义来自 [`../../coding/session-model_zh_cn.md`](../../coding/session-model_zh_cn.md) 和 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md)。

## 部署意图

本 Profile 有意采用非对称组合：

- **Input-side Reasoning** 使用 `qwen3.8-max` 承担高价值语义决策。
- **Primary Output** 使用 `qwen3.8-flash` 承担高体量仓库探索、实现/物化、原始工具交互、调试和机械验证。

这种拆分是有意的。`qwen3.8-flash` 是成本敏感的执行 Runtime；不能仅因为 Max 技术上也能实现代码，就在 Flash 不方便时静默把 Primary Output 移回父级 Max Session。

## 角色绑定与拓扑

Coding Flow 启动时，应先通过 Host Adapter 确认当前 Session 的实际模型，再应用本 Profile。

- **Input-side Reasoning**：首选父级绑定为 `qwen3.8-max`。
- **Primary Output**：必须绑定 `qwen3.8-flash`。
- **正常双 Session 映射**：当前 Session 明确为 `qwen3.8-max` 时，高价值语义决策保留在父 Session，并创建/复用一个显式绑定 `qwen3.8-flash` 的独立 regular Qwen Code subagent 承担 Primary Output。
- **双角色 eligibility**：当前 Session 明确确认自身为 `qwen3.8-flash` 时，只要所需 effort 能满足且没有结构性拆分理由，本 Profile 允许通用 Runtime 使用 Single-Session Coding Mode。不得为了维持形式上的 Max/Flash 拓扑，再额外创建一个 Flash Worker。
- **非预期父 Runtime**：如果当前 Session 既不是明确确认的 `qwen3.8-max` 父级，也不是明确确认的双角色 `qwen3.8-flash` Session，则不得根据模型族相似性或 alias 猜测 eligibility，应遵循 unavailable rule。

因此正常优化部署为：

```text
qwen3.8-max parent
    -> Input-side Reasoning

qwen3.8-flash regular subagent
    -> sticky Primary Output / Primary Execution Session
```

## Qwen3.8 reasoning-effort 档位

Alibaba Cloud 当前对 Qwen3.8 暴露的实际有效 reasoning 档位是 `low`、`medium` 和 `xhigh`。其他通用 effort 名称可能由 provider 映射：`minimal` 映射到 `low`，`high` 与 `max` 映射到 `xhigh`。本 Profile 只使用原生实际有效档位，不把 Qwen3.8 描述成存在独立有效的 `high` 或 `max` 档。

具体策略：

- **`qwen3.8-max` 父级**：架构、产品、跨模块、schema/API、安全/权限、困难调试等实质性高价值决策优先使用 `xhigh`。输入侧上下文本来就被有意控制在低体量，因此适合使用更强 reasoning intensity。
- **`qwen3.8-flash` Primary Output —— 默认 `medium`**：普通实现、仓库探索、迭代调试、常规重构、build/test loop 以及大多数易机械验证的 Coding stage 默认使用 `medium`。这是高体量执行角色的默认成本/能力平衡档。
- **Flash `xhigh`**：只有 output-side stage 确实需要较强局部实现判断时才使用，例如非平凡跨模块重构、困难调试、复杂测试设计、迁移逻辑、并发行为，或者某个 Semantic Contract 已稳定的有界 stage 在 `medium` 下反复失败。
- **Flash `low`**：只用于严格有界、低语义风险且易验证的工作，例如精确搜索/提取、formatter/linter/test 执行、文件/路径元数据收集、字面替换、简单生成表格或其他确定性转换。

输出长度或仓库规模本身不能成为升级到 `xhigh` 的理由。反过来，也不能仅因为 Flash 便宜就把任务强行压到 `low`。

## Qwen Code 中的 effort 控制限制

Profile 定义的是期望的 effective effort，但某个 regular subagent 是否能独立应用该 effort，属于 Qwen Code Host Adapter 的职责。subagent 的 model selector 本身并不能证明存在独立的 per-subagent effort 设置。

因此：

- 精确的 `qwen3.8-flash` 模型身份是 Primary Output 的硬要求；
- Host 可以对该 Worker 独立设置并确认请求的 effort 时，使用上述分级策略；
- Host 无法独立改变 Worker effort、但能确认准确 Flash 模型时，使用部署中显式配置的 Flash effort；如果它与本任务期望档位存在实质差异，应在第一个相关 checkpoint 报告该限制；
- effective value 未知时，不得静默声称 `medium`、`low` 或 `xhigh` 已生效；
- 某任务明确需要比当前已确认 Flash 配置更强的 reasoning 时，应对这个有界 stage 做升级，而不是假装控制成功。

## Escalation

Qwen3.8 在本部署中不存在独立有效的 `max` 档。因此定向 escalation 只有两种主要方式：

1. 把一个有界 Flash 任务从 `medium` 升到已确认的 `xhigh`；或
2. 把语义 blocker / evidence package 返回 `qwen3.8-max` 父级重新决策，然后继续让既有 Flash Primary Execution Session 负责物化。

不得把日常 Primary Output 普遍转给 Max，当成通用 escalation 捷径。Max 负责高价值 reasoning；Flash 仍然是默认有状态执行 owner。

确实需要替换已经阻塞的 Flash Worker 时，优先按照 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md) 保留可复用状态，再创建替代 Worker。

## 成本敏感执行纪律

这套部署的经济价值依赖于：在不削弱语义 ownership 的前提下，把高体量工作稳定留给 Flash。

Alibaba Cloud 公开价格会随区域变化，因此本 Profile 不把具体价格写成规范性的 Runtime 常量。真正的架构不变量是：`qwen3.8-flash` 绑定 Primary Output，而 `qwen3.8-max` 保留给高价值 Input-side Reasoning。价格发生变化时可以重新评估本 Profile，但不能因此静默改写 Core 语义。

active provider 支持 prompt/context cache 时应利用缓存，但 cache hit 不改变角色 ownership。历史 reasoning content 自身可能成为计费输入，因此应避免重复上下文转发，尽量依赖 Qwen Code/provider 原生 continuation 保存执行状态。

## Profile 约束

- 不得用其他 Qwen 模型、泛化的 `fast` fallback 或 inherited parent model 静默替代要求的 `qwen3.8-flash` Primary Output 绑定。
- 实际操作中若使用 `fast`，必须确认它最终确实解析为 `qwen3.8-flash`；否则视为 binding unavailable。
- Flash 启动或 continuation 失败时，不得仅因为 `qwen3.8-max` 技术上能实现，就把父级 Max 当成 Primary Output。
- 精确角色绑定重要时，不得使用无法确认最终解析结果的 provider alias。
- Host 无法为要求独立 Primary Output 的任务创建/复用 regular Flash subagent 时，应停止对应实质性工作并报告阻塞。
- 如果准确模型身份已确认但 effort 无法控制，可以继续严格有界的只读诊断，前提是该任务不依赖更强 reasoning tier。

## 验证状态

本 Profile 基于当前 Alibaba Cloud Model Studio 和 Qwen Code 公开文档中的 Qwen3.8 模型、effort 映射、Skills、subagents、模型选择、continuation 与 provider 配置能力。在真实 Qwen Code CLI run 完成完整 Max-parent/Flash-subagent 映射验证之前，Runtime Registry 不得把这套部署标成本地已 smoke-tested。
