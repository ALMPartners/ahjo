"""Tests for ahjo.operation_manager module."""
import re

from ahjo.operation_manager import OperationManager, format_message


class TestFormatMessage:
    def test_format_includes_timestamp(self):
        result = format_message("hello world")
        # Should match [YYYY-MM-DD HH:MM:SS] hello world
        pattern = r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] hello world$"
        assert re.match(pattern, result)

    def test_empty_message(self):
        result = format_message("")
        pattern = r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] $"
        assert re.match(pattern, result)

    def test_message_with_special_chars(self):
        result = format_message("action 'deploy' started!")
        assert "action 'deploy' started!" in result


class TestOperationManager:
    def test_context_manager_logs_enter_and_exit(self, caplog):
        import logging

        with caplog.at_level(logging.INFO, logger="ahjo"):
            with OperationManager("Test operation"):
                pass

        messages = [r.message for r in caplog.records]
        # Entry message should contain "Test operation" with timestamp
        assert any("Test operation" in m for m in messages)
        # Exit should log separator line
        assert any("------" in m for m in messages)

    def test_context_manager_logs_on_exception(self, caplog):
        import logging

        with caplog.at_level(logging.INFO, logger="ahjo"):
            try:
                with OperationManager("Failing operation"):
                    raise ValueError("boom")
            except ValueError:
                pass

        messages = [r.message for r in caplog.records]
        # Should still log the separator on exit even if exception occurs
        assert any("------" in m for m in messages)
