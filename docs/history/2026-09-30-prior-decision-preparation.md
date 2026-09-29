# Retained prior decisions: one-field-family comparison prepared

Follows the [argument audit](2026-09-30-evidence-argument-audit.md). Provider-free;
the runtime, previous inputs, grades and closed results remain unchanged.

## Problem and chosen diagnostic

The prior reduced-context arm retained attempt-card turn_decision objects, including
public explanations and plans. HF cards described PASS; tox cards explained a possible
default-swallowing mechanism and repair. Their presence in both arms prevents treating
that experiment as a comparison without prior explanatory context.

Prepared new A/B views at the same four HF/AnyIO/tox dev-train checkpoints:

- New A exactly equals the previous experiment's B view, including its neutral question.
- New B removes only recent_attempt_result_next_question[*].turn_decision objects.
- Removed counts: C1 2, C2 3, C3 3, C4 2; ten objects across four pairs.

No new question, omission marker, target hint, code, expected result or source is
added. Remaining next_question advice, provenance caveats, workflow state and probe
questions/expectations are held constant. This tests these prior decision objects,
not all interpretation, independent solving, source trust or length alone.

## Implementation and validation

`diagnostics/prior_decision_design.py` and the
[contract](../../.agent/prior-decision-design.md) provide preparation/validation only.
The original evidence-context preparation is hash-bound and reconstructed before use.
Each saved derivative has immutable artifacts and an append-only dev-run-v1 journal.

Reinserting the removed objects reconstructs the original entire view exactly. This
proves all other values survive, including program/assertion strings, stdout/stderr,
setup observations, source bodies, task/check definitions and candidate/action IDs.
The audit recursively decodes JSON strings and checks remaining decision/plan fields
and whitespace-normalized exact copies of removed basis/plan prose. All four actual
B views pass. Semantic paraphrases and other advice are outside that guarantee.
Duplicate discoveries stop preparation; no arbitrary evidence strings are rewritten.

Nineteen focused tests passed (new preparation 9, source preparation 5, documentation
5), and Ruff passed. Tests cover nested JSON copies, prose copies, unsupported input,
evidence preservation, tampering and duplicate output roots. Actual-source preparation
and validation passed for all eight views; no token API, credentials, provider, tools,
Docker or evaluator was used. No runtime behavior changed, so task smoke is not relevant.

## Frozen artifacts and next boundary

Root: C:/pt/analyses/prior-decision-preparation-20260930-v1.
Packet SHA: sha256:4382e95030d986ed2112d0ece9783083517422e9b17bf0693f2cce33b1f9fb0b.
Journal: run_dev_priordecisionprep.
Source: evidence-context-preparation-20260930-v3, SHA
sha256:f0d76812521444fb21724e4e7773258d455572ed8271d2ad70daeed9576e8f7e.

Status PREPARED_NOT_EXECUTABLE; dispatch disabled. No collector or new paid approval.
An eventual comparison must use fresh responses for both arms, keeping other model
and response settings fixed; prior B outputs are not newly sampled A observations.
Freeze scoring before collection and retain the limitation that the general AnyIO
question previously omitted the target setup assessment. Narrowing that question
would be another intervention. No runtime adoption or performance conclusion follows
from preparation, and all prior paid allocations remain closed.
