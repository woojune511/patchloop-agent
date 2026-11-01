# Public repair alternative and comparison readiness

Date: 2026-10-29. Runtime baseline: `1f7c26f0`. Operator-authored local
diagnosis, a bounded source-delivery fix and zero-provider rehearsals. No paid model,
real input count, Docker
or private evaluator execution. Historical runs and task artifacts are unchanged.

## Question and decision

The preceding [finish-choice audit](2026-10-29-finish-choice-local-audit.md)
excluded immediate resource exhaustion at A's unchanged submission, but did not
establish a correct alternative repair. The user requested continuing that work,
forecast comparison preparation and edit-quota selection. A useful intervention
needs a concrete failure mechanism, not another generic finish instruction.

The local comparison now establishes a small public-source alternative for
Astroid-1333 under the tested Windows conditions. It also reveals a distinction
between previously observed source and source present in the decisive request.
The saved B boundary exposed a source-delivery defect: relevant source had been
selected within the existing bound, then removed while edits remained available.
The follow-up preserves that selection; it does not inject the operator repair.
Verify the corrected request before a repair-quality forecast comparison. Do not start a
4-versus-12 quota comparison from traces uniformly capped at three.

## Public mechanism and smallest alternative

Public task: `tasks/dev-train/current-dev20/13/public.yaml`, base
`d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`. Public task SHA256:
`bd47d10d4eb19d9db18dcccf04e27019f6307139b4d8841ec505b439135c4412`.
The saved A candidate diff is
`sha256:1ac127d0b6c304ac53f23ba4724953b59e25e665926f2b00bae9253af9d6ad57`.

The actual caller is pylint 2.12.2, running `pylint src/project -sn --score=n`
where `src/__init__.py` exists, `project/__init__.py` is absent and `file.py`
contains `import os`. This is the public issue's reproduction, also executed by
A's own probe at start236/result239.

The saved repair changes `_spec_from_modpath`'s package-directory branch when
`_has_init` returns None. In the ordinary observed filesystem state,
`ImportlibFinder` returns that package type only after finding an initializer;
the added return was not reached in probe239's coverage. The earlier problem is
that `_get_relative_base_path` compares an absolute filename against a search
root that can still be literal `.`. Pylint supplies that relative root, then falls
back to module name `project` when resolution fails and queues a nonexistent
initializer. The minimal alternative changes one line in `astroid/modutils.py`:

```diff
-    path_to_check = os.path.normcase(path_to_check)
+    path_to_check = os.path.normcase(os.path.abspath(path_to_check))
```

The experiment distinguishes this explanation from a sufficient package-type
classification fix. If corrected module-name resolution still produced F0010,
normalization would not be sufficient. An absolute-root control distinguishes a
general resolver defect from relative-root handling; an initializer-present
control checks the already-working caller path.

## Executed local comparison

Four fresh Git copies use the same exact public base and dependency source.
The saved candidate is applied as its exact patch; the normalization is the only
additional change. Each arm/control gets a fresh subprocess. The temporary caller
cwd is explicitly absent from `sys.path`, preventing implicit cwd lookup from
masking the failure. The real pylint call runs before helper inspection.

| Source | Missing initializer | Initializer present | Relative `.` helper |
|---|---|---|---|
| Exact base | F0010; `file.py` not observed | No F0010; `file.py` inspected | None |
| Saved candidate | F0010; `file.py` not observed | No F0010; `file.py` inspected | None |
| Base + normalization | No F0010; `file.py` inspected | No F0010; `file.py` inspected | `src.project` |
| Candidate + normalization | No F0010; `file.py` inspected | No F0010; `file.py` inspected | `src.project` |

All eight caller/control assertions passed. Actual inspection requires W0611
on `file.py`, not merely absence of F0010. The absolute-cwd helper produces
`src.project` in every arm. Thus the minimal alternative does not need the saved
candidate's extra classifier branch; candidate-plus-normalization also models a
possible subsequent edit without first undoing that candidate.

The unmodified public `tests.unittest_modutils` module ran in all four arms:
**43 passed and the same three symlink-related host errors per arm** (46 tests).
No new failure appeared within those executed cases. These are not a clean full
regression PASS: the host lacks required Windows symlink permissions and one
dependent symlink path cannot be created. No test was weakened or edited.

Environment: local CPython 3.10.20 on Windows, existing prepared pylint 2.12.2,
wrapt 1.13.3 and other public dependency sources. Portable import fallbacks allow
reuse of that prepared tree without installing packages. This differs from the
historical Linux sandbox. The original registered Linux full regression, hidden
acceptance, safety and general correctness remain NOT_RUN/unestablished.

The first diagnostic harness attempt failed during Windows temporary-directory
cleanup because its cwd had not been restored. It is retained and excluded. The
v2 script restores cwd in `finally`; it preserves the caller/source conditions.
All copies, scripts, patches and observations remain outside the repository.

- Audit journal: `C:/pt/finish-alternative-20261029-v1/runs/run_dev_relativepathalternative.jsonl`
- Eight-case CAS report: `sha256:2b4f055c8996f06af70c9013dfcff8ae2c98f141f35aed268dd95435075daace`
- Reviewable patch: `C:/pt/finish-alternative-20261029-v1/alternative.patch`
- Patch identity: `sha256:bccca60f05bb2728d9d0da07319fd35891bb6c4525e2bf3ea60b3d38b00af1d4`
- Probe script/runner v2 and their exact outputs are bound by journal CAS references.

This is an operator repair diagnostic, not a successful solver continuation or
independent acceptance. Do not feed the proposed replacement to a repair-model
comparison and call that model improvement.

## What the decisive inputs actually contained

The relevant old line was observed in read action39 (240–320), and mutation195
revalidated source200–470 against the candidate. However, actual prepared public
inputs A247, B261 and B277 contain neither `_get_relative_base_path` nor its
`path_to_check` replacement line. The source-visibility audit excludes encrypted
reasoning and exports hashes/presence, not raw reasoning.

This narrows the prior interpretation: failure stdout was delivered, but the
specific repair source was absent. It does not establish that the model knowingly
ignored the correct line, nor prove source omission caused its choice. A had four
ordinary responses: read + successful edit + required check + finish could fit,
with no additional diagnostic response. B had three and already lacked read/search.

## Forecast-only rehearsal

The reusable B checkpoint is cut258, after the public read batch through257.
Existing `observation_exposure.fork` and `ScriptedClient` were sufficient; no new
collector or runtime policy was added. Both forks preserve the B observations.
OFF omits only `action_horizon.action_budget`; ON retains it. Policy calculation,
tools, source, quotas and system guidance stay the same.

Both current-runtime synthetic continuations stop after one scripted response.
The v2 synthetic clock is fixed. Actual dispatch request objects are identical
after removing that one forecast field, and each synthetic counted projection
matches dispatch/prepared identities exactly. The initial v1 wall-clock drift is
retained separately, not normalized away in the v2 claim.

- OFF request: `sha256:3659110942c251c8841b0ae9990c27c11b17f3b4ffd3537f2b8fdfaba35b6578`
- ON request: `sha256:7215d028ca59e1089c064a8b18892509c8e7e439120c9611044fc1718b5e4b77`
- Journal: `C:/pt/forecast-wire-rehearsal-20261029-v2/runs/run_dev_forecastwirepair.jsonl`
- Report: `sha256:732da5eb6804d4baf5dacaf6e40c20c2bd61411c8a630c65c45bc98351315c55`
- Existing action-budget/finish-audit tests: 18 passed.

Arithmetic is unchanged: 4 total calls minus 1 correction reservation leaves
3 ordinary calls for edit/check/finish. A probe leaves 2; more edit slots cannot
restore the spent response. Both current inputs expose replace_text, edit_files,
finish, stop, probes and selected tests, but no read/search. Generic anchored
mutation feasibility must not be interpreted as sufficient model-visible source
for a specific correct repair. This rehearsal proves intervention isolation,
not behavioral or repair benefit, and authorizes no paid dispatch.

A final read-only check on the new v2 ON clone confirms the distinction directly:
the gateway accepts the one-line replacement at line291 from its current-file
`revalidated_after_mutation` span200–470, while both actual public request bodies
contain only the later160–260 span and omit the helper/old_text. The source,
envelope, branch journal and diff remain unchanged; no patch was applied or added
to any model input. Audit report:
`sha256:2e52c304c296120a824467b3c9998bfad47390480547fba6f5774563e06b5420`.

## Source-delivery defect and correction

The decisive distinction is the selected projection, not the gateway's larger
registry. Both v2 forks' canonical context at turn265 contains current
`astroid/modutils.py:261–470` (`span_135fa5a4a607f162`), including the helper and
line291. Retention is 22,155/24,000 characters, with zero omitted observed lines
or ranges. Calling `completion_context.project` removes this selected body before
native deduplication and request assembly. Thus source selection did not cause
the observed omission.

The common selected-source hash is
`sha256:33d8ef84aa7617079e2b456972743ff48696bceae674f1c393f19714367669f4`.
OFF canonical context is
`sha256:12f51927daeaa2a0dfb104c3c9eb8731d71b9529b358f0060d7e80c634e47265`;
ON is `sha256:b509362b5048a97774c0fcc5e9c128c498564faac0b226375f1f5a2933af5b9d`.
These are distinct from the actual request hashes above.

`completion_context.project` now preserves the existing `source_spans`,
`observed_source_index` and `context_projection` whenever a mutation tool is
offered. Currency checks and retention selection remain in the gateway; the
normal native reference/catalog/count path remains in use. The prompt and
delivery flag describe this conditional preservation. Completion without a
mutation tool retains its compact behavior and the latest-source/probe exceptions.
No source read, task-specific prioritization, broader retention, new permission,
memory subsystem or mandatory gate is introduced.

This fixes a source-delivery contract independently of whether the omission
caused the historical model's finish choice. Repair success and latency effects
remain unmeasured. Regression tests cover both mutation tools, actual append and
segmented requests, exact native body reuse, closing tools, correction and recovery.
Existing gateway tests cover stale/unread source exclusion and retention bounds.

Post-fix validation uses runtime
`sha256:45e1bfe96a20897102c6903cc14a19e261f82bb5d4a0887a8f63e579707acb7c`:

- Four fresh public-snapshot assemblies (OFF/ON x append/segmented) deliver the
  selected helper body exactly once. Original journals/artifacts/source hashes
  remain unchanged. This is input assembly, not historical continuation replay.
  Journal: `C:/pt/completion-source-delivery-20261029-v2/runs/run_dev_completionsourcedelivery.jsonl`;
  report: `sha256:02af923c8fb67739542205724e9381dff85b925b531211a1c188c242be9906c6`.
  The v1 audit's overstrict assertion about two intentionally removed accounting
  metadata fields is retained separately; source delivery itself was correct.
- A fresh v3 OFF/ON fork rehearsal also passes through synthetic count, prepared
  request and actual scripted dispatch. Both retain the naturally selected helper
  and exclude the operator's proposed replacement. After removing the forecast
  field, the complete requests match under a fixed clock. No source supplementation
  is used. Journal: `C:/pt/forecast-wire-rehearsal-20261029-v3/runs/run_dev_forecastwirepair.jsonl`;
  report: `sha256:fee27b45a3c0e9857778ffeee3448a7d5c75228d36dd5d2da9a80062a15fb5d0`.
  Prepared OFF request: `sha256:f961006aa44c8fffee14cd8d604e333470d39ab197f26e9ee729559127ad1372`;
  ON: `sha256:84318fa8b6f2214b34132fce5f4a4a035c6bc46d8cc0d6af1240a3184547299e`.

The selected-source omission is resolved for this boundary. These are synthetic
mechanism checks: real token counts, cost admission for live generation, model
choice, repair benefit and independent acceptance remain untested.

## Validation

- Completion projection, current-source retention and completion guidance:
  **72 passed in 16.87 seconds**. The new selected-source regressions fail before
  the fix. A native-reference assertion was corrected to the existing field syntax.
- Finalization and edit availability: **15 passed**, including actual count/dispatch
  equality and correction/resume under both repair-capable and terminal-only views.
- Guidance/gateway contract owners and documentation: **46 passed in 43.00 seconds**.
- Ruff over `patchloop`, `tests` and `diagnostics`: **PASS**.
- Frozen quick suite, including isolated mock evaluation: **1,101 passed in
  276.40 seconds**. Command:

  ```powershell
  uv run --locked pytest '@tests/quick.txt' -n 4 --dist loadfile `
    --max-worker-restart 0 --basetemp C:/pt/tmp/completion-src-final-1029 `
    -o addopts= -p no:cacheprovider --tb=short -q
  ```

The first quick run had 1,099 passes and two stale current tool-surface hash pins.
The completion contract intentionally changes the current identity to
`sha256:bba5c4022076bd08ff02e14a340d960349978f6f181ccfeaee5e3108252de4a0`.
Only current pins were updated; frozen historical identities, argument/schema
serialization and run-schema expectations remain pinned. Runtime bytes were
unchanged between the passing v3 rehearsal and final quick run.

HTML static checks found 51 unique IDs, 57 valid links and one inline script;
Node syntax check passed. Browser visual QA was not run. Full-suite completion,
actual provider work, live repair gain and end-to-end latency improvement remain
unverified. All task-source alternatives are external operator experiments,
separate from the repository runtime fix and mock acceptance.

## Quota census and next work

All 20 public dev20 journal chains were validated: ten runs used one accepted
edit, nine used two, one used three. Only row9, pydicom-1694, reached the cap. Its
three edits were one implementation edit and two additive-test revisions; the
last public check failed. At the recorded limit it retained 7 responses, 19
actions, approximately 1,769.64 solver seconds and USD3.77435 of its USD4.50 cap.
The blocker was accepted mutations, not those other resources.

Every run was capped at three, so four-edit exhaustion was unobservable. This
does not establish that four is sufficient. `edit_files` also changes what one
edit can contain; historical counts are not current-runtime four-edit baselines.
Task `max_changed_files=4` is a separate full-diff constraint, not four attempts.

Census journal:
`C:/pt/edit-quota-selection-audit-20261029/runs/run_dev_editquotaselection20261029.jsonl`;
report `sha256:518f85890b6375f733b3ff47d96f5be950c7034a8f57f9af3f509df482fb9b34`.
Selection uses public actions/checks/resources, never private grades.

Next decisions, in order:

1. The corrected decision input and forecast-only request difference now pass
   local checks. Any paid comparison still needs a frozen current scope and live
   cost admission. Reuse its naturally selected public source; keep the operator
   replacement out of model inputs. Source supplementation, if ever used, must
   be labelled an assisted mechanism experiment.
2. Once that condition holds, vary forecast delivery alone and measure actual
   repair/regressions/acceptance as well as action choice, time and cost. A changed
   action or submission alone is insufficient.
3. If authorized later, start quota investigation with one current-runtime cap4
   diagnostic on `tasks/dev-train/current-dev20/9/public.yaml`, not a cap4-versus12
   efficacy claim. Stop quota escalation if another resource binds first or no
   quota-bound failure occurs. Only then is a controlled quota comparison grounded.

The concrete historical resource reference for that diagnostic is GPT-5.4/xhigh,
output40k/correction25k, 20 calls, 40 actions, 2,400 seconds and USD4.50. It is not
new authorization. Exact current commit/configuration, task, model, credential,
repeat count, positive cap and stop conditions are required before any paid run.
No new behavioral instruction, mandatory gate or quota default is adopted from
this local study. The completion prompt only describes its corrected source delivery.
