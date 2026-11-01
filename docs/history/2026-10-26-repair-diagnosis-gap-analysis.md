# Repair diagnosis gap after a captured target exception

Date: 2026-10-26. Status: CLOSED analysis. official=false; no quality claim.
Runtime inspected: `73ee1e1a`, unchanged from implementation `b26bd729`.
Runtime hash: `sha256:61887a3ccfabb9db830b1ae63548babb53e411a7bcf5e351a202e0c5511c7f64`.

## Problem and reason for selection

The [latest pilot](2026-10-26-target-exception-live.md) retained the original-call
exception and blocked finish, yet both edits failed. Another fresh solve would
not distinguish missing diagnostic evidence from ineffective model decisions.
The question is whether the actual post-edit request supplied both the failure
and a usable route to locate its cause. This matters more immediately than
another submission safeguard: correct negative classification did not produce a
supported repair, and the latest newly changed helper-exit branch was not exercised.

## Saved evidence and reproducible analysis

Source run: `C:/pt/target-exception-live-v1`, `run_dev_b43b14dd7b2741ad`.
New analysis: `C:/pt/repair-diagnosis-gap-analysis-v1/analyze.py` and `analysis.json`.
Append-only journal: `runs/run_dev_repairdiagnosisgap.jsonl` under that new root.
Analysis artifact:
`sha256:901422add4aa1aaab309de0eae5cbdac4ac13352dde6132bbedb004e08ca4dbf`.

The script validates the saved source journal and model-input/request artifact
hashes, reconstructs all six post-edit model requests, and recomputes completion
and repair-path projections. Three current-candidate replay receipts are checked.
Assertions passed; historical input bytes and runtime hash remained unchanged.
No provider, target execution, Docker operation or private evaluator access occurred.

## Findings

1. **The negative result was delivered.** Every post-edit input contains the
   current `FileNotFoundError` and excludes finish. The generic original-failure
   diagnostic opportunity was offered. The overall case stays UNKNOWN; positive
   selected-call failure is separate evidence.
2. **The exception location was never collected.**
   `probe_call_capture.observed_target` catches the exception and saves only type
   and a 256-character message. It saves no traceback or exception chain.
   `target_outcome._outcome` also exposes only those two exception fields. In all
   three post-edit replays, the failing call's complete stdout and stderr are
   both empty. The location was absent at capture, not merely lost by a later
   context reset. A larger context cannot restore that missing record.
3. **The specialized path tool was not offered.** `repair_path.review` requires
   a comparable REFUTED original case and measured unobserved changed Python
   lines. Here the case is UNKNOWN with a confirmed unexpected exception, and
   changed-line feedback has no unobserved executable changed ranges. Both
   mutations' relevant new lines were entered on the launch thread. The path
   projection is `not_needed`, and all three offered post-edit `run_probe`
   schemas require `call_path=null`; none offers `observe_original`. Generic
   reads and authored probes remained possible. This is a missing route for
   an executed but still incorrect repair, not proof that all diagnosis was impossible.
4. **The next actions did not discriminate between causes.** After the first
   automatic replay, the model repeated the same original on the same candidate.
   It then assigned `namespace_module.file` to the missing initializer path.
   After that failed it read the edited builder again. No new post-edit failing
   frame was observed. There were 29 read/search actions before the first edit.
   That count alone does not establish that every inspection was wasteful.

The final source still gives `Module._get_stream` a nonexistent `module.file`
without `file_bytes`, so a later source-stream open is a concrete candidate
mechanism. The first edit returned a namespace node without that assignment.
The exact escaped exception stack for either latest candidate was not collected;
do not silently transfer the earlier pilot's confirmed downstream stack to these
new candidates or conflate a primary error with error-reporting failures.

## Interpretation correction and alternatives

The earlier statement that the model had a diagnostic opportunity but did not
use call-path diagnosis needs this qualification: the generic allowance existed,
but the existing specialized original-call path request was unavailable. The
[prior analysis](2026-10-26-target-exception-propagation-analysis.md) correctly
identified the failure/blocking route; it did not establish a complete diagnostic
route for this changed failure. Closed records remain unchanged.

Missing frames and the restricted tool route are confirmed defects in diagnostic
coverage. They do not establish that supplying frames will make this model repair
the task. Long generation and weak action selection remain plausible independent
contributors: 109,115 of 116,421 output tokens were billed reasoning tokens, and
three admitted responses ended without tools. Their internal reasoning is unknown.
The USD 1.20 cap was not fully spent; USD 1.071262200 was billed. Larger output or
context limits have no demonstrated causal benefit here. Conversely, failure
with absent frames does not prove the model is incapable with adequate evidence.

ARS methodological scan: 11/11 checked. This is one adaptively selected development
trajectory, not an accuracy estimate. Selection on failure, adaptive intervention
choices and unsupported causal attribution are relevant cautions. No inferential
statistical test, generalization or comparative model claim is warranted.

## Decision and smallest next diagnostic

Stop using another fresh solve as the immediate diagnostic for this failure.
Preserve the finish blocker, but prioritize useful error evidence over another
mandatory state or retry rule. The next local intervention should attach bounded
public exception frames and causal/context exception information to the existing
failure packet. Frame origin, candidate and selected-call identity must remain
explicit; partial collection cannot become evidence of absence or success.

First use the saved public candidate and frozen original to establish which
frame actually fails, including any secondary error while reporting it. Verify
locally that the model-visible packet retains that location. A limited model
repair from this saved failed state would then test whether the information
supports a better next edit; it must be labeled a seeded repair, not a fresh solve.
Keep model/settings/budget fixed for an information-delivery comparison. If clear
failure frames are already delivered and the model still repeats uninformative
actions or emits no tool, investigate model/reasoning settings and workflow
constraints instead of adding another exception-specific gate. No such run is
authorized or executed by this analysis.

Implemented this turn: analysis artifacts and documentation only. Runtime repair,
new stack capture, candidate execution, model continuation and independent
acceptance remain NOT_RUN. Documentation-layout validation: 5 passed.
