# HF v6 behavior-based evaluation and calibration

## Problem and contract change

The [HB2 diagnosis](2026-10-01-hb2-evaluator-contract-diagnosis.md) found that v5's
private checks required an undocumented parser signature and ambient rebasing
inconsistent with the public no-explicit-endpoint preservation rule. Added a
separate hf-hub-xet-endpoint-propagation-v6 package. All v5 bytes and original
FAIL verdicts remain unchanged; runtime acceptance still requires hidden,
regression and scope PASS.

V6 preserves the issue, repository/base, public constraints, visible commands and
image exactly; only the public version increments. Its task-private-v2 inventory
hash-binds both hidden files. Tests observe refresh route, file hash, errors,
request count and transfer count through metadata/download APIs. They do not
require a parser parameter or compare AST signature hashes. The mock HTTP fixture
is extracted from the existing public fixture; this is shared infrastructure,
not an independent implementation of HTTP semantics.

One unittest method executes 192 subcases: six metadata/download entry paths,
two carriers (header/Link), explicit versus absent endpoint, and eight route
ownership forms. Cases include ambient endpoint state, endpoint path prefixes,
normalized default origin, relative/already-custom/foreign/lookalike routes and
non-default scheme/port. These are scoped behavioral checks, not complete API
coverage. No missing hidden check was removed or converted to PASS.

The reference artifact is explicitly HB2's saved patch, not an independent oracle
implementation. Checks were authored after reviewing HB2 and v5's failures;
this is post-run development calibration, not a held-out benchmark revision.
Task hash: sha256:b7e8d39d85083af8304b87fcefa518f17197c85336e20faffee51735e90e01ee.

## Frozen calibration results

Before dispatch, the external protocol fixed one run per control and expected
HB2 PASS with every wrong-behavior control FAIL. All ran in the existing pinned
Docker check environment with network disabled and read-only workspace/root.

| Control | Hidden result | Failing subcases |
| --- | --- | --- |
| Unmodified base | FAIL | 20 |
| HB2 saved submitted patch | PASS | 0 |
| HA1 saved overbroad repair | FAIL | 12 |
| HB2 with rebasing disabled | FAIL | 20 |
| HB2 with origin hostname restriction removed | FAIL | 20 |
| HB2 with absent endpoint replaced by ambient endpoint | FAIL | 28 |

The last three are independent behavioral mutations, not signature modifications.
Their failures establish discrimination of these behaviors; they do not exhaust
possible wrong repairs. Imports/setup succeeded; these are assertion failures,
not timeout or cleanup failures. The original patch and source records were not
modified. New calibration workspaces alone contain the altered controls.

Full isolated EvaluationEngine replay of HB2 on v6 returned hidden PASS,
regression PASS, scope PASS, safety PASS and scope_compliant_success true. It uses
a separate manifest labelled operator-saved-patch-no-model and the exact submitted
patch hash 3ebc37224e9e574f456630af2a0db98cc6cd88bc72aaa31ec64207825a189b96.
No model/count call or paid cost occurred. This result does not replace HB2's
historical v5 FAIL or count as another autonomous solve.

## Evidence, validation and limits

External root: C:\pt\analyses\hf-v6-calibration-20261001-v1.
Journal: runs/run_dev_hfv6calibration.jsonl. Six control receipts include exact
diff hashes and full command outputs; evaluation/ holds the persisted replay
manifest and isolated results. Protocol and setup corrections are append-only.
The operator helper first omitted the prepared-source admission hash, then the
persisted evaluator manifest. Both were corrected before their respective
execution stages; completed controls were not rerun or retuned.

Package CLI validation, 7 package/integrity/projection tests and 5 documentation
checks PASS; Ruff and diff whitespace checks PASS. The first pytest invocation
could not create Windows default temporary directories; the same tests passed
with a fresh short external basetemp. Runtime/full suite and mock smoke were not
repeated for this package-only change; real isolated evaluation covers its
integration. No agent policy, prompt, task-v5 bytes or historical report changed.

Decision: v6 is calibrated for the stated development behavior contract. Keep
the agent baseline and historical outcomes unchanged; no paid rerun is queued.
Any future quality measurement must distinguish this exposed development package
from an original unmodified benchmark task and use a separately approved scope.
