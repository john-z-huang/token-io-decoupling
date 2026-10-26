# Enhanced Schema 迁移

[English](enhanced-schema-migrations.md) | [简体中文](enhanced-schema-migrations_zh_cn.md)

本文档负责 Enhanced Root/Worker store 的 Schema 兼容诊断，以及独立迁移、备份和恢复边界。它不负责业务状态字段、授权政策或语义恢复决策。

## 通用规范

### 独立历史与兼容性

Root 与 Worker store 使用相互独立且由程序包固定支持的迁移历史。每个已应用版本都有不可变名称和 checksum；不得编辑或重新编号已发布迁移。受保护写入前，先验证数据库身份、类型、连续历史、checksum、当前版本受支持、结构和完整性。非空数据库缺失历史、类型未知、checksum 冲突、未来版本或结构不兼容时必须 fail closed；不得静默初始化或重建未知 store。

Schema version 与 State Revision、规则 Hash、Verification Epoch 相互独立。迁移须保留现有控制状态、引用、收据和索引；不得重置 Mode/Count、Run、Allocation、生命周期、Revision 或 Epoch。

### 只读状态、迁移和备份

Schema 状态检查是只读操作：报告角色绑定的 store 是否存在、数据库类型、当前/目标版本、待执行版本、兼容性和安全原因。不得创建数据库或父目录、迁移或更改任何状态。缺少可信角色/路径边界时，应在访问状态路径前返回不可用。Root 和 Worker 只能检查各自的 store。

获授权的写入打开操作须先验证可信身份、权限、派生路径和数据库类型。取得有界独占迁移锁后，核对兼容性与历史；受支持的既有数据库存在待迁移版本时，先创建 SQLite 备份。每项迁移及其历史行在同一事务内应用；完成后校验必要结构、完整性和外键，再开放写入。迁移代码由程序包固定提供，不得自行提交事务或调用外部服务。失败时回滚当前迁移，保留此前成功版本与备份。打开 Root 不会扫描或升级全部 Worker store。

恢复是独立的显式授权操作，须由上层先停止所有业务写入。迁移锁本身不能证明写入已停止。替换目标前，验证备份完整受支持的历史和兼容性。不得暴露任意数据库/备份路径或 MCP 恢复操作；不实现自动降级或 last-write-wins 恢复。

## Codex CLI / ChatGPT Desktop 特别优化指令

当前本地实现使用固定迁移执行器和只读 Schema 状态操作。诊断只使用状态查询；受保护迁移仍要求与其他 Root/Worker 状态写入相同的宿主绑定核验和写守卫。协议测试不能证明真实宿主的停写或文件系统边界。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的迁移优化。遵循通用规范，不得推断宿主守卫存在或业务写入已经停止。

## 相关概念

- [Enhanced 状态存储](enhanced-state-store_zh_cn.md) — 负责状态权威、Root/Worker 范围、CAS 和恢复索引。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 负责迁移时必须保留的受保护任务记录值。
- [Coding Delegation Worker Boundary](delegation-worker-boundary_zh_cn.md) — 负责 Worker 数据隔离。
