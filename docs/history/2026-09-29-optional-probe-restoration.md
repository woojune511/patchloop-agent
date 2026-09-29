# Optional-probe public applicability and checkpoint restoration

Date: 2026-09-29. Provider-free follow-up to the
[candidate survey](2026-09-29-optional-probe-survey.md). Historical packets are unchanged.

## Public tox behavior

Validated T2 without LoaderStub/ConfStub or package import bypasses. Used the existing
pinned task image and real `python -m tox c -c tox.ini -e py311 -k description`,
with public INI cross-section references. Copied candidate/base src into separate
temporary directories and supplied the generated tox/version.py as the task's public
check already prescribes. No dependencies were downloaded or installed.

| Public case | Base | Frozen candidate | Required behavior |
| --- | --- | --- | --- |
| py310-only value requested from py311 | literal reference remains | empty | empty |
| py311 matching factor | pkg311 | pkg311 | pkg311 |
| missing key with explicit :fallback | fallback | empty | fallback |

All six CLI invocations exited zero; these exit codes alone do not certify behavior.
The public entry point confirms the candidate fixes the intended empty-factor case
but regresses explicit replacement defaults. The issue explicitly requires preserving
those defaults. This validates the observed public counterexample's applicability;
it is not a hidden benchmark pass/fail or an agent repair result. Used one bounded,
network-disabled, read-only container with temporary writable storage and read-only
source mounts; --pull=never, existing image only, automatic removal on completion.

## Provenance correction: tox is a seeded diagnostic

Detailed prefix restoration found diagnostic_candidate_seeded in T1/T2. The probe
was model-requested, but the candidate patch was inserted at diagnostic startup,
consuming one mutation slot. The event explicitly records resume_allowed=false.
The prior survey's paid-call/action match established probe authorship, not a fresh
unseeded candidate trajectory. Keep tox as a seeded public-repair diagnostic; do not
count it as an ordinary resumable fresh solve or silently override that flag.

## Restored constituents and runtime check

All five candidate files were rebuilt from local prepared base sources plus exact
historical accepted edits (and the explicit tox seed). Candidate diff hashes match
the checkpoint. Copied completed journal prefixes and referenced CAS bytes; checked
artifact hashes, historical model/tool counters, settled cost, mutation allowances,
and action_id/input_hash result lookup. No historical checks/probes were re-executed.
The next original dispatch is excluded. Historical funding remains closed.

The current DevToolGateway rehydrated all five prefixes and exposed each target
observation. For N1/P1/P2, consumed mutation counts match the original state; source
spans and working findings were also recovered. For T1/T2 the generic gateway counts
zero edits, while the seed consumed one. Thus the constituents are recoverable but
ordinary tox continuation fails the mutation-budget equivalence gate. No patched
gateway or resume override was introduced to hide this mismatch.

| Cut | Candidate/prefix/CAS/counters | Current gateway mutation state | Direct live continuation |
| --- | --- | --- | --- |
| N1 | verified | matches 1 consumed | NOT_RUN |
| P1 | verified | matches 3 consumed | NOT_RUN |
| P2 | verified | matches 0 consumed | NOT_RUN |
| T1/T2 | verified including explicit seed slot | mismatch: 0 instead of 1 | ineligible as ordinary resume |

Full provider-request reconstruction/parity, inherited-reference resolver use through
the complete runner, current runtime admission and actual model behavior remain
NOT_RUN. Recovering gateway state is not equivalent to passing those gates.
Both task and probe image identities were present for each selected case; image
presence alone is not execution readiness for every probe. Only tox public CLI
behavior was actually executed in a container during this follow-up.

## Source hash compatibility

Tox's old prepared-source manifest initially failed current content-hash validation.
Git commit/tree and clean status matched; recomputing the pre-9ccabcbf Windows Path
ordering reproduced its stored hash exactly. Created separate prepared source copies
with the current deterministic ordering and bound both old/new descriptor hashes.
Current validation then passed without changing the original checkout/manifest.
This is an explicit source-descriptor conversion, not skipped integrity validation.

Attempts v1-v3 remain preserved: initial old-hash rejection, then an invalid copied
descriptor layout, then detection of the seeded patch. Final v4 restores all five
constituents and separately records the gateway mismatch. No historical bytes were
edited and no model credentials loaded.

## Evidence and next decision

Packet: C:/pt/analyses/optional-probe-restore-20260929-v4.
restoration.json binds candidates, prefixes, copied references, image identities,
remaining budgets and source conversion. gateway-recovery.json records current
rehydration results; public-cli-receipt.json records the exact bounded Docker command
and six CLI outputs. public_tox_cli.py is an operator-only diagnostic, not model
context. The external run_dev_optionalrestore hash chain records evidence hashes.
All five original journal hashes remained unchanged and the owned container was
absent after execution. Five documentation checks and git diff --check passed.
Runtime code was unchanged; no full runtime suite or mock smoke was repeated.

Next prefer N1/P1 for the interpretation/verification-recovery comparison, with P2
as an alternative, and finish full-request exposure parity/admission checks before
paid execution. Tox can inform a separately designed seeded-repair experiment only
with explicit seed-state restoration and new authorization; it is not a third ready
natural task. No general repair improvement or new paid allocation is claimed.
