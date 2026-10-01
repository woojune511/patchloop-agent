# OpenSandbox public repair diagnosis

## Why this failure

The [fixed batch](2026-10-01-fixed-batch-live-results.md) submitted three patches
that passed public checks but failed target bug cases. OpenSandbox has one edit
and a narrow, security-relevant public requirement. Diagnose it before proposing
another agent intervention. This investigation used the frozen public issue,
base source, submitted patch and public action/probe evidence only. No hidden
test contents, reference patch or new model call was used.

Task base: `fb78091f947f62ae2c71a372af42425a764aacee`.
Saved run: `run_dev_75ec90f0be654c84`; submitted patch SHA256:
`5295695164a555a65c6373515dfdf9ecf3c1deadafebc617044fe9ba00896493`.

## Observed repair and verification

The public issue names both `ensure_valid_host_path` and `_validate_host_volume`.
The patch only changes the shared helper: it walks native path components and
rejects existing symbolic links. The backend retains its conditional helper call:
it revalidates only when allowed prefixes are truthy and the subPath changes the
host path. The ordinary `_validate_volumes` sequence first runs shared validation,
then backend validation. Thus a direct backend gap alone would not prove that an
unchanged symlink bypasses the ordinary full validation sequence.

The agent read docker.py lines 1462-1545, searched for helper calls, read helper
source, and searched for the exact text `realpath(strict=True)`. That search returned
no match. The PVC implementation actually uses multiline `os.path.realpath(...,
strict=True)` calls later in docker.py, outside the delivered range. No follow-up
read of that code appears in the action trace. A literal search miss is not evidence
that the functionality is absent. This establishes an inspection gap, not the
agent's internal reason for choosing its repair.

Its public probe successfully tested a clean path and an existing intermediate
symlink through the shared helper only. Registered upstream regressions passed.
Neither observation demonstrated backend validation. The probe result is valid
within its scope; broadening it into backend correctness was unsupported.

## Frozen diagnostic and alternatives

Before execution, recorded three possibilities: helper repair is sufficient in
the ordinary flow; backend fails to revalidate; import/environment behavior explains
the discrepancy. Used fresh base, submitted-patch and local-control checkouts with
the same pinned benchmark image and PYTHONPATH=/workspace/server. No private
assets were mounted. Each real DockerSandbox check used a read-only source/root,
network none, existing resource bounds and 60-second timeout. Symlinks and filesystem
changes existed only in temporary container storage. No actual Docker volume mount
or external host access was attempted. All checks exited 0 with confirmed cleanup.

The local control adds one unconditional call to the already repaired helper before
backend filesystem operations. It is an operator causal control, not a submitted
repair, a replacement reference patch or a complete security fix.

| Public diagnostic | Base | Submitted | Local backend guard |
| --- | --- | --- | --- |
| Clean helper path | Accept | Accept | Accept |
| Symlink through helper | Accept | Reject | Reject |
| Clean backend path, no subPath | Accept | Accept | Accept |
| Symlink through backend, no subPath | Accept | Accept | Reject |
| Shared then backend, static symlink | Accept | Reject | Reject |
| Shared then backend, symlinked subPath with allowlist | Accept | Reject | Reject |
| Shared then backend, symlinked subPath without allowlist | Accept | Accept | Reject |
| Backend after path replaced between validation stages | Accept | Accept | Reject |

The final case deterministically validates a normal directory in the shared stage,
replaces it with a symlink, then calls the backend. It demonstrates lack of
revalidation at that boundary, not exploitable race timing or atomic mount safety.
Even the local guard leaves a later validation-to-mount race unresolved. The
no-allowlist case tests the issue's reject-symlinks requirement; it is not a bypass
of a configured whitelist. No Windows execution or permission-denial matrix was run.

## Decision and remaining question

The patch makes a real improvement for static symlinks in shared validation, but
does not implement backend validation comprehensively. The same-environment local
control changes precisely the uncovered outcomes, supporting the conditional
backend call as the mechanism for these public gaps. This diagnosis does not
identify the exact private assertion responsible for the original benchmark FAIL;
private evaluation remains unchanged and was not rerun here.

Preserve the agent baseline and original artifacts. The actionable failure is
incomplete coverage of named requirements across caller/helper boundaries, combined
with a helper-only verification scope. Do not add prompts, memory or mandatory
probe rules on this one case. The next useful question is whether public evidence
from pyinfra or isort shows the same coverage failure or a different mechanism.
Strict canonicalization, permission failures and race-safe mounting remain outside
this bounded diagnosis; the one-call control is not an adoption candidate.

## Evidence

Root: `C:\pt\analyses\opensandbox-public-diagnosis-20261001-v1`.
`runs/run_dev_opensandboxpublicdiagnosis.jsonl` binds the protocol/program before
execution and all receipts/diffs; `summary.json` contains 24 outcomes across three
conditions. Driver: `C:\pt\opensandbox_public_diagnosis_20261001.py`.
An initial incorrect Python class import failed before any evidence directory,
container or diagnostic was created; corrected to existing RegisteredCheck before
execution. No task package, agent runtime, historical report or paid allocation
was modified. Documentation checks passed.
