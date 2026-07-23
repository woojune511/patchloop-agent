import unittest

from mini_data_utils import format_elapsed


class HiddenMinuteBoundaryTests(unittest.TestCase):
    def test_uses_only_fully_completed_minutes(self) -> None:
        cases = {
            90: "1m",
            119: "1m",
            150: "2m",
            179: "2m",
            3599: "59m",
        }
        for seconds, expected in cases.items():
            with self.subTest(seconds=seconds):
                self.assertEqual(format_elapsed(seconds), expected)

    def test_keeps_the_first_second_of_each_bucket(self) -> None:
        self.assertEqual(format_elapsed(61), "1m")
        self.assertEqual(format_elapsed(121), "2m")


if __name__ == "__main__":
    unittest.main()
