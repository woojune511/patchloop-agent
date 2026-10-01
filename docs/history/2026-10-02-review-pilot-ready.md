# Revised review pilot approval proposal

Date: 2026-10-02. Provider-free preparation following the
[completion/accounting fix](2026-10-01-review-completion-contract.md).
Status: READY FOR EXACT-MANIFEST APPROVAL; NOT AUTHORIZED FOR PAID EXECUTION.

## Reason and fixed comparison

The first allocation stopped before producing a reviewer report and could not
compare review procedures. The observed missing horizon and partial-accounting
defects are now corrected and locally tested. This supplies a concrete reason for
a new bounded comparison; no repair-quality advantage has been established.

The proposal retains the four original dev-train checkpoints and fixed orders:

| Task | Order | Evaluation |
| --- | --- | --- |
| original-opensandbox-816 | C/A/B | v1 plus frozen public matrix |
| original-isort-2491 | A/B/C | v1 plus frozen public matrix |
| original-pyinfra-1679 | B/C/A | original v1 retained; separate v2 |
| original-conan-19735 | C/B/A | v1 |

C is ordinary continuation; A reviews with the original trajectory; B reviews
the public factual context without that trajectory. A/B reports return to the
original repair context. Both now receive their remaining review allowance and
must use the final call for finish_review. No extra call is granted.

One repeat per condition gives twelve new episodes. Model:
gpt-5.4-2026-03-05 / xhigh / 25,000 output tokens. Credential file:
C:/Users/geonj/Documents/PatchLoop/.env. New cap: USD 2 per episode, USD 24 total.
Each episode has 900 active seconds, 16 calls, 48 actions and two new accepted edits;
review consumes up to 180 seconds, four calls and twelve actions from that allowance.
Separate operator-only scoring has 300 seconds and no model calls.
The [protocol](../../.agent/review-context-pilot.md) retains adoption criteria,
private-evaluation separation and stop rules. No retries, resume or replacements.
The prior allocation remains closed; its completed C result is not reused as a
new control observation. Scoring cases and task selection were not changed after
the stopped pilot; this remains an exposed, outcome-selected development panel.

## Frozen identities and executed admission

Manifest: C:/pt/analyses/review-pilot-ready-20261002-v1/manifest.json.
SHA: `sha256:8822888faab6122852f00c6eefc9566a89968ca7936c6c00a58fb67778cb6d59`.
Fresh future result root: C:/pt/runs/review-context-pilot-20261002-v1.
Driver: C:/pt/review_pilot_ready_20261002.py.
Executing preparation commit: `4c94f8e0`; implementation commit: `a1ecfa6b`.

The driver compared the entire proposal with the prior execution manifest.
Only the result root and four bound implementation/protocol hashes changed.
Source checkpoints, candidate hashes, task/evaluator packages, scoring programs,
runtime, model settings, prices, row order and resource caps matched exactly.
All original source identities were revalidated by the builder. The old manifest
was checked byte-identical after preparation.

Exact-manifest reconstruction and tracked-clean implementation checks passed.
All four source/evaluation/probe environments returned READY using existing local
images and dependencies. Credential loading was explicitly blocked. No provider
calls, credential-content reads, image acquisition, evaluator execution or paid
result-root creation occurred. Admission will run again before future dispatch.

The unchanged implementation already passed 62 focused tests in 100.88 seconds,
3,904 full local tests with 16 skipped, Ruff and mock isolated evaluation. This
preparation is identity/environment evidence; it does not prove live report quality,
repair improvement or generalization. Paid execution requires a new explicit
approval of this exact manifest and cap.
Preparation documentation passed all five layout/link tests and git diff --check.
