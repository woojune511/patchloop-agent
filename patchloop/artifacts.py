"""Content-addressed artifact storage."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from patchloop.contracts import Artifact
from patchloop.errors import RecoveryError
from patchloop.util import sha256_bytes, utc_now


class ArtifactStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.objects = self.root / "objects" / "sha256"
        self.objects.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, content: bytes, media_type: str = "application/octet-stream") -> Artifact:
        digest = sha256_bytes(content)
        hex_digest = digest.split(":", 1)[1]
        path = self.objects / hex_digest[:2] / hex_digest[2:]
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                existing = path.read_bytes()
            except OSError as exc:
                raise RecoveryError(f"content-addressed artifact is unreadable: {digest}") from exc
            if sha256_bytes(existing) != digest:
                raise RecoveryError(f"content-addressed artifact failed integrity check: {digest}")
        else:
            temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("xb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        return Artifact(
            artifact_id=f"art_{uuid.uuid4().hex}",
            content_hash=digest,
            media_type=media_type,
            size_bytes=len(content),
            path=str(path),
            created_at=utc_now(),
        )

    def put_text(self, content: str, media_type: str = "text/plain") -> Artifact:
        return self.put_bytes(content.encode("utf-8"), media_type=f"{media_type}; charset=utf-8")

    def put_json(self, value: Any) -> Artifact:
        content = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
        return self.put_text(content, media_type="application/json")

    def read_bytes(self, artifact: Artifact) -> bytes:
        hex_digest = artifact.content_hash.removeprefix("sha256:")
        if len(hex_digest) != 64:
            raise RecoveryError(f"artifact has an invalid content identity: {artifact.artifact_id}")
        expected_path = (self.objects / hex_digest[:2] / hex_digest[2:]).resolve()
        try:
            actual_path = Path(artifact.path).resolve()
        except OSError as exc:
            raise RecoveryError(
                f"artifact path cannot be resolved: {artifact.artifact_id}"
            ) from exc
        if actual_path != expected_path:
            raise RecoveryError(
                f"artifact path does not match its content identity: {artifact.artifact_id}"
            )
        try:
            content = actual_path.read_bytes()
        except OSError as exc:
            raise RecoveryError(f"artifact is unavailable: {artifact.artifact_id}") from exc
        if len(content) != artifact.size_bytes or sha256_bytes(content) != artifact.content_hash:
            raise RecoveryError(f"artifact failed integrity verification: {artifact.artifact_id}")
        return content

    def write_bytes_atomic(
        self,
        path: str | Path,
        content: bytes,
    ) -> None:
        """Atomically replace one derived file below the artifact root."""

        target = Path(path)
        try:
            root = self.root.resolve()
            resolved = target.resolve()
        except OSError as exc:
            raise RecoveryError("derived artifact path cannot be resolved") from exc
        if not resolved.is_relative_to(root) or target.is_symlink():
            raise RecoveryError("derived artifact path escapes the artifact root")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def write_text_atomic(
        self,
        path: str | Path,
        content: str,
    ) -> None:
        self.write_bytes_atomic(path, content.encode("utf-8"))

    def write_text_immutable(
        self,
        path: str | Path,
        content: str,
    ) -> None:
        target = Path(path)
        encoded = content.encode("utf-8")
        if target.exists():
            if target.is_symlink():
                raise RecoveryError("immutable artifact path is a symlink")
            try:
                existing = target.read_bytes()
            except OSError as exc:
                raise RecoveryError("immutable artifact is unreadable") from exc
            if existing != encoded:
                raise RecoveryError("immutable artifact conflicts with durable content")
            return
        self.write_bytes_atomic(target, encoded)
