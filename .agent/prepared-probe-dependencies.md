# Prepared public probe dependencies

`--enable-probes --prepared-probe-dependencies <descriptor>` lets `run_probe`
import public third-party dependencies and the current project implementation.
The model still supplies only a question and bounded Python source. Required
checks, finish eligibility, planning/context policies and cost controls are unchanged.

## Preparation

First prepare the exact public task source with `task prepare-source`. Choose either
the existing source-lock selection below or explicit public metadata resolution.

### Select from an existing source lock

Select
compatible wheels from that checkout's public `uv.lock` into a JSON document:

```json
{
  "schema_version": "public-probe-wheel-lock-v1",
  "source_lock": "uv.lock",
  "source_lock_hash": "sha256:<hash of the public lock bytes>",
  "source_roots": ["src"],
  "wheels": [
    {"url": "https://files.pythonhosted.org/packages/<exact wheel path>.whl",
     "hash": "sha256:<locked wheel hash>", "size": 12345}
  ]
}
```

Include the transitive wheel dependencies for the selected public extras. Keep only
`url`, `hash` and `size` in each selected wheel; optional upstream lock fields such
as `upload-time` do not belong in this input. Every selected tuple must occur in a
public PyPI registry package in the source lock. `uv export --frozen --offline`
can identify the package set before selecting compatible wheels; this command does
not select the wheel set automatically. Do not include the workspace project itself:
its source roots precede the dependency directory.

```powershell
patchloop task prepare-probe-dependencies <task-dir> `
  --prepared-source <prepared-source.json> `
  --wheel-lock <selected-public-wheel-lock.json> `
  --output <new-external-directory>
```

The initial implementation targets CPython 3.12, Linux amd64, on the existing pinned
clean Python image. The operator must already have `uv`. Preparation verifies the
source checkout, public lock hash, wheel origins and SHA-256/size; downloads exact
public PyPI wheels without redirects or environment credentials; and invokes
`uv pip install --offline --no-index --no-build` with a separate target and copy mode.
The Linux compatibility target is `x86_64-manylinux_2_28`. No package source builds,
project installation, image acquisition or Docker Desktop start occurs.

The descriptor `prepared-probe-dependencies.json` is published last. It binds the
repository/base, source/lock provenance, exact wheels, source roots, Python/platform
and every installed file. Failed or interrupted preparation has no usable descriptor.
Existing output directories are never overwritten; a corrected preparation uses a
fresh directory. Downloads and installed contents are capped at 256 MiB each,
with at most 128 wheels and 15,000 installed files. Local wheel URL metadata is
rewritten to its already verified public origin before publishing.

Workspace projects listed as editable in the public lock receive minimal name/version
metadata from their public `pyproject.toml`; no build hooks or project code run during
preparation. Static versions are preserved. Dynamic versions use
`0+patchloop.<source-commit>`, explicitly marked as a source snapshot, not a release
version. This permits `importlib.metadata.version()` during imports but does not reproduce
release-version decisions, entry points or complete distribution metadata. Those limits
also appear in the model's probe description. Current source imports remain authoritative.

### Resolve a repository without a source lock

```powershell
patchloop task prepare-probe-dependencies <task-dir> `
  --prepared-source <prepared-source.json> --resolve `
  --source-root src --output <new-external-directory>
```

`--resolve` reads only the exact checkout's root `pyproject.toml`. By default it selects
static `[project].dependencies`. Repeat `--extra <name>` to include declared optional
dependencies or `--group <name>` to include PEP 735 dependency groups. Group includes
are expanded with missing/cyclic entries rejected. No test/development group is selected
implicitly. Repeat `--source-root` to choose public import trees; omitted roots retain
the existing all-tracked-public-files snapshot. These three options require `--resolve`,
which is mutually exclusive with `--wheel-lock`.

Resolution uses installed `uv pip compile --format pylock.toml`, public PyPI and
`--only-binary :all:`. The command receives flattened validated PEP 508 requirements,
not project build hooks, source overrides, host configuration or operator credentials.
URL/path/self dependencies, dynamic dependency metadata, unsupported project Python,
missing extras/groups and packages without compatible wheels fail preparation. This
version supports static PEP 621/735 metadata, not setup.py or arbitrary requirements files.
The project itself is never downloaded or built; it receives the same minimal public
name/version metadata described above. Empty third-party dependency sets are supported.

Markers and wheel tags target CPython 3.12/Linux amd64, manylinux 2.28, independently
of the host. The marker baseline is Python 3.12.0; kernel release/version markers have
empty values. This is a recorded resolution target, not a reproduction of every image
patch/kernel attribute or of a task's check environment. One compatible wheel per
resolved package is selected, including transitive dependencies. Existing byte/file
bounds and offline hash-verified installation apply without changes.

The new external `resolved-wheel-lock.json` has schema
`resolved-public-probe-wheel-lock-v1`. It binds the prepared source descriptor/hash,
exact commit/tree/content, public metadata hash, selected groups/extras/requirements,
source roots, target marker environment/image, resolver executable hash, raw `pylock.toml`
hash and exact wheel URLs/hashes/sizes. `resolution-input.json` and `resolve.json` retain
the public inputs and resolver receipt. Resolution has a 120-second timeout and zero
HTTP retries; no failed preparation is automatically resumed or changed.

The final descriptor retains `prepared-probe-dependencies-v1` and embeds this provenance
in `wheel_lock`. Existing bundles, runtime admission, per-probe independent copies and
closed-run reading contracts remain compatible. Reuse the completed descriptor for
offline execution; `--wheel-lock` continues to accept the original source-lock selection
schema, not this new audit record. A later `--resolve` is a fresh preparation whose
package versions may differ. Never silently re-resolve an admitted run.

See [uv locking](https://docs.astral.sh/uv/pip/compile/), the
[pylock specification](https://packaging.python.org/en/latest/specifications/pylock-toml/)
and [target wheel tags](https://packaging.pypa.io/en/stable/tags.html).

See [uv's CLI reference](https://docs.astral.sh/uv/reference/cli/) for offline,
target, platform and no-build semantics, and the
[wheel specification](https://packaging.python.org/en/latest/specifications/binary-distribution-format/)
for the binary distribution format. Preparation is operator work outside the agent loop.

## Execution and recovery

Add the descriptor to the existing fully specified `patchloop dev` command:

```text
--enable-probes --prepared-probe-dependencies <prepared-probe-dependencies.json>
```

Missing, changed or wrong-source bundles fail normal preflight before model dispatch;
there is no network fallback. Admission records the descriptor/content identity in
the envelope and hash-chained journal. Active resume revalidates contents; terminal
receipt replay stays read-only. Omitted options keep the previous stdlib behavior
and serialized optional fields remain absent for older manifests/envelopes.

Each probe independently copies and verifies the public dependency files, then mounts
that snapshot read-only at `/opt/patchloop-dependencies`. With nonempty source roots,
the source snapshot contains tracked regular repository-root files and those source
trees, including accepted edits. Other trees are omitted. With empty roots, all tracked
regular public files are selected. The existing 128 MiB source bound stays in force.
Choose source roots covering the project implementation and any needed public fixtures.

In this opt-in mode, tracked symlinks are omitted without reading/following them;
omitted link paths are bound into the snapshot hash. Unexpected links/reparse points
replacing regular files, submodules and merge stages in selected trees remain failures.
Default stdlib probes retain their original strict snapshot behavior.

Import order is `/workspace`, the configured public source roots, then dependencies.
The trusted parent reads only its host-written path configuration; the child installs
the existing process filter before exposing these paths. Dependency `.pth` startup
hooks are not processed. The tool description states the capability and source omissions;
local preparation paths never enter model input. Import failures remain diagnostics.

Image, no-network policy, nonroot user, read-only root/mounts, process filter,
CPU/memory, scratch, output/timeout and cleanup limits remain in force. The v2 profile
supports [bounded same-process threads](probe-threads.md) with pids=8 (supervisor,
child and at most six workers); new processes remain denied. The profile hash
includes the bundle identity and snapshot policy. Probe receipts and submitted manifests
carry the same identity; isolated evaluation validates provenance without mounting the
bundle or exposing its own environment to arbitrary probe code. Execution success never
grants required-check credit or certifies the model's behavioral question.

## Evidence and limits

Tests cover preparation failures, exact public bytes, overwrite rejection, offline
independent copies, missing/changed bundles, early failure, active/terminal recovery,
both actual context inputs, sandbox wiring and evaluator receipt binding.
The Pydantic AI public profile contrast exercises actual source imports through
the clean image, with prepared public wheels and no evaluator-image reuse.

Evidence root: `C:\pt\analyses\prepared-probe-dependencies-20260918-v1`.
External resolution evidence: `C:\pt\analyses\resolved-probe-dependencies-20260921-v1`.
Focused69 PASS/24.90s; full3079 PASS/16 SKIP/0 failures across140 files in1040.145s.
Ruff, lock consistency and both-policy isolated mocks with10 actual inputs pass.
The exact AnyIO public source prepares its two runtime dependencies successfully.
An explicit test-group/trio-extra preparation stops because forbiddenfruit has no
usable wheel; it publishes no descriptor. No dependency was dropped or built to
bypass this failure. This evidence covers preparation and provider-free mock execution,
not an actual Linux probe import or another model experiment.
This feature is opt-in and does not establish improved model decisions or acceptance.
Packages requiring new processes, more threads than the fixed limit, runtime installation
or unsupported platform dependencies can still fail under the sandbox. Dependency
availability does not imply broader permissions or an automatic retry.
