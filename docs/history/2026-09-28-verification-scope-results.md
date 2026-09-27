# Verification-scope cue: scope acknowledged, actions unchanged

2026-09-28, official=false. One cued continuation compared sequentially with one
[earlier unhinted continuation](2026-09-28-post-edit-budget-results.md).
See [preparation](2026-09-28-verification-scope-preparation.md). This is selected
development data, not a randomized comparison, fresh solve or general efficacy test.

## Execution

The user authorized one continuation with a fresh $3.00 cap under the prepared
manifest `sha256:566a916c7782bb0b1f9011d8c7fcf66dc7141a39b7529457f67431fe09fb0cbe`.
Implementation commit: `fcf8237`. Task, model, credentials and inherited limits match
preparation: original-toqito-1538, gpt-5.4-2026-03-05 xhigh, repository `.env`.

| Observation | Unhinted | Verification-scope cue |
| --- | --- | --- |
| New model calls / counts | 2 / 2 | 2 / 2 |
| New actions | regression check, finish | regression check, finish |
| New inspections / probes / edits | 0 / 0 / 0 | 0 / 0 / 0 |
| Public regression | 14 pass, 1 deselected | 14 pass, 1 deselected |
| Submitted candidate | unchanged | same unchanged patch |
| Benchmark acceptance / safety | FAIL / PASS | FAIL / PASS |
| New cost | $0.2168265 | $0.234737 |

The cued collector took 77.58 seconds including preparation/evaluation. Billing is
known; no retry or new allocation was used. The unused $2.765263 is closed. Branch
cumulative bookkeeping ($1.326036) includes inherited $1.091299; only $0.234737 is
new spend. Earlier runs and their NOT_RUN/FAIL classifications remain unchanged.

## Input to judgment to action

Actual first dispatch differs from the earlier unhinted actual first dispatch only
by `verification_scope_cue`. Its source prefix, candidate, tools and remaining
resources match. Both new dispatched inputs match saved public-state projections.
No task-specific operator hint, failing case or private evaluator feedback was added.

At the first decision the agent correctly described the public suite as testing
preserved default/downarrow behavior and invalid inputs. Its plan said the new
uparrow cases were not exercised and left a possible targeted probe as remaining
work. This is a narrower, more accurate stated interpretation than the unhinted
run's claim that PASS would verify the extension. It is not evidence of a newly
performed assertion inspection: no source read/search was executed in either run.

After PASS, the agent still had 31 model calls, 84 tools, three edits, approximately
1,180 active seconds and $2.86881 before the last dispatch. Probe/read/edit tools
remained available. It acknowledged that the check confirmed preserved behavior,
but characterized remaining uncertainty as hidden cases rather than a concrete
public blocker, cleared its open question and submitted. No new evidence about
the extension intervened between acknowledging its verification gap and closure.
The reference to hidden cases is model speculation, not evaluator information.

The literal cue was present in the first request and absent from the complete
second request after the ordinary `major_result_reviewed` segment transition.
This matches the designed one-time injection. The first public plan and question
still influenced the subsequent state; the cue itself was not reinjected. The
second request retained ordinary finish guidance saying eligibility is not proof
of untested behavior, but recommending finish absent a concrete remaining question.

Therefore the observation is **better stated scope, unchanged verification and
repair behavior in this sample**. It does not establish that scope cues never help.
Text, timing/persistence, inherited implementation confidence and completion advice
remain competing influences. Do not turn this into mandatory probes or adopt a
default prompt merely because the first plan sounded better.

## Correctness and evidence boundaries

Both submissions and the earlier publicly audited candidate have patch hash
`sha256:fdd4fa640b555cc3ef43317ec9b4b3fa2a694902f11d571f43fb48dd2a318745`.
The prior journal-bound public mathematical witness still applies by byte identity:
returned 0.5849625 versus feasible objective 0.7715533. It was not rerun on unchanged
bytes. Aggregate benchmark FAIL is separate evidence; private failing tests and
evaluator internals were not inspected and are not inferred from this witness.

If another diagnostic is selected, first isolate why the acknowledged verification
gap is dropped at completion. One possible single-axis experiment holds cue text
fixed and varies its delivery at the submission decision; this separates timing
from claims about better cue content. It requires its own checkpoint and allocation.
No further paid run, runtime/default change or generalization claim is authorized.

## Records and validation

- Collector: `C:/pt/scopecuelive0928a/result.json`; group journal
  `runs/run_dev_posteditcontinuation.jsonl`, branch `A1/runs/run_dev_33068b6e257f423a.jsonl`.
- Audit: `C:/pt/analyses/verification-scope-results-20260928-v1/public-process-audit.json`;
  `runs/run_dev_scopecueresultaudit.jsonl` binds the public report and collector result.
- Script: `C:/pt/audit_scope_cue_results_0928.py`.

Provider-free assertions checked exact first-input difference, source preservation,
both delivery projections, cue presence/absence, action sequence, cost settlement,
unchanged patch identity and the previous counterexample receipt. Documentation
checks passed. No runtime change, extra provider call or full-suite run was needed.
