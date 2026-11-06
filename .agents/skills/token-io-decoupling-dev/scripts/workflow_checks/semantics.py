"""中文事件文档必须保留的安全、证据与恢复语义。"""

SEMANTIC_REQUIREMENTS = {
    "README.md": {
        "交付与原生覆盖": (
            "静态规则交付不需要模型/API/Memory/计划服务",
            "Stop/SubagentStop 没有 additionalContext",
            "不是模型注入契约",
            "主动检查 completion_requested",
            "不据此声称全局完成强制或持久重试计数",
        )
    },
    "shared.md": {
        "权限与范围": (
            "实际权限",
            "绝对禁止 Computer Use",
            "Root 负责重要决定和最终验收",
            "用户明确分工优先",
        ),
        "Agent 上下文": (
            "自身对话上下文",
            "Workflow 不提供数据库",
            "任务状态文件",
            "Session Store",
            "不记忆先前调用",
            "不要求计划/Memory 后端",
            "上下文缺失是需指明的证据缺口",
        ),
        "证据与结果": (
            "不能认证事实或授权效果",
            "分别跟踪 implementation/content、documentation 和 Git metadata epoch",
            "不是独立验证",
            "任何结果都不独自授权或宣布完成",
        ),
        "独立工具": (
            "自身当前输入、资源及授权契约",
            "先读回当前状态",
            "不存储 workflow 实时状态",
            "完整内容保全核验",
        ),
        "协作与可见性": (
            "容量预留或执行者建议不创建/派发子级",
            "不通过回收已创建身份/职责隐藏容量使用",
            "适任子级忙时等待",
            "读取完整真实安全返回",
            "不强制提问或计时器",
        ),
    },
    "task-received.md": {
        "判断": (
            "Multi-Agent，预留一个子级",
            "Single-Agent 为零子级",
            "任务开始不自动初始化子级",
            "不构成必需 workflow 持久化步骤",
        )
    },
    "boundary-requested.md": {
        "判断": (
            "下一个有界 Slice",
            "新建/绑定子级前先放行准确任务和 Slice",
            "Root 不立即物化",
            "Single-Agent 保持其拓扑",
            "用户明确方向仍优先",
            "yes 不创建子级",
        ),
        "失败与恢复": ("不因建议失败创建替代者或默认 Root", "不能追认操作授权"),
    },
    "action-observed.md": {
        "判断": (
            "获准读回",
            "implementation/content、documentation 和 Git metadata",
            "当前指纹",
            "实现阶段检查仍是临时证据",
        )
    },
    "progress-reported.md": {
        "判断": (
            "Continue、Amend 或 Stop",
            "Amend 先修改 Contract/Decision",
            "Evidence-on-Demand 是中间请求",
            "不是第四种最终放行选择",
            "必需指令缺失不触发作者源查找",
        )
    },
    "completion-requested.md": {
        "适用范围": ("Root 保留最终验收权", "原生 Stop 提示不能证明"),
        "判断": ("每项标准", "真实最终状态", "独立验证", "未请求 Git 效果", "保留完整字节"),
        "结果与反馈": ("完成候选", "服务不宣布任务完成"),
        "失败与恢复": ("预算耗尽", "不自动阻塞 Stop", "Agent 上下文"),
    },
    "session-resumed.md": {
        "判断": (
            "同 Session 决定和 allocation",
            "不用数据库",
            "获准读回",
            "指令缺失或混合批次阻塞依赖判断",
            "不转向搜索作者文件",
        ),
        "失败与恢复": ("不静默重建 Memory", "不用结构检查结果替代缺失历史"),
    },
}
