# Self-validation CSV infrastructure fixture

This package exists only to exercise the opt-in `task-public-v2` probe and
structured-review lifecycle. It deliberately mirrors the small CSV calibration
repository so the harness behavior is deterministic.

It is outside `tasks/`, is not listed in `data/dataset-manifest.yaml`, and must
not be counted as a calibration, memory-development, held-out, core, or
headline task.
