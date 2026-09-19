# Repair Checkpoint

[English](repair.md) | [简体中文](repair_zh_cn.md)

## Actions

1. Name the failing evidence, affected paths, and smallest repair that can address it.
2. Confirm the repair remains inside the approved Contract and Decision. If it changes scope, architecture, security, compatibility, or another material decision, stop and return to Contract and Decision.
3. Apply only the authorized repair and run focused checks for it.
4. Send every state-changing repair back through Verification with a new final-state fingerprint or epoch.

## Pass condition

The narrow repair is complete and its new state is queued for verification, or the repair is paused with the required decision or capability named.

## Boundary

This checkpoint does not authorize broad cleanup, unrelated improvements, documentation, Git effects, or external effects.
