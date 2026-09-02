from __future__ import annotations

import contextlib
import io
import unittest

from loguru import logger


class InvalidFormatFeedbackTests(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()
        logger.configure(patcher=None, extra={})

    def tearDown(self) -> None:
        logger.remove()
        logger.configure(patcher=None, extra={})

    def test_catch_true_reports_actionable_context(self) -> None:
        logger.add(lambda message: None, format="{missing_context}", catch=True)
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            logger.info("message that cannot be formatted")

        feedback = stderr.getvalue()
        self.assertIn("missing_context", feedback)
        self.assertIn("logger.bind(key=value)", feedback)
        self.assertIn("extra[key]", feedback)
        for record_key in ("elapsed", "exception", "extra", "file", "level", "message"):
            self.assertIn(record_key, feedback)

    def test_catch_false_raises_enhanced_key_error(self) -> None:
        logger.add(lambda message: None, format="{another_missing_key}", catch=False)

        with self.assertRaises(KeyError) as raised:
            logger.info("message that cannot be formatted")

        feedback = str(raised.exception)
        self.assertIn("another_missing_key", feedback)
        self.assertIn("logger.bind(key=value)", feedback)
        self.assertIn("extra[key]", feedback)

    def test_patcher_supplied_top_level_key_remains_valid(self) -> None:
        output: list[str] = []

        def add_request_id(record: dict) -> None:
            record["request_id"] = "req-hidden"

        logger.configure(patcher=add_request_id)
        logger.add(output.append, format="{message}:{request_id}", catch=False)
        logger.info("ok")

        self.assertEqual([str(message).strip() for message in output], ["ok:req-hidden"])


if __name__ == "__main__":
    unittest.main()
