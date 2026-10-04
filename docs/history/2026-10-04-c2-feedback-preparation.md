# C2 regression-feedback continuation: provider-free preparation

Date: 2026-10-04. No provider generation/count calls; actual model cost USD 0.
Baseline retained. The [new scope](../../.agent/c2-feedback-evaluation.md) awaits
separate approval; the [previous allocation](2026-10-04-c2-choice-results.md) stays closed.

## Problem and decision

Two fourth-edit choices fixed the issue output but broke public regression. Both
runs stopped without another model request. That answers pre-feedback choice, not
whether the model can use an observed regression to narrow its next change.
The user authorized offline preparation of that separate question.

Existing DevLimits already supports five accepted mutations. We reused that setting
instead of adding a conditional opportunity-issuing policy or new runtime state.
The total becomes five edits, with four already spent; calls, actions, wall time,
settled cost, check currency and native observations are not reset. An envelope
change is recorded in a fresh fork; ordinary resume continues to reject it.

## Exact post-failure boundaries

Both sources use run_dev_8ae27bd1b3464578 in distinct external roots. Prefixes end
at the completed batch containing the failed registered check, before terminal.
Their original check outputs have exit 1, complete output, no timeout and clean
teardown. The operator post-run public pair and known correction are excluded.

| Source | Prefix sequence | Calls/actions/edits spent | Historical USD | Active milliseconds spent | Remaining USD |
| --- | ---: | --- | ---: | ---: | ---: |
| C:/pt/c2cp01/live1 | 320 | 19 / 35 / 4 | 2.4150790 | 1,255,915 | 0.5849210 |
| C:/pt/c2cp01/live2 | 310 | 18 / 36 / 4 | 2.1922615 | 1,188,259 | 0.8077385 |

Prefix hashes:

- live1: sha256:3f91a55cfb6e17d140391d819387eed10495f3dd58d9b2f0667cf0cc2b53c7c5
- live2: sha256:754ad1fe88173d9acc8a70ef6bac715804491bba7f4a1a979b00879d7df5318b

Original source hashes and cumulative diff identities are verified. CAS copying
resolves exact inherited references across the earlier fork; recorded encrypted
continuation is retained without decrypting it. Four recorded replacements are
reconstructed with preimage/postimage/diff checks in fresh local workspaces.

The runtime naturally creates the next input with the failed regression and one
remaining edit. It is captured before input counting, not fabricated as an old
request. The saved input contains both actual failed public case IDs and the
correct current candidate. No correction condition or later operator observation
is injected. The rendered initial time remainders are 543 and 611 seconds; source
upper bounds are 544.085 and 611.741 seconds, with preparation timing retained.

## Validation

The two-source restoration/control group completed in 61.6 seconds:

- With the original four-edit limit, the runner stops LIMIT_REACHED without count
  or model dispatch. With five, it exposes one edit and preserves other resources.
- Each generated input is dispatched unchanged to a synthetic stop response in
  an independent copy of the seed. No historical check or mutation is rerun.

The failure/repair group completed in 98.3 seconds:

- Synthetic count timeout, transport timeout and missing usage all stop with no
  new tool action. Naturally rebuilt inputs match the frozen inputs apart from
  the documented elapsed-time comparison. Ordinary resume rejects changed limits.
- An operator-authored correction is supplied only as a synthetic SDK response
  after a registered current-source read, on a separate validation fork. It counts
  as edit five. Existing repair-recheck and saved-program-v1 paths automatically
  run the required regression and saved program on the new candidate.
- Actual existing Docker sandboxes report all 506 public regressions passing;
  full issue output matches the public expected lines and the saved preservation
  case passes on the same diff. No timeout, truncation or cleanup failure occurs.
- After edit five the next request has zero edits left and no replace_text tool.
  The scripted stop does not submit, so original acceptance remains NOT_RUN.

That corrected fixture reproduces the previously verified operator candidate:
sha256:2c0c19ffbab7ea0eb9c6813e66792b805c7b34269e81b5924fb49e8e32030c59.
This verifies execution plumbing and check currency, not autonomous model repair.
No policy was adopted and no hidden acceptance was run on that fixture.

An independent two-row collector rehearsal uses synthetic stop responses and a
stubbed post-run public pair. It checks exact prepared inputs and new-only group
accounting; its public behavior and acceptance are explicitly NOT_RUN. All new
provider use throughout preparation is synthetic, with actual billed cost zero.

## Evidence and remaining question

External records: C:/pt/analyses/c2-feedback-prep-20261004-v1. Scripts prepare.py,
verify.py and collect.py, live1.json/live2.json, packet.json, validation.json and
collector-audit.json retain the procedures and results. Hash-chained dev-run-v1
journals bind starts/results. Workspaces and captured seeds are under C:/pt/c2fb01.
Only uncorrected source-prefix seeds are eligible for a later authorized run;
synthetic repair and error branches are separate evidence.

Repository changes are documentation only. Relevant closeout checks are documentation
layout/links, Ruff and diff checks; all passed, including 16 selected tests.
Existing collector tests additionally cover
new-cost isolation, uncertainty stop-all and a synthetic isolated-evaluation path;
the full fast suite and separate mock smoke are not rerun for unchanged runtime.

The implementation needed for a bounded feedback continuation is locally verified.
Whether either actual model continuation can use the regression to preserve both
requirements is NOT_RUN. A newly approved evaluation would measure feedback plus
extra-edit completion, not unchanged-budget scope judgment or a conditional policy.
