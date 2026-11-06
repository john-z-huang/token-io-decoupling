# 完成请求 Hook


```json
{
  "schema_version": 1,
  "event_id": "completion_requested",
  "modes": [
    "single-agent",
    "multi-agent"
  ],
  "required_facts": [
    "objective",
    "acceptance",
    "results"
  ],
  "required_evidence": [
    "verification_result",
    "final_state"
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

Agent 准备报告任务完成，或准备执行要求最终验收证据的交付时触发。最终声明前由 Agent 主动消费本事件。

## 适用范围

两种模式。Root 保留最终验收权；子级完成仅是其范围内结果。原生 Stop 提示不能证明已执行本检查，也不自动将本契约注入模型。

## 上下文与证据

提供 objective、acceptance、results 及 verification_result、final_state。包括全部适用标准、真实最终状态的当前指纹/epoch、已执行检查及真实状态、独立性要求、范围/效果和未解决项。证据引用或调用方通过声明不是语义证明。

## 判断

### 验收

将每项标准映射到适用的 implementation/content、documentation 和 Git metadata 当前 epoch 证据。必需验证须覆盖真实最终状态；preflight、prepared artifact、apply 回执和临时检查不能替代。分开报告 pass、fail、not-run、unavailable、assumed。要求独立验证时须真实独立。缺失必需检查、未解决失败、能力、权限或变化 epoch 复验均阻止完成声明。

### 文档与 Git

检查获准文档范围、受众、来源及适用的语言/链接/空白检查；影响行为或验收的文档须重新验证内容。Git/外部交付须有准确仓库/ref/remote 和已验证内容的单独授权。未请求 Git 效果时说明 not_applicable，不强制 Git 阶段。保留无关用户改动，不重复已完成效果。

### 独立资源完成

只有请求的计划/Memory/资源工作需要自身完成证据。保留累积记录和来源历史，不用最终摘要替换。仅按自身版本/内容/目标守卫归档匹配的已完成资源，保留完整字节并解决结果不明。独立资源失败仍须可见，但 workflow 本身不引入存储要求。

## 结果与反馈

continue：证据支持交由 Code Agent 审阅验收的完成候选，服务不宣布任务完成。needs_evidence：指出未映射标准或缺失当前证据。amend：指出须审阅的验收/Contract 变化。wait：指出待返回结果或用户动作。stop：以准确状态结束依赖的自动工作，不把停止等同成功。not_applicable：说明此时并非任务完成/交付请求。

## 失败与恢复

在 Agent 上下文保留未完成标准、效果和当前证据。等待、阻塞、不可用或预算耗尽的任务可以如实报告状态并结束当前轮；不自动阻塞 Stop 形成无尽续跑。新证据到达后只恢复受影响工作，不重置预算或编造已通过历史。
