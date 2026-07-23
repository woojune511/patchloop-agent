import unittest

from mini_data_utils import parse_rows


class HiddenMultilineCsvTests(unittest.TestCase):
    def test_preserves_newline_inside_quoted_field(self) -> None:
        text = 'id,note\n1,"first line\nsecond line"\n2,done'
        self.assertEqual(
            parse_rows(text),
            [["id", "note"], ["1", "first line\nsecond line"], ["2", "done"]],
        )

    def test_handles_crlf_after_multiline_record(self) -> None:
        text = 'id,note\r\n1,"a\r\nb"\r\n'
        self.assertEqual(parse_rows(text), [["id", "note"], ["1", "a\r\nb"]])


if __name__ == "__main__":
    unittest.main()

