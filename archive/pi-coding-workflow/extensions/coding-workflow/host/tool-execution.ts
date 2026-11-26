import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import type { WorkflowToolSchemas } from "../tool-schemas.ts";
import { MAX_RESULT, RESULT_PAGE_SIZE, toolResult, type ToolHost } from "./tool-results.ts";
import type { ExecuteToolOptions, ExtensionToolContext } from "@earendil-works/pi-coding-agent";
import type { Workflow } from "../engine.ts";
import { affectsEpoch, scopedPath, WORKFLOW_TOOL_NAMES, type ToolIntent } from "../tool-guards.ts";
import type { RunInput } from "../tool-schemas.ts";
import { requireEvidence, sessionStatus } from "./session-state.ts";
import { reachedTool } from "./tool-results.ts";

export function registerSliceTool(pi: ExtensionAPI, schemas: WorkflowToolSchemas, host: ToolHost): void {
  pi.registerTool({
    name: "coding_slice",
    label: "Coding Slice",
    description:
      "放行有界 Slice：Objective、精确路径/影响、Return conditions、Unreleased boundary，须有当前授权与计划依据",
    parameters: schemas.slice,
    executionMode: "sequential",
    exposure: "model-only",
    async execute(...[_id, input, _signal, _update, context]) {
      try {
        const workflow = host.requireWorkflow();
        for (const path of input.slice.paths) {
          if (scopedPath(context.cwd, path) !== path) throw new Error("路径须使用规范项目相对路径");
        }
        workflow.release(input.revision, input.slice);
        host.persist(context);
        return toolResult(sessionStatus(workflow));
      } catch (error) {
        return toolResult(String(error), true);
      }
    },
  });
}

interface OpaqueToolCall {
  callId: string;
  input: RunInput;
  options: ExecuteToolOptions;
  intent: ToolIntent;
}

type ToolExecutionHost = ToolHost & { context: ExtensionToolContext };
type ToolOutcome = Awaited<ReturnType<ExtensionToolContext["executeTool"]>>;

function prepareRunIntent(workflow: Workflow, input: RunInput, host: ToolExecutionHost): ToolIntent {
  workflow.assertRevision(input.revision);
  const { tool, effect, evidence } = input;
  if (
    WORKFLOW_TOOL_NAMES.has(tool) ||
    host.isDelegate(tool) ||
    !host.context.tools.some((available) => available.name === tool)
  ) {
    throw new Error("工具不存在/hidden/递归/子代理旁路；先发现真实工具与 Schema");
  }
  if (!input.rationale?.trim()) throw new Error("缺少效果分类依据");
  requireEvidence(workflow.state, evidence);
  const verification =
    effect === "git" ? workflow.checkGitEvidence(input.verificationEvidence ?? []) : undefined;
  const blocked = workflow.canRun(effect, undefined, verification);
  if (blocked) throw new Error(blocked);
  return { effect, verification };
}

function storeRunReceipt(host: ToolExecutionHost, callId: string, outcome: ToolOutcome) {
  // 完整工具正文留给后续分页，分页只读取收据缓存。
  const body = JSON.stringify(outcome.result);
  host.calls.results.set(callId, body);
  host.persist(host.context);

  const paged = body.length > MAX_RESULT;
  return toolResult(
    {
      callId,
      isError: outcome.isError,
      total: body.length,
      result: paged ? body.slice(0, RESULT_PAGE_SIZE) : outcome.result,
      nextOffset: paged ? RESULT_PAGE_SIZE : null,
      note: paged ? "用 coding_checkpoint result 分页读完；不可仅凭摘要接受结果" : undefined,
    },
    outcome.isError,
  );
}

async function runOpaqueTool(workflow: Workflow, call: OpaqueToolCall, host: ToolExecutionHost) {
  const { callId, input, options, intent } = call;
  const { calls, context } = host;

  // 保存调用中状态后再进入宿主工具，中断恢复才能定位具体调用。
  calls.intents.set(callId, intent);
  workflow.state.inFlight.push(callId);
  host.persist(context);
  const epochAtCall = structuredClone(workflow.state.epoch);
  const outcome = await context.executeTool(input.tool, input.input, options);

  if (options.signal?.aborted) {
    workflow.pause("调用被中止：须先读回实际效果，不自动重试");
  } else {
    workflow.state.inFlight = workflow.state.inFlight.filter((id) => id !== callId);
  }
  const actuallyRan = outcome.durationMs !== undefined;
  workflow.observe(
    {
      id: callId,
      tool: input.tool,
      effect: input.effect,
      ok: actuallyRan && !outcome.isError && !options.signal?.aborted,
    },
    epochAtCall,
  );
  if (actuallyRan && affectsEpoch(input.effect) && !calls.observedMutations.has(callId)) {
    workflow.mutate(input.effect);
  }

  return storeRunReceipt(host, callId, outcome);
}

export function registerRunTool(pi: ExtensionAPI, schemas: WorkflowToolSchemas, host: ToolHost): void {
  const { calls } = host;
  pi.registerTool({
    name: "coding_run",
    label: "Coding 显式影响调用",
    description:
      "经宿主实际工具链运行已授权的不透明工具；effect 是声明，不是命令安全证明。只调用真实可调用工具，不绕过 hidden/审批。",
    parameters: schemas.run,
    executionMode: "sequential",
    exposure: "model-only",
    reachesTools: reachedTool,
    async execute(...[callId, input, signal, onUpdate, context]) {
      const executionHost = { ...host, context };
      try {
        const workflow = host.requireWorkflow();
        const intent = prepareRunIntent(workflow, input, executionHost);
        return await runOpaqueTool(
          workflow,
          { callId, input, intent, options: { signal, onUpdate } },
          executionHost,
        );
      } catch (error) {
        const workflow = host.activeWorkflow();
        if (workflow?.state.inFlight.includes(callId))
          workflow.pause("不透明调用中断：效果未知，须读回，禁止自动重放");
        host.persist(context);
        return toolResult(String(error), true);
      } finally {
        calls.intents.delete(callId);
      }
    },
  });
}
