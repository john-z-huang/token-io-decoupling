from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from coding_dsl_templates import validate_route_diagram
from workflow_checkpoint_lookup import find_block
from workflow_flowcharts import MERMAID, parse_flowchart, validate_hook_flowcharts

COMPILER = runpy.run_path(str(SCRIPTS / "compile-reference-dsl.py"))


class WorkflowFlowchartTests(unittest.TestCase):
    def test_both_compiled_routes_include_all_hook_flowcharts(self):
        outputs = COMPILER["compile_rules"]()
        workflows = COMPILER["SKILL"] / "workflows"
        shared = MERMAID.findall(outputs[workflows / "README.md"])
        self.assertEqual(len(shared), 7)
        for mode in ("single", "multi"):
            with self.subTest(mode=mode):
                route = outputs[workflows / f"coding-{mode}-agent.md"]
                self.assertEqual(MERMAID.findall(route)[1:], shared)

    def test_adding_an_execution_clause_requires_a_matching_node(self):
        guide_path = COMPILER["ROUTES"] / "README.yaml"
        guide = dict(COMPILER["read_rules"]([guide_path]))[guide_path]
        _, flowcharts, _ = find_block(guide, "hook-flowcharts")
        hooks = dict(COMPILER["read_hook_documents"]())
        _, clause, _ = find_block(hooks[COMPILER["HOOK_SOURCE"] / "planning.yaml"], "execution-body")
        clause["text"] += "\n4. 新的执行要求。"
        with self.assertRaisesRegex(ValueError, "planning-flowchart.*EXECUTION_4"):
            validate_hook_flowcharts(flowcharts, hooks.values())

    def test_conditional_edge_cannot_bypass_delivery(self):
        path = Path("workflows/coding-single-agent.yaml")
        source = COMPILER["SOURCE"] / path
        route = dict(COMPILER["read_rules"]([source]))[source]
        _, chart, _ = find_block(route, "flowchart")
        _, body, _ = find_block(route, "flowchart-body")
        body["text"] = body["text"].replace("\n```", "\n    SM02 -. 绕过交付 .-> DONE\n```")
        with self.assertRaisesRegex(ValueError, "完成节点只能由交付阶段"):
            validate_route_diagram(path, chart["blocks"], [f"SM{i:02}" for i in range(1, 6)])

    def test_every_branch_must_start_and_finish_at_the_shared_boundaries(self):
        diagram = '\n'.join((
            '```mermaid', 'flowchart TD', 'START(["开始"])', 'TASK[任务]', 'LOOP[回路]',
            'END(["结束"])', 'START --> TASK', 'TASK --> END', 'LOOP --> LOOP',
        ))
        for edge, message in (
            ("LOOP --> TASK", "从「开始」无法到达：LOOP"),
            ("TASK --> LOOP", "无法汇入「结束」：LOOP"),
            ("END --> LOOP", "「结束」只能接收连线"),
        ):
            with self.subTest(edge=edge), self.assertRaisesRegex(ValueError, message):
                parse_flowchart("示例", f"{diagram}\n{edge}\n```")
