# Coding Context Exchange

This module owns Coding Flow context sharing, Semantic Contract transport boundaries, file-backed multi-Agent Context Exchange, and Worker replacement handoff.

All Semantic Contract fields, amendments, context-block rules, Dispatch Preview behavior, event-driven reporting, and Evidence-on-Demand primitives continue to follow [`../shared-protocols.md`](../shared-protocols.md).

## Context sharing and Semantic Contract

### Simple, self-contained tasks

Normal two-Session mode uses a compact prompt: provide only the goal, necessary constraints, relevant paths, and facts to return. Do not make the input-side Agent copy large file contents or project state that the Primary Output Agent can inspect itself.

Single-Agent Luna Mode does not re-encode already-known information into a prompt addressed to itself. Maintain only the minimum stable goal, constraints, key decisions, and acceptance criteria needed in the current context.

### Complex, context-heavy tasks

In normal two-Session mode, when a task clearly depends on substantial conversation, business, or project background, prefer sharing the full relevant context that the host can safely provide with the Primary Output Agent, plus a short Semantic Contract. This avoids making the input-side Agent generate large output simply to redescribe existing background while the Contract stabilizes the currently effective decisions.

Single-Agent Luna Mode continues to use the Semantic Contract as a logical decision anchor but must not resend it to itself as a self-delegation prompt for formal completeness.

## File-backed Context Exchange for multi-Agent Coding

When Coding Flow uses multiple independent execution Agents, reusable cross-Agent context should be externalized into small workspace documents instead of repeatedly passing through parent-generated summaries. This mechanism supplements the Semantic Contract, Decision Checkpoints, Evidence-on-Demand, and each Agent's live context; it does not replace them.

### Workspace layout and ownership

- The parent Agent establishes a **Context Exchange Root** at `<primary-worktree>/.token-io-decoupling/context/`. Here, `primary-worktree` means the working tree used by the current parent/high-value decision Agent to coordinate the task, even when an execution Agent is editing a different worktree.
- The Context Exchange Root is runtime-only coordination state. Do not stage or commit it, do not treat it as a product artifact, and remove it after the workflow unless the user explicitly asks to preserve it. If the host cannot provide shared read/write access to this path, fall back to compact parent-mediated handoffs instead of pretending the shared path exists.
- Assign each independent Worker a stable, filesystem-safe **Context ID** and a dedicated subtree such as `<root>/worker-auth/`. A Worker writes only its own subtree. A successor or escalation Agent creates a new subtree and treats predecessor directories as read-only history.

### Bounded document set

Each active Worker maintains a compact `INDEX.md` containing only the information needed to route context: current `Task`, `Scope`, `Status`, last material update, a one-line purpose for each context document, and any current blocker or handoff target. Create additional documents only when they provide reusable value; recommended names include `findings.md`, `changes.md`, `verification.md`, and `handoff.md`. Do not mechanically create every file or turn the directory into an execution journal.

Context documents may contain stable findings, relevant paths or symbols, execution-level assumptions and local choices, attempted approaches and failure reasons, a concise changed-file summary, exact verification commands and outcomes, remaining work, and pointers to evidence. Prefer references to project files or log locations over copying raw content.

Do not store credentials, secrets, unnecessary personal data, complete logs, complete diffs, large source-file copies, or unrelated conversation history in Context Exchange documents. High-volume raw evidence remains with the Agent that owns it and is expanded only through Evidence-on-Demand when needed.

### Synchronization and handoff

Update reusable context at material milestones, blocking Decision Checkpoints, and before an Agent exits or is replaced; do not write a note after every command or tool call.

When another Agent needs prior work, the parent should pass paths rather than regenerate the background. A narrow dispatch may use a form such as `Context: <INDEX path>; Read: <specific document paths>`. The receiving Agent reads the index first and then only the named documents and direct project files required for its task. It must not recursively load every Worker's directory by default.

The parent Agent should synthesize a new prose summary only when it must integrate multiple contexts, make a high-value decision, or publish an authoritative Semantic Contract amendment. The shared directory is a low-output transport layer, not a reason to bypass the Context Firewall or preload unrelated state.

The Semantic Contract remains authoritative for `Goal`, `Constraints`, `Decisions`, and `Acceptance`. Worker context documents cannot silently override it. If a Worker's findings imply a Contract change, use the existing Decision Checkpoint and amendment path before execution crosses that boundary.

For Worker replacement or reasoning-effort escalation, the predecessor should, when possible, refresh `INDEX.md` and produce a `handoff.md` covering achieved state, failed approaches and evidence, current modifications and verification state, the remaining blocker, and the next useful action. The successor receives a new Context ID and reads the predecessor's index/handoff as read-only input rather than restarting project exploration from zero. If the predecessor is unavailable, the parent may create only the smallest recovery note supported by facts already present; do not reconstruct the full history as a long parent-generated transcript.
