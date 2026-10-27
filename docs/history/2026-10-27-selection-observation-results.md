# Public-observation A/B: both candidates fail acceptance

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run, then public-evidence validation
- Origin Date: 2026-10-27
- Verification Status: EXECUTED / ANALYZED; stochastic replication NOT_RUN
- Version Label: selection-observation-results-v1

## Question, scope and disposition

The [prepared comparison](2026-10-27-selection-observation-plan.md) asked whether
operator-curated public selection/resolution/parsing observations help the same
mini model repair Astroid-1333 from clean base. Both arms produced one edit, but
neither resolved the original F0010 or passed isolated acceptance. B also broke
the ordinary-package semantic control. Do not adopt the packet as an effective
repair policy from this pair; production defaults stay unchanged.

The user authorized A/B once each, total $2.40, under the prepared conditions.
The task, model, xhigh setting, credentials, tools, budgets and model input bytes
were preserved. Each arm used a fresh clean base, not an old candidate. All 15
provider responses have settled usage. The allocation is closed at **$0.3003564**;
no extra model run, repair continuation or evaluator retry was performed.

## Pre-dispatch correction

Original manifest `48ab06c60cc258978e216dec8afe26efe3baec8febf2706ea84bf5de411154e3`
failed before credential loading/counting/generation/target execution: the harness
read nonexistent `dependency_hash` from `DockerProbeSandbox.preflight()`, which
returns image/profile identity. Commit `751dc391` reads the separately verified
dependency manifest identity and records it alongside probe identity. A regression
test reproduces the actual two-field preflight contract: 14 focused tests passed
in 4.77 seconds. No runtime defaults or scientific condition changed.

The failed root is preserved at `C:/pt/selection-observation-live-v1` with zero
provider calls. A corrected, separately sealed manifest lives at
`C:/pt/selection-observation-plan-v2/manifest.json`, hash
`sha256:b2e3fdd9b74c49543bba87d13c3b3f46e5e3040afc95d05240aec1c65df76f14`.
`preflight-correction.json` binds the original approval to the corrected operator;
scope, credential path and both first-request hashes are identical. The actual
one-per-arm model collection is `C:/pt/selection-observation-live-v2`.

## Results

| Measure | A: original failure | B: additional base observations |
| --- | --- | --- |
| Normal responses / corrections | 8 / 0 | 7 / 0 |
| Model tool actions | 12 | 9 |
| Model diagnostic probes | 1 | 0 |
| Accepted edits | 1 | 1 |
| Model cost USD | 0.2425758 | 0.0577806 |
| Model phase seconds, from clean-base receipt | 329.140 | 44.857 |
| Public check phase seconds | 96.390 | 97.791 |
| Original call-1 conditions match base | yes | yes |
| Original F0010 resolved | no | no |
| Standalone control output unchanged | yes | yes |
| Empty / import / invalid namespace fixtures | F0010, child omitted | F0010, child omitted |
| Direct invalid-file control | E0001, exit 2, unchanged | E0001, exit 2, unchanged |
| Ordinary-package invalid-child control | E0001, exit 2, unchanged | empty output, exit 0, child omitted |
| Registered public regression | 1,231 PASS | 1,231 PASS |
| Isolated acceptance | FAIL | FAIL |
| Isolated regression / scope / safety | PASS / PASS / PASS | PASS / PASS / PASS |

Both public regression runs also report 69 skipped and 15 xfailed. Public case
fixtures, caller conditions and candidate hashes remained fixed. Call-2 input
identity also happened to match in both original replays; its known cache-related
identity issue did not affect this outcome. The evaluator ran once per candidate
and returned only safe verdict/identity summaries to this analysis.

All generation requests kept the exact assigned packet once. A's first request
hash was `38d9ca5963416bb88ab6ec386c07e98efb552fd6505e90596f5d02723d647625`;
B's was `d01ed41dff95b7edca6bddbdbd099ad7c575ed9e0941d898722cc9cf64d54fae`.
B's 6/6/9 supplementary events were preserved across all seven requests. A did
not receive them. No cost-based opportunity narrowing occurred; all response
ceilings remained 40K. Maximum counted input was 30,354 / 22,771 and maximum
actual output per response was 26,138 / 1,716 for A/B. Both stopped because an edit
was produced, not because a context, output, money or time cap was reported.
A used all normal/action slots; these observations do not prove extra actions
would be useless. Lower B cost/time is not a repair-efficiency improvement when
both repairs fail.

## What the public evidence explains

**A:** The patch in `check_modpath_has_init` replaces `join(modpath)` with a slice
ending at `modpath.index(part) + 1`. The hypothesis says the old code checked the
full path instead of the current prefix. Source shows `modpath=[]` and an append
per iteration, so it already contains the current prefix. For nonrepeated names
such as src/project the expressions are equivalent. They can differ for repeated
component names; this is not a universal no-op claim. Changed executable lines
268-269 were not observed in the collected original/syntax probes, within their
Python launch-thread scope. This supports a wrong premise and an irrelevant edit
for the measured failure, without claiming exhaustive branch coverage.

A's one helper probe called `modpath_from_file` on a temporary file without the
needed search path. Its first ImportError ended the helper before the later
comparison loop. It did not invoke the original `pylint.Run`. The complete capture
and confirmed cleanup distinguish this known helper failure from infrastructure
uncertainty; the host independently replayed the original after the edit.

**B:** The patch in `_get_relative_base_path` adds `__init__` when the resolved
input is a directory. This runs opposite to its stated expectation of avoiding a
fabricated initializer. In the missing-initializer selection helper, modpath now
returns `["__init__"]`; file_info raises `No module named __init__`, module_files
returns empty, and the same nonexistent initializer produces F0010. Changed lines
were observed, but whole-helper line entry must not be attributed to a particular
internal call without the corresponding wrapper event.

In the ordinary-package control the model changes `["src", "project"]` into
`["src", "project", "__init__"]`. The public caller sees PY_SOURCE and an explicit
`.__init__` name. Its `has_init` condition is false, and neither namespace nor
directory classification restores recursive discovery. The actual event list has
no module_files call and selects/builds only the initializer. The invalid child
therefore disappears from checking. This is a newly introduced public semantic
regression despite the registered suite passing.

The additional packet was delivered and B changed the path-resolution function,
but no model probe tested its proposed directory conversion before the one edit.
The unresolved decision is how to turn observed call-path facts into a testable
repair premise and check the proposed transformation. This pair does not establish
that more context, money, another model or new agent machinery would solve it.
No further intervention was executed under the unused allocation.

## Integrity and statistical interpretation

Public audit verified journal chains, receipt bytes, per-response billing,
first requests, persistent packets, clean bases, candidate immutability, fixture
equivalence, original results, public regression and safe acceptance summaries.
No evaluator logs, hidden tests, reference patches or full evaluation artifacts
were opened or projected into coding/model context.

Fallacy scan coverage: **11/11 considered**, no inferential statistics performed.

| Check | Disposition |
| --- | --- |
| Simpson / ecological | No pooled subgroup statistic; no task-population inference. |
| Berkson / selection | Development-exposed, selected failure and operator-curated evidence; limited scope. |
| Collider | No post-outcome adjustment; both assigned arms retained. |
| Base rate | No model-accuracy or predictive-rate estimate. |
| Regression to mean | Historical failures are not a before/after control. |
| Survivorship | Both failures and the zero-call preflight interruption are retained. |
| Look-elsewhere | All prespecified public/acceptance outcomes reported, including B's new regression. |
| Forking paths | Frozen design; disclosed metadata-only pre-dispatch correction. |
| Causal overclaim | One stochastic run per arm cannot establish general benefit or harm. |
| Reverse causality | Packet precedes each model run; its post-solution human selection is disclosed. |

No p-value, general success-rate claim, repeated-model reproducibility claim or
automatic policy adoption follows. The separate accepted operator candidate
remains valid evidence of task repairability, not evidence of model success.

## Evidence locations

- Result: `C:/pt/selection-observation-live-v2/result.json`,
  `sha256:75cf653c10b80abe1a930ddd57ff2242c64de6ddaa9e0e710b88d4bfb059a0bd`.
- Audit: `C:/pt/selection-observation-audit-v1/audit.json` and `audit.py`.
- Top journal: `sha256:4cc8b4c63ce1838f190a8a2bf315c4decce2cf0e87a081737eade236902e58e9`.
- A patch: `sha256:93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5`.
- B patch: `sha256:e73d9de3c9e17f49d8b71a2fc3f3ee6430bba399ae77366b908ce74dbad723d1`.
- Safe evaluations: `A/acceptance/summary.json`, `B/acceptance/summary.json` under result root.
- Runtime: `sha256:5753dbef010721c721db788aa01525fc269ad12093b46e45ffc2ffd158c929f3` unchanged.

The two benchmark-model candidates stay in external workspaces and are not applied
to PatchLoop. Only the known harness metadata defect and evidence documentation
changed in this execution turn.
