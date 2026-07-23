import unittest

from mini_data_utils import merge_config


class HiddenFalsyOverrideTests(unittest.TestCase):
    def test_applies_all_falsey_values(self) -> None:
        base = {
            "enabled": True,
            "retries": 3,
            "label": "default",
            "tags": ["stable"],
        }
        override = {
            "enabled": False,
            "retries": 0,
            "label": "",
            "tags": [],
        }
        self.assertEqual(merge_config(base, override), override)

    def test_preserves_new_empty_value(self) -> None:
        self.assertEqual(
            merge_config({"mode": "safe"}, {"note": ""}),
            {"mode": "safe", "note": ""},
        )


if __name__ == "__main__":
    unittest.main()
