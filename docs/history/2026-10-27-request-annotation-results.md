# Request annotation comparison: an edit without a repair

## Material Passport

Date: 2026-10-27. Status: CLOSED; official=false, claim-ineligible.
The user explicitly approved the [prepared comparison](2026-10-27-request-annotation-plan.md)
at manifest `936f0da9...`, A/B one run each, USD 1.20 per arm and USD 2.40 total.
Implementation: `dfe6b33f`; operator hash `d5f8be73...`; product runtime remains
`5753dbef...`. Preparation, authorization and execution journals are separate.

## Observed result

Neither arm produced a verified repair within the one-new-edit horizon. B reached
an actual diagnostic execution and an edit; A made an invalid probe request and
stopped. This is an observed action difference in one run per arm, not evidence
of general superiority or a confirmed causal effect of annotation removal.

| Measure | A: current annotations | B: nullable root memory field |
| --- | --- | --- |
| Normal / correction responses | 8 / 0 | 8 / 0 |
| Model read/search actions | 6 | 6 |
| Probe requests / actual backend starts | 1 / 0 | 1 / 1 |
| New accepted edits | 0 | 1 |
| Terminal | AGENT_STOPPED | CANDIDATE_PRODUCED |
| Frozen original/control verification | NOT_RUN | Original failed; control unchanged |
| Public regression | NOT_RUN | FAIL |
| Settled cost, USD | 0.107448300 | 0.121209150 |
| Maximum input / ceiling | 24,790 / 60,000 | 31,212 / 60,000 |
| Maximum used output / ceiling | 4,815 / 40,000 | 3,191 / 40,000 |
| First dispatch to model-phase terminal, seconds | 99.54 | 86.77 |

Total cost is **USD 0.228657450**, all sixteen responses settled, no retries or
protocol corrections. All unused allocation is closed. Historical unknown bills
are not resolved or included in this separate invocation. Submission and independent
task acceptance are NOT_RUN for both arms.

## A: invalid request, then an unsupported source judgement

The fourth response requested `run_probe` with `python_source=null`,
`replay_action_id=null`, `call_path=null` and `purpose.kind=original_requirement`.
Gateway preflight rejected `/python_source`: source must contain 1-8000 characters.
No probe backend or target started. The supplied original program was available
in the request, but the model did not include executable source or a replay ID.

The diagnostic operator's one probe allowance counts a request attempt, including
a rejected request. It was consumed here; no funded tool-rejection repair was part
of this approved scope. The reserved protocol correction was not triggered by a
gateway tool result. Do not read `diagnostic_probes=1` as execution evidence.

After further inspection, the eighth request still offered `replace_text/stop_task`,
one normal response, five tool actions, one edit and USD 1.116920700 remaining.
The model chose `no_safe_scoped_mutation`. Its summary suggested the saved candidate
appeared sufficient, although the same failing call and exception chain remained
in the input. That is the model's unverified assessment, not a successful check.
Reservation reached the final decision; the missing edit was not caused by a
zero-action dispatch or exhausted input/output/cost ceiling.

## B: observed failure did not validate the chosen repair hypothesis

The seventh response supplied an executable original-requirement probe. It observed
the `pylint.lint.Run` bug/control calls. The bug call still escaped with
FileNotFoundError while the underlying context was AttributeError `__enter__` in
`pylint/utils/utils.py:164`, `tokenize_module`. The helper process exited zero, but
the host classified the reproduction UNKNOWN/not_compared because the target
raised. Its authored JSON booleans being false did not establish success.
The helper tested `isinstance(getattr(call_bug, 'exception', None), Exception)`, but the capture API
returns exception metadata as a dictionary. This test therefore missed the recorded
target exception. Host judgement remained UNKNOWN and prevented false success credit.

The eighth response changed `astroid/builder.py:file_build`. The hypothesis was
that the fallback needed to cover absent or noncanonical `modname`. The patch
removed both the truthy-modname guard and `not os.path.exists(path)`, then supplied
a basename fallback for the namespace name. It did not change the module's stream
behavior. Removing the existence guard also routes existing `__init__` files under
directories into the namespace return branch before normal source loading; this
is broader than the stated missing-initializer intent.

The host then ran the frozen original program on the new candidate. Call conditions
and original program/expectation matched; the control was unchanged. The bug call
still raised the same escaped FileNotFoundError and underlying tokenizer AttributeError.
Whole-case support was false. The scope condition changed, but the observed stream
failure was not repaired.
Public line feedback collected execution of the edited namespace return lines
127-128 during host replay. This confirms line entry in that execution, not full
branch coverage or per-call argument attribution; it does not prove correctness.

Registered public regression reported **71 failed, 1160 passed, 69 skipped,
15 xfailed**. This comparison did not run a matching regression baseline on the
seed, so the number of newly introduced failures cannot be attributed from that
count. The static overbroad condition is independently visible in the public patch;
do not claim all 71 failures were introduced by it.

## Audit and decision

All sixteen actual provider requests retained the prepared full failure/source
messages and the fixed model configuration. Initial input messages were identical;
only the three selected tools' annotation schemas differed. Each request artifact,
journal chain and settled charge was checked. Later histories naturally diverged
with the treatments' annotations and chosen actions. No raw reasoning or private
evaluator material was used in this analysis.

The reservation mechanism was exercised: B used the last two responses for probe
and edit, while A used its final response to stop. Correct interpretation of
observations and a hypothesis that changes the actual failing behavior remain
unresolved. More context/output is not motivated by these measured ceilings alone.
The fixed eight-response and one-edit horizon still limits what can be inferred
about longer repair/recheck loops.

Retain current production defaults. The next discriminating question can compare
model settings under a fixed request representation and the same feasible horizon;
another successful repair is not a prerequisite. This result does not authorize
that comparison or justify another failure-specific controller stage. Annotation
policy adoption, independent acceptance and fresh-solve generalization remain
unestablished.

Execution: `C:/pt/request-annotation-live-v1/result.json`, hash
`sha256:5226870accc0907b59ba0c4873d53a6ab35e564f461563809c35c6571e6f239b`.
Audit: `C:/pt/request-annotation-analysis-v1/analysis.json`, hash
`sha256:303c81a36d939ba46f8a35ec1fa470792a2fcf782a3afb99a4b86215dfbcb186`.
B candidate diff: `sha256:66640d5a2d7788ac34bbdf601f8849159d5aee13afebaa4ec4dc81771127e202`.
Repair detail audit: `C:/pt/request-annotation-analysis-v1/repair-details.json`, hash
`sha256:2b0fb994e1d630a761e01a51666288f12c743e05cf528c61367646402677ec7a`.

ARS methodological scan: 11/11 checked. No significance test or repair-rate
estimate is warranted for one development case and one run per arm. Failed and
unknown observations are preserved; process completion is not task correctness.
