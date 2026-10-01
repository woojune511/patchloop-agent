# Conan probe environment follow-up

## Problem and choice

The prior wheel-only preparation failed on patch-ng>=1.18.0,<1.19. Investigated
whether the existing reviewed generated-wheel admission could supply it without
relaxing Conan requirements or disabling probes. PyPI's public 1.18.1 release has
only a 17,913-byte sdist, SHA-256
52fd46ee46f6c8667692682c1fd7134edc65a2d2d084ebec1d295a6087fc0291.
Its inspected setup metadata packages one pure-Python module with no runtime
dependencies; build-system requires setuptools and wheel.
Source: https://pypi.org/pypi/patch-ng/1.18.1/json.

Reused the existing reviewed setuptools 80.9.0 and wheel 0.45.1 public wheel
bytes after hash/size verification. Built once in the pinned clean probe image,
network none, no host mounts, one CPU, 512 MiB, 64 PIDs, 120-second timeout,
capabilities dropped and no-new-privileges. This was a package wheel build, not
an image build; Docker was already running and no image was pulled. Conan's
setup.py and evaluator materials were never used as build inputs.

## Result and change

Build succeeded and its container was removed. The explicit receipt binds source,
release metadata, build tools, script, result and wheel. Receipt SHA-256:
aa628192e41515c5a8304c7f2cb78074dcc0dcbf72308c49cd23518a582014f5.
The setup adapter now forwards the two existing generated-wheel receipt options;
ordinary resolver/admission behavior and agent tools remain unchanged.

Fresh preparation selected the reviewed wheel under unchanged public requirements
and published a dependency descriptor. Real DockerProbeSandbox preflight and
import canary passed: patch_ng version 1.18.1 and callable Conan
detect_emcc_compiler, exit 0, 7,849 ms, no timeout, cleanup confirmed.
The actual probe retained network none, read-only source/dependencies, non-root
user and existing resource limits. No behavior repair or general quality result
is implied. The original hidden evaluator remains separate and unchanged.

## Evidence and remaining scope

Root: C:\pt\preparations\original-next-20261001-v1.
Build: patch-ng-build-v1/receipt.json and runs/run_dev_patchngbuild.jsonl beneath
that build directory. Preparation: probe-dependencies-v2/prepared-probe-dependencies.json
and its preparation journal. Canary: runs/run_dev_conanprobecanary.jsonl.
The original failed probe-dependencies-v1 and all calibration records are preserved.
The host helper initially failed before dispatch due to its operator.py filename
shadowing a standard module; safe-path execution corrected this before the one
build attempt. No build retry occurred.

Probe import readiness is established, not complete runtime coverage. No paid
model call occurred. Any live invocation still needs exact model/credential/task/
repeat/cap authorization; earlier allocations remain closed.

## Validation

112 focused setup-adapter/generated-wheel/resolver/preparation tests PASS;
5 documentation tests, Ruff and diff whitespace checks PASS. The adapter test
also verifies receipt forwarding and hook restoration after admission failure.
Mock run_dev_9333dd6de3e54796 at C:\pt\validation\conan-wheel-mock-20261001 reaches
isolated EVALUATOR_PASS with safety NOT_RUN and zero paid cost. The full suite
was not repeated for this operator adapter option-forwarding change.
