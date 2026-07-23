import unittest

from mini_data_utils import format_elapsed


class FormatElapsedTests(unittest.TestCase):
    def test_preserves_subminute_seconds(self) -> None:
        self.assertEqual(format_elapsed(0), "0s")
        self.assertEqual(format_elapsed(59), "59s")

    def test_formats_exact_minute_boundaries(self) -> None:
        self.assertEqual(format_elapsed(60), "1m")
        self.assertEqual(format_elapsed(120), "2m")

    def test_rejects_negative_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            format_elapsed(-1)


if __name__ == "__main__":
    unittest.main()
