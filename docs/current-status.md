# Current status

Updated: 2026-10-28. Runtime source owns behavior. Historical reports are evidence,
not an active queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies changes
and submits within bounded resources. Start improvements from observed failures.
Recovery, sandboxing and isolated evaluation support that product.

- dev-head is the sole mutable runtime; official=false and claim-ineligible.
- General baseline: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
- Selected policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- Limits: 40 model calls, 100 actions, four accepted edits, 1,800 seconds.
  Paid work also requires the exact task/model/credential/repeat scope and cap.
- Cross-run memory, held-out tuning and claim execution are disabled. Bounded
  run-local notes remain available. Historical Rapid executables are absent.
- These are selected settings, not CLI defaults or evidence of general accuracy.

See [guide](../.agent/guide.md), [operations](operations.md), [product](product.md)
and [evidence boundaries](evidence.md).

## Active decision

The [saved-candidate processing comparison](history/2026-10-28-file-processing-results.md)
locally observed the second and third Astroid-1333 candidates, with one real probe
per candidate and no provider calls. Both omit file.py during file enumeration:
project lookup raises ImportError, expand_modules falls back to is_namespace=false,
and get_module_files(list_all=false) returns no files from the init-less directory.
The selected list contains only the nonexistent __init__.py. Candidate3 changes
only its AST construction: an empty module replaces the exception, so F0010
disappears while file.py still never enters checking. The control file reaches
AST construction and actual checking in both conditions.

All selected trace calls close, with no overflow or callback errors. Exact original
call inputs, outputs, fixtures, image, dependencies and candidate snapshots match
the saved receipts. This supports the selection-before-builder diagnosis for these
two candidates; it does not establish a successful repair or benchmark acceptance.
W0611 remains an added processing witness beyond the public issue's error absence.

Keep the original processing check and failure delivery. The next repair hypothesis
should address module resolution and traversal, rather than suppressing the builder
exception. No production gate, repair, paid continuation or evaluation was added.
The [model trial](history/2026-10-28-post-reproduction-repair-results.md) had stopped at
three accepted edits, with context/output/time/cost remaining. Its final feedback
did not reach another model turn; whether one extra edit or earlier path evidence
helps remains untested. The USD4.13241570 allocation remains CLOSED.

New diagnostic tests pass. The broader quick run exposed three existing failures:
helper_recovery reads malformed purpose values as dicts (two cases), and one test
expects the obsolete invocation example. Runtime and those tests were unchanged
in this diagnostic. These must be addressed before calling quick validation green.
No new provider-backed execution is currently funded.

## Supporting evidence

- [Security maintenance](history/2026-10-23-security.md): refreshed host dependencies
  and public Python 3.12 images after the emSign incident. Old task/legacy images
  remain offline-only. New runs need newly prepared identities; prior manifests
  do not authorize execution against the updated runtime.
- [Helper-path results](history/2026-10-22-helper-path-results.md): useful information,
  no repair in A1/B1/B2; partial comparison stopped on drift. Allocation closed.
- [Invocation linkage](history/2026-10-22-probe-invocation-results.md): submitted
  repairs 0/3; ON mechanism use 0/2. Partial run; no adoption or quality claim.
- [Caller evidence](history/2026-10-19-caller-evidence-results.md): A/B 0/6;
  original-caller verification remained missing.
- [Portfolio remeasurement](history/2026-10-06-portfolio-dev20-results.md): 9/20,
  below the 11/20 threshold; test300 remains unprepared and unauthorized.
- [History](history/README.md) indexes the closed investigations and allocations.
  Their past next steps, settings and approvals do not carry forward.

## Execution and claim boundaries

All prior paid allocations are closed. The [older interrupted call](history/2026-09-28-expectation-review-results.md)
retains unknown billing; later settled allocations do not resolve it. The latest
source-ready diagnostic also retains one unsettled response.

Fresh solves, seeded repairs, funded continuations, saved-patch evaluations,
operator replays and scripted tests are different evidence. Do not pool them as
solve rates or expose private evaluator details to the agent. Public case support,
submission, independent task acceptance and safety are separate. Mock safety is NOT_RUN.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
uncertainty. Earlier saved candidates failed isolated acceptance; the clean-source operator
resolver candidate passes. The saved-evidence A model trial now passes acceptance;
fresh-solve and held-out improvement remain unverified.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
