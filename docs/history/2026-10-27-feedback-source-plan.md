# Public failure feedback with partial or complete current-file source

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan
- Origin Date: 2026-10-27
- Verification Status: DESIGN ONLY; source inspection completed; model experiment NOT_RUN
- Version Label: feedback-source-plan-v1

The user requested a follow-up design and an assessment of whole-file reading.
This document proposes a two-run pilot. It does not authorize execution, implement
a runtime policy, create a sealed executable manifest, or reopen any paid allocation.

## Observed defect and design choice

The [last analysis](2026-10-27-selection-observation-failure-analysis.md) separated
an unsupported source premise in A from B's code/prediction contradiction. Neither
model saw its post-edit public failures because the diagnostic stopped at one edit.

`patchloop/dev/tools.py` searches literal matches and returns two lines on either
side. It limits output to 20 match spans and 24,000 source characters; overlapping
hits are not merged. A's decisive `namespace` search returned five spans totaling
860 characters with `truncated=false`. Its missing prefix construction was caused
by the fixed window, not exhaustion of the search output allowance. This flag
describes output clipping, not completeness of a function's semantics.

The source anchor contract admits an exact replacement whose current bytes are
covered by delivered search/read spans. It does not certify that the model saw the
enclosing function or understood it. In A, reading was also unavailable after that
search because the diagnostic reserved the remaining response/action slots.

The clean-base function is 11 lines/392 characters. The saved candidate's function
is 13 lines/449 characters. Showing the enclosing function would refute the prefix
premise at little cost, but would not by itself establish the actual repair.
The saved A `astroid/modutils.py` is 676 lines, 23,441 UTF-8 bytes and 23,438
characters, with SHA-256
`7728b5200cd0049919dbeeb049a7fafa6f83b2063acd7d5f6044ca8f9313bb46`.
Its full body fits the existing 24,000-character output allowance, although the
400-line request limit requires two reads. Full request token fit remains a
preparation/dispatch check, not a character-count inference.

Recommended product direction: keep search as a locator, make a selected small
file readable in one request, and retain explicit ranges for larger files. A
proposed `read_file(path)` could return the complete file when it fits the existing
character bound; otherwise return a clearly incomplete, consecutive page with its
continuation. Do not silently omit the middle, label a partial file complete, or
automatically emit every matching file. Keep current public-path, file-version,
exact-anchor and idempotency boundaries. Do not add a mandatory whole-file-read
gate or mandatory diagnostic declaration as a response to this case.

Function-based reading is a useful alternative for large files. It is not required
to test this file: two existing range reads can produce the complete source packet.
Production's bounded source retention is a separate concern: delivering a whole
file once does not establish that it remains available across later handoffs.
An optional read tool alone would not fix a state where reads have been removed.
Any later horizon simplification needs its own explicit scope; this pilot keeps
the same horizon in both arms to avoid confounding the source comparison.

## Primary question and hypotheses

Given the same saved failed candidate and the same public failure feedback, does
preloading the complete current changed file help the model produce a correct
next repair compared with providing the current changed hunk alone?

- Leading explanation: acquiring too little surrounding source leaves a wrong
  repair premise unchallenged; broader source may also expose an upstream cause.
- Alternative: source availability is adequate, but the model does not test or
  apply the relevant transformation, as the earlier B suggests.
- Alternative: limited responses/probe usability prevent useful diagnosis even
  with source supplied. Report these constraints rather than calling them a
  negative source-content effect.

The effect being tested combines extra source content, saved acquisition effort,
and wider already-observed edit anchors. It is not a token-length-matched test of
reasoning, nor an isolated test of feedback versus no feedback.

## Controlled pair

Use two fresh workspaces and new model conversations, both starting from saved A:
`C:/pt/selection-observation-live-v2/A/workspaces/base/repo`, patch
`sha256:93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5`.
Verify and reconstruct from the immutable prepared task base plus that saved patch;
never modify the original evidence workspace.

| Item | R0: partial source | R1: complete file |
| --- | --- | --- |
| Public issue, saved candidate and previous authored hypothesis | Identical | Identical |
| Full saved candidate diff | Identical, no removed context lines | Identical |
| Public baseline/candidate failure and controls | Same content-bound receipts | Same receipts |
| Current source packet | Postimage of the changed hunk, lines 265-273 | All current modutils.py, lines 1-676 |
| Further tool access, limits and model | Identical | Identical |

The common saved diff already includes `modpath.append(part)`. Do not remove it
to manufacture the old information gap. This continuation tests broader current
source availability, not the causal effect of that single line's earlier omission.
Do not replay old source as current or restore an invented model reasoning state.

Project public observations mechanically: original call identity and captured
output, child-selection/parsing events, measured changed-line observations with
their launch-thread scope, public control outcomes and registered regression.
Keep earlier model hypotheses explicitly authored/unverified. Include the original
program/fixture definitions needed to interpret results. Both arms receive exactly
the same feedback; omit operator causal explanations, successful operator patches,
relative/absolute-root counterfactuals, old B's trajectory and all acceptance data.

Build source packets using current registered reads; R1 uses 1-400 and 401-676.
Register only actually delivered current source spans as editable observations in
each arm. Account for host packet acquisition separately from the 12 model actions;
do not claim an end-to-end acquisition saving from this assisted experiment.
Removing the source-packet difference must make the two initial request structures
identical. Verify persistent packet presence, source hashes and complete coverage.
The model retains existing 400-line range reads in both arms during this pilot;
the proposed whole-file tool interface is not silently introduced in R1.

## Proposed fixed resources

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333, dev-train.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, same thin request policy.
- Credential path for future execution: `C:/Users/geonj/Documents/PatchLoop/.env`;
  unread during design. Default service tier, zero SDK retries.
- R0/R1 once each in sealed sequential order; no failed-run replacement.
- Per arm: eight normal responses, one protocol correction, 12 model tool actions,
  one diagnostic probe request, one additional accepted edit, 600 model-stage seconds.
- Counted input limit 60,000; ordinary/correction output limits 40,000/25,000.
- Proposed cap $1.20 per arm, $2.40 invocation-wide; no transfer or reuse of old funds.
- Public post-edit checks: 390 seconds; separate isolated acceptance: 390 seconds.

These are ceilings, not a guarantee that all maximum-sized responses are affordable.
Use fresh input counts and the existing reservation policy before every dispatch.
Record any output/opportunity narrowing or cap/time stop. If one arm is constrained,
do not report its result as a clean source-effect comparison. A settled helper
failure consumes the single probe under this fixed pilot; no hidden retry is added.

## Procedure, outcomes and stopping

1. Offline preparation: validate candidate/source/receipt hashes, original-call
   identity, public/private projection, packet equality outside source and source
   coverage. Confirm source/packet preservation across normal and correction turns.
   Test this small preparation/operator change under two minutes with fake provider
   and evaluator boundaries. No benchmark-model call is a local test.
2. After a separate exact executable scope is authorized, start R0/R1 independently.
   Both begin with the saved candidate's public failure already visible. A new
   successful edit closes that model row; stop/no-edit and all failures are retained.
3. Replay the original caller on the new candidate and fresh base, with unchanged
   inputs. Check F0010 resolution, unexpected errors, real child selection/parsing
   and the standalone control; report call-2 cache identity separately.
4. Run the same five public fixtures: empty/import/invalid namespace child,
   direct invalid file and ordinary package. Preserve direct/package behavior.
   Run registered regression on that exact candidate.
5. Run one isolated acceptance per new candidate only when registered regression
   passes, even if an added diagnostic failed. Otherwise record NOT_RUN under the
   existing contract. Do not feed any private result to either model or repair again.

Primary task outcome is isolated acceptance, reported alongside regression, scope
and safety. The full public mechanism criterion requires original F0010 resolved,
real child selection/parsing, expected fixture diagnostics and unchanged controls.
Regression PASS, a new patch, or a retracted hypothesis alone is not repair success.
Also record source/ranges acquired, final public hypothesis and actual code, probe
execution versus setup failure, calls/actions, cost/time and constraint exposure.

Stop all remaining dispatches on count, transport, billing, cleanup or identity
uncertainty; do not retry uncertain actions. Monitor process liveness, stage deadlines
and append-only hash-chained dev-run-v1 journals outside the repository. Preserve
action_id/input_hash and immutable source/candidate artifacts. Never pull/build an
evaluation image automatically. All results remain official=false and claim-ineligible.

## Interpretation and next decision

For these decision rules, a successful repair requires acceptance PASS and the
full public mechanism criterion with regression PASS. Preserve separate outcomes
when they disagree; an acceptance PASS with a new public regression is not a clean
positive result for this design.

- R1 alone succeeds: a promising complete-file delivery signal on this saved state;
  replicate before adopting a general agent-quality claim.
- Both succeed: complete-file preloading was not necessary in this pair; compare
  acquisition effort and cost without claiming feedback caused success.
- Both fail: inspect whether the relevant source was used, whether a meaningful
  probe ran, and whether limits constrained the row. Do not add context or reject
  the model categorically from two samples.
- R0 alone succeeds: investigate distraction/cost or stochastic variation; no
  universal harm claim about full-file reading.

This is an assisted saved-candidate continuation, not a clean-base solve, literal
conversation resume, held-out estimate or full production-loop comparison. Same
feedback plus fresh opportunities differs from the previous run in several ways;
comparison with that historical failure does not identify a feedback effect.
The earlier B candidate is not the other arm because its starting patch differs.
A source-by-feedback 2x2 or second candidate should require a new evidence-based
question, not automatic use of remaining budget.

## Relation to mini-SWE-agent

The [recorded dev20 comparison](2026-10-16-patchloop-mini-dev20-results.md) favors
mini descriptively: 10/5/5 PASS/FAIL/NOT_RUN versus PatchLoop 8/10/2; among 15
jointly graded rows mini alone passed two. Cost caps, tools, edit limits, context,
solver environment and verification differed. Astroid-1333 was unsubmitted in
mini's original run and FAIL in its separate larger-budget fresh completion run.

The frozen mini v2.4.6 source used linear history and model-controlled bash actions.
Its prepared observation template clips outputs at 10,000 characters to the first
and last 5,000; it does not automatically provide complete files. The original
wrapper guarded input plus output at 400,000, while observed maximum counted input
was 77,660. It did not have PatchLoop's 60K segment reset. The later completion run
used its own 250K counted-input cap. Keep these scopes separate.

Sources: `C:/pt/mini20prep05/upstream/src/minisweagent/agents/default.py`,
`C:/pt/mini20prep05/upstream/src/minisweagent/config/benchmarks/swebench.yaml`,
`C:/pt/mini20rerun01/public-trace.json`, the frozen mini runtime and the linked
result reports. The current [official overview](https://mini-swe-agent.com/latest/)
also describes bash and linear history, but does not replace the frozen run evidence.
The practical lesson is to reduce unnecessary inspection friction and preserve
useful source; the comparison does not isolate whole-file delivery as the cause.

## Execution readiness

No collection command or sealed manifest exists for this new design. Existing
`diagnostics/selection_observation.py` and `exception_frame_repair.py` provide
reusable source/receipt and accounting machinery, but need a separate saved-state
packet/profile preparation path. Do not run their old collect command as this plan.
Next implementation should freeze exact commands, hashes, image/dependency identity,
credential path and the proposed cap before requesting execution. Production source
and defaults remain unchanged by this design.
