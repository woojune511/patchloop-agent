# Original-case completion: fresh Astroid pilot

Date: 2026-10-22. One live, development-exposed task; official=false and
claim-ineligible. The separately authorized USD 0.88 allocation is closed.

## Question and frozen conditions

The [local completion controls](2026-10-22-finish-reproduction-results.md)
established retention and replay of cases supplied by a scripted agent. The
remaining product question was whether the model would acquire a faithful
original caller case itself, retain it through repair, and submit a correct fix.
Earlier caller/helper failures made Astroid-1333 a relevant diagnostic. Their
results are selection context, not a matched control for this run.

This was one fresh ON solve of
`tasks/dev-train/current-dev20/13/public.yaml`, with no operator case, helper
packet or repair hint injected into the solver. It was not an A/B comparison.
The user approved the exact command, credential path, repeat count and cost cap
before dispatch. No earlier allocation was reopened.

- Runtime commit: `8f256b0cb5cc96e7f5c0f1b9ad43bbd55df2249b`.
- Runtime hash:
  `sha256:8111c5bcbb643ee1c4dd484f11b862d6834cf4991ba86f21c4f24f40a6a9ab9c`.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens.
- Policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost.
- Limits: one solve, USD 0.88 total, 40 model calls, 100 tool actions,
  four accepted edits and 1,800 active seconds.
- Source: Astroid base `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`, using the
  existing prepared source and Python 3.9 dependencies with Pylint 2.12.2.
- A separate managed checkout kept runtime and task bytes fixed. Source,
  dependency and runtime identities were rechecked after execution.

The plan allowed at most two operator public-caller checks after submission,
sharing a 120-second allowance and adding no model calls. It required stopping
after this solve, and on counting, transport, billing or cleanup uncertainty.
The existing registered isolated evaluation remained separate. No evaluator
image was pulled or built, and no solver feedback or automatic retry occurred.

## Observed execution

Run `run_dev_cac5c2f428a946e1` completed in 486.729 wall-clock seconds
(484.940 active seconds). Process exit was 0; task terminal was EVALUATOR_FAIL.
There were 25 model calls, 26 input counts, 27 tool actions and four accepted
edits. Settled cost was USD 0.52241625. Counting and billing were known;
remaining budget grants no further invocation.

| Measurement | Result |
| --- | --- |
| Final visible regression | 1,232 PASS, 69 SKIP, 15 XFAIL |
| Agent `run_probe` calls / original bound cases | 0 / 0 |
| Finish verification | `unverified`, submission allowed |
| Automatic original-case replay / finish rejection | 0 / 0 |
| Independent task acceptance | FAIL |
| Sandbox safety | PASS |
| Public caller, missing project initializer | FAIL: F0010, child not analyzed |
| Public caller, present project initializer | PASS: exit 0, child analyzed |

The agent made 17 source read/search actions and changed namespace detection
in `astroid/interpreter/_import/util.py` to consult `importlib.util.find_spec`.
The first visible regression passed 1,231 tests. The other three edits added
and repaired a test in `tests/unittest_modutils.py`: its first version used
`assertNoLogs`, unavailable on the task's Python 3.9; its next version raised
ImportError. One `run_tests` request was rejected because a directory was
supplied where a Python test file or pytest node was required. The final
registered check passed on the submitted diff.

The final added test inserted a temporary root into `sys.path` and called
`modutils.modpath_from_file` on `src/project/file.py`. It did not invoke the
reported `pylint src/project` caller. In its finish assessment the model treated
this helper test as covering the mechanism and remaining unrun scenarios as
nonblocking. The host independently recorded case_count=0 and `unverified`.
No probe attempt, original baseline observation, automatic replay or rejected
finish appears in the complete journal.

## Public assessment and evidence integrity

The full submitted diff was
`sha256:99d0c3591b176a43c2ea41aa6229dfb10deaae7dbf4affe10bdd90ac1ea27274`.
The operator assessed its source-only projection,
`sha256:5a34c6727b9d6a40acc119dcf7529371a1a8b6a1a9ef3f89aba28b64fbc747b0`,
omitting the additive `tests/unittest_modutils.py` changes. This is exactly
the first source edit; later edits changed only the added test. Registered
acceptance assessed the full submitted diff.

Both public programs were frozen before authorization and used the original
Pylint entry, relative argument, fixture, environment and source origins. The
missing-initializer case still returned F0010 and did not analyze the child;
the normal control returned zero and analyzed it. Both execution receipts
confirmed cleanup. The pair took 18.223 seconds with zero model calls.

A pre-assessment check found that the existing `caller_grade` function pinned
different historical program hashes. An operator-only function copy rebound
only that identity table to the exact two approved program hashes. Its code,
setup predicates, behavioral criteria, source programs and solver command
were unchanged. This correction was recorded while the solve was in progress,
before any public assessment. The operator knew the registered acceptance
result before the public checks; this was not a blinded review. Neither grade
was fed back to the solver. Preparation serialization/export errors and the
identity adjustment remain recorded; they were not solver retries.

External evidence roots:

- `C:/pt/finish-reproduction22-live-ready/`: exact command, request and frozen
  public programs. Request hash:
  `sha256:9a352bffa8a56bef5f568d9bdbb7af948241a884022112cc1deded542291bfe1`.
- `C:/pt/finish-reproduction22-live/`: `result.json`, `result.md`, CLI/process
  outputs, `public-assessment.json`, `assessment-identity-binding.json`,
  source projection, raw public receipts and content-addressed artifacts.
- Solver journal: `runs/run_dev_cac5c2f428a946e1.jsonl`, 388 events; operator
  journal: `runs/run_dev_finishreproductionliveoperator.jsonl`. Both are
  append-only, hash-chained dev-run-v1. Result hash:
  `sha256:ce52ea389eed918a7363a0efafe71f1ba0c3934287df021cb3400e8d6291f9be`.

Durable evaluation references, journal integrity, settled provider usage and
all four visible-check cleanup receipts were verified. No private tests,
reference patch, evaluator internals or raw reasoning were added to solver
context or this report.

## Decision and unresolved boundary

The repair failed under the independent evaluation and the original public
input. The observed prerequisite gap is acquisition: retaining and replaying
original cases cannot act when the agent never creates one. The specified
unverified path labeled this absence correctly but permitted submission.
Thus the change did not ensure original-caller verification in this solve.

Keep the local retention/replay guarantees at their tested scope; this result
neither establishes a live repair benefit nor tests recovery after rejection.
There was no replay overhead in this run, so it also cannot estimate that
tradeoff. A wrong source hypothesis and unproven helper-to-caller equivalence
remain plausible explanations. Probe feasibility or source-size limits were
not tested by the agent and cannot be assigned as causes from zero attempts.

The next question is how to acquire a faithful original caller case before
helper-level evidence is accepted as coverage, and how to represent a
submission with no such case. The present evidence does not select a specific
prompt, tool or universal hard gate. Another comparison needs a concrete
intervention and a new exact authorization. No additional run is queued.
