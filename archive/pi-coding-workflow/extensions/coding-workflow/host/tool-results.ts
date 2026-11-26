import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import type { Workflow } from "../engine.ts";
import type { ToolCallState } from "../tool-guards.ts";

export const MAX_RESULT = 64000;
export const RESULT_PAGE_SIZE = 24000;

export interface ToolHost {
  calls: ToolCallState;
  activeWorkflow(): Workflow | undefined;
  requireWorkflow(): Workflow;
  isDelegate(name: string): boolean;
  persist(context: ExtensionContext): void;
}

export function toolResult(
  value: unknown,
  isError = false,
): {
  content: [{ type: "text"; text: string }];
  details: Record<string, never>;
  isError: boolean;
} {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return { content: [{ type: "text" as const, text }], details: {}, isError };
}

export function reachedTool(input: Record<string, unknown>): string[] {
  return typeof input.tool === "string" ? [input.tool] : [];
}
