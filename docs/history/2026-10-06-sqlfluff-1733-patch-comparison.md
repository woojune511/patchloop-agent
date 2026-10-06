# SQLFluff-1733: successful and failed patch comparison

This is a public-source follow-up to the closed
[verification comparison](2026-10-06-verification-closure-results.md), requested to
compare successful row 06 with failed row 08. The original evidence is unchanged.
All work is `official=false`, claim-ineligible and development-exposed. No provider
or evaluator was called, and no runtime/default change or paid follow-up was made.

## Question and controls

Both runs reproduced the same CTE indentation defect and obtained the same useful
rule contrast: L036 moves the first target, while L003 supplies indentation. Their
single-file patches nevertheless changed different mechanisms and had different
acceptance outcomes. This pair is useful for separating patch correctness from
source availability and the failure to verify the changed public behavior.

The leading explanation was an incorrect indentation calculation left untouched
by row 08. Alternatives included a trigger-lifetime defect, unavailable source at
the decision point, and a correct public repair with some other acceptance gap.
Equal public outputs from the patches would weaken the leading explanation.
Source delivery alone cannot prove why the model chose either patch.

Before execution, a new packet froze three sequential public probes: base, exact
row 06 and exact row 08. Each ran the same public issue SQL and a plain SELECT
control, with exact expected output established from the public issue and the
earlier public reproduction. The parsed issue has four spaces before the inner
SELECT; it matches both runs' historical probe literals. No input normalization
changed that indentation. No hidden tests, private specs, reference patches or
evaluator contents entered the comparison.

- Base: `a1579a16b1d8913d9d7c7d12add374a290bcc78c`.
- Row 06: `run_dev_34c6612b1eb647c4`, patch from
  `C:/pt/vcp06/wave3/native/18/source-only.patch`.
- Row 08: `run_dev_33938f53e2834d4f`, patch from
  `C:/pt/vcp06/wave4/native/18/source-only.patch`.
- Operator HEAD: `e0224f016586a598b6d5005556efa87929b2a56b`.
- Operator runtime:
  `sha256:52bd5ca036bc876556b29e6f949fbfc67b7222445b3228015d0bb54b806a3c0e`.
- Identical existing Python 3.12 probe image, prepared dependencies and read-only
  public snapshots; fresh workspaces under `C:/pt/1733pair06`.
- Limits: three invocations, one worker, 30 seconds each, 240 seconds overall,
  no retry/resume, image pull/build, provider or evaluator. Stop on setup,
  infrastructure, cleanup or output uncertainty.
- Standard logging recorded selected L003/L036 events without modifying project
  code. Full output equality is the result criterion, separate from diagnostics.

## Patch mechanics and executed result

Row 06 changes `L003.py:706` from `c - t` to `c + d - t`, where `c` is the comparison
line's physical indent in units, `t` is the current line's, and `d > 0` is their
syntactic indentation-balance difference. This branch already requires `t < c`.
The old insertion reaches only `c`; the new insertion reaches `c + d`.

The new public logs establish the actual branch values after L036 moves `my_id`:
current indentation is zero, comparison indentation is four spaces, and structural
balances are two versus one. With four spaces per unit, `t=0`, `c=1`, `d=1`.
Row 06 therefore inserts eight spaces in one operation. This is an observed
calculation correction, not a literal one-character deletion.

Row 08 changes `L003.py:425-430` to clear `memory["trigger"]` only if a newline's
immediate parent is `select_clause`. It leaves the faulty arithmetic unchanged.
The reset happens after processing the current line. Other newline parents now
retain the previous trigger; a following nonblank line normally replaces it.
Because raw-stack processing stops at the remembered trigger, revisiting an old
line before replacement is a plausible side effect. Additional blank-line/EOF
regressions were not executed or claimed.

| Variant | Public CTE exact output | `my_id` indent | Plain SELECT exact output |
| --- | --- | ---: | --- |
| Base | FAIL | 9 spaces | PASS |
| Row 06 | PASS | 8 spaces | PASS |
| Row 08 | FAIL, byte-identical to base | 9 spaces | PASS |

Base and row 08 both first insert four spaces. Their subsequent L003 observations
show indentation 4, then 5, then 9; a final ineffective edit is rejected by the
formatter's repeated-state protection. Row 06 reaches the expected result after
the initial eight-space insertion. The selected logs do not identify every other
rule responsible for intermediate whitespace transitions; no such attribution is
needed to establish the patch difference on these inputs.

All three probes completed assessably in 61.612 seconds overall. There was no
timeout, output truncation, cleanup failure or dropped selected diagnostic record.
Source diffs were unchanged after execution. The hash-chained journal was checked.
These are two public cases per saved source variant, not additional fresh solves,
full regression coverage, or a new acceptance/generalization estimate.

## What the original agents could see

Both originally read all 799 lines of L003 without read-result truncation. Their
immediate mutation inputs differed:

- Row 06 request sequence 336 included lines 260-799, including the calculation.
- Row 08 had the calculation in requests 261 through 393. After the final
  rule-isolation probe and fixture search, the handoff at 408 removed the old
  function-output replay. From request 409 through mutation request 462, the
  calculation was absent. The 24,000-character retained-source selector used
  priority/recency; no pinned range was reported omitted. This is not evidence of
  a source-delivery contract violation.
- Row 08 then searched select-clause types and reread L003 1-250 and 330-430.
  The last read's public intent was to locate fix construction. A specific
  trigger-reset hypothesis first appeared in the mutation; earlier public notes
  retained the rule interaction but no concrete arithmetic explanation.
- Request 449 warned of the last inspection opportunity: nine model calls left,
  eight reserved for protected completion. Its next read was 330-430. Request 462
  then exposed only `replace_text` and `stop_task`, with eight calls remaining and
  eight reserved. It still had 58 tool actions, 777 solver seconds and USD
  0.41057625. The binding limit was the model-call reserve, not time or spend.
- After the public check passed, request 491 had six calls left and one required
  for completion. Reads, probes and selected tests reopened, and the arithmetic
  body was available again. The agent chose to finish.

Thus row 08 had earlier access, lost the relevant source at the immediate edit
decision, and temporarily lacked a reread tool. Availability may have contributed,
but this pair does not establish a causal context-policy defect. Restoring that
source could still leave the model choosing the same wrong hypothesis.

## Decision and unresolved question

The public repair difference is established: row 06 corrects the exercised
under-indentation calculation; row 08 leaves the reported defect intact. The
alternative that row 08 repaired the reproduction but failed only another case
is contradicted for this public input.

Both original candidates passed the broad public regression check (506 tests),
and neither ran a post-edit reproduction. Row 06 even cited its pre-edit failing probe as proof of
current success. Its eventual acceptance does not validate that evidence claim.
Row 08's reopened verification opportunity means temporary tool closure does not
explain the whole submission failure. Replaying the public case after its edit
would have exposed the unchanged bug; this operator replay does not prove how
the agent would respond to that failure or that automatic replay improves solves.

Keep the baseline. No new prompt, memory, mandatory probe rule, reserve policy or
paid comparison is justified by this pair alone. A focused next question is
whether the retained-source selection and completion reserve together discard
useful already-observed repair evidence at the last mutation decision. Any
intervention needs a demonstrated contract defect or a distinct bounded causal
test. The separate failure to select available post-edit verification remains.

## Evidence

External immutable root: `C:/pt/analyses/1733-patch-pair-20261006-v1`.

- `replay/packet.json`, packet hash
  `sha256:3c8610c60920245f8e3228e2c806ac50b1d11e66195f763fc14106b537fc7a5e`.
- `replay/result.json`, `base.json`, `row06.json`, `row08.json`,
  `probe_program.py`, and `runs/run_dev_1733patchpair.jsonl`.
- `trace/evidence.json`, `source-delivery.txt`, `followup-v2.json`,
  `followup-v2.txt`, and `runs/run_dev_1733pairtrace.jsonl`.
- Trace follow-up hash:
  `sha256:c6e4a689116536e2a40fb1e13e2cf7910570e8f2b659b62755554b04d0073ae9`.

Original journals, source workspaces, patches and closed history were preserved.
Only this follow-up and current status were added or updated.
