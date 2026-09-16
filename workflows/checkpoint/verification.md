# Verification Checkpoint

[English](verification.md) | [简体中文](verification_zh_cn.md)

## Actions

1. Capture the current final-state fingerprint or epoch and the acceptance conditions.
2. Run the strongest applicable holistic and targeted checks against that exact state.
3. For material changes, use an independent Change Verification Session when the Contract requires it. Same-Session checks must be labeled logical verification, not independent verification.
4. Record passed checks, failed checks, unavailable checks, assumptions, and residual risks.
5. Treat any later change as a new final-state epoch; an earlier result does not verify it.

## Pass condition

Every required verification item has current evidence, or the unresolved item and its blocking effect are explicitly reported.

## Boundary

This checkpoint reports verification status. It does not repair failures, write documentation, perform Git effects, or declare overall acceptance by itself.
