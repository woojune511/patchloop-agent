.PHONY: setup test lint task-smoke agent-smoke experiment-smoke report audit serve

setup:
	uv sync --extra dev

test:
	uv run pytest

lint:
	uv run ruff check .

task-smoke:
	uv run patchloop eval-task tasks/smoke/csv-quoted-newline --patch tasks/smoke/csv-quoted-newline/reference.patch --backend local

agent-smoke:
	uv run patchloop run --task tasks/smoke/csv-quoted-newline/public.yaml --model mock --memory no_memory

experiment-smoke:
	uv run patchloop evaluate --suite experiments/smoke.yaml

report:
	uv run patchloop report --experiment offline-smoke --output reports/offline-smoke

audit:
	uv run patchloop dataset audit

serve:
	uv run patchloop serve
