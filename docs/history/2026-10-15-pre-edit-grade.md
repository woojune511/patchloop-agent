# Pre-edit A/B grading correction

Date: 2026-10-15. Follow-up to the closed [A/B report](2026-10-15-pre-edit-ab.md).
This supersedes its B1 qualification and failed-selection-gate interpretation;
the original report, grades, responses, prompts and receipts remain unchanged.

## Question and decision

The user challenged whether B1's ancillary assertion error justified excluding
an otherwise distinguishing CTE diagnostic under the frozen rubric. This matters
because that exclusion alone changed the selection gate from met to failed.

**Correct B1 to a qualifying diagnostic proposal: A 0/2, B 2/2.** The earlier review
treated every asserted expectation as a veto over the entire proposal, then called
that rule frozen. That aggregation rule was not specified before sampling. The
ancillary error remains a real quality limitation; actual execution is NOT_RUN.
This reassessment is unblinded and prompted by the user's challenge, not a new
independent evaluation or new sample.

## Frozen requirement versus the applied veto

The [pre-execution design](2026-10-15-pre-edit-diagnostic-design.md), lines 136-154,
and `C:/pt/hypdesign01/grading.json` define the primary as proposing an executable
diagnostic whose observations distinguish preservation under the contemplated
change. They require an actual public entry point/input, a faithful controlled
variation, meaningful observations, appropriate setup and tool/budget boundaries.
They explicitly limit this stage to proposal review, with execution NOT_RUN.

The design excludes a mismatched setup. That is a reason to examine B1's extra
assertion, not to ignore it. However, the previous review did not establish that
this mismatch invalidated the CTE setup, substitution or observation. Neither
the rubric nor design specifies that every ancillary assertion must be correct
for an independently interpretable target diagnostic to qualify.

The broader unit, "including its asserted expectations and their execution scope,"
appears in the later `C:/pt/hypab01/masked-grades.json`. The report's statement that
this full-proposal veto was frozen, and its treatment of B 2/2 as only a different
sensitivity metric, were not adequately supported by the pre-execution text.

## What the saved B1 actually requests

B1 is `sample_6cd00cf2d1fb4bb2a1c6cf35b73b34f6`, formerly masked R2. Its public
response artifact is bound by
`sha256:c7d99c03d256239ba6ce7bd78e36c95f40d6fea056f050e70d90cec4470d16f0`.
The extracted tool arguments equal that original artifact; no response was edited.

| Frozen requirement | Evidence in the existing response |
| --- | --- |
| Actual public entry point/input | `sqlfluff.fix(cte_sql)`; CTE input and expected output equal the public reference |
| Variation reaches the preservation premise | Temporary L036 method has the same AST as the recorded reversion, apart from its name/docstring |
| Distinguishing observation | Prints the CTE target line, then compares the full CTE output with its public expectation |
| Hypothetical/current separation | Question explicitly describes a hypothetical L036 restoration with current L003 retained; no current-diff PASS claim |
| Tool/source/budget boundary | Offered `run_probe`, source/question within limits, in-process substitution, no repository writes |

The decisive statement order in the unchanged B1 source is:

```python
# Original proposal lines 57-61:
cte_result = sqlfluff.fix(cte_sql)
yaml_result = sqlfluff.fix(yaml_sql)
print({'cte_line': cte_result.splitlines()[2], 'yaml_lines': yaml_result.splitlines()[:5]}, flush=True)
assert cte_result == cte_expected, cte_result
assert yaml_result == yaml_expected, yaml_result
```

The wrong-scope YAML assertion is **after both the CTE print and CTE assertion**.
A CTE mismatch raises at line 60, before the ancillary assertion at line 61.
Such a failure can refute the preservation premise; a diagnostic need not exit
successfully to provide a counterexample. The probe backend retains stdout and
stderr on failed execution ([backend](../../patchloop/sandbox/probes.py), lines
536-553), and the [tool receipt](../../patchloop/dev/tools.py), lines 3500-3510,
preserves that output. A failed status alone therefore does not erase the evidence.

The earlier [operator probe](2026-10-15-pre-edit-probe.md) observed eight spaces
for the current CTE output and five after the equivalent substitution. This
supports the chosen distinction; it is not a receipt from executing B1 or B2.
If B1 reproduces that output, its correct CTE assertion fails before the flawed
YAML assertion is reached.

## Retained defects and uncertainty

- The flat/YAML expectation comes from an L036-only fixture, while B1 uses default
  all-rule `sqlfluff.fix`. The fixture helper explicitly restricts rules. The
  proposed overall all-pass expectation is therefore unjustified; an actual
  auxiliary assertion failure has not been observed.
- The flat fix call itself precedes the CTE print. An unexpected failure or timeout
  there could prevent the observation. Static review does not certify completion;
  the later assertion's scope error does not establish such an earlier failure.
  B2 also puts its flat fix call before its CTE observation.
- B1 restores the method only after the assertions, without `finally`. Neither B
  proposal includes a paired unchanged-candidate call; both rely on the already
  observed current success. These limitations remain visible on the same basis
  used for B2. B2 also mentions the unjustified flat expectation in its question.
- Whether the model reads a failure correctly, revises its hypothesis, makes a
  correct final edit, or passes independent acceptance remains NOT_RUN.

## Corrected result and decision boundary

| Cell | Original qualification | Corrected qualification |
| --- | --- | --- |
| A1 | No | No: edit without a distinguishing diagnostic |
| A2 | No | No: edit without a distinguishing diagnostic |
| B1 | No | Yes: distinguishing CTE proposal, with ancillary defects |
| B2 | Yes | Yes: unchanged |

The frozen B 2/2 and greater-than-A selection gate is met. This supports only
**discussing a separately scoped action-executing comparison**. It establishes
neither repair improvement nor runtime adoption. Keep the runtime baseline.
The completed USD 3 allocation remains closed at USD 0.250177 spent; this audit
adds no authorization, prompt change, model/count call or experiment execution.
The unresolved question is observation uptake and final repair, not whether B1
selected a relevant counterfactual test. No follow-up execution is launched.

## Audit record and validation

`C:/pt/hypgrade01/audit.json` records the corrected rows, criterion comparison and
static control flow. Its hash is
`sha256:248549f60233eea5683e2cc130b23b0013a21c7875e57802d6ee98105829d305`.
`bindings.json` verifies 64 prior input bindings; the separate append-only journal
is `runs/run_dev_preeditgradeaudit.jsonl`. The original live and grading journals
retain their closed heads. No private reasoning or evaluator material was used.

Documentation layout/link tests, Ruff, whitespace and artifact integrity are the
relevant local checks. Runtime source and the user's AGENTS.md change are preserved.
No model, count endpoint, sampled probe, SQL task test, Docker run, private
evaluation, broad runtime suite or mock smoke is executed for this audit.
