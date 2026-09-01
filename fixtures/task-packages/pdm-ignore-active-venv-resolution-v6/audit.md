# PDM public behavior-check successor v6

This package preserves the version-1 repository commit, environment, reference patch and hidden evaluator bytes. It is
an append-only successor to task-v5, which was consumed by qualification-v6; only the public task version/check surface
and matching private metadata version are changed.

It lives under `fixtures/task-packages/` as an opt-in offline successor. It is not registered in the frozen dataset
manifest and therefore cannot silently replace or reinterpret the consumed version-1 task.

The exact base-commit public implementation independently fixes the Conda setup used by the targeted check:
`os.getenv("VIRTUAL_ENV", os.getenv("CONDA_PREFIX"))` falls back to `CONDA_PREFIX` only when `VIRTUAL_ENV` is absent,
not when that key is present with an empty value. The public task requires both active-environment variables but does
not require an empty `VIRTUAL_ENV` to defer to Conda. Task-v6 therefore changes only the `conda-false-zero` fixture from
`virtual_env=""` to `virtual_env=None`, representing a Conda-only environment while retaining the false-like `"0"`
assertion. It removes no case and changes no expected result.

Public source evidence:

- immutable `core.py` at base commit:
  `https://github.com/pdm-project/pdm/blob/881cd4e38d31663ae67bdae227ec1ccdfd5e2c77/src/pdm/project/core.py`
- immutable `config.py::ensure_boolean()` at base commit:
  `https://github.com/pdm-project/pdm/blob/881cd4e38d31663ae67bdae227ec1ccdfd5e2c77/src/pdm/project/config.py`

No hidden assertion, reference patch body or reference result determines this delta. The package is locally
schema/syntax qualified only; it grants no Docker, task, evaluator, provider, network or paid authority.
