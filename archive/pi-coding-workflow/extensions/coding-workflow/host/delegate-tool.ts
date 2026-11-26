import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import type { WorkflowToolSchemas } from "../tool-schemas.ts";
import { MAX_RESULT, RESULT_PAGE_SIZE, toolResult, type ToolHost } from "./tool-results.ts";
import { runDelegation } from "../delegation.ts";
import { reachedTool } from "./tool-results.ts";

export function registerDelegateTool(pi: ExtensionAPI, schemas: WorkflowToolSchemas, host: ToolHost): void {
  pi.registerTool({
    name: "coding_delegate",
    label: "Coding 有界委派",
    description:
      "通过 @mjakl/pi-subagent@3.1.0 的 calls[] 派发一次性任务。预留职责预算后可并行执行独立任务。",
    parameters: schemas.delegate,
    executionMode: "sequential",
    exposure: "model-only",
    reachesTools: reachedTool,
    async execute(...[callId, input, signal, _update, context]) {
      try {
        const workflow = host.requireWorkflow();
        const { body, ok } = await runDelegation(
          workflow,
          { callId, input, signal },
          {
            context,
            calls: host.calls,
            isDelegate: host.isDelegate,
            persist: host.persist,
          },
        );
        const paged = body.length > MAX_RESULT;
        const results: unknown = paged ? body.slice(0, RESULT_PAGE_SIZE) : JSON.parse(body);
        return toolResult(
          {
            callId,
            results,
            total: body.length,
            nextOffset: paged ? RESULT_PAGE_SIZE : null,
            note: "结果绑定 allocation 与真实调用，不构造 Session ID；须读完实际任务正文。终态不释放预算。",
          },
          !ok,
        );
      } catch (error) {
        return toolResult(String(error), true);
      }
    },
  });
}
