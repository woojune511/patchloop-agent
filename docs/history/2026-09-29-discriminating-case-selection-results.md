# Fixed-candidate evidence selection: response-only results

The [frozen design](2026-09-29-discriminating-case-selection-design.md) completed
24 responses: six dev-train candidates, A/B twice, immediately before their first
public check. A requested verification selection; B added the generic instruction
to seek the same candidate guard with different requirement-defined behavior.
The user authorized the exact new USD 13 invocation. Model, credential, inputs,
order, caps and stop rules remained as designed. No returned tool was executed.

## Observed result

Anonymous grades were frozen before arm mapping. Under the registered selection
rubric, A selected a discriminating case in 0/12 responses and B in 5/12. This is
a reviewer judgment about selected evidence, not five discovered bugs or better
task acceptance. All A responses chose registered checks; B chose eight probes
and four checks. Relevant existing checks are legitimate verification actions.

| Case | A, two responses | B, two responses | Interpretation |
| --- | --- | --- | --- |
| P: Pydantic | Existing synthetic-history check twice | Unsupported expectation twice | Neither B response retained the provider-profile provenance condition. |
| H: HF Hub | Existing endpoint check twice | Discriminating probe twice | Ambient-only versus explicit HfApi endpoint with the same effective endpoint and refresh route. |
| F: Fromager | Existing orphan-removal check twice | Justified no-counterexample; discriminating probe | ROOT retention control, then surviving versus temporarily remaining parent in converging removal. |
| L: Loguru | Existing invalid-format check twice | Unresolved scope question; existing check | Nested-extra KeyError is a concrete question, but different required diagnostic was not established. |
| D: PDM | Existing exclusion check twice | Justified no stronger counterexample; existing check | No new supported cause for the earlier PDM failure. |
| G: pgmpy | Existing ABC check twice | Discriminating probe twice | Four-node examples test neighbor refresh between conditioning rounds. |

B categories: five discriminating selections, two justified no-counterexample
responses, two relevant non-discriminating selections, one unresolved scope
question, and two unsupported expectations. No refusal, incomplete response,
read request, mutation or submission occurred. All 24 responses had completed
status and single-action shape; shape is not tool admission or semantic validity.

The strongest concrete change is H: B selected the explicit-versus-ambient
distinction twice without receiving the operator's counterexample. Earlier
[public replay](2026-09-29-boundary-discrimination-replay.md) independently exposed
that boundary in the candidate. These newly generated programs have not run.

P shows a remaining interpretation failure. B repeat one described a copied
provider profile but constructed a fresh OpenAIModelProfile with only field mode
and a custom field name, then expected empty-field insertion. The task preserves
plain profiles unless given the provider profile. Repeat two asserted all
guard-satisfying field-mode messages require insertion and denied the supported
exception. Thus the added instruction can produce a probe that endorses the
candidate's erroneous generalization instead of challenging it.

F/G selections test plausible mechanism boundaries in candidates that appear
correct; they do not establish defects. F repeat two overlaps the already
registered shared/diamond graph shapes, so it adds explicit diagnostic rationale,
not demonstrated new check coverage. G adds a concrete between-round refresh
example beyond the registered three-node example. L's nested-key probe leaves
normative scope undecided; it is not evidence of a newly discovered Loguru bug.

## Grading limits and execution readiness

The same investigator reviewed randomized anonymous completed pairs as collection
continued, freezing each batch before mapping. Sample IDs, public decisions and
programs were visible; arm, repetition and usage were hidden. Wording can reveal
the treatment, so this is not independent blinded evaluation. The final collection
also emitted its independently shuffled review artifact. All 24 grades were
combined and hash-journaled before mapping. All samples remain in the denominator.

The primary tally requires a concrete applicability/lifecycle distinction and
an independently supported outcome, not just a relevant regression example or
use of the word "falsify." Ordinary catch-mode and path-relation checks remain
useful even when they do not meet this narrower rubric. F's temporary-parent and
G's between-round cases require investigator judgment about lifecycle scope.
Excluding those control selections leaves H alone: A 0/2 versus B 2/2. Neither
view establishes a general quality gain across tasks.

All eight probe programs parse as Python. Actual registered admission, dependency
availability, setup validity and observations are NOT_RUN. H assumes controlled
module-import timing; its setup checks test the effective endpoint. Both G
programs import pgmpy (one also imports pandas) despite the visible stdlib-only
dependency environment. Replacing DataFrame with DummyData in one program does
not remove package import dependencies or prove API compatibility. L imports
workspace Loguru; its transitive requirements are unverified. Project source is
mounted, so a non-stdlib import alone is not proof of failure. One G program
checks literal variant/depth values instead of observing constructed settings.
Do not silently repair any program or substitute an evaluator image and call
that agent probe execution.

## Accounting and integrity

- Terminal: SAMPLES_COLLECTED; 24/24 responses, 24 input counts and 24 provider calls.
- All 24 dispatched request identities match frozen cells; source journal/envelope
  bindings and runtime/design hashes revalidated after collection.
- A cost USD 0.639778; B cost USD 1.815754; total USD 2.455532, all billing known.
  Unused USD 10.544468 is closed; no retries, replacements, resume or extension.
- Whole collection: 1,597.607 seconds. Summed provider-call intervals: A 302.588
  seconds, B 1,278.628 seconds. B cost about 2.84 times A and took about 4.23 times
  its provider time; these are this sample's measurements, not fixed overheads.
- No task tool execution, repair, isolated acceptance or safety evaluation occurred.
  All remain NOT_RUN; official=false, claim_eligible=false, adoption disabled.

Evidence roots:

- Frozen packet: C:/pt/analyses/discriminating-case-selection-20260929-v1/packet.json
- Live content-addressed artifacts and dev-run-v1 hash chain: C:/pt/caseselection0929a
- Approval, anonymous exports, batch grades, grades-frozen.json, mapped-grades.json,
  summary.json and review hash chain:
  C:/pt/analyses/selection-execution-20260929-v1

Preparation had 47 passing focused/shared-collector/documentation tests and Ruff.
Result work changed documentation only; documentation tests and diff checks passed.
The full runtime suite and mock solve were not rerun for this documentation update;
their results would not validate the collected selections.

## Decision and next question

Keep the baseline unchanged. The instruction changed verification choice and helped
select H's missing distinction, but did not repair P's requirement interpretation;
the full-run effect remains unknown. Do not automatically tune prompts or start
another solve panel from these results.

The next bounded question is whether the frozen model-selected programs produce
the predicted observations through the registered probe path without operator
corrections. Preserve all eight programs, including the unsupported P expectation
and possible environment failures, to separate selection, setup and reproduction.
That execution stage and any subsequent model repair are not performed here.
