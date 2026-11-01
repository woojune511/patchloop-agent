# Pre-edit task correspondence: fresh task8 independent PASS

2026-11-01. Status: CLOSED. Development-only, official=false, claim-ineligible.
Execution commit: `e6374d6fb481f0e94d2164cea5ac3177f78b3c03`.
Runtime: `sha256:a1c2a5948d4cb0992f1cdecbe49e1af4a5566dae69145eab2d131f8d20213b20`.

## Question, scope and comparison boundary

The [pre-edit change](2026-11-01-pre-edit-task-correspondence.md) addresses adopting
a helper failure as the repair target without explaining the public input. The
user approved one fresh dev-train 8/pydicom1413 solve using
gpt-5.4-2026-03-05/xhigh and `C:/Users/geonj/Documents/PatchLoop/.env`, with a new
USD4 cap. Limits were 12 edits, 40 model calls, 100 actions and 1,800 seconds,
including 330 seconds for evaluation. No prior patch, helper, checkpoint,
counterexample or private expectation was injected. Immediate input counting,
zero SDK retries and stop on count/transport/billing/cleanup uncertainty remained.

The latest [normal baseline](2026-11-01-condition-normal-task8-retry-results.md)
already passed at 523e5da6. Only the three runtime files of this intervention
differ. Task/model/source/dependencies/policies/resource limits match, but the cap
is USD4 versus USD3.3744305 and the model trajectory is not fixed. The earlier
failed solve is historical context, not a matched control. This exposed development
case tests behavior; it cannot establish causal gain or generalization. Preparation
recorded the question, criteria, differences and stop conditions before dispatch.

## Result and public sequence

Run `run_dev_354257e1864c4cf2` completed in 494.296 seconds:

- Independent task acceptance PASS and safety PASS, one submission/evaluation.
- 14 model calls, 14 input counts, 21 tools and one accepted two-file edit.
- Required public check: 213 PASS. Selected OL tests: three PASS.
- Three public probes; process success does not certify their observations.
- Recorded generation usage USD1.1495245, all 14 response usages settled.
- No retry, resume, protocol correction, extra evaluator or second repair.

The new repair instructions reached input7. Mutation tools were not offered yet;
both existing intent descriptions first reached the edit-capable input23, before
mutation. The source investigation followed the conversion caller into the value
setter and identified missing binary-VR exemptions from backslash splitting.

| Public evidence | Actual observation and limit |
| --- | --- |
| Base probe, seq82/84/85 | Literal OL bytes containing 0x5c became MultiValue while OB stayed bytes. Both writer calls failed because ordinary BytesIO lacks write_tag. |
| Mutation, seq140/141 | Add OD/OL/OV to the setter's no-split list; add an OL regression asserting preserved value and the complete encoded element. |
| Required check, seq155/156 | Current-diff dataelem/filewriter suite passed 213 tests. |
| Same-program replay, seq171/173/174 | OL now stayed bytes. The writer setup error remained; this compared the intermediate value, not successful serialization. |
| Selected tests, seq188/189 | Existing implicit/explicit OL nodes and the new backslash-byte regression passed. |
| New caller probe, seq203/205/206 | Dataset.add_new with reported tag 0x00660040 and OL, then save_as. Backslash-containing and plain OL controls both saved 16-byte files with payload presence and matching tails. |
| Finish, seq220/221 | Submit unchanged candidate; acknowledge missing bound original replay and source-only OD/OV evidence. |

The third probe followed an explicit decision that passing tests still left the
public add_new/save_as caller unobserved. It avoided the earlier helper's API setup
problem using a different caller, explicit little-endian configuration and a
same-VR control. It was not the identical original caller replayed before/after.
All three probes contain zero Python assert statements and catch writer/save
exceptions. The observations above come from actual output, not exit status;
the added pytest does assert value equality and full encoded output.

The three selected tests overlap the earlier whole-file check. Before choosing
them, input178 supplied file-level PASS with truncated output,
collection_status=not_reported and no recent_tests. The new node name appeared in
source/patch evidence, not a per-node execution receipt. The stated reason was to
verify collection and execution of those nodes. This is overlapping validation
under an information gap, not evidence of ignoring delivered identical node
results. It does not prove collection was missing or repetition was necessary;
the request also said absent collection telemetry alone need not trigger a rerun.

## Interpretation and remaining limits

The observed behavior fits the intended direction: preserve bytes representation,
investigate the producing step, observe the wrong intermediate state before repair,
and add a closer public caller check rather than treat helper success as complete
coverage. A correct initial patch was independently accepted.

This was one repair, not discovery of another defect followed by a second repair.
The original H-array conversion, unknown indexData and lineSeq/ds relationship were
not reproduced. The helpers use literal bytes and flat datasets. OD/OV runtime
cases remain source-inferred, as disclosed in the plan and final assessment.
Active post-edit guidance reached input145, but scope_review remained null; use
of the structured table itself is not demonstrated. Original-case delivery remains
unverified_delivery despite acceptance. The last request still had 27 model calls,
80 actions and approximately 1,024 solver seconds; exhaustion did not force finish.

The prior PASS cost USD0.6997885 and took 316.883 seconds with 10 calls/18 tools.
This run cost and took more while adding base/current observations and a node-level
check. Trajectory and cap differences prevent assigning this difference to the
prompt or treating it as an efficiency result. Both runs passed independently.

Decision: retain the small guidance change. It reached the intended decision point
and the desired source/observation/caller-check behavior occurred in this case.
No new gate or larger budget follows. The probe setup weakness, non-asserting
observations, collection-evidence gap and original correspondence limits remain
recorded questions; no further runtime modification was made.

## Accounting and evidence

The new USD4 allocation is CLOSED; unused USD2.8504755 grants no further execution.
Earlier closed allocations and the previous UNKNOWN call remain unchanged.
Recorded usage is not invoice/count-endpoint reconciliation. The independent
summary was not fed back to the solver. This audit read public actions and receipts,
not private evaluator bodies, hidden tests, reference patches or provider reasoning.

Preparation passed import, public operation and selected-test canaries with cleanup
confirmed. Ten frozen bindings, normal driver control flow and no history injection
were independently reviewed. Wrapper/recording scripts passed Ruff. Runtime and
local-validation bindings match the preceding 133 focused tests and 1,457 quick
passes/one platform skip, including isolated mock evaluation; those were not rerun.
Result documentation is checked separately.

- Preparation: `C:/pt/pre-edit-normal8-20261101-v1/`.
  Manifest `sha256:4f588a610b8d59359df4b0b9040374cc043d25ce293bd6187a5183d61bb94ffd`.
  Preflight `sha256:0a4aaeca25c1951b641f24d2ff3e07b57643e83d684f4c06d6954a20d0811548`.
- Execution: `C:/pt/pre-edit-normal8-run-20261101-v1/result.json` and task8 journal.
  Patch `sha256:adf0931bef198f142d38d3b62e0b6ee63a94fd97084005260103399d12203ded`.
- Public audit, patch, usage closure and content-addressed evidence:
  `C:/pt/pre-edit-normal8-closure-20261101-v1/`, with append-only dev-run-v1 receipts.
