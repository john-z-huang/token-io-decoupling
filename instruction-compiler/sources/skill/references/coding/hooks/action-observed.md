# 动作观察 Hook


```json
{
  "schema_version": 1,
  "event_id": "action_observed",
  "modes": [
    "single-agent",
    "multi-agent"
  ],
  "required_facts": [
    "action",
    "result",
    "scope"
  ],
  "required_evidence": [
    "operation_result"
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

真实工具/子级动作返回、失败、中断，或可能部分产生效果时触发。收集普通结果，不把每次调用变成新阶段。

## 适用范围

两种模式。原生 PostToolUse 只提供观察，不能撤销效果或批准已完成操作。

## 上下文与证据

提供 action、result、scope 及 operation_result。包括真实返回、变更路径、回执、适用的前后状态、当前 epoch、检查和不确定性。Root 依赖子级结果前须读取完整真实返回。

## 判断

### 观察效果

区分请求、已尝试、已完成、失败和不明效果。启动成功、进程回执、prepared artifact 或队列删除不表示任务完成。对照当前文件核对部分应用。效果不明时，先通过获准读回确认再决定重复；不假定回滚，不重放已完成创建/写入/Git 动作。

### 验证 Epoch

按 implementation/content、documentation 和 Git metadata 分类实际变化，只复用未变化覆盖的证据。文档改变可执行含义、Contract 或验收也使内容验证失效。仅 Git metadata 变化不独自使产品检查失效，但 staged/committed 内容须与已验证指纹一致。只推进受影响维度，not-run、unavailable、assumed 检查与通过分开记录。

### 修复证据

修复需有具体失败证据、受影响路径和最小候选；诊断不是修复授权。机械修复留在已放行范围内，语义/范围变化交回修订。改变状态的修复后捕获当前指纹，在依赖完成前取得受影响验证。实现阶段检查仍是临时证据。

## 结果与反馈

continue：可用当前结果支持继续范围内工作。needs_evidence：指出缺失结果/当前状态/覆盖。amend：指出变化的决定或范围。wait：指出待返回结果。stop：报告禁止、无法协调冲突或预算停止。not_applicable：说明无相关效果/变化。

## 失败与恢复

在 Agent 上下文保留真实结果、效果状态和待办。失败或未返回结果不会因另一次调用消失。只有当前证据解决不确定性后才恢复，可选建议不能编造结果。
