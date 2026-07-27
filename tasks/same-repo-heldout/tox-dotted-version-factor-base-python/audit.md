# Task audit: tox-dotted-version-factor-base-python

- Dataset role: admitted `core-same-repo`
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

The official corpus contains ten semantic partials: the exact #3846 production
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

The clean, network-disabled official Docker matrix recorded:

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| hardened #3846 + #3851 reference | `run_41553bac68ee4214`, `run_6917e86f2f2a4a20`, `run_0fd0206fb8144eb9` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_4bd98e35f36c4fe7` | visible pass, hidden fail | rejected |
| exact #3846 without follow-up | `run_a64d4e9fd59c4f6f` | ignored-factor conflict handling fail | rejected |
| exact #3851 without factor grammar | `run_a4d76dfa461c420e` | compound dotted-factor extraction fail | rejected |
| restrict major only | `run_cf5d23ef8f1047e4` | compound dotted-factor extraction fail | rejected |
| explicit factors only | `run_2ffd9b9ee3ad4931` | classic-factor regression | regression and hidden fail |
| first match wins | `run_0274332691db4949` | conflict detection fail | regression and hidden fail |
| ignore every validation conflict | `run_b17cf94c4e404256` | older single-factor override contract fail | regression and hidden fail |
| ignore in default resolution only | `run_8b68477a7bc542dc` | validation conflict-policy fail | rejected |
| ignore in validation only | `run_0499c984ec814e1c` | default-resolution conflict-policy fail | rejected |
| strip compound threaded suffix | `run_60fb1826103d45bf` | free-threaded factor fail | rejected |
| accept dotted major 4 and above | `run_7d153b8ec0e44c95` | non-Python dotted-factor guard fail | regression and hidden fail |
| forbidden test edit | `run_4efaa4b1bbe549f6` | hidden, scope and test-tampering fail | rejected |

The private oracle collects 17 cases from eight test functions. The registered
visible check covers 101 of the benchmark's 110 declared P2P nodes: the first
invocation passes 99 after nine deterministic environment-incompatible nodes
are deselected, and a second invocation re-includes two healthy sibling nodes
that pytest's prefix deselection also removed. Base/no-op and every semantic
partial failed hidden acceptance; four semantic partials also failed visible
regression. The forbidden edit passed the regression and aggregate safety
verdicts but failed hidden acceptance, scope and test-tampering policy.

All 15 runs used clean harness commit
`678d30a50ae27cb48623c1fbe5bc04bb65d34bad`, the digest-pinned evaluator
image and `official=true`. The public task hash is
`sha256:1e05ada1d2812b270851bb9770ad6071629cb48dff1114d908a197085605b3f9`,
the private task hash is
`sha256:80bf4aa66ed0247cacad1bcd772de4de90ebcdafa48b64ea924330a53cf341e1`,
and the hardened reference hash is
`sha256:3245865999cca1398bc922389d93f9f92d8729da19423fcda7e23a0275d4bb37`.
The [admission report](../../../reports/docker-gate/research-tox-dotted-version-factor-base-python.json)
binds each patch, manifest, result and provenance artifact; its SHA-256 is
`sha256:216ccfd1f9017ca499c9902ac857a2e6d4ebc0dca1aeb1aff04e9af396485fe6`.

The external image has no configured `User`, so Docker ran it as the default
root user. Network denial and read-only root and submitted filesystems remained
enforced; this limitation is not conflated with the native PatchLoop image's
separate non-root smoke.

This is deterministic evaluator admission evidence with zero model calls,
API calls, tokens and model cost. It is not a live-model task result or a core
campaign performance measurement.
