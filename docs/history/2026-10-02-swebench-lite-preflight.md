# SWE-bench Lite: original evaluation ready, public regression blocks the pilot

## Question and decision

The user chose GPT-5.4 mini and approved three Lite development tasks, their exact
images and a conditional USD 3.60 invocation. The question is whether the existing
agent can complete original tasks cheaply enough to justify a larger measurement.
This addresses repeated diagnosis on familiar tasks; it does not select a memory
or prompt intervention. The 300-task test split is not part of the approval.

Do not dispatch the paid pilot yet. Original benchmark controls work, but the
newly attached public full-suite check fails on untouched pydicom source. Requiring
that check to pass would make the agent repair unrelated baseline/test-runner
compatibility problems. Retain original tests, all failed preparations and the
same three task identities. No solver attempts, model costs or success rate exist.

## Frozen selection and evaluation

See the [pilot protocol](../../.agent/swebench-lite-pilot.md) for exact dataset,
harness/model/image/source identities, public/private partition, budgets and stops.
Selection uses a seeded hash of IDs and one task per repository, without consulting
answers or outcomes: astroid-1978, pydicom-1256 and marshmallow-1359.

Native execution uses the pinned upstream run_instance, original evaluation script,
repository parser and grader. Docker transport is network-disabled, drops extra
capabilities and refuses image acquisition. The only content transport correction
restores upstream's canonical LF bytes after Windows text writes; it rejects any
other content difference. This is local development evidence, official=false.

| Original control | Base | Reference | Required cases present |
| --- | --- | --- | --- |
| astroid-1978 | unresolved | resolved | 13/13 for both |
| pydicom-1256 | unresolved | resolved | 23/23 for both |
| marshmallow-1359 | unresolved | resolved | 77/77 for both |

Six original controls meet expectations. These are known-answer environment
controls, not six agent solves. All six owned containers were removed.

## Integration findings

1. Windows Path.write_text changed the upstream shell file to CRLF. Conda activation,
   paths and test commands failed before tests ran. The first native attempt is
   preserved; a separately recorded transport correction produced the six results
   above. A collector also initially assumed the wrong log directory; it now uses
   upstream constants. Neither change modifies an assertion or scoring rule.
2. core.autocrlf=false alone does not preserve LF when upstream declares text=auto
   and the host's native EOL is CRLF. Such prepared source failed original test-patch
   application in Linux. Remote preparation now also sets core.eol=lf before
   checkout. A regression reproduces a CRLF-host configuration and verifies exact
   LF bytes plus a clean checkout. Original prepared sources remain immutable;
   corrected preparations use a new sources-lf directory.
3. The registered-check adapter imports unchanged Python parser/grading modules
   without upstream's Docker/cloud package initializers. Original test patches and
   pytest arguments are unchanged. Source is copied into a temporary directory and
   selected through PYTHONPATH instead of editable installation. Unexpected adapter
   errors return infrastructure exit 2, not wrong-answer exit 1. Final agent patches
   still require native upstream evaluation; adapter parity alone is insufficient.
4. Astroid's public full suite initially rejected two newer setuptools deprecation
   warnings. Narrow message filters restore that public suite without deselecting
   tests or modifying assertions. Base and reference then pass public checks and
   respectively fail/pass the original private adapter.
5. Pydicom's full public suite fails on unmodified source. Its image uses Python
   3.9.21 and pytest 8.3.5. Public test classes still define legacy setup/teardown;
   errors include unset _value/logger fixture attributes, followed by further
   failures. The same image's benchmark-selected original tests work correctly.
   This is a concrete public-check compatibility/scope problem, not evidence of an
   incorrect agent patch or a broken original hidden oracle. Full output exceeds
   the registered output limit; the saved output is explicitly marked truncated.

The leading explanation for the public failures is test lifecycle compatibility.
Pytest's [removal notes](https://docs.pytest.org/en/8.1.x/deprecations.html#support-for-tests-written-for-nose)
confirm that plain setup/teardown support was removed in pytest 8.0. This supports
the observed fixture failures, without establishing the cause of every suite failure.
It would be weakened if the same full suite failed identically under its documented
supported pytest version with setup methods actually called. No dependency downgrade,
full-suite exclusion list, replacement task, new public-check policy or paid retry
was adopted. The next decision concerns public verification suitable for this pinned
environment, without using private test targets or changing the original grader.

## Evidence and validation

- Preparation, approval, exact image pulls and native controls:
  C:/pt/analyses/swebench-lite-dev-preparation-20261002-v1.
- Preserved native transport failure: native-controls; corrected results:
  native-controls-lf. Approval and subsequent actions are bound in the external
  runs/run_dev_swebenchliteprepare.jsonl chain and content-addressed artifacts.
- Registered adapter attempts: C:/pt/analyses/swebench-lite-registered-controls-20261002-v1,
  v2 and v3. Each has its own journal and immutable output artifacts.
- Unpublished astroid/pydicom drafts were retained under the v3 retained-drafts
  directory; they are not admitted tasks. The preparation driver now stages drafts
  outside the repository until all prerequisites pass.
- Focused source preparation checks: 30 passed in 25.35 seconds. Transport/selection
  checks: 12 passed. Earlier full suite: 3,964 passed, 16 skipped in 814.47 seconds;
  this preceded the LF checkout fix. Final validation is recorded separately below.
- Initial mock smoke reached EVALUATOR_PASS, safety NOT_RUN; it is not Lite evidence.

Final validation after the LF checkout fix: 3,968 passed, 16 skipped in 826.64
seconds using four workers; XML is pytest-final.xml in the preparation root. Ruff
passed for patchloop, tests and all four new diagnostics, and git diff --check
passed. Focused source preparation remained under two minutes. Documentation
checks passed (5 tests). Final mock run run_dev_e1a84b7efbde4fe9 reached
EVALUATOR_PASS with safety NOT_RUN under
C:/pt/swebench-lite-prep-smoke-20261002-v2. The four preparation/adapter journals
and 141 unique referenced artifacts passed hash verification. Docker reported no
remaining containers. This is local Windows validation; remote CI was not run.

No OpenAI or token-count requests were dispatched and no credential file was loaded.
The USD 3.60 conditional authorization remains unspent; its prerequisites still apply.
Historical task results, experiments and reference records are unchanged.
