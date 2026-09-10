# Coding Context Exchange

This module owns Coding Flow context sharing, Semantic Contract transport boundaries, file-backed multi-Agent Context Exchange, and Worker replacement handoff.

All Semantic Contract fields, amendments, context-block rules, Dispatch Preview behavior, event-driven reporting, and Evidence-on-Demand primitives continue to follow [`../shared-protocols.md`](../shared-protocols.md).

## Context sharing and Semantic Contract

### Simple, self-contained tasks

Normal two-Session mode uses a compact prompt: provide only the goal, necessary constraints, relevant paths, and facts to return. Do not make the input-side Agent copy large file contents or project state that the Primary Output Agent can inspect itself.

Single-Session Coding Mode does not re-encode already-known information into a prompt addressed to itself. Maintain only the minimum stable goal, constraints, key decisions, and acceptance criteria needed in the current context.

### Complex, context-heavy tasks

In normal two-Session mode, when a task clearly depends on substantial conversation, business, or project background, prefer sharing the full relevant context that the host can safely provide with the Worker that owns the current slice, plus a short Semantic Contract. The Primary Output Agent receives implementation context; a Change Verification Agent receives only the final-state verification inputs; and the Documentation/Comments & Git Operations Agent receives the final verified state and approved documentation/comment scope for a docs slice, or the exact repository/worktree/ref/remote scope, current Git evidence, approved content, and explicit authorization for a Git slice. This avoids making the input-side Agent generate large output simply to redescribe existing background while the Contract stabilizes the currently effective decisions.

Single-Session Coding Mode continues to use the Semantic Contract as a logical decision anchor but must not resend it to itself as a self-delegation prompt for formal completeness.

### Role-specific handoffs and parent-led rendezvous

The parent Input-side Reasoning Agent creates and manages all independent Workers. Each Worker receives only the context required for its role:

- **Primary Output** receives the approved implementation Contract, relevant project context, authorized write scope, and the current Interaction Slice. Its focused checks are implementation feedback and are passed forward as a compressed summary.
- **Change Verification** receives a fresh Context ID, the final project state or an isolated verification snapshot, the Contract and acceptance criteria, changed-scope evidence, and the compressed implementation-feedback summary. It must not inherit the Primary Output implementation history, must not modify tracked product/test/documentation files, and must return evidence rather than repairs.
- **Documentation/Comments & Git Operations** receives a fresh bounded context for one explicitly released slice. For a docs slice, it is created only after the verifier passes (or an explicit trivial-task skip) and receives the final verified state, Contract, verifier conclusion, and docs/comment-only scope. For a Git slice, it receives the exact repository/worktree/ref/remote scope, current Git evidence, approved content, applicable workflow, allowed operations, and explicit user/task authorization. It may operate on Git metadata or the remote repository as authorized and may resolve conflicts only with already approved content; it must not make semantic decisions, implement functionality/tests, or infer authorization from another role. It returns compressed documentation or Git-operation evidence.

When a verifier reports a material failure and Primary Output repairs it, the parent provisions a new verifier Context ID and fresh Session for the new final state. Do not reuse a verifier after a material repair: the required independent review must not inherit the earlier implementation or failure history.

### Parent-led rendezvous for multiple Coding Workers

When multiple independent Coding Workers are active, the parent Agent defines an Interaction Slice and feedback boundary for each Worker before dispatch. Each Worker receives its own `Objective`, `Authorized scope/mutations`, `Return conditions`, and `Unreleased boundary`; parallel execution does not authorize a Worker to cross an unreleased boundary or infer permission from another Worker's progress.

Workers may emit compressed Progress Signals within their authorized slices, but the parent owns every blocking Control Checkpoint. At a Control Checkpoint, the parent analyzes the evidence and decides `Continue`, `Amend`, or `Stop` for that Worker, or requests Evidence-on-Demand first. If the Semantic Contract, architecture, scope, permission, security, or public-interface assumptions change, the parent decides whether other Workers continue, receive amended slices, or stop; Workers must not silently continue on stale instructions. The verifier's pass/fail conclusion does not itself release documentation, repair, or Git work; only the parent can release the next dependent slice.

Context Exchange documents transport compressed findings, handoff state, and reusable evidence between Workers; they do not replace this live parent-led control loop. The parent should update the routing index and relevant Worker context at material rendezvous points, not after every Progress Signal or command.

## File-backed Context Exchange for multi-Agent Coding

When Coding Flow uses multiple independent execution Agents, reusable cross-Agent context should be externalized into small workspace documents instead of repeatedly passing through parent-generated summaries. This mechanism supplements the Semantic Contract, Decision Checkpoints, Evidence-on-Demand, and each Agent's live context; it does not replace them.

### Workspace layout and ownership

- The parent Agent establishes a **Context Exchange Root** at `<primary-worktree>/.token-io-decoupling/context/`. Here, `primary-worktree` means the working tree used by the current parent/high-value decision Agent to coordinate the task, even when an execution Agent is editing a different worktree.
- The parent Agent creates and exclusively maintains `<root>/INDEX.md` as the routing index for the shared workspace. It records each active or historical Worker/Context ID and its corresponding dedicated subdirectory, plus only the minimum routing metadata needed by the parent, such as task, scope, status, and handoff relationship. Workers must not edit the root `INDEX.md`.
- The parent Agent provisions a dedicated subdirectory for every independent Worker before that Worker uses file-backed Context Exchange, for example `<root>/worker-auth/`, and tells the Worker the exact directory it owns. A Worker may create, read, update, and delete context documents only inside its own assigned subdirectory during ordinary execution.
- A Worker must never write, rename, move, or delete files in another Worker's subdirectory, the Context Exchange Root itself, or any other Worker-owned location. This write boundary is absolute even when another Worker's documents are visible through the shared filesystem.
- A Worker must not browse or read another Worker's subdirectory by default. Cross-Worker reading is allowed only when the parent Agent explicitly instructs that Worker to read specifically identified documents or paths for a concrete handoff, verification, escalation, or dependency need. The Worker reads only the named material and does not recursively inspect the other directory.
- A successor or escalation Agent receives a new Context ID and a new parent-provisioned subdirectory. Predecessor directories remain read-only to the successor unless the parent explicitly identifies documents to read; the successor never writes into the predecessor's directory.
- The Context Exchange Root is runtime-only coordination state. Do not stage or commit it, do not treat it as a product artifact, and remove it after the workflow unless the user explicitly asks to preserve it.

### Filesystem capability enforcement

The ownership rules above should be enforced by host filesystem permissions or sandbox capabilities whenever possible, rather than relying only on the Worker to follow natural-language instructions.

- `git worktree` provides independent working copies, branches, and a clear physical directory boundary, but **a worktree is not itself a filesystem write-permission mechanism**. `git worktree lock`, sparse-checkout, `.gitignore`, `skip-worktree`, and similar Git features must not be treated as cross-Worker write isolation.
- When the host supports per-Agent sandboxes, container or mount namespaces, path allowlists, or equivalent filesystem capabilities, the parent should configure the smallest capability set before the Worker starts substantive execution:
  - **RW**: that Worker's own code worktree and its dedicated `<root>/<worker-context-id>/` context subdirectory;
  - **RO**: only individual documents or tightly bounded paths from another Worker that the parent explicitly grants for the current handoff;
  - **DENY / not exposed**: `<root>/INDEX.md`, all remaining paths owned by other Workers, and any Context Exchange path not explicitly granted.
- During a documentation slice, tracked functionality and tests remain outside RW capability. During a Git slice, the parent grants only the Git metadata, target worktree, and remote capabilities required for the named operations; tracked-content editing remains denied except for a narrowly scoped, explicitly authorized conflict-resolution edit using already approved content. If conflict resolution requires a new semantic decision, the Worker must stop and return to the parent; a Git role does not grant implementation authority.
- These capabilities are host/process-level constraints, not merely recommendations in a Dispatch prompt. If a Worker drifts semantically and attempts an out-of-scope write, the filesystem layer should reject it.
- If multiple Workers actually run as the same OS user, `chmod` or ordinary Unix owner/group permissions alone generally cannot distinguish Worker identity reliably. Strong enforcement requires a real per-Worker sandbox, separate container/mount namespace, path capability, or equivalent mechanism.
- Cross-Worker sharing should prefer a **targeted read-only capability on the original document**. The parent passes only the document paths and authorization boundary; it does not read the body, copy the body into the prompt, or regenerate a summary merely to transport the same content.
- If the host cannot safely expose a specifically named file from another Worker's directory as read-only, but the parent can still perform filesystem-tool operations, the parent may **mechanically copy** the named original documents into `imports/<source-context-id>/` inside the receiving Worker's own context directory. The copy must be performed by the filesystem/tool layer, not regenerated by the LLM. The copied file is a disposable input snapshot; even if the receiving Worker edits that snapshot, it cannot mutate the source Worker's original document or state.
- Only when the host can provide neither safe targeted read-only access nor filesystem-level copying should the workflow fall back to a compact parent-mediated handoff. Even then, transmit only the stable facts needed for the immediate decision and do not re-encode complete context documents into long parent output.

### Bounded document set

Each active Worker maintains a compact `INDEX.md` inside its own assigned subdirectory. This **Worker-local index** is distinct from the parent-maintained root `INDEX.md`. It contains only the information needed to route that Worker's context: current `Task`, `Scope`, `Status`, last material update, a one-line purpose for each context document, and any current blocker or handoff target. Create additional documents only when they provide reusable value; recommended names include `findings.md`, `changes.md`, `verification.md`, and `handoff.md`. Do not mechanically create every file or turn the directory into an execution journal.

Context documents may contain stable findings, relevant paths or symbols, execution-level assumptions and local choices, attempted approaches and failure reasons, a concise changed-file summary, exact verification commands and outcomes, remaining work, and pointers to evidence. Prefer references to project files or log locations over copying raw content.

Do not store credentials, secrets, unnecessary personal data, complete logs, complete diffs, large source-file copies, or unrelated conversation history in Context Exchange documents. High-volume raw evidence remains with the Agent that owns it and is expanded only through Evidence-on-Demand when needed.

### Synchronization and handoff

Update reusable context at material milestones, blocking Decision Checkpoints, and before an Agent exits or is replaced; do not write a note after every command or tool call.

The parent uses the root `INDEX.md` to track which Worker owns which subdirectory and to decide what context, if any, another Worker should receive. When another Agent needs prior work, the parent should preferably grant a read-only capability on the specifically named original documents and pass only the exact paths and capability boundary in the Dispatch, for example `Own Context RW: <path>; Read-only Context: <specific paths>`. The receiving Agent reads only the Worker-local index and specifically named documents that the parent authorized, plus direct project files required for its task. It must not discover or recursively load other Worker directories on its own.

If targeted read-only capability is unavailable, follow the fallback order from the previous section: use tool-level mechanical copies first, and use a compact parent-mediated handoff only when necessary. The parent must not read complete documents and then regenerate the same content through the LLM merely to transport it between Workers.

The parent Agent should synthesize a new prose summary only when it must integrate multiple contexts, make a high-value decision, or publish an authoritative Semantic Contract amendment. The shared workspace and its capabilities are a low-output transport layer, not a reason to bypass the Context Firewall or preload unrelated state.

The Semantic Contract remains authoritative for `Goal`, `Constraints`, `Decisions`, and `Acceptance`. Worker context documents cannot silently override it. If a Worker's findings imply a Contract change, use the existing Decision Checkpoint and amendment path before execution crosses that boundary.

For Worker replacement or runtime escalation, the predecessor should, when possible, refresh its Worker-local `INDEX.md` and produce a `handoff.md` covering achieved state, failed approaches and evidence, current modifications and verification state, the remaining blocker, and the next useful action. The parent updates the root `INDEX.md`, provisions a new Context ID and subdirectory for the successor, and should first expose specifically named predecessor documents to the successor through host-level read-only capability. If safe read-only exposure is unavailable, mechanically copy those documents into the successor's `imports/` directory before dispatch. The successor does not restart project exploration from zero and never writes into the predecessor's directory. If the predecessor is unavailable, the parent may create only the smallest recovery note supported by facts already present; do not reconstruct the full history as a long parent-generated transcript.
