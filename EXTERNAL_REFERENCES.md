# External References

[English](EXTERNAL_REFERENCES.md) | [简体中文](EXTERNAL_REFERENCES_zh_cn.md)

This index is for development and maintenance of the `token-io-decoupling` Skill only. It is a reference directory, not execution guidance. Do not load it for ordinary Coding tasks; the Coding workflow does not depend on it.

| Source | URL | Related document | Development use and boundary |
| --- | --- | --- | --- |
| Codex desktop app | https://developers.openai.com/codex/app/ | [delegation-mode-confirmation.md](references/coding/layer-01-fundamental-concepts/delegation-mode-confirmation.md) | General composer background only. It is not a source for the `request_user_input_async` capability. |
| Codex CLI | https://developers.openai.com/codex/cli/ | [delegation-mode-confirmation.md](references/coding/layer-01-fundamental-concepts/delegation-mode-confirmation.md) | Background for interactive terminal use. |
| Codex Prompting Guide | https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide | [delegation-mode-confirmation.md](references/coding/layer-01-fundamental-concepts/delegation-mode-confirmation.md) | Background for presenting multiple suggestions as numbered choices. |
| Claude Code tools reference | https://code.claude.com/docs/en/tools#askuserquestion | [delegation-mode-confirmation.md](references/coding/layer-01-fundamental-concepts/delegation-mode-confirmation.md) | Background for the `AskUserQuestion` interface and its response behavior. |
| MCP Python SDK v2 | https://py.sdk.modelcontextprotocol.io/whats-new/ | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Verify the v2 server/client API and distinguish protocol revision from package version. |
| MCP SDK testing | https://py.sdk.modelcontextprotocol.io/get-started/testing/ | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Design in-memory behavior tests; these do not prove either host client's compatibility or a wire exchange. |
| MCP protocol versions | https://py.sdk.modelcontextprotocol.io/protocol-versions/ | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Verify modern protocol discovery and version evidence independently of SDK major-version labels. |
| MCP client transports | https://py.sdk.modelcontextprotocol.io/client/transports/ | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Verify subprocess stdio tests without GUI interaction or extra Agent Sessions. |
| MCP transport authorization | https://py.sdk.modelcontextprotocol.io/run/authorization/ | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Verify that HTTP token verification does not authenticate stdio or in-memory clients; require a separate trusted launch boundary. |
| OpenAI Decisions | https://developers.openai.com/api/docs/guides/decisions | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Verify typed choice requests and refusal responses for optional semantic evaluation; this reference authorizes no live request. |
| OpenAI Python Decisions reference | https://developers.openai.com/api/reference/python/resources/decisions/methods/create | [Decisions Advisory](references/coding/layer-01-fundamental-concepts/decisions-advisory.md) | Verify the SDK request, fixed choice response, and refusal contract for optional advice; local configuration, authorization, and final judgment remain separate requirements. |
| SQLite backup API | https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Use the database backup API before authorized schema upgrades. |
| uv GitHub Actions integration | https://docs.astral.sh/uv/guides/integration/github/ | [MCP development](mcp/DEVELOPMENT.md) | Verify pinned uv setup, managed Python matrices, and locked dependency installation for CI; workflow execution is separate evidence from local checks. |
| Linux Unix-domain socket credentials | https://man7.org/linux/man-pages/man7/unix.7.html | [MCP development](mcp/DEVELOPMENT.md) | Verify kernel peer credentials for the inherited privileged host channel; this does not establish runtime Session mappings or operation guards. |
| Apple peer credentials | https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getpeereid.3.html | [MCP development](mcp/DEVELOPMENT.md) | Verify native macOS peer-credential authentication independently of Python socket API availability. |
| Codex MCP | https://learn.chatgpt.com/docs/extend/mcp?surface=cli | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Verify local transport controls without inferring trusted per-Agent identity or filesystem isolation. |
| Claude Code MCP runtimes | https://code.claude.com/docs/en/mcp | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Check corresponding client protocol behavior and runtime-dependent limits. |
| Claude Code MCP interface | https://code.claude.com/docs/en/mcp | [Codex caller matching](mcp/CODEX_CALLER_CONTEXT.md) | Check the corresponding runtime before applying Codex request metadata; no equivalent threadId/sessionId contract was documented in the inspected page. |
| Claude Code hook input | https://code.claude.com/docs/en/hooks#common-input-fields | [Codex caller matching](mcp/CODEX_CALLER_CONTEXT.md) | Distinguish hook session_id from MCP request metadata and avoid treating either as independent host authentication. |
