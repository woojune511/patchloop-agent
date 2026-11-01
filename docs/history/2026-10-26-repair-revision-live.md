# Revision pilot: source hypothesis revised, replacement exception, no submission

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-26
- Verification Status: LIVE_EXECUTED; PUBLIC_EVIDENCE_ANALYZED; REPAIR_UNVERIFIED
- Version Label: repair-revision-live-v1

Status: CLOSED after one authorized fresh solve. official=false; claim_eligible=false.
No retry, resume, replacement or transfer of the remaining allocation.

## Question, intervention and authorization

The [previous pilot](2026-10-26-trace-budget-live.md) delivered complete traces but
the next edit did not address the refuted source mechanism. This pilot asks whether
the [revision contract](2026-10-26-repair-revision.md) makes the real model revise
that mechanism, check its prediction or added test, and resolve the original failure.
Useful revision and verified repair are separate outcomes.

The user approved the [exact prepared scope](2026-10-26-repair-revision-live-plan.md)
with "실행해줘". The immutable authorization binds request
`sha256:fe05604d1c1c5dc867f0a9c0ecff3efe26d708390326acfe0772c18c95c7ae14`.
Preparation and prior closed records remain unchanged.

- Astroid-1333, `tasks/dev-train/current-dev20/13/public.yaml`.
- `gpt-5.4-mini-2026-03-17`, xhigh; credential
  `C:/Users/geonj/Documents/PatchLoop/.env`; repeat **1**, total cap **$1.20**.
- Normal/correction ceilings **40,000/25,000**; 40 model calls, 100 actions,
  four accepted edits, 1,800 active seconds and 1,920-second supervision.
- Frozen HEAD `0e3d8785001d4766634713afb42561b0509523c2`; runtime
  `sha256:e304d2de750e10c4e4b1b09fbfe29181c9a79f2893d5aaaf7fa6210f70026726`.
  This includes revision commit `98827233333823f7d44cacf6daffbd7f13b4974d`
  and the actual-task public pytest wrapper adapter. Other settings and prepared
  identities follow the plan; no task bytes, model or limits changed during execution.
- Preparation `C:/pt/repair-revision-live-ready-v1`; execution
  `C:/pt/repair-revision-live-v1`; solver `run_dev_cc37da21cc4a476f`.

This was a fresh solve without an operator patch, diagnosis or fixed caller seeded
into the model. One exposed-task run cannot establish a causal gain or generalization.

## Execution and repair evidence

| Model call / stage | Result |
| --- | --- |
| 1 | Original probe reproduced F0010; initialized control had no F0010 |
| 13 | Pre-edit original-call observation completed |
| 30 | First source edit accepted; automatic replay retained F0010 with different diagnostic text |
| 31 | Post-edit path diagnosis completed and refuted the expected original effect |
| 32 | No tool call; admitted 17,797 output tokens exhausted |
| 33 | Protected correction selected `targets=["tests"]`; rejected before test execution |
| 34 | Second source edit revised the mechanism and bound `original_failure_absent` |
| Automatic replay | Missing-initializer call raised FileNotFoundError; host judgment and prediction unverified |
| 35 | Public base-regression PASS: 1,231 passed, 69 skipped, 15 xfailed |
| 36-37 | No tool calls; both admitted output ceilings exhausted |
| Terminal | INCOMPLETE_RESPONSE; no finish, submission or isolated evaluation |

The caller used `pylint.lint.Run(["src/project"])`, with `src/__init__.py` and
`src/project/file.py`, from separate `/tmp/patchloop-case/bug` and `control` roots.
The control additionally had `src/project/__init__.py`. Its output was F0010-free
but not otherwise clean: C0114/W0611 produced exit 20. The original bug exited 1.
This differs from the preceding pilot's same-tree `["src"]` control; historical
results are not paired inputs. Direct Python API invocation under prepared
Linux/Python 3.9.25 does not establish shell/venv equivalence.

Both traces were complete under `selected_call_launch_thread`. Before editing,
coverage counted 31,317 global calls and 14 selected events; after the first edit,
31,816 and 14. Each retained 13 detail records, using 2,268 and 2,266 value bytes.
Neither hit a collection limit or omitted/coalesced events.

The first edit guarded `AstroidManager.ast_from_file`'s file-build path with
`os.path.isfile(filepath)`. It then fell back to module-name resolution. This
changed the actual path: the captured diagnostic moved from missing-file parsing
to `Failed to import module project`. The trace observed the new guard and fallback,
with AstroidImportError at line 126. The unobserved added lines 127-128 were a
redundant terminal raise after that failing call. Their absence does **not** mean
the existence guard or the whole repair mechanism was unexecuted.

Call 32 received the full returned trace exactly; call 34 still received the linked
factual refutation and import exception. The second explicit hypothesis acknowledged
that module-name lookup could fail when the source root was not importable. It
added a direct `_build_namespace_module(modname, [directory])` branch for a missing
package initializer. This is substantive source revision using the observed failure,
not merely attaching an evidence ID to the same patch.

The second replay entered the new namespace branch, including its return line.
However, the declared call then raised `builtins.FileNotFoundError` for
`src/project/__init__.py`, with empty captured stdout and no normal exit code.
The helper-authored F0010 booleans became false/false, but the host did not accept
that as success: comparison was `not_compared`, reason
`declared_call_unobserved_or_incomplete`, and prediction/original effect stayed
`unverified`. The record proves a target exception, not its exact downstream stack
location; no final stack trace or additional replay was collected.

The current diff's public regression passed in 9.50 seconds. This does not resolve
the failing original call. Registered-check line coverage was unknown because its
launcher was unsupported by that observer; unknown coverage is not non-execution.
No test was added. The selected comparison of `tests` was invalid because a Python
test file or pytest node ID was required. No paired children ran, so the actual-task
comparison wrapper and test-only historical-diagnosis reuse remain NOT_EXERCISED.

## Feedback and completion gap

The final exception exists in the durable call receipt, but not in dispatched
public inputs 35, 36 or 37. The audit checked all public message/state/tool-output
items, excluding reasoning items. These inputs had no native function outputs,
no `builtins.FileNotFoundError`, and `current_public_failure=null`; their
reproduction view retained `UNKNOWN` / `automatic_attempt_unverified`.

Consequently, it is unsupported to say the model saw and ignored the new exception.
There is a concrete projection gap between the captured invocation outcome and
the compact repair feedback. The host still preserved unverified status. After
regression passed, `ready_to_submit` meant candidate-return eligibility, and the
guidance explicitly required an assessment and said missing original evidence
would yield `unverified_delivery`. Finish was never called, so no final-delivery
classification or independent acceptance was produced.

The next question is how to preserve an unexpected target exception as actionable
current failure evidence, distinguish it from absent observation, and allow a
bounded response before regression/finish. Compact finalization context and adequate
completion funding are a separate concern. This run does not show that increasing
the configured 40K ceiling alone would solve either problem.

## Resource accounting and limits

- Settled cost **$1.199996700**, remaining **$0.000003300**; billing/counting known.
- Wall time **668.33 seconds**; 37 model calls, 38 input counts, 39 recorded
  actions including two automatic replays, and two accepted source edits.
- 19 searches, 11 reads, two model run_probe calls, one observe_original,
  two edits, one rejected run_tests and one run_check comprise the 37 dispatched
  model responses' requested actions. With the two automatic replays, the action
  journal contains 39 action receipts; the CLI reports 39 tool calls.
- Tokens: 1,240,196 input, including 455,936 cached; 128,357 output, including
  119,577 reasoning tokens. Reasoning tokens are part of output, not additional.
  No reasoning text was inspected.

| Call | Admitted output | Used | Outcome |
| --- | ---: | ---: | --- |
| 32 | 17,797 | 17,797 | Incomplete, no tool call |
| 33 | 25,000 | 2,182 | Correction produced rejected test selection |
| 34 | 40,000 | 32,869 | Second source edit |
| 35 | 4,385 | 3,314 | Public regression check |
| 36 | 4,677 | 4,677 | Incomplete, no tool call |
| 37 | 4,157 | 4,157 | Final correction incomplete, no tool call |

The single protected 25K correction was consumed at call 33. Its unused tokens
did not renew the reserve. The later correction used remaining per-call funding;
it did not receive another protected 25K allowance. The last two input contexts
were 39,131 and 37,206 tokens. Their outputs were entirely reasoning-token usage
according to metadata. This explains the immediate terminal condition without
claiming access to the model's private reasoning or why it failed to choose a tool.
There was no timeout, count/billing uncertainty or hard model/action/edit limit hit.

## Integrity, decision and evidence

The collector verified 124 frozen source/task/diagnostic files, unchanged runtime,
sealed command/scripts, 184 content-addressed objects and all journal chains.
Provider dispatches and action_id/input_hash pairs have matching settled receipts.
No cleanup failure, image acquisition, provider retry, operator feedback or additional
target execution occurred during analysis. The authorized post-submission assessor
returned NOT_RUN/no_submission, with zero checks or provider calls.

The result supports live uptake of the source-revision/prediction mechanism and
preserves its distinction between a prediction and original verification. It does
not support repair success or a causal benefit. Complete traces are no longer the
observed bottleneck here. The new target exception, its omitted compact feedback,
and final no-action generation are the unresolved failures. The test-addition and
reuse route remains locally validated only. This allocation is closed.

| Artifact under execution root | SHA-256 |
| --- | --- |
| collection.json | 3b5d73e364ab36bcdbb52b1275a96f1371c9e37e0024fc092644c51cad3eb42e |
| public-analysis.json | 77146597ebcf147bd1f7ce339f01e59f109189edc434af87a2226c939430d4fd |

User-owned changes and prior historical artifacts were preserved. The repository
closeout changes documentation only; runtime/local mechanism tests remain those
recorded in the preparation. Documentation layout tests: 5 PASS in 0.29 seconds;
git diff --check PASS. The external closeout receipt records these checks and the
documentation commit. Linux CI, independent acceptance, safety and general
improvement remain unverified.
