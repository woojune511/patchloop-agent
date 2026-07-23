import unittest

from mini_data_utils import parse_chunks


class HiddenFinalRecordTests(unittest.TestCase):
    def test_flushes_final_record_without_newline(self) -> None:
        self.assertEqual(
            parse_chunks(["name,age\nAda,36"]),
            [["name", "age"], ["Ada", "36"]],
        )

    def test_flushes_final_record_assembled_from_multiple_chunks(self) -> None:
        self.assertEqual(
            parse_chunks(["name,age\nAda,", "36"]),
            [["name", "age"], ["Ada", "36"]],
        )

    def test_flushes_a_single_quoted_record(self) -> None:
        self.assertEqual(
            parse_chunks(['Ada,"hello, world"']),
            [["Ada", "hello, world"]],
        )


if __name__ == "__main__":
    unittest.main()
