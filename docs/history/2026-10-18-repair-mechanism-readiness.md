# Retention and judgment: execution readiness

Date: 2026-10-18. Provider-free preparation completed. Paid execution remains
**NOT_AUTHORIZED**; the frozen manifest is **READY_FOR_EXPLICIT_PAID_APPROVAL**.

## Problem and decision

The [four-arm validation](2026-10-17-repair-mechanism-isolation.md) established
local correctness and offline factor isolation, but did not finish fresh public
environment checks or resolve every execution-request default. These checks matter
because an environment failure or a different effective setting could obscure the
retention/judgment comparison before any repair-quality result was available.
The user authorized this preparation while retaining the prohibition on paid calls.

All nine public capability checks passed; no environment repair was needed. The
12 requests now bind the tested commits, actual imports, task/source/dependency
identities, prompts, limits, prices and public-only audit rubric. Keep the default
runtime and the [comparison specification](../../.agent/plans/question-support-comparison.md)
unchanged in behavior. This establishes preparation readiness, not repair success.

## Frozen execution packet

Evidence root: `C:/pt/analyses/repair-mechanisms-readiness-20261018-v1`.
Manifest: `execution-manifest.json` under that root, with SHA-256
`5d3304caf267cf01bccfbb86021def126a5af9b506a6a09932267654d6a2019b`.
It contains no dispatch entry point and records authorization as false.

| Arm | Tested commit | Focused retention / judgment support |
| --- | --- | --- |
| E0J0 | `33e95588a9fb204fd7a7635393004a38c026e3a8` | Off / off |
| E1J0 | `6c8e929a40f6de9d422ce87559ad968c83c91a24` | On / off |
| E0J1 | `bd2125757b711ad7bfe3de1adf5779173de35a0d` | Off / on |
| E1J1 | `116e970b6a51a7c921b278f60ccd39b5854b3037` | On / on |

Each clean checkout still matches its previously tested runtime bytes. The manifest
binds the existing full-suite receipts: **5,225 passed, 19 existing skips, zero
failures/errors per arm**. Product code did not change in this preparation; full
suites, replay and mock evaluation were not rerun. Their exact-head results and
limitations remain in the prior validation record.

Three dev-train tasks (13 Astroid-1333, 1 Marshmallow-1343, 9 Pydicom-1694), four
arms, one fresh repeat each: **12 rows**. Model: `gpt-5.4-mini-2026-03-17`, xhigh,
25,000 desired output tokens. Credential file:
`C:/Users/geonj/Documents/PatchLoop/.env`; existence checked, contents unread.
Row cap USD 0.88; invocation cap **USD 10.56**, also bounded to USD 2.64 per arm
and USD 3.52 per task. Unused allocation does not transfer.

The fixed row order is E0J0/13, E1J0/1, E0J1/9, E1J0/13, E0J1/1, E1J1/9,
E0J1/13, E1J1/1, E0J0/9, E1J1/13, E0J0/1, E1J0/9. Each row uses a fresh
interpreter importing its own arm and one settled row per wave; the worker ceiling
remains two. All waves share the invocation allocation and stop boundary. Ordinary
graded failure permits the remaining rows; count, transport, billing, cleanup or
assessor uncertainty stops admission. No retries, resume, replacements, extra
repeats, continuations or tuning of exposed cases are authorized.

Every `DevRunRequest` field is explicit, including `agent_policy=current`,
`probe_policy=none`, `probe_recheck=none`, `retained_source_chars=24000` and
`max_output_tokens=25000`. Unchanged: `segmented-v1/result-or-size-v1/brief-v1`,
two references, 24,000 source characters, 60,000 counted input tokens, 1,048,576
request bytes, 262,144 encrypted-item bytes, 40 model calls, 100 actions, four
accepted edits, 1,800 seconds including the 330-second evaluation reserve, zero
SDK retries, and 8,000/10,809 base/brief prompt maxima. Fresh solver state receives
no operator notes or preselected references. The audit rubric remains operator-only.

The official [model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
and [pricing](https://developers.openai.com/api/docs/pricing) were checked on
2026-10-18: the pinned snapshot supports xhigh; standard/global rates match the
registered USD 0.75 input, 0.075 cached input and 4.50 output per million tokens.
This public documentation check establishes no account/model access.

## Fresh public environment checks

| Task | Import | Ordinary operation | Selected public test |
| --- | --- | --- | --- |
| 13 Astroid-1333 | PASS | Infer `1 + 2` as `3`: PASS | `tests/unittest_brain.py::HashlibTest::test_hashlib`: PASS |
| 1 Marshmallow-1343 | PASS | Ordinary schema validation: PASS | `tests/test_decorators.py::test_decorated_processors`: PASS |
| 9 Pydicom-1694 | PASS | Ordinary DICOM roundtrip: PASS | `pydicom/tests/test_json.py::TestPersonName::test_json_pn_from_file`: PASS |

These nine checks test environment capability, not the target bugs or repair
acceptance. The selected tests use the existing first-public-test selector.
Shared environment-driver bytes, preflight functions, interpreter/dependency
versions and task/source/image identities match across all four arms, so checks
ran once per task from E1J1. All six existing probe/evaluator image digests match;
no image was pulled or built. Docker was already running and was not started.

All checks returned exit code zero, without timeout, deadline exhaustion,
truncation or cleanup failure; cleanup was confirmed and no owned containers
remained. Network was disabled and source mounts were read-only. Probe timeouts
remain 30 seconds, public tests 300 seconds. The native harness interpreter,
revision and file hashes match their pinned identity; native task evaluation was
not run. Its future 300-second test/600-second host limits remain unchanged.
Astroid emitted the existing `pkg_resources` deprecation warning and passed.

## Validation and remaining question

`manifest-validation.json` records 12 schema-valid resolved requests and rejection
of nine deliberately invalid variants: changed invocation cap, reference cap,
source budget, transition contract, model, row cap, duplicate state directory,
wrong arm commit and unapproved execution. This validates the frozen preparation
packet, not a new runtime authorization mechanism.

`closing-validation.json` records documentation layout/link checks, Ruff, diff
whitespace checks and final integrity comparisons. `post-commit-receipt.json`
binds the documentation commit and final report to the unchanged manifest.
The first closeout verifier incorrectly read the probe policy's `network` field
from a registered-test receipt. The follow-up validates each receipt's actual
schema, including `requested_network=none` for registered tests; no runtime limit
or assertion was relaxed. The original attempt and passed checks are preserved.
The prior three evidence packets and all previously tracked historical reports
remain byte-identical; the unrelated local `AGENTS.md` edit is preserved.

Public/private boundaries remain unchanged: only public task data and capability
results were inspected; private task-package bytes were hashed opaquely. No
provider-generation, availability or token-count API call was made. Cost is
USD 0. The reserved live state root `C:/pt/repairmechanisms17live01` remains absent.
Account access, real count admission, autonomous repairs and independent task
acceptance are **NOT_RUN**. A later authorized dispatch must recheck the exact
manifest, identities and rates before spending.

The unresolved question is whether E or J changes actual repairs within these
limits. Retention exposure may be absent, and J metadata can affect evidence
delivery at size admission; retain both observations in the audit. Three exposed
tasks with one repeat per arm support a descriptive pilot, not significance or
generalization claims. No paid execution or default adoption follows automatically.

Evidence in the external root: `preparation-result.json`, four
`<arm>/resolved.json` inspections, `shared-environment-validation.json`,
`environment-summary.json`, three `environment/task-<index>.json` results,
`local-images.json`, `native-identity.json`, `official-price-review.json`,
12 `requests/*.json` files, `operator-only-audit-rubric.md`, and the append-only
hash-chained `runs/run_dev_repairreadiness18.jsonl` journal.
