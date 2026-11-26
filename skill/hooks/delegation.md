# 委派 Hook

## 触发条件

多代理路线规划具体派发、续接或替换时，或运行中的子代理、所需角色与能力变化时。

## 输入与证据

当前任务计划、对应角色描述、同角色实例的真实标识和状态、调用参数与能力证据，以及下一项任务的前置结果。

## 执行要求

1. 按[任务和角色匹配](../references/delegation/delegation-policy.md#任务和角色匹配)选择职责。读取对应定义的职责边界、执行要求和回传证据，确认适合当前任务。
2. 核对该角色的实例、在途工作及派发记录。按[同角色复用与替换](../references/delegation/delegation-policy.md#同角色复用与替换)判断是否续接、排队、首次创建或替换。
3. 确定确需创建时，按[模型与推理强度](../references/delegation/delegation-policy.md#模型与推理强度)确认实际配置。任何创建路径均禁止 Ultra。
4. 按[派发与回执](../references/delegation/delegation-child-dispatch.md)和[上下文交接](../references/delegation/context-exchange-handoff.md)传递必要材料。按[委派交接规则](../references/delegation/delegation-policy.md#派发与结果交接)核对旧实例的未决效果，再按依赖整合已核实结果。

## 输出与落点

子任务、角色、实例标识、可观察状态及已接收证据。发生替换时，记录原因和剩余工作。

## 退出与阻断

派发或续接以实际回执为准。接收结果后核对交付物是否可用于后续工作；依赖仍未满足时留在受影响分支。

## 重新核验

用户指令、任务需要、实例状态或模型及强度设置变化时重新核对相关条件。

## 规则来源

[委派规则](../references/delegation/delegation-policy.md)定义能力核验、角色匹配、同角色复用与替换、交接和模型选择。
