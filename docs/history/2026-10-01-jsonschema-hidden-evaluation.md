# jsonschema hidden evaluation follow-up

## Decision

The user confirmed that hidden checks are required. Preserve the existing
acceptance rule: hidden, public regression and scope checks must all PASS.
Do not make public-only packages successful or weaken the evaluator. The previous
package omitted required evaluation evidence; this was a preparation defect.

Keep the original version 1 package and live FAIL record unchanged. Add
`tasks/dev-train/jsonschema-regex-recursion-1538-v2`, retaining the task ID and
incrementing task_version to 2. Original public issue, source pin, public check
commands, constraints and image are unchanged. Private v2 binds the hidden script
by content hash; it never enters coding-agent context.

Task content hash:
`sha256:e54cabb8af158bdf0288b8d325afd440ae8478540a36525bbb129669b8677256`.

## Hidden checks and calibration

Six unittest methods cover deep balanced/unbalanced patterns across six draft
validators, iter_errors/is_valid/validate behavior, direct FormatChecker error
conversion and cause identity, ordinary valid/invalid patterns, non-string values,
and propagation of unrelated RuntimeError/TypeError. These exercise behavior beyond
the public four-case contract, without requiring a particular implementation.

The suite and task hashes were frozen in an external journal before execution.
A subsequent Ruff-only context-manager flattening changed no assertions; both
hashes and the earlier replay are retained, and final bytes passed a second
provider-free isolated replay.
Baseline source fails; accept-all, reject-all and overbroad exception-catching
mutants also fail. The saved submission passes all six methods. The existing
approved local image was used with network disabled and confirmed cleanup;
no image build, pull, provider call or credential loading occurred.

These checks were authored after inspecting the submitted patch. They are private
from the coding agent but are post-run development checks, not a pre-registered
held-out trial. A positive result supports these behaviors, not independent
generalization or a causal improvement in the agent.

## Saved-patch evaluation

Origin run: `run_dev_c6b70ef10dfb4926` (preserved EVALUATOR_FAIL).
Replay: `run_dev_jsonschema1538hiddenfinal`.
Submitted bytes remain
`sha256:1cf85e65f9fead3400c77d52ddb70003174517260a82ea62910764d09ca741da`.

A separate manifest binds version 2 task hashes and the unchanged submitted
patch. Its model metadata identifies the original producer only; this replay
made zero model/token-count calls and incurred zero additional model cost.
EvaluationEngine evaluated in a fresh prepared-source workspace and returned:

- hidden_tests PASS (six methods with subtests);
- regression_tests PASS (public contract and eight upstream tests);
- scope_policy PASS;
- safety_policy PASS;
- scope_compliant_success true; official=false.

The evaluator took 9,137 ms. This is a separately identified saved-patch evaluation,
not another autonomous solve and not a revision to the original run's terminal.
No runtime acceptance logic changed, and no evaluator output was fed to the agent.

External evidence root: `C:\pt\evaluations\jsonschema-hidden-v2-20261001`.
Calibration journal: `runs/run_dev_hidden1538admission.jsonl`.
Replay journal: `runs/run_dev_jsonschema1538hiddenfinal.jsonl`.
Manifest/result: `replay-artifacts/runs/run_dev_jsonschema1538hiddenfinal/`.

## Validation and next boundary

Package CLI admission, 17 focused package/classification tests, documentation
checks and Ruff pass. Tests bind hidden inventory, reject modified/missing hidden
files, and exclude private data under both conversation policies. The real saved
patch ran through complete isolated aggregation; command calibration alone is no
longer the readiness evidence. No runtime change requires repeating the prior
full suite; no new paid or mock agent run was performed.

Future task readiness must include actual hidden checks and an end-to-end isolated
calibration, including rejection of the baseline and plausible wrong repairs.
No new paid allocation or automatic next experiment is authorized.
