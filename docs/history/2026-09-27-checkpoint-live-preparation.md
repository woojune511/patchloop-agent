# Live checkpoint collector preparation, 2026-09-27

## Problem and scope

The frozen N1 first-post-probe A/B inputs and offline restoration were available,
but a live comparison still lacked separate invocation accounting and environment
admission. The open hypothesis remains whether the current mutation recommendation
contributed to a premature repair. This preparation does not answer that question.
Earlier native-history exposure and other mutation cues remain in both arms.

## Change

Added `diagnostics/checkpoint_comparison.py` and its hidden contract. The collector
shares restoration and first-input verification with the offline continuation,
without changing production runtime or the frozen input-pair implementation.
It binds task, model, credential path, implementation, HEAD and first request hashes
in an external manifest. Four independent continuations run A1/B1/B2/A2.

Historical settled usage remains in each branch's budget/context but is excluded
from the new invocation ledger. Each row retains $0.967463 of original allowance;
the proposed new total is $3.869852. Unused prior allocations remain closed. Both
ledgers must admit the next counted request; no row can borrow another's allowance.
First count/dispatch must use the frozen input exactly. Later turns, registered
tools, checks, finish and isolated evaluation use the ordinary runtime.

An atomic fresh result root prevents automatic resume/retry. Count, transport,
usage, continuation or cleanup uncertainty stops all remaining rows. Unknown billing
is null, and unexecuted rows are NOT_RUN. Known ordinary row cost exhaustion may
advance to the next planned row. Unexpected usage above a reservation stops the
group and is not misreported as proof of compliance with actual billed cost.

Standard short-context GPT-5.4 rates were checked in the official
[pricing documentation](https://developers.openai.com/api/docs/pricing): $2.50 input,
$0.25 cached input and $15 output per million tokens. Existing runtime pricing
matches; service tier remains default, global endpoint and zero SDK retries.

## Environment result

Read-only admission verified current tracked task/runtime, exact credential path
existence (without reading contents), prepared source, and selected pytest dependency
bundle integrity. The dependency manifest remains
`sha256:ae8d0a01dd8c67305ea620a885a75c73344979104f6d067e83dc3aebc79f143e`.
Docker was unavailable. Status: PREFLIGHT_FAILED. Evaluator/probe image readiness,
provider acceptance, live comparison and task acceptance/safety are NOT_RUN.
No Docker start, image pull/build, real token count, provider dispatch or new charge
occurred. This infrastructure block is not a model problem-solving failure.

External packet: `C:\pt\analyses\checkpoint-live-comparison-20260927-v1`.
The manifest proposes fresh live root `C:\pt\mutationlive0927a`; that root is not
consumed or created by preparation. Preparation records are not paid authorization.
The manifest and preflight are bound by the preparation's append-only dev-run-v1 journal.

## Validation and evidence limits

- Collector tests: eight passed in 18.21 seconds, including a four-row synthetic
  collection with first-row repair/check/finish/isolated acceptance, exact first
  inputs, separate cost accounting, single-use enforcement, authorization identity,
  and count/transport/usage uncertainty. Three read-only admission tests additionally
  passed in 0.86 seconds (ready, unavailable Docker, mismatched probe profile).
- Shared offline continuation: six passed in 21.39 seconds, covering both arms,
  mutation/check idempotency, failed visible checks and uncertainty.
- Input-pair, public mutation projection and completion-cost regression group:
  68 passed in 43.60 seconds. Full repository test suite was not rerun.
- Ruff and five documentation layout/link tests passed. Mock smoke reached
  EVALUATOR_PASS; Docker safety remains NOT_RUN. Smoke root:
  `C:\pt\checkpoint-live-smoke-0927a`, run `run_dev_f6fe7d9f8f314f21`.
- Durable JUnit reports: `C:\pt\validation\checkpoint-live-complete-0927c.xml`,
  `checkpoint-live-env-0927a.xml`, `checkpoint-live-fast-0927a.xml` in the same directory.

Production runtime remains
`sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.
The prior frozen input-pair packet validates unchanged. Closed history, reports,
experiments and prior run stores were not edited. Earlier offline audit hashes
describe the earlier helper implementation; this shared-helper refactor is a new
change, not a rewrite of that audit.

## Next question

Restore Docker availability explicitly and repeat read-only admission. Only after
readiness and exact separate task/model/credential/repeat/cap approval may the
collector test provider acceptance and the local mutation-advice hypothesis.
No baseline/default adoption or general efficacy claim follows from these tests.
