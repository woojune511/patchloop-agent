# Assumption-directed verification: two fresh Darts runs

Status: COMPLETE / allocation CLOSED / official=false / claim_eligible=false.
Frozen correctness comparison: INCONCLUSIVE. No observed improvement on the
selected public cases. Direct verification was exercised only in B; no genuine
candidate defect was found and repaired through those probes.

## Problem, hypothesis and fixed scope

The [submitted-patch review](2026-09-30-submitted-patch-review.md) found that passing
registered checks and isolated acceptance did not cover grouped output widths or
zero-width feature restoration. The intervention replaced generic experiment advice
with selection of a minimal input that could refute a repair assumption, deriving
expectations independently from the public contract. No tool, probe quota,
annotation, submission gate or task package changed.

The user approved two fresh repeat=1 invocations on original-darts-3065 v1:
A with the previous guidance, then B with the new guidance. USD 3 per invocation,
USD 6 total, nontransferable caps, zero retries, no resume or replacement rows.
Both used gpt-5.4-2026-03-05, xhigh, desired output 25,000; segmented-v1,
result-or-size-v1, brief-v1, probes enabled with policy none, repair-recheck,
protected-v1 and per-call-v1. Limits were 40 model calls, 100 tools, four accepted
edits and 1,800 seconds per row. Credential file: project .env; no contents recorded.

A ran source commit f900d72d351beb04ec5e8672aec2b396b13eff15 in its isolated checkout.
B's runtime source was 617bb7fb20e6754c133c46fd124e3fd987b3f604, dispatched from its
documentation-only descendant a284ae27. Both source commits passed Linux/Windows
CI before admission. Actual runtime byte differences were confined to model.py;
AST comparison excluding DEV_SYSTEM_PROMPT was equal. An isolated checkout file's
line endings were aligned to the existing main bytes; tracked content stayed clean.
Exact runtime/task/prompt/tool and local source/dependency/image identities were
revalidated. Neither run received previous patches, operator cases, trajectories
or evaluator feedback. The frozen plan is retained at
[a284ae27](https://github.com/woojune511/patchloop-agent/blob/a284ae27/.agent/verification-selection-comparison.md).

## Results

| Observation | A: previous guidance | B: assumption-directed |
| --- | --- | --- |
| Registered public regression | 8 PASS | 8 PASS |
| Isolated acceptance / real sandbox safety | PASS / PASS | PASS / PASS |
| Accepted edits | 1 | 1 |
| Model calls / tools | 6 / 9 | 8 / 10 |
| Agent probes | 0 | 2 |
| Active seconds | 269.224 | 512.006 |
| Recorded provider-usage USD | 0.430408 | 0.694763 |

Total recorded provider usage was USD **1.125171**, reconciled against all 14 settled
provider calls and both terminal receipts. Input counts also numbered 14. No
unresolved call, retry, resumed row or uncertain cleanup remained. These are usage
ledger amounts, not an independently reconciled account invoice. In this one pair,
B cost 1.614 times A and took 1.902 times its active time; neither ratio is a stable
efficiency estimate or an isolated estimate of probe overhead.

All six A and eight B prepared requests were content-hash checked. Every request
carried the correct system prompt and offered run_probe. Thus non-use in A was not
absence of the tool, and B received the intended intervention.

## What B's probes actually established

After the registered regression passed, B identified that it did not directly
exercise the reported drop modes. Its program used a separate sklearn encoder to
derive expected output names/widths and attempted round trips for three-category
drop=first and binary drop=if_binary. These are relevant direct issue checks, but
they do not challenge category grouping or zero-width original features.

Probe 1 executed the first case but failed its DataFrame comparison: the expected
pre-TimeSeries frame had an integer index while the recovered frame used component
names. Public TimeSeries initialization sets the static-covariate index to its
component names. The observed failure was therefore an expectation/setup mismatch,
not a demonstrated candidate defect. The early assertion also prevented the
second case from running.

B corrected the program to compare with series.static_covariates; probe 2 passed
both cases. Both probe receipts bind the same submitted diff, so this was an
experiment correction, not an additional product repair. No original-source replay
was performed by either agent. Do not count these two calls as two valid discovered
counterexamples or treat the first FAIL as a product bug that B repaired.

A handles drop indices in the expanding mapping branch. B also routes equal-width
drop encodings through that branch, changing the binary output label from cat to
cat_b in the frozen review. That naming difference is separate from the failures
below and is not scored as a new quality advantage by the predeclared cases.

## Frozen public review after both submissions

The exact previously frozen operator program was run on fresh copies with each
hash-verified submitted patch. Both executions and cleanup succeeded. No new case,
private oracle or provider call was introduced, and no original verdict was changed.

| Selected case | A | B |
| --- | --- | --- |
| Ordinary drop first, round trip | PASS | PASS |
| Ordinary drop if_binary, round trip | PASS | PASS |
| Grouped categories plus drop first | IndexError | IndexError |
| Grouped categories without drop | IndexError | IndexError |
| Zero-width feature, round trip | Column loss / wrong values | Column loss / wrong values |

Each patch passed two of five deliberately selected cases. This is not a task
success rate. Grouping already failed on the original source; zero-width forward
transformation also originally failed. The patches leave incomplete repairs,
including a newly reachable incorrect inverse path, rather than regressing a
previously successful original round trip.

## Decision and unresolved question

The predeclared promising outcome required a B-only valid counterexample followed
by a correct repair without loss of checked behavior. It did not occur. B performed
relevant direct verification and corrected an invalid test expectation, but both
final patches retained the same frozen failures. The result does not establish a
causal improvement in test selection or patch correctness; one stochastic pair
also cannot establish that the wording is generally ineffective.

The guidance remains implemented but unproven. Do not add another reminder, impose
a probe gate or launch another paid row from this result. The USD 6 allocation is
closed. The narrower unresolved issue is selection of inputs that challenge the
patch's output-width and feature-ownership assumptions, beyond the ordinary modes
named in the issue. More probe calls alone did not resolve it here.

## Immutable evidence

- Proposal/approval/dispatch journal:
  `C:\pt\preflights\verification-selection-20260930-v1\runs\run_dev_5ae2ba97983f404b.jsonl`.
- Frozen proposal hash: `sha256:4b43f9e663a07ad89217c5f84e2c37f8e2e246eae36e9aa09482d975555c4aca`.
- Run root: `C:\pt\runs\verification-selection-ab-20260930-v1`.
- A: `row-1/runs/run_dev_490c9e30d09841d6.jsonl`;
  patch `sha256:d5e6681a111d3b012cf7cacfe747634e6c4e30b186028e4f4655523ed220007a`;
  runtime `sha256:7bb5a6abbbd7464a2e9e4ccf4f56b7c4e5b77892358fc9a521c7ca5a247f8517`.
- B: `row-2/runs/run_dev_b383db582a44435d.jsonl`;
  patch `sha256:42983459343a910a7a04e567d57f36145e37de6e3175848570ee8b1b5ad7a6b8`;
  runtime `sha256:0d589cce3a8f67204f2a4ebbbf0d6494758aa340cabfa8a1a17c3df226738d8d`.
- Execution audit: `audit/runs/run_dev_8bfc7cdc43fc418e.jsonl` under the run root.
- Frozen public review:
  `C:\pt\reviews\verification-selection-20261001-v1\runs\run_dev_0b53f2f4adb440e0.jsonl`.
- Public program hash: `sha256:2d85d35a71120fc9f8eaf65f03656e9ff75e2c52c76d885c6a8a8676d9b9a522`.

All generated receipts are external append-only hash-chained dev-run-v1 state.
Close-out documentation passed all five layout checks, Ruff and git diff --check.
No runtime code changed during execution or close-out; the full suite and mock
smoke were not rerun for the documentation-only result commit.
