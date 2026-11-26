import type { State } from "../host/session-state.ts";

function hasReadback(state: State, evidence: string[], after: number): boolean {
  return state.observations.some(
    (observation) =>
      evidence.includes(observation.id) &&
      observation.ok &&
      ["read", "check"].includes(observation.effect) &&
      observation.revision > after,
  );
}

export function resumeWorkflow(state: State, evidence: string[]): void {
  if (state.status !== "paused") throw new Error("仅暂停的任务可恢复");
  if (state.inFlight.length) {
    throw new Error("存在结果不明操作，先使用 resolve_effect 结合当前实际读回证据处置");
  }
  if (!hasReadback(state, evidence, state.pauseRevision ?? -1)) {
    throw new Error("恢复前须有暂停后实际读回/检查的证据");
  }
  state.status = "active";
  state.reason = "";
  state.recoveryHint = undefined;
  state.revision++;
}

export function resolveUnknownEffect(state: State, callId: string, evidence: string[]): void {
  if (!state.inFlight.includes(callId) || !hasReadback(state, evidence, state.pauseRevision ?? -1)) {
    throw new Error("须引用实际读回/检查来处置已知的结果不明操作");
  }
  state.inFlight = state.inFlight.filter((id) => id !== callId);
  // 读回可解除执行阻断，不能替宿主推断子任务的终态或归还已占预算。
  state.revision++;
}
