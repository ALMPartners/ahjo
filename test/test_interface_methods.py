"""Tests for ahjo.interface_methods module."""
import pytest
from unittest.mock import patch

from ahjo.interface_methods import (
    are_you_sure,
    verify_input,
    display_message,
    remove_special_chars,
    format_to_table,
    rearrange_params,
)


class TestRemoveSpecialChars:
    def test_basic_string(self):
        assert remove_special_chars("Hello World") == "hello_world"

    def test_special_characters_removed(self):
        assert remove_special_chars("test@#$%^&*()!") == "test"

    def test_underscores_preserved(self):
        assert remove_special_chars("my_table_name") == "my_table_name"

    def test_numbers_preserved(self):
        assert remove_special_chars("table123") == "table123"

    def test_empty_string(self):
        assert remove_special_chars("") == ""

    def test_spaces_become_underscores(self):
        assert remove_special_chars("a b c") == "a_b_c"

    def test_mixed_input(self):
        assert remove_special_chars("My Table! (v2)") == "my_table_v2"

    def test_dots_removed(self):
        assert remove_special_chars("dbo.my_proc") == "dbomy_proc"

    def test_result_is_lowercase(self):
        assert remove_special_chars("UPPER") == "upper"


class TestFormatToTable:
    def test_empty_list(self):
        assert format_to_table([]) == "No output."

    def test_single_row(self):
        result = format_to_table([["a", "bb", "ccc"]])
        assert "a" in result
        assert "bb" in result
        assert "ccc" in result

    def test_column_alignment(self):
        result = format_to_table([["Name", "Age"], ["Alice", "30"], ["Bob", "5"]])
        lines = result.strip().split("\n")
        assert len(lines) == 3
        # Columns should be aligned
        for line in lines:
            assert len(line.rstrip()) > 0

    def test_numeric_values(self):
        result = format_to_table([[1, 2], [3, 4]])
        assert "1" in result
        assert "4" in result


class TestAreYouSure:
    def test_user_confirms_y(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "Y")
        assert are_you_sure("Proceed?", use_logger=False) is True

    def test_user_confirms_lowercase_y(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert are_you_sure("Proceed?", use_logger=False) is True

    def test_user_declines_n(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "N")
        assert are_you_sure("Proceed?", use_logger=False) is False

    def test_user_declines_empty(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert are_you_sure("Proceed?", use_logger=False) is False

    def test_user_declines_other(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "maybe")
        assert are_you_sure("Proceed?", use_logger=False) is False

    def test_message_printed(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "N")
        are_you_sure("Custom warning!", use_logger=False)
        captured = capsys.readouterr()
        assert "Custom warning!" in captured.out

    def test_list_message(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "N")
        are_you_sure(["Line 1", "Line 2"], use_logger=False)
        captured = capsys.readouterr()
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out


class TestVerifyInput:
    def test_matching_input_returns_true(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda: "my_database")
        result = verify_input(
            "Verify DB name", "my_database", "database", use_logger=False
        )
        assert result is True

    def test_non_matching_input_returns_false(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda: "wrong_name")
        result = verify_input(
            "Verify DB name", "my_database", "database", use_logger=False
        )
        assert result is False

    def test_empty_input_returns_false(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda: "")
        result = verify_input("Verify", "expected", "field", use_logger=False)
        assert result is False


class TestDisplayMessage:
    def test_string_message_printed(self, capsys):
        display_message("Hello!", use_logger=False)
        captured = capsys.readouterr()
        assert "Hello!" in captured.out

    def test_list_message_printed(self, capsys):
        display_message(["Msg 1", "Msg 2"], use_logger=False)
        captured = capsys.readouterr()
        assert "Msg 1" in captured.out
        assert "Msg 2" in captured.out

    def test_string_message_logged(self, caplog):
        import logging

        with caplog.at_level(logging.INFO, logger="ahjo"):
            display_message("Logged message", use_logger=True)
        assert any("Logged message" in r.message for r in caplog.records)

    def test_list_message_logged(self, caplog):
        import logging

        with caplog.at_level(logging.INFO, logger="ahjo"):
            display_message(["Log 1", "Log 2"], use_logger=True)
        messages = [r.message for r in caplog.records]
        assert any("Log 1" in m for m in messages)
        assert any("Log 2" in m for m in messages)


class TestRearrangeParams:
    def test_rearranges_deprecated_kwarg(self):
        @rearrange_params({"old_name": "new_name"})
        def func(new_name=None):
            return new_name

        result = func(old_name="value")
        assert result == "value"

    def test_keeps_non_mapped_kwargs(self):
        @rearrange_params({"old": "new"})
        def func(other=None):
            return other

        result = func(other="kept")
        assert result == "kept"

    def test_no_kwargs_no_change(self):
        @rearrange_params({"old": "new"})
        def func(x):
            return x

        result = func(10)
        assert result == 10

    def test_mixed_kwargs(self):
        @rearrange_params({"old_param": "new_param"})
        def func(new_param=None, other=None):
            return (new_param, other)

        result = func(old_param="migrated", other="stays")
        assert result == ("migrated", "stays")
