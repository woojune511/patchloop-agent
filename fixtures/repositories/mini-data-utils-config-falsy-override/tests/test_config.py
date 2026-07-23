import unittest

from mini_data_utils import merge_config


class MergeConfigTests(unittest.TestCase):
    def test_replaces_existing_value(self) -> None:
        self.assertEqual(
            merge_config({"mode": "safe"}, {"mode": "fast"}),
            {"mode": "fast"},
        )

    def test_preserves_unmentioned_values(self) -> None:
        self.assertEqual(
            merge_config({"mode": "safe", "retries": 3}, {"mode": "fast"}),
            {"mode": "fast", "retries": 3},
        )

    def test_adds_new_value(self) -> None:
        self.assertEqual(
            merge_config({"mode": "safe"}, {"region": "eu-west"}),
            {"mode": "safe", "region": "eu-west"},
        )


if __name__ == "__main__":
    unittest.main()
