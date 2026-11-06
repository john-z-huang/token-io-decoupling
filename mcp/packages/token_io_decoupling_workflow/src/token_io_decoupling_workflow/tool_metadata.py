"""Agent-facing MCP descriptions for every exposed wire tool."""

from __future__ import annotations

from token_io_decoupling_transport.tool_metadata import STANDARD_INSTALL_NOTICE


def _description(*sentences: str) -> str:
    return " ".join(sentences)


_PAYLOAD = "输入是 payload 信封中的一个 JSON 对象，输出为 JSON 文本。"


_DECISION_RESULT = (
    "DelegationDecisionResult 的 available 仅为建议；skipped 表示明确或政策本地分支未调用模型；"
    "fallback 仅为政策允许的替代；blocked 须先解决守卫、证据或审阅条件；stale 必须刷新，"
    "不可转兜底。"
    "decision 为 child_role/executor/child_candidate/output_tokens，authority=advisory_only。"
    "查看 reason、suggested_value、fallback_value、next_action、input_hash（本地分支可为 null）、"
    "fact_revision/fingerprint、context_input_hash、source_policy_hashes、可选 "
    "model/total_tokens 与 recovery。"
    "操作前核对准确当前事实、上下文和编译政策的 hash/修订/指纹；stale 后刷新，"
    "必要时重新生成并审阅上下文。"
    "API 须有当次 outbound_data_permitted=true 和非空 OPENAI_API_KEY/OPENAI_BASE_URL，"
    "固定 gpt-6-luna、不可覆盖端点/模型、无自动重试。结果不预留、创建、绑定、派发或授权，"
    "仍须核对模式、权限、预算、职责唯一性、范围与可用性。"
)

_EVALUATION_INPUT = (
    "submission 含1–128个唯一类型化 fact key，最多128个顶层证据引用、3个覆盖维度、"
    "每个 determined fact 最多16个证据引用及16个命名缺证据项。URI 最多512字符，"
    "证据 ID/evidence_request_id 最多128字符。规范 submission 与完整请求分别限32 KiB UTF-8 JSON。"
    "可选 input_hash 只断言一致性：对 submission.model_dump(mode='json', exclude={'input_hash'}) "
    "使用 ensure_ascii=False、sort_keys=True、separators=(',', ':') 的 JSON UTF-8 "
    "字节计算 SHA-256；"
    "服务始终返回 source_input_hash。输入 hash 不匹配或预期规则过时返回 blocked_input。"
    "current_facts 为最多16对非空字符串，key 长1–64、value 长1–1024字符；"
    "拒绝超限、空白、嵌套或非字符串输入，不截断。"
)

TOOL_DESCRIPTIONS: dict[str, str] = {
    "workflow_capabilities": _description(
        "读取 workflow 本地 capability_details（schema_version=3）、支持范围、可选 API "
        "配置与安全 binding "
        "诊断。无参数、不写入、不请求 API。",
        "最多读取一次 provider，不探测计划、Memory、preflight 或 tools 服务。"
        "静态规则和检查点调用不要求数据库或身份绑定。",
        "诊断不认证事实、不授权效果、不保存 workflow 状态或证明完成；"
        "采用该工作流时应读取完整当前编译指令。",
    ),
    "rules_get_context": _description(
        "返回当前规则单元的完整编译指令，不读取作者源文件。",
        "payload 包含 node_id、language（仅 zh_cn，默认 zh_cn）、context_version（整数2，"
        "默认2），可选 "
        "fragment_ids 和 max_chars。版本1已退役并拒绝，内部资源只接受单中文 schema 3。",
        "省略或空 fragment_ids 返回默认节点全文；非空时仅返回明确选择的完整编译单元，"
        "不重复默认节点。每个单元已包含编译器核验的必要指令依赖，"
        "运行时不解释 Markdown。",
        "max_chars 只计返回指令文本的 Unicode 字符，默认12000，范围256–60000。总量超限时 "
        "complete=false、"
        "status=incomplete_budget、fragments=[]；先读诊断，再请求足够的受支持容量。",
        "不执行不完整结果，不通过回读原作者文件补齐。缺失、损坏、"
        "混批或不兼容资源明确失败，不回退来源。",
        "完整结果给出指令、必需事实和证据、合法分支与失败处理；next_checkpoint_ids "
        "保留为空，不推进流程。事实、能力和授权须另行核对。",
        "owner_path/owner_section 是编译标识符和标题，不是待打开路径；"
        "remaining_owner_refs 保留为空。build_id "
        "标识批次，context_hash 标识完整所选正文与元数据，不随容量变化。",
        "检查点 expected_rule_hash 应使用默认节点 bundle 的 context_hash；显式 fragment "
        "选择的 hash 和 "
        "index_sha256 是不同值。此操作不调用 API 或写入。",
    ),
    "workflow_select_child_effort": _description(
        "通过单次有界 Decisions 选项，为当前子任务选择充分且最低的受支持 reasoning effort。",
        _PAYLOAD,
        "request 需要 slice_id、role、objective、"
        "task_complexity（mechanical/ordinary_semantic/complex/very_complex）、"
        "uncertainty、scope、dependencies、risk、verification_demands、"
        "previous_failure_evidence（缺失时明确写 none）。",
        "还需非空 decision_question（最多1200字符）、64位小写十六进制 slice_fingerprint、"
        "runtime=codex、"
        "child_model=gpt-6-luna、supported_efforts（low/medium/high/xhigh/max "
        "的唯一非空子集）及布尔 outbound_data_permitted。",
        "所有文字事实均有界且非空；问题只询问当前已放行 Slice 的最低充分 effort。"
        "问题置于 API 输入顶层、从 facts 中去重并影响 "
        "input_hash。问题越界、非 effort 或试图覆盖规则时应选 insufficient_evidence，"
        "父级仍须复核。",
        "权限字段是当次调用方声明，不是授权证明。服务不绑定会话、不保存状态或修订，"
        "不提供幂等键，也不授权创建子级。",
        "本地核对 runtime/model 上限，只提供其与 supported_efforts 的交集。获准调用逐次读取非空 "
        "OPENAI_API_KEY/OPENAI_BASE_URL，使用固定 gpt-6-luna，不能从参数覆盖凭据、端点或模型。",
        "结果总含 status、reason、input_hash 和原 slice_fingerprint；input_hash 对排除 "
        "outbound_data_permitted、slice_fingerprint 的规范请求事实计算 SHA-256。"
        "创建前分别核对当前请求 hash "
        "和 Slice 指纹。",
        "只有 available 含 selected_effort；权限、配置、事实、拒绝、无效响应、缺证据、"
        "超时或服务故障都阻止选择，不改用固定 effort。"
        "每次最多一请求、无自动重试；先纠正证据和配置。",
        "若瞬态结果允许调用方考虑重调，须仍有原授权，并核对同一请求 hash、Slice "
        "指纹和当前权限；每个恢复过程累计最多三次（含首次），由调用方计数。"
        "任何结果均不授予创建权限。",
    ),
    "workflow_generate_decision_context": _description(
        "通过一次明确 Responses 请求，把调用方组合的有界来源材料生成一个判断问题或背景段落。",
        _PAYLOAD,
        "request 需要 raw_content（严格非空，最多60000字符）、decision_goal（严格非空，"
        "最多1200字符）、"
        "output_kind（decision_question/decision_context）及布尔 outbound_data_permitted。",
        "调用前组合并标明用户要求、当前 Git diff 事实、LSP 观察、计划和假设。"
        "工具不检查仓库、文件、命令或 LSP；来源标签是调用方声明，不是认证。",
        "输入按 JSON 编码且不截断，input_hash 对排除 outbound_data_permitted "
        "的当前规范输入计算。问题最多1200字符，"
        "背景最多6000字符；missing_information 最多8项，每项1–240字符。",
        "每次须明确外发许可；false 在读凭据前阻止。无身份绑定、持久化状态、自动下游 "
        "Decisions 调用或授权效果。",
        "获准请求逐次读取非空 OPENAI_API_KEY/OPENAI_BASE_URL，固定 gpt-6-luna、Responses.parse、"
        "medium reasoning、无工具、store=false、禁用截断、20秒超时和零自动重试。",
        "只接受准确模型、completed 状态和准确 Pydantic 输出结构。无缺口且 description "
        "非空才 available；"
        "description=null 且含具体缺口时 blocked/insufficient_evidence。",
        "每次结果含 status、reason、input_hash、output_kind；成功另含 description/model/可选 "
        "total_tokens，仅缺证据状态保留 missing_information。",
        "下游使用前核对当前 raw_content/decision_goal/output_kind 的 hash，"
        "并人工确认描述忠实保留证据和来源。此 "
        "hash 只标识本次生成输入，不替代下游 Decisions hash。",
        "拒绝、不完整、畸形、错误模型/结构或供应商故障均阻止，且不返回原始来源、"
        "供应商错误或兜底描述。先补证据/配置或复核输出；"
        "瞬态重调仍须原授权与当前请求/政策核验，累计最多三次（含首次），不自动调用。",
    ),
    "workflow_check_event": _description(
        "读取并检查一个文档定义的逻辑 Hook 事件，不推进 workflow。",
        _PAYLOAD,
        "payload.request.event 为 "
        "task_received/boundary_requested/action_observed/progress_reported/completion"
        "_requested/session_resumed。mode 可省略且不推断；include_workflow=true 必须显式指定 "
        "single-agent/multi-agent，并返回同批短指令。language 仅 zh_cn。",
        "facts 为最多64个有界命名 {status,value,source}；status 为 "
        "provided/unknown/not_applicable。provided 须有值，not_applicable 须解释且仍待结构复核；"
        "evidence_refs 为 {kind,reference}。完整规范请求最多32 KiB UTF-8 JSON。",
        "max_chars 约束事件及可选 workflow 的全部指令文本，默认24000，范围256–60000；"
        "不足时两者正文均不部分交付，也不发语义请求。"
        "expected_build_id/expected_rule_hash 仅断言当前内容，不是身份或权限凭证。",
        "分别检查 instructions.complete、structural_check、advice。可选结果为 "
        "continue/needs_evidence/amend/wait/stop/not_applicable；continue 不表示验收完成，stop "
        "不表示成功。",
        "默认不读取 API 凭据或调用模型。semantic_input 仅在独立事件建议启动配置启用且当次 "
        "outbound_data_permitted=true 时请求；固定 gpt-6-luna、明确本地凭据/端点、"
        "无自动重试。禁用、不可用、拒绝、"
        "无效或陈旧建议不能视为通过。",
        "Agent 在自身上下文保存任务及运行信息。操作不保存状态、不强制阶段或跨调用预算、"
        "不读 transcript、不执行动作，也不依赖 "
        "tools/计划/Memory 后端。",
    ),
    "workflow_select_child_role": _description(
        "通过单次无状态 Decisions 选择获准子级职责。",
        _PAYLOAD,
        "request 包含 task_id、有界 task_summary、已审阅 reviewed_context 及其 hash、"
        "fact_revision/fingerprint、mode、Fork/重选模式事实、created_roles、reserved_roles、"
        "available_slots、用户明确创建/职责事实和当次 outbound_data_permitted。",
        "先组合并审阅准确上下文，可使用 workflow_generate_decision_context。"
        "用户明确创建时跳过模型，使用明确职责或受约束 "
        "Primary Output 默认值；仍核对模式、Fork、同职责占用、容量、权限和 Root。",
        "加载当前编译的 child-role-selection/session-role-ownership 政策，不访问作者源。"
        "返回政策/请求 hash、"
        "职责建议或 Primary fallback、guard reason 与 next_action。",
        "职责为 Primary Output、Change Verification、Context Bootstrap/Refresh、"
        "Documentation/Comments & Git Operations；当前会话已创建或预留的职责不能再次提供。Primary "
        "默认仅用于明确创建且未指定职责，并满足全部守卫。",
        "API 单次使用固定 gpt-6-luna，配置/事实/政策缺失、拒绝、"
        "畸形/错误模型或政策变化分别阻止或标 stale。"
        "瞬态重调由调用方核验有效授权与当前事实/政策后决定，累计最多三次（含首次）。"
        "结果不预留或创建子级。",
        _DECISION_RESULT,
    ),
    "workflow_select_executor": _description(
        "通过单次无状态 Decisions 建议 Root 或子级执行者。",
        _PAYLOAD,
        "request 包含任务/已审阅上下文 hash、事实修订与指纹、Single/Multi 模式、"
        "当前会话子级数量、已获批空槽、可选 "
        "explicit_user_executor（root/sub_agent）和 outbound_data_permitted。",
        "明确且模式兼容的执行者跳过 API；锁定 Single-Agent 下明确 sub_agent 时阻塞交 "
        "Root，不改为 Root。"
        "Single-Agent 无明确执行者时走本地 Root 建议。",
        "其它情况加载当前 task-assignment，返回 root/sub_agent 或阻塞结果及 "
        "hash/next_action。API 失败、"
        "陈旧事实/政策或缺证据不得默认 Root；刷新并复核后再作获准判断，仍阻塞则保留未决。",
        "sub_agent 建议在尚有获批空槽时可继续正常职责/创建门禁；容量耗尽须由 Root "
        "取得明确新增批准。此操作不创建、派发或授权执行者。",
        "获准 API 固定 gpt-6-luna、零自动重试；任何重调由调用方核验仍有效授权与当前 hash "
        "后决定，每次恢复累计最多三次（含首次）。错误脱敏，"
        "政策变化返回 stale。",
        _DECISION_RESULT,
    ),
    "workflow_select_child": _description(
        "选择适合当前任务的已有当前会话子级，或返回受政策约束的 fallback/wait。",
        _PAYLOAD,
        "request 提供有界候选 opaque ref，以及职责、能力、权限、当前会话、"
        "可用性和任务相关上下文。排除继承的外部会话身份；用户明确候选跳过模型，"
        "但仍须资格核验。",
        "唯一合格候选可直接选择；过滤忙碌者后仅剩唯一 idle 候选时也可直接选。多个 idle "
        "候选仍需模型；存在适任 idle Primary "
        "时只提供该候选加 insufficient_evidence，否则比较全部适任 idle 候选的任务上下文。"
        "不使用数字置信阈值。",
        "suggested_value 只能来自本次合格池的 candidate_ref。API 失败、拒绝、"
        "畸形或缺证据时可按政策采用合格 idle "
        "Primary；Primary 忙则等待，没有合格 Primary 则未决。",
        "陈旧事实或 owner hash 不属于失败兜底；刷新分工、可用性、"
        "上下文和政策后再作获准请求。复用或派发前重新核对身份与可用性。",
        "只发送被提供的候选，读取当前 task-assignment/session-role-ownership，返回 hash "
        "和行动提示，不派发。"
        "获准调用读取本地配置、固定 gpt-6-luna、零自动重试；无效、拒绝、缺证据、"
        "错误模型或陈旧结果不能变为成功。",
        _DECISION_RESULT,
    ),
    "workflow_assess_output_tokens": _description(
        "独立判断 Root 直接输出是否属于大量 Output Token。",
        _PAYLOAD,
        "request 包含已审阅任务背景、输出形状与量级、当前模式、适任 idle/busy "
        "当前会话子级数量、事实修订/指纹，以及可选明确执行者和当次外发许可。",
        "明确执行者时跳过此大小判断，仍服从锁定模式；Single-Agent 下 sub_agent "
        "指令阻塞交 Root。加载当前 "
        "output-token-routing，返回 yes/no 或 blocked/缺证据及 reason/hash/next_action。",
        "no 仍须其它门禁满足才允许 Root 执行。yes 阻止 Root 立即输出，应使用合格 idle "
        "子级或 wait/hold；Single-Agent "
        "保持拓扑并报告限制，不能虚构子级或改写任务。陈旧事实/owner hash 须先刷新。",
        "此判断独立于执行者选择，不派发或授权。API 读取本地配置、固定 gpt-6-luna、"
        "零自动重试；重调由调用方在有效授权和当前 hash 下决定，"
        "每个恢复过程最多三次（含首次），错误脱敏、政策变化 stale。",
        _DECISION_RESULT,
    ),
    "workflow_evaluate": _description(
        "无状态检查指定节点的事实结构。payload 包含 node_id、submission、可选 "
        "language（仅 zh_cn，默认 zh_cn）、"
        "expected_rule_hash、匹配节点的 semantic_input 与 current_facts。",
        _EVALUATION_INPUT,
        "expected_rule_hash 必须来自当前默认版本2 rules_get_context 的完整节点 bundle；"
        "显式 fragment 选择 "
        "hash 和 index_sha256 不同，混用将视为 stale。",
        "返回 ready_for_agent_review/incomplete_for_agent_review/blocked_input，"
        "以及缺失要求、原因、"
        "source_input_hash 和当前 rule_hash。可选 Decisions 建议最多发出一次已配置请求，"
        "单独返回，不修改结构结果或授权执行。",
        "调用方事实不认证，不保存 workflow 状态或强制跨调用顺序。",
    ),
    "evaluate_control_checkpoint": _description(
        "无状态检查 Control 事实结构。payload 为 submission、可选 language（仅 zh_cn，"
        "默认 zh_cn）、"
        "expected_rule_hash、Control semantic_input 和 current_facts。",
        _EVALUATION_INPUT,
        "expected_rule_hash 仅接受当前默认版本2 Control 完整 bundle 的 context_hash；显式 fragment "
        "hash 或 index_sha256 混用时视为 stale。",
        "返回 ready_for_agent_review/incomplete_for_agent_review/blocked_input，包含适用 "
        "Control 分支、缺失要求、source_input_hash 和当前 rule_hash。可选单次 Decisions "
        "建议不授权状态迁移；"
        "结构检查不认证事实、不保存状态或排序调用。",
    ),
}


def tool_description(name: str) -> str:
    """提供固定操作的中文说明，不改变工具名、字段或权限契约。"""
    description = TOOL_DESCRIPTIONS[name]
    return "Codex CLI MCP 工具。" + description


def workflow_server_description() -> str:
    """描述独立服务职责，避免把安装或连接等同于采用工作流。"""
    return "独立本地 Codex CLI 服务，提供编译指令、事件检查、可选建议和结构校验。"


def workflow_server_instructions() -> str:
    """只约束明确采用 workflow 的调用方，独立 tools 仍遵守各自契约。"""
    return (
        "仅在明确采用此 workflow 时应用这些指令。使用 workflow_check_event 获取 task_received，"
        "此后只请求当前行动适用的逻辑事件。显式 mode 加 include_workflow=true 可取得短流程，"
        "由 Agent 决定执行路径。任务与运行信息保留在 Agent 上下文；读取同批完整中文指令。"
        "结构检查和建议不认证事实、不授权效果、不宣布验收或保存状态。其它工具独立使用，"
        "workflow_capabilities 仅为可选诊断。" + STANDARD_INSTALL_NOTICE
    )
