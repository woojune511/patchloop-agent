"""Content-addressed artifact storage."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from patchloop.contracts import Artifact
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
        if not path.exists():
            path.write_bytes(content)
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
