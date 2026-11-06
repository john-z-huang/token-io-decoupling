# 会话恢复 Hook


```json
{
  "schema_version": 1,
  "event_id": "session_resumed",
  "modes": [
    "single-agent",
    "multi-agent"
  ],
  "required_facts": [
    "retained_context",
    "pending_work",
    "effect_status"
  ],
  "required_evidence": [
    "context_source"
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

后续轮次、compact、中断、交接或同 Session 恢复需要 Agent 保留的事实时触发。区分真实新宿主 Session 和同会话继续。

## 适用范围

两种模式。Workflow 提供核对方法，不提供状态存储或恢复服务。

## 上下文与证据

提供 retained_context、pending_work、effect_status 及 context_source。说明当前 Contract/Slice、已确认 mode/count/真实子级身份、待办问题/动作、最后观察效果、证据/epoch 与相关宿主限制。区分保留事实和缺失/过时回忆。

## 判断

### Session 身份与保留上下文

各轮/压缩保留已确认同 Session 决定和 allocation，不重新询问 mode/count、不重新创建子级、不把来源 Session 子级计入 Fork。新身份先建立当前事实再继续依赖工作。Worker 只使用已放行快照；Root 在自身上下文维护规范任务决定。必需上下文缺失须补证据，不用数据库、猜测替代记录或声称旧门禁已通过。

### 不明效果

从待办问题及真实效果状态继续。重复创建/写入/Git 动作前，必要时通过获准读回解决不确定性。不因压缩而重放已回答提问、已完成派发、preflight/应用或已完成外部效果。普通资源工具不是强制状态恢复后端。

### 指令新鲜度

使用单一构建/语言的完整当前批准指令。只取得本动作需要的单元，已有单元仍当前时可复用。指令缺失或混合批次阻塞依赖判断，不转向搜索作者文件。只刷新变化事实、覆盖和能力，不重做独立已完成门禁。模型建议/指纹仍仅辅助输入一致性，不恢复授权。

## 结果与反馈

continue：保留的当前上下文支持具名有界继续。needs_evidence：指出缺失身份、任务、证据或效果事实。amend：指出重要 Contract 变化。wait：指出必需主体/输入。stop：报告无法恢复或被禁止的继续。not_applicable：说明不需要继续。

## 失败与恢复

在 Agent 上下文明确缺口，暂停其依赖动作；独立获准工作可继续。Workflow 不静默重建 Memory、重置计数、恢复隐藏任务记录，也不用结构检查结果替代缺失历史。
