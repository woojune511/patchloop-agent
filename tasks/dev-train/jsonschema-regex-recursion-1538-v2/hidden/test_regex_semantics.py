"""Private behavioral checks; never included in the coding-agent context."""

import re
import sys
import unittest
from unittest.mock import patch

try:
    import jsonschema
    from jsonschema import FormatChecker
    from jsonschema.exceptions import FormatError, ValidationError

    if not jsonschema.__file__.startswith("/workspace/"):
        raise RuntimeError("workspace import required")
except Exception:
    import traceback

    traceback.print_exc()
    sys.exit(2)


class RegexSemantics(unittest.TestCase):
    def test_deep_patterns_across_drafts(self):
        old_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(300)
            patterns = ["(" * 900, "(" * 900 + "a" + ")" * 900]
            for cls in (jsonschema.Draft3Validator, jsonschema.Draft4Validator,
                        jsonschema.Draft6Validator, jsonschema.Draft7Validator,
                        jsonschema.Draft201909Validator, jsonschema.Draft202012Validator):
                validator = cls({"format": "regex"}, format_checker=cls.FORMAT_CHECKER)
                for pattern in patterns:
                    with self.subTest(draft=cls.__name__, balanced=pattern.endswith(")")):
                        errors = list(validator.iter_errors(pattern))
                        self.assertEqual(len(errors), 1)
                        self.assertEqual(errors[0].validator, "format")
                        self.assertIsInstance(errors[0].cause, RecursionError)
                        self.assertFalse(validator.is_valid(pattern))
                        with self.assertRaises(ValidationError):
                            validator.validate(pattern)
        finally:
            sys.setrecursionlimit(old_limit)

    def test_direct_checker_preserves_recursion_cause(self):
        checker = FormatChecker(formats=["regex"])
        error = RecursionError("private recursion sentinel")
        with patch("jsonschema._format.re.compile", side_effect=error):
            with self.assertRaises(FormatError) as raised:
                checker.check("abc", "regex")
            self.assertIs(raised.exception.cause, error)
            self.assertFalse(checker.conforms("abc", "regex"))

    def test_valid_regex_controls(self):
        checker = FormatChecker(formats=["regex"])
        for pattern in ("", r"(?:ab|cd)+", r"[\w.-]+", r"(?P<word>ab)(?P=word)"):
            with self.subTest(pattern=pattern):
                checker.check(pattern, "regex")
                self.assertTrue(checker.conforms(pattern, "regex"))

    def test_syntax_error_cause_is_preserved(self):
        checker = FormatChecker(formats=["regex"])
        for pattern in ("*abc", "(?P<>", "[z-a]"):
            with self.subTest(pattern=pattern):
                with self.assertRaises(FormatError) as raised:
                    checker.check(pattern, "regex")
                self.assertIsInstance(raised.exception.cause, re.error)
                self.assertFalse(checker.conforms(pattern, "regex"))

    def test_non_strings_do_not_compile(self):
        checker = FormatChecker(formats=["regex"])
        with patch("jsonschema._format.re.compile", side_effect=AssertionError("not a string")):
            for value in (None, False, 2.5, [], {}, b"abc"):
                with self.subTest(value=value):
                    self.assertTrue(checker.conforms(value, "regex"))

    def test_unrelated_exceptions_still_propagate(self):
        checker = FormatChecker(formats=["regex"])
        for error in (RuntimeError("unrelated"), TypeError("unrelated")):
            with (
                self.subTest(error=type(error).__name__),
                patch("jsonschema._format.re.compile", side_effect=error),
                self.assertRaises(type(error)),
            ):
                checker.check("abc", "regex")


if __name__ == "__main__":
    unittest.main()
