# Target-failure classification and context capacity

Status: ANALYZED; no runtime change or new paid execution.
Date: 2026-10-26. official=false; claim-ineligible.

## Material Passport

- Origin: academic-research-suite / experiment-agent / validate.
- Version: target-failure-context-v1.
- Inputs: the closed [request-continuity pilot](2026-10-26-request-continuity-live.md),
  its saved public receipts and actual model inputs; frozen mini-SWE-agent source
  and dev20 public usage records. No private evaluator internals were opened.
- Question: why did a captured replacement exception not lead to another repair,
  would more context help, and did mini use the model window without an extra cap?
- Verification: deterministic offline classification and record inspection only;
  no target replay, provider call or claim of a repaired runtime.

## Direct failure and classification defect

The candidate made missing initializer files into empty source at the builder,
but later `Module._get_stream` reopened the missing file. Its original-call replay
captured `builtins.FileNotFoundError` from call-1. A later helper assertion raised
`RuntimeError` instead of recording observation JSON, so the whole probe exited 1.

`patchloop/dev/target_outcome.py:bound_failure` rejects any outer execution whose
status is not `passed` or whose exit code is nonzero, before it inspects a selected
call. This conflates a fully observed target failure with the completion status of
the surrounding model-authored helper. The contract intends to retain positive
selected-call failure even when whole-case comparison remains unknown.

Offline checks of the actual saved base/candidate pair established:

- Frozen binding, selected normalized inputs and execution environment match.
- Call-1 is valid, capture is complete and its exception is unexpected.
- Current classifier returns `None`.
- In an in-memory copy, changing only outer `status` to `passed` and `exit_code` to
  zero makes the same classifier return `original_target_exception` with no
  verification credit. No original record or runtime source was changed.

This isolates the guard excluding this receipt. It is not a proposal to accept
arbitrary failed probes: future changes must still establish trustworthy selected
call capture, identity, setup and cleanup, and keep whole-case verification unknown.
Target failure and later helper failure need distinct evidence and outcomes.

The consequence was visible in the final input: `target_failure_count=0`,
`current_public_failure=null`, repair path `not_needed`, and `ready_to_submit` after
public regression PASS. Nevertheless, the detailed original-case record still
contained the failed candidate replay and its exception. The model's finish
assessment described original reproduction as not rerun. Thus both classification
and evidence use matter; complete loss of failure information is contradicted.
Three further edits and substantial call/cost/time capacity were still available.

## What the current context actually did

| Axis | Recorded value |
| --- | --- |
| Segment input ceiling | 60,000 tokens |
| Source retention on ordinary reconstruction | 24,000 characters, not tokens |
| Maximum / mean / final actual input | 56,977 / 34,983.65 / 23,327 tokens |
| Segments / post-initial resets | 6 / 5 |
| Reset reasons | Repair entry 1, result follow-up 2, repair return 1, completion entry 1 |
| Size-triggered reset | 0 |
| Normal / correction output ceiling | 40,000 / 25,000 tokens |

The 40K setting is response output capacity, not input history capacity. Raising
60K alone does not remove any of these recorded stage/result triggers. Furthermore,
`runner.py` forces repair/diagnosis/completion stage changes to start new segments,
independently of `segments.boundary_reason`; selecting size-only boundaries alone
does not remove those forced transitions. Completion projection omits source
bodies and bulk history while preserving the current patch and verdicts.

Failure evidence remained at finalization, so there is no demonstrated hard-window
overflow explanation for the final submission. Longer continuity might still help
the model connect evidence to its next edit, preserve source and reduce repeated
reasoning. This run did not measure that counterfactual or isolate cache effects.

## What mini-SWE-agent actually used in the earlier comparison

The [original mini panel](2026-10-16-mini-swe-dev20-results.md) used the same mini
snapshot at xhigh. Executed wrapper commit
`dca0f0cf4848a6c53377f1352aa356eaf3a9730e`,
`diagnostics/mini_swe_runtime.py`, hashes to
`sha256:f1fc0ec5224fd1b16f354563353a5f4f51de5ed9cb9b5bb57810aaba631f7ebd`.
Its lines 153-181 send accumulated messages and encrypted continuation with
`truncation="disabled"`; its guard is input count plus admitted output at most
400,000, with a 25,000 output target. There is no extra 60K cap or segment reset.
The pinned upstream agent extends `messages` and passes the accumulated list.

This means it was allowed to grow within its model/runtime limits, not that it
actually consumed the whole window. Reinspection of 524 dispatched requests and
settled usage found maximum input **77,660** and mean **26,225.84** tokens, with
25K output and disabled API truncation throughout. Its tool-output template still
limits each bash observation to 10,000 characters (head/tail with omissions).
Forty generation calls, 100 actions, 1,470 solver seconds and USD 1.19987985 per
task also bounded execution.

The peak was Astroid-1333, row13. That original attempt reached 40 calls, ended on
an unavailable `apply_patch` command and did not submit; native evaluation was
NOT_RUN. This is a tool/closure failure, not evidence that larger context cannot
help or that the candidate was incorrect. The separately funded five-row follow-up
must not be pooled into the original panel.

For comparison, the [old PatchLoop segment audit](2026-10-16-segment-boundary-audit.md)
reported maximum input 59,461; 75 post-initial handoffs were 66 result-triggered,
seven input-triggered and two encrypted-item-size-triggered. Different tools,
prompts, budgets and handoff policies prevent attributing panel differences to
context size alone.

Current [official model documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
checked 2026-10-26, lists a 400K context window, 272K maximum input and 128K maximum
output for `gpt-5.4-mini-2026-03-17`. The historical wrapper's total-window check
does not override the API's separate input limit. Its observed 77,660 input tokens
did not reach either bound.

## Decision and next experiment boundary

Fix the demonstrated target/helper classification gap first. Then evaluate context
continuity as a separate intervention: keep the original call, edit and replay
history available through the follow-up repair decision instead of resetting at
each stage. A comparison at the same 60K ceiling can first isolate that policy;
increase input capacity, for example to 120K, separately if size then becomes the
limiting factor. These are proposals, not executed comparisons or new authorization.

Benefits to investigate are source availability, evidence reuse, fewer repeated
reads and cache/continuation reuse. Costs include larger requests, stale/conflicting
history and fewer calls under the same dollar cap. Current completion reservations
use `segments.MAX_INPUT_TOKENS`; increasing that constant also raises conservative
future-input reservations. A capacity experiment must report those effects rather
than claim the token setting alone changed quality.

## Evidence and limits

Reproducible offline analysis is at
`C:/pt/target-failure-context-analysis-v1/analyze.py`; `analysis.json` is CAS
`sha256:1663c65072d2f72d202fcba15bc1866f7c86a779d4859a883cab4d26c847b5f3`.
Its separate append-only `dev-run-v1` journal preserves the receipt; closed pilot
and historical evidence bytes remain unchanged. Historical public usage source:
`C:/pt/mini20rerun01/public-trace.json`; maximum request in
`C:/pt/mini20live02/13/runs/run_dev_minimodel.jsonl` (count197 / response199).
The frozen wrapper is retained by hash in the new analysis artifact store.

Fallacy scan: 11/11 considered. The important limits are selected-task bias,
one-run stochastic variation, ungraded attempts, differing harness conditions and
the inability to infer causal quality or cost gains from longer history. No
significance test, solve-rate gain or generalization claim is made. Verification
status remains ANALYZED; the runtime defect has not been fixed or live-retested.
