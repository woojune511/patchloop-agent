# Rapid R8 completion-policy candidate and result evidence — 2026-08-23

This archive records the public-development promotion of offline Lean Harness V7 into a fresh Rapid identity. It does
not alter or retry consumed R7, and it grants no Docker, evaluator, provider, paid or live-runtime authority.

## Frozen comparison

R8 keeps R7's AnyIO-v4 public task, `gpt-5.4-mini-2026-03-17`, no-memory condition, split
1,000,000-input/100,000-output/1,100,000-total-token budget, three balanced pairs, `$7.20` full-schedule reserve and
`$7.50` hard cap. The baseline remains `v2/phase-evidence-v5`; only the Lean arm changes from V6 `v10/v16` to V7
`v11/v17`.

The candidate binds the consumed 8,428-byte completion qualification at file/content
`sha256:79659122825b9d03c66f3cca627c5c37674d6b0cc3d05b1dbd81c973ca2f4bcd`/
`sha256:f044c96f65fe90f6e858df5a063593549343ce8dfdd0b7bb94f0cf95e8436ed3` and scenario set
`sha256:931d1c6f6fa189678a211f674e769ed62d950e845063b4f3e78d92336e90a915`. Five of its six qualified source files are
byte-identical. The sole permitted transition is `patchloop/contracts.py`, which adds the exact R8 `v11/v17` live
identity; no task, evaluator, runtime-policy or qualified behavior source drift is admitted.

## Candidate-v11

The write-once candidate is 16,596 bytes:

- file SHA-256: `sha256:ac1466bbb5c1ad449676d4c97246e5078328ea48a8fd4c6ca6eb575e9461a200`
- content hash: `sha256:79539c739d9343bd43c65bb843598bae6bc491c2f4323740e138602bda17615d`
- execution hash: `sha256:553f7cfca404df2985fe5a79b267738c4e63afadd2997c9451e1fc35328faa74`
- runtime/config/schedule hashes:
  `sha256:7c1f3b3e4a3873e34325ecf2c4646743ce487a97a3645139e6bfc180ecd560aa`/
  `sha256:448c2ec2ceb10221e265624980c87a5dd25fd0c46b489021f08d7d5ff79d1987`/
  `sha256:d9db8467f16c85ee76d3c4d6f3474d6b145c82a7ce3f00b9c151a0d2da6f60c5`
- cost-control hash: `sha256:a7bc2f24b7ec0ecb501130ef310f958b790108d5788d51dfad958c2cf4691605`

It binds consumed R7 candidate/result files at
`sha256:9a0e783919cb30bb660c4bff87e7e62920be7e4f1838ecb25fba6cca14f924e2` and
`sha256:4a37bcbee2090ed83937432e717f8291ad6bc2784f06e1b53162fbfef495858b`. It records
`source_qualified=true`, `execution_authorized=false`, zero provider/Docker calls and zero added cost.

## Production-order no-call rehearsal

The central registry admits plan-v11 and all six manifests once, then issues typed one-use row capabilities. The
rehearsal traverses the batch-start prefix, blocks at row 1's provider-dispatch boundary, records a realistic resolved
terminal and inter-row transition, then blocks again at row 2's provider-dispatch boundary. The R8 receipt binds only
its exact verifier entry (`sha256:e885adac2d9924605d8d72d76776ef549cb9a05805e3a0a8b0f3b7c4caab5989`), so later unrelated registry additions
cannot invalidate it.

Two consecutive rehearsals produced byte-identical stdout and the same 3,076-byte receipt:

- file SHA-256: `sha256:a71b7f74ce0ae9b9c6f861d0d9efaf6fe810fd61d409f3c641a1b39b1905ef4a`
- content hash: `sha256:55c44f5407b018f483694978e49b051cc28e35c98498746d3d3c6310f7b31b8d`
- plan hash: `sha256:843ba162f0fce937196cb64b3aad7a84f7d73010ef32c2472cd02ea0d7bbd96a`
- provider/Docker/task/evaluator calls: `0/0/0/0`; added cost: `$0`

Consumed R7 keeps its historical full-registry hash
`sha256:631471e4beda0f4e2f399f7130890cd92bb63fcf0814d5d73cd0b3478ee22577`; its candidate, rehearsal and result bytes were
not modified. This compatibility path passed all 12 R7 tests, and the existing Rapid v4-v8 registry suite passed all
60 tests.

## Consumed six-row result

The exact approval was consumed once. All six rows started and settled without a harness-admission or infrastructure
failure. The append-only bundle has eight events (batch start, six row terminals, batch completion) and is 9,567 bytes:

- file SHA-256: `sha256:5d05e062a32ed4d912fdde93f7ee4048f118f461f888d1516fbb82b7d6e9ce9c`
- terminal content hash: `sha256:a9ce3a74b3c1c22bde88910c0b43f4f66443eb9e58d12034e1763377aa5765dc`
- started/admission-failure/evaluator/submission/success: `6/0/0/0/0`
- model/tool calls: `277/444`; settled cost: `$5.30250600`

| Order | Arm | Rep | Terminal | Output/reasoning tokens | Model/tool calls | Cost |
| ---: | --- | ---: | --- | ---: | ---: | ---: |
| 1 | baseline V2/V5 | 1 | agent failure, token terminal | 88,588/82,775 | 56/97 | `$1.01136750` |
| 2 | Lean V7 | 1 | agent failure | 100,000/94,115 | 42/54 | `$0.82818450` |
| 3 | Lean V7 | 2 | agent failure | 100,000/95,166 | 29/41 | `$0.73666350` |
| 4 | baseline V2/V5 | 2 | agent failure, token terminal | 77,451/71,855 | 52/94 | `$0.94720275` |
| 5 | baseline V2/V5 | 3 | agent failure, token terminal | 76,460/70,594 | 57/103 | `$0.91730550` |
| 6 | Lean V7 | 3 | agent failure | 99,481/93,471 | 41/55 | `$0.86178225` |

Baseline cost/model/tool totals were `$2.87587575`/165/294; Lean totals were `$2.42663025`/112/150. Lean used fewer
input tokens (1,438,621 versus 2,734,323) but more output and reasoning tokens (299,481/282,752 versus
242,499/225,224). Both arms failed 3/3 before evaluator or submission, so these are descriptive efficiency and
terminal-path observations only, not a quality improvement.

## Validation and authority boundary

The R8 module's 13 focused tests pass, including exact candidate/receipt/result binding, the eight-event hash chain,
consumed-retry rejection, six-manifest admission, entry-hash growth
stability, one-use capability rejection, no-call rehearsal, pre-approval rejection and a fully mocked live-admission
boundary. Relevant contracts, Lean runtime, completion qualification and R7/R8 regression tests also exited zero;
source-tree Ruff, `py_compile` and `git diff --check` passed.

An exploratory mixed gate also exposed two historical-current-source suites that are not R8 candidate gates:
`test_r8_completion_correction.py` rejects the now-changed historical held-out source binding, while
`test_r7_offline_contract_chain.py` still freezes an older 26-package inventory and held-out contract template. They
were not weakened or used as positive evidence here. The R8 candidate instead binds the current source directly and
its own predecessor, qualification, admission and artifact tests pass.

The result remains `official=false`; external and confirmatory claims are unauthorized. The candidate, rehearsals,
approval and bundle are consumed and cannot be rebuilt, retried, resumed or relabeled. No current provider, Docker or
cost authority remains. The next valid step is a public-only, zero-call diagnosis bound to the exact result above.

## Public trace diagnosis and offline successor

That zero-call diagnosis is now complete. The 15,358-byte machine artifact at
`reports/rapid-development/artifacts/rapid-public-dev-anyio-completion-policy-20260823-r8-public-trace-diagnosis-v2.json`
has file/content `sha256:419b42b8188f0efbaa228f711a1d963e8c945d56936d7a95c519f87b6480dddf`/
`sha256:021af168a0fb1fb699641a6689fb5089c5f91780065cf215d5c95552ea682898`.

Public evidence separates three mechanisms. The task is materially coupled but not impossible: the same model, task
and 100,000-output cap produced one baseline success in consumed R7, while baseline success across R7/R8 is only 1/6.
V7 then amplified non-convergence: after each Lean row's first mutation it made no read/search call, 46 of 63 edit
calls failed, no diff passed both visible checks, and 14 upstream checks still ran after the targeted check failed.
Affected request contexts carried two to eight full edit-correction occurrences; retaining the latest once saved
356,077 JSON bytes over 63 contexts in an offline projection. No hidden/private/reference artifact, reasoning text or
LLM response text was read.

`patchloop/agent/completion_loop_successor.py` implements a pure opt-in projection: one check per response in task
order, targeted-before-upstream gating, current-source refresh before correction, structured-edit preference,
latest-correction-only context and 2,048/4,096/8,192/2,048 target ceilings. Its terminal-attribution projection
classifies an explicit incomplete status before an absent-usage mismatch while preserving both facts. Focused tests
pass; neither change is runtime-wired, externally executed or evidence of improved agent quality.
