import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { installWorkflow } from "./runtime.ts";
import { workflowToolSchemas } from "./tool-schemas.ts";

export default function codingWorkflow(pi: ExtensionAPI): void {
  installWorkflow(pi, workflowToolSchemas);
}
