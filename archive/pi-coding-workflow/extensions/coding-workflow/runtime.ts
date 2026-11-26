import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import type { Catalog } from "./catalog.ts";
import type { Workflow } from "./engine.ts";
import { RuntimeSession } from "./host/runtime-session.ts";
import { registerSessionHooks } from "./host/session-restore.ts";
import { isDelegateTool, registerToolHooks } from "./host/tool-events.ts";
import { registerTurnHooks } from "./host/turn-events.ts";
import { registerCodingCommand } from "./host/workflow-commands.ts";
import { registerStartupFlags } from "./startup.ts";
import type { WorkflowToolSchemas } from "./tool-schemas.ts";
import { registerSessionTool } from "./host/session-tool.ts";
import { registerSliceTool, registerRunTool } from "./host/tool-execution.ts";
import { registerDelegateTool } from "./host/delegate-tool.ts";

export { compatibleSubagent } from "./subagent-adapter.ts";
export { fileEffect, scopedPath } from "./tool-guards.ts";
export { MAX_CONTEXT, renderContext, renderHook } from "./rules/prompt.ts";

export type Schemas = WorkflowToolSchemas;

interface InstalledWorkflow {
  getWorkflow(): Workflow | undefined;
  isEnabled(): boolean;
  getRestoreError(): string;
}

// TypeBox 的 Schema 由入口注入，测试可以直接使用宿主事件适配层。
export function installWorkflow(
  pi: ExtensionAPI,
  schemas: Schemas,
  suppliedCatalog?: Catalog,
): InstalledWorkflow {
  const session = new RuntimeSession(pi, suppliedCatalog);
  registerStartupFlags(pi);
  pi.registerFlag("coding-volatile", {
    description: "不额外 appendEntry；状态仅存当前进程，Pi 自身日志需另用 --no-session 管理",
    type: "boolean",
    default: false,
  });
  registerCodingCommand(session);
  const host = {
    calls: session.calls,
    activeWorkflow: () => session.activeWorkflow(),
    requireWorkflow: () => session.requireWorkflow(),
    isDelegate: (name: string) => isDelegateTool(session, name),
    persist: (context: ExtensionContext) => session.persist(context),
  };
  registerSessionTool(pi, schemas, host);
  registerSliceTool(pi, schemas, host);
  registerRunTool(pi, schemas, host);
  registerDelegateTool(pi, schemas, host);
  registerSessionHooks(session);
  registerTurnHooks(session);
  registerToolHooks(session);
  return {
    getWorkflow: () => session.workflow,
    isEnabled: () => session.enabled,
    getRestoreError: () => session.restoreError,
  };
}
