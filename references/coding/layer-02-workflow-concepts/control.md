# Control Boundary Checkpoint

[English](control.md) | [简体中文](control_zh_cn.md)

## Actions

1. Report `Status`, `Findings`, `Changed`, `Verification`, `Issue`, `Need`, and `Unreleased boundary`.
2. Check whether the next action introduces a public interface, schema or migration, compatibility change, security-sensitive behavior, new risk domain, difficult-to-reverse mutation, scope expansion, or external effect.
3. Choose one outcome: Continue within the approved envelope, Amend the Contract and Decision, Stop, or request Evidence-on-Demand.
4. Release the next slice only after the outcome is explicit. In Single-Agent mode, perform this as a logical pause; in Multi-Agent mode, the parent controls the release.

## Pass condition

The next action is either released within the current envelope or is paused with the required amendment, evidence, capability, or authorization named.

## Boundary

This checkpoint controls release and authority. It does not silently approve scope expansion, replace verification, or grant Git or external-effect authorization.
