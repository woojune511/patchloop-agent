# Why the accepted SQLFluff repair differs from the earlier failed edit

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate; saved public evidence and bounded local patch comparison
- Origin Date: 2026-10-29
- Verification Status: VERIFIED for three saved variants on three public cases;
  model-choice causality remains unestablished
- Version Label: sqlfluff_success_mechanism_v1
- Evidence class: operator diagnostic, official=false, claim-ineligible

## Question and method

The user asked why the [latest run](2026-10-29-probe-followup-single-results.md)
passed independent acceptance whereas the [earlier edit](2026-10-29-edit-prerequisite-single-results.md)
failed. This investigation separates the code mechanism from why the model chose
that code. A prior [trace](2026-10-29-sqlfluff-branch-diagnosis.md) already showed
that the failed edit executed without changing its intermediate SQL. The latest
solver did not replay its final candidate on the original public example, so the
exact public before/after result still required direct confirmation.

Three isolated local executions compared the previous failed patch, the latest
run's first patch and its final patch. They used the same prepared source base,
dependencies, pinned public probe image and helper program. Inputs were the public
issue's CTE SQL plus the two existing public L036 fixtures named by the first
patch's regression failures. Those top-level cases used the repository's own
`assert_rule_fail_in_sql()` helper and exact fixture expected strings. No private
test or reference patch was read.

The helper recorded full CTE output and a bounded, read-only trace of rule fix
applications. Its traced and untraced CTE outputs matched for every version. Loaded
L036 hashes matched each workspace, complete diff hashes matched saved candidates,
and all executions exited zero without timeout, output/trace truncation or cleanup
uncertainty. The plan limited three target executions to 120 seconds overall,
30 seconds per target and 40 trace events per target, without retries. Recorded
target durations were 14.694, 10.477 and 9.704 seconds; timing is not compared.

## Controlled public results

| Saved version | CTE output / expected | Two existing top-level L036 cases |
| --- | --- | --- |
| Previous failed patch | 9 spaces; exact output mismatch | Both pass |
| Latest first patch | 8 spaces; full output exactly matches | Both fail |
| Latest final patch | 8 spaces; full output exactly matches | Both pass |

These are new operator observations made after the completed model run. They
confirm behavior of saved candidates but do not retroactively give the solver a
post-edit replay or change its recorded `unverified_delivery` diagnostic. The
latest run's independent acceptance/safety remain PASS; no evaluator was rerun.

## The previous edit changed operation form, not the faulty intermediate result

The previous hypothesis blamed a surviving original space. Its helper ran the
full formatter, but its segment dump parsed the original SQL rather than the
transformed output. Seeing a space in the original input did not establish that
the space survived the transformation.

The edit replaced `delete(space) + create(newline)` with `edit(space -> newline)`
for the first target. The traced branch executed and its fix was accepted, but
the first target still began with zero spaces. The subsequent public call followed
the same downstream path as previously traced:

`L036: 0 -> L003: 4 -> L003: 8 -> L039: 5 -> L003: 9`.

The final repeated nine-to-nine proposal was rejected as already-seen SQL. Public
regression success did not expose this unchanged final CTE behavior. The old
patch's failure was not caused by an unexecuted branch or missing source change.

## The new edit supplies the needed indentation at the transition

Before its first edit, the latest model compared `fix(..., rules=['L036'])` with
the full formatter. L036 alone put the target at zero spaces, while full formatting
left nine spaces and a remaining L003 violation. Its recorded hypothesis was to
reuse the existing select-target indentation when moving a target to a new line.

Both new candidates delete the old inline space and insert **a newline plus the
existing eight-space target indentation**. In the fresh local traces, L036's first
accepted fix immediately produces eight spaces. There are no subsequent L003 or
L039 fix applications on this CTE call. The patch therefore avoids entering the
fragmented-indentation correction sequence observed in the failed version.

This is a controlled code-level explanation on the public input. It does not
require the model to have reconstructed every L003/L039 internal step: the model
read L003 source and obtained a discriminating stage comparison, then changed the
upstream transition. L003 and L039 source were not changed. The prior proposal to
normalize the entire downstream indent buffer was one possible repair hypothesis,
not a necessary location established by the earlier trace.

## Regression feedback refined where the new behavior applies

The first new patch reused target indentation whenever its existing whitespace
index was available. That changed the expected L036-only output for two top-level
multiline SELECT fixtures. The live public suite returned 2 failures and 504 passes;
the bounded local comparison reproduces those two mismatches.

The second edit adds the condition that the SELECT token's
`pos_marker.working_line_pos > 1`. It is a column-position guard, not a syntactic
CTE detector. On the selected public CTE, the guard preserves indentation reuse;
on both top-level fixtures, it preserves the prior no-added-indent behavior. This
explains why the final candidate retains the public bug fix and recovers those
regressions. The live suite then passed all 506 cases and independent acceptance
passed. General behavior outside those checks is not established by this analysis.

## What changed in the model's evidence and what cannot be attributed

Stored actual requests were reconstructed and matched to input-count/dispatch
receipts: 11 previous requests and 17 current requests. Before the previous first
edit (input sequence 129), the helper result was present. Before the current first
edit (sequence 167), the L036-only/full-fix/remaining-violation observations were
present. The difference was the discriminating observation content, not a simple
absence of tool feedback in the old run.

The current first edit occurs in response 12. The new `probe_followup` card first
appears in response 13 (input sequence 181), so it cannot explain the earlier first
repair idea. The general probe description was changed from the initial request,
but its influence is not separated from stochastic action selection in a single
historical comparison. The model used no post-edit helper despite four replay
offers. Card delivery is verified; replay uptake and a causal repair gain are not.

The first public check's two named failures and `2 failed, 504 passed` summary
appear in the following request and remain in the pre-revision request at sequence
222. The subsequent recorded hypothesis and edit specifically preserve top-level
behavior. This is direct evidence of available failure feedback and a matching
revision, rather than an inference from the final PASS alone.

The model, reasoning setting and nominal resource limits were unchanged; request
JSON differs only in `state_root`. Actual usage was larger: 11 to 17 responses,
one to two helpers, one to two accepted edits, and USD0.587558 to USD1.18095550.
Neither run exhausted its cap. More useful exploration and a regression-driven
revision occurred, but this is not a cost-efficiency or context-size experiment.
Some searches still returned no matches; success does not establish uniformly
efficient exploration.

## Decision, scope and reproducibility

The supported engineering lesson is to obtain observations that distinguish a
repair hypothesis and preserve feedback that tests the change's applicability.
This run supplies concrete examples of both. It does not justify attributing the
success to the new card, increasing limits, or introducing mandatory replay merely
because the optional replay was unused. Submission policy and runtime are unchanged.

All 11 ARS interpretation fallacies were considered in `analysis.json`; this is a
mechanistic comparison with no p-values, effect estimate or population inference.
Failure-selected task exposure, repeated development history, stochastic run
variation and post-hoc analysis prevent general causal claims. The first new
candidate's regressions and the previous failed candidate are retained rather
than selecting only the final successful result.

Evidence root: `C:/pt/sqlfluff-success-comparison-v1/`:

- `plan.json`, `public-cases.json`, `execution-helper.py`, `run_compare.py`.
- `old_failed/`, `new_first/`, `new_final/`: exact patch, request, receipt, raw
  stdout/stderr and structured measurements.
- `summary.json`, `analyze.py`, `analysis.json`: controlled output comparison,
  actual model-input evidence, declared hypotheses and interpretation boundaries.
- Hash-chained `runs/run_dev_sqlfluffsuccesscomparev1.jsonl`.

The old/first/final diff hashes are respectively
`sha256:d3022a59756dfb1c7ad44b9b2c063306a384e147f78c9f0a0194d3fc560bfe62`,
`sha256:6c35d616c525d5945a00cbd9959aa34931db1b00feac715f766f17c6dc25848b`,
and `sha256:a7f85769bb06ac55aa190fb94c4d676a713674e280810abfe41d6a1effe0eb1e`.
Current runtime hash remained
`sha256:08b32133d33201efb3b55cd44db917ff76ffc8752676e00f5cdc366280b16b1e`.
No paid model, credential access, hidden evaluator, image pull/build or historical
artifact mutation occurred. This local analysis was authorized by the user's
current comparison request, not by reopening the closed USD4.50 allocation.
