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
            nodes += [f'{name}["{name}"]' for name in sorted(spec['branches'])]
            diagram = 'flowchart TD\n    ' + '\n    '.join(nodes) + '\n'
            diagram += ''.join(f'    {src} --> {dst}\n' for src, dst in sorted(spec['edges']))
            for lang in ('en', 'zh'):
                suffix = '_zh_cn' if lang == 'zh' else ''
                file = routes / f'coding-{route}{suffix}.md'
                header = validator.MAP_TITLE[lang]
                checklist = validator.CHECKLIST_TITLE[lang]
                lines = ''.join(f'{i}. **{name}.** Content and link.\n'
                                for i, name in enumerate(spec['steps'], 1))
                skip_edges = ((('D_RECON', 'S06'), ('D_DOC', 'S13'), ('D_GIT', 'S14'))
                              if route == 'single-agent' else
                              (('D_BOOT', 'M06'), ('D_RECON', 'M08'), ('D_MEMO', 'M10'),
                               ('D_DOC', 'M15'), ('D_GIT', 'M16')))
                localized = diagram
                for source, target in skip_edges:
                    old = f'    {source} --> {target}\n'
                    new = f'    {source} -- {"no / N/A" if lang == "en" else "不适用"} --> {target}\n'
                    localized = localized.replace(old, new)
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

    def test_extra_unapproved_edge(self) -> None:
        path = self.route()
        text = path.read_text(encoding='utf-8').replace('    S14 --> DONE\n',
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
        text = path.read_text(encoding='utf-8').replace('    M16 --> DONE\n',
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


if __name__ == '__main__':
    unittest.main()
