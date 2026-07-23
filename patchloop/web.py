"""Read-only FastAPI/Jinja trace viewer."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from patchloop.runtime import repository_root, runtime_root
from patchloop.state import StateStore

app = FastAPI(title="PatchLoop Trace Viewer", docs_url=None, redoc_url=None)
web_root = repository_root() / "patchloop" / "web_assets"
templates = Jinja2Templates(directory=web_root / "templates")
app.mount("/static", StaticFiles(directory=web_root / "static"), name="static")


def _state() -> StateStore:
    return StateStore(runtime_root() / "state.sqlite3")


@app.get("/healthz")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"runs": _state().list_runs()},
    )


@app.get("/runs/{run_id}")
def run_detail(request: Request, run_id: str):
    state = _state()
    try:
        manifest = state.get_manifest(run_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    row = next(item for item in state.list_runs() if item["run_id"] == run_id)
    events = state.list_events(run_id)
    checkpoint = state.latest_checkpoint(run_id)
    patch_path = runtime_root() / "runs" / run_id / "submitted.patch"
    return templates.TemplateResponse(
        request=request,
        name="run.html",
        context={
            "row": row,
            "manifest": manifest,
            "events": events,
            "checkpoint": checkpoint,
            "checkpoints": state.list_checkpoints(run_id),
            "patch_text": (patch_path.read_text(encoding="utf-8") if patch_path.exists() else ""),
            "result_json": json.dumps(row["result"], indent=2, ensure_ascii=False),
        },
    )


@app.get("/runs/{run_id}/patch")
def run_patch(run_id: str):
    path = runtime_root() / "runs" / run_id / "submitted.patch"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="patch not found")
    return FileResponse(path, media_type="text/x-diff", filename=f"{run_id}.patch")


@app.get("/runs/{run_id}/events")
def run_events(request: Request, run_id: str):
    state = _state()
    if not state.has_run(run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={"events": state.list_events(run_id)},
    )


@app.get("/experiments")
def experiments(request: Request):
    records = []
    for path in sorted((runtime_root() / "experiments").glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        records.append(
            {
                "experiment_id": raw["experiment_id"],
                "completed_runs": raw["completed_runs"],
                "expected_runs": raw["expected_runs"],
                "infrastructure_errors": raw["infrastructure_errors"],
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="experiments.html",
        context={"experiments": records},
    )


@app.get("/experiments/{experiment_id}")
def experiment_detail(request: Request, experiment_id: str):
    path = runtime_root() / "experiments" / f"{experiment_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="experiment not found")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return templates.TemplateResponse(
        request=request,
        name="experiment.html",
        context={"experiment": raw},
    )
