# Work Item 83 - R24 execution and halted public audit

Date: 2026-09-01 KST. This is an immutable execution/audit record, not current authority.

## Authority and entry

The user approved exactly candidate
`sha256:a4a8e75dfa0f1ae1365ef991b48cf18bd61f3dd717cf8d4d1bedff392236592e`, six AnyIO-v5 rows,
one pinned local image identity check, `$7.20` full-schedule reserve and `$7.50` hard cap. The approval allowed the
six agent/evaluator container paths and provider calls, but no image pull/build/tag/remove/prune.

Before entry, read-only validation recovered the stored candidate, rehearsal and qualification, matched the execution
and runtime hashes, checked the 3/3 V25/V27 schedule and cost contract, and confirmed that result, image receipt and
approved plan did not exist. No Docker or provider call occurred in this check.

The paid command was invoked exactly once:

```powershell
uv run --offline --frozen python scripts/run_rapid_public_development_v33.py `
  --mode execute --env-file .env --approve-live-cost `
  --approved-execution-hash sha256:a4a8e75dfa0f1ae1365ef991b48cf18bd61f3dd717cf8d4d1bedff392236592e
```

The process exited 0 after returning `batch-halted`. It was not retried or resumed. No separate Docker inventory,
pull, build, tag, remove or prune was invoked.

## Immutable execution result

- The shared image receipt records one inspection adapter call and one admitted local digest.
- Rows 1-3 started, returned one durable terminal each and settled exactly once.
- Rows 4-6 never started and received no row capability.
- Total settled model cost is `927549000` nanos, or `$0.927549`.
- Recorded input-count/model/tool calls are `43/42/41`.
- Evaluator reached/submission completed/success at budget are `0/0/0`.
- Cost is fully settled; the schedule is not fully observed.

| Order | Variant | Outcome | Cost nanos | Public terminal |
| ---: | --- | --- | ---: | --- |
| 1 | Lean V25 | agent failure | 240906900 | `SELF_DIRECTED_EXPLORATION_EXHAUSTED` |
| 2 | Lean V27 | agent failure | 459664650 | `WORK_PLAN_ADMISSION_REPEATED` |
| 3 | Lean V27 | infrastructure error | 226977450 | `APITimeoutError`, no typed code |
| 4 | Lean V25 | not started | 0 | none |
| 5 | Lean V25 | not started | 0 | none |
| 6 | Lean V27 | not started | 0 | none |

Bundle terminal reasons are `TERMINAL_CODE_NOT_ELIGIBLE`, `CHECK_FAILED_TERMINAL_STATE_ATOMIC`,
`CHECK_FAILED_TYPED_RECOVERY_TERMINAL` and `CHECK_FAILED_ARTIFACT_TRIAD_MATCHES`. These are continuation-policy checks,
not four independent runtime exceptions.

## Public trajectory diagnosis

Row 1 read `src/anyio/pytest_plugin.py` and `src/anyio/_backends/_asyncio.py`, using 6 searches and 4 reads. After
10 bounded information actions it still recorded a blocking ownership/lifecycle question and declared exploration
exhausted. It made no plan, mutation or visible-check call.

Row 2 recorded a valid initial plan. Its first structured-edit request was mechanically invalid; after a fresh read,
the second edit succeeded. The targeted check then failed with
`AssertionError: PUBLIC_CASE:anyio:test-resumed`. Two correction revisions were rejected with
`lifecycle_state_transition_unbound`, after which the one-retry gate ended the row.

Both row-2 revisions used owner component sets different from their state component sets, and each transition named
components absent from its owner set. Row 3's initial plan made the same two mistakes. The request schema exposes these
component identities as independent strings. Server admission correctly checks equality/subset relations, but the
feedback contained only the generic reason code and cspan/support-ID guidance; it did not return the mismatched
component sets. This is an observed machine-contract/feedback friction. It does not establish whether any semantic
hypothesis or proposed code change was correct.

Row 3's first invalid plan consumed the admission retry. The recovery request then recorded its 12th completed input
count and 12th context build, but no 12th `ModelCalled` event; `responses.create` raised `APITimeoutError`. Exact HTTP
request delivery/count and billing are not certified. The result, state terminal and artifact files were durably
present. General driver atomicity passed. Continuation policy separately admits only infrastructure terminals coded
`RECOVERY_ERROR`; the timeout carried no code, so its typed-terminal, continuation-atomic and artifact-triad policy
checks failed and no fourth-row capability was issued.

## Artifact identities

| Artifact | Bytes | File SHA-256 | Content/terminal SHA-256 |
| --- | ---: | --- | --- |
| approved plan | 14,028 | `sha256:550b57566c26d57047142f9c690002b1ff00185ded2ae6af431be3006ef05e14` | `sha256:d1260789ee9541cdae867fee5e6cf5771398c49a677cbc37df65b8eb83f11c08` |
| result bundle | 26,043 | `sha256:604583a194479b7ce6712488604dd75bfe0fa9f65bebfd89d3ba8233479e5746` | `sha256:0fba0439ea7863635e4d18c2bbb717df6ee53ce273cdd991a692ef721bd6fabd` |
| image receipt | 2,753 | `sha256:0278dbfe1fb539b7b19acba451df5737d2c90f85f772e0bd896141fb59d66b85` | `sha256:5acf85b7db222f05b1b3eeb30c763e3083208e1a0264f9f0248a6224dfcded14` |
| halted public audit | 29,718 | `sha256:78c1b54aa2de9c06927c31753dd293b2ddf1fe0b1376f56e0b3ce7870abf2155` | `sha256:0e6e94aaec6c803a9377ba46e1b25390ef1219871b8ec382e2d53b659bf7c457` |

The audit was built twice with the same content hash. It reads only the closed public bundle, image receipt, approved
plan, public task and agent-visible event/tool/check metadata. It does not read raw LLM response/reasoning, private
specification, hidden evaluator content or reference patch. It adds zero provider, Docker, agent, evaluator, visible
check, network call or cost.

## Validation and disposition

Initial focused validation:

```text
tests/test_rapid_r24_halted_audit.py: 5 passed
R24/driver/continuation/V27/R23/docs regression: 121 passed, 4 deselected
trace viewer regression: 13 passed
```

The four deselections are current-source binding guards, not result tests. One legacy V26 guard correctly rejects the
advanced successor source; three candidate-v33 guards correctly reject rebuilding a consumed candidate after adding
post-run audit/reader code. Direct byte hashes instead confirmed that the frozen candidate, rehearsal, qualification,
approved plan, result bundle, image receipt and halted audit are unchanged.

Validation initially exposed stale SQLite sidecars even though no Python/uv process held the files and the WAL was
zero bytes. The sidecars were moved, without changing `state.sqlite3`, into recoverable `.patchloop/analysis` backups.
The cause was then reproduced: `ReadOnlyTraceStore` used the SQLite connection context manager without an explicit
`close()`, which can leave WAL-mode reader sidecars. The reader now closes in `finally`; two audit builds again emitted
the same `sha256:0e6e94aaec6c803a9377ba46e1b25390ef1219871b8ec382e2d53b659bf7c457`, and repeated WAL
reads leave no sidecars. Ruff check/format and `git diff --check` all passed.

R24 is consumed and immutable. Candidate-v33, its image receipt and its three unstarted rows cannot retry or resume.
No V25/V27 quality, efficiency, cost or generalization comparison is supported; V27 is not promoted. Work Item 84 is
offline only: define lifecycle components once, reference them through machine-checkable bindings and return exact
relational mismatch feedback before any separate activation review.
