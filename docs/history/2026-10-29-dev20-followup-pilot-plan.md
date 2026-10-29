# Dev20 caller/test-guidance pilot preparation

Date: 2026-10-29. Prepared locally; no paid solve or candidate evaluation executed.
External plan: `C:/pt/dev20-followup-pilot-plan-v1/plan.md`; exact command:
`& 'C:/pt/dev20-followup-pilot-plan-v1/run.ps1'`. Approval remains pending for the
sealed manifest and the new USD9.00 allocation.

## Question and scope

The [implementation](2026-10-29-dev20-followup-implementation.md) restores public
caller capability and clarifies input comparability, expected behavior and test
construction. The prior [failure analysis](2026-10-29-repair-dev20-failure-analysis.md)
motivates two fresh attempts: current-dev20/13 Astroid-1333, then /9 pydicom-1694.
The first exercises caller availability/use; the second exercises test setup and
expectation choices under the same three-edit cap. A single Astroid attempt would
leave the second mechanism unexamined. No full-roster rerun is proposed yet.

Keep gpt-5.4-2026-03-05/xhigh, `.env`, USD4.50/task (no transfers), 20 responses,
40 tools, three edits, context60K/output40K/correction25K and 2,400 seconds including
390 for isolated evaluation. Keep public-checks-v1, thin, segmented-v1 and
completion-recovery-v1. Each starts from original source without prior repair,
observation, operator diagnosis or private feedback. No automatic retries.

Report original benchmark acceptance, public checks, submission, mechanism uptake,
cost and time separately. Historical outcomes are descriptive comparisons. This
two-task, development-exposed pilot cannot isolate individual feature effects or
establish repeatability/general performance. Continued failure after actual caller
use weakens missing availability as a sufficient explanation; no use leaves uptake
unresolved. Guidance delivery alone does not establish valid test expectations.

## Preparation findings and correction

The first local preflight stopped before any target/provider execution: current
adapter copies had changed, but their hashes in `private.yaml` still declared the
old bytes. The prior packaging test covered new package creation, not existing
packages. Commit `5e3a5c57` updates only the current twenty adapter hash declarations
and adds all-20 package loading to that test. Hidden test bytes, grading and closed
artifacts are unchanged. Both initial failed preflight attempts and the correction
remain in the new preparation journal; this was not a failed paid repair attempt.

Fresh Astroid caller preparation retains the previous Python3.10 image and every
existing dependency wheel hash. It adds pylint2.12.2 plus five-wheel total caller
closure (pylint, isort, mccabe, platformdirs, toml); no image is pulled or built.
pydicom reuses its verified Python3.12 dependency snapshot read-only. The older
Python3.9 caller snapshot was not substituted. Caller compatibility with the source
is still bounded evidence, not release-version equivalence.

Both generated first requests passed the guarded offline count/dispatch audit.
Astroid offers repository and dependency:pylint scopes automatically; pydicom keeps
repository scope. Both start with an empty diff and no earlier observations. The
synthetic token count is not a provider fit/cost measurement. Two ordinary public
operations and two small public test canaries passed; Astroid additionally imported
the pinned caller and inspected its signature. These preparation results are not
injected into model context and do not reproduce either task's bug.

Package admission tests: 2 passed, including all twenty current packages. External
batch-stop/accounting checks: 19 passed; summary separation checks: 4 passed.
Runtime validation from the implementation is reused because runtime bytes are
unchanged; package declarations and preparation scripts receive their own checks.
Exact hashes and review/validation receipts are bound in the external manifest.

## Execution boundary

Run-local JSONL and result roots remain outside the repository. Credentials are
checked for existence only during preparation. Execution requires a new affirmative
approval matching the manifest, then counts immediately before dispatch with zero
SDK retries. Count/transport/billing/execution/cleanup/identity uncertainty stops
remaining rows. A settled ordinary failure ends its row without extra budget.
Operator failure captures never feed the solver. If both runs pass, the failure-log
capture mechanism remains unexercised in this pilot. All previous allocations stay
closed; no defaults or performance claims are changed by preparing this plan.
