# 边界请求 Hook


```json
{
  "schema_version": 1,
  "event_id": "boundary_requested",
  "modes": [
    "single-agent",
    "multi-agent"
  ],
  "required_facts": [
    "objective",
    "proposed_action",
    "scope",
    "session_context"
  ],
  "required_evidence": [
    "authorization_scope"
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

拟执行动作将跨越已放行 Slice、语义决定、路径/效果、Agent allocation 或外部效果边界时触发。未变化 Slice 内的机械步骤不增加判断。

## 适用范围

两种模式；Single-Agent 的子级专属检查为 not_applicable。原生 PreToolUse 适配器是可选守卫，不替代本语义事件。

## 上下文与证据

提供 objective、proposed_action、scope、session_context 及 authorization_scope。包括用户方向、当前 Contract/Slice、实际执行者/身份/能力/权限、路径和预期效果。子级工作另含当前 allocation、获批容量、可用性、职责、返回路径和已放行快照。

## 判断

### 获准动作与 Slice

核对目标、允许变更、返回条件和未放行边界。重要选择未定时只放行获准证据收集；扩大实施前先有当前修订。Continue 仅覆盖下一个有界 Slice，外部效果的明确授权仍单独满足。

### 委派与输出

先遵从用户明确的执行者/职责/输出方向，再考虑可选建议。否则 Root 根据当前任务关联和实际能力判断。执行者/职责建议、大输出分类或未用名额均不创建子级。派发前核验 mode/count、真实身份、职责、能力、权限和空闲情况。复用适任现有子级，忙时等待。使用唯一当前 allocation，不回收已完成身份/职责。增加容量须真实批准；全部维护职责占用不能靠多申请名额解决。新建/绑定子级前先放行准确任务和 Slice。模型/effort 只在创建时检查。Worker 仅返回父级，不递归委派或联系同级。

### 可选资源操作

选用物化/preflight 时，要求准确候选、可信固定根/路径、匹配的独立 grant、当前基线与新鲜整批检查；准备不是应用。必需检查未知、过时、遗漏或失败仍属未解决。只有请求时才按独立资源契约使用计划/Memory；它们不提供 workflow 授权。

候选预检是只读的通用路径/基线检查：唯一支持的 `payload.request.policy_scope: generic_project` 返回 `policy_version: 2`。可信根目录和读取器由操作者提供，payload 和当前目录不能选择。它不验证语言镜像是否存在、Markdown 链接、分层结构或语义等价，不执行代码或授权写入。逐项审查 pass/fail/unknown/not_applicable 和 not_evaluated，包括限制与陈旧基线；按目标仓库自己的要求检查实际最终状态。

受保护的实体化需要当前可信 Worker 绑定/分工、独立授权及固定项目/产物根目录。支持范围为 Primary Output / code_configuration / generic_project，采用有限的 literal_text、json_document 和 fact_markdown 模板，不是项目专用 Skill 或通用文档写入器。prepare 在项目外生成产物，inspect 返回有界分页，apply 在新鲜整批预检和写入时检查后使用同一已审核清单，不重新生成内容。可选模型排序只能选择已提供事实 ID，本地代码渲染已提供事实。配置缺失、拒绝、无效输出或超限会停止准备，不回退自由生成。不得把未报告用量当零，不假定全局回滚或覆盖后续改动的权限；重试前读回 partial/conflict/uncertain 副作用。原生授权输出独立于该可选能力。

### 职责 Decisions 指令

选择与已放行任务和当前 Session 职责匹配的一个已提供职责，或 insufficient_evidence。遵从用户明确分配，不虚构容量、身份、权限或范围。建议不预留、创建或派发。

### 职责选项说明

#### Primary Output

有界代码/配置实现，或 Skill 指令/reference 编写。

#### Change Verification

真正独立的最终状态审查；除具名验证资产外，对被审查输出只读，不把实现职责重新命名为独立验证。

#### Context Bootstrap/Refresh

单独获准的中立事实/指针检索或刷新，不作语义决定或实现。

#### Documentation/Comments & Git Operations

按用户当前分工明确分配的文档/注释或非简单 Git 范围，并具有操作专属授权；不隐含产品变更。

#### insufficient_evidence

必需任务、政策、职责、身份、容量或权限证据缺失/冲突，或没有已提供职责适用。

### 执行主体 Decisions 指令

按语义责任、任务相关上下文、实际能力、当前身份和权限，为已放行任务选择 root、sub_agent 或 insufficient_evidence。用户明确方向跳过该建议。不因建议失败就选择 Root。

### 执行主体选项说明

#### root

Root 在当前分工、范围与输出边界内适合执行；重要决定和验收始终由 Root 保留。

#### sub_agent

适任当前子级应执行已放行任务，或单独获准创建可满足真实容量/职责/Slice 门禁；建议本身不创建。

#### insufficient_evidence

无法确认任一执行者获准且适任，事实冲突，或缺失必需上下文/能力。

### 子代理选择 Decisions 指令

选择一个已提供的不透明 candidate_ref 或 insufficient_evidence。按当前 Session 身份、匹配职责、能力、权限和范围过滤，优先适任空闲候选。只有一个合格/空闲候选可直接选择。多个空闲候选中存在适任空闲 Primary 时仅提供该候选，否则比较所供任务上下文关联。不用 transcript 大小或虚构置信阈值。忙碌候选须等待，不假定可用；失败保持未解决，除非当前获准直接判断有充分依据。

### 子代理选项说明

#### insufficient_evidence

无法根据任务关联和经核验资格安全区分所提供的当前候选，或没有获准候选可用。

### Output Token Decisions 指令

用户明确输出/执行者方向已经确定动作时跳过建议。否则按 Root 所请求输出的形状与预期体量评估是否需要路由；无关输入大小或任意数字阈值不是证据。yes 不创建子级，也不改变已确认 mode/count。

### Output Token 选项说明

#### yes

根据已审阅任务，所请求 Root 直接输出较大。Root 不立即物化：使用适任、空闲、获准子级或等待/挂起。Single-Agent 保持其拓扑并报告限制，用户明确方向仍优先。

#### no

Root 仅可在当前职责、范围和其他全部门禁满足后输出。

#### insufficient_evidence

输出形状、体量或相关任务事实不足以确立安全 yes/no，保持未解决并交 Root 审阅。

## 结果与反馈

continue：动作符合当前获准边界，仍受实际工具守卫约束。needs_evidence：指出缺失授权/能力/身份或候选证据。amend：说明所需 Contract/Slice 修订。wait：指出忙碌子级或待定批准。stop：报告被禁止/冲突动作。not_applicable：以证据说明边界未变化且仍在范围内，或可选分支不存在。

## 失败与恢复

不推断权限，不因建议失败创建替代者或默认 Root。在上下文保留拟执行动作与当前事实；重试前刷新变化事实。事后观察不能追认操作授权。
