# Coding 委派数量门禁

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

本文档负责多代理子 Agent 数量的建议、确认、锁定和数量预算边界。它消费已确认的模式和状态记录；不定义根模式确认、重新进入、子 Agent 创建或生命周期。

## 数量建议和确认

确认多代理后，根父级建议准确的正整数子 Agent 数量，询问确认并等待。该数量是根指令的总预算，不是阶段或职责数量。

## 数量锁定

数量确认后，在第一次 Dispatch 前锁定。在路线放行前形成恰好等于锁定数量的计划 allocation；这些条目在创建前可以保持 `agent: unbound`。如果在第一次 Dispatch 前发现确有 replacement 需求，父级只能更新尚未锁定的拟定数量或 allocation；数量未锁定时不得创建、spawn 或 handoff 到新子 Agent。随后父级必须重新确认或更新拟定方案，锁定修订后的数量，并重新满足路线放行条件。released 记录随后授权 child-creation owner 消费这些计划 allocation；如果运行时具备安全能力，则创建恰好锁定数量的子 Agent，创建后由该 owner 绑定每个 agent identity 和实际 lifecycle。任何步骤或能力失败时都必须阻塞，不能默默改变数量或创建额外名额。每个独立职责消耗一个名额；复用不创建新名额。数量锁定后，替换、fork、handoff 到新子 Agent 或增加 verifier 都属于新建：全部禁止执行，也不得为当前指令增加 `child_count`。

能力不可用时阻塞数量路线，不能据此默默改变已确认的数量。

## 相关概念

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位数量锁定归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。
