import { randomUUID } from "node:crypto";
import type { Catalog } from "../catalog.ts";
import { validateAnswers } from "../startup.ts";
import {
  hasText,
  ROLES,
  type State,
  type WorkflowSession,
  type WorkflowTask,
} from "../host/session-state.ts";

export function makeState(catalog: Catalog, session: WorkflowSession, request: WorkflowTask): State {
  const { sessionId, cwd } = session;
  const { mode, childCount, task } = request;
  if (!hasText(sessionId) || !hasText(cwd, 4096) || !hasText(task, 8000)) {
    throw new Error("会话、目录与任务必须明确");
  }
  if (!["single", "multi"].includes(mode) || !Number.isSafeInteger(childCount) || !hasValidBudget(request)) {
    throw new Error("模式与子代理数量不一致");
  }
  return {
    sessionId,
    cwd,
    catalogHash: catalog.digest,
    runId: randomUUID(),
    mode,
    childCount,
    revision: 0,
    status: "active",
    reason: "",
    epoch: { content: 0, documentation: 0, git: 0 },
    observations: [],
    allocations: [],
    inFlight: [],
  };
}

function hasValidBudget({ mode, childCount }: Pick<WorkflowTask, "mode" | "childCount">): boolean {
  return mode === "single" ? childCount === 0 : childCount >= 1;
}

function validateAllocations(state: Pick<State, "allocations" | "childCount">): void {
  const roles = new Set(state.allocations.map((slot) => slot.role));
  const ids = new Set(state.allocations.map((slot) => slot.id));
  if (
    state.allocations.length > state.childCount ||
    roles.size !== state.allocations.length ||
    ids.size !== roles.size ||
    state.allocations.some(
      ({ id, callId, role, status }) =>
        !hasText(id) ||
        !hasText(callId) ||
        !ROLES.includes(role) ||
        !["running", "completed", "failed", "uncertain"].includes(status),
    )
  ) {
    throw new Error("allocation 无效");
  }
}

// 只写入重载和切换分支后仍需核验的会话事实。
type SessionFacts = Pick<
  State,
  "sessionId" | "cwd" | "catalogHash" | "runId" | "mode" | "childCount" | "audit" | "allocations" | "inFlight"
>;
export type SessionSnapshot = SessionFacts & { version: 3 };

type SavedState = SessionFacts & { version: number; phase?: unknown; step?: unknown };

export function sessionSnapshot(state: State): SessionSnapshot {
  const { sessionId, cwd, catalogHash, runId, mode, childCount, audit, allocations, inFlight } = state;
  return { version: 3, sessionId, cwd, catalogHash, runId, mode, childCount, audit, allocations, inFlight };
}

function boundSnapshot(data: unknown, session: WorkflowSession): SavedState {
  const state = data as SavedState;
  if (
    !state ||
    ![1, 2, 3].includes(state.version) ||
    state.sessionId !== session.sessionId ||
    state.cwd !== session.cwd ||
    !hasText(state.runId) ||
    !hasText(state.catalogHash)
  ) {
    throw new Error("会话快照版本、身份或目录不匹配");
  }
  validateAnswers({ mode: state.mode, count: state.childCount, audit: state.audit });
  return state;
}

function validateActivity(state: SavedState): void {
  if (
    !Array.isArray(state.allocations) ||
    !Array.isArray(state.inFlight) ||
    state.inFlight.length > 256 ||
    state.inFlight.some((id) => !hasText(id))
  ) {
    throw new Error("会话效果记录无效");
  }
  validateAllocations(state);
}

function recoveryHint(state: SavedState, changed: boolean): string | undefined {
  const hints: string[] = [];
  if (changed) hints.push("规则或扩展版本变化，按当前合同重核受影响事实");
  if (hasText(state.phase, 32) && Number.isSafeInteger(state.step)) {
    hints.push("旧路线位置 " + state.phase + "/" + String(state.step) + "，仅供读回参考");
  }
  return hints.join("。") || undefined;
}

export function restoreState(catalog: Catalog, data: unknown, session: WorkflowSession): State {
  const state = boundSnapshot(data, session);
  validateActivity(state);
  const { sessionId, cwd, runId, mode, childCount, audit, allocations, inFlight } = state;
  return structuredClone({
    catalogHash: catalog.digest,
    sessionId,
    cwd,
    runId,
    mode,
    childCount,
    audit,
    allocations,
    inFlight,
    status: "paused",
    reason: "",
    revision: 0,
    epoch: { content: 0, documentation: 0, git: 0 },
    observations: [],
    recoveryHint: recoveryHint(state, state.catalogHash !== catalog.digest),
  });
}
