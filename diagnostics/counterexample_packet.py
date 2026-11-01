"""Verified public observations for one operator-assisted repair continuation.

This reads the frozen public comparison only. It neither executes its program nor
loads task/evaluator material. Acceptance preserves the baseline's eleven correct
cases; the shared pre-existing discrepancy remains separately reported.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

SCHEMA = "public-counterexample-packet-v1"
PREFIX = "PUBLIC-PATH-CONTRACT:"
METHOD = "Public documented search-root semantics; importlib PathFinder comparison"
CANDIDATE_DIFF_HASH = "sha256:141dc0f8e373a23b7379661de8c08b3b0f07c6fa010f2d7bbb8b18b0ed74967f"
SOURCE_HASHES = {
    "manifest": "sha256:6f2b5a7729a3f5404d4099143774b8b8d637d5743bd9657686a71238574efad9",
    "result": "sha256:2025fe629bf0dcf33db4814880a7747d595f6ce6fc45b8e3758d648eccc0533e",
    "program": "sha256:55ec5e3aa9d125372d9f710e81d5fd7529dd4809db81e4c10c28f9cdc3617353",
}
CASE_IDS = (
    "namespace_root_explicit", "namespace_root_implicit", "namespace_root_empty",
    "namespace_leaf_explicit", "namespace_leaf_implicit", "namespace_leaf_empty",
    "namespace_child", "regular_package", "split_namespace", "split_leaf_forward",
    "split_leaf_reverse", "absent_module",
)
REGRESSION_IDS = ("namespace_leaf_explicit", "split_leaf_forward", "split_leaf_reverse")
PREEXISTING_IDS = ("namespace_root_empty",)
INPUT_FIELDS = ("case", "parts", "mode", "search")
OUTCOME_FIELDS = ("public_api", "lower_resolver", "importlib_reference")


def require(condition, message):
    if not condition:
        raise ContractError(message)


def _read(path, expected_hash, evidence):
    require(path.is_file() and not path.is_symlink(), "public evidence is not a regular file")
    raw = path.read_bytes()
    require(sha256_bytes(raw) == expected_hash, "public evidence hash changed")
    evidence[str(path.resolve())] = expected_hash
    return raw


def _artifact(root, reference, evidence):
    require(isinstance(reference, dict), "invalid public artifact reference")
    path = Path(reference.get("path", ""))
    require(path.resolve().is_relative_to((root / "artifacts").resolve()),
            "public artifact outside comparison root")
    raw = _read(path, reference.get("content_hash"), evidence)
    require(type(reference.get("size_bytes")) is int
            and len(raw) == reference["size_bytes"], "public artifact size changed")
    return raw


def _strings(value, *, maximum, prefix=None):
    return (isinstance(value, list) and 0 < len(value) <= maximum
            and all(isinstance(item, str) and 0 < len(item) <= 512
                    and (prefix is None or item.startswith(prefix)) for item in value))


def _outcome(value):
    require(isinstance(value, dict), "invalid public outcome")
    if value.get("status") == "ImportError":
        require(set(value) == {"status"}, "invalid ImportError outcome")
        return
    require(value.get("status") == "found", "unexpected diagnostic error or outcome")
    require(set(value) == {"status", "type", "location", "namespace_paths"},
            "invalid found outcome fields")
    require(value["type"] in {"PY_NAMESPACE", "PY_SOURCE", "PKG_DIRECTORY"},
            "unknown module outcome type")
    paths = value["namespace_paths"]
    if value["type"] == "PY_NAMESPACE":
        require(value["location"] is None and _strings(paths, maximum=2, prefix="$FIXTURE/")
                and len(paths) == len(set(paths)), "invalid namespace outcome")
    else:
        require(isinstance(value["location"], str)
                and value["location"].startswith("$FIXTURE/")
                and len(value["location"]) <= 512 and paths == [], "invalid source outcome")


def _rows(rows):
    require(isinstance(rows, list) and len(rows) == len(CASE_IDS), "incomplete case matrix")
    names = []
    for row in rows:
        require(isinstance(row, dict)
                and set(row) == {*INPUT_FIELDS, *OUTCOME_FIELDS, "matches_reference"},
                "invalid public case fields")
        require(isinstance(row["case"], str), "invalid case id")
        names.append(row["case"])
        require(_strings(row["parts"], maximum=2)
                and row["mode"] in {"explicit", "implicit", "empty"}
                and _strings(row["search"], maximum=2, prefix="$FIXTURE/"),
                "invalid public case input")
        for field in OUTCOME_FIELDS:
            _outcome(row[field])
        matches = row["public_api"] == row["importlib_reference"]
        require(type(row["matches_reference"]) is bool
                and row["matches_reference"] == matches, "stale public case verdict")
    require(len(set(names)) == len(names) and set(names) == set(CASE_IDS),
            "duplicate or unexpected case id")
    return copy.deepcopy(rows)


def parse_receipt(receipt: dict, program_hash: str) -> dict:
    """Return the complete public report, rejecting uncertain or contradictory data."""
    require(isinstance(receipt, dict), "invalid probe receipt")
    require(receipt.get("status") == "passed" and type(receipt.get("exit_code")) is int
            and receipt["exit_code"] == 0, "probe did not complete successfully")
    require(all(receipt.get(key) is False for key in
                ("cleanup_failed", "timed_out", "truncated", "deadline_exhausted")),
            "incomplete or uncertain probe receipt")
    policy = receipt.get("execution_policy")
    require(isinstance(policy, dict) and policy.get("cleanup_status") == "confirmed",
            "probe cleanup is uncertain")
    require(receipt.get("source_hash") == program_hash, "probe program hash changed")
    stdout = receipt.get("stdout")
    require(isinstance(stdout, str) and len(stdout.encode()) <= 12_000,
            "invalid or oversized probe output")
    reports = [line[len(PREFIX):] for line in stdout.splitlines() if line.startswith(PREFIX)]
    require(len(reports) == 1, "missing or ambiguous public report")
    try:
        report = json.loads(reports[0])
    except (ValueError, TypeError) as exc:
        raise ContractError("invalid public report JSON") from exc
    require(isinstance(report, dict) and set(report) == {"python", "rows", "method"},
            "invalid public report fields")
    require(report["python"] == [3, 9, 25] and report["method"] == METHOD,
            "public probe environment or method changed")
    return {"python": report["python"], "method": METHOD, "rows": _rows(report["rows"])}


def build_packet(root: Path) -> dict:
    """Read run-v1 plus its sibling probe.py, without executing or adding context."""
    root = Path(root).resolve()
    evidence = {}
    manifest = json.loads(_read(root / "manifest.json", SOURCE_HASHES["manifest"], evidence))
    result = json.loads(_read(root / "result.json", SOURCE_HASHES["result"], evidence))
    program_path = root.parent / "probe.py"
    source = _read(program_path, SOURCE_HASHES["program"], evidence)
    require(manifest.get("schema") == "public-path-contract-comparison-v1"
            and manifest.get("official") is False and manifest.get("order") == ["base", "candidate"]
            and manifest.get("candidate_patch_hash") == CANDIDATE_DIFF_HASH,
            "comparison manifest identity changed")
    inputs = manifest.get("input_hashes", {})
    require(isinstance(inputs, dict)
            and any(Path(path).resolve() == program_path and digest == SOURCE_HASHES["program"]
                    for path, digest in inputs.items()), "program input identity changed")
    require(_artifact(root, manifest["execution"], evidence) == source,
            "frozen program differs from public source")
    require(result.get("schema") == "public-path-contract-result-v1"
            and result.get("status") == "COMPLETED" and result.get("official") is False,
            "comparison is not complete")
    identity = result.get("probe_identity")
    require(isinstance(identity, dict) and set(identity) == {"image_digest", "profile_hash"},
            "invalid comparison environment")
    observations = result.get("observations")
    require(isinstance(observations, dict) and set(observations) == {"base", "candidate"},
            "invalid comparison variants")
    reports, policies = {}, {}
    for variant, observation in observations.items():
        expected = CANDIDATE_DIFF_HASH if variant == "candidate" else sha256_bytes(b"")
        require(observation.get("diff_hash") == expected, "comparison diff changed")
        receipt = json.loads(_artifact(root, observation["receipt"], evidence))
        report = parse_receipt(receipt, SOURCE_HASHES["program"])
        require(all(receipt.get(key) == value for key, value in identity.items()),
                "probe environment changed")
        require(report["rows"] == observation.get("rows")
                and report["python"] == observation.get("python")
                and report["method"] == observation.get("method"), "raw public report mismatch")
        reports[variant] = {row["case"]: row for row in report["rows"]}
        policies[variant] = receipt["execution_policy"]
    require(policies["base"] == policies["candidate"], "comparison execution policy changed")
    cases, mandatory, regressions, preexisting = [], [], [], []
    for name in CASE_IDS:
        base, candidate = (reports[variant][name] for variant in ("base", "candidate"))
        require(all(base[field] == candidate[field] for field in INPUT_FIELDS)
                and base["importlib_reference"] == candidate["importlib_reference"]
                and base["lower_resolver"] == candidate["lower_resolver"],
                "comparison inputs or reference changed")
        if base["matches_reference"]:
            mandatory.append(name)
            if not candidate["matches_reference"]:
                regressions.append(name)
        else:
            require(candidate["public_api"] == base["public_api"],
                    "pre-existing discrepancy changed")
            preexisting.append(name)
        cases.append({**{field: base[field] for field in INPUT_FIELDS},
                      "base": base["public_api"], "candidate": candidate["public_api"],
                      "importlib_reference": base["importlib_reference"]})
    require(regressions == list(REGRESSION_IDS) and preexisting == list(PREEXISTING_IDS)
            and len(mandatory) == 11, "comparison acceptance partition changed")
    return {"schema": SCHEMA, "evidence_files": evidence,
            "program_text": source.decode("utf-8"), "program_hash": SOURCE_HASHES["program"],
            "candidate_diff_hash": CANDIDATE_DIFF_HASH,
            "task_path": manifest["task"], "baseline": manifest["baseline"],
            "environment": {**identity, "python": [3, 9, 25],
                            "dependencies": policies["base"]["dependencies"]},
            "mandatory_case_ids": mandatory, "regressions": regressions,
            "preexisting_discrepancies": preexisting, "cases": cases}


def model_visible(packet: dict, current_diff: str) -> dict:
    """Project observations only; a changed candidate makes these observations stale."""
    matched = current_diff == packet["candidate_diff_hash"]
    return copy.deepcopy({
        "schema": SCHEMA, "program_text": packet["program_text"],
        "program_hash": packet["program_hash"], "cases": packet["cases"],
        "mandatory_case_ids": packet["mandatory_case_ids"], "regressions": packet["regressions"],
        "preexisting_discrepancies": packet["preexisting_discrepancies"],
        "measured_diff_hash": packet["candidate_diff_hash"], "current_diff_hash": current_diff,
        "observations_current": matched, "new_verification_required": not matched,
    })


def assess_rows(packet: dict, rows: list) -> dict:
    """Preserve all previously correct cases; do not require the known discrepancy."""
    current = {row["case"]: row for row in _rows(rows)}
    require(packet.get("schema") == SCHEMA, "unknown public counterexample packet")
    require(packet.get("mandatory_case_ids") == [
        name for name in CASE_IDS if name not in PREEXISTING_IDS
    ] and packet.get("regressions") == list(REGRESSION_IDS)
            and packet.get("preexisting_discrepancies") == list(PREEXISTING_IDS),
            "packet acceptance partition changed")
    cases = {case["case"]: case for case in packet["cases"]}
    require(set(cases) == set(CASE_IDS), "incomplete packet cases")
    for name, row in current.items():
        case = cases[name]
        require(all(row[field] == case[field] for field in INPUT_FIELDS),
                "verification case inputs changed")
        require(row["importlib_reference"] == case["importlib_reference"],
                "verification reference changed")

    def group(names):
        failed = [name for name in names
                  if current[name]["public_api"] != cases[name]["importlib_reference"]]
        return {"status": "FAIL" if failed else "PASS", "case_ids": list(names),
                "passed_case_ids": [name for name in names if name not in failed],
                "failed_case_ids": failed}

    preservation = group(packet["mandatory_case_ids"])
    regressions = group(packet["regressions"])
    preexisting = {**group(packet["preexisting_discrepancies"]), "mandatory": False}
    return {"status": preservation["status"], "regressions": regressions,
            "preservation": preservation, "preexisting": preexisting}
