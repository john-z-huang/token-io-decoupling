"""Development-only checks for source compilation and product-resource integrity."""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from token_io_instruction_compiler.compiler import (  # noqa: E402
    CompilationError,
    Compiler,
    canonical,
    compile_repository,
    deterministic_zip,
    digest,
    extract_heading,
    safe_file,
    validate_dependency_graph,
)


class HeadingTests(unittest.TestCase):
    def test_fenced_heading_does_not_end_or_duplicate_real_section(self):
        text = "## Actions\nDo this.\n```md\n## Actions\nexample\n```\n## End\nOther.\n"
        selected = extract_heading(text, "Actions")
        self.assertIn("Do this.", selected)
        self.assertIn("example", selected)
        self.assertNotIn("Other.", selected)

    def test_duplicate_missing_and_empty_sections_fail(self):
        for text, title in (("## A\nx\n## A\ny", "A"), ("## A\nx", "B"), ("## A\n\n## B\nx", "A")):
            with self.subTest(text=text), self.assertRaises(CompilationError):
                extract_heading(text, title)


class ExecutionDependencyTests(unittest.TestCase):
    def index(self, fragments):
        return {
            "schema_version": 1,
            "nodes": [{"node_id": "contract", "default_fragment_ids": ["a"]}],
            "fragments": fragments,
        }

    def test_missing_dependency_blocks_compilation(self):
        with self.assertRaisesRegex(CompilationError, "missing execution dependency"):
            validate_dependency_graph(
                self.index([{"fragment_id": "a", "dependencies": ["missing"]}])
            )

    def test_cycle_blocks_compilation(self):
        with self.assertRaisesRegex(CompilationError, "cycle"):
            validate_dependency_graph(
                self.index(
                    [
                        {"fragment_id": "a", "dependencies": ["b"]},
                        {"fragment_id": "b", "dependencies": ["a"]},
                    ]
                )
            )

    def test_valid_order_does_not_turn_control_return_into_source_recursion(self):
        validate_dependency_graph(
            self.index([{"fragment_id": "a", "dependencies": ["b"]}, {"fragment_id": "b"}])
        )


class SourceBoundaryTests(unittest.TestCase):
    def test_traversal_and_symlink_sources_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "actual.md").write_text("policy")
            (root / "link.md").symlink_to(root / "actual.md")
            for path in ("../outside.md", "/tmp/outside.md", "link.md", "missing.md"):
                with self.subTest(path=path), self.assertRaises(CompilationError):
                    safe_file(root, path)

    def compiler(self, temp):
        compiler = Compiler.__new__(Compiler)
        compiler.root = Path(temp)
        compiler.project = Path(temp)
        compiler.source = Path(temp)
        compiler.max_chars = 12000
        compiler.report = {"closures": {}, "source_hashes": {}}
        compiler._content_cache = {}
        compiler.units = {}
        compiler._document_sources = {}
        compiler.node_map = {}
        (Path(temp) / "SKILL.md").write_text(
            "# Skill\n\n## Hard constraints\nCheck authorization.\n"
        )
        (Path(temp) / "SKILL_zh_cn.md").write_text("# Skill\n\n## 硬约束\n核验授权。\n")
        return compiler

    def test_navigation_not_an_execution_dependency_and_continuation_is_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            compiler = self.compiler(temp)
            (Path(temp) / "first.md").write_text(
                "# First\n\n## Actions\nBefore changing state apply [Second](second.md).\n\n"
                "## Related concepts\n[Missing](missing.md)\n"
            )
            (Path(temp) / "second.md").write_text(
                "# Second\n\n## Actions\nCheck the grant; reject missing authorization.\n"
            )
            result = compiler.closure(["first.md"], "en")
            self.assertNotIn("second.md", result["text"])
            self.assertIn(
                'rules_get_context(payload={"node_id":"decision","context_version":2,"language":"en","fragment_ids":["unit.',
                result["text"],
            )
            self.assertNotIn("missing", result["text"])
            self.assertEqual(1, len(compiler.units))
            self.assertEqual(
                ["first.md"], compiler.report["closures"]["en:codex:first.md"]["sources"]
            )

    def test_unavailable_required_policy_fails_instead_of_source_pointer(self):
        with tempfile.TemporaryDirectory() as temp:
            compiler = self.compiler(temp)
            (Path(temp) / "first.md").write_text("# First\nApply [Missing](missing.md).\n")
            with self.assertRaisesRegex(CompilationError, "missing operational policy target"):
                compiler.closure(["first.md"], "en")

    def test_document_links_keep_author_labels_while_mcp_keeps_exact_unit_lookups(self):
        with tempfile.TemporaryDirectory() as temp:
            compiler = self.compiler(temp)
            for language, suffix, labels in (
                ("en", "", ("Second policy", "The same policy")),
                ("zh_cn", "_zh_cn", ("第二项政策", "同一项政策")),
            ):
                source = f"first{suffix}.md"
                target = f"second{suffix}.md"
                text = f"# First\nApply [{labels[0]}]({target}) and [{labels[1]}]({target}).\n"
                (Path(temp) / source).write_text(text)
                (Path(temp) / target).write_text("# Second\nCheck authorization.\n")
                document = compiler.closure([source], language, "documents")["text"]
                expected_target = "../" + compiler.document_path("second.md", language)
                for label in labels:
                    self.assertIn(f"[{label}]({expected_target})", document)
                self.assertNotIn("instruction continuation:", document)
                self.assertNotRegex(document, r"\[unit\.[a-f0-9]+\]")
                mcp = compiler.closure([source], language)["text"]
                unit_id, _ = compiler.register_unit("second.md")
                self.assertIn(f'"fragment_ids":["{unit_id}"]', mcp)
                self.assertIn("rules_get_context(payload=", mcp)
                self.assertNotIn(expected_target, mcp)

    def test_budget_failure_never_truncates_required_instruction(self):
        with tempfile.TemporaryDirectory() as temp:
            compiler = self.compiler(temp)
            compiler.max_chars = 100
            (Path(temp) / "first.md").write_text("# First\n" + "Required guard. " * 50)
            with self.assertRaisesRegex(CompilationError, "exceeds approved bound"):
                compiler.closure(["first.md"], "en")

    def test_bilingual_whole_owner_has_one_stable_unit_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            compiler = self.compiler(temp)
            english = compiler.register_unit("references/owner.md")
            chinese = compiler.register_unit("references/owner_zh_cn.md")
            self.assertEqual(english, chinese)

    def test_readable_document_names_preserve_source_and_section_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            compiler = self.compiler(temp)
            source = "references/coding/layer-02-workflow-concepts/entry-and-context/contract.md"
            self.assertEqual(
                "instructions/workflow-concepts--entry-and-context--contract.md",
                compiler.document_path(source, "en"),
            )
            self.assertEqual(
                compiler.document_path(source, "zh_cn"),
                compiler.document_path(source.replace(".md", "_zh_cn.md"), "zh_cn"),
            )
            self.assertNotEqual(
                compiler.document_path(source, "en"),
                compiler.document_path(source + "#Actions", "en"),
            )
            self.assertNotEqual(
                compiler.document_path("references/first/policy.md", "en"),
                compiler.document_path("references/second/policy.md", "en"),
            )

    def test_readable_name_collision_fails_instead_of_merging_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            compiler = self.compiler(temp)
            compiler.document_path("references/first_owner.md", "en")
            with self.assertRaisesRegex(CompilationError, "document path collision"):
                compiler.document_path("references/first-owner.md", "en")

    def test_unique_repair_owner_keeps_its_exact_checkpoint_node(self):
        with tempfile.TemporaryDirectory() as temp:
            compiler = self.compiler(temp)
            owners = {
                "repair_scope": "repair-scope-gate",
                "repair_execution": "repair-execution",
                "repair_handoff": "repair-verification-handoff",
            }
            compiler.node_map = {
                node_id: {"owner_path": f"docs/skill/references/{owner}.md"}
                for node_id, owner in owners.items()
            }
            for node_id, owner in owners.items():
                english, english_node = compiler.register_unit(f"references/{owner}.md")
                chinese, chinese_node = compiler.register_unit(f"references/{owner}_zh_cn.md")
                self.assertEqual(english, chinese)
                self.assertEqual(node_id, english_node)
                self.assertEqual(node_id, chinese_node)

    def test_unknown_node_phase_fails_before_compilation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = root / "instruction-compiler/sources"
            sources.mkdir(parents=True)
            (sources / "rule-registry.json").write_text(
                json.dumps({"nodes": [{"node_id": "unregistered_checkpoint"}]})
            )
            (sources / "rule-context-index.json").write_text(
                json.dumps({"nodes": [], "fragments": []})
            )
            with self.assertRaisesRegex(CompilationError, "unsupported rule node phase"):
                Compiler(root)


class OptionalExportTests(unittest.TestCase):
    def setUp(self):
        repository = Path(__file__).resolve().parents[2]
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.preview = self.root / "skills/token-io-decoupling"
        resource = (
            repository
            / "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/_resources"
        )
        instructions = json.loads((resource / "instructions.json").read_bytes())
        bundle = repository / "mcp/src/token_io_decoupling/_resources/skill_bundle.zip"
        with zipfile.ZipFile(bundle) as archive:
            self.skill_files = {name: archive.read(name) for name in archive.namelist()}
        report = json.loads((repository / "instruction-compiler/build-report.json").read_bytes())
        report.pop("build_id")
        compiler_patch = patch("token_io_instruction_compiler.compiler.Compiler")
        compiler = compiler_patch.start().return_value
        self.addCleanup(compiler_patch.stop)
        compiler.compile.return_value = instructions, self.skill_files
        compiler.report = report
        compile_repository(self.root)
        self.persistent = [
            path
            for path in self.root.rglob("*")
            if path.is_file() and self.preview not in path.parents
        ]

    def test_absent_export_is_optional_and_check_does_not_create_it(self):
        shutil.rmtree(self.preview)
        snapshot = {path: path.read_bytes() for path in self.persistent}
        compile_repository(self.root, check=True)
        self.assertFalse(self.preview.exists())
        self.assertEqual(snapshot, {path: path.read_bytes() for path in self.persistent})

    def test_existing_export_still_rejects_missing_changed_and_extra_files(self):
        entry = self.preview / "SKILL.md"
        original = entry.read_bytes()
        entry.unlink()
        with self.assertRaisesRegex(CompilationError, "skills/token-io-decoupling/SKILL.md"):
            compile_repository(self.root, check=True)
        entry.write_bytes(original + b"unexpected change\n")
        with self.assertRaisesRegex(CompilationError, "skills/token-io-decoupling/SKILL.md"):
            compile_repository(self.root, check=True)
        entry.write_bytes(original)
        extra = self.preview / "obsolete.md"
        extra.write_text("obsolete\n")
        with self.assertRaisesRegex(CompilationError, "obsolete.md"):
            compile_repository(self.root, check=True)

    def test_persistent_artifacts_are_required_and_checked_without_export(self):
        shutil.rmtree(self.preview)
        self.assertEqual(4, len(self.persistent))
        for path in self.persistent:
            with self.subTest(path=path.relative_to(self.root)):
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(CompilationError, "resources are stale"):
                    compile_repository(self.root, check=True)
                path.write_bytes(original + b"unexpected change\n")
                with self.assertRaisesRegex(CompilationError, "resources are stale"):
                    compile_repository(self.root, check=True)
                path.write_bytes(original)

    def test_compile_recreates_the_optional_export(self):
        shutil.rmtree(self.preview)
        compile_repository(self.root)
        for path, expected in self.skill_files.items():
            self.assertEqual(expected, (self.preview / path).read_bytes())
        compile_repository(self.root, check=True)

    def test_compile_retires_only_unmodified_files_from_the_previous_manifest(self):
        retired = self.preview / "instructions/unit.0123456789abcdef.md"
        retired.write_text("old generated instruction\n")
        manifest_path = self.preview / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["files"][retired.relative_to(self.preview).as_posix()] = digest(
            retired.read_bytes()
        )
        manifest_path.write_text(json.dumps(manifest))
        retired.write_text("local edits\n")
        with self.assertRaisesRegex(
            CompilationError, "obsolete exported document has local changes"
        ):
            compile_repository(self.root)
        self.assertEqual("local edits\n", retired.read_text())
        retired.write_text("old generated instruction\n")
        compile_repository(self.root)
        self.assertFalse(retired.exists())
        compile_repository(self.root, check=True)
        compile_repository(self.root)
        compile_repository(self.root, check=True)


class ProductResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        cls._skill_export = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._skill_export.cleanup)
        cls.skill_root = Path(cls._skill_export.name)
        bundle = root / "mcp/src/token_io_decoupling/_resources/skill_bundle.zip"
        with zipfile.ZipFile(bundle) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise AssertionError("duplicate packaged Skill file")
            for name in names:
                path = Path(name)
                if path.is_absolute() or ".." in path.parts or "\\" in name:
                    raise AssertionError("unsafe packaged Skill path")
                destination = cls.skill_root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(name))

    def resource(self):
        root = Path(__file__).resolve().parents[2]
        path = (
            root
            / "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core"
            / "_resources/instructions.json"
        )
        return root, json.loads(path.read_text())

    def without_continuations(self, text):
        text = text.replace(" (instruction continuation: workflow_capabilities())", "")
        text = re.sub(
            r" \(instruction continuation: `rules_get_context\(payload=\{[^\n]+?\}\)`\)", "", text
        )
        text = re.sub(r" \(instruction continuation: \[[^\]]+\]\([^)]+\)\)", "", text)
        return re.sub(r"\[([^\]]+)\]\((?:\.\./)?(?:instructions|steps|routes)/[^)]+\)", r"\1", text)

    def test_generic_preflight_instructions_match_product_scope(self):
        _root, instructions = self.resource()
        self.assertNotIn("skill_maintenance", json.dumps(instructions))
        english = instructions["policies"]["candidate-compliance"]["en"]["text"]
        self.assertIn("payload.request.policy_scope: generic_project", english)
        self.assertIn("does not validate language-mirror presence", english)
        self.assertIn("target repository's own required", english)
        documentation = instructions["routes"]["single_agent"]["en"]["stages"]["documentation"][
            "text"
        ]
        self.assertIn("declared generic path and baseline checks", documentation)

    def test_generated_entry_and_document_cards_define_delivery_hash_boundaries(self):
        root, instructions = self.resource()
        skill_root = self.skill_root
        manifest = json.loads((skill_root / "manifest.json").read_text())
        compiler = Compiler(root)
        route_entry = "references/coding/layer-03-workflow-checkpoints/route-entry.md"
        for language in ("en", "zh_cn"):
            suffix = "_zh_cn" if language == "zh_cn" else ""
            entry_path = f"SKILL{suffix}.md"
            entry = (skill_root / entry_path).read_text()
            self.assertNotIn("Each step contains its required policy content", entry)
            self.assertNotIn("每步包含必要政策内容", entry)
            self.assertIn("workflow_capabilities", entry)
            self.assertIn("rules_get_context", entry)
            self.assertIn("context_version=2", entry)
            self.assertIn("decide_decoupling_workflow", entry)
            self.assertIn(
                f"[Mode]({compiler.document_path(compiler.node_path('mode', 'en'), language)}) → "
                f"[Route Entry]({compiler.document_path(route_entry, language)})",
                entry,
            )
            self.assertIn(
                "[Skill manifest](manifest.json)"
                if language == "en"
                else "[Skill 清单](manifest.json)",
                entry,
            )
            self.assertIn(f'manifest.files["{entry_path}"]', entry)
            self.assertEqual(
                digest(
                    (skill_root / entry_path)
                    .read_bytes()
                    .replace(instructions["build_id"].encode(), b"__BUILD_ID__")
                ),
                instructions["document_units"][entry_path],
            )
            for route in instructions["routes"].values():
                for stage in route[language]["stages"].values():
                    card_path = f"steps/{stage['module_id']}{suffix}.md"
                    card = (skill_root / card_path).read_text()
                    self.assertIn(f'manifest.files["{card_path}"]', card)
                    self.assertIn(
                        f'manifest.files["instructions/common.hard_constraints{suffix}.md"]',
                        card,
                    )
                    self.assertIn("../manifest.json", card)
                    self.assertIn("fragment.text_sha256", card)
                    self.assertIn("manifest.build_id", card)
                    for file_key in re.findall(r'manifest\.files\["([^"]+)"\]', card):
                        self.assertIn(file_key, manifest["files"])
                        self.assertEqual(
                            digest((skill_root / file_key).read_bytes()),
                            manifest["files"][file_key],
                        )

    def test_entry_only_delivery_change_invalidates_build_without_changing_rules(self):
        root, _instructions = self.resource()
        baseline, _files = Compiler(root).compile()
        original_notice = Compiler.document_integrity_notice

        def changed_entry(self, paths, language, manifest_href):
            text = original_notice(self, paths, language, manifest_href)
            return text + ("\nEntry delivery amendment." if paths == ["SKILL.md"] else "")

        with patch.object(Compiler, "document_integrity_notice", changed_entry):
            changed, _changed_files = Compiler(root).compile()
        self.assertNotEqual(baseline["build_id"], changed["build_id"])
        self.assertNotEqual(
            baseline["document_units"]["SKILL.md"], changed["document_units"]["SKILL.md"]
        )
        self.assertEqual(baseline["nodes"], changed["nodes"])
        self.assertEqual(baseline["fragments"], changed["fragments"])
        self.assertEqual(baseline["routes"], changed["routes"])

    def test_compact_stages_keep_local_actions_and_exact_shared_return_maps(self):
        root, instructions = self.resource()
        compiler = Compiler(root)
        for route, prefix, name in (
            ("single_agent", "SM", "coding-single-agent"),
            ("multi_agent", "MM", "coding-multi-agent"),
        ):
            for language in ("en", "zh_cn"):
                suffix = "_zh_cn" if language == "zh_cn" else ""
                route_source = f"references/coding/layer-04-workflows/{name}{suffix}.md"
                selector_source = f"workflows/coding{suffix}.md"
                heading = "前置返回映射" if language == "zh_cn" else "Prerequisite return map"
                expected = compiler.clean_text(
                    extract_heading(compiler.read_source(route_source), heading)
                )
                entry = instructions["routes"][route][language]["entry"]
                self.assertIn(expected, self.without_continuations(entry["text"]))
                shared_id = f"route.{route}.return_map"
                shared = instructions["fragments"][shared_id][language]
                self.assertIn(expected, self.without_continuations(shared["text"]))
                for stage, item in instructions["routes"][route][language]["stages"].items():
                    with self.subTest(route=route, language=language, stage=stage):
                        self.assertNotIn(expected, self.without_continuations(item["text"]))
                        self.assertNotIn(
                            compiler.source_identity(route_source), item["instruction_ids"]
                        )
                        self.assertNotIn(
                            compiler.source_identity(selector_source), item["instruction_ids"]
                        )
                        number = int(item["module_id"][-2:])
                        parts = compiler.route_stage_parts(route_source, language, number)
                        module_names = {
                            "entry_readiness": "entry-readiness",
                            "session_readiness": "session-readiness",
                            "work_definition": "work-definition",
                            "execution": "single-execution"
                            if prefix == "SM"
                            else "delegated-execution",
                            "verification_repair": "verification-repair",
                            "documentation": "documentation",
                            "delivery_acceptance": "delivery-acceptance",
                        }
                        module_path = (
                            "references/coding/layer-04-workflows/modules/"
                            f"{module_names[stage]}{suffix}.md"
                        )
                        parts["current_step"] = compiler.inline_stage_module(
                            route_source, parts["current_step"], module_path, language
                        )
                        for part in parts.values():
                            self.assertIn(
                                compiler.clean_text(part), self.without_continuations(item["text"])
                            )
                        current_step, _ = compiler.render_text(
                            route_source, parts["current_step"], language, "codex", prefix
                        )
                        own_module_id, _ = compiler.register_unit(module_path)
                        self.assertNotIn(own_module_id, current_step)
                        self.assertIn(
                            "the complete module provided below in this response"
                            if language == "en"
                            else "本响应下方已完整提供的模块",
                            current_step,
                        )
                        module_text = compiler.clean_text(
                            compiler.operational_source(module_path, "codex")
                        )
                        self.assertIn(module_text, self.without_continuations(item["text"]))
                        requirements = {
                            value["instruction_id"]: value for value in item["shared_requirements"]
                        }
                        requirement = requirements[shared_id]
                        self.assertEqual("needs_prerequisite", requirement["when"])
                        self.assertEqual(shared["text_sha256"], requirement["text_sha256"])
                        self.assertEqual(
                            [shared_id],
                            requirement["lookup"]["arguments"]["payload"]["fragment_ids"],
                        )
                        card = (
                            self.skill_root / f"steps/{item['module_id']}{suffix}.md"
                        ).read_text()
                        self.assertNotIn(expected, self.without_continuations(card))
                        self.assertIn(f"../instructions/{shared_id}{suffix}.md", card)
                        self.assertLessEqual(len(item["text"]), 60000)
                documentation = instructions["routes"][route][language]["stages"]["documentation"][
                    "text"
                ]
                if language == "en":
                    self.assertIn(f"return to {prefix}05", documentation)
                    self.assertIn(f"suspended {prefix}06 substep", documentation)
                    self.assertIn("Do not repeat those gates", documentation)
                    self.assertIn("readback and current epoch/effect checks", documentation)
                else:
                    self.assertIn(f"{prefix}05", documentation)
                    self.assertIn(f"{prefix}06", documentation)

    def test_complete_author_hard_constraints_are_delivered_without_paraphrase(self):
        root, instructions = self.resource()
        compiler = Compiler(root)
        for language in ("en", "zh_cn"):
            suffix = "_zh_cn" if language == "zh_cn" else ""
            source = compiler.read_source(f"SKILL{suffix}.md")
            expected = compiler.clean_text(
                extract_heading(source, "Hard constraints" if language == "en" else "硬约束")
            )
            entry = (self.skill_root / f"SKILL{suffix}.md").read_text()
            self.assertIn(expected, self.without_continuations(entry))
            for node in instructions["nodes"].values():
                self.assertIn(expected, self.without_continuations(node[language]["text"]))
                self.assertIn("common.hard_constraints", node[language]["instruction_ids"])
            for route in instructions["routes"].values():
                for stage in route[language]["stages"].values():
                    self.assertNotIn(expected, self.without_continuations(stage["text"]))
                    self.assertIn(compiler.critical_stage_guard(language), stage["text"])
                    requirement = stage["shared_requirements"][0]
                    self.assertEqual("common.hard_constraints", requirement["instruction_id"])
                    self.assertEqual("before_any_action", requirement["when"])
                    self.assertEqual(
                        instructions["fragments"]["common.hard_constraints"][language][
                            "text_sha256"
                        ],
                        requirement["text_sha256"],
                    )
                    self.assertNotIn("common.hard_constraints", stage["instruction_ids"])
            shared = instructions["fragments"]["common.hard_constraints"][language]
            self.assertIn(expected, self.without_continuations(shared["text"]))

    def test_document_only_provider_change_invalidates_build_identity(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary:
            synthetic = Path(temporary)
            source_root = synthetic / "instruction-compiler/sources"
            shutil.copytree(root / "instruction-compiler/sources", source_root)
            before, before_skill = Compiler(synthetic).compile()
            policy = (
                source_root
                / "skill/references/coding/layer-01-fundamental-concepts"
                / "execution-planning/candidate-compliance.md"
            )
            source = policy.read_text()
            marker = "## Related concepts"
            self.assertEqual(1, source.count(marker))
            policy.write_text(
                source.replace(marker, "Retain the verified document-build identity.\n\n" + marker)
            )
            after, after_skill = Compiler(synthetic).compile()
            self.assertEqual(before["nodes"], after["nodes"])
            self.assertEqual(before["policies"], after["policies"])
            self.assertNotEqual(before["document_units"], after["document_units"])
            self.assertNotEqual(before["build_id"], after["build_id"])
            self.assertNotEqual(before_skill, after_skill)
            old_manifest = json.loads(before_skill["manifest.json"])
            self.assertNotEqual(after["build_id"], old_manifest["build_id"])

    def test_author_hard_constraint_change_invalidates_all_delivery_surfaces(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary:
            synthetic = Path(temporary)
            source_root = synthetic / "instruction-compiler/sources"
            shutil.copytree(root / "instruction-compiler/sources", source_root)
            before, before_skill = Compiler(synthetic).compile()
            entry = source_root / "skill/SKILL.md"
            source = entry.read_text()
            guard = "Synthetic guard: do not mutate an unreleased candidate."
            self.assertEqual(1, source.count("## Completion"))
            entry.write_text(source.replace("## Completion", "- " + guard + "\n\n## Completion"))
            after, after_skill = Compiler(synthetic).compile()
            self.assertNotEqual(before["build_id"], after["build_id"])
            self.assertNotEqual(before_skill["SKILL.md"], after_skill["SKILL.md"])
            self.assertIn(guard, after_skill["SKILL.md"].decode())
            for node_id, item in after["nodes"].items():
                self.assertIn(guard, item["en"]["text"])
                self.assertNotEqual(before["nodes"][node_id]["en"], item["en"])
            for route_id, route in after["routes"].items():
                for stage_id, stage in route["en"]["stages"].items():
                    shared = after["fragments"]["common.hard_constraints"]["en"]
                    self.assertIn(guard, shared["text"])
                    self.assertEqual(
                        shared["text_sha256"], stage["shared_requirements"][0]["text_sha256"]
                    )
                    self.assertNotEqual(before["routes"][route_id]["en"]["stages"][stage_id], stage)

    def test_all_generated_markdown_has_exactly_one_final_newline(self):
        root, _instructions = self.resource()
        skill_root = self.skill_root
        manifest = json.loads((skill_root / "manifest.json").read_text())
        for path in manifest["files"]:
            if path.endswith(".md"):
                with self.subTest(path=path):
                    content = (skill_root / path).read_bytes()
                    self.assertEqual(content.rstrip() + b"\n", content)

    def test_shared_source_has_one_document_but_distinct_checkpoint_contracts(self):
        root, instructions = self.resource()
        compiler = Compiler(root)
        index = json.loads((self.skill_root / "instruction-index.json").read_bytes())
        self.assertEqual(1, index["schema_version"])
        self.assertEqual(set(instructions["nodes"]), set(index["checkpoints"]))
        for spec in compiler.registry["nodes"]:
            checkpoint = index["checkpoints"][spec["node_id"]]
            for key in (
                "node_id",
                "required_facts",
                "required_evidence",
                "legal_branches",
                "evaluation_mode",
                "failure_action",
                "next_checkpoint_ids",
            ):
                self.assertEqual(spec[key], checkpoint[key], (spec["node_id"], key))
        contract = index["checkpoints"]["contract"]
        change = index["checkpoints"]["contract_change"]
        self.assertEqual(contract["documents"], change["documents"])
        self.assertNotEqual(contract["required_facts"], change["required_facts"])
        self.assertNotEqual(contract["legal_branches"], change["legal_branches"])
        self.assertNotEqual(contract["next_checkpoint_ids"], change["next_checkpoint_ids"])
        unit_id, _ = compiler.register_unit(compiler.node_path("contract", "en"))
        self.assertEqual(contract["documents"], index["units"][unit_id])
        # Selected sections of one owner retain separate content and destinations.
        for language in ("en", "zh_cn"):
            self.assertNotEqual(
                index["checkpoints"]["slice"]["documents"][language],
                index["checkpoints"]["control"]["documents"][language],
            )

    def test_exported_instruction_bodies_are_unique_and_names_are_readable(self):
        seen = {}
        for path in sorted((self.skill_root / "instructions").glob("*.md")):
            self.assertNotRegex(path.name, r"^(?:unit\.[a-f0-9]{16}|checkpoint\.)")
            text = path.read_text()
            title = text.splitlines()[0]
            self.assertNotRegex(title, r"unit\.[a-f0-9]{16}")
            body = text.split("\n\n", 2)[2]
            fingerprint = digest(body)
            self.assertNotIn(fingerprint, seen, (path.name, seen.get(fingerprint)))
            seen[fingerprint] = path.name

    def test_instruction_index_is_integrity_bound_and_links_stay_in_language(self):
        root, instructions = self.resource()
        compiler = Compiler(root)
        payload = (self.skill_root / "instruction-index.json").read_bytes()
        index = json.loads(payload)
        manifest = json.loads((self.skill_root / "manifest.json").read_bytes())
        for mapping in (
            instructions["document_units"],
            instructions["skill_files"],
            manifest["files"],
        ):
            self.assertEqual(digest(payload), mapping["instruction-index.json"])
        for unit_id in index["units"]:
            self.assertIn(unit_id, instructions["fragments"])
        documents = [item["documents"] for item in index["checkpoints"].values()]
        documents.extend(index["units"].values())
        for localized in documents:
            self.assertEqual(set(localized), {"en", "zh_cn"})
            english, chinese = localized["en"], localized["zh_cn"]
            self.assertEqual(english.removesuffix(".md") + "_zh_cn.md", chinese)
            for path in localized.values():
                content = (self.skill_root / path).read_text()
                self.assertEqual(digest(content), manifest["files"][path])
                self.assertIn(
                    f"[English]({Path(english).name}) | [简体中文]({Path(chinese).name})", content
                )
        for path in self.skill_root.rglob("*.md"):
            text = path.read_text()
            # Only the explicitly labelled language switch may cross languages.
            text = "\n".join(line for line in text.splitlines() if "[English](" not in line)
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in target or not target.split("#", 1)[0].endswith(".md"):
                    continue
                self.assertEqual(path.name.endswith("_zh_cn.md"), target.endswith("_zh_cn.md"))
        for node_id in compiler.node_map:
            for language in ("en", "zh_cn"):
                source = compiler.node_path(node_id, language)
                expected = compiler.clean_text(compiler.operational_source(source, "documents"))
                card = (
                    self.skill_root / index["checkpoints"][node_id]["documents"][language]
                ).read_text()
                self.assertIn(expected, self.without_continuations(card))

    def test_all_document_links_use_readable_labels_including_shared_requirements(self):
        for path in self.skill_root.rglob("*.md"):
            text = path.read_text()
            self.assertNotRegex(text, r"\[unit\.[a-f0-9]{16}\]")
            self.assertNotIn("instruction continuation: [", text)
        for language, suffix in (("en", ""), ("zh_cn", "_zh_cn")):
            lifecycle = self.skill_root / (
                "instructions/fundamental-concepts--delegation--delegation-child-lifecycle"
                f"{suffix}.md"
            )
            label = (
                "Runtime and Model Provider Support"
                if language == "en"
                else "运行环境与模型厂商支持"
            )
            target = (
                "../instructions/fundamental-concepts--session-runtime--runtime-provider-support"
                f"{suffix}.md"
            )
            self.assertIn(f"[{label}]({target})", lifecycle.read_text())
            for prefix in ("SM", "MM"):
                step = (self.skill_root / f"steps/{prefix}01{suffix}.md").read_text()
                hard = "Hard constraints" if language == "en" else "硬约束"
                returns = "Prerequisite return map" if language == "en" else "前置返回映射"
                self.assertIn(f"[{hard}](../instructions/common.hard_constraints{suffix}.md)", step)
                self.assertIn(f"[{returns}](../instructions/route.", step)

    def test_zip_is_reproducible_and_manifest_is_at_skill_root(self):
        files = {"SKILL.md": b"entry", "manifest.json": b"{}", "steps/a.md": b"action"}
        first = deterministic_zip(files)
        self.assertEqual(first, deterministic_zip(dict(reversed(list(files.items())))))
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertEqual(sorted(files), archive.namelist())
            self.assertIn("manifest.json", archive.namelist())

    def test_generated_batch_and_all_continuation_ids_are_complete(self):
        root = Path(__file__).resolve().parents[2]
        resource = (
            root / "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/_resources"
        )
        data = (resource / "instructions.json").read_bytes()
        instructions = json.loads(data)
        manifest = json.loads((resource / "manifest.json").read_text())
        self.assertEqual(digest(data), manifest["files"]["instructions.json"])
        self.assertEqual(instructions["build_id"], manifest["build_id"])
        semantic = {
            key: value
            for key, value in instructions.items()
            if key not in {"build_id", "skill_files"}
        }
        self.assertEqual(digest(canonical(semantic)), instructions["build_id"])
        source_registry = json.loads(
            (root / "instruction-compiler/sources/rule-registry.json").read_text()
        )
        self.assertEqual(
            {entry["node_id"] for entry in source_registry["nodes"]}, set(instructions["nodes"])
        )
        self.assertEqual(20, len(instructions["nodes"]))
        expected_repair_chain = {
            "repair": ["repair_scope"],
            "repair_scope": ["repair_execution"],
            "repair_execution": ["repair_handoff"],
            "repair_handoff": ["verification"],
        }
        generated_registry = {
            entry["node_id"]: entry for entry in instructions["registry"]["nodes"]
        }
        for node_id, successors in expected_repair_chain.items():
            self.assertEqual(successors, generated_registry[node_id]["next_checkpoint_ids"])
        registered = {entry["fragment_id"] for entry in instructions["context_index"]["fragments"]}
        self.assertEqual(registered, set(instructions["fragments"]))
        for unit_id in re.findall(r'fragment_ids\\?"?:\[\\?"(unit\.[a-f0-9]+)', data.decode()):
            self.assertIn(unit_id, registered)
        texts = [
            item["text"]
            for localized in instructions["nodes"].values()
            for item in localized.values()
        ]
        texts += [
            item["text"]
            for localized in instructions["fragments"].values()
            for item in localized.values()
        ]
        texts += [
            item["text"]
            for localized in instructions["policies"].values()
            for item in localized.values()
        ]
        texts += [
            item["text"]
            for route in instructions["routes"].values()
            for localized in route.values()
            for item in localized["stages"].values()
        ]
        continuation_count = 0
        for text in texts:
            for serialized in re.findall(r"rules_get_context\(payload=(\{[^\n]+?\})\)", text):
                payload = json.loads(serialized)
                continuation_count += 1
                self.assertEqual(2, payload["context_version"])
                required = 0
                for fragment_id in payload["fragment_ids"]:
                    self.assertIn(fragment_id, registered)
                    required += len(
                        instructions["fragments"][fragment_id][payload["language"]]["text"]
                    )
                self.assertGreaterEqual(payload["max_chars"], required)
                self.assertLessEqual(payload["max_chars"], 60000)
        self.assertGreater(continuation_count, 100)
        skill_root = self.skill_root
        skill_manifest = json.loads((skill_root / "manifest.json").read_text())
        self.assertEqual(instructions["build_id"], skill_manifest["build_id"])
        self.assertEqual(instructions["skill_files"], skill_manifest["files"])
        self.assertEqual(
            set(skill_manifest["files"]) | {"manifest.json"},
            {
                path.relative_to(skill_root).as_posix()
                for path in skill_root.rglob("*")
                if path.is_file()
            },
        )
        for path, expected in skill_manifest["files"].items():
            self.assertEqual(expected, digest((skill_root / path).read_bytes()))
            if path.endswith(".md"):
                text = (skill_root / path).read_text()
                for target in re.findall(r"\]\(([^)]+)\)", text):
                    if "://" not in target and not target.startswith("#"):
                        self.assertTrue(
                            ((skill_root / path).parent / target.split("#", 1)[0]).is_file(),
                            (path, target),
                        )
                self.assertNotIn("instruction-compiler/sources/", text)
        for node, languages in instructions["nodes"].items():
            for language, item in languages.items():
                with self.subTest(node=node, language=language):
                    self.assertEqual(item["text"].strip(), item["text"])
                    self.assertEqual(digest(item["text"]), item["content_sha256"])
                    self.assertLessEqual(len(item["text"]), 12000)


if __name__ == "__main__":
    unittest.main()
