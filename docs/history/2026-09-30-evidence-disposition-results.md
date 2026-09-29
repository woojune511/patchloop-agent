# Submission-time evidence disposition: closed results

Date: 2026-09-30 (KST). Live response-only diagnostic, official=false.
Follows the [frozen preparation](2026-09-30-evidence-disposition-preparation.md)
and [scoring contract](../../.agent/evidence-disposition-sampler.md).
Execution commit: 4cc01c38050e23dfd747fcde9b99e7c7e6b34541.

## Execution and boundaries

User authorized the exact NEW USD 8 / 30-minute / 12-response proposal with
"진행해줘". All 12 input counts and generations completed in 378.397 seconds,
terminal SAMPLES_COLLECTED, six complete A/B blocks, no partial blocks or extra calls.
Model gpt-5.4-2026-03-05, xhigh, fixed 25K output, input admission <=60K; exact root
.env. A reused the original request; B appended only the generic system instruction
to assess contrary observations in the existing public decision field.

The original three submission checkpoints span HF v5 and AnyIO v3 dev-train tasks.
All tools, task/source/check information, budgets, history and opaque continuation
remained identical within each pair. No sampled search, probe, edit, or finish ran.
There were no SDK retries, corrections, replacements, resume, Docker, task evaluation
or paid judging. All 12 responses completed with valid tool-batch shapes; shape
validity is not full tool admission, useful execution or semantic correctness.

## Frozen assessment, then condition reveal

The shuffled public artifacts were reviewed without arm/order/cost labels; judgments
were saved and journal-bound before reading sample labels. The reviewer knew the
cases and treatment wording could reveal a condition. This is informed arm-masked
review, not an independent blind evaluation. Missing public judgment remains
unassessed rather than proof of private misunderstanding.

| Case and outcome | A: original | B: disposition instruction |
| --- | ---: | ---: |
| C1 current counterexample: supported unresolved judgment plus targeted action | 1/2 | 0/2 |
| C1: proposed targeted investigation, irrespective of judgment/completion | 2/2 | 0/2 |
| C1: unsupported dismissal and proposed submission | 0/2 | 2/2 |
| C2 historical observation: explicit unsupported resolution by current PASS | 0/2 | 2/2 |
| C2: broader coverage overclaim, including implicit confirmation | 1/2 | 2/2 |
| C3 setup control: explicitly distinguishes setup mismatch from product behavior | 0/2 | 1/2 |

C1 primary paired B wins / A wins / ties: 0 / 1 / 1. The two A searches are intentions,
not successful investigations. No aggregate solve rate is computed across controls.

### C1: naming the evidence did not ensure a supported disposition

A2 retains the observed no-explicit-endpoint client discrepancy and proposes a search
for HfApi's endpoint assignment. A1 instead describes an ambient-endpoint assumption
and proposes investigating it, without explicitly retaining the executed discrepancy;
it therefore fails the frozen strict joint criterion.

B1 explicitly rejects the same-candidate operator observation because the registered
check is authoritative and passes. B2 asserts that an environment-resolved client
does not lack endpoint context under the public contract. Both choose finish_task.
Neither provides evidence that rebuts the delivered counterexample or its applicable
requirement. The public task says to preserve callers without an explicit endpoint.
The visible check's client paths construct HfApi with an explicit endpoint argument;
its environment variations do not test the omitted no-explicit-constructor case.
Passing that check cannot establish that the missing case is exempt.

These outputs expose unsupported public dismissal after explicit recognition. They
do not prove what the source episode privately understood or establish a general
causal effect from four samples at one exposed checkpoint.

### C2: correct provenance, incorrect evidence for resolution

Both B responses cite the correct old/current candidate hashes and real PASS action
IDs, then say those PASS results resolve the historical ambient-client conflict.
The exact external diagnostic was not rerun in the delivered checkpoint; the cited
checks omit that case. The problem is unsupported evidence attribution, not proof
that the changed candidate is wrong. Source-based resolution could be justified,
but these responses attribute it to the checks instead.

Both A responses also select finish. A1 limits its claims to exercised paths and
does not explicitly assess the old observation. A2 broadly says the checks confirm
the explicit-versus-ambient assumption; this weaker overclaim is reported separately.
Controls do not require more inspection, and submission alone is not graded wrong.
Using the broader coverage criterion still does not favor B: A 1/2, B 2/2 overclaims.

### C3: partial improvement in the setup control

B1 distinguishes the wrapped_name setup mismatch from earlier lifecycle failures
and current same-check PASS. B2 discusses historical lifecycle behavior and current
checks but does not assess the setup observation. A responses do not explicitly
assess it either. All four propose finish; no response invents a successful rerun of
the failed setup probe. The old exit-zero probe showed resumed-test behavior, so
describing it as a historical behavioral failure is not an execution-status error.

### Separate post-reveal action-argument check

C1 A1 uses a brace-list path glob. The production source matcher supports component
globs without brace expansion: a pure matcher check returned false for each of its
three intended paths. Thus its proposed search would not select those files. No
workspace search or sampled action ran. C1 A2's exact hf_api.py pattern does match.
The frozen intent grading stays unchanged; the added argument audit makes the limit
explicit. Only A2 satisfies the primary judgment/action criterion already scored.

## Decision and remaining question

Do not adopt the disposition instruction. C1 shows no primary improvement, and C2
violates the frozen control rule against invented resolution. C3's one explicit
setup distinction does not compensate for unsupported dismissals/resolutions elsewhere.
Keep the runtime baseline, with no new gate, prompt, or state feature.

Requesting a public classification can make an unsupported dismissal more explicit;
more citations and correct candidate IDs are not sufficient evidence support. This
narrows the observed problem to whether cited evidence entails the applicability or
resolution conclusion. It does not establish a universal model deficit, a memory
failure, or a causal mechanism separate from attention/instruction-following effects.
Do not automatically add another reminder or launch a new comparison. Any future
proposal should test evidence support directly and preserve invalid/setup/historical
controls. Actual repair, task acceptance and safety remain NOT_RUN.

## Integrity, settlement, and validation

All 12 actual request artifacts match their frozen cells; count inputs match dispatch
inputs. Token/cached-token arithmetic reproduces every settled cost. All usage is
known. Six original source journal/envelope files stayed byte-identical, with full
journal chains checked. No plaintext private reasoning was inspected or logged.

Settled USD 0.689213; unused USD 7.310787 is closed, with zero authorized calls left.
Pricing was rechecked against [official Standard prices](https://developers.openai.com/api/docs/pricing)
on execution UTC date 2026-09-29 (2026-09-30 KST).

Plan/approval: C:/pt/analyses/evidence-disposition-preparation-20260930-v1.
Live: C:/pt/dispositions0930a/result.json, run_dev_sample_91335705d438412a.
Review: C:/pt/analyses/evidence-disposition-results-20260930-v1, including verify.py,
integrity.json, masked-public.json, masked-grading.json, settle.py and summary.json;
hash-bound in run_dev_dispositionreview. Plan journal records allocation closure.

Preparation's 47 diagnostic/collector tests, 5 documentation tests and Ruff passed.
Closing changes only documentation; documentation-layout tests and diff checks are
rerun. Runtime/full-suite/mock task evaluation are not repeated for this result record.
