"""Public endpoint ownership through existing metadata and download APIs."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

DEFAULT = "https://huggingface.co"
CUSTOM = "https://mirror.example.test:8443"
FILE_PATH = "/public-fixture/repo/resolve/main/config.json"
REFRESH_PATH = "/api/models/public-fixture/repo/xet-read-token/main?aud=read#refresh"
FILE_HASH = "public-fixture-xet-hash"
REQUEST = CUSTOM + "/hub"
AMBIENT = "https://ambient.example.test:9443/global"
ENVIRONMENTS = {"same": REQUEST, "other": AMBIENT}


def observe(selected_cases):
    import requests
    from huggingface_hub import constants, file_download, hf_api
    from huggingface_hub.utils import _xet

    for module, relative in (
        (file_download, "file_download.py"),
        (hf_api, "hf_api.py"),
        (_xet, "utils/_xet.py"),
    ):
        assert Path(module.__file__).resolve() == Path("/workspace/src/huggingface_hub") / relative

    def no_network(*args, **kwargs):
        raise AssertionError("Unexpected HTTP request outside the controlled HEAD response")

    def observe_case(case):
        requested, transfers = ([], [])

        def head_response(*args, **kwargs):
            assert kwargs["method"] == "HEAD"
            requested.append(kwargs["url"])
            response = requests.Response()
            response.status_code = 200
            response.url = kwargs["url"]
            response.request = requests.Request("HEAD", kwargs["url"]).prepare()
            response.headers.update(
                {
                    "X-Repo-Commit": "a" * 40,
                    "ETag": '"fixture-etag"',
                    "Content-Length": "0",
                    "X-Xet-Hash": FILE_HASH,
                }
            )
            if case["carrier"] == "header":
                response.headers["X-Xet-Refresh-Route"] = case["route"]
            else:
                response.headers["Link"] = f'''<{case["route"]}>; rel="xet-auth"'''
            return response

        def capture_transfer(**kwargs):
            transfers.append(kwargs["xet_file_data"])
            Path(kwargs["destination_path"]).write_bytes(b"")

        row = dict(
            id=case["id"],
            route=None,
            file_hash=None,
            requests=requested,
            transfer_count=0,
            error=None,
        )
        if "environment" in case:
            row.update(
                environment=constants.ENDPOINT, default_origin=constants._HF_DEFAULT_ENDPOINT
            )
        try:
            with (
                patch.object(requests.sessions.Session, "request", no_network),
                patch.object(file_download, "_request_wrapper", head_response),
                patch.object(file_download, "_download_to_tmp_and_move", capture_transfer),
                TemporaryDirectory(prefix="public-xet-") as temporary,
            ):
                entry = case["entry"]
                endpoint = case.get("endpoint", CUSTOM)
                if entry == "direct-no-endpoint":
                    data = file_download.get_hf_file_metadata(
                        case["url"], token=False
                    ).xet_file_data
                elif "download-" in entry:
                    is_client = entry.startswith("client-")
                    client = hf_api.HfApi(endpoint=endpoint, token=False)
                    download = (
                        client.hf_hub_download if is_client else file_download.hf_hub_download
                    )
                    context = {} if is_client else {"endpoint": endpoint}
                    destination = (
                        {"local_dir": Path(temporary) / "local"} if entry.endswith("local") else {}
                    )
                    result = download(
                        "public-fixture/repo",
                        "config.json",
                        token=False,
                        cache_dir=Path(temporary) / "cache",
                        force_download=True,
                        **context,
                        **destination,
                    )
                    assert Path(result).is_file() and len(transfers) == 1
                    data = transfers[0]
                else:
                    client = hf_api.HfApi(endpoint=endpoint, token=False)
                    data = client.get_hf_file_metadata(url=case["url"]).xet_file_data
                row.update(route=data.refresh_route, file_hash=data.file_hash)
        except Exception as error:
            row["error"] = f"{type(error).__name__}: {str(error)[:180]}"
        row["transfer_count"] = len(transfers)
        return row

    return [observe_case(case) for case in selected_cases]
