import type { ExtensionContext, ToolCallEvent, ToolExecutionEndEvent } from "@earendil-works/pi-coding-agent";
import type { Workflow } from "../engine.ts";
import { compatibleSubagent } from "../subagent-adapter.ts";
import {
  affectsEpoch,
  fileEffect,
  nearestIntent,
  parentCallId,
  scopedPath,
  WORKFLOW_TOOL_NAMES,
  type ToolIntent,
} from "../tool-guards.ts";
import { EPOCH_DIMENSIONS } from "./session-state.ts";
import type { RuntimeSession } from "./runtime-session.ts";

const READ_TOOLS = new Set(["read", "grep", "find", "ls", "tool_search"]);

export function isDelegateTool(runtime: RuntimeSession, name: string): boolean {
  return runtime.pi
    .getAllTools()
    .some((tool) => tool.name === name && (compatibleSubagent(tool.parameters) || name === "subagent"));
}

function guardFileWrite(
  runtime: RuntimeSession,
  context: ExtensionContext,
  request: { callId: string; path: unknown },
): string | undefined {
  const workflow = runtime.requireWorkflow();
  try {
    const path = scopedPath(context.cwd, request.path);
    const effect = fileEffect(path);
    const block = workflow.canRun(effect, path);
    if (block) return block;
    runtime.calls.intents.set(request.callId, { effect });
    workflow.state.inFlight.push(request.callId);
    runtime.persist(context);
  } catch (error) {
    return String(error);
  }
  return undefined;
}

function guardOpaqueTool(
  runtime: RuntimeSession,
  workflow: Workflow,
  event: ToolCallEvent,
): string | undefined {
  const intents = runtime.calls.intents;
  const intent = nearestIntent(intents, event.parentToolCallId);
  if (!intent || intent.delegate) {
    return "不透明工具须通过 coding_run 声明影响、依据和当前 Slice；不根据 Shell 名称猜测安全性";
  }
  const block = workflow.canRun(intent.effect, undefined, intent.verification);
  if (!block) intents.set(event.toolCallId, intent);
  return block;
}

function guardCurrentTool(
  runtime: RuntimeSession,
  context: ExtensionContext,
  event: ToolCallEvent,
): string | undefined {
  const { toolName, toolCallId, parentToolCallId } = event;
  if (isDelegateTool(runtime, toolName)) {
    if (!parentToolCallId || !runtime.calls.allowedDelegates.has(parentToolCallId)) {
      return "子任务必须经 coding_delegate 预算、角色、任务和实际 Schema 门禁；不允许直接或脚本旁路";
    }
    return undefined;
  }
  if (event.toolName === "edit" || event.toolName === "write") {
    return guardFileWrite(runtime, context, { callId: toolCallId, path: event.input.path });
  }
  if (READ_TOOLS.has(toolName)) {
    runtime.calls.intents.set(toolCallId, { effect: "read" });
    return undefined;
  }
  return guardOpaqueTool(runtime, runtime.requireWorkflow(), event);
}

function guardTool(
  runtime: RuntimeSession,
  context: ExtensionContext,
  event: ToolCallEvent,
): string | undefined {
  if (runtime.starting || runtime.startupError) {
    return READ_TOOLS.has(event.toolName)
      ? undefined
      : runtime.startupError || "启动进行中；暂缓可能有副作用的工具";
  }
  if (!runtime.enabled || WORKFLOW_TOOL_NAMES.has(event.toolName)) return undefined;
  if (runtime.restoreError) return READ_TOOLS.has(event.toolName) ? undefined : runtime.restoreError;
  if (!runtime.workflow) return "工作流状态不可用，须先核对会话";
  return guardCurrentTool(runtime, context, event);
}

function rememberParentMutations(runtime: RuntimeSession, parent: string | undefined): void {
  for (let id = parent; id; id = parentCallId(id)) {
    runtime.calls.observedMutations.add(id);
  }
}

function recordOutcome(
  runtime: RuntimeSession,
  workflow: Workflow,
  { event, intent }: { event: ToolExecutionEndEvent; intent: ToolIntent },
): void {
  const { effect } = intent;
  const ran = event.durationMs !== undefined;
  if (ran && affectsEpoch(effect)) {
    workflow.mutate(effect);
    rememberParentMutations(runtime, event.parentToolCallId);
  }
  workflow.state.inFlight = workflow.state.inFlight.filter((id) => id !== event.toolCallId);
  workflow.observe({ id: event.toolCallId, tool: event.toolName, effect, ok: ran && !event.isError });
  if (event.isError) workflow.state.capabilityChanged = true;
}

function finishTool(runtime: RuntimeSession, context: ExtensionContext, event: ToolExecutionEndEvent): void {
  const current = runtime.activeWorkflow();
  if (!current || WORKFLOW_TOOL_NAMES.has(event.toolName)) return;
  const { intents } = runtime.calls;
  const intent = intents.get(event.toolCallId) ?? nearestIntent(intents, event.parentToolCallId);
  if (intent && !intent.delegate) {
    recordOutcome(runtime, current, { event, intent });
    runtime.persist(context);
  }
  intents.delete(event.toolCallId);
}

export function registerToolHooks(runtime: RuntimeSession): void {
  runtime.pi.on("tool_call", (event, context) => {
    const reason = guardTool(runtime, context, event);
    if (reason) return { block: true, reason };
  });
  runtime.pi.on("tool_execution_end", (event, context) => finishTool(runtime, context, event));
  runtime.pi.on("user_bash", (_event, context) => {
    const current = runtime.activeWorkflow();
    if (!current) return;
    for (const dimension of EPOCH_DIMENSIONS) current.mutate(dimension);
    current.pause("用户 Shell 的实际影响尚未读回；不从命令名推断无副作用");
    runtime.persist(context);
  });
}
