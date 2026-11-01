# Shared repair guidance from affected public contracts

Date: 2026-10-30 KST. Mutable dev-head implementation follow-up, official=false.
Live execution and independent acceptance under this change: **NOT_RUN**.

## Why this change

The [SQLFluff1517 public diagnosis](2026-10-30-sqlfluff1517-public-contract-diagnosis.md)
found an incomplete branch repair and an option-bypassing partial-success return,
while the submitted test and probe exercised only the adjacent-delimiter example.
The new test was collected in replay, so a test-execution gate would not address
that observed gap. Existing prompts already requested preservation and falsifying
inputs; absence of those generic instructions is not an established cause.

The user asked to implement the proposed general procedure and test it. The
intervention makes that procedure concrete: derive verification from the public
contract affected by a changed return, condition or state, inspect related paths
and boundaries, and choose small checks of required results and preserved state.
The expected benefit is better choice of checks, not more probes or annotations.
This is a behavior-improvement hypothesis, not a proven quality gain.

## Implementation

`patchloop/dev/repair_guidance.py` defines one short shared instruction. It is used
by the current and thin system prompts and by compact repair and completion prompts.
The latter replace the ordinary prompt in the real runner; changing only the main
prompt would omit the guidance at those stages. Both `replace_text` and `edit_files`
receive the same system-level guidance.

Existing prose was condensed to keep the current prompt within its prior size:
7,948 to **7,935 characters**. Current plus brief planning is **10,744 characters**
with the reproduction default, or **10,631** with selected public-checks-v1.
This measures characters, not tokenizer counts or live latency. Policy-specific
original-reproduction replacements remain intact. No tool schemas, intent fields,
permissions, budgets, execution gates, fixed case counts or review agent were added.
The current guidance hash changed; frozen historical identities remain unchanged.

There are no SQLFluff inputs, repository names, diagnostic results or solution
hints in the shared instruction. The saved candidate and task package are unchanged.
The guidance reuses the existing hypothesis/expected_behavior, source inspection,
check/probe and submission mechanisms. Documentation points to this follow-up;
the closed diagnosis and run records remain immutable.

## Validation and interpretation

The new delivery tests exercise the real model-input builder across current/thin,
public/reproduction verification, general/repair/completion stages and
append/segmented contexts. They verify one copy of the shared instruction and
preservation of task, workflow gate, offered tools and remaining budget. Additional
checks confirm both mutation tools retain their exact existing fields and limits.
All 28 delivery/schema cases passed in 0.99 seconds.

These tests cannot establish that a live model follows the instruction or chooses
useful counterexamples. Neither a mock acceptance PASS nor prompt presence is
evidence of repair quality. Further local regression results are recorded below.

Focused validation passed **86 tests in 25.31 seconds**, including all 28 new cases,
compact source/evidence delivery, existing memory and tool-wire contracts, policy
substitution, prompt bounds, and thin mock runs reaching isolated evaluation in
append, native-window and segmented contexts. Ruff passed. The first focused attempt
exposed a test expectation that omitted appended transport guidance and the current
prompt's deliberately changed identity; both expectations were corrected without
changing execution behavior or historical identities.
The first two quick attempts each passed 1,235 tests and skipped one check,
but the same existing mutation contract test rejected shortened gateway wording.
Both the observed-evidence binding and prohibition on caller-supplied evidence IDs
or patch wrappers were restored explicitly. The final affected-contract/delivery
selection passed **38 tests in 1.33 seconds**.

The final quick regression passed **1,236 tests, one skipped, in 234.40 seconds**
with four file-grouped workers and no worker restarts or failures. It includes
isolated mock evaluation; no redundant standalone mock run was added. Final Ruff
passed, and documentation validation passed 6 tests. HTML validation found 51 unique
IDs and 65 links; its JavaScript was unchanged. Full regression, Linux execution,
live-model behavior and independent acceptance under this change remain unverified.
Test wall times are validation costs, not agent-latency improvement measurements.

Runtime: `sha256:4fe33c20ca40c4ed53ce58d5efb508bba6825ff1872d3eeed59da918ee2bf374`.
The default tool-surface identity remained unchanged. Reports and runtime/prompt
identities are retained in the external journal and content-addressed store below.

## Next assessment and boundaries

In a future authorized integrated development run, inspect whether the agent uses
public-contract evidence to choose relevant boundaries and preservation checks,
then assess independent acceptance, regressions, cost and elapsed time together.
A SQLFluff success alone would not establish general benefit. Use several public
development tasks; no extra paid one-factor study is a prerequisite.

No paid allocation was opened or reused by this implementation. All earlier
allocations remain closed. Evidence root:
`C:/pt/repair-contract-guidance-20261030-v1`; append-only `dev-run-v1` journal:
`runs/run_dev_repaircontractguidance.jsonl`.

Proposed live follow-up, pending new user authorization: dev-train 3 (pvlib1154),
9 (pydicom1694), 16 (SQLFluff1517), fresh once each, GPT-5.4-2026-03-05/xhigh,
credential file `C:/Users/geonj/Documents/PatchLoop/.env`, maximum two workers,
USD4 per task and USD12 total. Preserve the selected policies, 25K output tokens,
40 model calls, 100 actions, 12 edits and 1,800 seconds per task including evaluation
reserve. Zero retries; count/transport/billing/continuation/cleanup uncertainty stops
new admissions. No saved repair, operator diagnosis, private details or old notes
are seeded. Source task packages remain unchanged. This is a same-roster follow-up,
not a randomized or generalization claim. Fresh preparation:
`C:/pt/contract3916-20261030-v2`; fresh result path:
`C:/pt/contract3916-run-20261030-v2`. A prepared launcher is not execution approval.
The v1 preflight stopped before any provider call because the new runtime module
was not yet committed/tracked. Its preparation evidence is preserved; v2 is prepared
only after the implementation commit.
