# Selecting a distinguishing check before the last edit

Date: 2026-10-15. Preparation only; runtime baseline unchanged.
Source HEAD: `da783052e19d96c39260e703c7a502b34b4b8f1e`.
Provider calls, token-count calls, task executions and private evaluations: **zero**.
No paid execution is authorized. The proposed comparison has not sampled a model.

## Problem and smallest intervention

The [two-run audit](2026-10-15-hypothesis-comparison.md) located SQLFluff's unsupported
premise: after changing L003, undoing the earlier L036 change would preserve the
original CTE behavior while repairing a regression. The existing
[intermediate test](2026-10-07-intermediate-test.md) already rules out an easy remedy:
rerunning the selected test on the third-edit candidate returns PASS. That check
does not test what happens after the contemplated removal.

The proposed change is **one conditional instruction in the next model input**.
It asks for an observation that distinguishes current behavior from the proposed
behavior before consuming the last edit. No new tool, memory record, plan schema,
submission gate, extra edit allowance or automatic test execution is introduced.
This is a candidate intervention, not a proven necessary or sufficient repair.

The frozen B instruction is:

> Before using the last edit to fix a regression, check whether the planned change could undo behavior that already passed. If so, choose a small diagnostic whose observations differ between "the proposed change preserves that behavior" and "the current success depends on the code being changed". A rerun on unchanged code does not test that counterfactual. You may compare one temporary in-process behavior substitution in run_probe; label it hypothetical and leave the repository unchanged.

This is more specific than asking for another test or restating the issue. Its
distinct hypothesis is that making the dependency on the contemplated change
explicit will alter diagnostic selection at this checkpoint. The agent might
still choose an irrelevant test, fail to construct a useful experiment, or ignore
the eventual observation. Those are separate possible failures.

Prior [issue repetition](2026-09-28-pre-edit-issue-focus-results.md),
[prior-decision removal](2026-09-30-prior-decision-results.md), and
[requirement-selection review](2026-10-02-requirement-selection-decision.md) did
not justify another generic requirement, memory or planning prompt. This proposal
tests a narrower distinction: testing the **contemplated changed behavior**, not
more repetition of already available task text or current-candidate PASS.

## Frozen checkpoint and insertion boundary

Source: SQLFluff-1733 thin repetition 1, `run_dev_c6cdf266d5a34ded`, actual input
sequence **367**, before decision 370 and the fourth accepted edit. The current
diff is `sha256:59679012118d519810c25430eb177c6fe0fb5480b986b452b6c2e8bd676d2987`.
One accepted edit, 14 model calls, 57 actions and 704 solver seconds remain in
the recorded state. The required check currently fails. The older selected-test
PASS is historical; the later third-edit PASS was not known to this solver.

A is the exact historical prepared request. B appends only the paragraph above
as one developer message. Original system/task/source/state/native items, opaque
encrypted continuation, tools, budgets, model, reasoning and output allowance
remain identical. Neither arm receives the original next response, its proposed
replacement, final failure, L039 diagnosis, operator patch or private evaluation.
Future recorded events are confined to the operator's grading material.

The preparation's mechanical trigger uses only the delivered public state:

- Exactly one accepted edit remains; `replace_text` and `run_probe` are offered.
- A required check is FAIL on the current diff.
- An earlier selected-test PASS exists on a different diff.

Across the 40 saved inputs from the two audited runs, only SQLFluff input 367
matches. SQLFluff 351 has two edits left, SQLFluff 384 has none, and Pydicom 146
has four with no current regression failure. These are insertion controls, not
evidence that the instruction cannot harm model behavior on other tasks. The
trigger is implemented only in the external request preparation, not the runtime.
This is a historical thin-policy experiment; a positive result would not establish
benefit for the selected current-policy baseline.

## What the existing records can already discriminate

The proposed explanation predicts that the original task assertion stays passing
after removing the L036 addition. A competing explanation predicts that the
current success depends on that addition or another unresolved rule interaction.

| Candidate state | Original task behavior | Registered regressions |
| --- | --- | --- |
| Third edit, before removing the L036 addition | Selected file: 4 PASS | 1 FAIL / 505 PASS |
| Recorded fourth edit, after removing that addition | Added CTE node: FAIL, five spaces instead of eight | 506 PASS |

The final whole selected file was not rerun in the cited diagnostic; its failing
added node is the common task assertion. The intermediate PASS and final node
FAIL are existing public operator receipts, not new experiments or solver feedback.
The recorded difference contradicts the preservation premise while showing why
an unchanged-candidate rerun is insufficient. It does not identify a unique
replacement repair or prove that one remaining edit can implement it.

An operator reference program shows how to express the comparison through the
existing `run_probe` contract: execute the public default `sqlfluff.fix` case,
temporarily substitute the contemplated method body in that process, execute the
same input, report both outputs, then restore the method. It does not write the
repository or earn required-check credit. Only one proposed variation is compared.
The reference is **not supplied to either model arm**; supplying it would test
following an operator-designed experiment rather than selecting one.

The preparation reconstructs the complete L036 source from input 367 and verifies
that the original fourth replacement produces exactly the later recorded source
hash. The other full-patch sections are unchanged. The source transformation and
probe syntax pass static checks; the active reference program is 2,580 characters,
within the existing 8,000-character limit. Hypothetical code uses a synthetic
compile filename, so its line entries cannot masquerade as current-source coverage.
The earlier reference is retained with a separate superseding receipt.

The probe source is not AST-filtered by the existing sandbox; its process permits
ordinary Python calls and temporary in-process state while project files remain
read-only. This supports expressing the experiment without a new tool. **The new
reference probe was not executed.** Imports, registry/method dispatch, timing and
behavior under the actual probe environment remain unvalidated. If a later probe
fails setup, that is not a task counterexample. A harmless control followed by an
unfaithful substitution is likewise not a distinguishing experiment.

## Smallest proposed model experiment: selection only

The minimum next behavioral question is whether the instruction changes the very
next action. Historical decision 370 is not reused as the A response; both arms
must be freshly sampled from the same frozen checkpoint.

| Item | Frozen proposal |
| --- | --- |
| Task | `swebench-lite-dev-sqlfluff-sqlfluff-1733`, dev-train |
| Model | `gpt-5.4-2026-03-05`, xhigh, default service tier |
| Cells | A1, B1, B2, A2: two responses per arm, four total |
| Allowance | At most 60,000 input tokens and 25,000 output tokens per response |
| Calls | At most four counts and four generations; zero SDK retries |
| Tools / evaluation | Returned actions are recorded but not executed; private evaluation NOT_RUN |
| Invocation limit | Proposed USD 3.00, 1,200 seconds, no transfers or automatic continuation |
| Credential path | `C:/Users/geonj/Documents/PatchLoop/.env`; not read during preparation |

Using the repository's pricing configuration dated 2026-09-15, the four maximum
uncached reservations sum to USD 2.10. This is configuration arithmetic, **not a
current-price confirmation**. Before any authorized dispatch, live prices, snapshot
availability, exact manifest, opaque-continuation compatibility and token admission
must be checked. No count or price/model availability call was made here. There is
no new live collector or execution command in this change.

The frozen rubric grades the actual requested action and its public arguments,
not the presence of hypothesis language. A qualifying proposal must:

1. Use an offered tool with a concrete public entry point/input or a justified
   equivalent diagnostic and an identifiable observation.
2. Control a variation that reaches the preservation premise. Merely rerunning
   the unchanged candidate or testing the helper in isolation is insufficient.
3. Make the observations distinguish the competing explanations; fabricated or
   hardcoded outputs, a mismatched setup, and an unfaithful substitution do not count.
4. Keep hypothetical observations separate from current-diff verification and
   preserve the tool/source/budget boundary.

Source/schema/AST review can support a **distinguishing proposal**, not certify
execution. All sampled programs remain execution NOT_RUN in this stage. A useful
source inspection is recorded separately; it is not counted as a failed repair or
as the primary diagnostic-selection outcome. No unique file name, L039 answer or
specific operator probe is required. Merely requesting `run_probe` is not success.
Grade without arm labels before revealing them; content may disclose the treatment,
so this is not guaranteed independent blind review.

## Stop and decision rules

- Count, transport or billing uncertainty stops all remaining cells. Preserve
  partial results; no retry, replacement, resume or extra sample is allowed.
- Only B **2/2 qualifying proposals and strictly more than fresh A** supports
  discussing a separately scoped action-executing comparison. This is a deliberately
  small development diagnostic, not a statistical improvement claim.
- A tie, B 0/2 or B 1/2 preserves the baseline and closes this formulation. Do not
  adjust wording and resample this checkpoint merely because budget remains.
- Even the positive selection result does not justify runtime adoption. A subsequent
  separately approved comparison must show that the model observes the diagnostic,
  changes an unsupported repair, and preserves original task behavior plus regressions
  on its final diff; independent acceptance remains a separate outcome.

One edit remains at this checkpoint. A diagnostic may expose a bad change without
leaving a feasible complete repair. Do not reset edit counts, supply the operator
repair or count abandonment as repair success. The existing L039 operator control
starts from a different candidate and is not evidence that its repair is reachable
from this state in one edit. Any later study of earlier timing or additional edit
capacity would be a separate intervention, not folded into this instruction test.

## Prepared evidence and local validation

Root: `C:/pt/hypdesign01`; append-only journal:
`runs/run_dev_preeditdesign.jsonl`.

- `prepare.py`, `plan.json`, `requests/A.json`, `requests/B.json`, `request-delta.json`:
  immutable proposal and exact request projection, with original artifact/hash binding.
- `projection-controls.json`: one matching state across 40 saved inputs, three
  named negative controls, no model or tool execution.
- `grading.json`: scoring and stop rules frozen before any sampled response.
- `operator-only/discrimination.json`: source/patch equivalence and prior public
  receipt identities, never projected into either request.
- `operator-only/reference_probe_safe_trace.py`, `reference-followup.json`:
  active unexecuted reference and the source-attribution correction receipt.
- `bindings.json`, `closeout.json`: consumed-file integrity and final documentation
  validation/commit receipts. Original requests and historical records remain intact.

The original canonical prepared-request hash is
`sha256:47f3899db60e5fccd568655b7562294ce1dfc54364b386ad7abfc32d26af2f93`.
No production runtime or user-owned AGENTS.md edit is included. Documentation
layout/link and whitespace checks are the relevant local validation. The broad
runtime suite, mock smoke, Docker, probe execution, model sampling and private
evaluation are NOT_RUN. The separately prepared revision comparison is unaffected.
