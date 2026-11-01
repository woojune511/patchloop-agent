# Original obligation, bounded acquisition and explicit delivery

2026-10-22. Authorized implementation and local validation only; official=false.

Baseline c1019854 retained acquired cases but the fresh Astroid pilot acquired zero
cases and submitted after regression PASS while the original public caller failed.
The unresolved question is whether the protocol can preserve missing evidence and
offer a bounded acquisition opportunity without exhausting repair resources.

Implement a public-task-bound obligation independent of plans and helper cases.
Opt-in `reproduction_acquisition=bounded-v1` reserves at most two original probe
attempts or six investigation actions before the first edit. Release the stage
when a healthy failure on the unchanged base is acquired, the bound is reached,
the probe backend is unavailable, or one more investigation would consume the
protected completion budget. Release never means verification. Existing global
model/action/time/cost caps and recovery identities remain authoritative.

Record argv with fresh invocation observations while preserving v1 replay bytes.
Return `unverified_delivery` when no unchanged-base failure and comparable current
support were established. Preserve independent acceptance as a separate result.
Current comparable refutation still prevents a verified finish. This is a mechanism
test, not proof that a model maps the issue to the correct caller or repairs more tasks.

Local controls use the public CSV smoke task, scripted decisions and bounded local
subprocess probes (10-second timeout); no provider model, credentials or images.
Test missing evidence, helper substitution, normal-only cases, setup errors, valid
failure-to-pass with normal control, changed argv, action caps, protected-budget
release and interrupted-action recovery. Compare acquisition off/on with the same
delivery policy. Save experiment journals/results outside the repository.

Accept only if unresolved states cannot become verified, stage/action bounds hold,
crash recovery does not duplicate execution, and mock smoke reaches isolated
evaluation. Stop on identity/execution uncertainty; diagnose a failed local check
before a labelled rerun. Run focused tests, Ruff and required regression checks.
No LLM effectiveness, Linux CI or general repair-quality claim follows.
