# Task audit: mtplx-mixed-content-tool-call-stream

- Dataset role: admitted `core-cross-repo`
- Source: SWE-rebench leaderboard instance `youssofal__mtplx-21`,
  split `2026_03`
- Frozen benchmark revision:
  `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`
- Frozen benchmark row: `107`
- Upstream issue: <https://github.com/youssofal/MTPLX/issues/20>
- Upstream resolution: <https://github.com/youssofal/MTPLX/pull/21>
- Base commit: `c06cc13286e86d9ff3d2e3b991eba327549c534b`
- PR head: `a16a93b1f964d42509f490d52302eb972c42cd08`
- Merge commit: `3c0028b0700dd7b60281edcd748bc7ac9edfb63f`
- Created: `2026-05-07T19:59:26Z`
- Merged: `2026-05-07T20:33:55Z`
- License: Apache-2.0
- Retrieved: `2026-07-27`
- Task reference patch SHA-256:
  `sha256:d8f6e6d0fa4ebc181c261816591298f13c079bebc864514fc2097f61944003d5`
- Evaluator image:
  `swerebench/sweb.eval.x86_64.youssofal_1776_mtplx-21@sha256:32510a901064f5d405f3d4313a4556d924c94e72b2b0993296a43f04de83370e`
- Workflow: real-repository issue fix
- Failure pattern: streamed tool-call detection stops after ordinary content is
  observed
- Expected source change: `mtplx/server/openai.py`
- Benchmark declaration: four F2P and five P2P tests
- Contamination risk: high. The issue, PR, benchmark row, accepted patch, and
  one-file localization exposed by `allowed_paths` are public.

The frozen benchmark production patch changes two files. Its executable source
hunk is +71/-14 lines in `mtplx/server/openai.py`; its changelog hunk adds 14
lines. Thus the semantic production delta is +85/-14 (99 changed lines), while
the ledger's `gold_patch_lines=131` records serialized unified-patch lines.
Adversarial review found two false-positive boundaries in the accepted source
hunk: its marker stem also matched lookalike tags such as `<tool_calls>`, and
its final streaming parse could silently discard non-whitespace residue beside
or between complete blocks. The task therefore uses a hardened reference
policy rather than treating the upstream patch as sufficient. The reference
contains the accepted source change plus two stream-local guards: an exact
opening-tag delimiter and a residue check inside the streaming translator's
final parse path. It is +77/-15 (92 changed lines), excludes the changelog and
all upstream tests, stays within one allowed file, and introduces no dependency
or public API change. The global non-streaming parser remains unchanged and
continues accepting assistant preambles.

The exact accepted +71/-14 source patch remains in the known-bad corpus as
`upstream-accepted-missing-delimiter-residue.patch`, with SHA-256
`sha256:5850850bd5993c26aa1d963bf6f38eac694f0a4e799ab3c2db14fb74803094ad`.
This explicit distinction prevents an upstream merge from being mistaken for
the stronger independent acceptance contract.

The upstream test patch adds 158 test lines; the ledger's
`test_patch_lines=165` again counts serialized patch lines. All four F2P and
five P2P declarations are nodes from that patch, so they are useful benchmark
metadata but not an independent base-resident regression surface.

## Visible regression selection

An image probe of `tests/test_server_openai.py` and
`tests/test_openai_bridge.py` on the base commit reported 55 passing nodes and
three environment failures. The failing nodes instantiate MLX-backed session
paths; in the Linux CPU benchmark image, the absent MLX runtime leaves a stub
whose call signature does not satisfy those tests:

- `test_streaming_session_uses_generation_final_postcommit_without_retokenized_tail`
- `test_streaming_unsafe_postcommit_releases_without_blocking_second_request`
- `test_streaming_ar_keeps_retokenized_postcommit_path`

The registered check runs exactly those two files with three explicit
`--deselect` node arguments. `tests/test_session_bank.py` is not registered
because it fails collection when importing `mlx` in this image. These
exclusions are environment normalization, not task-specific acceptance
weakening: the independent hidden oracle exercises only the CPU/mock streaming
translator. The official base/no-op evaluation later reproduced all 55
registered regression passes with the same three explicit deselections.

## Independent acceptance design

The private oracle does not copy the upstream tests or assert any new helper
name. It uses different tool names, payloads, values, chunk layouts, and
reconstruction logic. Its 20 test functions collect as 21 cases because both
lookalike tags are parameterized. They cover:

- submitted-source binding;
- every two-chunk split boundary across preamble plus a complete tool call;
- adversarial multi-piece and mixed-case marker boundaries;
- release of disambiguated prefixes, exact round-trip of `<tool_calls>` and
  `<tool_calligraphy>` over every boundary, and a real call after a lookalike;
- exact finish-time release of the complete marker stem `<tool_call`;
- preamble plus two calls, ordered indices, unique call IDs, and reconstructed
  arguments;
- pure text, no-tool passthrough, and tool-only behavior;
- non-content field passthrough while a marker prefix is pending;
- exact flush of a dangling marker prefix at finish;
- rejection of same-buffer, pre-finish, and inter-call non-whitespace residue;
- acceptance of whitespace-only residue and post-call whitespace;
- preservation of the existing non-streaming preamble behavior; and
- one-character argument deltas with Unicode and nested values.

An authoring-time adversarial probe reported 21/21 hidden cases passing for the
hardened reference. The exact upstream accepted patch passed 14 and failed
seven, specifically demonstrating that the added boundaries are non-degenerate.
This probe was screening evidence; the official PatchLoop Docker matrix below
subsequently confirmed the hardened-reference and known-bad boundaries with
immutable run manifests and provenance artifacts.

The known-bad corpus contains nine semantic patches. Eight partial fixes
represent
removing only the content lock, recognizing markers only at a chunk start,
searching only the current chunk, searching only the initial buffer while
dropping the preamble, case-sensitive detection, no partial-tail retention,
one-character-only tail retention, and relaxing the trailing-text policy. The
ninth is the exact upstream accepted patch that lacks the delimiter and
residue hardening. A no-op and a forbidden test edit cover base rejection and
policy enforcement.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue points to the streaming bridge, but state transitions, buffering, parsing, and delta generation interact in a large server module. |
| Reasoning depth | 2 | A correct change must recognize a token across arbitrary chunks without losing bytes while preserving existing modes and protocol errors. |
| Implementation breadth | 1 | Only one production module changes and no public interface changes. |
| Verification breadth | 2 | Pure text, mixed text, multiple calls, field passthrough, marker lookalikes, case, finish, and trailing policy all interact. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

## Admission evidence

Admitted as the third `core-cross-repo` held-out task from clean harness commit
`82a0c23b6043481010b4aa5e1202fd4189b6ffc0`. The official 14-case Docker matrix
is recorded in
`reports/docker-gate/research-mtplx-mixed-content-tool-call-stream.json`.

- The hardened reference passed SCRR three times:
  `run_236767f9815b41e9`, `run_1e751bd099b44d82`,
  `run_647176898cdb411e`.
- Base/no-op preserved all 55 registered CPU/mock regressions but failed the
  21-case independent hidden oracle: `run_9a04e61629c74a27`.
- All nine semantic patches were rejected by hidden acceptance:
  - content-lock removal only: `run_7e3a2597aa464ab3`;
  - chunk-start marker detection only: `run_c8402fc708b043ec`;
  - current-chunk search only: `run_58f5c4143d9b43e4`;
  - initial-buffer search that drops the preamble:
    `run_4b088912a14741a1`;
  - case-sensitive marker scanning: `run_54eb40b2aa2b4ad1`;
  - no partial-marker tail retention: `run_75d42a5562464f21`;
  - one-character tail retention only: `run_8977994330c94642`;
  - relaxed trailing-text policy: `run_b564f13cb67146e2`; and
  - the exact accepted upstream source patch without delimiter and residue
    hardening: `run_7a98e3bcbf5c4e17`.
- The forbidden test edit was rejected by hidden acceptance, scope, and
  test-tampering policy: `run_89f4d3e5fd28425a`.

Every run was `official=true`, used the pinned image with network disabled and
a read-only submitted workspace, and made zero model/API calls. The image has
no configured user and therefore ran as Docker's default root user. The
evidence preserves the patch, manifest, result, and provenance hashes for each
run and keeps the upstream accepted patch explicitly separate from PatchLoop's
hardened reference policy.
