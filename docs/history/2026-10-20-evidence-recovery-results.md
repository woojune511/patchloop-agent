# Recovery comparison stopped on provider usage uncertainty

2026-10-20. The authorized fresh Astroid-1333 A/B allocation is **closed**.
A1 submitted a patch but failed independent acceptance. B1 stopped on its first
model response; the remaining ten rows were not run. The treatment's effect on
evidence use or repair success is **not established**. Every row is
`official=false` and claim-ineligible.

## Question, intervention and fixed scope

The [preceding diagnosis](2026-10-20-history-search-nonuse.md) found lost source
bodies followed by shallow searches, and helper results interpreted as original
caller success. The [implemented changes](2026-10-20-evidence-recovery.md) restore
prior bodies at ordinary source-search hits, distinguish helper evidence from
original-caller reproductions, and bind the program/expectation of a before/after
comparison. This experiment asked whether their combined effect changes actual
agent behavior and independently accepted repairs. Source delivery alone was not
the endpoint; failure to acquire the caller and misjudgment of available evidence
remained alternative explanations.

The user authorized the [frozen specification](../../.agent/plans/evidence-recovery-comparison.md)
with the subsequent request to execute. Its preparation-time authorization status
and all frozen bytes remain unchanged; the new authorization is recorded separately.

| Item | Frozen value |
| --- | --- |
| A, pre-change with history enabled | `bbdb2f4b7a20183aa2a974ed6a91e5687a87bdf5` |
| B, all three changes with history enabled | `d1eb5218e551c3daf4c00d0c7a9617f4894fb304` |
| Preparation/documentation commit | `27e0665` |
| Task | `swebench-lite-dev-pylint-dev-astroid-1333`, `tasks/dev-train/current-dev20/13/public.yaml` |
| Model and credential | `gpt-5.4-mini-2026-03-17`, xhigh, project `.env` |
| Allocation | Six rows per arm; twelve total; USD 0.88/row, 5.28/arm, 10.56 overall |
| Serial order | A1 B1 B2 A2 A3 B3 B4 A4 A5 B5 B6 A6 |
| Execution | 40 model calls, 100 actions, four edits, 1,800 seconds per row |
| Context | `segmented-v1`, `result-or-size-v1`, two references, 24k source characters, 60k counted input tokens |

Other request/probe limits and the prepared Pylint 2.12.2 environment stayed fixed.
There were no retries, replacements, continuations, cap transfers or paid judges.
Official pricing was checked before dispatch: input USD 0.75/M, cached input
0.075/M, output 4.50/M, matching the frozen rates
([OpenAI pricing](https://developers.openai.com/api/docs/pricing#text-tokens)).

## Execution and independent outcomes

| Row | Execution | Public checks | Registered | Native | Original caller, missing initializer | Present-initializer control | Safety |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Submitted; 39 model calls | PASS | FAIL | FAIL | FAIL | PASS | PASS |
| B1 | First response rejected; no tool action | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| Other ten | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

There are zero accepted repairs among the twelve assigned rows, but only one
submitted patch was evaluated. This is not a completed 0/6 versus 0/6 repair
comparison. B's missing behavior is infrastructure interruption, not observed
refusal to use the new tools. The predeclared improvement screen is unassessable.

Public-only annotations were sealed before opening new acceptance grades. A1's
saved submission then received exactly two caller checks and one separate native
evaluation in 49.66 seconds, with zero provider calls. Missing-initializer execution
still emitted F0010, exited 1 and did not analyze the child module. The preservation
control exited 0 and analyzed the child. Native and registered acceptance agree;
local assessment cleanup is confirmed. A later Docker inventory showed no running
containers. B had no submission or evaluator execution.

The native evaluation used the exact whole submitted patch, hash
`sha256:9ef3fcb0b921e9142cab69dadac36f09e715a58ceedd18325a6e5cf61a451728`.
Caller checks used its source-only projection, hash
`sha256:1ac127d0b6c304ac53f23ba4724953b59e25e665926f2b00bae9253af9d6ad57`;
the added `tests/unittest_modutils.py` test was omitted from that projection.

## Acquisition, delivery and judgment

A1 received relevant Astroid builder, manager and modutils bodies. No Pylint
caller-source acquisition, original caller execution or `run_probe` was observed.
It changed `_spec_from_modpath` to classify a package directory without an
initializer as a namespace package and added a helper-resolution test. That test
creates a directory but omits the issue's `project/file.py` and calls
`file_info_from_modpath`/`file_from_modpath`, rather than Pylint. There was no
before-edit execution of the new test, so its discriminating value was unverified.

The final public assessment nevertheless claimed that the change avoids the
reported F0010 path and that further public evidence would not change completion.
The independent caller failure confirms that this conclusion was too broad.
This single control trajectory therefore shows both a missing original-caller
observation and an unjustified inference from helper/regression success. It does
not show that the model saw a correct original-caller result and ignored it.

The 39 actions comprised 21 source searches, 13 reads, two edits, two public checks
and submission. There were zero explicit history searches. Applying B's restoration
predicate to each A search against its preceding public inputs found no eligible
same-version lost-body recovery opportunity. Thus this A trajectory alone would
not exercise automatic restoration, even though source was lost elsewhere.

A made five later transitions: two for input size and three after major results.
The inventories lose 24, 383, 158, 118 and 828 source-line appearances respectively.
These are repeated exposures, not unique lines; some reflect changed file hashes.
Builder lines 197-220 disappear at input 307 and return through ordinary retained
state at 420. Builder's body is absent at 436; final input 535 retains only manager
line 145. No retrieval ran, so these changes are not measured displacement caused
by the intervention. The exact caller code/setup was never acquired in the first
place. B produced no trajectory to measure restoration, comparison use or added
displacement. No encrypted reasoning was decoded.

## Provider stop and billing

B1's input-count request completed with **13,885 tokens**. Its generation request
used the same counted request hash, the specified model and a 25,000-token output
ceiling. After 1.710 seconds, the SDK response reported `incomplete` with
`max_output_tokens`, zero output items, and integer zero for input, cached input,
output, reasoning and total usage. The count mismatch was -13,885.

The existing adapter rejected this as `input_token_count_mismatch`, marked billing
UNKNOWN and stopped the allocation. This was the required uncertainty boundary;
neither the check nor the limit was relaxed. The evidence locates the inconsistency
in the SDK-exposed response, not its underlying provider/network/SDK cause. The
status alone does not prove that 25,000 output tokens were consumed or that context
was exhausted. It also does not establish a defect in B's prompt or schema.

| A1 settled component | USD |
| --- | ---: |
| Uncached input, 521,625 tokens | 0.39121875 |
| Cached input, 945,664 tokens | 0.07092480 |
| Reasoning output, 57,873 tokens | 0.26042850 |
| Other output, 8,074 tokens | 0.03633300 |
| A1 settled total | **0.75890505** |
| B1 actual cost | **UNKNOWN** |

A1 used 1,467,289 total input and 65,947 output tokens, with a maximum reported
single input of 59,575 tokens. No admitted output ceiling was reduced. B1's
pre-dispatch reservation was USD 0.12291375; it is not a billed charge. Its reported
zero is preserved but excluded from settlement. Total actual spend remains unknown,
not USD 0.75890505. There were 40 generation requests and 42 input-count requests;
the two additional A counts accompanied size transitions.

## Evidence, validation and decision

Immutable evidence root: `C:/pt/evidence-comparison28/`; solver journals:
`C:/pt/evidence-comparison28-live/`. Canonical manifest identity:
`sha256:688eb17b6e4c5355307e920fd4408e7dcf8175d1f033465863b0bdf3c52108e3`.
The exact authorization, collection, sealed annotations, public inventories, usage,
caller/native receipts and `result.json` remain separate. `execution-closeout.json`
hash `sha256:761e2f49bd9b56047d5004ffbf82dcb22efb0dae84ccb75591e280de15ed002d`
records final manifest validation, nine verified journal chains and snapshots of
the two bound guidance files before updating current status. The frozen plan and
old current-status bytes remain recoverable; historical evidence was not rewritten.

Five existing mocked SDK usage cases passed, distinguishing missing, null, zero,
mismatched and matching incomplete usage. This validates local classification,
not the remote root cause. Documentation checks passed 5/5; closeout-script Ruff
and diff checks passed. No runtime code changed, and no new full-suite claim is
made. Preparation's quick/mock results and its preserved historical prompt-check
failure remain as recorded in the frozen specification.

Keep the transition rules, two references, budgets and history opt-in unchanged.
The old helper-to-task inference failure recurred in A1; whether the three changes
prevent it remains unresolved. No treatment improvement, adoption or new prompt
change follows from this interrupted comparison. Any future paid work needs a new
scope after diagnosing the usage inconsistency; this closed allocation cannot be
resumed or silently replaced. No further paid execution is queued.
