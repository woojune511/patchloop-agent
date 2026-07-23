import unittest

from mini_data_utils import is_path_within


class HiddenPathBoundaryTests(unittest.TestCase):
    def test_rejects_sibling_with_shared_prefix(self) -> None:
        self.assertFalse(is_path_within("src/application/config.py", "src/app"))
        self.assertFalse(is_path_within("src/app2/config.py", "src/app"))

    def test_normalizes_parent_segments_before_comparison(self) -> None:
        self.assertFalse(
            is_path_within("src/app/../application/config.py", "src/app")
        )

    def test_accepts_exact_root_with_trailing_separator(self) -> None:
        self.assertTrue(is_path_within("src/app", "src/app/"))


if __name__ == "__main__":
    unittest.main()
