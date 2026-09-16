from __future__ import annotations

import ast
import hashlib
import inspect
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from huggingface_hub import HfApi, constants, file_download
from huggingface_hub import hf_api as hf_api_module
from huggingface_hub.file_download import HfFileMetadata
from huggingface_hub.utils._xet import XetFileData, parse_xet_file_data_from_response

WORKSPACE = Path("/workspace")
SOURCE_ROOT = WORKSPACE / "src"


def response_with_route(route: str, *, link: bool = False) -> MagicMock:
    response = MagicMock()
    response.headers = {
        constants.HUGGINGFACE_HEADER_X_XET_HASH: "sha256:independent",
    }
    response.links = {}
    if link:
        response.links[constants.HUGGINGFACE_HEADER_LINK_XET_AUTH_KEY] = {"url": route}
    else:
        response.headers[constants.HUGGINGFACE_HEADER_X_XET_REFRESH_ROUTE] = route
    return response


def public_signature_map(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    signatures: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(
            "_"
        ):
            signatures[node.name] = ast.dump(node.args, include_attributes=False)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            signatures[node.name] = "class"
            for child in node.body:
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not child.name.startswith("_"):
                    signatures[f"{node.name}.{child.name}"] = ast.dump(
                        child.args, include_attributes=False
                    )
    return signatures


class XetEndpointPropagationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        imported = Path(inspect.getsourcefile(parse_xet_file_data_from_response) or "").resolve()
        cls.imported_source = imported

    def test_submitted_source_is_imported(self) -> None:
        self.assertTrue(
            self.imported_source.is_relative_to(SOURCE_ROOT),
            msg=f"production code was imported from {self.imported_source}, not {SOURCE_ROOT}",
        )

    def test_default_origin_header_is_rebased_and_slashes_are_normalized(self) -> None:
        response = response_with_route(
            "https://huggingface.co/api/models/acme/widget/xet-read-token/value"
        )

        data = parse_xet_file_data_from_response(
            response,
            endpoint="https://mirror.example/",
        )

        self.assertIsNotNone(data)
        assert data is not None
        self.assertEqual(
            data.refresh_route,
            "https://mirror.example/api/models/acme/widget/xet-read-token/value",
        )

    def test_relative_and_foreign_routes_are_preserved(self) -> None:
        for route in (
            "/api/models/acme/widget/xet-read-token/value",
            "https://storage.example/api/models/acme/widget/xet-read-token/value",
            "https://proxy.example/forward/https://huggingface.co/api/refresh",
        ):
            with self.subTest(route=route):
                data = parse_xet_file_data_from_response(
                    response_with_route(route),
                    endpoint="https://mirror.example",
                )
                self.assertIsNotNone(data)
                assert data is not None
                self.assertEqual(data.refresh_route, route)

    def test_link_route_and_default_endpoint_context_are_supported(self) -> None:
        response = response_with_route(
            "https://huggingface.co/api/models/other/repo/xet-read-token/value",
            link=True,
        )
        with patch.object(constants, "ENDPOINT", "https://configured.example"):
            data = parse_xet_file_data_from_response(response)

        self.assertIsNotNone(data)
        assert data is not None
        self.assertEqual(
            data.refresh_route,
            "https://configured.example/api/models/other/repo/xet-read-token/value",
        )

    def test_low_level_metadata_path_passes_endpoint_to_xet_parser(self) -> None:
        response = response_with_route(
            "https://huggingface.co/api/models/acme/widget/xet-read-token/value"
        )
        response.headers.update(
            {
                constants.HUGGINGFACE_HEADER_X_REPO_COMMIT: "commit-abc",
                constants.HUGGINGFACE_HEADER_X_LINKED_ETAG: '"etag-abc"',
                constants.HUGGINGFACE_HEADER_X_LINKED_SIZE: "7",
            }
        )
        response.request.url = "https://mirror.example/acme/widget/resolve/main/file.bin"

        with (
            patch.object(file_download, "_request_wrapper", return_value=response),
            patch.object(file_download, "hf_raise_for_status"),
        ):
            metadata = file_download.get_hf_file_metadata(
                url=response.request.url,
                token=False,
                endpoint="https://mirror.example",
            )

        self.assertIsNotNone(metadata.xet_file_data)
        assert metadata.xet_file_data is not None
        self.assertEqual(
            metadata.xet_file_data.refresh_route,
            "https://mirror.example/api/models/acme/widget/xet-read-token/value",
        )

    def test_internal_download_metadata_path_forwards_endpoint(self) -> None:
        endpoint = "https://download.example"
        metadata = HfFileMetadata(
            commit_hash="commit-xyz",
            etag='"etag-xyz"',
            location=f"{endpoint}/org/repo/resolve/main/file.bin",
            size=11,
            xet_file_data=XetFileData(
                file_hash="sha256:file",
                refresh_route=f"{endpoint}/api/models/org/repo/xet-read-token/value",
            ),
        )
        with patch.object(
            file_download,
            "get_hf_file_metadata",
            return_value=metadata,
        ) as metadata_call:
            result = file_download._get_metadata_or_catch_error(
                repo_id="org/repo",
                filename="file.bin",
                repo_type="model",
                revision="main",
                endpoint=endpoint,
                proxies=None,
                etag_timeout=5,
                headers={},
                token=False,
                local_files_only=False,
            )

        self.assertEqual(metadata_call.call_args.kwargs["endpoint"], endpoint)
        self.assertIs(result[4], metadata.xet_file_data)
        self.assertIsNone(result[5])

    def test_hf_api_wrapper_forwards_instance_endpoint(self) -> None:
        endpoint = "https://api-wrapper.example"
        sentinel = object()
        with patch.object(
            hf_api_module,
            "get_hf_file_metadata",
            return_value=sentinel,
        ) as metadata_call:
            result = HfApi(endpoint=endpoint, token=False).get_hf_file_metadata(
                url=f"{endpoint}/org/repo/resolve/main/file.bin",
                token=False,
            )

        self.assertIs(result, sentinel)
        self.assertEqual(metadata_call.call_args.kwargs["endpoint"], endpoint)

    def test_public_signature_delta_is_exactly_scoped(self) -> None:
        expected_digests = {
            "src/huggingface_hub/file_download.py": (
                "9d2a2cb5fef198152aeda48b0fdd3f3012b624f461dd6da41ac4cc40fb695750"
            ),
            "src/huggingface_hub/hf_api.py": (
                "f277c23bc587e5e22b6b1d3d34475d7c93d7b2b0d4f75e30b41cf29abd3d5c3d"
            ),
            "src/huggingface_hub/utils/_xet.py": (
                "1139fb04e3faf750e43227409037da030b976a799ce288394fee152085d2e839"
            ),
        }
        for relative_path, expected in expected_digests.items():
            with self.subTest(path=relative_path):
                current = (WORKSPACE / relative_path).read_text(encoding="utf-8")
                signature_payload = json.dumps(
                    public_signature_map(current),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                actual = hashlib.sha256(signature_payload).hexdigest()
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
