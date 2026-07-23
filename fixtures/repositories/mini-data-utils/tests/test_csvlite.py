import unittest

from mini_data_utils import parse_rows


class ParseRowsTests(unittest.TestCase):
    def test_parses_rows(self) -> None:
        self.assertEqual(parse_rows("name,age\nAda,36"), [["name", "age"], ["Ada", "36"]])

    def test_preserves_quoted_comma(self) -> None:
        self.assertEqual(parse_rows('name,note\nAda,"hello, world"'), [["name", "note"], ["Ada", "hello, world"]])


if __name__ == "__main__":
    unittest.main()

