"""Operation descriptions without workflow gates or cross-tool calling order."""

from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS

SERVER_DESCRIPTION = "独立的本地 Codex MCP 开发、任务计划与 Memory 工具。"
SERVER_INSTRUCTIONS = (
    "直接按工具输入 schema 与操作说明选择能力，不要求 workflow 节点、路线、模式、计划、"
    "先前调用或后续工具。每项操作核对自身当前输入、资源状态及授权，遵守用户、仓库与宿主权限。"
    "API 工具使用已配置的进程环境，本地工具不要求 API 配置。写入结果不明时，"
    "先检查实际资源状态，不盲目重复。"
)

TOOL_DESCRIPTIONS = {
    "tools_capabilities": (
        "报告本服务已配置的任务计划、Memory、preflight 和物化依赖。无参数、不写入、"
        "不请求 API；此诊断是可选操作。"
    ),
    "task_plan_update": (
        "使用明确配置的后端创建任务计划或追加有界记录。请求包含 project_root、plan_id、"
        "expected_revision（创建时为 "
        "null）、request_id 和 records。当前修订保护已有内容，相同请求 ID 用于识别重放；"
        "返回状态、原因、修订与读回证据。"
    ),
    "task_plan_complete": (
        "在已配置后端记录现有计划的完成。提供当前修订、请求 ID、criterion_evidence "
        "及结果和限制记录；操作会检查实际存储的标准、"
        "验证结果及未解决阻塞。返回完成或冲突回执，不代表项目验收通过。"
    ),
    "task_plan_archive": (
        "按所提供的当前修订归档已完成计划。检查实际资源并验证完整保全，返回归档回执；"
        "已有资源可来自任何兼容写入方。"
    ),
    "serena_memory_tail_read": (
        "读取本地 Memory 尾部。直接传参，无 payload 信封：memory_path 相对于启动项目的 "
        ".serena/memories，可带 "
        "mem: 和 .md；tail_lines 范围为 0–10000，0 只返回元数据。UTF-8 "
        "内容最多64000字符；拒绝符号链接和根目录外路径。"
        "不创建文件、目录或 API 请求。"
    ),
    "serena_memory_write_check": (
        "对 Memory 尾部执行只读字面包含检查。直接参数为 memory_path、非空 "
        "changed_content（最多64000字符）和 "
        "tail_lines（0–10000），无 payload 信封。返回 success、reason 和窗口证据；"
        "匹配只证明当前文本存在，"
        "不证明谁在何时写入。使用启动项目的 .serena/memories。"
    ),
    "validate_decoupling_compliance": (
        "通过明确配置的只读 preflight 服务检查有界候选覆盖层。payload.request 包含 "
        "generic_project 的 "
        "policy_scope，以及1–64个 create/replace/delete 候选和 absent 或 SHA-256 基线。"
        "不执行候选脚本或写入；缺少磁盘证据返回 unknown，不能当作通过。"
    ),
    "materialize_decoupled_output": (
        "准备、检查或应用1–16个有界 code_configuration 文件。请求提供文件规格或已有 "
        "prepared artifact/receipt，"
        "不能提供调用方身份、分工或权限。操作依赖可信逐调用 Worker binding/assignment "
        "和独立操作者 grant；固定根、允许路径、"
        "当前基线、全批次新鲜 preflight 及写入时授权保护效果。同服务协作锁协调写入。"
        "可直接提供已有 artifact，不要求 workflow 检查点；"
        "缺少可信配置时不可用。"
    ),
    "check_branch_names": (
        "按配置政策检查给定分支名或当前仓库分支。本地验证与 API 判断分别返回，不写 Git。"
    ),
    "check_commit_message": (
        "按配置政策检查给定提交消息。本地验证与 API 判断分别返回，不创建提交。"
    ),
    "check_staged_changes": ("检查仓库真实暂存 diff 的空白错误。纯本地只读，不需要 API 配置。"),
    "stage_repository_paths": (
        "暂存准确的一组仓库相对路径。验证当前 index 并读回暂存路径；会写本地 index。"
    ),
    "commit_repository_changes": (
        "用给定消息及 expected_paths 提交实际暂存路径集合。在本操作内检查现状和消息政策，"
        "运行正常 Git hooks；会写 Git 历史。"
    ),
    "list_repository_worktrees": ("列出绝对仓库根目录对应的 worktree。本地只读，不请求 API。"),
    "switch_repository_branch": (
        "核对真实 checkout 后切换到现有本地分支。会修改 checkout，不发网络请求。"
    ),
    "create_repository_branch": (
        "在当前提交创建本地分支并让 HEAD 指向它，不改变工作树内容或 index。可用 "
        "expected_head_oid 防止提交已变化；不请求网络或模型。"
    ),
    "pull_origin_branch_fast_forward": (
        "仅当实际 checkout 和远端状态允许时，从 origin 快进当前本地分支。使用网络并写 "
        "Git 状态，不强制更新。"
    ),
    "fetch_upstream_branch": (
        "抓取指定 upstream 分支到本地远端跟踪状态。使用网络并写 Git 元数据。"
    ),
    "merge_upstream_branch_fast_forward": (
        "把当前分支快进到已有 upstream 跟踪 ref。只使用当前本地 ref，不抓取或强制更新。"
    ),
    "rebase_repository_branch": (
        "核对当前仓库和发布状态后，把指定分支 rebase 到给定 base。会改写本地历史；保留冲突供检查。"
    ),
    "remove_repository_worktree": ("检查仓库和分支身份后，删除指定的干净 worktree 目录。"),
    "create_repository_worktree": (
        "从已有本地 base，在明确目标路径创建本地分支和新 worktree。检查路径及当前 ref，不同步远端。"
    ),
    "capture_untracked_file_manifest": (
        "读取当前未跟踪文件的有界清单，包含路径、大小及 SHA-256。不复制或暂存文件。"
    ),
    "copy_untracked_files_to_worktree": (
        "按给定未跟踪文件清单复制到明确 worktree，检查当前源 hash 和目标路径。"
        "报告确认复制项与部分失败，不暂存文件。"
    ),
    "configure_project_hooks_path": (
        "核对目标和当前配置后，把仓库 hooks 路径设为给定目录。会写本地 Git 配置。"
    ),
    "audit_issue_pr_policy": (
        "按配置政策读取并评估给定 GitHub Issue/PR 事实。返回本地发现及 API 判断，不修改 "
        "GitHub 资源。"
    ),
    "cleanup_merged_pr_local_branch": (
        "核对已合并 PR 和给定 branch/OID，再依据当前仓库状态清理匹配的本地分支。可能同步 "
        "base，不执行 PR 合并。"
    ),
    "audit_repository_state": (
        "读取绝对仓库根、当前分支、状态及 remote 名称，并查询 GitHub 仓库身份。本地 ok "
        "与 github_error 独立，不写入或调用模型。"
    ),
    "list_github_issue_labels": (
        "读取指定 GitHub 仓库最多100个标签。仅网络读取，不调用模型或创建标签。"
    ),
    "create_github_issue": (
        "用给定标题、Markdown 正文及已有标签创建并读回 GitHub Issue，指派当前认证账号。"
        "分别报告创建和验证。"
    ),
    "push_issue_branch_to_origin": (
        "在当前调用内核对给定 Issue 和真实分支事实后，将当前 Issue 分支推到 origin。"
        "使用网络，不强制推送。"
    ),
    "create_github_pull_request": (
        "为明确 head/base ref 和给定 Issue 关系创建并读回 PR。核对实际资源，分别报告创建和读回。"
    ),
    "merge_github_pull_request": (
        "仅当实际 GitHub 检查及配置的合并政策允许时合并指定 PR；需要此远端写入的授权。"
    ),
    "push_fork_main_fast_forward": (
        "依据真实干净 checkout 及既有 upstream/main 关系，快进 fork 的 origin main。"
        "会网络写入，不强制更新。"
    ),
    "get_codex_session_summary_guidance": (
        "返回如何总结给定会话事实的指引。不读取聊天或 Memory、不调用模型或写文件。"
    ),
    "order_codex_session_sources": (
        "按已核实创建时间对给定会话元数据去重和排序。不访问聊天、Memory、模型或文件系统。"
    ),
    "prepare_codex_session_memory": (
        "验证给定会话事实并准备 Memory payload。不读取聊天或写 Memory，返回数据不授予写入权限。"
    ),
    "decide_skill_workflow": (
        "根据给定分类事实，使用已配置 API 返回可选路线建议。不替调用方选择执行模式，"
        "不调用其它工具。"
    ),
    "decide_codex_session_action": (
        "根据给定会话事实，使用已配置 API 返回可选查询或存储建议。不读取或持久化聊天、Memory。"
    ),
    "generate_skill_content": (
        "根据给定有界证据生成 Issue、PR、提交消息、计划、handoff 或会话摘要候选。"
        "使用已配置 API；Issue/PR 候选包含质量审阅。"
        "返回草案与采用诊断，不发布内容。"
    ),
    "check_api_input": (
        "对完整的拟外发 API 目的和内容执行已配置的本地及 API 检查。返回 passed/status "
        "和诊断，不执行拟议业务动作或授权发布。"
    ),
}

_API_TOOLS = {
    "check_branch_names",
    "check_commit_message",
    "audit_issue_pr_policy",
    "decide_skill_workflow",
    "decide_codex_session_action",
    "generate_skill_content",
    "check_api_input",
}


def tool_description(name: str) -> str:
    """提供本项目维护的中文操作说明，保留固定工具名及各自授权边界。"""
    description = TOOL_DESCRIPTIONS[name]
    if name in _API_TOOLS:
        description += (
            " API 调用使用进程环境中的非空 OPENAI_API_KEY、OPENAI_BASE_URL，"
            "固定 gpt-6-luna，并遵守外发输入审阅边界；凭据和端点不是工具参数。"
        )
    return description


if set(TOOL_DESCRIPTIONS) != TOOLS_SERVER_TOOLS:
    raise RuntimeError("standalone tool descriptions differ from the public inventory")
