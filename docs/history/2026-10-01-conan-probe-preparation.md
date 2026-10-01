# Conan optional probe preparation

## Problem and decision

Conan's admitted original benchmark task has calibrated public/private checks,
but its optional clean Python probes need public runtime dependencies. Its
setup.py reads conans/requirements.txt rather than declaring PEP 621 metadata.
This preparation gap matters because silently disabling probes would change the
planned agent baseline. The question was whether explicit public requirements
selection could prepare that environment within existing wheel-only limits.

Extended the existing operator-only setup adapter with --requirements-file.
It reads literal project name/Python metadata without executing setup.py and
binds the selected requirements path/hash. It accepts PEP 508 index declarations,
not pip options, includes, URL/local/self dependencies or source escapes. This
is an operator selection, not inference of arbitrary setup.py semantics. The
ordinary runtime resolver and agent tools are unchanged.

## Observed result

One preparation attempt selected conans/requirements.txt and source roots conan
and conans against the previously frozen prepared source. Public dependency
resolution failed because patch-ng>=1.18.0,<1.19 has no usable wheels. Thus the
metadata adapter alone is insufficient for this task. The existing no-build
boundary held: no descriptor was published, no import canary ran, no versions
were changed, and no source build, Docker startup/pull or paid call occurred.
No automatic retry or alternate resolution was attempted.

External evidence root:
`C:\pt\preparations\original-next-20261001-v1\probe-dependencies-v1`.
`resolution-input.json` binds public inputs, `resolve.json` records the resolver
command/error, and `runs/run_dev_preparedependencies.jsonl` records the start and
failure in the append-only hash chain. Historical calibration is unchanged.

The remaining decision is how to supply this source-only dependency under a
separately scoped preparation method, or explicitly choose a probes-disabled
baseline. This record does not authorize either or a paid run. Original evaluator
readiness is separate from optional probe readiness and agent repair quality.

## Validation

101 focused adapter/resolver/prepared-dependency/documentation tests PASS; Ruff
and git diff --check PASS. Documentation checks were repeated after the record
update. Mock run_dev_bd3235f6d73e466c reaches isolated EVALUATOR_PASS with safety
NOT_RUN and zero cost, under C:\pt\validation\conan-requirements-mock-20261001.
This mock is not a Conan import canary. The full suite was not repeated for this
operator-only change; prior full-suite results are not current-commit evidence.
