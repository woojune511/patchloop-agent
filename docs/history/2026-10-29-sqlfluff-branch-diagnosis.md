# SQLFluff branch diagnosis: executed edit, unchanged behavior

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate; bounded local execution trace and source analysis
- Origin Date: 2026-10-29
- Verification Status: VERIFIED for the recorded public call and trace comparisons
- Version Label: sqlfluff_branch_diagnosis_v1
- Evidence class: operator diagnostic; official=false, claim-ineligible

## Question and method

The [saved-candidate replay](2026-10-29-sqlfluff-public-candidate-replay.md) found
the same nine-space result before and after the patch, versus eight expected.
The user asked whether the edited branch executed and, if so, why its change had
no visible effect. This matters because increasing exploration or budgets cannot
help if a repair changes the operation form without changing the faulty behavior.

Competing explanations were: the branch never ran, its fix was rejected, a later
rule altered the result, or final serialization differed from the fixed tree.
The smallest distinguishing observation was the changed branch plus each rule's
fix application, intermediate SQL and acceptance decision on the same input.

Two fresh workspaces reproduced the original and saved candidate using the same
public SQL, `sqlfluff.fix(sql)` defaults, prepared dependencies and pinned image as
the previous replay. The only source difference was the submitted L036 patch.
The same read-only `sys.settrace` observer recorded selected L036 line events,
L003 indent-coercion returns, and linter fix applications. It replaced no target
functions and made no target source edits. Trace records were bounded at 40,
output at the existing 12,000-byte cap, each target at 30 seconds and the script
at 240 seconds. Any mismatch, timeout, overflow or execution uncertainty stopped
the comparison; there were no retries.

Both executions exited zero with no timeout, truncation, trace overflow or cleanup
failure. Original/candidate source snapshots and patch identities matched the
previous replay. Loaded module hashes matched each workspace. Traced final SQL
exactly matched the respective untraced output. This checks the observer's effect
on the measured output; it does not claim identical timing or every internal state.

## The edited branch executed and its fix was accepted

Candidate `src/sqlfluff/rules/L036.py:122`, the new whitespace-to-newline edit,
executed once. Its condition saw `i=0`, target `my_id`, and one single-space
whitespace segment. The returned fix was `edit(" " -> "\n")`. The linter accepted
the resulting tree in loop 0. The containing multi-target method ran five times;
the changed edit was produced only on the first pass.

The original instead returned `delete(" ")` plus `create("\n", before my_id)`.
On this input both produced the same observed intermediate SQL and select-clause
prefix: `SELECT`, indent metadata, newline, then `my_id` with **zero** leading
spaces. The suspected original space did not survive either operation. This
refutes branch nonexecution and rejected-edit explanations for this saved patch.
It also shows why merely changing the fix representation had no effect here;
it is not a claim of equivalence for all inputs or every AST metadata field.

## Where the ninth space actually came from

The rule-application events after L036 are identical in both traces. Loop numbers
below are the recorded zero-based linter fix-loop values.

| Loop | Rule | Operation at `my_id` | Resulting spaces | Accepted |
| --- | --- | --- | --- | --- |
| 0 | L036 | Move first target to a new line | 0 | Yes |
| 1 | L003 | Insert a four-space piece | 4 | Yes |
| 2 | L003 | Insert another four-space piece | 4 + 4 = 8 | Yes |
| 2 | L039 | Reduce the second four-space piece to one | 4 + 1 = 5 | Yes |
| 3 | L003 | Request eight spaces but replace only the first piece | 8 + 1 = 9 | Yes |
| 4 | L003 | Replace the first eight-space piece with eight again | 8 + 1 = 9 | No: already-seen SQL |

L039's `src/sqlfluff/rules/L039.py:38-65` state machine treats the first whitespace
piece as indentation, then clears `prev_newline`. With a second adjacent whitespace
piece, it later proposes normalizing that piece to one space as if it were internal
spacing. The observed L039 fix changes four spaces to one, making eight become five.

L003 then receives the explicitly traced indent buffer `["    ", " "]` and
`desired_indent` of eight spaces. `_coerce_indent_to()` at L003.py:277-286 edits
only `current_indent_buffer[0]`; it leaves the remaining one-space piece. The
result is nine. On the next pass the buffer is `["        ", " "]`, still with
desired eight. Replacing the first eight with eight changes no SQL.

`core/linter/linter.py:417` rejects that proposed raw SQL because it is already in
`previous_versions`; line 426 emits the repeated-fix warning. The trace reached
this check, so this occurrence is the seen-state path, not merely the alternative
`fixes == last_fixes` check. No accepted change occurs in the last loop and fixing
ends. Its final raw SQL equals the API return string, so serialization is not the
source of the extra space in this observed execution.

## Decision, proposed repair target and limits

The saved model edit targeted the wrong mechanism: an allegedly retained original
space. The extra space actually arises later from fragmented indentation and the
interaction between L003 and L039. Existing public regression PASS did not test
this final behavior, and the model's earlier helper parsed the original input
rather than the transformed output. That verification gap let the hypothesis
remain unchallenged until the operator replays.

A concrete next repair hypothesis is to normalize the **whole indent buffer** to
the requested width: replace the first piece and remove redundant later pieces,
or produce a single indentation piece earlier. A test must distinguish contiguous
eight spaces represented as one piece from multiple adjacent pieces, then assert
the complete public `fix()` output and stability across another fix call. Relevant
indentation/spacing regressions are still required. No such repair or counterfactual
intervention was implemented or tested here; this is not a validated patch choice.

The diagnosis resolves branch reachability and this public example's mechanism.
It does not establish the private evaluator's exact failure case, CLI equivalence,
general improvement, or model uptake of this information. No paid model call or
private evaluation was performed; API cost was USD0. This observation was not
retroactively delivered to the prior solver. Runtime and policy defaults remain
unchanged. A shared-context source reviewer also checked the traces; that is local
review, not blinded or cross-model evidence.

## Reproduction and provenance

Host checkout: `9797abd1`; unchanged runtime hash
`sha256:8eb3e389ce20f0b9143c330a3dae3dbd9fcca65f8f0b1ad5d1f5c6dc6a621cfb`.
Task: dev-train current-dev20/18, `swebench-lite-dev-sqlfluff-sqlfluff-1733`.
The submitted patch remained
`sha256:d3022a59756dfb1c7ad44b9b2c063306a384e147f78c9f0a0194d3fc560bfe62`.
The original plan's 29 sealed bindings were checked. Its closed paid authorization
was not reused; the current user request authorized this local diagnosis.

External evidence root: `C:/pt/sqlfluff-branch-trace-v1/`:

- `plan.json`, `trace_helper.py`, `run_trace.py`, `submitted.patch`.
- `baseline/` and `candidate/`: request, execution receipt, raw stdout/stderr and
  structured `trace.json`.
- `summary.json`, plus deterministic `analyze.py` and `analysis.json` comparing
  branch hits, intermediate results, later rule events and final output.
- Append-only hash-chained `runs/run_dev_sqlfluffbranchtracev1.jsonl` retains
  action/input identities and output hashes.

Executed command: `uv run --locked --offline python C:/pt/sqlfluff-branch-trace-v1/run_trace.py`.
The separate `analyze.py` command reads traces only; it does not rerun the target.
There were two target executions (14.242 and 10.338 seconds, not a timing comparison),
9/10 bounded trace events, and no image pull/build or credential read.
Historical artifacts and target source were preserved. Only follow-up documentation
was changed in the repository. `tests/test_documentation_layout.py` passed 5 tests
in 0.18 seconds, with `documentation-tests.xml` under the evidence root;
`git diff --check` passed. Broader regression and mock runs were unnecessary for
this documentation-only repository change.
