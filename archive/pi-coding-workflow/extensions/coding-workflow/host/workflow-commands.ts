import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Workflow, makeState } from "../engine.ts";
import { collectStartup, parseStartupCommand, type StartupAnswers, type StartupRequest } from "../startup.ts";
import {
  CONTEXT_TYPE,
  recordCommand,
  sessionIdentity,
  type RuntimeSession,
  type SessionLedger,
} from "./runtime-session.ts";
import { sessionStatus } from "./session-state.ts";
import { hasStartupMarker, scanSessionLedger } from "./session-restore.ts";

function matchesSessionBudget(ledger: SessionLedger, startup: StartupAnswers): boolean {
  return ledger.mode === startup.mode && ledger.count === startup.count && !ledger.inFlight.length;
}

function assertSessionBudget(
  runtime: RuntimeSession,
  context: ExtensionContext,
  startup: StartupAnswers,
): void {
  if (runtime.restoreError) throw new Error(runtime.restoreError);
  if (runtime.isVolatile() && !runtime.workflow && hasStartupMarker(context)) {
    throw new Error("volatile 历史存在但当前进程状态不可恢复；请使用新 Session，不能假设预算清空");
  }
  if (!runtime.isVolatile()) runtime.ledger = scanSessionLedger(runtime, context) ?? runtime.ledger;
  const { ledger } = runtime;
  if (ledger && !matchesSessionBudget(ledger, startup)) {
    throw new Error(
      "整个 Session 的模式/预算仍锁定或有未知效果；树导航不是重置授权，请恢复原任务或新建 Session",
    );
  }
}

function assertReplaceableRun(runtime: RuntimeSession): void {
  const previous = runtime.workflow?.state;
  if (previous?.status === "paused" || previous?.inFlight.length) {
    throw new Error("上个任务已暂停或仍有未决效果，先读回并恢复，再开始新任务");
  }
}

function assertPreviousBudget(runtime: RuntimeSession, sessionId: string, startup: StartupAnswers): void {
  const previous = runtime.workflow?.state;
  if (!previous || previous.sessionId !== sessionId) return;
  if (previous.mode !== startup.mode || previous.childCount !== startup.count) {
    throw new Error("同 Session 已锁定 Mode/count；新路线请使用新 Session，扩容须显式 add-slot");
  }
}

function startWorkflow(
  runtime: RuntimeSession,
  context: ExtensionContext,
  { startup, task }: { startup: StartupAnswers; task: string },
): void {
  assertSessionBudget(runtime, context, startup);
  const session = sessionIdentity(context);
  assertReplaceableRun(runtime);
  assertPreviousBudget(runtime, session.sessionId, startup);
  const catalog = runtime.getCatalog();
  const { mode, count, audit } = startup;
  const workflow = new Workflow(catalog, makeState(catalog, session, { mode, childCount: count, task }));
  const previousSlots = runtime.workflow?.state.allocations ?? runtime.ledger?.allocations;
  if (previousSlots) workflow.state.allocations = structuredClone(previousSlots);
  workflow.state.audit = structuredClone(audit);
  runtime.workflow = workflow;
  runtime.enabled = true;
  recordCommand(workflow, "/coding");
  runtime.clearCallTracking();
  runtime.persist(context);
}

function beginStartup(runtime: RuntimeSession, context: ExtensionContext) {
  if (runtime.starting) throw new Error("已有启动提问进行中；不能并发或重复启动");
  if (runtime.restoreError) throw new Error(runtime.restoreError);
  assertReplaceableRun(runtime);
  const token = ++runtime.generation;
  const sessionId = context.sessionManager.getSessionId();
  runtime.starting = true;
  runtime.startupError = "";
  return { token, sessionId };
}

function saveStartup(
  runtime: RuntimeSession,
  context: ExtensionContext,
  request: { startup: StartupAnswers; task: string },
): void {
  const previous = runtime.answers;
  runtime.answers = request.startup;
  try {
    startWorkflow(runtime, context, request);
  } catch (error) {
    runtime.answers = previous;
    throw error;
  }
}

export async function requestStart(
  runtime: RuntimeSession,
  context: ExtensionContext,
  request: StartupRequest & { fromFlags?: true },
): Promise<void> {
  const { token, sessionId } = beginStartup(runtime, context);
  if (request.fromFlags) runtime.startupError = "CLI 启动答案未完成";
  const current = () => {
    if (token !== runtime.generation || context.sessionManager.getSessionId() !== sessionId) {
      throw new Error("启动已取消：Session/树导航发生变化");
    }
  };
  try {
    const startup = await collectStartup(context, request.input, { saved: runtime.answers, current });
    current();
    saveStartup(runtime, context, { startup, task: request.task });
    runtime.answerSession = sessionId;
    runtime.startupError = "";
  } catch (error) {
    if (token === runtime.generation && request.fromFlags) runtime.startupError = String(error);
    throw error;
  } finally {
    if (token === runtime.generation) runtime.starting = false;
  }
}

function sendStart(runtime: RuntimeSession, context: ExtensionContext, task: string): void {
  runtime.pi.sendMessage(
    {
      customType: CONTEXT_TYPE + ".start",
      details: { sessionId: context.sessionManager.getSessionId() },
      content: [
        "用户已通过 /coding 明确选择路线与目标。按当前 Coding Hooks 开始，先核验 Contract/能力；模式选择不授权写入、Memory 或子任务。",
        task,
      ].join("\n\n"),
      display: true,
    },
    { triggerTurn: true },
  );
}

function statusText(runtime: RuntimeSession): string {
  if (runtime.workflow) return JSON.stringify(sessionStatus(runtime.workflow), null, 2);
  return (
    runtime.restoreError ||
    runtime.startupError ||
    "未启用。/coding start <任务> 或 single|multi [数量] <任务>"
  );
}

function pauseCommand(runtime: RuntimeSession, context: ExtensionContext, workflow: Workflow): void {
  workflow.pause("用户暂停");
  runtime.persist(context);
}

function disableWorkflow(runtime: RuntimeSession, context: ExtensionContext, workflow: Workflow): void {
  workflow.pause("用户停用扩展；恢复前须读取实际状态");
  runtime.enabled = false;
  runtime.persist(context);
}

function resumeCommand(runtime: RuntimeSession, context: ExtensionContext, workflow: Workflow): void {
  runtime.enabled = true;
  recordCommand(workflow, "/coding resume");
  // 读回证据由控制工具核验，收到恢复指令时仍保留暂停位置。
  runtime.persist(context);
  runtime.pi.sendMessage(
    {
      customType: CONTEXT_TYPE + ".resume",
      content:
        "用户要求恢复。按恢复 Hook 读回已完成效果及当前状态；用 coding_checkpoint resume/resolve_effect，勿重放命令。",
      display: true,
    },
    { triggerTurn: true },
  );
}

function controlCommand(runtime: RuntimeSession, context: ExtensionContext, input: string): void {
  const workflow = runtime.workflow;
  if (!workflow || runtime.restoreError) throw new Error(runtime.restoreError || "没有可恢复的任务");
  if (input === "pause") return pauseCommand(runtime, context, workflow);
  if (input === "off") return disableWorkflow(runtime, context, workflow);
  if (input === "resume") return resumeCommand(runtime, context, workflow);
  if (input.startsWith("add-slot ")) {
    workflow.addSlot(input.slice(9));
    if (runtime.answers) runtime.answers.count = workflow.state.childCount;
    recordCommand(workflow, "/coding add-slot");
    runtime.persist(context);
    return;
  }
  throw new Error(
    "未知命令；/coding status 查看状态。支持 start、single、multi、cancel、pause、resume、off、add-slot。",
  );
}

async function runCodingCommand(
  runtime: RuntimeSession,
  context: ExtensionContext,
  input: string,
): Promise<void> {
  const request = parseStartupCommand(input);
  if (request) {
    await requestStart(runtime, context, request);
    sendStart(runtime, context, request.task);
    return;
  }
  if (!input || input === "status") return runtime.reply(context, statusText(runtime));
  if (input === "cancel" && runtime.starting) {
    const reason = runtime.startupError ? "CLI 启动已取消" : "";
    runtime.cancelStartup(reason);
    runtime.reply(context, "启动已取消");
    return;
  }
  controlCommand(runtime, context, input);
}

export function registerCodingCommand(runtime: RuntimeSession): void {
  runtime.pi.registerCommand("coding", {
    description:
      "Coding start <任务> | single <任务> | multi [数量] <任务> | status | pause | resume | off | add-slot <完整职责名>",
    async handler(args, context) {
      try {
        await runCodingCommand(runtime, context, args.trim());
      } catch (error) {
        runtime.reply(context, String(error));
      }
    },
  });
}
