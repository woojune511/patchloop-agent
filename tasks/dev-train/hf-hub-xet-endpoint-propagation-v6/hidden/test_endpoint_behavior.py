"""Operator-authored post-run behavior checks; no prescribed parser API."""

import unittest
from unittest.mock import patch

import http_fixture as fixture
from huggingface_hub import constants


class EndpointBehavior(unittest.TestCase):
    def test_public_entry_points_preserve_endpoint_ownership(self):
        suffix = "/api/models/public-fixture/repo/xet-read-token/main?mode=read#token"
        explicit = "https://isolated-mirror.example.test:9443/prefix/"
        routes = [
            ("https://huggingface.co" + suffix, True),
            ("HTTPS://HUGGINGFACE.CO:443" + suffix, True),
            (suffix, False),
            ("https://foreign.example.test" + suffix, False),
            ("https://huggingface.co:444" + suffix, False),
            ("http://huggingface.co" + suffix, False),
            ("https://huggingface.co.evil.test" + suffix, False),
            (explicit.rstrip("/") + suffix, False),
        ]
        entries = [
            "client-custom-url",
            "direct-no-endpoint",
            "download-cache",
            "download-local",
            "client-download-cache",
            "client-download-local",
        ]
        for carrier in ("header", "link"):
            for endpoint in (explicit, None):
                for entry in entries:
                    for route, owned in routes:
                        with self.subTest(
                            carrier=carrier, endpoint=endpoint, entry=entry, route=route
                        ):
                            supplied = endpoint is not None and entry != "direct-no-endpoint"
                            expected = (
                                explicit.rstrip("/") + suffix if supplied and owned else route
                            )
                            case = {
                                "id": "ownership",
                                "entry": entry,
                                "endpoint": endpoint,
                                "url": explicit.rstrip("/") + fixture.FILE_PATH,
                                "carrier": carrier,
                                "route": route,
                            }
                            with patch.object(
                                constants, "ENDPOINT", "https://ambient-only.example.test/root"
                            ):
                                row = fixture.observe([case])[0]
                            self.assertIsNone(row["error"])
                            self.assertEqual(row["route"], expected)
                            self.assertEqual(row["file_hash"], fixture.FILE_HASH)
                            self.assertEqual(row["transfer_count"], int("download-" in entry))
                            self.assertEqual(len(row["requests"]), 1)


if __name__ == "__main__":
    unittest.main()
