## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-10-23
- Verification Status: ANALYZED
- Version Label: original-obligation-diagnosis-v1

## Reproduction recovery and budget diagnosis

This is a separate follow-up to the [live pilot](2026-10-22-original-obligation-live-results.md)
and [local implementation](2026-10-22-original-obligation.md). Those records remain
unchanged. The question is why two malformed reproduction requests were not repaired,
and why subsequent investigation left an unchecked patch at the cost boundary.
This matters because retaining an unmet requirement is useful only if the agent can
either obtain the missing evidence or deliver an honest, adequately funded outcome.

The observed chain is: a quote-binding error was misattributed to a separate note
error; an unchanged probe purpose/program failed again; the bounded acquisition
stage released after two rejected admissions; source investigation remained offered
and selected; the eventual edit consumed funding needed for the next model request.
The run preserved the original obligation but did not establish its reproduction.

Scope: one development-exposed task, `official=false`, no matched live OFF arm.
No provider call, token-count request, sandbox/probe execution, saved-patch evaluation,
or runtime change was performed for this diagnosis. Verification and repair quality
are not inferred from a process exit code, accepted mutation, or local protocol tests.

## Evidence and method

Source run: `run_dev_a27ef20245fb4e7c`, model `gpt-5.4-mini-2026-03-17`, xhigh,
cap USD 0.88, implementation commit `119f08796e9690227fb67cde4567dd70ccdbf362`.
The selected policies included `bounded-v1` acquisition, `protected-v1` inspection,
and `per-call-v1` cost admission. Current inspected runtime sources match that commit.

The analysis validates the 509-event journal chain, 35 public context artifacts,
and all 34 dispatched request hashes against their prepared request and admitted
output ceiling. It reads explicit public tool arguments, results, decisions and
plans. Provider reasoning payloads are excluded from analysis/output; only aggregate
usage counters are used. Private evaluation material is not consulted.

| Phase | Model calls | Tool actions | Settled model cost, USD | Outcome |
| --- | ---: | ---: | ---: | --- |
| Original reproduction requests | 2 | 2 | 0.139622100 | Both rejected before execution |
| Source reads/searches | 30 | 36 | 0.572054400 | Source evidence, no behavioral result |
| Helper request | 1 | 1 | 0.047825100 | Setup mismatch before target behavior |
| Mutation | 1 | 1 | 0.106803000 | One accepted, unchecked edit |
| Total | 34 | 40 | 0.866304600 | COST_CAP_REACHED; no submission |

These costs belong to model calls selecting each action class, including their input
and output tokens; they are not charges levied by the local search/read functions.
Required checks, finish, independent acceptance and post-submission checks were not run.

## 1. The first error reached the model, but the retry fixed the wrong layer

At sequences 20 and 33, `run_probe` returned the same action-level `CONTRACT_ERROR`:
`reproduction requirement_quote must occur in the public issue`. The submitted quote
contained doubled path backslashes relative to the actual public issue. Literal
substring membership failed in `reproduction.bind` (`reproduction.py:140-145`), before
the probe program or original caller could execute. Removing one level of backslash
doubling makes the string occur in the saved public issue; this is string analysis,
not an executed reproduction.

The first turn also contained two invalid source-note citations and an invalid focus
question citation. Sequence 17 recorded `unobserved_source_range` and
`question_source_not_observed`; the independent verification concern was stored.
That receipt was `partially_applied`, not a reason to skip the main action.

The exact second dispatched request (sequence 27) contains both outcomes in the same
`function_call_output`: the action is failed with the quote message, and
`memory_update_result` contains the note diagnostics. There is no truncation or omission
of the quote error. In its serialized 3,660-character output, the 2,223-character note
receipt precedes the 61-character action error message. `runner.py:2484-2513` preserves
the two outcomes; note errors are explicitly advisory in `model.py:54-74`.

Nevertheless, the public decision at sequence 29 attributes the failed execution to
the unobserved note citation and retries without a note update. Its question text is
rewritten, but its `purpose`, quote, program and replay selector are unchanged. The
same action-level error follows. This establishes an observable recovery mistake.
The competing error messages and their unequal presentation are a plausible
contributor; one trace cannot establish that ordering or verbosity caused the mistake.
The model's private reasoning is neither needed nor available as evidence here.

## 2. Invalid admissions used the reserved acquisition opportunity

`original_obligation.py:72-94` counts original attempts from durable `action_started`
records on the unchanged base, including invalid setup. The gateway records such an
admission even when reproduction preflight has failed (`tools.py:2629-2670,2746-2748`).
Thus two rejected requests counted as two attempts while actual original executions
remained zero. At context sequence 41, acquisition is `released`, with reason
`original_attempt_limit`, status `setup_blocked`, and verification `unverified`.
This release is derived from the journal; no explicit release event is required.

The guidance then changes from `needs_original_reproduction` to
`needs_source_evidence`. The pending stage restricts tools, but the released stage
uses the ordinary completion policy (`runner.py:896-975`). Importantly, `run_probe`
remains offered throughout turns 3-33. The cap ended the protected acquisition stage;
it did not forbid a corrected reproduction request. The next source read was a
prerequisite for editing, not for fixing the quote.

At sequence 45, the model changes its plan to reproduce "if needed" and dismisses
the reproduction concern because the failed quote supposedly no longer tracks an
executable purpose. Sequence 47 accepts that advisory dismissal. The separate original
obligation survives in all 34 dispatched contexts, correctly remaining unverified.
Preserving verification truth therefore worked; prioritizing recovery did not follow
from that preservation. There is no evidence that the original issue disappeared.

## 3. Source coverage permitted a long investigation without resolving behavior

The agent traced builder, manager, module-path resolution, package enumeration and
namespace-package handling. These were related sources, so the entire investigation
cannot be classified as irrelevant repetition. By turn 10 it had read the
`get_source_file` implementation later edited. At turn 11 its public explanation
recognized that this function preserves a directory path, but continued investigating
where the reported `__init__.py` path might originate. That causal uncertainty was
never resolved by an executed original caller.

Of 36 read/search actions, 27 added previously uncovered source lines. The inspection
counter resets when a successful batch adds source coverage (`runner.py:3270-3298`);
coverage gain does not require an original failure, a tested hypothesis or a narrowing
of the remaining behavioral question. The maximum observed no-gain streak was two.

A plateau warning did activate at sequence 462 and persisted at 475 and 488. It was
explicitly `hard_gate=false`, advising review of information value. It did not remove
read/search/probe tools. Actual exploration admission depends on completion headroom
(`runner.py:853-865,964-987`), not this warning. On turn 33 exploration was
`last_opportunity`; on turn 34 it closed with `completion_horizon` (transition 489).
The scheduler then offered only edit or stop, and the model selected the edit.
The legacy `max_consecutive_inspection_turns=24` field is not an active hard cap;
`tests/test_dev_runner.py:163-173` explicitly retains exploration at that boundary.

The late helper probe, turn 27, could have distinguished file loading from namespace
resolution, but it asserted cwd `/workspace` while actual cwd was `/tmp`. Its setup
check failed before target behavior. Turn 28 explicitly recognized the mismatch and
returned to source search rather than repairing the experiment. The harness correctly
gave this result no behavioral credit; the uncertainty remained open.

## 4. Completion protection reserved call/action slots, not future dollars

Under the selected `per-call-v1` policy, `_tool_policy` forecasts completion from
remaining model/tool slots. It intersects those slots with funded calls only under
`completion-reserve-v1` (`runner.py:763-818`). The current call is cost-admitted, but
its future reserve is zero in this run (`runner.py:5194-5210`; `cost.py:109-146`).
This prevents cap overspend; it does not guarantee money for later checks or finish.

Before the last edit, USD 0.120498400 remained and seven model calls were available.
The edit request received an output ceiling of 20,259 tokens and used 17,216 output
tokens, including 16,950 reported reasoning tokens. With its input, that call cost
USD 0.106803000. No reasoning content was inspected. Changing output limits or model
effort has not been tested as a repair for this failure.

After the edit, sequence 507 still reported six model slots, 60 tool slots,
`completion_possible=true`, `protected_completion_possible=true`, and offered
`run_check`. Only USD 0.013695400 remained. Even after a segment handoff reduced the
next counted input from 63,387 to 27,118 tokens, frozen uncached admission rates require:

`27,118 * USD 0.75 / 1,000,000 + 128 * USD 4.50 / 1,000,000 = USD 0.020914500`.

Input alone required USD 0.020338500. The next provider request was therefore denied
before dispatch at sequence 509. This was a monetary admission stop, not exhaustion
of the model-call, action, or wall-time limit. `run_check` availability could not help
because requesting it required another funded model call. Automatic repair-recheck
had no eligible earlier failed check to replay.

## Interpretation, alternatives and decision

- Missing feedback is contradicted by the exact second request. Confusion between
  note and action errors is observed in the public retry explanation; a presentation
  effect remains a hypothesis, not an isolated causal result.
- A global ban on further reproduction is contradicted by offered tools through
  turn 33. The bounded stage released without an executed attempt, while the model
  still had an opportunity to correct the request.
- Pure repeated reading is not the whole explanation: most actions gained source
  coverage. The supported mismatch is between source coverage and behavioral progress.
- Cap overspend or unknown billing is not the explanation. Usage settled, and the
  admission stop was correct. Funding the current call without its successor allowed
  an unchecked patch to consume the remaining affordable work.
- The final patch's correctness is unknown. Earlier inspection of its eventual
  location does not prove the agent could safely have edited it at turn 10.
- Correcting the quote alone is insufficient evidence of a complete fix. The
  [earlier static audit](2026-10-22-original-obligation-live-results.md) also found
  unexecuted caller-argument and expected-outcome concerns. No target behavior was
  observed to confirm or reject them.

Retain the unmet-obligation record and keep acquisition opt-in. The next local design
questions are distinct: make the primary action error unambiguous relative to optional
annotation diagnostics; distinguish bounded request correction from actual behavioral
attempts; and account for funded verification before optional investigation consumes
it. Stable public requirement references could avoid retyping escaped quotes, subject
to tests preserving exact public-task binding. None of these changes is implemented here.

Do not fix this by adding unlimited retries, forcing edits after an arbitrary read
count, or increasing the cap without evidence. Nor is simply switching to the existing
reserve policy proven sufficient: the [earlier funding diagnostic](2026-09-28-minimum-completion-funding.md)
documents how conservative future reservations can displace useful work. Any comparison
must measure request recovery, executed original evidence, checked delivery and cost
separately. This analysis changes the diagnosis, not the selected runtime policies;
all paid allocations remain closed.

## Statistical and reproducibility limits

This is deterministic trace accounting and source inspection of one run, not a
statistical treatment comparison. There are no p-values, confidence intervals or
effect-size estimates to interpret. Overall confidence is CAUTION for causal or
general improvement claims. The recorded event ordering and budget arithmetic are
directly checked; changing the interface has not been shown to improve model behavior.

Fallacy coverage: 11/11 checked. Simpson's paradox, ecological inference, collider
adjustment, base-rate neglect, regression to the mean and reverse causality are not
applicable to the reported comparisons. Berkson/selection risk limits generalization
from a selected development failure. Survivorship is addressed by retaining failed
actions and the non-dispatched terminal boundary. Look-elsewhere and forking-path
risks remain bounded by labeling this post-run diagnosis exploratory and reporting
competing explanations. Correlation-versus-causation limits the presentation-effect
hypothesis and all proposed improvement claims. No live reproducibility rerun occurred;
the status is ANALYZED, not VERIFIED.

## Artifacts and review

New root: `C:/pt/original-obligation22-diagnosis/`. `analyze_saved_run.py` records its
hash and derivation events in append-only `runs/run_dev_originalobligationdiagnosis.jsonl`.
Reports are stored in `artifacts/` and content-addressed objects:

- `timeline.json`: `sha256:fae2f75673269b7137bb8d51e339357c667f3a89aaff5ce076004e8895beeaa7`.
- `feedback-delivery.json`: `sha256:7c7eea58ff4cf081fb63ebc2f6afc9235751def7a6d74598a07ab9e2cfc5b0dd`.
- `summary.json`: `sha256:3441a1c35ab0d3785b02a070fa0c4e6d7aa6cb2ba4e32689884a89f2eb99498c`.
- Source journal bytes: `sha256:47d676823cf1cefc2bcadc3e2ce4bfbb349985758a23cdd544c3755b3fbdb195`;
  chain tail: `sha256:fcc5d1241e31f2923da932cbcab077f455f678dd2a4c8cfff4267c5697bc32ae`.

A native worker audited policy/source mechanics with shared prior context; the parent
checked its claims against the trace. A feedback worker failed on model capacity, so
the parent completed that audit directly. This is not blinded or cross-model review.
No old solver journal, report, patch or runtime source was modified.
The policy review is saved separately under `policy/policy-audit.md` and its public
projection, then bound into the diagnostic artifact store and journal. Documentation
layout tests passed 5/5, Ruff passed, and the diff whitespace check passed. Runtime
was unchanged, so no new full-suite or mock smoke was needed for this documentation
change. Additional provider cost was zero.
