# PDM public contract v2

Development-only successor of pdm-ignore-active-venv-resolution v1.
The issue, repository, constraints and upstream regression are unchanged.
A new public selection check distinguishes exact active roots, descendants,
similarly prefixed siblings, false-like values and creation fallback for both
VIRTUAL_ENV and CONDA_PREFIX. It uses real Project/PythonInfo and temporary
stdlib venvs; discovery order and the creation return are controlled. Saved
interpreter precedence and full discovery/creation integration are outside it.

Version 1 is immutable. Private material and the image are copied unchanged,
except the private task-version metadata. This is not a new private evaluator
validation or acceptance result. No reference patch or hidden test informed
the public cases; all development results are official=false.

Public diagnosis and real-image validation:
C:\pt\analyses\pdm-public-resolution-review-20260916-v1\docker-followup
