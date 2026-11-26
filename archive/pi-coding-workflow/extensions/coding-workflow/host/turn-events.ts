import { randomUUID } from "node:crypto";
import { startupFlags } from "../startup.ts";
import { renderContext } from "../rules/prompt.ts";
import { CONTEXT_TYPE, type RuntimeSession } from "./runtime-session.ts";
import { requestStart } from "./workflow-commands.ts";

function contextMessage(content: string) {
  return {
    role: "custom" as const,
    customType: CONTEXT_TYPE,
    content,
    display: false,
    timestamp: Date.now(),
  };
}

function workflowContext(runtime: RuntimeSession): string {
  if (runtime.restoreError) {
    return `[Coding 状态阻断] ${runtime.restoreError}。保留旧记录，停止依赖写入；不要通过重启任务绕过。`;
  }
  try {
    return renderContext(runtime.requireWorkflow());
  } catch (error) {
    const content = `[Coding 规则阻断] ${String(error)}。停止依赖操作。`;
    runtime.workflow?.pause(content);
    return content;
  }
}

function registerContextHook(runtime: RuntimeSession): void {
  runtime.pi.on("context", (event) => {
    const messages = event.messages.filter(
      (message) => !("customType" in message && message.customType === CONTEXT_TYPE),
    );
    if (runtime.starting || runtime.startupError) {
      const content = `[Coding 启动未完成] ${runtime.startupError || "正在提问"}。可只读查看，不得产生副作用或代替用户选择。`;
      return { messages: [...messages, contextMessage(content)] };
    }
    if (!runtime.enabled) return { messages };
    return { messages: [...messages, contextMessage(workflowContext(runtime))] };
  });
}

function registerUserInput(runtime: RuntimeSession): void {
  runtime.pi.on("input", (event, context) => {
    const current = runtime.activeWorkflow();
    if (!current || event.source === "extension") return;
    current.observe({ id: `input:${randomUUID()}`, tool: `user:${event.source}`, effect: "user", ok: true });
    current.state.capabilityChanged = undefined;
    current.state.scopeRevision = current.state.revision;
    if (current.state.status === "active") {
      current.state.slice = undefined;
      if (current.state.inFlight.length) current.pause("用户输入到达时仍有未决调用，先读回实际效果");
    }
    runtime.persist(context);
  });
  runtime.pi.on("before_agent_start", async (event, context) => {
    if (
      !runtime.workflow &&
      !runtime.restoreError &&
      runtime.pi.getFlag("coding-mode") &&
      event.messageType === "user"
    ) {
      try {
        await requestStart(runtime, context, {
          input: startupFlags(runtime.pi),
          task: event.prompt,
          fromFlags: true,
        });
      } catch (error) {
        runtime.reply(context, String(error));
      }
    }
    if (runtime.enabled || runtime.starting || runtime.startupError) {
      event.systemPromptOptions.sections.coding_workflow =
        "Coding 扩展已启用：按上下文中的 YAML 路线和适用 Hooks 行动，结合当前用户指令和实际工具回执判断授权、身份及验收。";
    }
  });
}

function registerTurnCompletion(runtime: RuntimeSession): void {
  runtime.pi.on("agent_settled", (event, context) => {
    const current = runtime.activeWorkflow();
    if (!current) return;
    if (event.aborted || current.state.inFlight.length) {
      current.pause("本轮中止或仍有未决调用；先读回实际效果，再决定恢复");
    } else if (current.state.slice) {
      current.state.slice = undefined;
      current.state.revision++;
    }
    runtime.persist(context);
  });
}

export function registerTurnHooks(runtime: RuntimeSession): void {
  registerUserInput(runtime);
  registerContextHook(runtime);
  registerTurnCompletion(runtime);
}
