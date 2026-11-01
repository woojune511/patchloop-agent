# Dev20 follow-up: caller readiness, failure capture and grounded checks

Date: 2026-10-29. Implemented with provider-free local validation; no live repair
experiment, saved-candidate reevaluation, or acceptance improvement claim.

## Problem and decision

The [failure analysis](2026-10-29-repair-dev20-failure-analysis.md) identified a
missing public caller dependency/source registration, cropped evaluation assertion
blocks, diagnostic input drift, self-selected expectations, and a failed new test
after mutation slots were exhausted. The user authorized proceeding. Changes
target these mechanisms without increasing overall budgets or adding a universal
reproduction gate. Exact private test expectations are not solver instructions.

## Task-owned caller capabilities

`PublicTask.caller_requirements` is an optional list of exact distribution/version
pins and explicit public source directories. Empty declarations serialize exactly
as before. Existing request fields and recovery envelope structure remain intact;
the task hash binds a declaration. Public metadata for current-dev20/13 declares
the caller version given in its issue and the public package directory.

Dependency preparation merges the task pins with explicit caller requirements.
It rejects conflicts and verifies the indexed public source before publishing.
Ordinary runs automatically merge task source registrations with additional
request scopes; no duplicated operator registration or guessed import root is
needed. Missing/wrong pins, absent source and conflicting overrides fail before
counting or dispatch. Existing dependency preflight detects changed bytes before
provider work. `execution_prepared` records the actual catalog and normal tools
expose it. This verifies availability, not whether the model chooses the caller
or whether importing it succeeds in every environment.

No dependency is downloaded or installed by run admission. Previously prepared
bundles that lack a newly declared caller must be prepared correctly before a
new live run. Historical plans and evidence remain unchanged and authorize no
run against the changed identities.

## Operator failure capture

`diagnostics/swebench_lite_oracle.py` keeps the existing 24KB per-stream tail,
full-stream hash and omitted-prefix fields. It additionally selects ordinary
uncolored pytest failure/error sections and unittest failure blocks, retaining
at most eight blocks and 12KB per stream. Oversized blocks retain their beginning
and end. Byte offsets, omitted/truncated counts and unclosed blocks make partial
coverage explicit. Unknown formats retain the old tail and report that no blocks
were recognized. Grading still consumes the original full output unchanged.

The current-dev20 twenty task adapter copies are synchronized to the updated
adapter; no reference patch, hidden test specification, grading rule or closed
result was changed. Fresh package construction is checked for byte-identical
adapter inclusion. Synthetic large-log tests check capture and envelope size.
The separate upstream grading report remains unbounded; this change does not
claim a universal whole-report size guarantee. Old cropped output cannot be
recovered without another evaluation, which was not run.

Private logs and new failure segments remain operator artifacts and are excluded
from model input and the public evaluator summary. Capturing a failure does not
make it a permissible repair hint.

## Guidance and mutation allowance

Existing tool descriptions now distinguish a comparable caller/input/setup from
a changed-input diagnosis, even if error strings match. Expected behavior should
come from the public issue or existing public conventions; a new assumption must
not become its own proof through a newly written test. Literal search syntax is
explained in the query field rather than only the path-glob description.

Additive-test descriptions and rejection messages suggest function-local imports,
which the existing policy already permits. They also disclose that all accepted
test edits use mutation slots and suggest checking setup/expectation before test
insertion when useful. No new mandatory fields, diagnostic execution, submission
gate or automatic action is introduced.

Review found mutation accounting consistent with its contract: one source edit,
test insertion and test correction are three successful mutations. Keep that cap,
completed-action idempotency and required-public-FAIL blocking. Exempting test edits
or silently granting another edit would change the experiment budget without
evidence that this is necessary. Local gateway coverage verifies shared-import
rejection, successful function-local import, and no extra charge on exact replay.

## Validation and remaining question

Evidence: `C:/pt/dev20-followup-local-v1/`, with hash-chained
`runs/run_dev_localfollowup.jsonl`, focused/quick XML and final validation receipt.
Caller tests forbid network and exercise real request construction using fake
provider/sandbox components. Log tests use synthetic failures and verify private
separation. The fast suite includes isolated mock evaluation. These demonstrate
local contracts, not live-model uptake or benchmark gains.

Parent validation: focused 46/46 passed in 26.702s; guidance 38/38 passed in 9.605s;
Ruff and whitespace checks passed. The 960-case quick suite took 390.870s:
951 passed, eight old description snapshots failed, and the operations page
exceeded its byte limit. Updated only the intentional description snapshots
(argument-shape digests and frozen arms stay unchanged) and shortened that page.
The affected five files then ran 74 cases in 37.912s: 73 passed, with the page still
six bytes over budget. A final documentation-only run passed 5/5 in 0.258s.
Every initial failed case has a later PASS; the passing 951 cases were not rerun.
The quick suite's isolated mock evaluation cases passed. Independent review found
no concrete caller/readiness defects. It did find superlinear regex backtracking
on a synthetic whitespace-heavy log line in the new capture. Replaced the header
matcher with linear byte-line scanning without expanding supported formats or
changing grading. Oracle revalidation passed 16/16 in 8.700s. The new 20KB whitespace
regression took 0.332s including subprocess startup, bounded by a five-second
timeout. The current twenty adapter copies were synchronized again; both sync
receipts are preserved. No outstanding review findings remain.

The implementation preserves allowed tools, original verification policy,
required public checks, total response/tool/edit/cost/time caps and fail-closed
uncertain execution. A new experiment would need freshly prepared dependencies,
new identities and exact execution/cost authorization. No paid run or evaluation
was started. The next empirical question is whether restored caller availability
and clearer evidence guidance change the model's repair choices under fixed limits.
