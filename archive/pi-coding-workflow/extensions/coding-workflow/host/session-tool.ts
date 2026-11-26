import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import type { WorkflowToolSchemas } from "../tool-schemas.ts";
import { MAX_RESULT, RESULT_PAGE_SIZE, toolResult, type ToolHost } from "./tool-results.ts";
import { HOOK_IDS, hookDocument, rewriteWorkflowLinks } from "../catalog.ts";
import type { Workflow } from "../engine.ts";
import { renderHook } from "../rules/prompt.ts";
import type { CheckpointInput } from "../tool-schemas.ts";
import type { ToolCallState } from "../tool-guards.ts";
import { sessionStatus } from "./session-state.ts";

function readRules(workflow: Workflow, query: Extract<CheckpointInput, { action: "rules" }>) {
  const { catalog, state } = workflow;
  const document = catalog.references.document(query.document ?? catalog.routes[state.mode]);

  if (query.fragment === undefined) {
    const fragments = document.fragments.map(({ id, kind, title }) => ({ id, kind, title }));
    const hook = HOOK_IDS.find((id) => document.id === hookDocument(id));
    let content: string | undefined;
    if (hook) content = renderHook(catalog, hook, state.mode);
    else if ([...Object.values(catalog.routes), "hook-readme"].includes(document.id)) {
      content = rewriteWorkflowLinks(catalog, document.path, catalog.references.readRoute(document.id));
    }
    if (content && content.length > MAX_RESULT) throw new Error("Hook 超出读取上限");
    return { document: document.id, title: document.title, fragments, content };
  }
  const body = catalog.references.readFragment(document.id, query.fragment);
  const content = rewriteWorkflowLinks(catalog, document.path, body);
  if (content.length > MAX_RESULT) {
    throw new Error(`规则片段超出读取上限：${document.id}#${query.fragment}`);
  }
  return { document: document.id, fragment: query.fragment, content };
}

function readResultPage(
  results: ToolCallState["results"],
  query: Extract<CheckpointInput, { action: "result" }>,
) {
  const result = results.get(query.resultId);
  if (result === undefined) throw new Error("结果已不可用；不要重跑任务，按实际调用记录核验");
  const offset = query.offset ?? 0;
  if (!Number.isSafeInteger(offset) || offset < 0) throw new Error("offset 无效");

  const end = offset + RESULT_PAGE_SIZE;
  return {
    resultId: query.resultId,
    offset,
    total: result.length,
    content: result.slice(offset, end),
    nextOffset: end < result.length ? end : null,
  };
}

type CheckpointChange = Exclude<CheckpointInput, { action: "status" | "rules" | "result" }>;

function applyCheckpointChange(workflow: Workflow, change: CheckpointChange): void {
  switch (change.action) {
    case "pause":
      workflow.assertRevision(change.revision);
      workflow.pause(change.reason);
      return;
    case "resume":
      workflow.resume(change.revision, change.evidence);
      return;
    case "resolve_effect":
      workflow.resolveEffect(change.revision, change.callId, change.evidence);
      return;
    default:
      throw new Error("未知控制动作");
  }
}

export function registerSessionTool(pi: ExtensionAPI, schemas: WorkflowToolSchemas, host: ToolHost): void {
  pi.registerTool({
    name: "coding_checkpoint",
    label: "Coding 规则与会话",
    description: "按 ID 查询规则与回执，或处理暂停、未确认效果和恢复",
    parameters: schemas.checkpoint,
    executionMode: "sequential",
    exposure: "model-only",
    async execute(...[_id, input, _signal, _update, context]) {
      try {
        const workflow = host.requireWorkflow();
        if (input.action === "status") return toolResult(sessionStatus(workflow, input.offset));
        if (input.action === "rules") return toolResult(readRules(workflow, input));
        if (input.action === "result") return toolResult(readResultPage(host.calls.results, input));

        applyCheckpointChange(workflow, input);
        host.persist(context);
        return toolResult(sessionStatus(workflow));
      } catch (error) {
        return toolResult(String(error), true);
      }
    },
  });
}
