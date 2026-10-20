# Public probe action replay: checkpoint readiness audit

Date: 2026-10-07. Read-only public evidence audit; official=false.
Runtime under audit: `17b423de69ea79125c76d503d6b858a8b65f0a85`.

## Problem and selection

The two SQLFluff continuations substituted old partial-path results and regression
PASS for current-patch verification. Ordinary action replay removes the need to
have saved or rewritten an earlier public program, but its model-use benefit is
unmeasured. Before funding a comparison, check that the model can identify an
eligible full-path program and still has an opportunity to execute it.

The relevant alternative explanations are unavailable identifiers, unusable probe
programs, and a tool/resource policy that prevents checking. These would make a
comparison of voluntary action replay at that boundary uninformative.

## Observations and decision

Audited completed journals and hash-bound actual prepared inputs in
`C:/pt/sretcl01/1` and `C:/pt/sretcl01/2`; no provider or project program ran.
Both final public inputs offer run_probe and retain usable action IDs. B2's
`call_YcnJuf5oV8ffOwrmGNBweCbB` survives specifically at
`state.working_notes.verification.observations.items[2].action_id` even though
the complete program is no longer among the three recent probes.

The program calls `sqlfluff.api.simple.fix` with ansi and no restricted rule list,
prints the WITH/plain SELECT outputs, and asserts their expected indentation.
It is a completed assertion failure with confirmed cleanup. Current replay
resolution verifies and recovers its original source/question without executing it.
This audit does not newly execute that program on the submitted patch.

B2 pre-edit boundary 493 offers only edit/stop, and post-edit boundaries 507/511
offer check/edit/stop. Boundary 526 follows regression PASS and reopens optional
verification: five model calls, 50 actions, three edits and 162 solver seconds,
plus 330 evaluation seconds. B1 boundary 509 offers four calls and 427 seconds,
but its retained full-path probe supplies printed observations rather than an
assertion of the desired indentation. Select B2/526 for one A/B pair.

The audit weakens identifier loss and complete tool unavailability as explanations
for a future failure to replay at this selected boundary. It does not establish
that five calls/162 seconds suffice to discover and repair the rule interaction.
It also does not show that the model will choose, correctly interpret or act on
the probe result. Keep all those outcomes separate in the comparison.

## Next question and boundaries

The [comparison contract](../../.agent/probe-action-comparison.md) keeps the source
prefix, model, 48k context, resource counters and observations fixed, changing only
ordinary action replay availability. General baseline remains 24k. Proposed paid
scope is two continuations, USD 1.20 each / USD 2.40 total, pending exact approval.
Preparation evidence belongs under `C:/pt/parpairaudit01` and `C:/pt/parpairprep01`.
Provider use, autonomous verification, repair improvement and new evaluation are
NOT_RUN. Previous results and allocations remain closed.
