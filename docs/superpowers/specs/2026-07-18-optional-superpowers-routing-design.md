# Optional Superpowers Routing Design

Date: 2026-07-18
Status: Approved

## Goal

Let the Cursor overlay work whether or not upstream `superpowers:*` skills are installed, while preserving the controller/worker boundary.

## Routing

At the start of a task, the controller checks whether upstream Superpowers skills are available in the current runtime.

- If they are unavailable, the controller uses its native planning, review, verification, and branch-completion capabilities. Missing upstream Superpowers is not a blocker.
- If they are available, the controller asks the user once for the whole task whether to use them. It does not load upstream Superpowers until the user confirms.
- An explicit user choice governs the entire task unless the user changes it.

In both routes, Cursor Agent remains the only implementation and review-fix worker. Implementation still goes through `executing-plans-with-cursor`, `cursor-agent-bridge`, and `reviewing-cursor-changes`.

## Scope

Update only the entry/routing skill, its UI metadata, contract tests, and README guidance. Do not change the bridge runner, execution loop, review gate, model, or git authority boundary.

## Acceptance

- Contract tests cover unavailable, available-but-unconfirmed, confirmed-use, and confirmed-native routes.
- README states that upstream Superpowers is optional.
- Existing bridge, execution, review, and authority-boundary tests remain green.
