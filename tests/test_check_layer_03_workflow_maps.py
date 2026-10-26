#!/usr/bin/env python3
"""Mutation tests for Layer-03 workflow-map structural validation."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check-layer-03-workflow-maps.py'
SPEC = importlib.util.spec_from_file_location('workflow_map_validator', SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class WorkflowMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        routes = self.root / validator.ROUTES
        routes.mkdir(parents=True)
        for route, spec in validator.ROUTE_SPECS.items():
            prefix = spec['prefix']
            nodes = [f'{prefix}{i:02d}["{i:02d} {title}"]'
                     for i, title in enumerate(spec['steps'], 1)]
            for lang in ('en', 'zh'):
                branch_nodes = []
                for name in sorted(spec['branches']):
                    label = (validator.AUDIT_NODE_LABELS.get(lang, {}).get(name)
                             or validator.PLAN_NODE_LABELS.get(lang, {}).get(name)
                             or ' '.join(validator.RULE_CONTEXT_NODE_REQUIREMENTS[lang].get(name, ()))
                             or ' '.join(validator.ENHANCED_NODE_LABEL_REQUIREMENTS[lang].get(name, ()))
                             or name)
                    branch_nodes.append(f'{name}["{label}"]')
                diagram = 'flowchart TD\n    ' + '\n    '.join(nodes + branch_nodes) + '\n'
                audit_labels = validator.AUDIT_EDGE_LABELS[lang]
                enhanced_labels = {
                    (src, f"{prefix}03" if dst == 'MODE_CHECKPOINT' else
                     f"{prefix}05" if dst == 'ROUTE_NEXT' else
                     f"{prefix}05" if dst == 'ROUTE_CONTEXT' and route == 'single-agent' else
                     f"{prefix}06" if dst == 'ROUTE_CONTEXT' else
                     f"{prefix}07" if dst == 'ROUTE_SLICE' and route == 'single-agent' else
                     f"{prefix}08" if dst == 'ROUTE_SLICE' else dst): label
                    for (src, dst), label in validator.ENHANCED_EDGE_LABELS[lang].items()
                }
                rule_context_labels = {
                    (src, 'ACT_PLAN_SCAN' if dst == 'RULE_NEXT' else dst): label
                    for (src, dst), label in validator.RULE_CONTEXT_EDGE_LABELS[lang].items()
                }
                advisory_labels = {
                    (src, f'{prefix}02' if dst == 'ROUTE_ENTRY' else
                     f'{prefix}{5 if route == "single-agent" else 6:02d}' if dst == 'ROUTE_CONTEXT' else dst): label
                    for (src, dst), label in validator.ADVISORY_EDGE_LABELS[lang].items()
                }
                lines = []
                for src, dst in sorted(spec['edges']):
                    target = dst
                    label = (audit_labels.get((src, dst)) or enhanced_labels.get((src, target))
                             or rule_context_labels.get((src, target))
                             or advisory_labels.get((src, target)))
                    if (src, dst) in {('D_PLAN', 'D_RECOVERY_GATE'),
                                      ('D_PLAN_SAVED', 'D_RECOVERY_GATE'),
                                      ('D_RECON', 'D_RECOVERY_GATE')}:
                        label = 'no / N/A' if lang == 'en' else '无计划／不适用'
                    if src == 'D_CONTROL' and dst == (f'{prefix}10' if route == 'single-agent' else f'{prefix}12'):
                        label = validator.CONTROL_COMPLETION_LABEL[lang]
                    if src == 'D_AUDIT_CONFIG' and target == 'ACT_AUDIT_CONFIRM':
                        label = audit_labels[('D_AUDIT_CONFIG', 'AUDIT_NEXT')]
                    edge = f'{src} -- {label} --> {target}' if label else f'{src} --> {target}'
                    lines.append(f'    {edge}\n')
                diagram += ''.join(lines)
                suffix = '_zh_cn' if lang == 'zh' else ''
                file = routes / f'coding-{route}{suffix}.md'
                header = validator.MAP_TITLE[lang]
                checklist = validator.CHECKLIST_TITLE[lang]
                lines = ''.join(
                    f'{i}. **{name}.** ' + (
                        ('Always list active plans/ and read each match; check freshness and current instructions. '
                         'Record Not applicable when none match; block dependent work if unavailable.')
                        if name == 'Context' and lang == 'en' else
                        ('始终列出活动计划并逐一读取匹配项；核对新鲜度和当前指令。'
                         '没有匹配项时记录 Not applicable；不可用时阻塞依赖工作。')
                        if name == 'Context' else
                        ' '.join(validator.SESSION_BOUNDARY_CHECKLIST_REQUIREMENTS[lang])
                        if name == 'Session' else 'Content and link.') + '\n'
                    for i, name in enumerate(spec['steps'], 1))
                skip_edges = ((('D_PLAN_MATCH', 'D_RECON'), ('D_RECON', 'S06'), ('D_PLAN', 'S07'), ('D_RULE_ACCESS', 'ACT_RULE_DIRECT'), ('D_DOC', 'S13'), ('D_GIT', 'S14'),
                               ('D_ARCHIVE', 'DONE'))
                              if route == 'single-agent' else
                              (('D_BOOT', 'M06'), ('D_PLAN', 'D_RECON'), ('D_RECON', 'M08'), ('D_MEMO', 'M10'),
                               ('D_RULE_ACCESS', 'ACT_RULE_DIRECT'),
                               ('D_DOC', 'M15'), ('D_GIT', 'M16'), ('D_PLAN_MATCH', 'M07'),
                               ('D_ARCHIVE', 'DONE')))
                localized = diagram
                for source, target in skip_edges:
                    old = f'    {source} --> {target}\n'
                    new = f'    {source} -- {"no / N/A" if lang == "en" else "不适用"} --> {target}\n'
                    localized = localized.replace(old, new)
                for decision in ('D_PLAN_SAVED', 'D_ARCHIVED', 'ACT_PLAN_SCAN', 'ACT_PLAN_READ'):
                    failure_edge = f'    {decision} --> BLOCK\n'
                    failure_label = f'    {decision} -- {"no / unavailable" if lang == "en" else "失败／不可用"} --> BLOCK\n'
                    localized = localized.replace(failure_edge, failure_label)
                file.write_text(f'# route\n\n{header}\n\n\x60\x60\x60mermaid\n{localized}\x60\x60\x60\n\n'
                                f'{checklist}\n\n{lines}', encoding='utf-8')
        for lang, filename in (('en', 'AGENTS.md'), ('zh', 'AGENTS_zh_cn.md')):
            (self.root / filename).write_text(validator.RULE_TITLE[lang] + '\n' +
                                              validator.SCRIPT + '\n', encoding='utf-8')
        workflow = self.root / validator.WORKFLOW
        workflow.parent.mkdir(parents=True)
        workflow.write_text('\n'.join(['"**/*.md"', validator.SCRIPT, validator.TEST,
                                      f'python3 {validator.SCRIPT}',
                                      "python3 -m unittest discover -s tests -p 'test_check_layer_03_workflow_maps.py'"]),
                            encoding='utf-8')

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def route(self, mode='single-agent', lang='en') -> Path:
        suffix = '_zh_cn' if lang == 'zh' else ''
        return self.root / validator.ROUTES / f'coding-{mode}{suffix}.md'

    def mutate(self, path: Path, old: str, new: str) -> None:
        original = path.read_text(encoding='utf-8')
        self.assertIn(old, original)
        path.write_text(original.replace(old, new, 1), encoding='utf-8')

    def reject(self, needle: str) -> None:
        errors = validator.check_repository(self.root)
        self.assertTrue(any(needle in e for e in errors), errors)

    def test_fixture_is_valid(self) -> None:
        self.assertEqual(validator.check_repository(self.root), [])

    def test_missing_map(self) -> None:
        self.mutate(self.route(), '\x60\x60\x60mermaid', '\x60\x60\x60text')
        self.reject('exactly one mermaid')

    def test_duplicate_map(self) -> None:
        path = self.route()
        original = path.read_text(encoding='utf-8')
        path.write_text(original.replace('\x60\x60\x60mermaid',
                           '\x60\x60\x60mermaid\nflowchart TD\n\x60\x60\x60\n\n\x60\x60\x60mermaid', 1),
                        encoding='utf-8')
        self.reject('exactly one mermaid')

    def test_deleted_checkpoint(self) -> None:
        self.mutate(self.route(), 'S06["06 Decision"]\n', '')
        self.reject('missing required map node S06')

    def test_wrong_checkpoint_label(self) -> None:
        self.mutate(self.route(), 'S06["06 Decision"]', 'S06["06 Implementation"]')
        self.reject('node S06 must identify Decision')

    def test_missing_or_renumbered_checklist(self) -> None:
        self.mutate(self.route(), '6. **Decision.', '17. **Decision.')
        self.reject('checklist numbering')

    def test_missing_required_edge(self) -> None:
        self.mutate(self.route(), 'S11 --> S10', 'S11 --> S12')
        self.reject('required map edge S11 -> S10')

    def test_missing_skip_label(self) -> None:
        self.mutate(self.route(), 'D_RECON -- no / N/A --> S06', 'D_RECON --> S06')
        # The fixture has no label; the structure requires a visible skip reason.
        self.reject('must label its skip/Not applicable path')

    def test_active_plan_read_branch_is_required(self) -> None:
        self.mutate(self.route(), 'D_PLAN_MATCH --> ACT_PLAN_READ', 'D_PLAN_MATCH --> D_RECON')
        self.reject('required map edge D_PLAN_MATCH -> ACT_PLAN_READ is missing')

    def test_active_plan_scan_failure_must_block(self) -> None:
        self.mutate(self.route(), 'ACT_PLAN_SCAN -- no / unavailable --> BLOCK', 'ACT_PLAN_SCAN --> BLOCK')
        self.reject('unavailable or failed ACT_PLAN_SCAN must route to BLOCK')

    def test_rule_context_cannot_bypass_direct_owner_confirmation(self) -> None:
        path = self.route()
        text = path.read_text(encoding='utf-8').replace(
            'S05 --> D_RULE_ACCESS', 'S05 --> ACT_PLAN_SCAN', 1)
        path.write_text(text, encoding='utf-8')
        self.reject('required map edge S05 -> D_RULE_ACCESS is missing')

    def test_context_must_check_active_plans_in_both_routes_and_languages(self) -> None:
        for route in ('single-agent', 'multi-agent'):
            for lang, phrase in (('en', 'Always list active plans/'), ('zh', '始终列出活动计划')):
                with self.subTest(route=route, lang=lang):
                    path = self.route(route, lang)
                    self.mutate(path, phrase, 'Skip the active-plan check')
                    errors = validator.check_repository(self.root)
                    expected = ('active-plan check requirement list active plan'
                                if lang == 'en' else 'active-plan check requirement 列出')
                    self.assertTrue(any(expected in error for error in errors), errors)

    def test_decision_advice_cannot_bypass_direct_review_or_release_gate(self) -> None:
        self.mutate(self.route(),
                    'ACT_DECISION_ADVICE -- current advice or failure / direct review --> ACT_DECISION_DIRECT',
                    'ACT_DECISION_ADVICE --> D_PLAN')
        self.reject('required map edge ACT_DECISION_ADVICE -> ACT_DECISION_DIRECT is missing')

    def test_verification_advice_cannot_bypass_direct_checks(self) -> None:
        self.mutate(self.route(),
                    'ACT_EPOCH_ADVICE -- coverage hint or failure / direct verification --> ACT_EPOCH_DIRECT',
                    'ACT_EPOCH_ADVICE --> D_VERIFY')
        self.reject('required map edge ACT_EPOCH_ADVICE -> ACT_EPOCH_DIRECT is missing')

    def test_control_keeps_evidence_on_demand_context_loop(self) -> None:
        self.mutate(self.route(),
                    'D_CONTROL -- Evidence-on-Demand (retrievable evidence pause) --> S05',
                    'D_CONTROL --> S05')
        self.reject('advisory edge D_CONTROL -> S05 must label Evidence-on-Demand')

    def test_native_reentry_cannot_bypass_canonical_audit_readback(self) -> None:
        for route, source, target in (
            ('single-agent', 'D_NATIVE_RECON', 'D_AUDIT_CONFIG'),
            ('multi-agent', 'D_NATIVE_RECON', 'D_AUDIT_CONFIG'),
            ('single-agent', 'ACT_RECOVERY_RECHECK', 'D_AUDIT_CONFIG'),
            ('multi-agent', 'ACT_RECOVERY_RECHECK', 'D_AUDIT_CONFIG'),
        ):
            with self.subTest(route=route, source=source):
                path = self.route(route)
                text = path.read_text(encoding='utf-8')
                line = next(line for line in text.splitlines()
                            if line.strip().startswith(source + ' --')
                            and line.rstrip().endswith('-> ' + target))
                path.write_text(text.replace(line + '\n', '', 1), encoding='utf-8')
                self.reject(f'required map edge {source} -> {target} is missing')
                path.write_text(text, encoding='utf-8')

    def test_native_reentry_cannot_jump_past_audit_or_recovery_gate(self) -> None:
        for route, source, target in (
            ('single-agent', 'D_NATIVE_RECON', 'S05'),
            ('single-agent', 'ACT_RECOVERY_RECHECK', 'S05'),
            ('multi-agent', 'D_NATIVE_RECON', 'M05'),
            ('multi-agent', 'ACT_RECOVERY_RECHECK', 'M05'),
            ('single-agent', 'D_NATIVE_RECON', 'S07'),
            ('multi-agent', 'ACT_RECOVERY_RECHECK', 'M08'),
        ):
            with self.subTest(route=route, source=source, target=target):
                path = self.route(route)
                text = path.read_text(encoding='utf-8')
                self.assertIn('\n```\n', text)
                path.write_text(text.replace('\n```\n',
                                             f'\n    {source} --> {target}\n```\n', 1),
                                 encoding='utf-8')
                self.reject('unexpected map edge')

    def test_control_completion_is_limited_to_normal_postimplementation(self) -> None:
        for route, lang in (
            ('single-agent', 'en'), ('single-agent', 'zh'),
            ('multi-agent', 'en'), ('multi-agent', 'zh'),
        ):
            with self.subTest(route=route, lang=lang):
                path = self.route(route, lang)
                self.mutate(path, validator.CONTROL_COMPLETION_LABEL[lang],
                            'done' if lang == 'en' else '已完成')
                errors = validator.check_repository(self.root)
                self.assertTrue(any('must restrict completion to normal post-implementation' in error
                                    for error in errors), errors)

    def test_session_checklist_requires_correct_native_direction_and_state_owners(self) -> None:
        for route, lang in (
            ('single-agent', 'en'), ('single-agent', 'zh'),
            ('multi-agent', 'en'), ('multi-agent', 'zh'),
        ):
            with self.subTest(route=route, lang=lang):
                path = self.route(route, lang)
                requirements = validator.SESSION_BOUNDARY_CHECKLIST_REQUIREMENTS[lang]
                missing_store = 'enhanced-state-store.md' if lang == 'en' else 'enhanced-state-store_zh_cn.md'
                self.mutate(path, missing_store, 'store-owner-omitted.md')
                errors = validator.check_repository(self.root)
                self.assertTrue(any('Session step must include correct Native direction and pre-open state/schema checks'
                                    in error and missing_store in error for error in errors), errors)

    def test_session_checklist_cannot_assign_reverse_transfer_to_native_canonicality(self) -> None:
        for route, lang in (
            ('single-agent', 'en'), ('single-agent', 'zh'),
            ('multi-agent', 'en'), ('multi-agent', 'zh'),
        ):
            with self.subTest(route=route, lang=lang):
                path = self.route(route, lang)
                phrase = validator.SESSION_BOUNDARY_CHECKLIST_REQUIREMENTS[lang][2]
                reversed_direction = 'if Native may still be canonical' if lang == 'en' else '若 Native 可能仍是规范权威'
                self.mutate(path, phrase, reversed_direction)
                errors = validator.check_repository(self.root)
                self.assertTrue(any('Session step must include correct Native direction and pre-open state/schema checks'
                                    in error and phrase in error for error in errors), errors)

    def test_pre_root_contract_cannot_call_advisory(self) -> None:
        self.mutate(self.route(), 'S01 --> ACT_INITIAL_CLASSIFY', 'S01 --> D_DECISION_ADVICE')
        self.reject('required map edge S01 -> ACT_INITIAL_CLASSIFY is missing')

    def test_missing_required_rule_owner_must_block(self) -> None:
        self.mutate(self.route(), 'ACT_RULE_DIRECT -- required owner unavailable --> BLOCK',
                    'ACT_RULE_DIRECT --> BLOCK')
        self.reject('rule-context edge ACT_RULE_DIRECT -> BLOCK must label required owner unavailable')

    def test_active_plan_read_failure_must_block(self) -> None:
        self.mutate(self.route(), 'ACT_PLAN_READ -- no / unavailable --> BLOCK', 'ACT_PLAN_READ --> BLOCK')
        self.reject('unavailable or failed ACT_PLAN_READ must route to BLOCK')

    def test_plan_memory_failure_must_block(self) -> None:
        path = self.route()
        self.mutate(path, 'D_PLAN_SAVED -- no / unavailable --> BLOCK',
                    'D_PLAN_SAVED --> BLOCK')
        self.reject('failed or unavailable D_PLAN_SAVED Memory must route to BLOCK')

    def test_plan_branch_must_name_user_intent_trigger(self) -> None:
        self.mutate(self.route(), 'D_PLAN[\"User goal requests planning, exploration, or producing/updating a plan?\"]',
                    'D_PLAN[\"Plan document produced?\"]')
        self.reject('node D_PLAN must identify User goal requests planning, exploration, or producing/updating a plan?')

    def test_plan_memory_branch_is_required(self) -> None:
        self.mutate(self.route(), 'D_PLAN --> ACT_PLAN', 'D_PLAN --> S07')
        self.reject('required map edge D_PLAN -> ACT_PLAN is missing')

    def test_plan_archive_branch_is_required(self) -> None:
        self.mutate(self.route(), 'S14 --> D_ARCHIVE', 'S14 --> DONE')
        self.reject('required map edge S14 -> D_ARCHIVE is missing')

    def test_multi_agent_plan_archive_skip_label_is_required(self) -> None:
        self.mutate(self.route(mode='multi-agent'),
                    'D_ARCHIVE -- no / N/A --> DONE', 'D_ARCHIVE --> DONE')
        self.reject('conditional D_ARCHIVE -> DONE must label its skip/Not applicable path')

    def test_plan_archive_failure_must_block(self) -> None:
        path = self.route()
        self.mutate(path, 'D_ARCHIVED -- no / unavailable --> BLOCK', 'D_ARCHIVED --> BLOCK')
        self.reject('failed or unavailable D_ARCHIVED Memory must route to BLOCK')

    def test_extra_unapproved_edge(self) -> None:
        path = self.route()
        text = path.read_text(encoding='utf-8').replace('    S14 --> D_ARCHIVE\n',
                            '    S14 --> DONE\n    S04 --> S14\n', 1)
        path.write_text(text, encoding='utf-8')
        self.reject('unexpected map edge')

    def test_language_topology_drift(self) -> None:
        path = self.route(lang='zh')
        text = path.read_text(encoding='utf-8')
        text = text.replace('    S11 --> S10\n', '    S11 --> S10\n    S11 --> S09\n', 1)
        path.write_text(text, encoding='utf-8')
        self.reject('English and Chinese Mermaid node IDs/edges differ')

    def test_single_agent_forbidden_branch(self) -> None:
        self.mutate(self.route(), 'S07["07 Implementation"]', 'S07["07 Child Creation Implementation"]')
        self.reject('inapplicable child branch')

    def test_shortcut_around_verification(self) -> None:
        path = self.route(mode='multi-agent')
        text = path.read_text(encoding='utf-8').replace('    M16 --> D_ARCHIVE\n',
                            '    M16 --> DONE\n    M11 --> DONE\n', 1)
        path.write_text(text, encoding='utf-8')
        self.reject('unauthorized shortcut')

    def test_policy_rule_removed(self) -> None:
        self.mutate(self.root / 'AGENTS_zh_cn.md', validator.RULE_TITLE['zh'], '## unrelated')
        self.reject('missing workflow-map ownership section')

    def test_ci_command_removed(self) -> None:
        workflow = self.root / validator.WORKFLOW
        text = workflow.read_text(encoding='utf-8').replace(f'python3 {validator.SCRIPT}', 'python3 noop.py')
        workflow.write_text(text, encoding='utf-8')
        self.reject('missing CI trigger or command')

    def test_audit_gate_rejects_direct_checkpoint_bypass(self) -> None:
        for mode, lang, prefix in (('single-agent', 'en', 'S'), ('single-agent', 'zh', 'S'),
                                   ('multi-agent', 'en', 'M'), ('multi-agent', 'zh', 'M')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                text = path.read_text(encoding='utf-8')
                text = text.replace(f'    {prefix}04 --> D_ROOT_STORE\n',
                                    f'    {prefix}04 --> D_ROOT_STORE\n    {prefix}04 --> {prefix}05\n', 1)
                path.write_text(text, encoding='utf-8')
                self.reject(f'unexpected map edge {prefix}04 -> {prefix}05')
                self.tearDown()
                self.setUp()

    def test_root_store_gate_rejects_direct_audit_bypass(self) -> None:
        for mode, lang, prefix in (('single-agent', 'en', 'S'), ('single-agent', 'zh', 'S'),
                                   ('multi-agent', 'en', 'M'), ('multi-agent', 'zh', 'M')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                text = path.read_text(encoding='utf-8').replace(
                    f'    {prefix}04 --> D_ROOT_STORE\n',
                    f'    {prefix}04 --> D_ROOT_STORE\n    {prefix}04 --> D_AUDIT_CONFIG\n', 1)
                path.write_text(text, encoding='utf-8')
                self.reject(f'unexpected map edge {prefix}04 -> D_AUDIT_CONFIG')
                self.tearDown()
                self.setUp()

    def test_session_cannot_exit_without_audit_persistence_confirmation(self) -> None:
        for mode, lang, prefix in (('single-agent', 'en', 'S'), ('single-agent', 'zh', 'S'),
                                   ('multi-agent', 'en', 'M'), ('multi-agent', 'zh', 'M')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                text = path.read_text(encoding='utf-8').replace(
                    f'ACT_AUDIT_CONFIRM -- canonical Root audit record confirmed and read back --> {prefix}05',
                    f'ACT_AUDIT_CONFIRM -- canonical Root audit record confirmed and read back --> {prefix}06') if lang == 'en' else path.read_text(encoding='utf-8').replace(
                    f'ACT_AUDIT_CONFIRM -- 规范 Root 审计记录已确认并读回 --> {prefix}05',
                    f'ACT_AUDIT_CONFIRM -- 规范 Root 审计记录已确认并读回 --> {prefix}06')
                path.write_text(text, encoding='utf-8')
                self.reject(f'required map edge ACT_AUDIT_CONFIRM -> {prefix}05 is missing')
                self.tearDown()
                self.setUp()

    def test_native_child_path_does_not_require_enhanced_worker_store(self) -> None:
        for lang, edge in (
            ('en', '    D_WORKER_STORE -- Native / Enhanced not selected / N/A --> D_MEMO\n'),
            ('zh', '    D_WORKER_STORE -- Native／未选择 Enhanced／不适用 --> D_MEMO\n'),
        ):
            with self.subTest(lang=lang):
                path = self.route(mode='multi-agent', lang=lang)
                text = path.read_text(encoding='utf-8')
                self.assertIn(edge, text)
                path.write_text(text.replace(edge, '', 1), encoding='utf-8')
                self.reject('required map edge D_WORKER_STORE -> D_MEMO is missing')
                self.tearDown()
                self.setUp()

    def test_enhanced_gate_rejects_direct_environment_bypass(self) -> None:
        for mode, lang, prefix in (('single-agent', 'en', 'S'), ('single-agent', 'zh', 'S'),
                                   ('multi-agent', 'en', 'M'), ('multi-agent', 'zh', 'M')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                text = path.read_text(encoding='utf-8')
                text = text.replace(f'    {prefix}02 --> D_ENHANCED\n',
                                    f'    {prefix}02 --> D_ENHANCED\n    {prefix}02 --> {prefix}03\n', 1)
                path.write_text(text, encoding='utf-8')
                self.reject(f'unexpected map edge {prefix}02 -> {prefix}03')
                self.tearDown()
                self.setUp()

    def test_enhanced_gate_requires_native_verified_and_block_paths(self) -> None:
        for mode, lang, prefix in (('single-agent', 'en', 'S'), ('single-agent', 'zh', 'S'),
                                   ('multi-agent', 'en', 'M'), ('multi-agent', 'zh', 'M')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                text = path.read_text(encoding='utf-8')
                edge = f'D_ENHANCED_HOST -- '
                lines = text.splitlines(keepends=True)
                removed = False
                for index, line in enumerate(lines):
                    if edge in line and f'--> {prefix}03' in line:
                        del lines[index]
                        removed = True
                        break
                self.assertTrue(removed)
                path.write_text(''.join(lines), encoding='utf-8')
                self.reject(f'required map edge D_ENHANCED_HOST -> {prefix}03 is missing')
                self.tearDown()
                self.setUp()

    def test_audit_gate_rejects_invalid_reply_as_acceptance(self) -> None:
        for mode, lang in (('single-agent', 'en'), ('single-agent', 'zh'),
                           ('multi-agent', 'en'), ('multi-agent', 'zh')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                old = ('D_AUDIT_REPLY -- invalid / ambiguous reply --> ACT_AUDIT_CLARIFY'
                       if lang == 'en' else
                       'D_AUDIT_REPLY -- 无效／歧义答复 --> ACT_AUDIT_CLARIFY')
                new = 'D_AUDIT_REPLY -- invalid / ambiguous reply --> ACT_AUDIT_REPLY' if lang == 'en' else 'D_AUDIT_REPLY -- 无效／歧义答复 --> ACT_AUDIT_REPLY'
                self.mutate(path, old, new)
                self.reject('required map edge D_AUDIT_REPLY -> ACT_AUDIT_CLARIFY is missing')
                self.tearDown()
                self.setUp()

    def test_audit_pending_resume_uses_original_state_and_never_reprompts(self) -> None:
        cases = {
            'en': (
                'D_AUDIT_CONFIG -- pending / no reply observed; resume original deadline --> D_AUDIT_REPLY',
                 'D_AUDIT_CONFIG -- pending / invalid reply already observed --> D_AUDIT_CORRECTION',
                 'D_AUDIT_CONFIG -- pending / invalid reply already observed --> D_AUDIT_REPLY',
                 'D_AUDIT_CONFIG -- unasked / first eligible question only --> ACT_AUDIT_PROMPT'),
            'zh': (
                'D_AUDIT_CONFIG -- pending／尚无答复；恢复原截止时间 --> D_AUDIT_REPLY',
                'D_AUDIT_CONFIG -- pending／已观察到无效答复 --> D_AUDIT_CORRECTION',
                'D_AUDIT_CONFIG -- pending／已观察到无效答复 --> D_AUDIT_REPLY',
                'D_AUDIT_CONFIG -- unasked／仅首次符合条件时询问 --> ACT_AUDIT_PROMPT'),
        }
        for mode, lang in (('single-agent', 'en'), ('single-agent', 'zh'),
                           ('multi-agent', 'en'), ('multi-agent', 'zh')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                resume, invalid_resume, bad_resume, first_ask = cases[lang]
                self.mutate(path, resume, '')
                self.reject('audit edge D_AUDIT_CONFIG -> D_AUDIT_REPLY must label')
                self.tearDown()
                self.setUp()

                path = self.route(mode, lang)
                self.mutate(path, invalid_resume, bad_resume)
                self.reject('audit edge D_AUDIT_CONFIG -> D_AUDIT_CORRECTION must label')
                self.tearDown()
                self.setUp()

                path = self.route(mode, lang)
                self.mutate(path, first_ask, first_ask.replace('unasked', 'pending')
                            if lang == 'en' else first_ask.replace('unasked', 'pending'))
                self.reject('audit edge D_AUDIT_CONFIG -> ACT_AUDIT_PROMPT must label')
                self.tearDown()
                self.setUp()

    def test_audit_clarification_wait_and_unavailable_paths_are_required(self) -> None:
        mutations = (
            ('ACT_AUDIT_CLARIFY -- same prompt / original deadline --> D_AUDIT_CORRECTION',
             '',
             'ACT_AUDIT_CLARIFY -- 沿用原问题／原截止时间 --> D_AUDIT_CORRECTION',
             '', 'ACT_AUDIT_CLARIFY -> D_AUDIT_CORRECTION'),
            ('D_AUDIT_REPLY -- pending / before deadline --> ACT_AUDIT_WAIT',
             '',
             'D_AUDIT_REPLY -- pending／尚未到期 --> ACT_AUDIT_WAIT',
             '', 'D_AUDIT_REPLY -> ACT_AUDIT_WAIT'),
            ('D_AUDIT_REPLY -- prompt or timing unavailable --> BLOCK',
             '',
             'D_AUDIT_REPLY -- 提问或计时不可用 --> BLOCK',
             '', 'D_AUDIT_REPLY -> BLOCK'),
        )
        for mode, lang in (('single-agent', 'en'), ('single-agent', 'zh'),
                           ('multi-agent', 'en'), ('multi-agent', 'zh')):
            for old_en, new_en, old_zh, new_zh, edge in mutations:
                with self.subTest(mode=mode, lang=lang, edge=edge):
                    path = self.route(mode, lang)
                    old, new = (old_en, new_en) if lang == 'en' else (old_zh, new_zh)
                    self.mutate(path, old, new)
                    self.reject(f'required map edge {edge.replace(" -> ", " -> ")} is missing')
                    self.tearDown()
                    self.setUp()

    def test_audit_timeout_requires_no_reply_and_full_sixty_seconds(self) -> None:
        replacements = {
            'en': ('D_AUDIT_REPLY -- no reply / actual elapsed >=60s --> ACT_AUDIT_TIMEOUT',
                   'D_AUDIT_REPLY -- pending / actual elapsed >=60s --> ACT_AUDIT_TIMEOUT'),
            'zh': ('D_AUDIT_REPLY -- 无回复／实际经过>=60秒 --> ACT_AUDIT_TIMEOUT',
                   'D_AUDIT_REPLY -- 等待中／实际经过>=60秒 --> ACT_AUDIT_TIMEOUT'),
        }
        for mode, lang in (('single-agent', 'en'), ('single-agent', 'zh'),
                           ('multi-agent', 'en'), ('multi-agent', 'zh')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                old, new = replacements[lang]
                self.mutate(path, old, new)
                self.reject('audit edge D_AUDIT_REPLY -> ACT_AUDIT_TIMEOUT must label')
                self.tearDown()
                self.setUp()

    def test_audit_correction_cannot_timeout_after_user_has_replied(self) -> None:
        for mode, lang in (('single-agent', 'en'), ('single-agent', 'zh'),
                           ('multi-agent', 'en'), ('multi-agent', 'zh')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                old = ('D_AUDIT_CORRECTION -- valid correction --> ACT_AUDIT_REPLY'
                       if lang == 'en' else
                       'D_AUDIT_CORRECTION -- 有效更正 --> ACT_AUDIT_REPLY')
                new = ('D_AUDIT_CORRECTION -- valid correction --> ACT_AUDIT_TIMEOUT'
                       if lang == 'en' else
                       'D_AUDIT_CORRECTION -- 有效更正 --> ACT_AUDIT_TIMEOUT')
                self.mutate(path, old, new)
                self.reject('unexpected map edge D_AUDIT_CORRECTION -> ACT_AUDIT_TIMEOUT')
                self.tearDown()
                self.setUp()

    def test_audit_timeout_default_is_balanced_milestone_full(self) -> None:
        replacements = {
            'en': ('ACT_AUDIT_TIMEOUT["No reply and actual elapsed time >=60s; default Root balanced/milestone_only; preserve Worker or fill full"]',
                   'ACT_AUDIT_TIMEOUT["No reply and actual elapsed time >=60s; apply economy/off"]'),
            'zh': ('ACT_AUDIT_TIMEOUT["无回复且实际经过>=60秒；Root 默认 balanced/milestone_only；保留 Worker 值，缺失才补 full"]',
                   'ACT_AUDIT_TIMEOUT["无回复且实际经过>=60秒；应用 economy/off"]'),
        }
        for mode, lang in (('single-agent', 'en'), ('single-agent', 'zh'),
                           ('multi-agent', 'en'), ('multi-agent', 'zh')):
            with self.subTest(mode=mode, lang=lang):
                path = self.route(mode, lang)
                old, new = replacements[lang]
                self.mutate(path, old, new)
                self.reject('node ACT_AUDIT_TIMEOUT must identify')
                self.tearDown()
                self.setUp()


if __name__ == '__main__':
    unittest.main()
