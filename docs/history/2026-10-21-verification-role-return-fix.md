# Selected public evidence on return from independent verification

Date: 2026-10-21. Provider-free correction to the
[blocked qualification](2026-10-21-verification-role-qualification.md).
Earlier qualification artifacts and verdicts remain unchanged.

## Problem and cause

At `c6c6e715`, the same two selected public probe exchanges reached repair in A
but disappeared in B (2/2 versus 0/2), although the request fit the size limits.
This made the proposed role comparison test a missing-evidence defect as well as
context separation. The report itself was delivered; selection failure or a
measured overflow did not explain the missing bodies.

The native journal view correctly excluded the verifier's conversation on return,
but the evidence lookup used that same view. It could no longer resolve selected
verifier actions. The report also called the source-only reference selector, so
tool-result references disappeared from its metadata. Generic report-delivery
tests checked the report object rather than the selected program/result bodies.

## Change

- The diagnostic controller derives quoted public exchanges only for the current
  question's selected verification results. It uses the original action, input and
  diff identities and removes owned note/plan interpretation envelopes.
- The runner accepts this explicit public evidence separately from native history.
  A continuing repair segment appends missing quotations; an ordinary new segment
  includes them in its existing optional-evidence manifest. Existing observations
  are deduplicated. The verifier's native reasoning and calls are never spliced
  into repair continuation.
- Report receipts retain both source and tool-result references in the existing
  two slots. They remain unverified assessments, not semantic acceptance.
- Actual byte/token overflow still follows the existing size transition and
  optional-body omission path. Omitted references remain `incomplete`; unknown
  counts stop before dispatch. Editing the candidate expires selection priority.

The phase triggers, result-or-size boundary, two references, 60,000 input tokens,
1 MiB request limit, 40 calls/100 actions/four edits, USD 0.88 row cap and shared
ledger/deadline remain unchanged. Unassigned runtime behavior is unchanged.
The role contract names `selected-public-exchanges-v1`, and execution bindings
include the return qualification tests, so earlier validation cannot authorize it.

## Local evidence and displacement

The regression fixture now delivers both selected program/result bodies in both
arms, with matching input hashes and complete delivery. B excludes an unselected
verifier exchange and verifier-authored basis text. A separate assembly at an open
repair checkpoint retains its segment identity while receiving both quotations.
Token and byte overflow fixtures omit the bodies only after measured overflow;
count uncertainty stops before the final request. The two probes execute exactly
twice, including when input construction is repeated.

Compared with the saved failing fixture, B gains exactly the two selected exchange
receipts. No previously delivered source line or public exchange is displaced in
this bounded example. Its request grows from about 89 kB to 108 kB; A remains near
109 kB. Exact bytes depend on receipt identities and are recorded externally.
This is a small public fixture, not a guarantee that larger reports never overflow.

The historical replay reconstructs all 89 stored requests exactly and verifies
374 source artifacts remain unchanged. All three A1/B1/B2 entry comparisons retain
equal common context and schemas, intended native-history contrast, and exactly
the previous source-displacement ranges (297/15/599 lines absent from B).
This fix changes return delivery, not the intended independent verifier's entry
history. The previous minimum-output funding result and its useful-output
limitation remain unchanged.

Final implementation receipts are kept under `C:/pt/verification-role50`:
`focused-final.xml`, `quick-final.xml`, `replay-final/`, and `closeout.json`.
The closeout binds the implementation and actual validation results; earlier
failed test receipts remain separate. Mock evaluation is isolated; no provider,
remote input-counting request, historical program or private evaluator replay was
performed. The user-owned AGENTS.md edit is preserved.

## Decision and remaining work

Keep the comparison's original limits and replace the defective public return
channel. Local delivery is repaired; model use, wrong-completion frequency and
actual repair improvement remain unmeasured. This scoped correction does not
claim a new full-suite qualification, frozen execution packet or paid allocation.
The final implementation full suite and sealed comparison qualification remain
required before execution freeze under the active specification.
