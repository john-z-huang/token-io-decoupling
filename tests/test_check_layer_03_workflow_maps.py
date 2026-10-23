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
                             or validator.PLAN_NODE_LABELS.get(lang, {}).get(name, name))
                    branch_nodes.append(f'{name}["{label}"]')
                diagram = 'flowchart TD\n    ' + '\n    '.join(nodes + branch_nodes) + '\n'
                audit_labels = validator.AUDIT_EDGE_LABELS[lang]
                lines = []
                for src, dst in sorted(spec['edges']):
                    target = f"{spec['prefix']}05" if (src, dst) == ('D_AUDIT_CONFIG', 'AUDIT_NEXT') else dst
                    label = audit_labels.get((src, dst))
                    if src == 'D_AUDIT_CONFIG' and target == f"{spec['prefix']}05":
                        label = audit_labels[('D_AUDIT_CONFIG', 'AUDIT_NEXT')]
                    edge = f'{src} -- {label} --> {target}' if label else f'{src} --> {target}'
                    lines.append(f'    {edge}\n')
                diagram += ''.join(lines)
                suffix = '_zh_cn' if lang == 'zh' else ''
                file = routes / f'coding-{route}{suffix}.md'
                header = validator.MAP_TITLE[lang]
                checklist = validator.CHECKLIST_TITLE[lang]
                lines = ''.join(f'{i}. **{name}.** Content and link.\n'
                                for i, name in enumerate(spec['steps'], 1))
                skip_edges = ((('D_PLAN_MATCH', 'D_RECON'), ('D_RECON', 'S06'), ('D_PLAN', 'S07'), ('D_DOC', 'S13'), ('D_GIT', 'S14'),
                               ('D_ARCHIVE', 'DONE'))
                              if route == 'single-agent' else
                              (('D_BOOT', 'M06'), ('D_PLAN', 'D_RECON'), ('D_RECON', 'M08'), ('D_MEMO', 'M10'),
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
                text = text.replace(f'    {prefix}04 --> D_AUDIT_CONFIG\n',
                                    f'    {prefix}04 --> D_AUDIT_CONFIG\n    {prefix}04 --> {prefix}05\n', 1)
                path.write_text(text, encoding='utf-8')
                self.reject(f'unexpected map edge {prefix}04 -> {prefix}05')
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
