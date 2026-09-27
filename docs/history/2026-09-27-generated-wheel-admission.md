# Explicit generated-wheel admission

## Problem and implementation

PICOS could be built offline, but the dependency preparer accepted only public
index wheels. Added opt-in --generated-wheel-receipt and
--generated-wheel-receipt-hash options, usable only together with --resolve.
No model-authored tool, build hook, automatic image build or dependency fallback
was added. The initial path accepts one reviewed pure-Python wheel per preparation.

Admission verifies the reviewed receipt hash, public source URL and saved PyPI
release entry, all source/tool/script/result/wheel byte hashes and sizes, clean
image identity, successful build result, package/version/Python compatibility,
and absence of URL dependencies. The operator receipt is provenance, not independent
proof of isolation. Input evidence is archived into the new output artifact store.

Only the verified wheel is staged for resolution. The ordinary requirements must
select it; the resolved package/version must agree, and other local wheel URLs
are rejected. Its bytes are rechecked before offline installation. Public-index
wheels keep existing URL/hash/size verification. Descriptor and installed-file
hashes bind the result for normal read-only probe reuse. Existing legacy/default
preparation paths retain their behavior. See
[preparation contract](../../.agent/prepared-probe-dependencies.md).

## Executed toqito preparation

Reviewed receipt:
`C:/pt/prepared/picos-built-wheel-0927-v1/receipt.json`, SHA-256
`a9e49952e5c6100290fcea3ef025bf39711ee79fcea2f3df882a1e4c5cf3aff3`.
It copies the prior public PICOS build inputs/results without changing that evidence.

Actual CLI preparation used original-toqito-1538, its clean prepared source,
--resolve, --source-root toqito and the exact receipt/hash. Output and append-only
preparation journal: `C:/pt/prepared/original-toqito-1538-probe-0927-v3`.
The resolver selected 28 wheels, including the generated PICOS wheel, totaling
120,649,889 download bytes. Offline installation exited 0.

Installed files total 385,689,041 bytes, above the unchanged 268,435,456-byte cap.
Inventory validation therefore failed and no usable dependency descriptor was
published. Actual toqito DockerProbeSandbox execution is NOT_RUN. Wheel admission
and installation succeeded; complete probe readiness did not. No dependencies were
removed, capacity bypassed or task substituted.

Summary journal: `C:/pt/analyses/generated-wheel-admission-20260927-v1`,
`run_dev_generatedwheeladmission`. Runtime hash:
`5531ceb8026874c587b19a324bfa124708e40b62ba8bdbbdc5b6baab48935a1a`.

## Validation and next question

Final focused generated-wheel/resolution/preparation/generated-project/setup-adapter
suite: 124 passed in 63.908 seconds. Includes rejected receipt/evidence mutation,
path escape, unreviewed image/source/local wheel, failed build, URL dependencies,
and invalid option combinations. Ruff passed. Mock smoke
`run_dev_4b91a4a4ab2d4ac0` at `C:/pt/generated-wheel-smoke-0927` reached isolated
EVALUATOR_PASS, safety NOT_RUN, with zero paid cost. Full suite and paid runs were
not executed. Documentation layout/link checks passed.

Both toqito (~368 MiB) and darts (~548 MiB) now encounter the installed dependency
size limit. Next establish an explicit installed-size policy distinct from wheel
download and execution-memory bounds, then revalidate the complete public probes.
Prior no-dispatch drafts remain immutable and are stale for this runtime; no live
invocation is authorized or ready. This result is environment engineering evidence,
not agent repair performance or original benchmark correctness.
