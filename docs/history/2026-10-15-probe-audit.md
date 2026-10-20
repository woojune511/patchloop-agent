# Public diagnostic audit outside SQLFluff

Date: 2026-10-15. Existing-record audit only. No new model, input-count,
diagnostic, task-test or evaluator execution. No private test, reference patch,
evaluator-output artifact or reasoning content was inspected. Existing terminal
acceptance/safety metadata supplies the outcome, not repair hints.

## Decision

Keep the runtime baseline, prompts, memory/context limits and tool gates.
The SQLFluff B1 configuration/expectation mismatch did **not** recur in the same
form in these three selected problems. A different pattern is visible: useful
but partial public observations were extended to broader repair or completion
claims. The concrete missing distinctions differ by task.

All five probes completed without timeout, truncation or cleanup failure; all
16 supplied setup comparisons matched. Exact stdout reached the next dispatched
model request and remained in the relevant later edit/finish inputs. This does
not establish correct expectations, complete setup, model attention or repair
correctness. No current tool/delivery contract violation was demonstrated.

| Problem | What the existing diagnosis established | Subsequent action and unresolved gap |
| --- | --- | --- |
| Astroid-1333 | Directly loading an existing directory raises `IsADirectoryError`; a separate module-path lookup resolves names under explicit `sys.path` settings. | Changes `source=True` to `os.path.isfile(filepath)`, then submits after 1,231 public tests pass. The public failure loading absent `project/__init__.py` was not reproduced through an equivalent caller, and the edited behavior was not probed. |
| isort-2491 | Two inspected comment maps differ; both chosen comment samples reach `wrap.line`, and the intermediate broad patch moves an item comment incorrectly. | Explicitly revises the hypothesis and narrows the patch to `type: ignore`; 73 public tests pass. Two unobserved comment categories and original-position versus comment-text ownership remain unresolved; no probe follows the final edit. |
| OpenSandbox-816 | The edited helper accepts a clean sibling path and rejects an intermediate symlink with the asserted error. | Keeps the patch and submits after 108 public tests and the helper probe pass. The separate public requirement for strict host-volume resolution, including the caller path, is not established. |

All three existing submissions have acceptance **FAIL**, safety **PASS**, and
`claim_eligible=false`. These are selected failures, not a performance sample.
An explicit hypothesis change, a good local diagnostic and a correct final
repair are different observations. In particular, isort contradicts a universal
explanation that the model simply refused to revise its hypothesis.

## Selection and evidence boundary

The question was whether the [SQLFluff uptake](2026-10-15-uptake-grade.md)
investigation warranted a general harness change. Recurrence matters because an
extra rule, memory field or gate would affect every task. Alternatives fixed
before inspecting probe programs were wrong expectation/configuration,
unsupported extension of valid observations, delivery loss, and setup failure
before target behavior.

Selection used metadata: OpenAI, `dev-train`, completed `EVALUATOR_FAIL`, an
actually executed public `run_probe`, no SQLFluff and no fork/import history.
Order was latest completion first, one run per distinct problem, at most three.
The initial six recent cohorts contained 90 run locations and only Astroid-1333
qualified. Before reading selected probe programs/results, the scope was
explicitly expanded to 36 older locations in known non-mock run directories and
the linked baseline comparison. The original plan's no-expansion clause was
superseded in a separate scope amendment; the original plan/selection remain.
This is a bounded historical search, not an exhaustive registry census.

A metadata classifier initially matched `forked` rather than the actual `fork`
event names. That was corrected before case interpretation. Five OpenSandbox
forks were excluded; the original run was retained. Final selection is three
eligible runs among 126 locations, representing three distinct problems.

| Problem | Original state root and run | Model / historical runtime |
| --- | --- | --- |
| Astroid-1333 | `C:/pt/cd20live06c/13`, `run_dev_4973e7b5f39a4978` | `gpt-5.4-mini-2026-03-17`; `db912ef8...` |
| isort-2491 | `C:/pt/runs/fixed-batch-20261001-v1/original-isort-2491`, `run_dev_49397fa9568d4b80` | `gpt-5.4-2026-03-05`; `dfd10fb7...` |
| OpenSandbox-816 | `C:/pt/runs/fixed-batch-20261001-v1/original-opensandbox-816`, `run_dev_75ec90f0be654c84` | `gpt-5.4-2026-03-05`; `dfd10fb7...` |

All three journal chains verify. The 60 dispatched request artifacts were
checked against their hashes and matched to counted-request and dispatch hashes.
The actual historical `public_task` messages are the authority; current public
specifications also match their envelope canonical hashes. Private packages
were not loaded. Run/model/configuration differences prevent a causal comparison
or an estimate of current-head quality.

## Astroid: a related failure is not yet the public failure

The public task describes `pylint src/project`, with `src/__init__.py` present
and `src/project/__init__.py` absent. Its error names the absent init file.
Action/result **310/311** instead calls `AstroidManager.ast_from_file(project_dir)`
on the existing directory. Four setup comparisons match. The program catches
`AstroidBuildingError` and prints `IsADirectoryError`; normal exit is therefore
diagnostic completion, not proof that the bug is fixed.

Action/result **352/353** asks whether `modpath_from_file(project_dir)` resolves
under two explicit settings: `sys.path=[root]` and `sys.path=[src]`. Five setup
comparisons match and the outputs are `['src', 'project']` and `['project']`.
That result answers its local question. It does not demonstrate successful
module loading, and the first probe did not supply those same `sys.path` settings.

Inputs **314/356** deliver the respective programs, setup receipts and stdout to
the next actual dispatch. Input **397**, dispatched at **401**, retains both
complete stdout strings before edit **407**. Its public hypothesis connects
the directory failure and name-resolution result to a one-line source change.
The model repeatedly plans a regression test, but the only accepted mutation is
in `astroid/manager.py`. Result **421** reports 1,231 public tests passing.
Input **425** still retains both probes, labelled historical on the new diff.
Finish **436** says no further public evidence is needed.

The source read at **64** shows module-name loading after the source-file branch;
the read at **95** shows `get_source_file` rejecting absent source files. The
record never establishes that changing directory handling fixes the public
missing-init caller path. This supports a reproduction/verification gap, not a
claim about the exact private failing assertion. A future discriminator would
bind the public symptom to the actual available same-process entry point and
check that behavior after editing; subprocess access is not assumed.

## isort: hypothesis revision with an unsupported discriminator

The public expectation is that a comment on the opening import line stays
there; `mypy` is given as an example. The first edit, **106**, hoists comments
broadly. Registered result **125** then has three failures and 70 passes.
The model reads those public regression expectations before revising.

Probe **219/220** uses `Config(line_length=88, use_parentheses=True)`. It prints
`categorized_comments['from']`, `['nested']` and the alias map. The issue sample
has empty `from`/`nested`; the item-comment control has a populated `nested` map.
Read **205**, already available when the probe was authored, lists two more
categories: `straight` and `above`. Read **191** shows the alias output path
reading `straight` at lines 402-403. These categories are not printed by the
probe. Nevertheless, public decisions **237/255** infer that the opening
comment is not stored in parser comment maps. Absence from two maps does not
establish absence from all maps.

Probe **270/271** uses the black profile and instruments the original formatter
functions without replacing their behavior. It shows both selected cases
reaching `wrap.line`. On the intermediate broad patch, the opening-line
`type: ignore` stays up, but the ordinary item comment is incorrectly moved up.
The two programs' configurations are explicit and their setup values match.
They have different diagnostic purposes; a configuration/expected-value
mismatch like SQLFluff B1 is not observed.

The next dispatch uses input **274**, containing the exact program, setup and
stdout, but returns `incomplete_response/max_output_tokens` at 25,000 tokens
with no tool calls. The next completed response uses input **286**, which still
contains those details. Input **321**, dispatched at **325**, retains both probe
stdout strings. Edit **331** explicitly falsifies the all-comment hoist and
adds the condition `"type: ignore" in comment`. This is observable revision.
However, the selected samples change both original comment position and text;
they do not distinguish preserving position from keyword-specific relocation.
The public search result **316** merely includes a test asserting that the
`type: ignore` text survives formatting, not its required position.

Automatic registered recheck **337** passes all 73 tests on the final diff.
No probe executes on that diff. Input **339** retains both now-historical probe
results; finish **349** says no concrete uncertainty remains. A future narrow
discriminator would keep text/configuration constant while varying opening-line
versus item placement, and inspect all ownership categories before selecting
where to repair. This audit proposes that distinction; it does not execute it
or assert an unobserved output.

## OpenSandbox: valid helper evidence, incomplete requirement closure

The public issue asks both for component-level symlink rejection in
`ensure_valid_host_path` and for host volumes to match PVC strict resolution.
Edit **97** changes only the shared validator. The source read at **31** shows
`_validate_host_volume` using `normpath` for a `sub_path` and conditionally
revalidating via the helper; no `docker.py` change is submitted.

After registered result **111** reports 108 passes, probe **126/127** creates
a real scratch symlink to `/` beneath an allowlisted directory. Three setup
checks confirm the absolute path, symlink and target. It asserts that a clean
sibling returns `None` and that the intermediate symlink path raises HTTP 400
with `INVALID_HOST_PATH`. Both assertions succeed. This is useful positive
evidence, consistent with the first public requirement, on the submitted diff.

Input **131**, dispatched at **135**, contains the exact program, setup and
stdout across the result handoff. Finish **141** cites the observed outcome
and submits without another edit. The direct helper call does not establish
the separate strict-resolution requirement or the complete caller path.
The public check's line feedback was `unknown`, not proof of unexecuted lines;
its stdout was truncated, while the diagnostic stdout was complete.

The supported conclusion is limited: a valid local PASS was treated as enough
to close the public task. This is not an ignored negative diagnostic or a
demonstrated bad expected error code. No private failure detail or new exploit
is inferred. A future check should distinguish helper correctness from the
public host-volume caller and strict-resolution requirement.

## What changes, and what stays

The investigation changes the working explanation from a universal wrong
expectation or stubborn-hypothesis story to **incomplete diagnostic scope and
overextended completion claims**. It does not identify one shared implementation
defect. It also does not show that more probes alone would improve repairs:
OpenSandbox already probed the final diff, and isort already revised its hypothesis.

The existing historical prompts and current `dev/model.py` already instruct
the model to limit conclusions to observed inputs. Current probe descriptions
also separate setup, execution and behavioral verification. The final requests
retain `behavior_verdict=not_assessed`, questions and diff currency. Full old
programs/setup receipts are not in every later compact input, so this is not a
claim of lossless memory; exact diagnostic stdout was not lost in these decisions.

`run_probe` remains offered in all three final inputs. Their displayed remaining
time is approximately 910 solver seconds, 281 seconds and 1,422 seconds,
respectively. isort's incomplete response and lower time/cost headroom leave
resource pressure plausible; availability does not guarantee another affordable
generation. No observed gate forces these three submissions.

No prompt addition, compulsory probe, memory expansion, pruning change, looser
tool access or setup-expectation gate is adopted. The actionable future question
is narrower: can a diagnostic distinguish the promised public behavior from a
plausible partial repair while holding unrelated inputs fixed? The isort
position/text distinction is one concrete candidate. It is not a queued run or
an adopted feature. A later implementation proposal still needs a specific
mechanism and a bounded comparison of final repair quality, regressions and cost.

## Evidence and validation

External audit root: `C:/pt/probeexpectaudit01`. Append-only journal:
`runs/run_dev_probeexpectaudit.jsonl`. Original plans/selections, scope amendment
and classifier correction remain alongside the final selection. Public artifact
projection and conclusion are separate from the immutable historical records.

| Artifact | Content hash |
| --- | --- |
| Final selection CAS | `sha256:b9230564b4a75c164bd8b47d06f77d2c8a2b02bcf86fff70d2452123df4fad48` |
| Public projection CAS | `sha256:e061c536d00b0beb489c253ecb313ad5123090a7443b0f4ed30ebb3776533bff` |
| Conclusion CAS | `sha256:66d70c6d4f96f566671301ae2f32a1247a42aa4a7a2fb470ba5d4cacf4bb3872` |
| `conclusion.json` export | `sha256:17132f1fa599e3f4c455374b29dce15e64dc72d3cc6878be0cea1e1b4107da15` |

Baseline HEAD: `e35ca5923b3b33c81078444a8cf88d31cc8ca5d7`. Current runtime source
is unchanged. Documentation layout/link checks and source/artifact hash checks
are the only validation performed for this follow-up. Model/count/diagnostic/
task/evaluator execution remains **NOT_RUN**; added provider cost is **USD 0**.
