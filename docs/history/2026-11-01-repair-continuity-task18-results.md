# Task18 after restoring plan and note delivery

Date: 2026-11-01 KST. Status: CLOSED. official=false, claim_eligible=false.

## Question and decision

The user selected one fresh SQLFluff1733 run to check whether existing run-local
plans and notes retain diagnostic findings and remaining questions, deliver them
to the next decision, and help avoid unnecessary repetition. The
[preceding task18 run](2026-11-01-pre-edit-dev20-results.md) passed independently
but consumed all 40 model calls and reopened answered L036/L003 questions. The
[actual-input audit](2026-11-01-diagnostic-continuity-delivery-audit.md) found a
compact-repair delivery gap; the [implemented correction](2026-11-01-repair-planning-continuity.md)
restored the existing plan, notes and review guidance without new tools or limits.

**Independent acceptance PASS, safety PASS.** The model wrote and received useful
notes/questions, used retained conclusions in subsequent public action bases,
detected that its first patch still failed, and narrowed the repair after a new
discriminating observation. However, one unchanged-base diagnostic was still
repeated. Cost and time increased despite fewer calls. This supports keeping the
delivery correction, not claiming a causal efficiency or general repair gain.

The remaining continuity question is which completed observations the model chooses
to retain and update. Storage did not reject or evict the missing finding. A separate
concrete issue remains: the new regression file was run explicitly but its final
name still does not match normal pytest discovery. No further runtime change or
paid run is part of this record.

## Frozen scope

- Execution HEAD: `21793a4b65dd603e1ac6b1bd9dd7b463f9011fec`.
- Runtime: `sha256:cfa5c287a3eb54ac3da3b2c42e9e153dd50d9f5a403912651076bc5b938acb95`.
- Task: checked-in dev-train current-dev20/18, `sqlfluff__sqlfluff-1733`, once fresh.
- Model: `gpt-5.4-2026-03-05`, xhigh, 25,000 output ceiling.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`; no secret contents saved.
- New invocation cap USD4; 12 edits, 40 calls, 100 actions, 1,800 seconds including
  a 330-second independent-evaluation reserve. One worker, zero SDK retries.
- segmented-v1, result-or-size-v1, brief-v1, probes enabled/none, repair-recheck,
  protected-v1 inspection, per-call-v1 and public-checks-v1.
- Same request as the preceding full20 task18 except fresh state_root. No earlier
  patch, notes, helper, checkpoint, diagnostic hint or private evaluation feedback
  was supplied. No runtime edit, retry, resume or additional evaluation occurred.

The pre-dispatch manifest records the question, baseline, intervention, selection,
criteria and stop conditions. Public import/operation/selected-test canaries passed
before dispatch. Running Docker and local images were used, without Desktop startup
or an image pull/build.
[Official Standard pricing](https://developers.openai.com/api/docs/pricing) was
checked: USD2.50 input, USD0.25 cached input and USD15 output per million tokens,
within the ordinary context tier. Historical allocations remain closed.

## Outcome and descriptive comparison

| Measure | Previous full20 task18 | Fresh task18 |
| --- | --- | --- |
| Independent acceptance / safety | PASS / PASS | PASS / PASS |
| Model calls / input counts | 40 / 40 | 34 / 34 |
| Tool actions / accepted edits | 58 / 2 | 45 / 2 |
| Probes / required checks / selected tests | 10 / 2 / 0 | 13 / 2 / 2 |
| Recorded generation USD | 3.259526 | 3.568309 |
| Row wall seconds | 1,402.869 | 1,473.436 |
| First accepted edit at model call | 34 | 14 |

The fresh run took **24m33s**, 70.567 seconds longer, and cost USD0.308783 more.
Calls fell by six, but this is not an observed cost/time improvement. Provider
dispatch occupied 1,064.884 seconds, about 72.3% of row time; actions occupied
254.138 seconds. The new trajectory found and repaired a different first-patch
failure, so raw counts do not isolate an intervention effect.

All 34 generations and input counts settled. Cost was independently recomputed
from their usage counters and matched scheduler accounting. The full allocation
and **USD0.431691 unused remainder are CLOSED**. Invoice and count-endpoint billing
were not independently verified. One submission manifest and one completed
independent evaluation are recorded; this runtime has no separate evaluator-start
event, so the audit does not infer zero launches from that absent event.

Final public evidence is **506 required tests PASS, one directly selected regression
PASS**, and a current-patch fix-loop probe ending at eight spaces with no lint
remainder. delivery_state remains `unverified_delivery`: helper/API evidence and
independent acceptance do not establish the registered original/CLI obligation.

## Storage, actual delivery and subsequent use

All 34 dispatched requests were compared with their saved native input and expected
projected public state. Current plan revisions survive from call2 onward. There
are 13 actual plan versions: one creation and 12 changes; the other 21 plan events
are `not_requested` receipts, not extra plans. All 12 note-update receipts were
applied without diagnostics. The model used one note ID, n1, throughout; no
automatic note eviction explains the repeat below.

| Public point | Saved / delivered state | Subsequent behavior |
| --- | --- | --- |
| Call5 / note seq83 | n1 records the parse whitespace location and an evidence-linked L036 question; delivered in call6 | Searches tests, then distinguishes the isolated L036 rewrite |
| Call8 / note seq130 | Replaces the incorrect preserved-space interpretation with the observed L036-only zero-space result; delivered in call9 | L036-only stdout leaves the input after call11, but the finding persists; call13 still cites the isolated-rule results while testing a new combination |
| Call18 / note seq299 | Remaining question asks which default-rule interaction causes the bad five-space line; delivered in call19 | Tries rule isolation, then switches to source and fix-loop tracing after a bounded timeout |
| Call28 / note seq451 | Replaces n1 with the observed L039 transition from eight spaces back to five and asks how L039 classifies indentation; delivered in call29 | Reads L039, then call30 reverts the failed L003 workaround and repairs L039 |
| Calls31-34 | Current patch interpretation and remaining verification question delivered with revision13 | Reuses the prior diagnostic program, runs the previously failing test on the new diff, then submits using those current results |

This is observed public continuity, not access to private model reasoning. Delivery
alone does not prove attention, and the result does not show that notes caused
success. At some points source and recent evidence also support the same conclusion.
Source changes mark old evidence historical; model-authored interpretations are
never promoted into certified correctness.

The shared saved-input checker initially rejected the derived
`current_diff.test_execution_review` field after the first edit. The operator-only
audit retained its full expected-projection equality check and compared canonical
diff authority after removing only that derived field. This was an audit shape
assumption, not a solver/runtime failure; the frozen runtime was unchanged.

## Repetition that remains, and useful repeated execution

**Probe5 at call9 redundantly repeats probe1 at call3 on the unchanged base.** Both
use identical CTE/control SQL and the same default fixer, source snapshot, image
and policy. `sqlfluff.fix` reexports `sqlfluff.api.simple.fix`; the different import
spelling does not change the entry point. Both return CTE9/plain4. The second adds
a numeric prefix length derivable from the first exact line string; neither has
assertions. No changed source, setup error or unobserved behavior required this
confirmation. An AST-only duplicate detector returns no candidate because the
program text/AST differs; the input/output/source comparison establishes this case.

Probe1's full stdout is present in calls4-8 and absent at call9. Its reproduction
result was never stored as a finding. At call9 n1 holds the L036-only observation,
while the prior plan mentions nine spaces without retaining probe1 as a note. Thus
the delivery repair works, but selection of what to preserve remains incomplete.
The experiment cannot prove that the missing result alone caused the repeat.

Other overlaps have different purposes:

- Probe6 adds linting of the default fixer's result, identifying the remaining L003
  violation. Probe7 tests the original-input L003/L036 combination, distinct from
  sequentially applying L003 to an already rewritten string.
- Probes8/9 replay earlier programs on the first changed diff. They expose a
  remaining defect and distinguish it from the narrower two-rule path.
- Probe11 times out at its 30-second sandbox limit with cleanup confirmed. Its
  partial output is not evidence that all added rules were checked. The model
  changes approach instead of treating timeout as a passing rule sweep.
- Probe12 traces rule transitions and identifies L039. Probe13 replays that program
  on the second diff, where its result can change submission judgment.
- Both required checks and both selected-file tests run on distinct diffs. The
  directly selected test is justified by the conflict between the broad check and
  the failing same-input probe; it is not a repeated adequate PASS on the same diff.
- After the final selected test passes, call34 explicitly cites sufficient current
  evidence and submits instead of asking for another observation.

Full-stdout matching in the audit is a content-presence test, not an action-identity
test: an identical later replay can supply an older stdout string. The separate
recent-probe IDs, diff hashes and action references distinguish those cases.

## Correctness, recovery and the remaining discovery problem

The first patch changes L003 indentation coercion and creates
`test/rules/std_L003_L036_combo.py`. Required `test/rules` reports 506 PASS, but
probe8 observes five spaces where the public expectation is eight, with L003 still
reported. Call21 runs the new file directly: **one FAIL at `assert result == expected`**,
confirming the helper/check conflict with an ordinary executable assertion.

The file name does not match pytest's normal discovery convention. The repository's
tox configuration specifies `*_test.py`; the new name also misses pytest's default
patterns. Required-check line telemetry is `unknown/unsupported_python_options`,
not proof of execution. No new collection-only or benchmark execution was added by
the operator. The agent's explicit selected run supplies execution evidence.

Probe12 follows the current fix loop: L036 moves the target, L003 reaches four then
eight spaces, L039 changes it to five, and another L003 correction would return to
a previously seen state. This supports a narrower next repair. Call30 restores
L003's original bytes and removes L039's premature clearing of `prev_newline` while
walking leading whitespace segments. The final implementation diff is only L039.

The newly added test's input and assertions remain byte-for-byte unchanged across
the two candidates. It subsequently passes when selected directly, and independent
evaluation passes. Its filename is still undiscoverable by the ordinary suite, so
explicit one-time execution does not repair its future automatic regression coverage.
This remains a concrete follow-up, separately from diagnosis retention.

## Validation, boundaries and evidence

This turn adds an experiment record and current human-facing summaries only.
Runtime/local focused, quick and mock evidence belongs to the linked implementation
record; those broad suites were not rerun for a documentation-only follow-up.
Documentation tests: 6 PASS; operator audit scripts: Ruff PASS. Frozen input
bindings, current runtime hash, journal chains, count-before-dispatch identities,
settled cost and submitted-patch bytes verify. Private evaluator bodies, hidden
tests, reference patches and provider reasoning were not inspected or supplied to
the solver. No model or target execution was added by the observer scripts.

Evidence roots:

- Preparation, approval, audit and closure: `C:/pt/repair-continuity18-20261101-v1/`.
  `manifest.json`, `approval.json`, `audit.json`, `repeat-case-proof.json`, `closure.json`;
  CAS artifacts and append-only `run_dev_repaircontinuity18preparation` journal.
- Execution: `C:/pt/repair-continuity18-run-20261101-v1/result.json`;
  task journal `18/runs/run_dev_bc0bd84569a74e43.jsonl` and external CAS.
- Manifest hash: `sha256:792dc5a048caed077f5e74890282498fc52f0db1ce8cbbbae5a22cfb73dc6131`.
- Submitted patch: `sha256:451e1de78cddadcc37e90ba0c6193d79578b133878ae71eea99b492658940653`.
- Closure: `sha256:5610812202608f2a99125ecd6df161325523297c41a848bb91a02fa181df2674`.
- Baseline run: `run_dev_f0f0167940ee4441`, HEAD `f994a2b6`, runtime implementation
  `e6374d6f`; all historical records and artifacts are unchanged.

One development-exposed task with one fresh trajectory supports the described
mechanisms and outcomes only. It does not establish a general repair rate, a causal
memory effect, or a reason to increase budgets.
