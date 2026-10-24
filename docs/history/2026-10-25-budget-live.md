# Cap-only fresh solve: edits and submission, original failure remains

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run, followed by public receipt analysis
- Origin Date: 2026-10-25
- Verification Status: ANALYZED; live execution and separate public checks completed
- Version Label: budget25-live-v1
- official=false; claim_eligible=false; allocation CLOSED

## Problem, question and decision

The [previous observation pilot](2026-10-25-observation-live.md) acquired the
original failure/control but made no edit after 19 inspections. Calls 22 and 23
received only 18,107 and 10,657 output tokens under the USD 0.88 cap; call 1 also
exhausted a full 25,000-token allowance. This made a cap-only diagnostic useful:
can additional headroom carry the same agent into a repair and verified submission?
Cost pressure was a plausible contributor, not an established sole cause.

The new run reached two edits, a passing public regression check and submission.
Every model call received 25,000 output tokens and none was incomplete. However,
the submitted patch retained the original F0010 failure. The frozen public
failure check and registered independent acceptance both failed; the normal-input
control and sandbox safety passed. Integrated repair success was not achieved.

Do not increase the cap automatically again. The next question is whether the
repair hypothesis changes the original caller's failing path before submission.
Separately, observed call-identity drift prevented a comparable completion verdict.
One stochastic run per condition does not establish that the cap caused progress.

## Authorized design and preparation

The user approved the preceding cap-only recommendation with
`그럼 그렇게 실험해줘`. A new request-bound approval was recorded; no prior allocation
was reopened. The only request changes were `max_cost_usd` and a fresh state root.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333, dev-train.
- Model: `gpt-5.4-mini-2026-03-17`; reasoning xhigh; output ceiling 25,000.
- Credential file: repository `.env`; contents were not logged.
- One fresh solve, USD 1.20 invocation cap, 40 model calls, 100 actions, four
  accepted mutations, 1,800 active seconds and 1,920-second outer supervision.
- Same segmented-v1, result-or-size-v1, brief-v1, probes/none, bounded-v1 acquisition,
  repair-recheck/protected-v1 and completion-recovery-v1 policies.
- Same prepared source, dependency manifest, local images, public programs and
  grader. No seeded probe, old solver context, operator hint or private evaluator
  content entered the agent. Zero SDK retries; no automatic resume or replacement.
- Up to two frozen offline checks on the full submitted patch shared 120 seconds.
  Count/transport/billing/cleanup uncertainty or frozen-source drift stops work.

Executed from `C:/Users/geonj/Documents/PatchLoop`:

```powershell
uv run --locked --offline python C:/pt/budget25-live-ready-v1/supervisor.py
uv run --locked --offline python C:/pt/budget25-live-ready-v1/assess_submission.py
```

Runtime commit at dispatch: `259a6fb2e3fdedb263da4c4e1703b21edb48ffce`.
The runtime content hash remained
`sha256:6dd1cad5aeb16063857c28bb5df099cf52c75debb471d1ba1c57ba42ce5aaef1`,
identical to the baseline implementation at `be874225`.
Request hash:
`sha256:99708ec4bc66210be8777b59a91270e8d987026d7dd63eb9e6fef59d33f4e629`.

Preparation verified 111 source inputs, source/dependencies and existing local
Docker images, a stubbed exact CLI roundtrip and two synthetic assessment skip
branches. No provider/count requests or containers ran during preparation.
The unchanged runtime retains its [prior split validation](2026-10-25-observation.md):
271 selected cases, including 35 observation controls, Ruff and isolated mock
evaluation. These were not rerun as new runtime tests for a cap configuration change.

## Observed comparison

| Measure | Previous USD 0.88 sample | New USD 1.20 sample |
|---|---|---|
| Run | `run_dev_3f0132d090d04653` | `run_dev_8302ca202b3544e6` |
| Settled cost | USD 0.788844900 | USD 0.821097150 |
| Solver wall time | 517.658 s | 655.403 s |
| Model / input-count calls | 23 / 25 | 30 / 31 |
| Output allowance | Reduced on final two calls | 25,000 on all 30 calls |
| Incomplete responses | 3 | 0 |
| Original failure/control acquisition | Acquired | Acquired |
| Inspections before first edit/end | 19; no edit | 24 before first edit |
| Accepted edits / submission | 0 / NOT_RUN | 2 / submitted |
| Required public regression | NOT_RUN | 1,232 passed, 69 skipped, 15 xfailed |
| Frozen public failure / control | NOT_RUN / NOT_RUN | FAIL / PASS |
| Independent acceptance / safety | NOT_RUN / NOT_RUN | FAIL / PASS |
| Terminal | INCOMPLETE_RESPONSE | EVALUATOR_FAIL |

The new run used 32 actions: 14 searches, 11 reads, two replacements, one public
check, one finish and three probes (original, helper and automatic completion
replay). Mutation was offered from model call 3; the first edit came at call 26.
The public regression ran in 8.51 seconds. Separate public assessment took
16.396 seconds. The solver process exited normally with known billing/counting.
USD 0.378902850 remained when this one-run allocation closed.

Token totals were 1,256,219 input, including 718,592 cached input; 80,885 output,
including 69,461 reasoning output. Reasoning is a subset, not an additional charge.
The actual cost increase was USD 0.032252250. Different stochastic trajectories,
including different early responses, prohibit attributing that difference or
the stage progress solely to the cap. Cap changes also alter funded policy horizons.

## Repair hypothesis and verification gap

The helper probe observed an ImportError from `modpath_from_file` while a supplied
search path let `file_info_from_modpath` identify a namespace package. The model
changed `check_modpath_has_init` in `astroid/modutils.py` to use that path-aware
module specification and added a direct helper regression/control test in
`tests/unittest_modutils.py`. The public regression passed on the submitted diff.
That did not establish correctness of the original `pylint.lint.Run` call.

The final model assessment acknowledged that the exact caller had not been rerun
and relied on automatic replay at finish. That replay returned the same observation
as the baseline: `{"bug_has_f0010":true,"control_has_f0010":false}` with complete
per-call capture. No provider call followed the replay. Its failure observation
and changed-line feedback therefore did not enter another repair turn.

The public launch-thread line collector observed entry to the added `base_path`
assignment, but not the new resolution branch at lines 269-273 of `modutils.py`.
This supports investigating whether the edited branch addresses the caller path;
it is not complete branch coverage or proof of nonexecution in all processes.

The exact full submitted patch was separately checked with frozen public programs:
the missing-initializer case had caller exit 1, F0010 and no analyzed child; the
normal control had exit 0, no F0010 and an analyzed child. Independent acceptance
also failed. Only its registered status was read, not private tests or reference
patches. Sandbox safety PASS is separate from task correctness.

## Completion identity limitation

Original acquisition was qualified, but completion remained `unverified` and the
submission was `unverified_delivery`. The baseline and candidate used the same
frozen program, normalized target arguments and selected input content hashes.
Their call-condition hashes differed at six paths: each call's runner argv length
and selected HOME/PYLINTHOME value hashes. The candidate's host line tracing added
`/opt/patchloop/line_request.json`; each execution generated a different temporary
root for the two environment variables. Current identity includes these fields.

Thus the completion projection could not treat the candidate as a comparable
REFUTED/SUPPORTED case, even though the raw candidate observation retained F0010.
The independent frozen public failure check supplies a separate failure result.
Neither historical observations nor the completion verdict were regraded. Target
setup identity versus host instrumentation needs a separate investigation.

## Evidence, integrity and limitations

Preparation: `C:/pt/budget25-live-ready-v1/`; results: `C:/pt/budget25-live-v1/`.

- `collection.json`: `sha256:06233f55c56ac3b4d57d138b8bfa6e407518d27d461341984b0f357b82e54850`.
- `public-analysis.json`: `sha256:8efe4426993662e146b020423a16caf713b174e9fa1374b9a8448e9ec50b41a9`.
- `diagnosis.json`: `sha256:72ce08d29914a4314c2181c05ed851128fb39ba79647faabeac298419733eb40`.
- Submitted patch: `sha256:e93c514d972f0ee8352cc04037d277a02e5c9dc0c44cc8f598072b7b9fe85a6a`.
- `process-result.json`, `cli-result.json`, `public-assessment.json`, approval,
  source-bound preparation/solver/operator journals and CAS retain the receipts.

Collection checked hash chains, 166 CAS objects, all 32 action/input-hash pairs,
30 settled dispatches, cleanup flags and unchanged frozen runtime/task inputs.
Provider reasoning contents were not inspected. No extra solve or target replay
was added after the authorized two public checks. Historical artifacts are intact.

All 11 interpretation-fallacy categories were checked in `diagnosis.json`.
This selected, repeatedly exposed task and one stochastic sample per condition
support stage-level observations, not a causal repair gain, success rate estimate
or generalization. The decision is to preserve this failure and investigate
original-caller feedback before submission, with call-identity drift kept separate.
