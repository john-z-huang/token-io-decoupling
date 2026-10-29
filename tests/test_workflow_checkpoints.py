"""Negative regressions for Layer-03 checkpoint ownership and route consumption."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-workflow-checkpoints.py"
SOURCE_DIR = SCRIPT.parent.parent / "references/coding/layer-03-workflow-checkpoints"
ROUTE_DIR = SCRIPT.parent.parent / "references/coding/layer-04-workflows"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("workflow_checkpoints", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WorkflowCheckpointValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        MODULE.ROOT = self.root
        MODULE.DIR = self.root / "references/coding/layer-03-workflow-checkpoints"
        MODULE.DIR.mkdir(parents=True)
        routes = self.root / "references/coding/layer-04-workflows"
        routes.mkdir(parents=True)
        for slug in MODULE.SLUGS:
            (MODULE.DIR / f"{slug}.md").write_text(
                "[English](x) | [简体中文](x)\n" + "\nbody\n".join(MODULE.REQUIRED_SECTIONS["en"]) + "\nbody",
                encoding="utf-8",
            )
            (MODULE.DIR / f"{slug}_zh_cn.md").write_text(
                "[English](x) | [简体中文](x)\n" + "\n正文\n".join(MODULE.REQUIRED_SECTIONS["zh"]) + "\n正文",
                encoding="utf-8",
            )
        for route, nodes in MODULE.CONSUMERS.items():
            lines = []
            grouped: dict[str, list[str]] = {}
            for slug, steps in nodes.items():
                for step in steps:
                    grouped.setdefault(step, []).append(slug)
            for step, slugs in sorted(grouped.items(), key=lambda item: int(item[0][:-1])):
                lines.append(f"{step} **step**")
                suffix = "_zh_cn" if route.endswith("_zh_cn.md") else ""
                lines.extend(
                    f"[node](../layer-03-workflow-checkpoints/{slug}{suffix}.md)" for slug in slugs
                )
            base = route.removesuffix(".md")
            (routes / f"{base}.md").write_text("\n".join(lines), encoding="utf-8")
            (routes / f"{base}_zh_cn.md").write_text(
                "\n".join(line.replace(".md)", "_zh_cn.md)") for line in lines),
                encoding="utf-8",
            )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_validator(self) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = MODULE.main()
        return result, output.getvalue()

    def test_complete_fixture_passes(self):
        self.assertEqual(self.run_validator()[0], 0)

    def test_missing_owner_fails(self):
        (MODULE.DIR / "route-entry.md").unlink()
        result, output = self.run_validator()
        self.assertEqual(result, 1)
        self.assertIn("missing owner", output)

    def test_missing_route_consumer_fails(self):
        path = self.root / "references/coding/layer-04-workflows/coding-single-agent.md"
        path.write_text(
            path.read_text().replace(
                "../layer-03-workflow-checkpoints/enhanced-path-selection.md", "missing.md"
            ),
            encoding="utf-8",
        )
        result, output = self.run_validator()
        self.assertEqual(result, 1)
        self.assertIn("enhanced-path-selection not consumed", output)

    def test_bare_path_does_not_count_as_route_consumer(self):
        path = self.root / "references/coding/layer-04-workflows/coding-single-agent.md"
        target = "../layer-03-workflow-checkpoints/enhanced-path-selection.md"
        path.write_text(path.read_text().replace(f"[node]({target})", target), encoding="utf-8")
        result, output = self.run_validator()
        self.assertEqual(result, 1)
        self.assertIn("enhanced-path-selection not consumed", output)

    def test_wrong_directory_or_language_does_not_count_as_route_consumer(self):
        route_path = self.root / "references/coding/layer-04-workflows/coding-single-agent.md"
        wrong_targets = (
            "../layer-01-fundamental-concepts/enhanced-path-selection.md",
            "../layer-03-workflow-checkpoints/enhanced-path-selection_zh_cn.md",
        )
        for target in wrong_targets:
            with self.subTest(target=target):
                route_path.write_text(
                    route_path.read_text().replace(
                        "../layer-03-workflow-checkpoints/enhanced-path-selection.md",
                        target,
                    ),
                    encoding="utf-8",
                )
                result, output = self.run_validator()
                self.assertEqual(result, 1)
                self.assertIn("enhanced-path-selection not consumed", output)
                route_path.write_text(
                    route_path.read_text().replace(target, "../layer-03-workflow-checkpoints/enhanced-path-selection.md"),
                    encoding="utf-8",
                )

    def test_session_audit_timeout_and_reuse_regressions(self):
        en = (SOURCE_DIR / "session-audit-resolution.md").read_text(encoding="utf-8")
        zh = (SOURCE_DIR / "session-audit-resolution_zh_cn.md").read_text(encoding="utf-8")
        for text, heading, next_heading in (
            (en, "   - **Timeout and record check.**", "## Multi-Agent audit evidence"),
            (zh, "   - **超时与读回核对。**", "## 多代理审计证据"),
        ):
            timeout_section = text.split(heading, 1)[1].split(next_heading, 1)[0]
            self.assertNotIn("worker_log_visibility", timeout_section)
            self.assertNotIn("worker_log_evidence", timeout_section)
            self.assertNotIn("Without a Worker", timeout_section)
            self.assertNotIn("无 Worker 时", timeout_section)
        self.assertIn("preserve a valid Worker cadence or fill a missing one as `full/default`", en)
        self.assertIn("保留有效 Worker cadence，缺失时补为 `full/default`", zh)
        self.assertIn("status: reused` and resolution `startup_explicit`", en)
        self.assertIn("status: reused` and resolution `prior_record`", en)
        self.assertIn("status: reused` 和 resolution `startup_explicit`", zh)
        self.assertIn("status: reused` 和 resolution `prior_record`", zh)
        self.assertIn("prompt, timing, and response evidence", en)
        self.assertIn("提示、计时和答复证据", zh)

    def test_fixed_prompt_is_owned_once_and_absent_from_routes(self):
        en = (SOURCE_DIR / "session-audit-resolution.md").read_text(encoding="utf-8")
        zh = (SOURCE_DIR / "session-audit-resolution_zh_cn.md").read_text(encoding="utf-8")
        self.assertEqual(en.count("> Root audit preference for this Coding session?"), 1)
        self.assertEqual(zh.count("> 当前 Coding 会话的 Root 审计偏好？"), 1)
        for route_path in ROUTE_DIR.glob("coding-*-agent*.md"):
            route = route_path.read_text(encoding="utf-8")
            self.assertNotIn("Root audit preference for this Coding session?", route)
            self.assertNotIn("当前 Coding 会话的 Root 审计偏好？", route)

    def test_missing_or_empty_section_fails(self):
        path = MODULE.DIR / "context-source-selection.md"
        path.write_text(
            "[English] [简体中文]\n## Trigger and inputs\n\n## Decision and result\nbody\n## Failure boundary\nbody\n## Related concepts\nlink\n",
            encoding="utf-8",
        )
        result, output = self.run_validator()
        self.assertEqual(result, 1)
        self.assertIn("empty section", output)


if __name__ == "__main__":
    unittest.main()
