import type { ExtensionContext, ExtensionToolContext } from "@earendil-works/pi-coding-agent";
import type { Workflow } from "./engine.ts";
import {
  resolveSubagentAdapter,
  subagentInput,
  subagentModelInput,
  type SubagentAdapter,
} from "./subagent-adapter.ts";
import type { Audit } from "./startup.ts";
import { fileEffect, scopedPath, type ToolCallState } from "./tool-guards.ts";
import type { DelegateInput, DelegateJob } from "./tool-schemas.ts";
import { ROLES, type Allocation, type Epoch } from "./host/session-state.ts";

interface DelegateInvocation {
  callId: string;
  input: DelegateInput;
  signal: AbortSignal | undefined;
}

interface DelegationHost {
  context: ExtensionToolContext;
  calls: ToolCallState;
  isDelegate(name: string): boolean;
  persist(context: ExtensionContext): void;
}

interface PreparedJob {
  job: DelegateJob;
  modelInput: Record<string, string>;
}

interface JobDispatch {
  invocation: DelegateInvocation;
  prepared: PreparedJob;
  allocationId: string;
}

interface BatchPreflight {
  adapter: SubagentAdapter;
  cwd: string;
  claimedPaths: Set<string>;
}

function checkWritePath(workflow: Workflow, path: string, batch: BatchPreflight): void {
  const canonical = scopedPath(batch.cwd, path);
  if (canonical !== path || !workflow.state.slice?.paths.includes(path) || batch.claimedPaths.has(path)) {
    throw new Error("子任务写入必须在 Slice 内且并行任务路径不冲突");
  }
  const effect = fileEffect(path);
  const blocked = workflow.canRun(effect, path);
  if (blocked) throw new Error(blocked);

  const isSkillDocument = path.startsWith("docs/skill/") || path.endsWith("/SKILL.md");
  if (effect === "documentation" && !isSkillDocument) {
    throw new Error("普通文档由 Root 处理；Primary 仅可承接 Skill 文档");
  }
  batch.claimedPaths.add(path);
}

function checkWritePaths(workflow: Workflow, job: DelegateJob, batch: BatchPreflight): void {
  if (job.paths.length && job.role !== "Primary Output") {
    throw new Error("只读职责不能取得写入路径");
  }
  for (const path of job.paths) {
    checkWritePath(workflow, path, batch);
  }
}

function prepareModelInput(job: DelegateJob, adapter: SubagentAdapter): Record<string, string> {
  if (job.model !== undefined && !job.modelReason?.trim()) {
    throw new Error("显式模型选择须有 Root 任务依据；不静默忽略设置");
  }
  if (job.model === undefined && job.modelReason !== undefined) {
    throw new Error("模型选择依据必须对应实际 model 请求");
  }
  return subagentModelInput(adapter, job.model);
}

function prepareJob(workflow: Workflow, job: DelegateJob, batch: BatchPreflight): PreparedJob {
  if (!ROLES.includes(job.role) || !job.agent?.trim() || !job.task?.trim()) {
    throw new Error("职责、扩展 agent 配置名和真实任务必须明确");
  }
  const modelInput = prepareModelInput(job, batch.adapter);
  checkWritePaths(workflow, job, batch);
  return { job, modelInput };
}

function prepareBatch(workflow: Workflow, input: DelegateInput, host: DelegationHost) {
  const tool = host.context.tools.find((tool) => tool.name === input.tool);
  const adapter = tool && resolveSubagentAdapter(tool.parameters);
  if (!adapter || !host.isDelegate(input.tool)) {
    throw new Error(
      "委派需要 @mjakl/pi-subagent@3.1.0 的可调用 calls[] Schema，且须支持 initialContext: empty",
    );
  }
  const observations = workflow.state.observations;
  if (
    !input.evidence?.length ||
    input.evidence.some((id) => !observations.some((observation) => observation.id === id))
  ) {
    throw new Error("委派缺少真实授权/任务依据引用");
  }
  if (input.jobs.some((job) => job.role === "Primary Output") && !workflow.state.slice) {
    throw new Error("Primary Output 委派须有当前 Slice");
  }
  if (input.jobs.some((job) => job.role === "Documentation/Comments & Git Operations")) {
    throw new Error(
      "当前适配器不支持 Git 子任务；非简单 Git 仍须实际合格的独立扩展与单独授权，不可由本接口冒充",
    );
  }

  // 整批预检完成才占用名额，任何后续任务不合格时也不触发前面的调用。
  const preflight = { adapter, cwd: host.context.cwd, claimedPaths: new Set<string>() };
  return input.jobs.map((job) => prepareJob(workflow, job, preflight));
}

function formatDelegateTask(job: DelegateJob, allocationId: string, audit: Audit | undefined): string {
  const scope = job.paths.length
    ? `仅获准写入这些精确路径：${job.paths.join(", ")}。`
    : "此任务只读，不准写项目文件。";
  return [
    `会话审计偏好及每字段来源：${JSON.stringify(audit)}。仅安全摘要策略，不代表完整日志访问或私有思维链披露；不改变权限或独立验证。`,
    `父级逻辑 allocation=${allocationId}；职责=${job.role}；这是一次性真实任务，不是可恢复会话。${scope}`,
    "禁止创建/派发其他代理，禁止 Computer Use；未授权 Git/Memory/网络或扩大范围。工具/路径限制是任务合同，不是OS沙箱。先读必要上下文，只返回有界实际结果、证据、失败与未决项；不得只给状态词。",
    job.task,
  ].join("\n");
}

function findAllocation(workflow: Workflow, id: string) {
  const allocation = workflow.state.allocations.find((allocation) => allocation.id === id);
  if (!allocation) throw new Error(`委派回执找不到对应的 allocation：${id}`);
  return allocation;
}

async function dispatchJob(workflow: Workflow, dispatch: JobDispatch, host: DelegationHost) {
  const { invocation, prepared, allocationId } = dispatch;
  const { job, modelInput } = prepared;
  const task = formatDelegateTask(job, allocationId, workflow.state.audit);
  const input = subagentInput({ agent: job.agent, task, cwd: host.context.cwd, modelInput });
  const outcome = await host.context.executeTool(invocation.input.tool, input, { signal: invocation.signal });
  const allocation = findAllocation(workflow, allocationId);
  const notRun = outcome.isError && outcome.durationMs === undefined;

  const reportedStatus = outcome.isError ? "failed" : "completed";
  allocation.status = invocation.signal?.aborted ? "uncertain" : reportedStatus;

  // 只有宿主确认调用未运行时才可撤回预留，已执行的失败不会退还名额。
  if (notRun) {
    host.calls.releasedReservations.add(allocation.id);
    workflow.state.allocations = workflow.state.allocations.filter((slot) => slot.id !== allocation.id);
  } else {
    for (const path of job.paths) workflow.mutate(fileEffect(path));
  }
  host.persist(host.context);
  return { allocation, reservationReleasedBeforeExecution: notRun, outcome };
}

interface BatchSettlement {
  allocations: Allocation[];
  epoch: Epoch;
  results: PromiseSettledResult<Awaited<ReturnType<typeof dispatchJob>>>[];
}

function settleBatch(workflow: Workflow, invocation: DelegateInvocation, batch: BatchSettlement) {
  const { callId, input, signal } = invocation;
  const { results, allocations, epoch } = batch;
  let uncertain = signal?.aborted === true;
  for (const [index, result] of results.entries()) {
    if (result.status === "rejected") {
      findAllocation(workflow, allocations[index].id).status = "uncertain";
      uncertain = true;
    }
  }
  if (uncertain) {
    workflow.pause("部分子任务结果未知，读回实际效果前不能重派");
  } else {
    workflow.state.inFlight = workflow.state.inFlight.filter((id) => id !== callId);
  }
  const ok =
    !uncertain && results.every((result) => result.status === "fulfilled" && !result.value.outcome.isError);
  workflow.observe({ id: callId, tool: input.tool, effect: "delegate", ok }, epoch);
  if (ok && input.jobs.every((job) => job.role === "Change Verification")) {
    workflow.observe({ id: `${callId}:check`, tool: input.tool, effect: "check", ok: true }, epoch);
  }
  return {
    ok,
    results: results.map((result) =>
      result.status === "fulfilled" ? result.value : { error: String(result.reason) },
    ),
  };
}

function reserveBatch(workflow: Workflow, invocation: DelegateInvocation, host: DelegationHost) {
  const { callId, input } = invocation;
  workflow.assertRevision(input.revision);
  const jobs = prepareBatch(workflow, input, host);
  const allocations = workflow.reserve(jobs.map(({ job }) => ({ role: job.role, callId })));
  workflow.state.inFlight.push(callId);
  host.calls.allowedDelegates.add(callId);
  host.calls.intents.set(callId, { effect: "read", delegate: true });
  host.persist(host.context);
  return { jobs, allocations };
}

export async function runDelegation(
  workflow: Workflow,
  invocation: DelegateInvocation,
  host: DelegationHost,
): Promise<{ ok: boolean; body: string }> {
  const { callId } = invocation;
  try {
    const { jobs, allocations } = reserveBatch(workflow, invocation, host);
    const epoch = structuredClone(workflow.state.epoch);
    const results = await Promise.allSettled(
      jobs.map((prepared, index) =>
        dispatchJob(
          workflow,
          {
            invocation,
            prepared,
            allocationId: allocations[index].id,
          },
          host,
        ),
      ),
    );
    const batch = settleBatch(workflow, invocation, { allocations, epoch, results });
    const body = JSON.stringify(batch.results);
    host.calls.results.set(callId, body);
    host.persist(host.context);
    return { ok: batch.ok, body };
  } finally {
    host.calls.allowedDelegates.delete(callId);
    host.calls.intents.delete(callId);
  }
}
