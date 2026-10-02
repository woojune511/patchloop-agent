# SWE-bench Lite dev20 registration and batch preparation

Date: 2026-10-02. Provider-free work following calibration at `412edd73`;
official=false. See the [execution plan](../../.agent/swebench-lite-dev20-batch.md).

## Problem and decision

The remaining twenty Lite dev tasks were calibrated but lived only in external
draft directories, which cannot pass live tracked-source admission. Register that
fixed roster and prepare a bounded baseline measurement before seeking paid scope.
No agent intervention or causal comparison is proposed. The user requested this
preparation; the earlier USD 3.60 pilot allocation remains closed.

## Change and evidence

Copied each final effective package from
`C:/pt/analyses/lite-public-regression-contract-20261002-v1/final-summary.json`
to its exact task ID under `tasks/dev-train`. All twenty task-content hashes and
every copied file's bytes match the calibrated package. Generalized the existing
Lite Git attributes to preserve raw bytes for all Lite packages, including private
artifact inventories. Existing pilot packages are unchanged.

Prepared an operator-only manifest and one-shot batch driver under
`C:/pt/analyses/lite-dev20-registration-20261002-v1`. The manifest binds the exact
task, prepared-source, native-row and image identities. Registration evidence uses
an append-only hash-chained dev-run-v1 journal and content-addressed artifacts.
The provider-free preflight receipt is generated after commit, binding clean HEAD
task/runtime bytes and checking all twenty source trees, local evaluator images,
the pinned public probe image and credential schema without provider calls.

The paid proposal is one sequential fresh solve per task with
`gpt-5.4-mini-2026-03-17`, xhigh, 25,000 output tokens, the unchanged baseline policies,
USD 1.20 each and USD 24 total. No retry, resume, replacement, extra image acquisition
or budget transfer is included. Original native evaluation of submitted patches
remains required; hidden/reference material never enters solver context.

## Validation and limits

- Existing focused package/projection/native/prepared-source suite: 56 passed.
- External operator-driver controls: 9 passed, including exact twenty-task scope,
  one-shot execution, preflight drift, transport/count/billing/cleanup/evaluator
  uncertainty and exception stops. These use mocks and make no provider calls.
- Ruff passed. Mock smoke reached isolated acceptance PASS; safety NOT_RUN remains
  separate from a live safety result.
- Full cross-platform suite belongs to PR CI; no new runtime source was changed.
  Exact-head preflight and CI completion must be read from their receipts/status,
  not inferred from this preparation record.

Registration preserves all earlier calibration evidence, including eight corrected
images and two narrowly projected public regression checks. It supplies no new
agent-correctness evidence. No paid run or new allocation was approved or executed
in this preparation step. Next decision: approve or decline the exact proposed scope.
