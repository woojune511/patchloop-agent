# Trace-budget pilot: complete observations, original failure persists

Status: CLOSED after one authorized fresh solve. Updated 2026-10-26.
official=false; claim_eligible=false. No retry, resume or replacement.

## Question, intervention and authorization

The previous pilot reached its first edit but both traces were incomplete and
F0010 persisted. The [predeclared plan](2026-10-26-trace-budget-live-plan.md) tested
whether the [collector correction](2026-10-26-trace-budget.md) supplies complete
original-call evidence that the real model uses to repair the failure. Separating
collection, delivery, useful revision and repair matters: successful observation
alone does not establish the product's repair capability.

The user authorized the exact preceding scope with "실행해줘". A new immutable
authorization receipt binds request hash
`c0802c8d6246d55edf642f857fb0ebe83322ef293d2dece38604dcc8eb20d389`
(SHA-256). The closed preparation record and earlier allocations were not changed.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- Repeat 1; invocation cap $1.20; ordinary/correction ceilings 40,000/25,000;
  40 model calls, 100 actions, four accepted edits, 1,800 active seconds and
  1,920-second supervision. Other policies and prepared identities match the plan.
- Implementation `2c54996951b69e6d493e0522895a70c8404e2358`; frozen execution HEAD
  `2edfbbafc53bd421a345b6c98c1e0df0783e243f`; runtime
  `sha256:207d9b9e81ec10b3e013e7028520366d3103c2dea59a289307fba700b5125dda`.
- Preparation `C:/pt/trace-budget-live-ready-v1`; execution
  `C:/pt/trace-budget-live-v1`; solver `run_dev_433cab2f94dd4fed`.

This was a fresh solve without an operator patch, diagnosis or fixed caller seeded
into the model. A single exposed-task run cannot isolate causal repair gain.

## Observations

| Stage | Observed result |
| --- | --- |
| Call 1 | Original probe rejected before execution: question length outside 1-500 |
| Call 2 | Corrected request reproduced F0010; distinct control exited zero |
| Call 5 | Original-call observation executed; both coverage and detail complete |
| Calls 6-30 | Observation, prediction verdicts and event counts delivered in all 25 dispatched inputs |
| Call 30 | First source edit accepted at 557.70 seconds from supervisor start |
| Automatic replay | F0010 persisted; changed source lines were not observed |
| Call 31 | Whole-call post-edit diagnosis completed without collection limits |
| Call 32 | Diagnosis delivered; second accepted edit added a test, leaving source unchanged |
| Automatic replay | Same F0010 and clean control; new diff required path diagnosis again |
| Terminal | VERIFICATION_INCOMPLETE; completion cost admission blocked further work |

The original caller used `pylint.lint.Run(["src/project"])` from
`/tmp/patchloop-case`. Its fixture contained empty `src/__init__.py` and
`src/project/file.py`, with no project initializer. The control called `["src"]`
on the same tree. Original exit 1/F0010 and control exit 0/empty output persisted
across all five executions: baseline, pre-edit observation, first replay,
post-edit diagnosis and second replay. Program/binding and entire captured call
records, including cwd, arguments, fixture hashes and outputs, were identical.
Host and authored judgments agreed in every receipt.

This fresh caller matches the issue's cwd and relative target argument. The prior
run's `/tmp` plus absolute-target caveat must not be assigned to this run.
Direct Python API invocation under prepared Linux/Python 3.9.25 still does not
establish full shell/venv equivalence. The new control also differs from the prior
run's separate initialized directory; historical runs are not identical inputs.

| Trace | Global calls | Selected events | Detail records | Value bytes | Coverage / detail |
| --- | ---: | ---: | ---: | ---: | --- |
| Before first edit | 31,315 | 8 | 8 | 2,771 | complete / complete |
| After source edit | 31,321 | 15 | 10 | 3,446 | complete / complete |

Both scopes were `selected_call_launch_thread`; both had zero coalesced/omitted
collector events and no exhausted limits. Bounds remained 200,000 global calls,
200,000 selected events, 48 detail records and 8,000 value bytes. This exercises
the new collection path, but not repeat coalescing or sampled-detail behavior.

Before editing, `file_info_from_modpath` was entered once and raised ImportError,
matching one prediction. `AstroidManager.ast_from_module_name` had zero entries,
contradicting the other prediction under complete coverage. Both findings were
retained in the public inputs through the first edit. Return events during exception
unwinding do not imply normal returns.

## Repair interpretation and remaining defect

The first edit changed `_spec_from_modpath`: after a `PKG_DIRECTORY` spec is found,
an absent initializer now returns `PY_NAMESPACE`. Its explicit hypothesis names
the observed resolver, but the observation did not establish that this successful
discovery branch was reached.

The complete post-edit trace resolves that distinction. `_spec_from_modpath`
entered once and observed lines 607, 608, 609 and 617. Line 617 calls
`spec.find_spec(modpath, path)`; it raised ImportError before the new lines 632-633.
Thus function entry was real while the modified branch was irrelevant to this
failing execution. The original F0010 replay refuted the expected repair effect.

Call 32 received the diagnosis linked to the current diff, including exception
counts, observed lines and the unobserved changed lines. Its compact summary
omitted some detailed events, but `latest_tool_results[0].output.call_path` in the
actual dispatched input exactly matched the full returned trace. ImportError at
617 and 398 and `original_effect_refuted` were delivered, not lost in projection.
The next explicit hypothesis nevertheless treated the existing source fix as valid and added
`test_file_info_from_modpath_namespace_package_without_init` to
`tests/unittest_modutils.py`. It did not revise the source branch. The new test
supplies `path=[src]`, unlike the original caller's observed search path, and was
never executed or compared on base versus patch. Its expected PASS is a model
prediction, not evidence that it fixes or distinguishes the reported failure.

The second mutation receipt links the diagnosis, but that link does not establish
useful revision. Evidence supports partial uptake of the initial resolver finding;
the later public hypothesis does not reconcile the branch's non-execution and the
failed original replay. The current unresolved question is how observed failure
location and refuted predictions constrain the next source change or discriminating
test. Another collector or output-ceiling increase is not supported by this run.

## Resources and termination

- Settled cost **$0.944915400**; remaining **$0.255084600**, not transferred.
- Wall time **662.76 seconds**, about 11 minutes 3 seconds.
- 32 model calls, 33 input counts, 40 actions and two accepted mutations: one source
  edit and one test addition. No second source repair was attempted.
- 13 reads, 19 searches, five run_probe requests, one observe_original and two edits.
  Six probe-related requests comprised one rejection and five actual executions.
- Tokens: 1,116,624 input (479,232 cached), 95,762 output including 86,923 reasoning.
  Reasoning tokens are included in output, not added to it. No reasoning text read.
- No incomplete response or no-action protocol correction. The one correction
  credit remained unused. Calls 30/31/32 used 32,900/5,457/12,396 output tokens
  against admitted ceilings 40,000/14,408/13,575 respectively.

The final horizon required four minimum model calls but funded two. The unused
correction reserved $0.157500; each conservative successor reserved $0.045576
(60,000 uncached input plus 128 output). After correction reservation, $0.097584600
remained, enough for two such calls. Four plus correction required $0.339804.
Eight model slots and 60 action slots remained, so this was cost admission,
not the action count, timeout or an exhausted generation-output limit.

Releasing the correction reserve would arithmetically fund five minimum calls;
that counterfactual does not prove a useful diagnosis or repair would follow.
No reserve change or continuation was performed. Adding only a test changed the
full diff, triggered replay and left a new path-diagnosis obligation even though
the source was unchanged; whether that diagnosis can be safely reused is a separate
unresolved efficiency question.

## Evidence integrity, decision and limits

Preflight and collection verified 122 frozen source/task/diagnostic files, prepared
inputs, local image/profile identities and unchanged runtime. All dispatches and
actions have settled matching receipts; action_id/input_hash pairs and hash-chained
journals passed. Collection checked 166 content-addressed objects. No source drift,
timeout, unknown count/billing, transport or cleanup failure occurred. Zero SDK
retries, no image acquisition and no operator feedback to the solver.

Read-only analysis added zero provider calls and zero target executions. Registered
checks, selected tests, base/patch test comparison, finish, submission, the two frozen
post-submission checks, isolated acceptance and safety are **NOT_RUN**. The latter
checks were skipped as declared because no patch was submitted. User-owned changes
and previous evidence were preserved; only result documentation changes in the repo.
Documentation validation: `tests/test_documentation_layout.py` 5 PASS (0.09 s),
and `git diff --check` passed. Runtime tests were not repeated for this docs-only
closeout; the preparation record retains the prior core/quick/mock results.

| Artifact under the execution root | SHA-256 |
| --- | --- |
| collection.json | 51603893f8a0387c37bdc321ec56d1f93cd9bfb1420e9f1c315da1bb511255c8 |
| public-analysis.json | d7a59b2358403473080c9950dd9a5e84365f012812813f256fed0094c363684d |
| execution-findings.json | 61f2d35f74f43f3c88c935235be71bcf339f84bd46380039b06f8cdc03a37e5e |

The result preserves the collector correction as a locally validated mechanism
also exercised without truncation in this run. It weakens incomplete collection
as the main remaining explanation for this failure: complete evidence was delivered,
but the next change did not address the earlier exception. Original verification
correctly prevented a success claim. Repair improvement, independent acceptance
and generalization remain unestablished. This allocation is closed.
