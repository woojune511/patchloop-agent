# Current-runner request parity and admission audit

Date: 2026-09-29. Provider-free follow-up to
[checkpoint restoration](2026-09-29-optional-probe-restoration.md).
No credentials loaded, provider/token-count requests, task actions or containers run.

## What was actually rebuilt

For N1 AnyIO and P1/P2 pyfakefs, copied verified inherited artifacts into new external
stores and resolved exact inherited metadata through the existing scoped resolver.
Rehydrated the current gateway and counters, computed current source projections and
tool policy, called runner._build_context and runner._build_model_input, and constructed
the full body with OpenAIResponsesAdapter.request_payload and an inert offline client.
Input assembly was network-disabled. This is current code construction, not replacing
a field in an old saved request and calling that a runtime rebuild.

Both arms use gpt-5.4-2026-03-05, xhigh, 25,000 maximum output tokens and identical
current tool schemas/system instructions. B is the rebuilt request. A suppresses only
the automatic verification observations in the serialized request. Original public
tool output remains in A. Native encrypted items are retained as opaque continuation
state; not decoded, summarized or interpreted as durable task facts.

## Results

| Cut | A request bytes | B request bytes | Only changed location |
| --- | ---: | ---: | --- |
| N1 | 121472 | 123432 | current state's working_notes.verification.observations |
| P1 | 166770 | 169963 | current state's working_notes.verification.observations |
| P2 | 84853 | 86063 | current state's working_notes.verification.observations |

For all three, removing B's declared field yields exactly A, including all other
messages, native items, tools and provider options. The target action is present in
B's catalog; displayed model/action/edit/time/cost budgets match the checkpoint;
callable tools match the historical checkpoint. No unresolved provider call appears
in the restored prefix. Source journal hashes remain unchanged.

Existing probe-image identity and local prepared dependency bytes passed the real
DockerProbeSandbox.preflight. N1 has prepared wheels; old P1/P2 legitimately have no
prepared dependency descriptor, so use the unchanged no-bundle profile. No new wheel
bundle, installation, image build/pull or Docker startup was performed. Environment
preflight does not demonstrate successful execution of an arbitrary future probe.

These byte counts are not token counts or cost predictions. The exposed catalog is
an intentional context-length difference, not an instruction to equalize by padding.

## Execution is not admitted

All three historical runtime hashes differ from current dev-head. The actual
_validate_resume_envelope function rejects an otherwise identical envelope with
the current runtime identity. Do not rewrite an old envelope or bypass that guard.
This is an expected revision boundary, not evidence that candidate restoration failed.

The request projection is an offline diagnostic function. A synthetic serialized
function_call_output containing working_notes_after_batch confirms it removes the
catalog there while preserving unrelated observations. It is not yet integrated as
a persistent per-turn runner intervention, and no multi-turn A-arm leakage claim is
made. First-request parity is PASS; persistent exposure execution is NOT_IMPLEMENTED.

Historical displayed cost is retained only for reconstruction equality. Old unused
allocations remain closed. Live credential admission, remote counting, new pricing/
funded admission, runtime fork provenance, full multi-turn intervention and actual
model efficacy are NOT_RUN. Initial requests use the current model/settings in both
arms; equality to the old model/request as a whole is neither claimed nor required.

## Evidence and next implementation

Packet: C:/pt/analyses/observation-request-parity-20260929-v2.
check.py constructs the requests; report.json binds hashes/byte counts/policy/images;
validation.json records exact parity, budgets and actual resume rejection. Each cut
has A-request.json and B-request.json in its external directory. The append-only
run_dev_requestparity journal hashes the report/script and validation.
v1 remains preserved: N1 succeeded while old pyfakefs optional descriptor handling
raised KeyError; v2 handles the absent optional field without inventing dependencies.

Next implement a bounded diagnostic fork under current runtime identity, with
immutable parent provenance, new explicit funding, preserved task state/allowances
and one exposure policy applied at every dispatch boundary. Before paid work, rehearse
multiple turns through that fork using synthetic responses, including after-batch
projection, idempotent recovery and hard stops. Do not spend a model call to diagnose
these deterministic runner boundaries. No paid allocation is opened by this audit.
Five documentation layout/link tests and git diff --check passed. Runtime source
is unchanged; no full suite or mock solve was repeated for this documentation audit.
