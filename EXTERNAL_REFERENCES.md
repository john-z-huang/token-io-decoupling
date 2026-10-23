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
| SQLite backup API | https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Use the database backup API before authorized schema upgrades. |
| Codex MCP | https://learn.chatgpt.com/docs/extend/mcp?surface=cli | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Verify local transport controls without inferring trusted per-Agent identity or filesystem isolation. |
| Claude Code MCP runtimes | https://code.claude.com/docs/en/mcp | [Enhanced architecture](ENHANCED_ARCHITECTURE.md) | Check corresponding client protocol behavior and runtime-dependent limits. |
