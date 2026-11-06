# 任务接收 Hook


```json
{
  "schema_version": 1,
  "event_id": "task_received",
  "modes": [
    "single-agent",
    "multi-agent"
  ],
  "required_facts": [
    "task",
    "constraints",
    "session_context"
  ],
  "required_evidence": [
    "request_source"
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

收到新任务、用户重要需求变化，或明确要求重新确立任务时触发。普通工具调用不重启本检查。

## 适用范围

两种模式。只建立当前任务所需事实，不创建 Agent，也不要求外部存储。

## 上下文与证据

提供 task、constraints、session_context 及 request_source。包括当前目标、用户禁止条件、允许仓库/路径/效果、实际能力、已有 mode/count、已定决定、未知项与验收条件。调用方来源标签仍须审阅。

## 判断

### Contract 与证据

区分请求结果、事实、计划和假设。重要架构、接口、安全或验收选择先解决，再实施依赖工作；已有授权内的有界调查可以继续。不确定性需要时在 Agent 上下文保留精简计划和 Decision Brief。明确请求的独立资源工作遵循自身操作契约，不构成必需 workflow 持久化步骤。

### 模式与能力

遵从明确有效的 mode/count 和更高优先级限制。没有当前选择时采用维护中的缺省值：Multi-Agent，预留一个子级；Single-Agent 为零子级。明确自定义数量无效或方向含糊时，只聚焦补问，不推断选择。mode/count 只预留容量，任务开始不自动初始化子级。同 Session 各轮沿用已确认 mode/count；创建仍须核对真实获准边界。

### Agent 上下文

在 Agent 自身上下文保留当前 Contract、事实与继续位置。只识别拟执行工作真正需要的能力缺口，不用产品名或模型标签证明访问权。依赖规则前取得完整、当前、同批次指令。

## 结果与反馈

continue：事实支持已有权限内的有界工作。needs_evidence：逐项指出未知或冲突。amend：指出变化的 Contract/验收。wait：等待具名用户/依赖。stop：报告任务禁止或无法恢复的边界。not_applicable：说明此次并非新/变更任务。

## 失败与恢复

仅暂停依赖缺失事实、指令或权限的工作。保留已确认 mode/count 与已完成效果。新证据到达后从未解决问题继续，不重复已回答提问或已完成操作。
