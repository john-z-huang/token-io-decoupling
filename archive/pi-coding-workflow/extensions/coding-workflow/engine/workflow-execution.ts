import { randomUUID } from "node:crypto";
import {
  sameContentAndDocumentation,
  hasText,
  ROLES,
  type Allocation,
  type ContentVerification,
  type Effect,
  type Slice,
  type State,
} from "../host/session-state.ts";

const SLICE_EFFECTS: Effect[] = ["read", "check", "content", "documentation", "git", "memory"];

export function exactPath(path: string): boolean {
  if (!hasText(path, 4096) || path.startsWith("/") || path.startsWith("@") || path.includes("\\")) {
    return false;
  }
  // Slice 只接受字面路径，拒绝控制字符和通配符。
  for (const character of path) {
    if (character.charCodeAt(0) < 0x20 || "*?[]{}".includes(character)) return false;
  }
  return path.split("/").every((segment) => !["", ".", "..", ".git"].includes(segment));
}

function assertSliceFields(slice: Slice): void {
  const { objective, returnConditions, unreleased, paths, mutations } = slice;
  if (
    ![objective, returnConditions, unreleased].every((value) => hasText(value)) ||
    !Array.isArray(paths) ||
    paths.length > 64 ||
    paths.some((path) => !exactPath(path))
  ) {
    throw new Error("Slice 四字段必须完整，路径须为精确仓库相对文件，不接受目录/通配/穿越");
  }
  if (
    !Array.isArray(mutations) ||
    !mutations.length ||
    mutations.some((effect) => !SLICE_EFFECTS.includes(effect))
  ) {
    throw new Error("Slice 影响类型无效");
  }
}

export function releaseSlice(state: State, slice: Slice): void {
  assertSliceFields(slice);
  state.slice = structuredClone(slice);
  state.revision++;
}

interface ExecutionEffect {
  effect: Effect;
  path: string | undefined;
  verification?: ContentVerification;
}

export function executionBlock(state: State, request: ExecutionEffect): string | undefined {
  const { effect, path } = request;
  if (["read", "check"].includes(effect)) return undefined;
  if (state.status !== "active") return "路线已暂停/阻断，先取得当前证据并恢复；不要重放效果";
  // 计划等 Memory 写入由实际工具核验存储范围与授权，仓库文件 Slice 无法描述该目标。
  if (effect === "memory") return undefined;
  const slice = state.slice;
  if (!slice?.mutations.includes(effect)) return "该影响未被当前 Slice 放行";
  if (effect === "git" && !sameContentAndDocumentation(request.verification, state.epoch)) {
    return "Git 操作须另获授权，并引用当前内容与文档验证证据";
  }
  if (path !== undefined && !slice.paths.includes(path)) return "路径不在本次 Slice 的精确路径集合中";
  return undefined;
}

type Reservation = Pick<Allocation, "role" | "callId">;

export function reserveJobs(state: State, jobs: Reservation[]): Allocation[] {
  if (state.mode !== "multi" || state.inFlight.length) {
    throw new Error("委派须使用 Multi-Agent 模式，且不存在未决调用");
  }
  const roles = [...state.allocations, ...jobs].map((job) => job.role);
  if (
    !jobs.length ||
    roles.length > state.childCount ||
    roles.some((role) => !ROLES.includes(role)) ||
    new Set(roles).size !== roles.length
  ) {
    throw new Error("批准预算不足或职责重复；已创建任务的名额不能回收");
  }
  const allocations = jobs.map((job) => ({ id: randomUUID(), ...job, status: "running" as const }));
  state.allocations.push(...allocations);
  state.revision++;
  return structuredClone(allocations);
}

export function addAvailableSlot(state: State, role: string): void {
  const unusedRole =
    ROLES.some((available) => available === role) && !state.allocations.some((slot) => slot.role === role);
  if (state.mode !== "multi" || !unusedRole || state.allocations.length < state.childCount) {
    throw new Error("只能为尚未占用的不同职责，在没有未用名额时明确增加一个名额");
  }
  state.childCount++;
  state.revision++;
}
