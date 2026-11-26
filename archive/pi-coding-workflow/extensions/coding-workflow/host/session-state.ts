import type { Mode } from "../catalog.ts";
import type { Audit } from "../startup.ts";

export const EPOCH_DIMENSIONS = ["content", "documentation", "git"] as const;
export const WORKFLOW_HISTORY_LIMIT = 128;
export type Dimension = (typeof EPOCH_DIMENSIONS)[number];
export type Epoch = Record<Dimension, number>;
export type ContentVerification = Pick<Epoch, "content" | "documentation">;
export type Effect = "read" | "check" | Dimension | "memory";

export const ROLES = [
  "Primary Output",
  "Change Verification",
  "Context Bootstrap/Refresh",
  "Documentation/Comments & Git Operations",
] as const;
export type Role = (typeof ROLES)[number];

export interface Observation {
  id: string;
  tool: string;
  effect: Effect | "user" | "delegate";
  ok: boolean;
  epoch: Epoch;
  revision: number;
}

export type ObservationInput = Pick<Observation, "id" | "tool" | "effect" | "ok">;

export interface WorkflowSession {
  sessionId: string;
  cwd: string;
}

export interface WorkflowTask {
  mode: Mode;
  childCount: number;
  task: string;
}

export interface Slice {
  objective: string;
  paths: string[];
  mutations: Effect[];
  returnConditions: string;
  unreleased: string;
  evidence: string[];
}

export interface Allocation {
  id: string;
  role: Role;
  callId: string;
  status: "running" | "completed" | "failed" | "uncertain";
}

export function hasText(value: unknown, limit = 2000): value is string {
  return typeof value === "string" && value.trim().length > 0 && value.length <= limit;
}

export function requireActive(state: State): void {
  if (state.status !== "active") throw new Error(`当前为 ${state.status}：${state.reason}`);
}

export function requireEvidence(state: State, evidence: string[]): void {
  if (
    !Array.isArray(evidence) ||
    evidence.length < 1 ||
    evidence.length > 16 ||
    evidence.some((id) => !state.observations.some((observation) => observation.id === id))
  ) {
    throw new Error("必须引用当前运行中真实观察到的工具调用或用户输入；引用不是语义真实性证明");
  }
}

export interface State extends WorkflowSession, Omit<WorkflowTask, "task"> {
  catalogHash: string;
  runId: string;
  audit?: Audit;
  revision: number;
  status: "active" | "paused";
  reason: string;
  pauseRevision?: number;
  epoch: Epoch;
  scopeRevision?: number;
  slice?: Slice;
  observations: Observation[];
  allocations: Allocation[];
  inFlight: string[];
  capabilityChanged?: boolean;
  recoveryHint?: string;
}

export function pauseWorkflow(state: State, reason: string): void {
  state.status = "paused";
  state.reason = reason;
  state.slice = undefined;
  state.pauseRevision = state.revision++;
}

export function recordMutation(state: State, dimension: Dimension): void {
  state.epoch[dimension]++;
  state.revision++;
}

export function sameContentAndDocumentation(
  previous: ContentVerification | undefined,
  current: Epoch,
): boolean {
  return previous?.content === current.content && previous.documentation === current.documentation;
}

interface SessionStatus extends State {
  observationCount: number;
  observationsOffset: number;
  nextObservationsOffset: number | null;
}

export function sessionStatus({ state }: { state: State }, offset?: number): SessionStatus {
  const { observations, ...status } = state;
  const start = offset ?? Math.max(0, observations.length - 24);
  const end = start + 24;
  return {
    ...status,
    observationCount: observations.length,
    observationsOffset: start,
    nextObservationsOffset: end < observations.length ? end : null,
    observations: observations.slice(start, end),
  };
}
