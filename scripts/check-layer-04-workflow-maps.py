#!/usr/bin/env python3
"""Check Layer-04 Mermaid route maps against checklists, mirrors, AGENTS rules, and CI.

This is a structural check, not a proof of semantic equivalence of translations.
Nodes have stable language-independent IDs; matching IDs and edges ensure that
translations cannot silently change executable route topology.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROUTES = Path('references/coding/layer-04-workflows')
WORKFLOW = Path('.github/workflows/multilingual-docs.yml')
SCRIPT = 'scripts/check-layer-04-workflow-maps.py'
TEST = 'tests/test_check_layer_04_workflow_maps.py'
RULE_TITLE = {'en': '## Layer-04 workflow maps', 'zh': '## Layer-04 工作流路线图'}
MAP_TITLE = {'en': '## Workflow map', 'zh': '## 工作流路线图'}
CHECKLIST_TITLE = {'en': '## Ordered route checklist', 'zh': '## 路线顺序检查清单'}
FENCE_RE = re.compile(r'^\x60{3}([^\n]*)\n(.*?)^\x60{3}\s*$', re.M | re.S)
STEP_RE = re.compile(r'(?m)^(\d+)\.\s+\*\*')
NODE_RE = re.compile(r'^\s*([A-Z][A-Z0-9_]*)\s*[\[\{(]')
ID_RE = re.compile(r'[A-Z][A-Z0-9_]*')

ROUTE_SPECS = {
    'single-agent': {
        'prefix': 'S',
        'steps': ('Contract', 'Environment', 'Mode', 'Session', 'Context', 'Decision',
                  'Implementation', 'Stage Feedback', 'Control', 'Verification',
                  'Repair', 'Documentation', 'Git', 'Acceptance'),
        'branches': {
            'ACT_CONTEXT_DIRECT', 'ACT_CONTEXT_GEN', 'ACT_EXECUTOR_CONFLICT', 'ACT_EXECUTOR_ROOT',
            'ACT_OUTPUT_ADVICE', 'ACT_OUTPUT_DIRECT', 'ACT_OUTPUT_HOLD', 'ACT_OUTPUT_NO',
            'ACT_NATIVE', 'ACT_ROOT_OPEN', 'ACT_NATIVE_TRANSFER', 'ACT_NATIVE_RECON',
            'ACT_RECOVERY_RECHECK', 'ACT_AUDIT_CONFIRM', 'ACT_RULE_CONTEXT', 'ACT_RULE_DIRECT',
            'ACT_INITIAL_CLASSIFY', 'ACT_DECISION_ADVICE', 'ACT_DECISION_DIRECT', 'ACT_CONTROL_ADVICE',
            'ACT_CONTROL_DIRECT', 'ACT_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT', 'ACT_PLAN', 'ACT_PLAN_SCAN',
            'ACT_PLAN_READ', 'ACT_ARCHIVE', 'ACT_RECON',
            'ACT_AUDIT_PROMPT', 'ACT_AUDIT_REPLY', 'ACT_AUDIT_CLARIFY', 'ACT_AUDIT_DEFAULT',
            'ACT_AUDIT_WAIT', 'ACT_AUDIT_TIMEOUT', 'D_ENHANCED', 'D_ENHANCED_HOST', 'D_ROOT_STORE',
            'D_AUTHORITY_TRANSFER', 'D_NATIVE_RECON', 'D_RECOVERY_GATE', 'D_RULE_ACCESS',
            'D_DECISION_ADVICE', 'D_CONTROL_ADVICE', 'D_EPOCH_ADVICE', 'D_PLAN', 'D_PLAN_SAVED',
            'D_PLAN_MATCH', 'D_ARCHIVE', 'D_ARCHIVED', 'D_RECON', 'D_CONTEXT_GEN', 'D_TASK_ASSIGN',
            'D_OUTPUT_EXPLICIT', 'D_OUTPUT_RESULT', 'D_CONTROL', 'D_VERIFY', 'D_DOC', 'D_GIT',
            'D_AUDIT_CONFIG', 'D_AUDIT_REPLY', 'D_AUDIT_CORRECTION', 'BLOCK', 'DONE',
        },
        'edges': {
            ('S01', 'ACT_INITIAL_CLASSIFY'), ('ACT_INITIAL_CLASSIFY', 'S02'), ('ACT_INITIAL_CLASSIFY', 'BLOCK'), ('S02', 'D_ENHANCED'), ('D_ENHANCED', 'S03'),
            ('D_ENHANCED', 'D_ENHANCED_HOST'), ('D_ENHANCED_HOST', 'S03'),
            ('D_ENHANCED_HOST', 'ACT_NATIVE'), ('ACT_NATIVE', 'S03'), ('D_ENHANCED_HOST', 'BLOCK'),
            ('S03', 'S04'), ('S04', 'D_ROOT_STORE'),
            ('D_ROOT_STORE', 'D_NATIVE_RECON'), ('D_ROOT_STORE', 'D_AUTHORITY_TRANSFER'), ('D_ROOT_STORE', 'BLOCK'),
            ('ACT_ROOT_OPEN', 'D_AUDIT_CONFIG'), ('ACT_ROOT_OPEN', 'BLOCK'),
            ('D_AUTHORITY_TRANSFER', 'D_AUDIT_CONFIG'), ('D_AUTHORITY_TRANSFER', 'ACT_NATIVE_TRANSFER'), ('D_AUTHORITY_TRANSFER', 'BLOCK'),
            ('ACT_NATIVE_TRANSFER', 'D_AUDIT_CONFIG'), ('ACT_NATIVE_TRANSFER', 'BLOCK'),
            ('D_NATIVE_RECON', 'ACT_ROOT_OPEN'), ('D_NATIVE_RECON', 'D_AUDIT_CONFIG'), ('D_NATIVE_RECON', 'ACT_NATIVE_RECON'),
            ('ACT_NATIVE_RECON', 'D_AUDIT_CONFIG'), ('ACT_NATIVE_RECON', 'ACT_RECOVERY_RECHECK'), ('ACT_NATIVE_RECON', 'BLOCK'),
            ('ACT_RECOVERY_RECHECK', 'D_AUDIT_CONFIG'),
            ('D_AUDIT_CONFIG', 'ACT_AUDIT_CONFIRM'), ('D_AUDIT_CONFIG', 'ACT_AUDIT_PROMPT'),
            ('D_AUDIT_CONFIG', 'D_AUDIT_REPLY'), ('D_AUDIT_CONFIG', 'D_AUDIT_CORRECTION'),
            ('D_AUDIT_CONFIG', 'BLOCK'), ('D_AUDIT_CONFIG', 'ACT_AUDIT_CLARIFY'),
            ('ACT_AUDIT_PROMPT', 'D_AUDIT_REPLY'), ('D_AUDIT_REPLY', 'ACT_AUDIT_REPLY'),
            ('ACT_AUDIT_REPLY', 'ACT_AUDIT_CONFIRM'), ('D_AUDIT_REPLY', 'ACT_AUDIT_CLARIFY'),
            ('ACT_AUDIT_CLARIFY', 'D_AUDIT_CORRECTION'), ('D_AUDIT_CORRECTION', 'ACT_AUDIT_REPLY'),
            ('D_AUDIT_CORRECTION', 'ACT_AUDIT_CLARIFY'), ('D_AUDIT_CORRECTION', 'ACT_AUDIT_DEFAULT'),
            ('ACT_AUDIT_DEFAULT', 'ACT_AUDIT_CONFIRM'), ('D_AUDIT_REPLY', 'ACT_AUDIT_WAIT'),
            ('ACT_AUDIT_WAIT', 'D_AUDIT_REPLY'), ('D_AUDIT_REPLY', 'ACT_AUDIT_TIMEOUT'),
            ('ACT_AUDIT_TIMEOUT', 'ACT_AUDIT_CONFIRM'), ('ACT_AUDIT_CONFIRM', 'S05'),
            ('ACT_AUDIT_CONFIRM', 'BLOCK'), ('D_AUDIT_REPLY', 'BLOCK'),
            ('S05', 'D_RULE_ACCESS'), ('D_RULE_ACCESS', 'ACT_RULE_CONTEXT'),
            ('D_RULE_ACCESS', 'ACT_RULE_DIRECT'), ('ACT_RULE_CONTEXT', 'ACT_RULE_DIRECT'),
            ('ACT_RULE_DIRECT', 'ACT_PLAN_SCAN'), ('ACT_RULE_DIRECT', 'BLOCK'),
            ('ACT_PLAN_SCAN', 'D_PLAN_MATCH'), ('ACT_PLAN_SCAN', 'BLOCK'),
            ('D_PLAN_MATCH', 'ACT_PLAN_READ'), ('D_PLAN_MATCH', 'D_RECON'),
            ('ACT_PLAN_READ', 'D_RECON'), ('ACT_PLAN_READ', 'BLOCK'),
            ('D_RECON', 'ACT_RECON'), ('ACT_RECON', 'S05'), ('D_RECON', 'D_CONTEXT_GEN'),
            ('D_CONTEXT_GEN', 'ACT_CONTEXT_GEN'), ('D_CONTEXT_GEN', 'ACT_CONTEXT_DIRECT'),
            ('ACT_CONTEXT_GEN', 'S06'), ('ACT_CONTEXT_GEN', 'ACT_CONTEXT_DIRECT'),
            ('ACT_CONTEXT_DIRECT', 'S06'), ('ACT_CONTEXT_DIRECT', 'BLOCK'),
            ('S06', 'D_DECISION_ADVICE'), ('D_DECISION_ADVICE', 'ACT_DECISION_ADVICE'), ('D_DECISION_ADVICE', 'ACT_DECISION_DIRECT'), ('ACT_DECISION_ADVICE', 'ACT_DECISION_DIRECT'), ('ACT_DECISION_DIRECT', 'D_PLAN'), ('ACT_DECISION_DIRECT', 'BLOCK'), ('D_PLAN', 'ACT_PLAN'), ('D_PLAN', 'D_RECOVERY_GATE'),
            ('ACT_PLAN', 'D_PLAN_SAVED'), ('D_PLAN_SAVED', 'D_RECOVERY_GATE'), ('D_PLAN_SAVED', 'BLOCK'),
            ('D_RECOVERY_GATE', 'D_TASK_ASSIGN'), ('D_RECOVERY_GATE', 'D_CONTROL_ADVICE'),
            ('D_TASK_ASSIGN', 'ACT_EXECUTOR_ROOT'), ('D_TASK_ASSIGN', 'ACT_EXECUTOR_CONFLICT'),
            ('ACT_EXECUTOR_CONFLICT', 'BLOCK'), ('ACT_EXECUTOR_ROOT', 'D_OUTPUT_EXPLICIT'),
            ('D_OUTPUT_EXPLICIT', 'S07'), ('D_OUTPUT_EXPLICIT', 'ACT_OUTPUT_ADVICE'),
            ('ACT_OUTPUT_ADVICE', 'D_OUTPUT_RESULT'), ('ACT_OUTPUT_ADVICE', 'ACT_OUTPUT_DIRECT'),
            ('D_OUTPUT_RESULT', 'ACT_OUTPUT_NO'), ('D_OUTPUT_RESULT', 'ACT_OUTPUT_HOLD'),
            ('D_OUTPUT_RESULT', 'ACT_OUTPUT_DIRECT'), ('ACT_OUTPUT_DIRECT', 'ACT_OUTPUT_NO'),
            ('ACT_OUTPUT_DIRECT', 'ACT_OUTPUT_HOLD'), ('ACT_OUTPUT_DIRECT', 'BLOCK'),
            ('ACT_OUTPUT_NO', 'S07'), ('ACT_OUTPUT_HOLD', 'BLOCK'),
            ('S07', 'S08'), ('S08', 'S09'), ('S09', 'D_CONTROL_ADVICE'), ('D_CONTROL_ADVICE', 'ACT_CONTROL_ADVICE'), ('D_CONTROL_ADVICE', 'ACT_CONTROL_DIRECT'), ('ACT_CONTROL_ADVICE', 'ACT_CONTROL_DIRECT'), ('ACT_CONTROL_DIRECT', 'D_CONTROL'), ('ACT_CONTROL_DIRECT', 'BLOCK'),
            ('D_CONTROL', 'S05'), ('D_CONTROL', 'S06'), ('D_CONTROL', 'S10'), ('D_CONTROL', 'BLOCK'),
            ('S10', 'D_EPOCH_ADVICE'), ('D_EPOCH_ADVICE', 'ACT_EPOCH_ADVICE'), ('D_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT'), ('ACT_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT'), ('ACT_EPOCH_DIRECT', 'D_VERIFY'), ('ACT_EPOCH_DIRECT', 'BLOCK'), ('D_VERIFY', 'S11'), ('D_VERIFY', 'S12'), ('D_VERIFY', 'BLOCK'),
            ('S11', 'S10'), ('S12', 'D_DOC'), ('D_DOC', 'S10'), ('D_DOC', 'S06'),
            ('D_DOC', 'S13'), ('S13', 'D_GIT'), ('D_GIT', 'S14'), ('D_GIT', 'BLOCK'),
            ('S14', 'D_ARCHIVE'), ('D_ARCHIVE', 'ACT_ARCHIVE'), ('D_ARCHIVE', 'DONE'),
            ('ACT_ARCHIVE', 'D_ARCHIVED'), ('D_ARCHIVED', 'DONE'), ('D_ARCHIVED', 'BLOCK'),
        },
        'forbidden': re.compile(r'\b(?:Child Creation|Child Dispatch|Worker Memo|Context Bootstrap|'
                                r'Child Lifecycle|Child Role Allocation)\b|子代理创建|子代理派发|'
                                r'子代理生命周期|子代理职责分配|跨 Worker', re.I),
    },
    'multi-agent': {
        'prefix': 'M',
        'steps': ('Contract', 'Environment', 'Mode', 'Session', 'Allocation', 'Context',
                  'Decision', 'Slice', 'Child Creation', 'Dispatch', 'Implementation',
                  'Verification', 'Repair', 'Documentation', 'Git', 'Acceptance'),
        'branches': {
            'ACT_ARCHIVE', 'ACT_AUDIT_CLARIFY', 'ACT_AUDIT_CONFIRM', 'ACT_AUDIT_DEFAULT', 'ACT_AUDIT_PROMPT', 'ACT_AUDIT_REPLY',
            'ACT_AUDIT_TIMEOUT', 'ACT_AUDIT_WAIT', 'ACT_BOOT_PLAN', 'ACT_BUDGET_APPROVAL', 'ACT_CHILD_ADVICE', 'ACT_CHILD_DIRECT',
            'ACT_CHILD_REVIEW', 'ACT_CHILD_WAIT', 'ACT_CONTEXT_DIRECT', 'ACT_CONTEXT_GEN', 'ACT_CONTROL_ADVICE', 'ACT_CONTROL_DIRECT',
            'ACT_DECISION_ADVICE', 'ACT_DECISION_DIRECT', 'ACT_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT', 'ACT_INITIAL_CLASSIFY', 'ACT_MEMO',
            'ACT_NATIVE', 'ACT_NATIVE_RECON', 'ACT_NATIVE_TRANSFER', 'ACT_OUTPUT_ADVICE', 'ACT_OUTPUT_CHILD', 'ACT_OUTPUT_HOLD',
            'ACT_OUTPUT_NO', 'ACT_OUTPUT_WAIT', 'ACT_PLAN', 'ACT_PLAN_READ', 'ACT_PLAN_SCAN', 'ACT_RECON_PLAN',
            'ACT_RECOVERY_RECHECK', 'ACT_ROLE_ADVICE', 'ACT_ROLE_NA', 'ACT_ROLE_RESERVE', 'ACT_ROLE_REVIEW', 'ACT_ROOT_OPEN',
            'ACT_RULE_CONTEXT', 'ACT_RULE_DIRECT', 'ACT_TASK_ASSIGN', 'ACT_WORKER_OPEN', 'BLOCK', 'DONE',
            'D_ARCHIVE', 'D_ARCHIVED', 'D_AUDIT_CONFIG', 'D_AUDIT_CORRECTION', 'D_AUDIT_REPLY', 'D_AUTHORITY_TRANSFER',
            'D_BOOT', 'D_CHILD_POOL', 'D_CONTEXT_GEN', 'D_CONTROL', 'D_CONTROL_ADVICE', 'D_DECISION_ADVICE',
            'D_DOC', 'D_ENHANCED', 'D_ENHANCED_HOST', 'D_EPOCH_ADVICE', 'D_EXECUTOR', 'D_GIT',
            'D_INDEPENDENT_CHILD', 'D_MEMO', 'D_NATIVE_RECON', 'D_NEW_CHILD', 'D_OUTPUT_EXPLICIT', 'D_OUTPUT_RESULT',
            'D_PLAN', 'D_PLAN_MATCH', 'D_PLAN_SAVED', 'D_RECON', 'D_RECOVERY_GATE', 'D_ROLE_CAPACITY',
            'D_ROLE_SELECT', 'D_ROOT_STORE', 'D_RULE_ACCESS', 'D_VERIFY', 'D_WORKER_STORE',
        },
        'edges': {
            ('ACT_ARCHIVE', 'D_ARCHIVED'), ('ACT_AUDIT_CLARIFY', 'D_AUDIT_CORRECTION'), ('ACT_AUDIT_CONFIRM', 'BLOCK'), ('ACT_AUDIT_CONFIRM', 'M05'),
            ('ACT_AUDIT_DEFAULT', 'ACT_AUDIT_CONFIRM'), ('ACT_AUDIT_PROMPT', 'D_AUDIT_REPLY'), ('ACT_AUDIT_REPLY', 'ACT_AUDIT_CONFIRM'), ('ACT_AUDIT_TIMEOUT', 'ACT_AUDIT_CONFIRM'),
            ('ACT_AUDIT_WAIT', 'D_AUDIT_REPLY'), ('ACT_BOOT_PLAN', 'ACT_TASK_ASSIGN'), ('ACT_BUDGET_APPROVAL', 'ACT_ROLE_RESERVE'), ('ACT_BUDGET_APPROVAL', 'BLOCK'),
            ('ACT_CHILD_ADVICE', 'ACT_CHILD_REVIEW'), ('ACT_CHILD_DIRECT', 'D_OUTPUT_EXPLICIT'), ('ACT_CHILD_REVIEW', 'ACT_CHILD_DIRECT'), ('ACT_CHILD_REVIEW', 'BLOCK'),
            ('ACT_CHILD_REVIEW', 'D_OUTPUT_EXPLICIT'), ('ACT_CHILD_WAIT', 'D_CHILD_POOL'), ('ACT_CONTEXT_DIRECT', 'BLOCK'), ('ACT_CONTEXT_DIRECT', 'M07'),
            ('ACT_CONTEXT_GEN', 'ACT_CONTEXT_DIRECT'), ('ACT_CONTEXT_GEN', 'M07'), ('ACT_CONTROL_ADVICE', 'ACT_CONTROL_DIRECT'), ('ACT_CONTROL_DIRECT', 'BLOCK'),
            ('ACT_CONTROL_DIRECT', 'D_CONTROL'), ('ACT_DECISION_ADVICE', 'ACT_DECISION_DIRECT'), ('ACT_DECISION_DIRECT', 'BLOCK'), ('ACT_DECISION_DIRECT', 'D_PLAN'),
            ('ACT_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT'), ('ACT_EPOCH_DIRECT', 'BLOCK'), ('ACT_EPOCH_DIRECT', 'D_VERIFY'), ('ACT_INITIAL_CLASSIFY', 'BLOCK'),
            ('ACT_INITIAL_CLASSIFY', 'M02'), ('ACT_MEMO', 'M10'), ('ACT_NATIVE', 'M03'), ('ACT_NATIVE_RECON', 'ACT_RECOVERY_RECHECK'),
            ('ACT_NATIVE_RECON', 'BLOCK'), ('ACT_NATIVE_RECON', 'D_AUDIT_CONFIG'), ('ACT_NATIVE_TRANSFER', 'BLOCK'), ('ACT_NATIVE_TRANSFER', 'D_AUDIT_CONFIG'),
            ('ACT_OUTPUT_ADVICE', 'D_OUTPUT_RESULT'), ('ACT_OUTPUT_CHILD', 'ACT_ROLE_NA'), ('ACT_OUTPUT_HOLD', 'ACT_OUTPUT_WAIT'), ('ACT_OUTPUT_HOLD', 'D_INDEPENDENT_CHILD'),
            ('ACT_OUTPUT_NO', 'D_NEW_CHILD'), ('ACT_OUTPUT_WAIT', 'ACT_OUTPUT_ADVICE'), ('ACT_PLAN', 'D_PLAN_SAVED'), ('ACT_PLAN_READ', 'BLOCK'),
            ('ACT_PLAN_READ', 'D_CONTEXT_GEN'), ('ACT_PLAN_SCAN', 'BLOCK'), ('ACT_PLAN_SCAN', 'D_PLAN_MATCH'), ('ACT_RECON_PLAN', 'D_BOOT'),
            ('ACT_RECOVERY_RECHECK', 'D_AUDIT_CONFIG'), ('ACT_ROLE_ADVICE', 'ACT_ROLE_REVIEW'), ('ACT_ROLE_NA', 'D_RECOVERY_GATE'), ('ACT_ROLE_RESERVE', 'BLOCK'),
            ('ACT_ROLE_RESERVE', 'D_RECOVERY_GATE'), ('ACT_ROLE_REVIEW', 'BLOCK'), ('ACT_ROLE_REVIEW', 'D_ROLE_CAPACITY'), ('ACT_ROOT_OPEN', 'BLOCK'),
            ('ACT_ROOT_OPEN', 'D_AUDIT_CONFIG'), ('ACT_RULE_CONTEXT', 'ACT_RULE_DIRECT'), ('ACT_RULE_DIRECT', 'ACT_PLAN_SCAN'), ('ACT_RULE_DIRECT', 'BLOCK'),
            ('ACT_TASK_ASSIGN', 'D_EXECUTOR'), ('ACT_WORKER_OPEN', 'BLOCK'), ('ACT_WORKER_OPEN', 'D_MEMO'), ('D_ARCHIVE', 'ACT_ARCHIVE'),
            ('D_ARCHIVE', 'DONE'), ('D_ARCHIVED', 'BLOCK'), ('D_ARCHIVED', 'DONE'), ('D_AUDIT_CONFIG', 'ACT_AUDIT_CLARIFY'),
            ('D_AUDIT_CONFIG', 'ACT_AUDIT_CONFIRM'), ('D_AUDIT_CONFIG', 'ACT_AUDIT_PROMPT'), ('D_AUDIT_CONFIG', 'BLOCK'), ('D_AUDIT_CONFIG', 'D_AUDIT_CORRECTION'),
            ('D_AUDIT_CONFIG', 'D_AUDIT_REPLY'), ('D_AUDIT_CORRECTION', 'ACT_AUDIT_CLARIFY'), ('D_AUDIT_CORRECTION', 'ACT_AUDIT_DEFAULT'), ('D_AUDIT_CORRECTION', 'ACT_AUDIT_REPLY'),
            ('D_AUDIT_REPLY', 'ACT_AUDIT_CLARIFY'), ('D_AUDIT_REPLY', 'ACT_AUDIT_REPLY'), ('D_AUDIT_REPLY', 'ACT_AUDIT_TIMEOUT'), ('D_AUDIT_REPLY', 'ACT_AUDIT_WAIT'),
            ('D_AUDIT_REPLY', 'BLOCK'), ('D_AUTHORITY_TRANSFER', 'ACT_NATIVE_TRANSFER'), ('D_AUTHORITY_TRANSFER', 'BLOCK'), ('D_AUTHORITY_TRANSFER', 'D_AUDIT_CONFIG'),
            ('D_BOOT', 'ACT_BOOT_PLAN'), ('D_BOOT', 'ACT_TASK_ASSIGN'), ('D_CHILD_POOL', 'ACT_CHILD_ADVICE'), ('D_CHILD_POOL', 'ACT_CHILD_DIRECT'),
            ('D_CHILD_POOL', 'BLOCK'), ('D_CHILD_POOL', 'D_OUTPUT_EXPLICIT'), ('D_CONTEXT_GEN', 'ACT_CONTEXT_DIRECT'), ('D_CONTEXT_GEN', 'ACT_CONTEXT_GEN'),
            ('D_CONTROL', 'BLOCK'), ('D_CONTROL', 'M06'), ('D_CONTROL', 'M07'), ('D_CONTROL', 'M12'),
            ('D_CONTROL_ADVICE', 'ACT_CONTROL_ADVICE'), ('D_CONTROL_ADVICE', 'ACT_CONTROL_DIRECT'), ('D_DECISION_ADVICE', 'ACT_DECISION_ADVICE'), ('D_DECISION_ADVICE', 'ACT_DECISION_DIRECT'),
            ('D_DOC', 'M07'), ('D_DOC', 'M12'), ('D_DOC', 'M15'), ('D_ENHANCED', 'D_ENHANCED_HOST'),
            ('D_ENHANCED', 'M03'), ('D_ENHANCED_HOST', 'ACT_NATIVE'), ('D_ENHANCED_HOST', 'BLOCK'), ('D_ENHANCED_HOST', 'M03'),
            ('D_EPOCH_ADVICE', 'ACT_EPOCH_ADVICE'), ('D_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT'), ('D_EXECUTOR', 'BLOCK'), ('D_EXECUTOR', 'D_CHILD_POOL'),
            ('D_EXECUTOR', 'D_OUTPUT_EXPLICIT'), ('D_GIT', 'BLOCK'), ('D_GIT', 'M16'), ('D_INDEPENDENT_CHILD', 'ACT_OUTPUT_WAIT'),
            ('D_INDEPENDENT_CHILD', 'D_ROLE_SELECT'), ('D_MEMO', 'ACT_MEMO'), ('D_MEMO', 'M10'), ('D_NATIVE_RECON', 'ACT_NATIVE_RECON'),
            ('D_NATIVE_RECON', 'ACT_ROOT_OPEN'), ('D_NATIVE_RECON', 'D_AUDIT_CONFIG'), ('D_NEW_CHILD', 'ACT_CHILD_WAIT'), ('D_NEW_CHILD', 'ACT_ROLE_NA'),
            ('D_NEW_CHILD', 'D_ROLE_SELECT'), ('D_OUTPUT_EXPLICIT', 'ACT_OUTPUT_ADVICE'), ('D_OUTPUT_EXPLICIT', 'D_NEW_CHILD'), ('D_OUTPUT_RESULT', 'ACT_OUTPUT_CHILD'),
            ('D_OUTPUT_RESULT', 'ACT_OUTPUT_HOLD'), ('D_OUTPUT_RESULT', 'ACT_OUTPUT_NO'), ('D_OUTPUT_RESULT', 'BLOCK'), ('D_PLAN', 'ACT_PLAN'),
            ('D_PLAN', 'D_RECON'), ('D_PLAN_MATCH', 'ACT_PLAN_READ'), ('D_PLAN_MATCH', 'D_CONTEXT_GEN'), ('D_PLAN_SAVED', 'BLOCK'),
            ('D_PLAN_SAVED', 'D_RECON'), ('D_RECON', 'ACT_RECON_PLAN'), ('D_RECON', 'D_BOOT'), ('D_RECOVERY_GATE', 'D_CONTROL_ADVICE'),
            ('D_RECOVERY_GATE', 'M08'), ('D_ROLE_CAPACITY', 'ACT_BUDGET_APPROVAL'), ('D_ROLE_CAPACITY', 'ACT_ROLE_RESERVE'), ('D_ROLE_CAPACITY', 'BLOCK'),
            ('D_ROLE_SELECT', 'ACT_ROLE_ADVICE'), ('D_ROLE_SELECT', 'ACT_ROLE_REVIEW'), ('D_ROOT_STORE', 'BLOCK'), ('D_ROOT_STORE', 'D_AUTHORITY_TRANSFER'),
            ('D_ROOT_STORE', 'D_NATIVE_RECON'), ('D_RULE_ACCESS', 'ACT_RULE_CONTEXT'), ('D_RULE_ACCESS', 'ACT_RULE_DIRECT'), ('D_VERIFY', 'BLOCK'),
            ('D_VERIFY', 'M13'), ('D_VERIFY', 'M14'), ('D_WORKER_STORE', 'ACT_WORKER_OPEN'), ('D_WORKER_STORE', 'BLOCK'),
            ('D_WORKER_STORE', 'D_MEMO'), ('M01', 'ACT_INITIAL_CLASSIFY'), ('M02', 'D_ENHANCED'), ('M03', 'M04'),
            ('M04', 'D_ROOT_STORE'), ('M05', 'M06'), ('M06', 'D_RULE_ACCESS'), ('M07', 'D_DECISION_ADVICE'),
            ('M08', 'M09'), ('M09', 'BLOCK'), ('M09', 'D_MEMO'), ('M09', 'D_WORKER_STORE'),
            ('M10', 'BLOCK'), ('M10', 'M11'), ('M11', 'BLOCK'), ('M11', 'D_CONTROL_ADVICE'),
            ('M12', 'BLOCK'), ('M12', 'D_EPOCH_ADVICE'), ('M13', 'BLOCK'), ('M13', 'M12'),
            ('M14', 'BLOCK'), ('M14', 'D_DOC'), ('M15', 'BLOCK'), ('M15', 'D_GIT'),
            ('M16', 'D_ARCHIVE'),
        },
    },
}


PLAN_NODE_LABELS = {
    'en': {'D_PLAN': 'User goal requests planning, exploration, or producing/updating a plan?',
           'D_PLAN_SAVED': 'Plan Memory saved and read-verified?',
           'D_ARCHIVE': 'Active plan Memory for this task exists?',
           'D_PLAN_MATCH': 'Relevant active plan exists?', 'D_ARCHIVED': 'Archived plan verified?'},
    'zh': {'D_PLAN': '用户目标是否要求规划、探索或制定／输出／更新计划？',
           'D_PLAN_SAVED': '计划 Memory 是否写入并读回核验？',
           'D_ARCHIVE': '是否存在本任务对应的活动计划 Memory？',
           'D_PLAN_MATCH': '是否存在相关活动计划？', 'D_ARCHIVED': '归档计划是否已核验？'},
}

CONTROL_COMPLETION_LABEL = {
    'en': 'normal post-implementation only; no recovery Slice pending',
    'zh': '仅限正常实现后；不存在待放行的恢复 Slice',
}

SESSION_STATE_REQUIREMENTS = {
    'en': ('Native Reconciliation', 'Native Authority Transfer', 'An outage alone never changes authority',
           'Root-only access', 'read-only identity/status guards', 'compatible schema/history',
           'Never recreate', 'block state-dependent work'),
    'zh': ('Native 对账', 'Native 权威转移', '单纯故障绝不改变权威',
           '仅 Root 访问', '只读身份/状态守卫', '兼容的 schema/history',
           '不得把重建', '阻塞依赖 state 的工作'),
}

ENHANCED_NODE_LABEL_REQUIREMENTS = {
    'en': {
        'D_ENHANCED': ('Optional Enhanced operation needed?',),
        'D_ENHANCED_HOST': ('Trusted identity', 'required operation guards'),
        'ACT_NATIVE': ('Native candidate', 'verify prior Enhanced authority before use'),
        'D_ROOT_STORE': ('Enhanced Root store', 'identity', 'guards', 'schema'),
        'ACT_ROOT_OPEN': ('Open or resume Root store', 'audit as pending'),
        'D_AUTHORITY_TRANSFER': ('previously canonical Enhanced record', 'transfer back to Native'),
        'ACT_NATIVE_TRANSFER': ('Freeze Enhanced writers', 'complete canonical record', 'read back'),
        'ACT_RECOVERY_RECHECK': ('Recheck Contract', 'current Context', 'Decision', 'current canonical audit record', 'without reopening Mode', 'repeating a completed prompt'),
        'D_NATIVE_RECON': ('Native currently canonical', 'Root comparison unresolved'),
        'ACT_NATIVE_RECON': ('full set', 'exact comparison', 'supported differences'),
        'D_RECOVERY_GATE': ('post-floor Control Continue', 'current', 'Control rule', 'relevant Epochs'),
        'ACT_AUDIT_CONFIRM': ('selected canonical Root audit record', 'read it back'),
        'D_WORKER_STORE': ('real child', 'identity bound'),
        'ACT_WORKER_OPEN': ('Worker store', 'schema validation'),
    },
    'zh': {
        'D_ENHANCED': ('是否需要可选 Enhanced 操作？',),
        'D_ENHANCED_HOST': ('可信身份', '操作必需守卫'),
        'ACT_NATIVE': ('Native 候选路径', '使用前核验既有 Enhanced 权威'),
        'D_ROOT_STORE': ('Enhanced Root store', '身份', '守卫', 'Schema'),
        'ACT_ROOT_OPEN': ('打开或恢复 Root store', '保持 pending'),
        'D_AUTHORITY_TRANSFER': ('既有规范 Enhanced 记录', '转回 Native'),
        'ACT_NATIVE_TRANSFER': ('冻结 Enhanced 写入者', '在途操作', '完整规范记录'),
        'ACT_RECOVERY_RECHECK': ('重核 Contract', '当前 Context', 'Decision', '当前规范审计记录', '不重开 Mode', '重复已完成提问'),
        'D_NATIVE_RECON': ('Native 当前', 'Root 对账是否未决'),
        'ACT_NATIVE_RECON': ('完整集合', '精确比较', '受支持差异'),
        'D_RECOVERY_GATE': ('floor 后', 'Control Continue', '当前 Control 规则', '相关 Epoch'),
        'ACT_AUDIT_CONFIRM': ('所选规范 Root 审计记录', '读回'),
        'D_WORKER_STORE': ('真实子代理', 'allocation'),
        'ACT_WORKER_OPEN': ('Worker 自身 store', 'Schema 核验'),
    },
}

ENHANCED_EDGE_LABELS = {
    'en': {
        ('D_ENHANCED', 'MODE_CHECKPOINT'): 'no / Native default / N/A',
        ('D_ENHANCED', 'D_ENHANCED_HOST'): 'yes / Enhanced needed',
        ('D_ENHANCED_HOST', 'MODE_CHECKPOINT'): 'verified',
        ('D_ENHANCED_HOST', 'ACT_NATIVE'): 'Native candidate; verify prior Enhanced authority before use',
        ('D_ENHANCED_HOST', 'BLOCK'): 'required capability missing or unknown',
        ('D_ROOT_STORE', 'D_NATIVE_RECON'): 'Enhanced selected; current identity and schema verified',
        ('D_ROOT_STORE', 'D_AUTHORITY_TRANSFER'): 'Native / Enhanced not selected / check existing authority',
        ('ACT_ROOT_OPEN', 'D_AUDIT_CONFIG'): 'open or resume Root store',
        ('D_AUTHORITY_TRANSFER', 'D_AUDIT_CONFIG'): 'no prior Enhanced authority / N/A',
        ('D_AUTHORITY_TRANSFER', 'ACT_NATIVE_TRANSFER'): 'prior Enhanced authority; transfer authorized',
        ('D_AUTHORITY_TRANSFER', 'BLOCK'): 'history, freeze, or readback unknown / failed',
        ('ACT_NATIVE_TRANSFER', 'D_AUDIT_CONFIG'): 'complete record frozen, copied, and read back',
        ('ACT_NATIVE_TRANSFER', 'BLOCK'): 'incomplete or indeterminate',
        ('D_NATIVE_RECON', 'ACT_ROOT_OPEN'): 'no Native history / N/A',
        ('D_NATIVE_RECON', 'D_AUDIT_CONFIG'): 'prior resolution current; no unresolved comparisons',
        ('D_NATIVE_RECON', 'ACT_NATIVE_RECON'): 'unresolved Native history or comparison',
        ('ACT_NATIVE_RECON', 'D_AUDIT_CONFIG'): 'exact comparison confirmed',
        ('ACT_NATIVE_RECON', 'ACT_RECOVERY_RECHECK'): 'material resolution committed; recheck Contract',
        ('ACT_NATIVE_RECON', 'BLOCK'): 'unsupported difference or incomplete review',
        ('ACT_RECOVERY_RECHECK', 'D_AUDIT_CONFIG'): 'Contract rechecked; confirm current canonical audit record',
        ('D_ROOT_STORE', 'BLOCK'): 'required identity, guard, or schema unavailable',
        ('ACT_ROOT_OPEN', 'BLOCK'): 'open or validation failed',
        ('D_RECOVERY_GATE', 'ROUTE_SLICE'): 'no recovery floor / N/A or post-floor Continue is current for Control rule and relevant Epochs',
        ('D_RECOVERY_GATE', 'D_CONTROL_ADVICE'): 'fresh or current Continue required',
        ('ACT_AUDIT_CONFIRM', 'ROUTE_NEXT'): 'canonical Root audit record confirmed and read back',
        ('ACT_AUDIT_CONFIRM', 'BLOCK'): 'canonical record missing or not confirmed',
        ('D_WORKER_STORE', 'ACT_WORKER_OPEN'): 'Enhanced selected; identity bound; guards valid',
        ('D_WORKER_STORE', 'D_MEMO'): 'Native / Enhanced not selected / N/A',
        ('D_WORKER_STORE', 'BLOCK'): 'required identity, guard, or schema unavailable',
        ('ACT_WORKER_OPEN', 'BLOCK'): 'open or validation failed',
    },
    'zh': {
        ('D_ENHANCED', 'MODE_CHECKPOINT'): '否／Native 默认／不适用',
        ('D_ENHANCED', 'D_ENHANCED_HOST'): '是／需要 Enhanced',
        ('D_ENHANCED_HOST', 'MODE_CHECKPOINT'): '已验证',
        ('D_ENHANCED_HOST', 'ACT_NATIVE'): 'Native 候选路径；使用前核验既有 Enhanced 权威',
        ('D_ENHANCED_HOST', 'BLOCK'): '必需能力缺失或未知',
        ('D_ROOT_STORE', 'D_NATIVE_RECON'): 'Enhanced 已选择；当前身份和 Schema 已核验',
        ('D_ROOT_STORE', 'D_AUTHORITY_TRANSFER'): 'Native／未选择 Enhanced／核验既有规范权威',
        ('ACT_ROOT_OPEN', 'D_AUDIT_CONFIG'): '对账后打开或恢复',
        ('D_AUTHORITY_TRANSFER', 'D_AUDIT_CONFIG'): '从未有 Enhanced 权威／不适用',
        ('D_AUTHORITY_TRANSFER', 'ACT_NATIVE_TRANSFER'): '已有 Enhanced 权威；转移获准且已核验',
        ('D_AUTHORITY_TRANSFER', 'BLOCK'): '历史、冻结或读回未知／失败',
        ('ACT_NATIVE_TRANSFER', 'D_AUDIT_CONFIG'): '完整记录已冻结、写入并读回',
        ('ACT_NATIVE_TRANSFER', 'BLOCK'): '不完整或结果不确定',
        ('D_NATIVE_RECON', 'ACT_ROOT_OPEN'): '无 Native 历史／不适用',
        ('D_NATIVE_RECON', 'D_AUDIT_CONFIG'): '先前裁决仍当前；无未决比较',
        ('D_NATIVE_RECON', 'ACT_NATIVE_RECON'): '存在未决 Native 历史或比较',
        ('ACT_NATIVE_RECON', 'D_AUDIT_CONFIG'): '精确比较已确认',
        ('ACT_NATIVE_RECON', 'ACT_RECOVERY_RECHECK'): '实质差异已裁决并提交；重核 Contract',
        ('ACT_NATIVE_RECON', 'BLOCK'): '差异不受支持或审阅不完整',
        ('ACT_RECOVERY_RECHECK', 'D_AUDIT_CONFIG'): 'Contract 已重核；确认当前规范审计记录',
        ('D_ROOT_STORE', 'BLOCK'): '必需身份、守卫或 Schema 不可用',
        ('ACT_ROOT_OPEN', 'BLOCK'): '打开或核验失败',
        ('D_RECOVERY_GATE', 'ROUTE_SLICE'): '无恢复 floor／不适用，或 floor 后 Continue 对当前 Control 规则和相关 Epoch 仍有效',
        ('D_RECOVERY_GATE', 'D_CONTROL_ADVICE'): '需要新的当前 Continue',
        ('ACT_AUDIT_CONFIRM', 'ROUTE_NEXT'): '规范 Root 审计记录已确认并读回',
        ('ACT_AUDIT_CONFIRM', 'BLOCK'): '规范记录缺失或未确认',
        ('D_WORKER_STORE', 'ACT_WORKER_OPEN'): '已选择 Enhanced；身份已绑定；守卫有效',
        ('D_WORKER_STORE', 'D_MEMO'): 'Native／未选择 Enhanced／不适用',
        ('D_WORKER_STORE', 'BLOCK'): '必需身份、守卫或 Schema 不可用',
        ('ACT_WORKER_OPEN', 'BLOCK'): '打开或核验失败',
    },
}

RULE_CONTEXT_NODE_REQUIREMENTS = {
    'en': {
        'D_RULE_ACCESS': ('bounded current rule lookup',),
        'ACT_RULE_CONTEXT': ('current node', 'mapped owner heading'),
        'ACT_RULE_DIRECT': ('direct owner text', 'required references'),
    },
    'zh': {
        'D_RULE_ACCESS': ('有界', '当前规则读取'),
        'ACT_RULE_CONTEXT': ('当前节点', '映射的 owner 标题'),
        'ACT_RULE_DIRECT': ('直接 owner 正文', '必需引用'),
    },
}

RULE_CONTEXT_EDGE_LABELS = {
    'en': {
        ('D_RULE_ACCESS', 'ACT_RULE_CONTEXT'): 'yes / bounded lookup selected',
        ('D_RULE_ACCESS', 'ACT_RULE_DIRECT'): 'no / direct source / N/A',
        ('ACT_RULE_CONTEXT', 'ACT_RULE_DIRECT'): 'loaded or unavailable / direct fallback',
        ('ACT_RULE_DIRECT', 'RULE_NEXT'): 'current owner and required references confirmed',
        ('ACT_RULE_DIRECT', 'BLOCK'): 'required owner unavailable',
    },
    'zh': {
        ('D_RULE_ACCESS', 'ACT_RULE_CONTEXT'): '是／选择有界读取',
        ('D_RULE_ACCESS', 'ACT_RULE_DIRECT'): '否／直接来源／不适用',
        ('ACT_RULE_CONTEXT', 'ACT_RULE_DIRECT'): '已读取或不可用／直接回退',
        ('ACT_RULE_DIRECT', 'RULE_NEXT'): '已核验当前 owner 与必需引用',
        ('ACT_RULE_DIRECT', 'BLOCK'): '必需 owner 不可用',
    },
}

ADVISORY_EDGE_LABELS = {
    'en': {
        ('ACT_INITIAL_CLASSIFY', 'ROUTE_ENTRY'): 'direct sources confirmed / advice N/A before Root',
        ('ACT_INITIAL_CLASSIFY', 'BLOCK'): 'required source unavailable',
        ('D_DECISION_ADVICE', 'ACT_DECISION_ADVICE'): 'explicitly enabled and relevant',
        ('D_DECISION_ADVICE', 'ACT_DECISION_DIRECT'): 'Native / disabled / unavailable / N/A',
        ('ACT_DECISION_ADVICE', 'ACT_DECISION_DIRECT'): 'current advice or failure / direct review',
        ('ACT_DECISION_DIRECT', 'D_PLAN'): 'owner and facts confirmed',
        ('ACT_DECISION_DIRECT', 'BLOCK'): 'required owner or evidence unavailable',
        ('D_CONTROL_ADVICE', 'ACT_CONTROL_ADVICE'): 'explicitly enabled',
        ('D_CONTROL_ADVICE', 'ACT_CONTROL_DIRECT'): 'Native / disabled / unavailable / N/A',
        ('ACT_CONTROL_ADVICE', 'ACT_CONTROL_DIRECT'): 'current advice or failure / direct review',
        ('ACT_CONTROL_DIRECT', 'D_CONTROL'): 'explicit trusted outcome selected',
        ('ACT_CONTROL_DIRECT', 'BLOCK'): 'required owner or essential evidence unobtainable',
        ('D_CONTROL', 'ROUTE_CONTEXT'): 'Evidence-on-Demand (retrievable evidence pause)',
        ('D_EPOCH_ADVICE', 'ACT_EPOCH_ADVICE'): 'explicitly enabled',
        ('D_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT'): 'Native / disabled / unavailable / N/A',
        ('ACT_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT'): 'coverage hint or failure / direct verification',
        ('ACT_EPOCH_DIRECT', 'D_VERIFY'): 'current evidence confirmed',
        ('ACT_EPOCH_DIRECT', 'BLOCK'): 'required evidence unavailable',
        ('M12', 'D_EPOCH_ADVICE'): 'verifier exchange visible / no child verifier required: N/A',
    },
    'zh': {
        ('ACT_INITIAL_CLASSIFY', 'ROUTE_ENTRY'): '已核验直接来源／Root 前建议不适用',
        ('ACT_INITIAL_CLASSIFY', 'BLOCK'): '必需来源不可用',
        ('D_DECISION_ADVICE', 'ACT_DECISION_ADVICE'): '明确启用且与当前问题相关',
        ('D_DECISION_ADVICE', 'ACT_DECISION_DIRECT'): 'Native／关闭／不可用／不适用',
        ('ACT_DECISION_ADVICE', 'ACT_DECISION_DIRECT'): '建议当前或失败／直接核验',
        ('ACT_DECISION_DIRECT', 'D_PLAN'): '已核验 owner 和事实',
        ('ACT_DECISION_DIRECT', 'BLOCK'): '必需 owner 或证据不可用',
        ('D_CONTROL_ADVICE', 'ACT_CONTROL_ADVICE'): '明确启用',
        ('D_CONTROL_ADVICE', 'ACT_CONTROL_DIRECT'): 'Native／关闭／不可用／不适用',
        ('ACT_CONTROL_ADVICE', 'ACT_CONTROL_DIRECT'): '建议当前或失败／直接核验',
        ('ACT_CONTROL_DIRECT', 'D_CONTROL'): '已选择可信显式结果',
        ('ACT_CONTROL_DIRECT', 'BLOCK'): '必需 owner 或关键证据不可取得',
        ('D_CONTROL', 'ROUTE_CONTEXT'): 'Evidence-on-Demand（可补证据暂停）',
        ('D_EPOCH_ADVICE', 'ACT_EPOCH_ADVICE'): '明确启用',
        ('D_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT'): 'Native／关闭／不可用／不适用',
        ('ACT_EPOCH_ADVICE', 'ACT_EPOCH_DIRECT'): '覆盖提示或失败／直接验证',
        ('ACT_EPOCH_DIRECT', 'D_VERIFY'): '已核验当前证据',
        ('ACT_EPOCH_DIRECT', 'BLOCK'): '必需证据不可用',
        ('M12', 'D_EPOCH_ADVICE'): 'verifier 通信可见／无需子代理 verifier：N/A',
    },
}

MULTI_AGENT_EDGE_LABEL_REQUIREMENTS = {
    'en': {
        ('D_CHILD_POOL', 'D_OUTPUT_EXPLICIT'): (
            'suitable child busy; assess output before waiting',
            'no suitable existing child; a new child may be required',
        ),
        ('D_ROLE_SELECT', 'ACT_ROLE_REVIEW'): (
            'explicit creation/role; skip role advice',
            'context generation failed; direct facts suffice; no downstream advice',
        ),
    },
    'zh': {
        ('D_CHILD_POOL', 'D_OUTPUT_EXPLICIT'): (
            '合适子代理忙碌；先评估输出再等待',
            '没有合适现有子代理；可能需要创建新代理',
        ),
        ('D_ROLE_SELECT', 'ACT_ROLE_REVIEW'): (
            '用户明确要求创建／指定职责；跳过职责建议',
            '上下文生成失败但直接事实足够；不发下游建议',
        ),
    },
}

SINGLE_AGENT_EDGE_LABEL_REQUIREMENTS = {
    'en': {
        ('D_CONTEXT_GEN', 'ACT_CONTEXT_GEN'): ('unresolved downstream decision needs background',),
        ('D_CONTEXT_GEN', 'ACT_CONTEXT_DIRECT'): ('explicit direction settles choices / no downstream advice: N/A',),
        ('ACT_CONTEXT_GEN', 'S06'): ('reviewed context and exact input hash are current',),
        ('ACT_CONTEXT_GEN', 'ACT_CONTEXT_DIRECT'): ('failed / insufficient facts; direct review only',),
        ('ACT_CONTEXT_DIRECT', 'S06'): ('verified facts suffice / explicit instruction honored',),
        ('ACT_CONTEXT_DIRECT', 'BLOCK'): ('essential facts unavailable or conflicting',),
        ('D_TASK_ASSIGN', 'ACT_EXECUTOR_ROOT'): ('explicit Root or no conflicting executor direction; local deterministic route',),
        ('D_TASK_ASSIGN', 'ACT_EXECUTOR_CONFLICT'): ('explicit sub_agent conflicts with locked Single; return for review',),
        ('ACT_EXECUTOR_CONFLICT', 'BLOCK'): ('unresolved conflict; block without silent Root fallback',),
        ('D_OUTPUT_EXPLICIT', 'S07'): ('explicit Root/output direction; skip matching advice',),
        ('D_OUTPUT_EXPLICIT', 'ACT_OUTPUT_ADVICE'): ('route unsettled; assess output independently',),
        ('ACT_OUTPUT_ADVICE', 'ACT_OUTPUT_DIRECT'): ('unavailable or failed; direct owner review only',),
        ('D_OUTPUT_RESULT', 'ACT_OUTPUT_NO'): ('no / verified current facts',),
        ('D_OUTPUT_RESULT', 'ACT_OUTPUT_HOLD'): ('yes / unresolved route; Single-Agent topology boundary',),
        ('D_OUTPUT_RESULT', 'ACT_OUTPUT_DIRECT'): ('insufficient evidence / conflicting facts',),
        ('ACT_OUTPUT_DIRECT', 'ACT_OUTPUT_NO'): ('verified facts establish no',),
        ('ACT_OUTPUT_DIRECT', 'ACT_OUTPUT_HOLD'): ('verified facts establish yes',),
        ('ACT_OUTPUT_DIRECT', 'BLOCK'): ('facts missing, conflicting, or still unresolved',),
        ('ACT_OUTPUT_HOLD', 'BLOCK'): ('hold and report topology boundary; stop before output',),
    },
    'zh': {
        ('D_CONTEXT_GEN', 'ACT_CONTEXT_GEN'): ('未决的下游决策需要背景',),
        ('D_CONTEXT_GEN', 'ACT_CONTEXT_DIRECT'): ('明确指令已定分支／无需下游建议：不适用',),
        ('ACT_CONTEXT_GEN', 'S06'): ('上下文已审阅且精确输入 Hash 仍当前',),
        ('ACT_CONTEXT_GEN', 'ACT_CONTEXT_DIRECT'): ('失败／事实不足；仅直接审阅',),
        ('ACT_CONTEXT_DIRECT', 'S06'): ('已核实事实足够／遵循明确指令',),
        ('ACT_CONTEXT_DIRECT', 'BLOCK'): ('必需事实缺失或冲突',),
        ('D_TASK_ASSIGN', 'ACT_EXECUTOR_ROOT'): ('用户明确指定 Root 或无冲突执行主体指令；本地确定性路由',),
        ('D_TASK_ASSIGN', 'ACT_EXECUTOR_CONFLICT'): ('明确 sub_agent 与已锁定 Single 冲突；交 Root 审阅',),
        ('ACT_EXECUTOR_CONFLICT', 'BLOCK'): ('冲突未解决；阻塞且不得静默回退 Root',),
        ('D_OUTPUT_EXPLICIT', 'S07'): ('Root/输出指令已明确决定路由；跳过对应建议',),
        ('D_OUTPUT_EXPLICIT', 'ACT_OUTPUT_ADVICE'): ('输出路由未定；独立评估输出',),
        ('ACT_OUTPUT_ADVICE', 'ACT_OUTPUT_DIRECT'): ('不可用或失败；仅直接审阅 owner',),
        ('D_OUTPUT_RESULT', 'ACT_OUTPUT_NO'): ('no／当前事实已核实',),
        ('D_OUTPUT_RESULT', 'ACT_OUTPUT_HOLD'): ('yes／路由未定；Single-Agent 拓扑边界',),
        ('D_OUTPUT_RESULT', 'ACT_OUTPUT_DIRECT'): ('证据不足／事实冲突',),
        ('ACT_OUTPUT_DIRECT', 'ACT_OUTPUT_NO'): ('已核实事实支持 no',),
        ('ACT_OUTPUT_DIRECT', 'ACT_OUTPUT_HOLD'): ('已核实事实支持 yes',),
        ('ACT_OUTPUT_DIRECT', 'BLOCK'): ('事实缺失、冲突或仍未决',),
        ('ACT_OUTPUT_HOLD', 'BLOCK'): ('挂起并报告拓扑边界；不得继续输出',),
    },
}

CONTEXT_PLAN_REQUIREMENTS = {
    'en': ('active plan', 'plans/', 'read every match', 'freshness',
           'current instructions take precedence', 'infer authorization from memory',
           'block work depending on it', 'do not substitute filesystem files',
           'ordinary reusable project knowledge', 'approved authoritative project files',
           'read that authoritative owner directly'),
    'zh': ('活动计划', 'plans/', '读取每个匹配项', '新鲜度',
           '当前指令优先', '从记忆推断授权',
           '阻塞依赖工作', '不得用文件替代该计划',
           '普通可复用项目知识', '已批准的权威项目文件', '直接读取权威 owner'),
}

DECISION_CONTEXT_REQUIREMENTS = {
    'en': ('explicit user direction', 'source provenance', 'input hash', 'policy binding',
           'do not send it to downstream advice', 'verified facts are sufficient'),
    'zh': ('用户明确指令', '来源溯源', '输入 Hash', '政策绑定',
           '不得发送给下游建议', '已核实事实足够'),
}
MIGRATED_CHECKPOINT_REQUIREMENTS = {
    'en': {
        'planning-output-selection': ('planning intent', 'stored item', 'Not applicable', 'Archive is owned only by Acceptance'),
        'bootstrap-selection': ('current task', 'role occupancy', 'skip conditions', 'Bootstrap/Refresh', 'does not reserve'),
        'executor-selection': ('current facts', 'explicit direction', 'Single-Agent mode', 'two or more eligible idle candidates', 'never defaults to Root', 'does not reserve'),
        'output-route-selection': ('shape, expected output volume', '`yes` means Root should route', 'Single-Agent mode', 'Multi-Agent mode', 'does not authorize creating a child'),
        'role-reservation': ('Child Role Selection', 'Count Gate', 'State Record', 'unique reservation', 'exactly `+1`', 'all four roles', 'Slice release and child creation remain later, separate gates.'),
        'advisory-selection': ('Root authorization', 'freshness', 'policy/input/context hashes', 'Task Assignment', 'advice never authorizes work'),
        'repair-disposition': ('concrete failing evidence', 'affected paths', 'smallest repair candidate', 'new fingerprint', 'changed epochs'),
        'documentation-impact': ('before/after fingerprints', 'Git metadata', 'required checks', 'evidence that remains reusable', 'Verification disposition'),
    },
    'zh': {
        'planning-output-selection': ('规划意图', '存储项', 'Not applicable', '归档只由 Acceptance 负责'),
        'bootstrap-selection': ('当前任务', '角色占用', '跳过条件', 'Bootstrap/Refresh', '不预留'),
        'executor-selection': ('当前事实', '明确指令', 'Single-Agent 模式', '两个或更多合格空闲候选', '绝不默认 Root', '不预留'),
        'output-route-selection': ('请求形式、预期输出量', '`yes` 表示大型输出应避免由 Root 直接物化', 'Single-Agent 模式', 'Multi-Agent 模式', '不授权创建子代理'),
        'role-reservation': ('Child Role Selection', 'Count Gate', 'State Record', '唯一预留', '恰好 `+1`', '四种角色', 'Slice 放行和子代理创建仍是后续独立门禁。'),
        'advisory-selection': ('Root 授权', '新鲜度', '政策/输入/上下文 Hash', 'Task Assignment', '不授权工作'),
        'repair-disposition': ('具体失败证据', '受影响路径', '最小修复候选', '新指纹', '变更 epoch'),
        'documentation-impact': ('变更前后指纹', 'Git 元数据', '必需检查', '仍可复用的证据', 'Verification 处置结果'),
    },
}
CHECKPOINT_LINK_RE = re.compile(r'\[[^\]]+\]\(([^)]+)\)')

AUDIT_NODE_LABEL_REQUIREMENTS = {
    'en': {
        'D_AUDIT_CONFIG': ('valid explicit', 'completed', 'pending', 'unasked'),
        'ACT_AUDIT_PROMPT': ('fixed audit question', 'only if unasked', 'deadline'),
        'D_AUDIT_REPLY': ('valid reply', 'invalid/ambiguous', 'verified timeout', 'unavailable'),
        'ACT_AUDIT_REPLY': ('valid reply', 'selected root fields'),
        'ACT_AUDIT_CLARIFY': ('only invalid/ambiguous fields', 'pending prompt'),
        'D_AUDIT_CORRECTION': ('valid correction', 'still invalid/ambiguous', 'explicit default'),
        'ACT_AUDIT_DEFAULT': ('explicit root balanced/milestone_only', 'preserve worker value', 'timeout history'),
        'ACT_AUDIT_WAIT': ('before deadline', 'pending state'),
        'ACT_AUDIT_TIMEOUT': ('no reply', 'actual elapsed time >=60s', 'default root balanced/milestone_only', 'preserve worker or fill full'),
    },
    'zh': {
        'D_AUDIT_CONFIG': ('有效显式', '已完成', 'pending', 'unasked'),
        'ACT_AUDIT_PROMPT': ('固定审计问题', '仅在 unasked', '截止时间'),
        'D_AUDIT_REPLY': ('有效答复', '无效/歧义答复', '已验证超时', '不可用'),
        'ACT_AUDIT_REPLY': ('有效答复', '所选 root 字段'),
        'ACT_AUDIT_CLARIFY': ('仅澄清无效/歧义字段', 'pending 提问'),
        'D_AUDIT_CORRECTION': ('有效更正', '仍无效/歧义', '明确选择默认值'),
        'ACT_AUDIT_DEFAULT': ('root 明确选择 balanced/milestone_only', '保留 worker 值', '超时历史'),
        'ACT_AUDIT_WAIT': ('截止前等待', '保留 pending 状态'),
        'ACT_AUDIT_TIMEOUT': ('无回复', '实际经过>=60秒', 'root 默认 balanced/milestone_only', '保留 worker 值，缺失才补 full'),
    },
}

AUDIT_NODE_LABELS = {
    'en': {
        'D_AUDIT_CONFIG': 'Reuse valid explicit/completed settings, resume pending prompt, or ask if unasked?',
        'ACT_AUDIT_PROMPT': 'Ask fixed audit question only if unasked; record actual prompt and deadline',
        'D_AUDIT_REPLY': 'Valid reply, invalid/ambiguous reply, verified timeout, or unavailable?',
        'ACT_AUDIT_REPLY': 'Record valid reply; update only selected Root fields',
        'ACT_AUDIT_CLARIFY': 'Clarify only invalid/ambiguous fields; retain pending prompt',
        'D_AUDIT_CORRECTION': 'Valid correction, still invalid/ambiguous, or explicit default?',
        'ACT_AUDIT_DEFAULT': 'Record explicit Root balanced/milestone_only; preserve Worker value and timeout history',
        'ACT_AUDIT_WAIT': 'Wait before deadline; preserve pending state',
        'ACT_AUDIT_TIMEOUT': 'No reply and actual elapsed time >=60s; default Root balanced/milestone_only; preserve Worker or fill full',
    },
    'zh': {
        'D_AUDIT_CONFIG': '复用有效显式／已完成配置、恢复 pending 提问，还是仅在 unasked 时询问？',
        'ACT_AUDIT_PROMPT': '仅在 unasked 时调用固定审计问题；记录实际提问时间与截止时间',
        'D_AUDIT_REPLY': '有效答复、无效/歧义答复、已验证超时或不可用？',
        'ACT_AUDIT_REPLY': '记录有效答复；仅更新所选 Root 字段',
        'ACT_AUDIT_CLARIFY': '仅澄清无效/歧义字段；保留 pending 提问',
        'D_AUDIT_CORRECTION': '有效更正、仍无效/歧义或明确选择默认值？',
        'ACT_AUDIT_DEFAULT': '记录 Root 明确选择 balanced/milestone_only；保留 Worker 值和超时历史',
        'ACT_AUDIT_WAIT': '截止前等待；保留 pending 状态',
        'ACT_AUDIT_TIMEOUT': '无回复且实际经过>=60秒；Root 默认 balanced/milestone_only；保留 Worker 值，缺失才补 full',
    },
}

AUDIT_EDGE_LABELS = {
    'en': {
        ('D_AUDIT_CONFIG', 'AUDIT_NEXT'): 'yes / migration reuse',
        ('D_AUDIT_CONFIG', 'ACT_AUDIT_PROMPT'): 'unasked / first eligible question only',
        ('D_AUDIT_CONFIG', 'D_AUDIT_REPLY'): 'pending / no reply observed; resume original deadline',
        ('D_AUDIT_CONFIG', 'D_AUDIT_CORRECTION'): 'pending / invalid reply already observed',
        ('D_AUDIT_CONFIG', 'ACT_AUDIT_CLARIFY'): 'invalid config / focused clarification',
        ('D_AUDIT_CONFIG', 'BLOCK'): 'unavailable / unresolved schema conflict',
        ('D_AUDIT_REPLY', 'ACT_AUDIT_REPLY'): 'valid actual reply',
        ('D_AUDIT_REPLY', 'ACT_AUDIT_CLARIFY'): 'invalid / ambiguous reply',
        ('ACT_AUDIT_CLARIFY', 'D_AUDIT_CORRECTION'): 'same prompt / original deadline',
        ('D_AUDIT_CORRECTION', 'ACT_AUDIT_REPLY'): 'valid correction',
        ('D_AUDIT_CORRECTION', 'ACT_AUDIT_CLARIFY'): 'still invalid / ambiguous',
        ('D_AUDIT_CORRECTION', 'ACT_AUDIT_DEFAULT'): 'explicit default choice',
        ('D_AUDIT_REPLY', 'ACT_AUDIT_WAIT'): 'pending / before deadline',
        ('ACT_AUDIT_WAIT', 'D_AUDIT_REPLY'): 'check reply / retain deadline',
        ('D_AUDIT_REPLY', 'ACT_AUDIT_TIMEOUT'): 'no reply / actual elapsed >=60s',
        ('D_AUDIT_REPLY', 'BLOCK'): 'prompt or timing unavailable',
    },
    'zh': {
        ('D_AUDIT_CONFIG', 'AUDIT_NEXT'): '是／迁移后复用',
        ('D_AUDIT_CONFIG', 'ACT_AUDIT_PROMPT'): 'unasked／仅首次符合条件时询问',
        ('D_AUDIT_CONFIG', 'D_AUDIT_REPLY'): 'pending／尚无答复；恢复原截止时间',
        ('D_AUDIT_CONFIG', 'D_AUDIT_CORRECTION'): 'pending／已观察到无效答复',
        ('D_AUDIT_CONFIG', 'ACT_AUDIT_CLARIFY'): '配置无效／定向澄清',
        ('D_AUDIT_CONFIG', 'BLOCK'): '不可用／未解决的 schema 冲突',
        ('D_AUDIT_REPLY', 'ACT_AUDIT_REPLY'): '有效实际答复',
        ('D_AUDIT_REPLY', 'ACT_AUDIT_CLARIFY'): '无效／歧义答复',
        ('ACT_AUDIT_CLARIFY', 'D_AUDIT_CORRECTION'): '沿用原问题／原截止时间',
        ('D_AUDIT_CORRECTION', 'ACT_AUDIT_REPLY'): '有效更正',
        ('D_AUDIT_CORRECTION', 'ACT_AUDIT_CLARIFY'): '仍无效／歧义',
        ('D_AUDIT_CORRECTION', 'ACT_AUDIT_DEFAULT'): '用户明确选择默认值',
        ('D_AUDIT_REPLY', 'ACT_AUDIT_WAIT'): 'pending／尚未到期',
        ('ACT_AUDIT_WAIT', 'D_AUDIT_REPLY'): '检查答复／保留截止时间',
        ('D_AUDIT_REPLY', 'ACT_AUDIT_TIMEOUT'): '无回复／实际经过>=60秒',
        ('D_AUDIT_REPLY', 'BLOCK'): '提问或计时不可用',
    },
}


def section(content: str, header: str) -> tuple[str, int] | None:
    """Locate exactly one top-level section, returning body and heading offset."""
    hits = list(re.finditer(r'(?m)^' + re.escape(header) + r'\s*$', content))
    if len(hits) != 1:
        return None
    match = hits[0]
    following = re.search(r'(?m)^## ', content[match.end():])
    end = match.end() + following.start() if following else len(content)
    return content[match.end():end], match.start()


def parse_map(raw: str, path: Path, errors: list[str]) -> tuple[dict[str, str], set[tuple[str, str]]]:
    lines = raw.splitlines()
    if not lines or not re.match(r'^flowchart\s+(?:TD|TB|LR)\s*$', lines[0].strip()):
        errors.append(f'{path}: Mermaid map must begin with flowchart TD/TB/LR')
    nodes: dict[str, str] = {}
    edges: set[tuple[str, str]] = set()
    for number, line in enumerate(lines, 1):
        match = NODE_RE.match(line)
        if match:
            name = match.group(1)
            if name in nodes:
                errors.append(f'{path}: duplicate Mermaid node {name} on map line {number}')
            nodes[name] = line
        if '-->' in line:
            left, right = line.split('-->', 1)
            src_match = ID_RE.match(left.strip())
            dst_match = ID_RE.match(right.strip())
            if src_match and dst_match:
                edges.add((src_match.group(), dst_match.group()))
            else:
                errors.append(f'{path}: unparsable Mermaid edge on map line {number}')
    for source, target in edges:
        if source not in nodes or target not in nodes:
            errors.append(f'{path}: edge {source} -> {target} refers to undefined node')
    return nodes, edges


def validate_route(root: Path, route: str, lang: str, errors: list[str]) -> tuple[set[str], set[tuple[str, str]]] | None:
    filename = f'coding-{route}{"_zh_cn" if lang == "zh" else ""}.md'
    path = root / ROUTES / filename
    if not path.is_file():
        errors.append(f'missing route file: {path}')
        return None
    content = path.read_text(encoding='utf-8')
    expected_header = MAP_TITLE[lang]
    map_section = section(content, expected_header)
    checklist_section = section(content, CHECKLIST_TITLE[lang])
    if map_section is None:
        errors.append(f'{path}: exactly one {expected_header} section is required')
        return None
    if checklist_section is None:
        errors.append(f'{path}: exactly one {CHECKLIST_TITLE[lang]} section is required')
        return None
    if map_section[1] >= checklist_section[1]:
        errors.append(f'{path}: workflow map must precede the ordered checklist')
    fences = list(FENCE_RE.finditer(content))
    maps = [f for f in fences if f.group(1).strip() == 'mermaid']
    if len(maps) != 1 or not (map_section[1] < maps[0].start() < checklist_section[1]):
        errors.append(f'{path}: exactly one mermaid code block must be inside the workflow map section')
        return None
    nodes, edges = parse_map(maps[0].group(2).strip(), path, errors)
    spec = ROUTE_SPECS[route]
    prefix = spec['prefix']
    steps = spec['steps']
    expected = {f'{prefix}{n:02d}' for n in range(1, len(steps) + 1)} | spec['branches']
    for name in sorted(expected - nodes.keys()):
        errors.append(f'{path}: missing required map node {name}')
    for name in sorted(nodes.keys() - expected):
        errors.append(f'{path}: unexpected map node {name}')
    for number, keyword in enumerate(steps, 1):
        node = f'{prefix}{number:02d}'
        if node in nodes and not re.search(r'\b' + re.escape(keyword) + r'\b', nodes[node], re.I):
            errors.append(f'{path}: node {node} must identify {keyword} checkpoint')
    for name, label in PLAN_NODE_LABELS[lang].items():
        if name in nodes and label not in nodes[name]:
            errors.append(f'{path}: node {name} must identify {label}')
    for name, fragments in ENHANCED_NODE_LABEL_REQUIREMENTS[lang].items():
        for fragment in fragments:
            if name in nodes and fragment.casefold() not in nodes[name].casefold():
                errors.append(f'{path}: node {name} must identify {fragment}')
    for name, fragments in RULE_CONTEXT_NODE_REQUIREMENTS[lang].items():
        for fragment in fragments:
            if name in nodes and fragment.casefold() not in nodes[name].casefold():
                errors.append(f'{path}: node {name} must identify {fragment}')
    audit_nodes = AUDIT_NODE_LABEL_REQUIREMENTS[lang]
    for name, fragments in audit_nodes.items():
        for fragment in fragments:
            if name in nodes and fragment.casefold() not in nodes[name].casefold():
                errors.append(f'{path}: node {name} must identify {fragment}')
    audit_edges = dict(AUDIT_EDGE_LABELS[lang])
    audit_edges[('D_AUDIT_CONFIG', 'ACT_AUDIT_CONFIRM')] = audit_edges.pop(('D_AUDIT_CONFIG', 'AUDIT_NEXT'))
    map_text = maps[0].group(2)
    for (source, target), label in audit_edges.items():
        match = re.search(
            r'(?m)^\s*' + re.escape(source) + r'\s+--\s+(.+?)\s+-->\s+' + re.escape(target) + r'\s*$',
            map_text,
        )
        if not match or label.casefold() not in match.group(1).casefold():
            errors.append(f'{path}: audit edge {source} -> {target} must label {label}')
    enhanced_edges = {
        (source, f'{prefix}03' if target == 'MODE_CHECKPOINT' else
         f'{prefix}05' if target == 'ROUTE_NEXT' else
         f'{prefix}05' if target == 'ROUTE_CONTEXT' and route == 'single-agent' else
         f'{prefix}05' if target == 'ROUTE_CONTEXT' else
         'D_TASK_ASSIGN' if target == 'ROUTE_SLICE' and route == 'single-agent' else
         f'{prefix}08' if target == 'ROUTE_SLICE' else
         f'{prefix}05' if target == 'ROOT_CONTEXT' and route == 'single-agent' else
         f'{prefix}05' if target == 'ROOT_CONTEXT' else target): label
        for (source, target), label in ENHANCED_EDGE_LABELS[lang].items()
    }
    for (source, target), label in enhanced_edges.items():
        if source not in nodes or target not in nodes:
            continue
        match = re.search(
            r'(?m)^\s*' + re.escape(source) + r'\s+--\s+(.+?)\s+-->\s+' + re.escape(target) + r'\s*$',
            map_text,
        )
        if not match or label.casefold() not in match.group(1).casefold():
            errors.append(f'{path}: enhanced edge {source} -> {target} must label {label}')
    rule_context_edges = {
        (source, 'ACT_PLAN_SCAN' if target == 'RULE_NEXT' else target): label
        for (source, target), label in RULE_CONTEXT_EDGE_LABELS[lang].items()
    }
    for (source, target), label in rule_context_edges.items():
        if source not in nodes or target not in nodes:
            continue
        match = re.search(
            r'(?m)^\s*' + re.escape(source) + r'\s+--\s+(.+?)\s+-->\s+' + re.escape(target) + r'\s*$',
            map_text,
        )
        if not match or label.casefold() not in match.group(1).casefold():
            errors.append(f'{path}: rule-context edge {source} -> {target} must label {label}')
    advisory_edges = {
        (source, f'{prefix}02' if target == 'ROUTE_ENTRY' else
         f'{prefix}{5 if route == "single-agent" else 6:02d}' if target == 'ROUTE_CONTEXT' else target): label
        for (source, target), label in ADVISORY_EDGE_LABELS[lang].items()
    }
    for (source, target), label in advisory_edges.items():
        if source not in nodes or target not in nodes:
            continue
        match = re.search(
            r'(?m)^\s*' + re.escape(source) + r'\s+--\s+(.+?)\s+-->\s+' + re.escape(target) + r'\s*$',
            map_text,
        )
        if not match or label.casefold() not in match.group(1).casefold():
            errors.append(f'{path}: advisory edge {source} -> {target} must label {label}')
    if route == 'multi-agent':
        for (source, target), required_labels in MULTI_AGENT_EDGE_LABEL_REQUIREMENTS[lang].items():
            labels = re.findall(
                r'(?m)^\s*' + re.escape(source) + r'\s+--\s+(.+?)\s+-->\s+'
                + re.escape(target) + r'\s*$',
                map_text,
            )
            for required_label in required_labels:
                if not any(required_label.casefold() in label.casefold() for label in labels):
                    errors.append(
                        f'{path}: edge {source} -> {target} must preserve branch label {required_label}'
                    )
    if route == 'single-agent':
        for (source, target), required_labels in SINGLE_AGENT_EDGE_LABEL_REQUIREMENTS[lang].items():
            labels = re.findall(
                r'(?m)^\s*' + re.escape(source) + r'\s+--\s+(.+?)\s+-->\s+'
                + re.escape(target) + r'\s*$',
                map_text,
            )
            for required_label in required_labels:
                if not any(required_label.casefold() in label.casefold() for label in labels):
                    errors.append(
                        f'{path}: edge {source} -> {target} must preserve branch label {required_label}'
                    )
    completion_target = f'{prefix}10' if route == 'single-agent' else f'{prefix}12'
    completion_match = re.search(
        r'(?m)^\s*D_CONTROL\s+--\s+(.+?)\s+-->\s+' + re.escape(completion_target) + r'\s*$',
        map_text,
    )
    if (not completion_match
            or CONTROL_COMPLETION_LABEL[lang].casefold() not in completion_match.group(1).casefold()):
        errors.append(f'{path}: D_CONTROL -> {completion_target} must restrict completion to normal post-implementation with no pending recovery Slice')
    recorded_steps = [int(match.group(1)) for match in STEP_RE.finditer(checklist_section[0])]
    wanted_steps = list(range(1, len(steps) + 1))
    if recorded_steps != wanted_steps:
        errors.append(f'{path}: checklist numbering must be {wanted_steps}, got {recorded_steps}')
    context_step = steps.index('Context') + 1
    context_match = next((match for match in STEP_RE.finditer(checklist_section[0])
                          if int(match.group(1)) == context_step), None)
    session_step = steps.index('Session') + 1
    session_match = next((match for match in STEP_RE.finditer(checklist_section[0])
                          if int(match.group(1)) == session_step), None)

    def consumed_owner(match: re.Match[str] | None, slug: str, step_name: str) -> str | None:
        if not match:
            errors.append(f'{path}: missing {step_name} step for {slug} checkpoint')
            return None
        next_step = STEP_RE.search(checklist_section[0], match.end())
        step_text = checklist_section[0][match.start():next_step.start() if next_step else None]
        suffix = '_zh_cn' if lang == 'zh' else ''
        expected = f'../layer-03-workflow-checkpoints/{slug}{suffix}.md'
        targets = [unquote(target.strip()) for target in CHECKPOINT_LINK_RE.findall(step_text)]
        if expected not in targets:
            errors.append(f'{path}: {step_name} step must link the same-language {slug} checkpoint')
            return None
        owner = root / 'references/coding/layer-03-workflow-checkpoints' / f'{slug}{suffix}.md'
        if not owner.is_file():
            errors.append(f'{path}: consumed checkpoint is missing: {owner}')
            return None
        return owner.read_text(encoding='utf-8').casefold()

    if context_match:
        context_owner = consumed_owner(context_match, 'context-source-selection', 'Context')
        decision_owner = consumed_owner(context_match, 'decision-context-selection', 'Context')
        for owner_text, requirements, owner_slug in (
            (context_owner, CONTEXT_PLAN_REQUIREMENTS[lang], 'context-source-selection'),
            (decision_owner, DECISION_CONTEXT_REQUIREMENTS[lang], 'decision-context-selection'),
        ):
            if owner_text is None:
                continue
            for required in requirements:
                if required.casefold() not in owner_text:
                    errors.append(f'{path}: consumed {owner_slug} checkpoint must include requirement {required}')
    if session_match:
        session_owner = consumed_owner(session_match, 'session-state-resolution', 'Session')
        if session_owner is not None:
            for required in SESSION_STATE_REQUIREMENTS[lang]:
                if required.casefold() not in session_owner:
                    errors.append(f'{path}: consumed session-state-resolution checkpoint must include requirement {required}')
    # Validate migrated checkpoint material only through the route's verified same-language link.
    all_route_steps = {
        'planning-output-selection': 'Decision', 'bootstrap-selection': 'Decision',
        'executor-selection': 'Decision', 'output-route-selection': 'Decision',
        'role-reservation': 'Decision', 'advisory-selection': 'Decision',
        'repair-disposition': 'Repair', 'documentation-impact': 'Documentation',
    }
    consumed_slugs = set(all_route_steps)
    if route == 'single-agent':
        consumed_slugs.discard('bootstrap-selection')
        consumed_slugs.discard('role-reservation')
    route_steps = {slug: step for slug, step in all_route_steps.items() if slug in consumed_slugs}
    for slug in route_steps:
        step_name = route_steps[slug]
        step_index = steps.index(step_name) + 1
        match = next((item for item in STEP_RE.finditer(checklist_section[0])
                      if int(item.group(1)) == step_index), None)
        owner_text = consumed_owner(match, slug, step_name)
        if owner_text is not None:
            for required in MIGRATED_CHECKPOINT_REQUIREMENTS[lang][slug]:
                if required.casefold() not in owner_text:
                    errors.append(f'{path}: consumed {slug} checkpoint must include requirement {required}')
    for edge in sorted(spec['edges'] - edges):
        errors.append(f'{path}: required map edge {edge[0]} -> {edge[1]} is missing')
    for edge in sorted(edges - spec['edges']):
        errors.append(f'{path}: unexpected map edge {edge[0]} -> {edge[1]}; update the approved route contract explicitly')
    skip_edges = (
        (('D_PLAN_MATCH', 'D_RECON'), ('D_RECON', 'D_CONTEXT_GEN'), ('D_PLAN', 'D_RECOVERY_GATE'), ('D_RULE_ACCESS', 'ACT_RULE_DIRECT'), ('D_DOC', 'S13'), ('D_GIT', 'S14'),
         ('D_ARCHIVE', 'DONE'))
        if route == 'single-agent' else
        (('D_BOOT', 'ACT_TASK_ASSIGN'), ('D_PLAN', 'D_RECON'), ('D_RECON', 'D_BOOT'), ('D_MEMO', 'M10'),
         ('D_RULE_ACCESS', 'ACT_RULE_DIRECT'),
         ('D_WORKER_STORE', 'D_MEMO'),
         ('D_DOC', 'M15'), ('D_GIT', 'M16'), ('D_PLAN_MATCH', 'D_CONTEXT_GEN'), ('D_ARCHIVE', 'DONE'))
    )
    skip_words = (r'\b(?:no|N/A|disabled|not applicable)\b'
                  if lang == 'en' else r'不适用|不需要|关闭|无变化')
    for source, target in skip_edges:
        match = re.search(
            r'(?m)^\s*' + source + r'\s+--\s+(.+?)\s+-->\s+' + target,
            maps[0].group(2),
        )
        if not match or not re.search(skip_words, match.group(1), re.I):
            errors.append(f'{path}: conditional {source} -> {target} must label its skip/Not applicable path')
    failure_label = (r'\b(?:no|failed|unavailable)\b'
                     if lang == 'en' else r'失败|不可用')
    for decision in ('D_PLAN_SAVED', 'D_ARCHIVED'):
        blocked_result = re.search(
            rf'(?m)^\s*{decision}\s+--\s+(.+?)\s+-->\s+BLOCK',
            maps[0].group(2),
        )
        if not blocked_result or not re.search(failure_label, blocked_result.group(1), re.I):
            errors.append(f'{path}: failed or unavailable {decision} Memory must route to BLOCK')
    for action in ('ACT_PLAN_SCAN', 'ACT_PLAN_READ'):
        blocked_action = re.search(
            rf'(?m)^\s*{action}\s+--\s+(.+?)\s+-->\s+BLOCK',
            maps[0].group(2),
        )
        if not blocked_action or not re.search(failure_label, blocked_action.group(1), re.I):
            errors.append(f'{path}: unavailable or failed {action} must route to BLOCK')
    # Extra edges are allowed only when they cannot bypass the permission/verification gates.
    forbidden_shortcuts = {
        (f'{prefix}03', f'{prefix}09'),
        (f'{prefix}07', f'{prefix}12' if route == 'multi-agent' else f'{prefix}10'),
        (f'{prefix}11' if route == 'multi-agent' else f'{prefix}09', 'DONE'),
        ('BLOCK', 'DONE'),
    }
    for edge in sorted(forbidden_shortcuts & edges):
        errors.append(f'{path}: unauthorized shortcut {edge[0]} -> {edge[1]}')
    if route == 'single-agent' and (bad := spec['forbidden'].search(maps[0].group(2))):
        errors.append(f'{path}: Single-Agent map contains an inapplicable child branch: {bad.group()}')
    for target in ('BLOCK', 'DONE'):
        if any(source == target for source, _ in edges):
            errors.append(f'{path}: terminal node {target} must have no outgoing edges')
    return set(nodes), edges


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for lang, policy_name in (('en', 'AGENTS.md'), ('zh', 'AGENTS_zh_cn.md')):
        path = root / policy_name
        if not path.is_file():
            errors.append(f'missing policy file: {path}')
            continue
        policy = path.read_text(encoding='utf-8')
        if RULE_TITLE[lang] not in policy:
            errors.append(f'{path}: missing workflow-map ownership section {RULE_TITLE[lang]}')
        if SCRIPT not in policy:
            errors.append(f'{path}: required validator command is not documented')
    for route in ROUTE_SPECS:
        english = validate_route(root, route, 'en', errors)
        chinese = validate_route(root, route, 'zh', errors)
        if english and chinese and english != chinese:
            errors.append(f'{route}: English and Chinese Mermaid node IDs/edges differ')
    path = root / WORKFLOW
    if not path.is_file():
        errors.append(f'missing workflow file: {path}')
    else:
        ci = path.read_text(encoding='utf-8')
        for required in (SCRIPT, TEST, f'python3 {SCRIPT}',
                         f"python3 -m unittest discover -s tests -p 'test_check_layer_04_workflow_maps.py'"):
            if required not in ci:
                errors.append(f'{path}: missing CI trigger or command: {required}')
        if '"**/*.md"' not in ci and "'**/*.md'" not in ci:
            errors.append(f'{path}: Markdown changes must trigger CI')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check_repository(args.root.resolve())
    if errors:
        print('Layer-04 workflow map validation failed:', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1
    print('Layer-04 workflow map validation passed (2 routes x 2 languages; map/checklist/CI aligned).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
