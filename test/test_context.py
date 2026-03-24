"""Tests for ahjo.context module - unit tests for non-DB logic."""
import pytest
from unittest.mock import MagicMock, patch
from ahjo.context import Context, filter_nested_dict


class TestFilterNestedDict:
    def test_find_string_leaf(self):
        tree = {"a": {"b": "target", "c": "other"}, "d": "target"}
        result = filter_nested_dict(tree, "target")
        assert result == {"a": {"b": "target"}, "d": "target"}

    def test_find_int_leaf(self):
        tree = {"x": 42, "y": 99}
        result = filter_nested_dict(tree, 42)
        assert result == {"x": 42}

    def test_find_in_list(self):
        tree = {"items": ["a", "b", "c"], "other": "x"}
        result = filter_nested_dict(tree, "b")
        assert result == {"items": ["a", "b", "c"]}

    def test_not_found_returns_none(self):
        tree = {"a": "x", "b": {"c": "y"}}
        result = filter_nested_dict(tree, "missing")
        assert result is None

    def test_none_node(self):
        assert filter_nested_dict(None, "x") is None

    def test_empty_dict(self):
        assert filter_nested_dict({}, "x") is None

    def test_deeply_nested(self):
        tree = {"l1": {"l2": {"l3": {"l4": "found"}}}}
        result = filter_nested_dict(tree, "found")
        assert result == {"l1": {"l2": {"l3": {"l4": "found"}}}}

    def test_string_not_matching(self):
        assert filter_nested_dict("other", "target") is None

    def test_string_matching(self):
        assert filter_nested_dict("target", "target") == "target"

    def test_int_not_matching(self):
        assert filter_nested_dict(10, 20) is None

    def test_list_not_matching(self):
        assert filter_nested_dict(["a", "b"], "c") is None


class TestContextGetCliArg:
    """Test get_cli_arg without needing a real config file."""

    @patch("ahjo.context.Config")
    def _make_context(self, cli_args, MockConfig):
        """Helper to create Context with mocked Config."""
        mock_config_instance = MagicMock()
        mock_config_instance.as_dict.return_value = {"allowed_actions": "ALL"}
        MockConfig.return_value = mock_config_instance
        ctx = Context.__new__(Context)
        ctx.command_line_args = cli_args
        ctx.configuration = {"allowed_actions": "ALL"}
        return ctx

    def test_reserved_key_returned_as_is(self):
        ctx = self._make_context({"action": "deploy"})
        assert ctx.get_cli_arg("action") == "deploy"

    def test_single_value_list_unwrapped(self):
        ctx = self._make_context({"my-arg": ["value1"]})
        assert ctx.get_cli_arg("my-arg") == "value1"

    def test_multi_value_list_returned(self):
        ctx = self._make_context({"my-arg": ["a", "b", "c"]})
        assert ctx.get_cli_arg("my-arg") == ["a", "b", "c"]

    def test_empty_list_returns_true(self):
        ctx = self._make_context({"flag": []})
        assert ctx.get_cli_arg("flag") is True

    def test_missing_key_returns_none(self):
        ctx = self._make_context({})
        assert ctx.get_cli_arg("nonexistent") is None

    def test_string_value_returned(self):
        ctx = self._make_context({"mode": "fast"})
        assert ctx.get_cli_arg("mode") == "fast"

    def test_reserved_key_files(self):
        ctx = self._make_context({"files": ["a.sql", "b.sql"]})
        # Reserved keys return value as-is (no unwrapping)
        assert ctx.get_cli_arg("files") == ["a.sql", "b.sql"]


class TestContextGetCommandLineArgs:
    def test_returns_all_args(self):
        ctx = Context.__new__(Context)
        ctx.command_line_args = {"a": 1, "b": "two"}
        assert ctx.get_command_line_args() == {"a": 1, "b": "two"}


class TestContextTransaction:
    def test_set_and_get_enable_transaction(self):
        ctx = Context.__new__(Context)
        ctx.enable_transaction = None
        ctx.set_enable_transaction(True)
        assert ctx.get_enable_transaction() is True
        ctx.set_enable_transaction(False)
        assert ctx.get_enable_transaction() is False

    def test_commit_and_close_with_no_connection(self):
        """Should log warning when no transaction or connection."""
        ctx = Context.__new__(Context)
        ctx.connectivity_type = "connection"
        ctx.transaction = None
        ctx.connection = None
        # Should not raise
        ctx.commit_and_close_transaction()

    def test_commit_and_close_non_connection_type(self):
        """Should do nothing when connectivity_type is not 'connection'."""
        ctx = Context.__new__(Context)
        ctx.connectivity_type = "engine"
        ctx.transaction = MagicMock()
        # Should not raise or call anything
        ctx.commit_and_close_transaction()

    def test_commit_and_close_transaction_with_transaction(self):
        """Should commit and close the transaction."""
        ctx = Context.__new__(Context)
        ctx.connectivity_type = "connection"
        mock_txn = MagicMock()
        ctx.transaction = mock_txn
        ctx.connection = MagicMock()
        ctx.commit_and_close_transaction()
        mock_txn.commit.assert_called_once()
        mock_txn.close.assert_called_once()
        assert ctx.transaction is None

    def test_commit_and_close_with_connection_no_transaction(self):
        """Should commit and close the connection when no transaction."""
        ctx = Context.__new__(Context)
        ctx.connectivity_type = "connection"
        ctx.transaction = None
        mock_conn = MagicMock()
        ctx.connection = mock_conn
        ctx.commit_and_close_transaction()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
        assert ctx.connection is None


class TestContextGetConnectable:
    def test_defaults_to_engine(self):
        ctx = Context.__new__(Context)
        ctx.connectivity_type = None
        ctx.configuration = {}
        ctx.engine = MagicMock()
        ctx.conn_info = None

        # Mock get_engine to avoid real DB call
        mock_engine = MagicMock()
        ctx.get_engine = MagicMock(return_value=mock_engine)

        result = ctx.get_connectable()
        assert result is mock_engine

    def test_connection_type(self):
        ctx = Context.__new__(Context)
        ctx.connectivity_type = None
        ctx.configuration = {"context_connectable_type": "connection"}
        ctx.connection = None
        ctx.enable_transaction = None
        ctx.transaction = None

        mock_conn = MagicMock()
        ctx.get_connection = MagicMock(return_value=mock_conn)

        result = ctx.get_connectable()
        assert result is mock_conn

    def test_set_connectable(self):
        ctx = Context.__new__(Context)
        ctx.connectivity_type = None
        ctx.set_connectable("connection")
        assert ctx.connectivity_type == "connection"
