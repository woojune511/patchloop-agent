import unittest

from mini_data_utils import is_path_within


class PathMatchTests(unittest.TestCase):
    def test_accepts_direct_child(self) -> None:
        self.assertTrue(is_path_within("src/app/main.py", "src/app"))

    def test_accepts_nested_windows_separator(self) -> None:
        self.assertTrue(is_path_within(r"src\app\core\config.py", "src/app"))

    def test_rejects_unrelated_root(self) -> None:
        self.assertFalse(is_path_within("docs/readme.md", "src/app"))


if __name__ == "__main__":
    unittest.main()
