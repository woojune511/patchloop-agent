# PDM repair observation

Status: COMPLETE; USD 3 allocation CLOSED at USD 0.3550415 recorded usage.
official=false; claim_eligible=false. No further run, retry or resume is authorized.

## Problem and scope

After restoring the previous verification guidance, observe one real repair on
the exposed PDM dev-train v2 active-virtualenv selection task. This is neither
an unseen-task evaluation nor a prompt comparison. The prior panel's unresolved
failure was not supplied as a hint and its cause remains unresolved.

Provider-free preparation reproduced 20 failures among 24 public bug-contract
cases on unchanged source; all 36 upstream regression tests passed. Thus this
task's public contract detects the original bug, unlike the earlier Darts
regression suite that passed unchanged source.

The user approved the exact proposed scope: gpt-5.4-2026-03-05, xhigh, 25,000
output tokens, project `.env`, repeat=1, USD 3 invocation cap. Selected baseline
policies and 40-call/100-action/4-edit/1,800-second limits were retained.
Optional probes used the existing stdlib-only profile. No runtime, task, prompt
or dependency-profile changes accompanied the run.

## Observed repair and validation

Run `run_dev_de43faeef7ee4c76`, harness commit
`a8c37b54e1a6071524ddca08583a643ec40a3492`, completed in 196.691 active seconds.
Six model calls and six input counts settled, with nine tool actions: four
searches, one read, one replacement, two registered checks and finish. No probe,
retry, resume, replacement row or additional paid execution occurred.

The single patch removes the ignore flag from the condition enabling virtualenv
resolution. It normalizes false-like values, preserves active reuse when ignoring is disabled,
and, when ignoring the active environment, excludes its resolved root and
descendants before constructing an interpreter candidate. Component-aware path
ancestry preserves eligible sibling paths. Normal creation fallback remains.
This source review describes the mechanism; it is not additional executed tests.

| Evidence | Result |
| --- | --- |
| Public bug contract on submitted patch | 24 PASS / 0 FAIL |
| Upstream project regression | 36 PASS |
| Isolated task acceptance | PASS |
| Real sandbox safety | PASS |
| Provider cost | USD 0.3550415 of USD 3 |
| Journal integrity | 100 run events read back successfully |

The agent verified the changed behavior through a bug-sensitive registered check.
Zero optional probes therefore does not demonstrate inadequate verification on
this run. The checks cover false-like settings, both environment variables,
exact/descendant exclusion, sibling retention and creation fallback. No separate
operator edge-case replay was run; complete semantic coverage and generalization
remain unestablished. One successful exposed task cannot establish a prompt effect
or explain the older failed panel row.

## Evidence and decision

- External root: `C:\pt\pdm-repair-20261001-v1`.
- Invocation result: `result.json` under that root.
- Run journal: `runs\run_dev_de43faeef7ee4c76.jsonl`.
- Approval and close-out: `operator\runs\run_dev_88bd3a8eb49c4c03.jsonl`.
- Submitted patch hash:
  `sha256:4d13c7f3a29e71fe5eea4fdbdfa70682c39793e58b8cab7d792dfe6b201ba71a`.
- Prepared source and baseline journal remain under
  `C:\pt\preparations\pdm-next-repair-20261001-v1`.

Keep the restored runtime baseline. This observation supplies no reason to add
a mandatory probe rule or another prompt intervention. Choose further work from
a concrete observed failure; do not automatically cycle through another task.
Historical evidence is preserved and the unused allocation grants no follow-up.
