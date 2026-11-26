import { randomUUID } from "node:crypto";
import { realpathSync } from "node:fs";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { loadCatalog, type Catalog, type Mode } from "../catalog.ts";
import type { Workflow } from "../engine.ts";
import { sessionSnapshot } from "../engine/workflow-snapshot.ts";
import type { StartupAnswers } from "../startup.ts";
import type { ToolCallState } from "../tool-guards.ts";
import type { Allocation, WorkflowSession } from "./session-state.ts";

// 沿用会话条目名称以读取旧版本，具体格式由 state.version 区分。
export const STATE_TYPE = "token-io.coding-workflow.v1";
export const CONTEXT_TYPE = "token-io.coding-hooks.v1";

export interface SessionLedger {
  mode: Mode;
  count: number;
  allocations: Allocation[];
  inFlight: string[];
}

export function sessionIdentity(context: ExtensionContext): WorkflowSession {
  return { sessionId: context.sessionManager.getSessionId(), cwd: realpathSync(context.cwd) };
}

export function recordCommand(workflow: Workflow, command: string): void {
  workflow.observe({ id: `command:${randomUUID()}`, tool: command, effect: "user", ok: true });
}

export class RuntimeSession {
  readonly pi: ExtensionAPI;
  readonly calls: ToolCallState = {
    intents: new Map(),
    allowedDelegates: new Set(),
    observedMutations: new Set(),
    releasedReservations: new Set(),
    results: new Map(),
  };
  workflow: Workflow | undefined;
  enabled = false;
  restoreError = "";
  answers: StartupAnswers | undefined;
  answerSession = "";
  generation = 0;
  starting = false;
  startupError = "";
  ledger: SessionLedger | undefined;
  private catalog: Catalog | undefined;
  private persistedLedger: string | undefined;

  constructor(pi: ExtensionAPI, catalog?: Catalog) {
    this.pi = pi;
    this.catalog = catalog;
  }

  getCatalog(): Catalog {
    return (this.catalog ??= loadCatalog());
  }

  isVolatile(): boolean {
    return this.pi.getFlag("coding-volatile") === true;
  }

  activeWorkflow(): Workflow | undefined {
    return this.enabled ? this.workflow : undefined;
  }

  requireWorkflow(): Workflow {
    const current = this.activeWorkflow();
    if (!current || this.restoreError) {
      throw new Error(
        this.restoreError || "先由用户通过 /coding start 或 single|multi [数量] <任务> 完成启动收集",
      );
    }
    return current;
  }

  cancelStartup(reason = ""): void {
    this.generation++;
    this.starting = false;
    this.startupError = reason;
  }

  clearCallTracking(): void {
    this.calls.intents.clear();
    this.calls.allowedDelegates.clear();
    this.calls.observedMutations.clear();
    this.calls.results.clear();
    this.persistedLedger = undefined;
  }

  persist(context: ExtensionContext): void {
    this.persistLedger();
    if (!context.hasUI) return;
    const current = this.activeWorkflow();
    if (current) {
      const { mode, status } = current.state;
      context.ui.setStatus("coding-workflow", `Coding ${mode} · ${status}`);
      return;
    }
    context.ui.setStatus("coding-workflow", this.restoreError ? "Coding: 状态需人工恢复" : undefined);
  }

  private persistLedger(): void {
    if (this.isVolatile() || !this.workflow || this.restoreError) return;
    const entry = {
      enabled: this.enabled,
      state: sessionSnapshot(this.workflow.state),
      releasedReservations: [...this.calls.releasedReservations],
    };
    const serialized = JSON.stringify(entry);
    if (serialized === this.persistedLedger) return;
    this.pi.appendEntry(STATE_TYPE, structuredClone(entry));
    this.persistedLedger = serialized;
  }

  reply(context: ExtensionContext, message: string): void {
    if (context.hasUI) context.ui.notify(message, "info");
    else this.pi.sendMessage({ customType: CONTEXT_TYPE + ".notice", content: message, display: true });
  }
}
