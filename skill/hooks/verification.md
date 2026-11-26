# 验证 Hook

## 触发条件

主代理接收任务结果、汇总交付物、需要独立验证或修复后进行复核时。

## 输入与证据

验收条件、当前产物、执行证据及适用的验证方法。

## 执行要求

1. 根据任务风险与实际变化选择适用检查。主代理按[证据时效规则](../references/verification/verification-epoch.md)逐项核对用户要求、实际产物与检查结果。
2. 需要独立验证时，按[独立性规则](../references/verification/verification-independence.md)核实执行者和证据。多代理路线可按委派规则使用 [Change Verification](../references/roles/change-verification.md)，由主代理核对返回证据并验收。
3. 发现缺陷时先核对[修复范围](../references/execution/repair-scope-gate.md)，按[修复与复验交接](../references/verification/repair-verification-handoff.md)重查受影响事项。按[结果报告规则](../references/verification/verification-reporting.md)分别记录通过、失败、跳过与受阻。

## 输出与落点

验收条件与实际证据的对应关系、失败原因、跳过或阻断项及残余影响。

## 退出与阻断

必要条件均有支持证据时验收通过。证据过期、验证失败或独立性要求未满足的项目保持未通过状态。

## 重新核验

产物、依赖或验收条件变化，或修复影响既有证据时，重新核验受影响项目。

## 规则来源

验证分工见 [Change Verification](../references/roles/change-verification.md)，核对返回证据见[派发与结果交接](../references/delegation/delegation-policy.md#派发与结果交接)。
