# Task audit: tox-dotted-version-factor-base-python

- Dataset role: proposed `core-same-repo`
- Primary source: SWE-rebench leaderboard instance `tox-dev__tox-3846`, split
  `2026_03`
- Frozen benchmark revision: `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Benchmark row: 42
- Upstream issue: <https://github.com/tox-dev/tox/issues/3845>
- Primary resolution PR: <https://github.com/tox-dev/tox/pull/3846>
- Follow-up regression: <https://github.com/tox-dev/tox/issues/3850>
- Follow-up resolution PR: <https://github.com/tox-dev/tox/pull/3851>
- Benchmark base: `ae05f2a33ccfe52ff22ac578ec6c8eb9f750ce4a`
- Base tree: `b3844c56ae1eaad3c77231d079b9de92c81074f6`
- PR #3846 head: `0971603a6f1e14cb8cba2d294b1b887f2e2c2d6b`
- PR #3846 merge commit: `225e22835d121582560feebe52098190712babb5`
- PR #3851 head: `630c09e0dab517409bc90c17fff6df4066a17180`
- PR #3851 head tree: `85cd381bda9f6ad6e449c73a29d10ed84c9f1155`
- PR #3851 merge commit: `5e1db72ea6e4dbef2dfedaaf6a27de11f3820973`
- License: MIT; base `LICENSE` blob
  `364982344fbd94d55705e1f27a9a87abaa255333` (1,023 bytes)
- Retrieved: `2026-07-27T14:39:20Z`
- Benchmark gold patch SHA-256:
  `sha256:064fb6156cd9f3b2cda17dfad95f00e7ae8eca598755bc8bcdce282beaf84c85`
  (43 Python `splitlines()` records, 44 trailing-record ledger lines;
  documentation plus one production module)
- Benchmark test patch SHA-256:
  `sha256:bacf75f3e975c41a2ff1f150595b1f071a882d63818ec190854aae38ea091bd6`
  (33 Python `splitlines()` records, 34 trailing-record ledger lines)
- Evaluator image:
  `swerebench/sweb.eval.x86_64.tox-dev_1776_tox-3846@sha256:269a32558d3aeac5f9e9b6fc451302667b83a85f260f0b915babe1838b50b3bc`
- Benchmark declaration: seven F2P and 110 P2P nodes. The base-resident
  `tests/tox_env/python/test_python_api.py` check deterministically passes 101
  nodes after nine environment-incompatible nodes are explicitly deselected.
  Pytest treats a deselection node as a prefix, so deselecting
  `test_python_set_hash_seed` also removes the healthy `_negative` and
  `_incorrect` siblings; the registered command immediately runs those two
  exact nodes in a second invocation, restoring the intended 101-node surface.
- Expected source change: `src/tox/tox_env/python/api.py`
- Workflow: real-repository issue fix with accepted upstream follow-up hardening
- Failure pattern: factor extraction occurs before the configured conflict policy
  can handle ambiguous environment names
- Contamination risk: high. Both issues, both accepted PRs, tests and benchmark
  patch are public.

The benchmark patch for PR #3846 recognizes dotted factors inside compound
environment names and limits them to Python major versions 2 and 3. Within
hours, issue #3850 showed that this accepted change regressed real tox-ansible
names containing two Python-like factors. PR #3851 fixed both places where
factor extraction can raise before `ignore_base_python_conflict` is honored.
PatchLoop therefore uses the combined production state of #3846 and #3851 as
the hardened reference. The exact #3846 production patch is retained as a
known-bad semantic partial rather than accepted as the oracle solution.

The independent hidden oracle checks compound dotted factors at several
positions, free-threaded suffixes, classic factors, whole-name CPython/PyPy
normalization, rejection of major versions 4 and above, multiple-factor
diagnostics, default-resolution and validation handling with the ignore flag,
the default error when the flag is false, and the older single-factor override
contract. It deliberately does not require compound `qa-pypy-3.10`: the
accepted grammar treats `pypy` and `3.10` as separate factors in that form.
Bare `2.N` is a valid Python-like factor and can legitimately conflict with
another version.

The draft corpus contains ten semantic partials: the exact #3846 production
change without its follow-up, the exact #3851 production change without the
factor grammar, compound scanning with an overly broad major range,
major-range restriction without compound scanning, first-match conflict
suppression, loss of classic factors, loss of the free-threaded suffix,
default-only and validation-only ignore handling, and an over-broad validation
shortcut that changes the older single-factor contract. A no-op and a
forbidden test edit cover the base and scope/tampering boundaries.

This task is distinct from development task
`tox-cross-section-empty-substitution`. That task changes INI cross-section
empty-versus-missing resolution in `src/tox/config/loader/ini/replace.py`; this
task changes interpreter-factor grammar and conflict-policy propagation in
`src/tox/tox_env/python/api.py`. They do not share a module, trigger, state
transition, remediation, or solution lineage.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue identifies interpreter selection, but not both pre-policy extraction boundaries. |
| Reasoning depth | 2 | Grammar, normalization, ambiguity and two meanings of the ignore flag interact. |
| Implementation breadth | 1 | One production module changes without an API or dependency change. |
| Verification breadth | 2 | Main, regression, conflict, fallback, validation and legacy cases diverge independently. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

Admission remains pending. It requires a clean, network-disabled Docker matrix
showing base visible pass/private fail, three hardened-reference SCRR passes,
rejection of the exact #3846 partial and the other semantic/scope patches, and
content-addressed evidence. No such result is claimed by this draft.
