# jsonschema source and probe preparation

Provider-free preparation for public issue #1538. No autonomous repair was run.

## Change and evidence

Add only `https://github.com/python-jsonschema/jsonschema.git` to the existing
repository allowlist. Arbitrary remote URLs remain rejected. Normal source
preparation now succeeds at the previously pinned commit
`51cd75e399c760e5aa3adce600dcce1385756ab0`; no alternate clone path was used.

Prepare static runtime dependencies, the public test group and format-nongpl
extra as a hash-bound Python 3.12/Linux wheel bundle. The existing clean Python
probe image executes this bundle offline with read-only source/dependencies.
No Docker start, image download or image build occurred.

An initial operator configuration used source_roots=["."], which omitted the
package tree from the snapshot. Both initial programs failed to import jsonschema.
Those records and the bundle remain unchanged. A separate bundle explicitly
selects ["jsonschema"], preserving the normal source-root filtering contract.
This preparation error was not an agent or product defect.

## Executed public checks

On unchanged source, Python 3.12.13:

| Input/check | Result |
| --- | --- |
| Valid regex [a-z]+ | Zero validation errors |
| Invalid regex [ | One validation error, no escaped exception |
| Public issue input: 500 opening parentheses | Escaped RecursionError |
| Upstream jsonschema.tests.test_format | 8 passed; zero skips/errors/failures |

Thus the Python 3.13 issue reproduces on the available Python 3.12 environment.
The reproduction wrapper catches the exception to record it: its execution PASS
does not mean the issue is fixed. The upstream regression also passes unchanged
source and cannot by itself establish repair of this bug. All probe cleanup was
confirmed. No production patch or new expected-value oracle was introduced.

## Identities and limits

External root: `C:\pt\preparations\jsonschema-1538-20261001-v2`.

- Source manifest: `source\prepared-source.json`;
  `sha256:21fc91dc7f69981c6caa661c90ead7140f72b7193e0d23cc78920abaf503bab8`.
- Dependency descriptor: `dependencies-package-root\prepared-probe-dependencies.json`;
  `sha256:7a953e7a913601fcbfa14bdb3d474257a8e5616a393952e26ca697bf185787cf`.
- Dependency content:
  `sha256:97bffed0cb577a87cdd96c27eb392b0bbd5a7145aba40b0a1e794f6062cf02c1`.
- Journal: `audit\runs\run_dev_ac3fbd909d62437a.jsonl` (15 events verified at close-out).
- Public draft: `public-draft.json`; preparation input only, not an admitted task.

Source and optional-probe readiness are established. Registered-check and isolated
evaluation environment readiness are NOT established: prepared probe dependencies
do not automatically become evaluator dependencies. No checked-in dev-train task
or exact live proposal exists. The next step is explicit task/check admission,
retaining the distinction between public checks and independent evaluation.

The earlier failed source preparation and rejected SQLGlot candidate are preserved
under the v1 intake roots. Provider calls and new budget allocations: zero.

Focused prepared-source tests passed (29). Ruff passed. Mock smoke reached
EVALUATOR_PASS with safety NOT_RUN, which is not live safety evidence. Full-suite
validation is recorded separately in the current preparation note after completion.
