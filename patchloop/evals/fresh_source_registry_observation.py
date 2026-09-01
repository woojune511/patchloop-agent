"""Append-only metadata-only Harbor registry observation for fresh acquisition.

The captured requests resolve the official Harbor client source and query only
public package/version metadata.  They never request dataset-task membership,
task archives, files, solution material, or private data.  This observation
narrows the v3 browser ambiguity; it is not raw-source completeness evidence
and cannot be consumed as a candidate registry or execution authority.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-harness-fresh-source-registry-observation-v1"
OBSERVATION_ID = "lean-harness-fresh-source-registry-observation-20260818-v1"
STATUS = "OFFICIAL_METADATA_OBSERVED_NO_QUALIFYING_SNAPSHOT"
OUTPUT_PATH = "experiments/lean-harness-fresh-source-registry-observation-20260818-v1.json"

PREDECESSOR_PATH = "experiments/lean-harness-fresh-source-availability-20260818-v3.json"
PREDECESSOR_BYTES = 5_117
PREDECESSOR_FILE_SHA256 = "sha256:e7cb73fa16059c72a6aee072ee2e7d661dcc1287abeeb53ba034d5378dbc599b"
PREDECESSOR_CONTENT_HASH = "sha256:2b84e6271fa11ebb4285c5a0fde5b6b66af407503e2ef219bc2db63cab174f15"

HARBOR_REPOSITORY = "https://github.com/harbor-framework/harbor"
HARBOR_HEAD = "f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e"
REGISTRY_ORIGIN = "https://ofhuhcpkvzjlejydnvyd.supabase.co"
OBSERVED_STARTED_AT = "2026-08-17T18:49:28.1777599Z"
OBSERVED_FINISHED_AT = "2026-08-17T18:49:29.7228882Z"


class FreshSourceRegistryObservationError(ContractError):
    """The Harbor metadata observation is invalid or has drifted."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FileBinding(FrozenModel):
    path: Literal[PREDECESSOR_PATH]
    file_bytes: Literal[PREDECESSOR_BYTES]
    file_sha256: Literal[PREDECESSOR_FILE_SHA256]
    content_hash: Literal[PREDECESSOR_CONTENT_HASH]
    role: Literal["browser-availability-v3-predecessor"]


class OfficialClientSource(FrozenModel):
    repository: Literal[HARBOR_REPOSITORY]
    head_commit: Literal[HARBOR_HEAD]
    head_committed_at: Literal["2026-08-16T14:25:07Z"]
    commit_response_bytes: Literal[23_397]
    commit_response_sha256: Literal[
        "sha256:789fa9fd63a95ea9c51f2d3ea82aa0337d33af820f195a5a7107639fcbbd3a90"
    ]
    auth_constants_url: Literal[
        "https://raw.githubusercontent.com/harbor-framework/harbor/f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e/src/harbor/auth/constants.py"
    ]
    auth_constants_bytes: Literal[2_034]
    auth_constants_sha256: Literal[
        "sha256:90cfcf350ecf396d9d6c6166faa6f54c9de4348deef6b6240440fdb942f71dd3"
    ]
    db_client_url: Literal[
        "https://raw.githubusercontent.com/harbor-framework/harbor/f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e/src/harbor/db/client.py"
    ]
    db_client_bytes: Literal[26_275]
    db_client_sha256: Literal[
        "sha256:8c5445f47f114ccc175d06aaa733a156a1712c6dcf4ddf3e233d8ae0813fa747"
    ]
    registry_origin: Literal[REGISTRY_ORIGIN]
    public_publishable_key_persisted: Literal[False]


class PackageRow(FrozenModel):
    id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    org: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str = Field(pattern=r"^[a-z0-9-]+$")
    type: Literal["dataset"]
    visibility: Literal["public"]


class VersionRow(FrozenModel):
    id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    package: Literal[
        "swe-rebench/swe-rebench-leaderboard",
        "ibragim-badertdinov/swe-rebench-07-2026",
    ]
    revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    published_at: str
    yanked: Literal[False]
    tags: tuple[str, ...]

    @field_validator("revision", mode="before")
    @classmethod
    def require_exact_revision(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("revision must be a JSON integer")
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def freeze_tags(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value


class MetadataQuery(FrozenModel):
    id: Literal[
        "swe-rebench-package-name-scan",
        "exact-august-monthly-package",
        "visible-source-package-versions",
    ]
    method: Literal["GET"]
    path: Literal["/rest/v1/package", "/rest/v1/dataset_version"]
    canonical_query: str
    status: Literal[200]
    response_bytes: int = Field(ge=2)
    response_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    row_count: int = Field(ge=0)
    returned_less_than_server_page_limit: Literal[True]
    exact_count_header_observed: Literal[False]

    @model_validator(mode="before")
    @classmethod
    def require_exact_counts(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in ("status", "response_bytes", "row_count"):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        return value


class ObservedRows(FrozenModel):
    packages: tuple[PackageRow, ...]
    exact_august_packages: tuple[PackageRow, ...]
    versions: tuple[VersionRow, ...]

    @field_validator("packages", "exact_august_packages", "versions", mode="before")
    @classmethod
    def freeze_rows(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_rows(self) -> Self:
        if len(self.packages) != 4 or self.exact_august_packages or len(self.versions) != 3:
            raise ValueError("observed Harbor row counts differ")
        source_names = {(row.org, row.name) for row in self.packages}
        if (
            ("ibragim-badertdinov", "swe-rebench-07-2026") not in source_names
            or ("swe-rebench", "swe-rebench-leaderboard") not in source_names
            or ("ibragim-badertdinov", "swe-rebench-08-2026") in source_names
        ):
            raise ValueError("observed Harbor package set differs")
        return self


class ObservationDecision(FrozenModel):
    harbor_current_status_established: Literal[True]
    exact_august_monthly_package_visible: Literal[False]
    latest_visible_monthly_source: Literal["ibragim-badertdinov/swe-rebench-07-2026@revision-1"]
    qualifying_post_window_snapshot_observed: Literal[False]
    qualifying_snapshot_absence_proven: Literal[False]
    absence_scope: Literal["public-harbor-package-registry-at-observation-time-only"]
    raw_source_completeness_qualified: Literal[False]
    observation_is_selector_input: Literal[False]
    future_snapshot_availability_ruled_out: Literal[False]


class Authority(FrozenModel):
    scope: Literal["final-capture-transcript-only-not-exploratory-turn-total"]
    official_source_identity_gets: Literal[3]
    public_registry_metadata_gets: Literal[3]
    total_recorded_network_gets: Literal[6]
    dataset_task_membership_requests: Literal[0]
    task_archive_or_file_requests: Literal[0]
    task_rows_downloaded: Literal[0]
    solution_test_oracle_private_fields_read: Literal[0]
    credentials_or_personal_api_keys_read: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    raw_source_qualification_executed: Literal[False]
    candidate_registry_materialized: Literal[False]
    fresh_task_panel_materialized: Literal[False]
    candidate_created: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_effect_claim_authorized: Literal[False]


class FreshSourceRegistryObservation(FrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    observation_id: Literal[OBSERVATION_ID]
    status: Literal[STATUS]
    observed_started_at: Literal[OBSERVED_STARTED_AT]
    observed_finished_at: Literal[OBSERVED_FINISHED_AT]
    predecessor_binding: FileBinding
    official_client_source: OfficialClientSource
    queries: tuple[MetadataQuery, ...]
    observed_rows: ObservedRows
    decision: ObservationDecision
    authority: Authority
    next_gate: Literal[
        "wait-for-the-earliest-qualifying-snapshot-then-capture-raw-bytes-and-qualify-its-source-specific-adapter-before-selector-use"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("queries", mode="before")
    @classmethod
    def freeze_queries(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if tuple(query.id for query in self.queries) != (
            "swe-rebench-package-name-scan",
            "exact-august-monthly-package",
            "visible-source-package-versions",
        ):
            raise ValueError("Harbor metadata query order differs")
        if tuple(query.row_count for query in self.queries) != (4, 0, 3):
            raise ValueError("Harbor metadata query counts differ")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("fresh-source registry observation content hash differs")
        return self


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FreshSourceRegistryObservationError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshSourceRegistryObservationError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise FreshSourceRegistryObservationError(f"{label} must be an object")
    return value


def _predecessor() -> FileBinding:
    return FileBinding(
        path=PREDECESSOR_PATH,
        file_bytes=PREDECESSOR_BYTES,
        file_sha256=PREDECESSOR_FILE_SHA256,
        content_hash=PREDECESSOR_CONTENT_HASH,
        role="browser-availability-v3-predecessor",
    )


def _source() -> OfficialClientSource:
    return OfficialClientSource(
        repository=HARBOR_REPOSITORY,
        head_commit=HARBOR_HEAD,
        head_committed_at="2026-08-16T14:25:07Z",
        commit_response_bytes=23_397,
        commit_response_sha256="sha256:789fa9fd63a95ea9c51f2d3ea82aa0337d33af820f195a5a7107639fcbbd3a90",
        auth_constants_url=f"https://raw.githubusercontent.com/harbor-framework/harbor/{HARBOR_HEAD}/src/harbor/auth/constants.py",
        auth_constants_bytes=2_034,
        auth_constants_sha256="sha256:90cfcf350ecf396d9d6c6166faa6f54c9de4348deef6b6240440fdb942f71dd3",
        db_client_url=f"https://raw.githubusercontent.com/harbor-framework/harbor/{HARBOR_HEAD}/src/harbor/db/client.py",
        db_client_bytes=26_275,
        db_client_sha256="sha256:8c5445f47f114ccc175d06aaa733a156a1712c6dcf4ddf3e233d8ae0813fa747",
        registry_origin=REGISTRY_ORIGIN,
        public_publishable_key_persisted=False,
    )


def _queries() -> tuple[MetadataQuery, ...]:
    return (
        MetadataQuery(
            id="swe-rebench-package-name-scan",
            method="GET",
            path="/rest/v1/package",
            canonical_query="select=id,name,type,visibility,org:org_id!inner(name)&type=eq.dataset&name=ilike.*swe-rebench*&order=name.asc",
            status=200,
            response_bytes=637,
            response_sha256="sha256:9f5c4884750600d567c32d69a948621bf9f4aae7313386a96376482c285f5ba6",
            row_count=4,
            returned_less_than_server_page_limit=True,
            exact_count_header_observed=False,
        ),
        MetadataQuery(
            id="exact-august-monthly-package",
            method="GET",
            path="/rest/v1/package",
            canonical_query="select=id,name,type,visibility,org:org_id!inner(name)&type=eq.dataset&name=eq.swe-rebench-08-2026&org.name=eq.ibragim-badertdinov",
            status=200,
            response_bytes=2,
            response_sha256="sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
            row_count=0,
            returned_less_than_server_page_limit=True,
            exact_count_header_observed=False,
        ),
        MetadataQuery(
            id="visible-source-package-versions",
            method="GET",
            path="/rest/v1/dataset_version",
            canonical_query="select=id,package_id,revision,content_hash,published_at,yanked_at,tags:dataset_version_tag(tag)&package_id=in.(<two-observed-source-package-ids>)&order=published_at.asc",
            status=200,
            response_bytes=871,
            response_sha256="sha256:3a6998b6a1880d19e5186fd8610641bbabcbcf72233c474098b4b9ccb90cde85",
            row_count=3,
            returned_less_than_server_page_limit=True,
            exact_count_header_observed=False,
        ),
    )


def _rows() -> ObservedRows:
    packages = (
        PackageRow(
            id="71e13c51-0761-493b-9d62-c90f98ea770c",
            org="ibragim-badertdinov",
            name="swe-rebench-07-2026",
            type="dataset",
            visibility="public",
        ),
        PackageRow(
            id="2454eaf3-5205-4cfe-a989-108a3edc17d5",
            org="swe-rebench",
            name="swe-rebench-leaderboard",
            type="dataset",
            visibility="public",
        ),
        PackageRow(
            id="b9143293-78f0-4950-9e14-78d63d8235e4",
            org="openthoughts",
            name="tasktrove-swe-rebench-patched-oracle",
            type="dataset",
            visibility="public",
        ),
        PackageRow(
            id="8f0a1b82-814e-459e-bdff-f9273bfb290a",
            org="openthoughts",
            name="tasktrove-swe-rebench-v2-patched-oracle",
            type="dataset",
            visibility="public",
        ),
    )
    versions = (
        VersionRow(
            id="2d6bca54-b245-452c-af2d-bc021a737225",
            package="swe-rebench/swe-rebench-leaderboard",
            revision=1,
            content_hash="sha256:c90d7716b4ab56bd545dd31af46a808ff3ce44c0537fba041524c5dad353a159",
            published_at="2026-06-25T20:30:39.658965+09:00",
            yanked=False,
            tags=(),
        ),
        VersionRow(
            id="b5a1b010-d34b-43e9-b08a-a23e4169a327",
            package="swe-rebench/swe-rebench-leaderboard",
            revision=2,
            content_hash="sha256:ebe7444e313a0d8db94fa541139826eaebe2b0abcd4900c6f73e750494910dca",
            published_at="2026-06-26T03:52:28.245788+09:00",
            yanked=False,
            tags=("latest",),
        ),
        VersionRow(
            id="574acb72-70aa-46fb-8758-0a814a5eb213",
            package="ibragim-badertdinov/swe-rebench-07-2026",
            revision=1,
            content_hash="sha256:e2e357045bf03e4900d2506c36562f6eaff7acd37f63780600967ea3aecdcd79",
            published_at="2026-07-27T01:08:18.172829+09:00",
            yanked=False,
            tags=("2026-07", "latest"),
        ),
    )
    return ObservedRows(packages=packages, exact_august_packages=(), versions=versions)


def _decision() -> ObservationDecision:
    return ObservationDecision(
        harbor_current_status_established=True,
        exact_august_monthly_package_visible=False,
        latest_visible_monthly_source="ibragim-badertdinov/swe-rebench-07-2026@revision-1",
        qualifying_post_window_snapshot_observed=False,
        qualifying_snapshot_absence_proven=False,
        absence_scope="public-harbor-package-registry-at-observation-time-only",
        raw_source_completeness_qualified=False,
        observation_is_selector_input=False,
        future_snapshot_availability_ruled_out=False,
    )


def _authority() -> Authority:
    return Authority(
        scope="final-capture-transcript-only-not-exploratory-turn-total",
        official_source_identity_gets=3,
        public_registry_metadata_gets=3,
        total_recorded_network_gets=6,
        dataset_task_membership_requests=0,
        task_archive_or_file_requests=0,
        task_rows_downloaded=0,
        solution_test_oracle_private_fields_read=0,
        credentials_or_personal_api_keys_read=0,
        docker_calls=0,
        provider_calls=0,
        evaluator_calls=0,
        agent_runs=0,
        added_model_cost_usd=0,
        raw_source_qualification_executed=False,
        candidate_registry_materialized=False,
        fresh_task_panel_materialized=False,
        candidate_created=False,
        approval_granted=False,
        execution_authorized=False,
        official_analysis_authorized=False,
        memory_effect_claim_authorized=False,
    )


def _read_predecessor(root: Path) -> bytes:
    selected = ensure_within(root, PREDECESSOR_PATH)
    raw = selected.read_bytes()
    parsed = _json_object(raw, label="fresh-source availability v3 predecessor")
    if not (
        len(raw) == PREDECESSOR_BYTES
        and sha256_bytes(raw) == PREDECESSOR_FILE_SHA256
        and parsed.get("content_hash") == PREDECESSOR_CONTENT_HASH
    ):
        raise FreshSourceRegistryObservationError(
            "fresh-source availability v3 predecessor differs"
        )
    return raw


def build_fresh_source_registry_observation(
    repository: str | Path = ".",
) -> FreshSourceRegistryObservation:
    root = Path(repository).resolve()
    _read_predecessor(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "observation_id": OBSERVATION_ID,
        "status": STATUS,
        "observed_started_at": OBSERVED_STARTED_AT,
        "observed_finished_at": OBSERVED_FINISHED_AT,
        "predecessor_binding": _predecessor(),
        "official_client_source": _source(),
        "queries": _queries(),
        "observed_rows": _rows(),
        "decision": _decision(),
        "authority": _authority(),
        "next_gate": (
            "wait-for-the-earliest-qualifying-snapshot-then-capture-raw-bytes-and-"
            "qualify-its-source-specific-adapter-before-selector-use"
        ),
    }
    hashed = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    hashed["queries"] = [query.model_dump(mode="json") for query in body["queries"]]
    return FreshSourceRegistryObservation(**body, content_hash=sha256_json(hashed))


def observation_bytes(value: FreshSourceRegistryObservation) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _validate_frozen(value: FreshSourceRegistryObservation) -> None:
    if not (
        value.predecessor_binding == _predecessor()
        and value.official_client_source == _source()
        and value.queries == _queries()
        and value.observed_rows == _rows()
        and value.decision == _decision()
        and value.authority == _authority()
    ):
        raise FreshSourceRegistryObservationError("Harbor registry observation facts differ")


def load_fresh_source_registry_observation(
    repository: str | Path = ".", path: str = OUTPUT_PATH
) -> FreshSourceRegistryObservation:
    root = Path(repository).resolve()
    selected = ensure_within(root, path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshSourceRegistryObservationError(
            "Harbor registry observation is unavailable"
        ) from exc
    _json_object(raw, label="Harbor registry observation")
    try:
        value = FreshSourceRegistryObservation.model_validate_json(raw)
    except ValueError as exc:
        raise FreshSourceRegistryObservationError(
            "Harbor registry observation contract is invalid"
        ) from exc
    if observation_bytes(value) != raw:
        raise FreshSourceRegistryObservationError(
            "Harbor registry observation bytes are not canonical"
        )
    _read_predecessor(root)
    _validate_frozen(value)
    return value


def materialize_fresh_source_registry_observation(
    repository: str | Path = ".", path: str = OUTPUT_PATH
) -> FreshSourceRegistryObservation:
    root = Path(repository).resolve()
    selected = ensure_within(root, path)
    if selected.exists():
        return load_fresh_source_registry_observation(root, path)
    value = build_fresh_source_registry_observation(root)
    raw = observation_bytes(value)
    selected.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(selected, flags, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return load_fresh_source_registry_observation(root, path)
