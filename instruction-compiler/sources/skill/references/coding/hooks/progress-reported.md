# 进展反馈 Hook


```json
{
  "schema_version": 1,
  "event_id": "progress_reported",
  "modes": [
    "single-agent",
    "multi-agent"
  ],
  "required_facts": [
    "objective",
    "progress",
    "boundary"
  ],
  "required_evidence": [
    "progress_signal"
  ],
  "allowed_outcomes": [
    "continue",
    "needs_evidence",
    "amend",
    "wait",
    "stop",
    "not_applicable"
  ]
}
```

与本事件一起应用[共享契约](shared.md)。

## 触发

重要结果、新事实、偏离或已声明返回条件需要判断如何继续时触发。普通无变化等待和机械步骤不重启 Control。

## 适用范围

两种模式。Single-Agent 在自身上下文判断；Multi-Agent 子级向 Root 返回精简事实，由 Root 决定放行。

## 上下文与证据

提供 objective、progress、boundary 及 progress_signal。压缩状态、发现、变更路径/范围、检查、问题和需要，并附当前未放行边界及相关变化 epoch。不以投递回执或不完整子级正文替代真实结果。

## 判断

### Control 决策

据当前证据选择 Continue、Amend 或 Stop。Continue 只放行有依据的下一有界 Slice。Amend 先修改 Contract/Decision 及受影响上下文，再核对拟执行工作。Stop 停止依赖工作并报告原因，不通过 Acceptance。Evidence-on-Demand 是中间请求：暂停放行、指出缺失证据，取得后再判断，不是第四种最终放行选择。重要变化使依赖的旧 Control 证据失效。

### 上下文与建议

只取得当前判断需要的最少证据。核对生成背景保留来源标签与准确当前事实；不向另一模型下传过时、冲突或虚构背景。按当前编译规则和真实证据审阅建议。可选检查不可用时，可以充分直接判断替代，不能假定成功或弱化必需守卫。必需指令缺失不触发作者源查找。

### 待处理工作

在 Agent 上下文保留待办目标、继续位置、已完成效果和所需输入。等待子级期间，Root 可继续独立获准工作。在当前范围和已确认容量内复用适任真实子级；辅助/Bootstrap 完成不等于原任务完成。仅增量汇报实质变化，保留必要失败和验收证据。

## 结果与反馈

continue：指出有依据的当前/下一 Slice，不选择写死阶段。needs_evidence：指出证据请求和保留的问题。amend：说明决定/边界修订。wait：指出待返回主体/输入。stop：说明原因及安全汇报。not_applicable：说明没有实质 Control 边界。

## 失败与恢复

无法安全继续时报告阻塞或等待，不反复索取同一证据或重做已完成动作。仅在获准原因变化或明确有界重试适用时重试。原生 SubagentStop 提示本身不能证明本逻辑检查或独立验证已执行。
