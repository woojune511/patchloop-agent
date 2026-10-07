# Thin policy specification and public candidate matrix

Date: 2026-10-07. Source HEAD: `44961b84`. Preparation only, official=false.
The user approved the two preparation artifacts proposed by the
[system review](2026-10-07-system-review.md). No runtime change, new task/probe,
provider call, private evaluation or paid allocation was made.

## Question and decision

Can a simpler model-facing policy preserve the execution contract, and do saved
public checks actually distinguish existing candidate patches? These are separate
questions. The first needs an explicit interface design before a live comparison;
the second can be partially answered from immutable saved receipts.

The [thin-policy reference](../../.agent/thin-policy-reference.md) is now specified.
It requires a real parsing/annotation/recovery adapter, not merely shorter prompt
text. It is not implemented and execution parity is not yet established.

The candidate matrix finds one useful existing public discriminator (2419), one
clear requirement with rejected candidates and a missing candidate measurement
(1733), and one incomplete public oracle (1517). This does not justify a universal
selector or mandatory generated-test gate. Keep the selected baseline. The next
implementation step, if chosen, is the policy adapter and focused parity fixtures;
the next candidate-evidence gap is the saved 1733 A2 patch's current public replay.
Neither live work nor that replay is queued by this preparation.

## Exact policy proposal

- A retains the selected current prompt, brief-v1 planning, decision schema and
  model-state projection.
- B omits required `turn_decision` narration and plan maintenance; retains the
  operational tool arguments, including mutation hypothesis/expected behavior;
  moves the unchanged nullable note/concern update to a standalone call field.
- B removes only enumerated advice fields from derived public state. Raw task,
  source, diff, tool results, current/historical identities, resource facts and
  actual provider wire remain intact. Fresh trajectories can subsequently diverge.
- Tool availability, source-anchor rules, additive-test preservation, finish
  eligibility, cost admission, sandboxing and idempotent recovery stay shared.
  No invented model basis is inserted to satisfy the old schema.

The note identifies the parser, schema, note-extraction, native-transcript,
attempt-card and recovery consumers that must handle the absence of a decision.
Fourteen provider-free acceptance cases cover positive actions, rejection,
annotation errors, check invalidation, scarce resources and recovery. These are
specified test obligations, not fourteen executed tests. This is a declared
policy/interface bundle, not an isolated causal test of a single sentence.

## Matrix scope and evidence selection

Selected three SQLFluff development tasks because an existing public-only packet
already ran identical programs on original and saved candidate code with fixed
environments. It includes a candidate-pair discriminator and two counterexamples
to treating all probe PASS/FAIL outcomes alike. This is a purposive evidence audit,
not a representative sample or a held-out evaluation.

The core consists of seven historical execution receipts from
`C:/pt/analyses/verification-closure-20261006-v1/replay/`.
The new extraction re-parses stdout and compares it with public requirements,
rather than importing task-acceptance labels. The historical variant named
`previous_success` is called `single_quotes` in the new matrix; that old label
does not determine its result. No hidden test, reference patch or private verdict
was used to choose an expected output.

For each core task, program hash, public base commit, prepared dependency identity
and execution profile match across variants. Setup checks passed; no timeout,
truncation, deadline exhaustion or uncertain cleanup was recorded. Source programs,
patch bytes, original journals/envelopes and receipt hashes were checked unchanged.
Different tasks have different base commits and dependency/profile identities;
their outcomes are not pooled into a solve rate.

## Public behavior matrix

Hashes below abbreviate SHA-256 patch identities; full hashes, program bytes,
profiles, observed outputs and exact receipt paths are in the machine-readable
matrix. Empty means the original public base, not a submitted candidate.

| Task / candidate | Patch | Public behavior observed | Preservation / missing evidence |
| --- | --- | --- | --- |
| 1517 original | empty | Doubled semicolon raises the reported dropped-elements RuntimeError | Ordinary single-semicolon parse succeeds |
| 1517 submitted | `c9c38f4b08a6` | Original exception disappears; returned tree retains the input | Ordinary parse succeeds; correct doubled-semicolon lint semantics remain unspecified |
| 1733 original | empty | WITH first field has 9 spaces; public expected output has 8 | Plain SELECT control matches |
| 1733 supplement candidate | `f184803fa153` | Same 9-space mismatch | Plain SELECT control matches |
| 1733 continuation B1 | `a54cc78fa21d` | Instrumented full-linter output has 5 spaces | Different program family; no plain SELECT control in this receipt |
| 1733 continuation B2 | `339ced45df87` | Same 5-space mismatch | Different program family; no plain SELECT control in this receipt |
| 1733 saved A2, row 06 | `d69d881c095a` | **UNMEASURED on submitted patch** in the inspected reproduction records | Current regression PASS; all three probes precede the edit |
| 2419 original | empty | Both function names remain in each warning instead of the encountered name | COALESCE produces no L060 warning |
| 2419 single-quotes candidate | `b9edbbc5126b` | Both IFNULL/NVL messages match the public examples | COALESCE control also passes |
| 2419 backticks candidate | `8297beb065a7` | Names are specific but backtick formatting misses both exact public examples | COALESCE control passes |

The machine matrix has eleven rows: the table's ten task/candidate identities
plus a second observation of the 1733 original under the instrumented program.
The duplicate base is not another candidate or independent problem.

### 2419: useful scoped candidate selection evidence

The [public task](../../tasks/dev-train/current-dev20/20/public.yaml) explicitly
shows `Use 'COALESCE' instead of 'IFNULL'.` and the analogous NVL message.
Program `3a6a60ad69ee` calls the public lint API with L060 and checks IFNULL, NVL
and a COALESCE negative control under the same environment for all three variants.
The two actual candidate patches differ, and this public check distinguishes them.

The narrower requirement "mention only the encountered function" would accept
both candidates. The exact public examples supply the additional formatting
criterion; it was not inferred from a private evaluator. Neither candidate's
success on this small check certifies every input or the entire task. This is
evidence that a usable selector input exists for one case, not that a model will
generate or select it reliably within the budget.

### 1733: rejected candidates do not prove there is no useful alternative

The [public task](../../tasks/dev-train/current-dev20/18/public.yaml) contains the
complete expected WITH output. Program `e958a374bd89` tests that full output and
a plain SELECT control. It rejects both the original and `f184803fa153`.

The additional `C:/pt/sretwhy01/observations.json` receipts compare the original,
B1 and B2 under the same instrumented program `70a8002ddcf1` and the same profile.
They record 9/5/5 spaces. These are genuine recorded output mismatches, but are a
separate comparison group: instrumentation differs from the original program,
the optional scalar setup-check status is `not_checked`, and no plain SELECT
control was executed. Execution completed with confirmed cleanup. These receipts
must not be silently pooled with the original-program rows or promoted into
complete behavior verification. The later
[counterexample result](2026-10-07-counterexample-results.md) supplies additional
B2 failure evidence but no new candidate: both arms submitted `339ced45df87`.

A distinct A2 patch is already available. Its journal
`C:/pt/vcl06/06/runs/run_dev_34c6612b1eb647c4.jsonl` records pre-edit probes at
180/193/266, mutation at 347, current regression at 364, finish at 380 and submitted
identity at 384. This extraction checks the actual submitted patch bytes and does
not use its historical acceptance label to fill a missing public-test cell.
The next narrow evidence question is how **this existing patch** behaves under
the same frozen public reproduction and plain SELECT control. Candidate generation
or a two-candidate live experiment is premature while that cell is unmeasured.

### 1517: a no-crash check is not a complete oracle

The [public task](../../tasks/dev-train/current-dev20/16/public.yaml) explicitly
says the desired treatment of a doubled semicolon is uncertain: ignore it or
report a rule. Program `813138867f2f` only checks parsing and the original crash,
with an ordinary-input control. The submitted patch passes that narrow check.
It does not establish full lint/CLI behavior or which semantic outcome is correct.

Consequently the matrix calls this `CRASH_ONLY_PASS`, not task PASS. Creating a
test that simply copies the candidate's returned error or output would not resolve
the uncertainty. This case should not serve as a decisive selector-adoption case
until additional public behavior requirements justify its expected outcome.

## Generated evidence and validation

New immutable root: `C:/pt/analyses/policy-candidate-prep-20261007-v1/`.

- `build_matrix.py`: read-only extraction/classification of saved records; never
  imports or executes task code. It binds its own bytes and the source inputs.
- `candidate-matrix.json`: eleven rows, three tasks, 136 successful integrity and
  observation checks; SHA-256
  `9c09bec0651e01299a5f05a543d81e9480c3b1ff994596cbf78ba4d46abb9138`.
- `runs/run_dev_policycandidateprep.jsonl`: append-only hash-bound preparation
  receipt. Generated state stays outside the repository.

The extraction compared public expectations to the issue text, verified existing
program/patch/receipt identities and matched within-task environments, independently
recomputed seven scoped outcomes, kept the instrumented group separate, and
checked A2's missing current-probe evidence. No new historical execution or accuracy
result was created. Safety/evaluation was not rerun.

Runtime implementation, policy parity execution, mock smoke and live comparison
remain NOT_RUN. They are not implied by completion of these two preparation
artifacts. Existing AGENTS.md edits and closed historical records are preserved.

Local documentation validation: 5 PASS in 0.16 seconds
(`C:/pt/validation/policy-candidate-prep-20261007.xml`). Both new documents' local
links and whitespace checks passed, as did `git diff --check`. All matrix input
bytes were rechecked unchanged after generation. Runtime suites were not rerun
for this documentation/preparation change.
