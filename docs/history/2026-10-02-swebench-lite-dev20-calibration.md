# SWE-bench Lite dev20: acquired images and calibrated original evaluation

## Problem and decision

The three-task pilot established a working small evaluation path, but not readiness
for the other 20 dev tasks. The user approved the exact 20 digest-pinned image
downloads and provider-free integration/calibration proposed by the
[inventory](2026-10-02-swebench-lite-dev20-inventory.md). Paid model work, image
builds, image deletion and a 300-task run were outside this scope.

All 20 images were acquired and verified. The full fixed roster was investigated:
12 tasks passed native and registered base/reference controls, including public
regressions after three narrowly scoped public environment follow-ups. Eight are
blocked by original-image/test-environment failures. Do not launch the proposed
20-task paid batch or silently remove its blocked rows.

This changes the next decision from model budgeting to environment compatibility.
The original reference patches cannot pass on eight of the pinned stock images,
so charging the agent for attempts there would mix repair ability with setup
failures. Further work should establish compatible dependencies/system libraries
under a separately bound environment revision, preserving original test/scoring
bytes and these failed stock-image controls. No such image was built here.

These are calibration controls with known reference patches, not fresh solves.
The earlier mini pilot remains 1/3 resolved; this work adds no agent success result.
No solver received reference patches or private test feedback.

## Fixed scope and acquisition

Dataset revision b0dde1093fe417d83b7184254edf8199c1f0dff5 and original harness
revision 02e7a74ffd0b707aab73d203fe87bdc7c76afc8e are unchanged. Selection is exactly
the 23-row dev split minus the three completed pilot IDs, sorted by ID. Public
check candidates were frozen from public issues, pinned public repository trees
and existing test paths before executing this calibration. Hidden test membership
did not determine visible test paths. No task was replaced.

The exact manifest from the inventory was authorized and bound into the new
acquisition journal. Every pull used its repository digest; subsequent inspection
confirmed Linux/amd64 and the exact RepoDigest. No tag-only pull, build or deletion
was performed. Pulls stopped on failure or a 12 GiB host free-space reserve; neither
stop was triggered. C: had about 58.4 GiB free initially and 34.62 GiB after image
acquisition. Those host snapshots include unrelated concurrent activity; they are
not a precise downloaded/unpacked image measurement. Final control work used
additional space, without removing previous evidence.

## Integration changes

- The native operator runner now accepts a nonempty roster with unique instance
  IDs and valid digest pins instead of requiring exactly three rows. Its bounded
  containers still have no network and cannot pull/build images; original scripts,
  patch bytes, parsers and scoring remain unchanged.
- Package construction is reusable independently of the old three-task orchestration.
  Explicit public source roots and pytest arguments are supplied independently of
  the private oracle. The legacy pilot entry point keeps its public-check defaults.
  Draft construction is not live admission. The generic source constraints also
  protect the singular test/ tree used by SQLFluff.
- pvlib, PyVista and SQLFluff were added to the exact remote repository allowlist.
  All 20 public sources were prepared at their base commits with LF-preserving
  checkout and immutable source manifests.

No coding-agent prompt, planner, tool surface or cost cap changed.
The 20 packages remain external calibration drafts; none was silently admitted
as a replacement paid cohort.

## Results for the complete roster

| Repository | Passed calibration | Blocked | Observed blocker |
| --- | --- | --- | --- |
| marshmallow | 1343 | none | none |
| pvlib | none | 1072, 1154, 1606, 1707, 1854 | NumPy 2.x removes np.Inf used during import. |
| pydicom | 901, 1694 | 1139, 1413 | pytest 8.3.5 does not initialize old setup methods; self.tag is absent even with the reference patch. |
| astroid | 1196, 1268, 1333, 1866 | none | 1268 needed the public-only distutils setting below. |
| PyVista | none | 4315 | libGL.so.1 is missing while importing VTK. |
| SQLFluff | 1517, 1625, 1733, 1763, 2419 | none | 1517/1625 needed the documented optional-dbt selection below. |

On each of the 12 passing tasks, the original native base fails, the original
reference passes, all required test IDs are accounted for, and the registered
private adapter agrees. Public regressions pass on both base and reference.
The actual isolated EvaluationEngine reference submissions also pass hidden tests,
regressions, scope and safety for all 12. These are seeded acceptance/safety
controls, not a comparison of agent quality or a general safety claim.

The first unchanged-public-plan pass calibrated nine tasks. The other three became
calibrated only after the separately recorded public follow-ups below. Original
failed attempts, packages and journals were preserved.

For the five pvlib images, native base evaluation fails at import with zero test
results, and native reference evaluation stops at that failed gate. Registered
base and reference checks reproduce the same import failure. PyVista similarly
fails before test collection because VTK cannot load libGL.so.1. These are
infrastructure outcomes, not unresolved model patches.

For pydicom-1139/1413, original native tests run and are fully accounted for, but
two existing TestBadValueRead tests fail even on the supplied reference. Public
source places self.tag initialization in setup(); the pinned image runs pytest
8.3.5. The registered reference also fails. Restoring a compatible test lifecycle
is an environment question; no private test was removed or patched to pass.

## Public environment follow-ups

1. **Astroid-1268:** the full public suite had one failure comparing stdlib
   distutils with setuptools' replacement path. Set SETUPTOOLS_USE_DISTUTILS=stdlib
   for its public check only. Both base and reference then report 1,184 passed,
   67 skipped and 15 xfailed. No public test was deselected; private bytes and
   original native controls remain unchanged.
2. **SQLFluff-1517:** the single public failure was an upstream dbt-marked optional
   test in linter regressions, unrelated to this doubled-semicolon parsing issue.
   Use the repository's own pytest.ini/tox.ini -m 'not dbt' policy on the selected
   parser/linter check. Both controls report 166 passed and one deselected.
3. **SQLFluff-1625:** its L031 rule issue similarly hit one optional dbt-marked test.
   The same documented selection gives 500 passed and one deselected on both
   controls. This is not full dbt coverage. No private checks were deselected.

No blanket dbt filter was applied to SQLFluff-1763, whose public issue mentions dbt.
Its existing selected CLI/linter regressions report 146 passed. That selection
does not establish complete plugin/database integration coverage. Public check
coverage and original private acceptance remain separate claims.

## Evidence and validation

Evidence root: C:/pt/analyses/lite-dev20-calibration-20261002-v1. Acquisition,
preparation, calibration, three follow-ups and isolated engine controls have
separate append-only dev-run-v1 journals. Driver and input hashes bind the frozen
conditions. acquisition.json, prepared.json, calibration.json, the three follow-up
JSON files and engine-results.json are derived projections. Native files, check
output and unchanged private package bytes are retained as operator artifacts.

Public sources/drafts: C:/pt/ld20p01. Initial controls: C:/pt/ld20c01. Public-only
follow-up drafts/workspaces: C:/pt/ld20f01, C:/pt/ld20f02, C:/pt/ld20f03. Isolated
engine workspaces: C:/pt/ld20e01. No historical files, existing task packages,
images, worktrees or branches were deleted or rewritten.

Execution used 283b43e7 plus this subsequently committed integration change;
operator code hashes and engine runtime-content hashes bind executed bytes.
Local full suite: 3,982 passed, 16 skipped in 1,061.26 seconds. The final focused
integration group passed 28 tests in about two seconds; documentation layout,
Ruff and diff checks passed. Mock smoke reached isolated acceptance PASS with
safety NOT_RUN. Real reference controls provide the separate Docker evidence.
Final integrity audit verified 672 artifact references across eight journals,
confirmed unchanged private bytes in all three follow-ups, and found no remaining
owned containers. final-summary.json records the complete effective roster.

PR #20 received these changes; exact final-head CI status belongs to the live PR.
The earlier 283b43e7 Ubuntu/Windows jobs passed. No merge was performed here.
Live provider calls and provider cost remain zero. No new paid allocation exists;
the earlier USD 24 proposal remains unapproved. Every result is official=false
and claim-ineligible; no 300-task execution occurred.
