import unittest

from mini_data_utils import parse_chunks


class ParseChunksTests(unittest.TestCase):
    def test_parses_terminated_records_across_chunks(self) -> None:
        self.assertEqual(
            parse_chunks(["name,age\n", "Ada,36\n"]),
            [["name", "age"], ["Ada", "36"]],
        )

    def test_preserves_a_record_split_across_chunks(self) -> None:
        self.assertEqual(
            parse_chunks(["name,age\nAda,", "36\n"]),
            [["name", "age"], ["Ada", "36"]],
        )

    def test_preserves_quoted_commas(self) -> None:
        self.assertEqual(
            parse_chunks(['name,note\nAda,"hello, world"\n']),
            [["name", "note"], ["Ada", "hello, world"]],
        )


if __name__ == "__main__":
    unittest.main()
