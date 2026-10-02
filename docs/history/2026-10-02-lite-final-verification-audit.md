# SQLFluff final-verification audit

Date: 2026-10-02. Provider-free diagnosis at `44c196f07459f9a20609f10c5fa9f1a2b14a5221`.
Runtime bytes match the closed [three-task execution](2026-10-02-lite-sql3-probe-results.md).
No solver was resumed, no model was called, and no benchmark verdict was changed.

## Question, alternatives and decision

All three failed submitted patches lacked a custom reproduction after their final
edit. This matters because public regression PASS did not establish task correctness.
The question was whether missing final verification came from tool/budget denial,
lost public evidence, an implementation defect in completion/recheck, or the
agent's evidence selection and interpretation. An exact saved-probe replay on the
submitted source distinguishes an omitted useful check from a check that would
still be insufficient. It does not measure what the model would do after seeing it.

The audit finds no contract violation in the inspected submission path. Tools,
budget and historical observations remained available; optional probes and advisory
concerns intentionally do not block submission. More importantly, the existing
1733 probe tests disappearance of a symptom rather than the positive expected
output. Replaying it produces a false boolean for extra space while the actual
indentation remains wrong. In 1625, replaying the saved example pair passes both
examples and would not expose the remaining original-evaluation failure.

Keep runtime, prompts and gates unchanged. Do not add a mandatory replay, another
memory field or a paid advice-removal comparison from this evidence. The next
mechanism to investigate is turning public expected behavior into a discriminating
check: a known-bad candidate should fail that condition, and an unrelated wrong
candidate must not pass merely because the original symptom disappears. This is
an investigation target, not an adopted new gate or an authorized paid experiment.
Public expected-output comparison is sufficient to expose the 1733 defect; it
must not be represented as autonomous model discovery or hidden-derived guidance.

## Actual submission inputs

Read the final recorded request for each task and reconstructed its segmented
public state. Encrypted continuation content was neither interpreted nor projected.
All three final tool schemas offered `run_probe`, `replace_text` and `finish_task`.
The table records remaining resources before the final model call, not final cost.

| Instance suffix | Calls left | Seconds left | USD left | Unresolved concerns |
| --- | ---: | ---: | ---: | --- |
| 1517 | 26 | 1456 | 0.87416220 | none |
| 1625 | 11 | 552 | 0.43945755 | v1 |
| 1733 | 17 | 1257 | 0.71334435 | none |

The 1625 concern remained in the actual input and warned that the bracketed-identifier
exemption must not suppress unrelated alias violations. Its final public decision
nevertheless said there was no remaining public uncertainty that would change the
repair. Historical probes were correctly labelled as historical. In 1733 the saved
baseline reproduction observations were likewise present and historical. This
contradicts a blanket explanation based on tool unavailability or absent context;
it does not reveal the model's internal reason for choosing submission.

Completion guidance recommends `finish_task` once eligible, also explicitly offering
an affordable probe for a concrete remaining uncertainty and warning that eligibility
is not proof of untested behavior. Recommendation influence remains possible, but
this audit does not isolate it. The earlier [advice comparison](2026-09-26-completion-status-comparison.md)
found no acceptance gain on two different seeded tasks; that is neither proof of
no effect here nor a reason to repeat the same prompt experiment automatically.

## Current contract and observed operation

- `DevToolGateway.ready_to_submit`, `state_snapshot` and `_finish_task` in
  `patchloop/dev/tools.py` require a nonempty tracked diff and current-diff public
  check PASS. This matches the implementation guide and existing completion tests.
- `select_repair_recheck` in `patchloop/dev/repair_recheck.py` selects the latest
  failed registered check from the mutation's prior diff. It does not select
  arbitrary model-authored probes or assess their semantic predicates.
- In 1625 the automatic repair recheck did run the failed `base-regression` after
  the final edit and delivered its current-diff PASS. In 1517 and 1733 there was
  no preceding failed registered check that required this automatic recheck.
- Verification concerns in `patchloop/dev/verification_concerns.py` preserve
  advisory uncertainty and evidence currency; they explicitly do not certify
  semantic coverage or add a finish gate. The unresolved 1625 concern was not lost.

These are deliberate current boundaries. Changing them is a design intervention,
not a repair of an observed broken recheck implementation.

## Exact public-program replays

Selection was recorded before execution: use the first successful behavior probe
for each task that had one (1625 completed action sequence 176; 1733 sequence 163).
1517 has no agent-authored probe, so no operator-invented substitute was run.
Both programs were byte-identical to the agent's saved programs, used the same
dependency/profile hashes, and ran on hash-verified final solver workspaces.
Private evaluator workspaces were not used. Workspace diffs were verified unchanged
after execution. Both isolated runs exited zero without timeout or cleanup errors.

**1625:** The saved pair checks the public no-alias and bracketed-alias examples.
Both return no L031 violations on the final patch. This replay alone would not
expose its remaining failure. The residual failure's cause is unresolved here;
no private test content was consulted to invent more cases.

**1733:** The public expected output puts eight spaces before `my_id,`.
The original observation has nine; the submitted patch produces five. Comparing
the full output against the public expected output is false. The saved program's
`full_has_extra_space` only searches for the nine-space form, so it changes from
true to false even though the output is still wrong. The raw output exposes this
error to a careful reader, but its boolean summary does not encode correctness.
Thus replay could provide useful evidence without guaranteeing correct interpretation.

This identifies two distinct weaknesses: final-patch evidence was not obtained,
and the candidate check did not fully express the expected behavior. Neither
"exit zero" nor "old symptom absent" is an adequate semantic success condition.
Do not generalize this to all probes or claim these weaknesses fully explain all
three hidden failures.

## Evidence and validation

External root: `C:/pt/analyses/lite-sql3-final-verification-20261002-v1`.
`diagnose.py`, `summary.json`, `interpretation.json` and the append-only
`runs/run_dev_litesql3finalverification.jsonl` bind original request/action hashes,
submitted diff identities, exact program identities, remaining budgets and replay
outputs. Historical run evidence and submitted patches are unchanged.

Existing completion-choice, repair-recheck and verification-concern tests: 72 PASS
in 105.246 seconds; five documentation checks and `git diff --check` also passed.
No new runtime behavior or tests were introduced. The local
full fast suite and mock smoke were not rerun for this diagnosis/documentation-only
change. Original hidden evaluation and model calls were NOT_RUN during this audit;
the prior batch remains 0/3 at USD 1.67171265. Two public operator replays are
diagnostic evidence, not fresh agent solves or additional benchmark successes.
