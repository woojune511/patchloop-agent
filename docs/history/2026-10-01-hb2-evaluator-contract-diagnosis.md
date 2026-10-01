# HB2 residual failure: evaluator contract mismatch

## Question and identity verification

The previous public replay passed three endpoint ownership cases for HB2 while
its isolated evaluation remained FAIL. This operator diagnosis asks whether that
residual failure is behavioral, environmental or a task/evaluator contract issue.
No new agent run or intervention was authorized or performed.

Verified all 313 hash-chained events for run_dev_1165bdf5982748dc, its saved
submission/evaluation artifact hashes and the workspace diff. Submitted patch:
sha256:3ebc37224e9e574f456630af2a0db98cc6cd88bc72aaa31ec64207825a189b96.
Current task hf-hub-xet-endpoint-propagation v5 matches all three envelope hashes
(public, private and complete package); complete task hash:
sha256:e6f04af5b239cbeebe8febe75bf8cbde4373abc215e2c8f0ba44b0ab0df95435.
There is no evidence of task drift or a different submitted patch explaining FAIL.

## Saved failure classification

Both public checks passed in isolated evaluation. Scope, dependency, test-tampering
and public API policy checks passed; safety PASS. The hidden command exited 1
with two failures and four errors, without timeout or cleanup failure. This is
not an observed import, Docker or resource problem.

Operator inspection of the frozen private receipt and evaluator source explains
every reported failing outcome. Four errors call the low-level parser with an
endpoint keyword that HB2 did not add. One assertion requires a fixed public
signature shape in that module. Another expects ambient endpoint rebasing when
the parser receives no explicit endpoint. No reference patch was read and none
of these private details was supplied to a coding agent.

The frozen public issue requires request-specific endpoint propagation through
metadata access paths while preserving callers without an explicit endpoint. It
allows public API changes but does not mandate a parser signature extension,
an exact signature hash or placement of rebasing inside that helper. HB2 instead
implements rebasing in get_hf_file_metadata and forwards explicit endpoint context
from the wrapper/download path. Its unchanged parser is compatible with this
implementation choice. The ambient-rebasing assertion also conflicts with the
public no-explicit-endpoint preservation rule, absent a declared helper exception.

Thus the residual rejection is explained by hidden implementation constraints and
an inconsistent default-context expectation. Do not interpret it as demonstrated
inability to distinguish explicit and ambient endpoints. This does not establish
complete correctness of HB2 or invalidate the known public errors in other HF rows.

## Bounded public replay

Before execution, froze a six-case replay using the existing public fixture and
saved submitted source: explicit custom endpoint, no explicit endpoint under an
ambient custom setting, and foreign route preservation, each with header and Link
metadata. The first three conditions extend the earlier public-only diagnostic
across both publicly supported carriers. The operator had already inspected the
private failure receipt, so this is not an independent holdout or blind review.

All six pass, with source import assertions and mocked HTTP responses. Source-only
snapshot contains no private tests/reference/Git state; its hashes were unchanged
after execution. Existing pinned image c698facf4c9a9e636b8dc114aa9bda6a17ee5f89fe3efd43f39a6543540e891f,
network none, read-only root/mounts, two CPUs, 2 GiB, 256 PIDs and 90-second timeout.
One replay completed at exit 0; container removal was confirmed. No images pulled
or built, Docker startup, credentials, provider calls or new private evaluation.

This replay does not prove all metadata/download behavior, or that every public
requirement is satisfied. It provides no public repair-defect reproducer within
the selected cases. The private receipt independently explains the recorded FAIL.

## Decision and next engineering work

Preserve the original FAIL, task v5 bytes, panel results and all earlier reviews.
Do not silently recalculate historical success rates or relax runtime acceptance.
The earlier statement that HB2's residual cause was unknown is superseded only by
this separate diagnosis. Keep the agent baseline unchanged.

The next justified change is task-level evaluator alignment: a new version should
test endpoint behavior at declared public entry points without requiring one
internal implementation. Calibrate it against the clean base, saved overbroad
repairs and independent wrong-behavior controls; retain hidden evaluation and
public/private separation. First make the no-explicit-endpoint rule consistent
throughout that contract. A passing saved-patch replay under such a new version
would remain post-run operator evidence, not another successful agent solve.
This diagnosis does not create that version or authorize a paid rerun.

## Evidence and validation

New record: C:\pt\analyses\hb2-failure-diagnosis-20261001-v1,
runs/run_dev_hb2diagnosis.jsonl. It binds parent journal/task/patch, public fixture
and diagnostic hashes, complete source inventory, Docker receipt and classification.
Parent evidence: C:\pt\boundarypair0928b\state\HB2.
Earlier [public replay](2026-09-29-boundary-discrimination-replay.md) and
[development review](2026-09-30-development-review.md) remain immutable.
Documentation-only repository change; layout/link/size and whitespace checks run.
Runtime/full-suite/mock tests are not required for this diagnostic record.
