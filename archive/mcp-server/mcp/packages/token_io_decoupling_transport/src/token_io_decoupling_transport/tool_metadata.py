"""Agent-facing descriptions for the single tools MCP server."""

from __future__ import annotations

SERVER_DESCRIPTION = (
    "面向 Pi 的 stdio MCP 服务，提供规则查询、合规预检、Memory 只读检查、"
    "受保护输出物化和通用 Git/GitHub 开发工具。"
)


def _description(*sentences: str) -> str:
    return " ".join(sentences)


_PAYLOAD = "Input is one JSON object in the payload envelope; output is JSON text."

TOOL_DESCRIPTIONS: dict[str, str] = {
    "serena_memory_tail_read": _description(
        "Read the last N logical lines from a local project Memory file. Two direct arguments, "
        "no payload envelope: memory_path is a project-relative name under .serena/memories, "
        "with optional mem: prefix and .md suffix. Absolute, global, and external paths are "
        "rejected. "
        "tail_lines is a strict integer 0..10000; zero returns only line-count metadata. "
        "The returned content is bounded to 64000 characters; oversized windows fail rather than "
        "silently truncate. Returns status/reason, canonical Memory/path identity, total_lines, "
        "returned_lines and the selected line range/content on success. Files are opened as "
        "UTF-8; symlinks and paths outside the local Memory folder are rejected. "
        "Project scope is fixed to the tools server's actual startup directory. The tool "
        "reads only files under that directory's .serena/memories folder, with no parent/"
        "sibling/project discovery and no installation-time project binding. It uses Python "
        "standard-library file operations only; it does not require Serena-Agent or another "
        "local program. Missing folders or files return unavailable. Rejects "
        "traversal, symlinks, non-regular files, out-of-root targets, and oversized tail windows. "
        "No files/directories, state, models or API requests are written or invoked. "
        "Missing files return unavailable. No files or directories are created, and no "
        "revision/idempotency key is used.",
    ),
    "serena_memory_write_check": _description(
        "Quick read-only literal containment check of expected text in a Serena Memory tail. "
        "Three direct arguments, no payload envelope: memory_path follows serena_memory_tail_read; "
        "changed_content is nonempty text of at most 64000 characters; tail_lines is a strict "
        "integer 0..10000. Invokes the same local tail-read implementation exactly once and "
        "matches changed_content literally against its returned content, without regex or text "
        "normalization. Returns a compact success flag/reason and selected-window evidence; "
        "does not echo the expected text or full tail. A match only proves the text is currently "
        "present in that window: pre-existing text may match, and a valid edit outside the "
        "window may not. It does not prove a recent write occurred, preservation, semantic "
        "correctness, append-only history or concurrency/CAS safety, and cannot replace required "
        "full-content acceptance or archive comparisons. Same startup-directory scope, path "
        "checks, UTF-8 encoding, and tail limits as tail read. No write, model/API request; "
        "no revision/idempotency key. Treat unavailable/error as unverified; investigate or use "
        "an appropriately sized authorized window without claiming the write itself failed.",
    ),
    "rules_get_context": _description(
        "Load a checkpoint's legacy owner context or an explicit version-1",
        "indexed fragment bundle.",
        "Legacy payload: node_id (registered checkpoint enum) and language",
        "(en by default; en or zh_cn).",
        "When context_version and all extension fields are omitted, return the unchanged legacy",
        "RuleContext fields, owner text, and context hash. fragment_ids and max_chars require",
        "context_version=1; unknown fields and unsupported versions fail validation.",
        "Version 1 starts with the node's indexed default fragments, adds any",
        "explicit fragment_ids,",
        "and resolves only the index's declared dependency edges in deterministic order.",
        "The response contains bounded node metadata and whole text fragments;",
        "node metadata is not",
        "charged to max_chars. max_chars counts Unicode characters",
        "in fragment text only, defaults",
        "to 12000, and is limited to 256..60000. No fragment is truncated.",
        "index_sha256 binds the canonical versioned index; context_hash binds it",
        "with node metadata, returned fragment text/hashes, the budget result, and",
        "the remaining-owner-reference report.",
        "complete=true means every requested fragment in the explicit index closure was loaded; it",
        "does not mean the task's other direct owners or linked documents have been read.",
        "remaining_owner_refs is a bounded list of local Markdown links found in",
        "returned fragments whose target section is not in the returned closure;",
        "it marks references to read separately,",
        "not rules already included. The list is capped at 16 with a truncation flag.",
        "Budget omissions and missing owner files/headings appear in missing_fragments with",
        "complete=false and an incomplete status. Invalid paths/symlinks, unknown IDs, duplicate",
        "index IDs, dependency cycles, and duplicate real headings fail closed.",
        "owner_path is repository-relative source provenance under skill/, not",
        "an installed Skill",
        "file path. Installed servers use their packaged versioned index and normalized fragments;",
        "fragment hashes cover the same trimmed text returned by either source.",
    ),
    "validate_decoupling_compliance": _description(
        "Run a bounded, read-only preflight over a candidate document overlay before an "
        "authorized write.",
        _PAYLOAD,
        "Payload envelope: request.policy_scope is skill_maintenance or generic_project; "
        "request.candidates has 1-64 unique entries. Each entry has a canonical "
        "repository-relative POSIX path (at most 512 characters), operation=create/replace/delete, "
        "baseline={state:absent} for create or {state:sha256,value:<64 lowercase hex>} for "
        "replace/delete, and content for create/replace. A file is limited to 131072 Unicode "
        "characters and the whole batch to 524288 UTF-8 bytes.",
        "The trusted CompliancePreflightService root and allowed policy scopes are fixed by "
        "operator startup code loaded only through --compliance-factory MODULE:CALLABLE. Payload "
        "and current working directory cannot choose a root. Without a configured reader, the "
        "tool performs no path probe and disk/baseline evidence is unknown. A disallowed scope "
        "is not evaluated.",
        "For skill_maintenance, Chinese documents are the sole authority; bilingual_mirror is "
        "not_applicable. Checks cover Markdown layer links and direct targets, and Layer-01 "
        "three-section structure when applicable. The overlay covers all submitted candidates. "
        "generic_project returns not_applicable for Skill-maintenance checks. The implementation "
        "never imports or executes candidate-repository scripts.",
        "Returns overall status fail/unknown/pass/not_applicable, policy_version=1, bounded "
        "per-rule check objects with rule_id, path/line/reason evidence, and an explicit "
        "evidence_missing list, limits, and not_evaluated entries. Unknown checks name the "
        "missing evidence; other checks use an empty list. Overall precedence is fail, then "
        "unknown, then pass; not_applicable checks do not mask active results. Link-target and "
        "output-check limits turn omitted evidence into unknown.",
        "This is a read-only lookup: no target file writes, API request, subprocess, reverse "
        "inbound-link scan, proof of semantic correctness, or full CI run. Unknown means "
        "the relevant disk evidence could not be safely verified; correct scope, baseline, path, "
        "reader configuration, or budget issues and rerun against current content.",
    ),
    "materialize_decoupled_output": _description(
        "Prepare, inspect, or apply 1–16 files per request using an explicitly configured trusted "
        "output-materializer factory. The typed payload has an action (prepare/inspect/apply), a "
        "bounded batch of file specifications, and action-specific manifest or receipt hashes; "
        "it cannot supply caller identity, assignment, grant, or authorized=true. Each file is "
        "limited to an authorized project-relative path, operation, template, and bounded content, "
        "and prepare also enforces the batch byte limit. The server requires the current bound "
        "Worker role, passes the per-call binding to the materializer, and independently verifies "
        "the startup-injected authorization provider's current assignment and hash plus a separate "
        "operator grant. It rechecks authority between phases and enforces pinned roots, allowed "
        "paths/operations/templates, a fresh whole-batch 185 result before writes, candidate "
        "baselines, receipts, and Same-service cooperative locking. Without both trusted providers "
        "the tool is unavailable or denied before writes."
    ),
}


def tool_description(name: str) -> str:
    """Return metadata for each locally registered utility."""
    try:
        description = TOOL_DESCRIPTIONS[name]
    except KeyError as exc:
        raise ValueError(f"missing Agent-facing metadata for MCP tool: {name}") from exc
    if name == "materialize_decoupled_output":
        recovery = (
            "Missing binding, revoked authority, stale baseline, failed preflight or unsafe paths "
            "deny writes. On uncertain apply, inspect the same prepared identity "
            "and current hashes."
        )
    else:
        recovery = (
            "This read-only utility does not authenticate supplied facts or authorize execution. "
            "Correct invalid input or stop on failure."
        )
    return "Local MCP tool. " + description + " " + recovery


def tools_server_description() -> str:
    return SERVER_DESCRIPTION


def tools_server_instructions() -> str:
    return (
        "按实际发现的工具 Schema 和说明核验输入、效果及成功条件。"
        "Pi 的 codemode 可用 searchTools 和 describeTool 发现工具，hidden 不可绕过。"
        "流程由宿主协调，规则查询、预检和建议只提供辅助证据。\n\n"
        "repo_path 使用经核实的绝对仓库根。每项写入需要当前动作、目标和范围的用户授权，"
        "并遵守实际宿主审批。工具说明中的 Codex writes approval 仅适用于提供该机制的宿主；"
        "在 Pi 仍须遵守其实际权限。能力缺口仅在现有授权与同等校验内由宿主补足。"
        "实际拒绝或校验失败不可换入口绕过，部分成功或结果不明先只读回查。"
        "物化单独核验逐次可信 Worker 绑定、任务分配和操作员 grant；"
        "stdio 连接或请求自报字段不能建立身份或隔离。\n\n"
        "check_api_input 会把最终用途和内容发往配置的审核服务。"
        "在任务允许的范围内无需递归审核，审核通过后可按原用途和目的地外发同一内容。"
        "用途、内容、策略或目的地变化时重新核对范围并按需重审。更高优先级限制和实际拒绝继续有效。"
        "业务 API 自动审核实际请求；审核结果不授权发布或其他写入。"
        "不传凭据或无关私有数据。按工具说明处理超时和失败，不盲目重跑。\n\n"
        "起草 Issue/PR 时提供当前已核实事实、证据指针与缺口；"
        "涉及 Git 交付时核对目标 base/head、待交付的完整提交范围及最终 diff。"
        "生成结果须结合实际证据审阅并核对质量状态，发布需独立授权。"
    )
