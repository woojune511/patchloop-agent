# Evidence index

This document links to canonical machine artifacts. It does not duplicate the full historical narrative,
which is preserved at `docs/archive/snapshots/d121/09-evidence.full.md`.

## D-129 offline successor — approval required

- Gate `reports/live-pilot/artifacts/d129-d128-terminal-successor-offline-source-gate.json`:
  ID `d129_fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c`;
  body `sha256:fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c`;
  file `sha256:fd57c187d1f260952b581e60f7d0ff98243f3b4ef172c9a6d6669b3e84968512`;
  18,678 bytes; status `D129_D128_TERMINAL_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED`.
- Clean source commit `1fef6716cddca571777c8b7f9f1dc4501f988d1c`; tree
  `eda4ca04aa6998d46bd4fba7c96e2a5fa487cea4`; sole parent
  `4633f867ebd8b1ad8f6c6cd0dc357250fbe58d81`.
- Focused tests 12/12; selected D-122–D-129 regression union 115/115. Selected includes focused, so these counts
  are not additive.

The gate records two user-reported checks of `npipe:////./pipe/dockerDesktopLinuxEngine`: first daemon
unavailable/rc 1, later client/server 29.6.2, linux/amd64/rc 0. The user also reported no pre-existing
container auto-start. These facts are self-attested, unauthenticated, not independently agent-observed and not
preserved as raw output; a future receipt-bound phase must reobserve them.

D-129 invoked zero Docker, network, pricing GET, SDK, provider, evaluator, agent, retrieval or runtime-memory
calls and made no image/container mutation. Historical D-128 agent Docker calls remain three. No D-129 receipt,
external attempt, pricing/preflight, execution hash/candidate, reservation/cost or A/C run exists. The next
approval must quote the exact tuple above, 18,678 bytes and the eventual local evidence commit that tracks this
gate; the offline artifact cannot self-bind that descendant commit.

## D-128 external successor — historical terminal blocked

- Offline predecessor gate ID `d128_9edb9d1396b2f572c3b1ade623c7c5f6fb3fdf083d17a71680e7f1041bfba7de`;
  body `sha256:9edb9d1396b2f572c3b1ade623c7c5f6fb3fdf083d17a71680e7f1041bfba7de`;
  file `sha256:2528aa018908958bdd35b4b6202c75be2b4ca72521d64bfed800284a015a739c`; 12,557 bytes;
  evidence commit `aeac01a04447c731ee5eac4c56e599eb74532a60`.
- Source `23038c16467a32c5b862f84e09797a298101f4e4`; tree
  `46862cc0d48035e866d8d5086926391b56f90ba2`; sole parent `aeac01a04447c731ee5eac4c56e599eb74532a60`.
- Receipt commit `4b2ef5a15e9c721c1c8fa1e73375a3bf061bda50`; tree
  `2d01c39b264cff0abf18ec1a11a05c49b2507895`; sole parent the source commit.
- Receipt `reports/live-pilot/artifacts/d128-d127-terminal-successor-external-no-call-preflight-approval-receipt.json`:
  ID `d128approval_11c8d00ba507ead135d82db96de9e0d2ff66600b06801261daad6bf5c25abacd`;
  body `sha256:11c8d00ba507ead135d82db96de9e0d2ff66600b06801261daad6bf5c25abacd`;
  file `sha256:b5cb1e1d65e1a1d3ebf726ba85031ccb66dfb7cf950fab1dde68cbeebaf72050`; 7,713 bytes.
- Attempt `reports/live-pilot/artifacts/d128-docker-image-readiness-remediation-attempt-intent.json`:
  ID `d128dockerimagereadinessremediationattempt_25c78d210117696eb1f2f8b7f73069c022b9bb00b332bc83350eb5dab388cc21`;
  body `sha256:25c78d210117696eb1f2f8b7f73069c022b9bb00b332bc83350eb5dab388cc21`;
  file `sha256:04c5d2a32bc908d2dfc4b754779ec75a43aee19ff28c68c1bc7843c4d38c71c5`; 5,583 bytes.
- Terminal `reports/live-pilot/artifacts/d128-exact-docker-image-readiness-remediation-observation.json`:
  ID `d128dockerremediation_2682a64e07d869c9989f02028d994f7e16a50327f07b0692917475cdac0ad78f`;
  body `sha256:2682a64e07d869c9989f02028d994f7e16a50327f07b0692917475cdac0ad78f`;
  file `sha256:77dbd861466e5ce4913a0a7f0c4d1240b83a0a5be5169571c104c0e42a95e939`; 9,270 bytes;
  status `D128_EXACT_DOCKER_IMAGE_READINESS_REMEDIATION_OBSERVED_BLOCKED`; blocker
  `already-running-docker-desktop-linux-daemon-unavailable`.

The exact CLI made three read-only calls (`version`, Moto inspect, Babel inspect), all return code 1.
Desktop/daemon start, pull/mutation, container/workload, provider/evaluator/agent, retrieval/injection, pricing
GET, SDK attempt, hash/candidate, cost and A/C counts are zero. No pricing/preflight/gate descendant exists.
The receipt is consumed. Later D-129 self-attestation does not reopen or rewrite this terminal.

## D-127 terminal blocked Docker remediation

- Receipt, attempt and terminal artifacts are under `reports/live-pilot/artifacts/` with the `d127-` prefix.
- Terminal status `D127_EXACT_DOCKER_REMEDIATION_OBSERVED_BLOCKED`; source
  `cec335f345a56d544614fe0c9ec3e75cba78bf17`.

Static imported only the `OPENAI_API_KEY` name. Six read-only Docker calls recorded blocker
`preexisting-container-auto-restart-state-unverified`; every mutation/later action stayed zero and the receipt
is consumed. Exact historical tuples remain in the canonical artifacts and D-129 predecessor binding.

## D-126 clean-source/pricing/no-call preflight

Receipt, preflight and gate artifacts use the `d126-ac-clean-` prefix under `reports/live-pilot/artifacts/`.
Gate status is `D126_CLEAN_SOURCE_PRICING_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED`; it binds source
`68b7c8b0779a33443a4a4e5ae423e3c64e0e1d22`. It recorded fresh pricing, 12 Docker reads and a zero-network
SDK probe but five blockers and no replayable raw pricing bytes. It created no hash/candidate/live/cost
authority. Exact historical tuples and blockers remain in the canonical artifacts.

## Historical A/C source predecessors

D-122 through D-125 gates under `reports/live-pilot/artifacts/` preserve fixed delivery, cost/settlement and
local/mock finalization source history. They created no live authority; use their sealed-historical validators.

## Historical/deferred D-121 preparation

D-121 artifacts under `reports/memory-development/` verified no-start configuration only. Runtime isolation
and successor execution remain false; the deferred candidate ID appears only in `docs/current-status.md`.

## No-memory baseline

`reports/live-pilot/dev-no-memory-condition-neutral-3000k-20260805-r1.json` seals 12 terminal rows, 11
official-evaluator rows and 2 resolved task pairs. Its token/cost details are development evidence only.

## Structured-memory chain

D-103 through D-115 artifacts under `reports/memory-development/` preserve three-entry admission/render/freeze,
the +702 exact-pair count and failed selective-scoring diagnostics. None records runtime injection or a
memory-conditioned outcome.

## Deferred applicability/isolation chain

D-116 through D-121 retain the applicability, source, partial-isolation and no-start evidence under
`reports/memory-development/`. No classifier/successor run was authorized; this lane is off the A/C path.

## Historical documentation snapshot

The exact pre-reorganization active documents are under `docs/archive/snapshots/d121/`. See
`docs/archive/snapshots/d121/snapshot-manifest.json` for original paths, byte sizes and SHA-256 values.

The snapshot is historical evidence, not current authority. Its source worktree was dirty relative to HEAD;
the manifest records that limitation explicitly.
