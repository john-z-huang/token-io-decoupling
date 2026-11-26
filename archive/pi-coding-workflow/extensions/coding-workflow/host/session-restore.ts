import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Workflow, restoreState } from "../engine.ts";
import type { SessionSnapshot } from "../engine/workflow-snapshot.ts";
import { validateAnswers, type StartupAnswers } from "../startup.ts";
import type { State } from "./session-state.ts";
import {
  CONTEXT_TYPE,
  sessionIdentity,
  STATE_TYPE,
  type RuntimeSession,
  type SessionLedger,
} from "./runtime-session.ts";

interface SnapshotEnvelope {
  state?: Omit<SessionSnapshot, "version"> & { version: number };
  answers?: StartupAnswers;
  enabled?: boolean;
  error?: string;
  releasedReservations?: string[];
}

type SessionEntry = ReturnType<ExtensionContext["sessionManager"]["getEntries"]>[number];

function snapshotEnvelope(entry: SessionEntry): SnapshotEnvelope | undefined {
  if (entry.type !== "custom" || entry.customType !== STATE_TYPE) return undefined;
  return entry.data as SnapshotEnvelope | undefined;
}

export function hasStartupMarker(context: ExtensionContext): boolean {
  const sessionId = context.sessionManager.getSessionId();
  return context.sessionManager.getEntries().some((entry) => {
    if (entry.type !== "custom_message" || entry.customType !== CONTEXT_TYPE + ".start") return false;
    const details: unknown = entry.details;
    return Boolean(
      details && typeof details === "object" && "sessionId" in details && details.sessionId === sessionId,
    );
  });
}

type BoundSnapshot = SnapshotEnvelope & { state: NonNullable<SnapshotEnvelope["state"]> };

function sessionSnapshots(context: ExtensionContext): BoundSnapshot[] {
  const sessionId = context.sessionManager.getSessionId();
  const candidates = context.sessionManager
    .getEntries()
    .map(snapshotEnvelope)
    .filter((entry): entry is BoundSnapshot => entry?.state?.sessionId === sessionId);
  if (!candidates.length) return [];
  const { cwd } = sessionIdentity(context);
  return candidates.filter(({ state }) => state.cwd === cwd);
}

function summarizeLedger(
  states: State[],
  latestVersion: number,
  releasedReservations: Set<string>,
): SessionLedger {
  const allocations = new Map<string, State["allocations"][number]>();
  const runs = new Map<string, State>();
  for (const state of states) {
    for (const slot of state.allocations) {
      if (!releasedReservations.has(slot.id)) allocations.set(slot.id, slot);
    }
    runs.set(state.runId, state);
  }
  const latest = states[states.length - 1];
  // v3 每次写入整个 Session 的未决调用，避免旧分支把已处置调用重新带回。
  const inFlight =
    latestVersion === 3
      ? latest.inFlight
      : [...new Set([...runs.values()].flatMap((state) => state.inFlight))];
  return {
    mode: latest.mode,
    count: Math.max(...states.map((state) => state.childCount)),
    allocations: [...allocations.values()],
    inFlight,
  };
}

export function scanSessionLedger(
  runtime: RuntimeSession,
  context: ExtensionContext,
): SessionLedger | undefined {
  const snapshots = sessionSnapshots(context);
  if (!snapshots.length) return undefined;
  runtime.calls.releasedReservations = new Set(
    snapshots.flatMap((entry) => entry.releasedReservations ?? []),
  );
  const session = sessionIdentity(context);
  const catalog = runtime.getCatalog();
  const states = snapshots.map(({ state }) => restoreState(catalog, state, session));
  return summarizeLedger(
    states,
    snapshots[snapshots.length - 1].state.version,
    runtime.calls.releasedReservations,
  );
}

function restoreAnswers(runtime: RuntimeSession, context: ExtensionContext): void {
  const latest = sessionSnapshots(context).at(-1);
  if (!latest?.state) return;
  const snapshot = latest.state;
  const facts = { mode: snapshot.mode, count: snapshot.childCount, audit: snapshot.audit };
  const answers = validateAnswers(snapshot.version === 3 ? facts : latest.answers);
  if (
    answers.mode !== snapshot.mode ||
    answers.count !== snapshot.childCount ||
    JSON.stringify(answers.audit) !== JSON.stringify(snapshot.audit)
  ) {
    throw new Error("会话启动答案与工作流快照冲突");
  }
  if (runtime.ledger) answers.count = runtime.ledger.count;
  runtime.answers = answers;
}

function applyLedger(workflow: Workflow, ledger: SessionLedger): void {
  workflow.state.childCount = ledger.count;
  workflow.state.allocations = ledger.allocations;
  workflow.state.inFlight = [...ledger.inFlight];
}

function blockRestore(runtime: RuntimeSession, error: string): void {
  runtime.enabled = true;
  runtime.restoreError = error;
}

function restoreBranch(runtime: RuntimeSession, context: ExtensionContext, navigation: boolean): boolean {
  const entry = context.sessionManager
    .getBranch()
    .findLast((item) => item.type === "custom" && item.customType === STATE_TYPE);
  if (!entry && !runtime.ledger?.inFlight.length) return true;
  const envelope = entry ? snapshotEnvelope(entry) : sessionSnapshots(context).at(-1);
  return restoreEnvelope(runtime, context, { envelope, navigation });
}

function restoreEnvelope(
  runtime: RuntimeSession,
  context: ExtensionContext,
  { envelope, navigation }: { envelope: SnapshotEnvelope | undefined; navigation: boolean },
): boolean {
  const state = envelope?.state;
  if (!envelope || !state?.sessionId) {
    blockRestore(runtime, "工作流快照缺少 Session 身份，不能隐式重置");
    return false;
  }
  if (state.sessionId !== context.sessionManager.getSessionId()) return true;
  try {
    if (envelope.error) throw new Error(envelope.error);
    restoreWorkflow(runtime, context, {
      state,
      enabled: envelope.enabled === true,
      navigation,
    });
  } catch (error) {
    blockRestore(runtime, String(error));
  }
  return true;
}

function restoreWorkflow(
  runtime: RuntimeSession,
  context: ExtensionContext,
  request: { state: NonNullable<SnapshotEnvelope["state"]>; enabled: boolean; navigation: boolean },
): void {
  const catalog = runtime.getCatalog();
  const workflow = new Workflow(catalog, restoreState(catalog, request.state, sessionIdentity(context)));
  runtime.workflow = workflow;
  runtime.enabled = request.enabled;
  if (runtime.ledger) applyLedger(workflow, runtime.ledger);
  // 文件系统效果不会随会话树回退，恢复后必须重新核对。
  for (const slot of workflow.state.allocations) {
    if (slot.status === "running") slot.status = "uncertain";
  }
  workflow.pause(
    request.navigation ? "分支/会话导航后须读回实际文件及效果" : "重载/恢复后须读回当前状态，不自动重放操作",
  );
}

function resetForRestore(runtime: RuntimeSession, sessionId: string): void {
  runtime.cancelStartup();
  if (runtime.answerSession !== sessionId) {
    runtime.answers = undefined;
    runtime.ledger = undefined;
  }
  runtime.answerSession = sessionId;
  runtime.workflow = undefined;
  runtime.enabled = false;
  runtime.restoreError = "";
  runtime.calls.releasedReservations = new Set();
  runtime.clearCallTracking();
}

function pauseVolatile(runtime: RuntimeSession, context: ExtensionContext, reason: string): boolean {
  const workflow = runtime.workflow;
  if (
    !runtime.isVolatile() ||
    !workflow ||
    workflow.state.sessionId !== context.sessionManager.getSessionId()
  )
    return false;
  runtime.cancelStartup();
  workflow.pause(reason);
  runtime.persist(context);
  return true;
}

function readSessionHistory(runtime: RuntimeSession, context: ExtensionContext): boolean {
  try {
    runtime.ledger = scanSessionLedger(runtime, context);
    restoreAnswers(runtime, context);
    return true;
  } catch (error) {
    blockRestore(runtime, String(error));
    return false;
  }
}

function restoreSession(runtime: RuntimeSession, context: ExtensionContext, navigation: boolean): void {
  if (pauseVolatile(runtime, context, "volatile 仅保留当前进程状态，须读回实际效果")) return;
  resetForRestore(runtime, context.sessionManager.getSessionId());
  if (!runtime.isVolatile()) {
    if (!readSessionHistory(runtime, context) || !restoreBranch(runtime, context, navigation)) return;
  }
  if (context.hasUI) updateRestoreStatus(runtime, context);
}

function updateRestoreStatus(runtime: RuntimeSession, context: ExtensionContext): void {
  let status: string | undefined;
  if (runtime.restoreError) status = "Coding: 状态需人工恢复";
  else if (runtime.activeWorkflow()) status = "Coding: 等待读回恢复";
  context.ui.setStatus("coding-workflow", status);
}

function startSession(runtime: RuntimeSession, context: ExtensionContext, reason: string): void {
  const lostVolatile = runtime.isVolatile() && !runtime.workflow && ["reload", "resume"].includes(reason);
  if (lostVolatile && (runtime.pi.getFlag("coding-mode") || hasStartupMarker(context))) {
    runtime.generation++;
    runtime.starting = false;
    blockRestore(runtime, "volatile 无跨进程/扩展重载恢复证据；请新建 Session，不能把丢失状态当空预算");
    return;
  }
  restoreSession(runtime, context, ["new", "resume", "fork"].includes(reason));
}

export function registerSessionHooks(runtime: RuntimeSession): void {
  runtime.pi.on("session_start", ({ reason }, context) => startSession(runtime, context, reason));
  runtime.pi.on("session_tree", (_event, context) => {
    if (pauseVolatile(runtime, context, "volatile 不回放历史流程；保留当前预算/效果，须读回后原位处理"))
      return;
    restoreSession(runtime, context, true);
  });
}
