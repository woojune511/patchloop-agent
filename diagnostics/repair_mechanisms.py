"""Build frozen E/J ablations in separate checkouts; never dispatch a solver."""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import subprocess
from pathlib import Path

from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash

BASE = "168765b55b7d5c26cdfc7ce50c0d70cf729e39b8"
J0_PROMPT_ORIGIN = "fcfa496dfb57f7e0d79616e5389fac034cfbc6b2"
BASE_RUNTIME = "sha256:2f0d160691daa1df55f1a9a671b7ff09881b53932559380eae6fc8abac7684d9"
ARMS = ("E0J0", "E1J0", "E0J1", "E1J1")
FILES = tuple(f"patchloop/dev/{name}.py" for name in (
    "tools", "runner", "model", "model_state", "working_plan",
))
E1_HELP = "mutation anchors precede current countercheck, then primary."
E0_HELP = "References get no priority; mutation anchors stay first."
J1_HELP = (
    "Missing bodies stay explicit. evidence_currency=current and closed_by_model never certify\n"
    "behavior. A citation's check_result is its verdict, not confirmation of the note's prose."
)
J0_HELP = (
    "status=current and model concern resolution never certify\n"
    "behavior. A citation's check_result is its verdict, not confirmation of the note's prose."
)


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root)


def base_sources(root: Path) -> dict[str, str]:
    return {p: git(root, "show", f"{BASE}:{p}").decode("utf-8") for p in FILES}


def replace_exact(text: str, old: str, new: str, *, count: int = 1) -> str:
    if text.count(old) != count:
        raise ValueError(f"Expected {count} exact occurrences: {old[:70]!r}")
    return text.replace(old, new)


def assignment(source: str, name: str) -> tuple[str, str]:
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return ast.get_source_segment(source, node), ast.literal_eval(node.value)


def completion_paragraph(source: str) -> str:
    prompt = assignment(source, "DEV_SYSTEM_PROMPT")[1]
    start = prompt.index("Check evidence_review ")
    return prompt[start:prompt.index("Call finish_task only", start)]


def transform(sources: dict[str, str], factor: str, legacy: dict[str, str]) -> dict[str, str]:
    """Two disjoint source transforms; validators and mutation authority are untouched."""
    out = dict(sources)
    model = "patchloop/dev/model.py"
    if factor == "E":
        tools = "patchloop/dev/tools.py"
        out[tools] = replace_exact(out[tools],
            "focus_references=self.focus_source_references(),", "focus_references=[],", count=2)
        runner = "patchloop/dev/runner.py"
        out[runner] = replace_exact(out[runner],
            "        optional = [] if replace_pending else evidence_focus.optional_exchanges(\n"
            "            state.get(\"working_notes\", {}).get(\"open_question\"), events, ids,\n"
            "            diff_hash=state[\"current_diff\"][\"patch_hash\"],\n"
            "        )",
            "        optional = []  # Experiment E0: no optional question-cited exchanges.")
        out[runner] = replace_exact(out[runner], "    evidence_focus,\n", "")
        out[model] = replace_exact(out[model], E1_HELP, E0_HELP)
    elif factor == "J":
        state = "patchloop/dev/model_state.py"
        out[state] = replace_exact(out[state],
            "from patchloop.dev.evidence_focus import project_interpretations\n", "")
        out[state] = replace_exact(out[state],
            "    project_interpretations(view, history, archive_kind=archive_kind)\n", "")
        plan = "patchloop/dev/working_plan.py"
        out[plan] = replace_exact(out[plan], assignment(out[plan], "INSTRUCTIONS")[0],
                                 assignment(legacy[plan], "INSTRUCTIONS")[0])
        out[model] = replace_exact(out[model], completion_paragraph(out[model]),
                                  completion_paragraph(legacy[model]))
        out[model] = replace_exact(out[model], J1_HELP, J0_HELP)
    else:
        raise ValueError(f"Unknown factor: {factor}")
    for path, source in out.items():
        ast.parse(source, filename=path)
    return out


def arm_sources(root: Path, arm: str) -> dict[str, str]:
    if arm not in ARMS:
        raise ValueError("Unknown E/J arm")
    source = base_sources(root)
    legacy = {p: git(root, "show", f"{J0_PROMPT_ORIGIN}:{p}").decode("utf-8")
              for p in ("patchloop/dev/model.py", "patchloop/dev/working_plan.py")}
    ej = transform(transform(source, "E", legacy), "J", legacy)
    je = transform(transform(source, "J", legacy), "E", legacy)
    if ej != je:
        raise ValueError("Factor transformations do not commute")
    for factor, enabled in (("E", arm[1]), ("J", arm[3])):
        if enabled == "0":
            source = transform(source, factor, legacy)
    return source


def verify_sources(root: Path, expected: dict[str, str]) -> None:
    """Keep frozen replay/arm identity exact, including unrelated source changes."""
    changed = [path for path, source in expected.items()
               if (root / path).read_bytes() != source.encode("utf-8")]
    if changed:
        raise ValueError("Frozen arm source mismatch: " + ", ".join(changed))


def prepare(checkout: Path, arm: str, output: Path) -> dict:
    """Require a separate, pristine checkout and write only the frozen changed files."""
    checkout = checkout.resolve()
    if checkout == repository_root().resolve():
        raise ValueError("Never patch the calling/product checkout")
    if git(checkout, "status", "--porcelain").strip():
        raise ValueError("Arm checkout must be clean")
    if runtime_content_hash(checkout) != BASE_RUNTIME:
        raise ValueError("Arm checkout is not the fixed common runtime")
    if output.exists():
        raise ValueError("Use a new evidence directory")
    source = base_sources(checkout)
    candidate = arm_sources(checkout, arm)
    # Check all bytes before writing any file, including Windows line-ending conversion.
    for path, text in source.items():
        if (checkout / path).read_bytes() != text.encode():
            raise ValueError(f"Noncanonical base bytes: {path}")
    output.mkdir(parents=True)
    journal = DevJournal(output, "run_dev_repairarm")
    journal.append("arm_preparation_started", {
        "arm": arm, "base_commit": BASE, "base_runtime_hash": BASE_RUNTIME,
        "checkout": str(checkout), "head": git(checkout, "rev-parse", "HEAD").decode().strip(),
        "provider_execution_authorized": False,
    })
    diff = []
    changed = []
    for path, text in candidate.items():
        if text != source[path]:
            changed.append(path)
            diff.extend(difflib.unified_diff(source[path].splitlines(True), text.splitlines(True),
                                            fromfile=f"a/{path}", tofile=f"b/{path}"))
            (checkout / path).write_bytes(text.encode())
    patch = "".join(diff).encode()
    (output / "experiment.patch").write_bytes(patch)
    receipt = {
        "arm": arm, "evidence_retention": bool(int(arm[1])),
        "judgment_support": bool(int(arm[3])), "base_commit": BASE,
        "test_source_commit": git(checkout, "rev-parse", "HEAD").decode().strip(),
        "checkout": str(checkout), "runtime_hash": runtime_content_hash(checkout),
        "changed_runtime_files": changed, "patch_sha256": digest(patch),
        "source_hashes": {p: digest(s.encode()) for p, s in candidate.items()},
        "provider_calls": 0, "input_count_calls": 0, "paid_cost_usd": "0",
        "provider_execution_authorized": False, "validation": "NOT_RUN",
    }
    (output / "arm.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    journal.append("arm_prepared", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.checkout, args.arm, args.output), indent=2))


if __name__ == "__main__":
    main()
