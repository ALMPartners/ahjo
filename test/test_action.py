"""Tests for ahjo.action module."""
import pytest
from unittest.mock import MagicMock, patch

import ahjo.action as action_module
from ahjo.action import (
    ActionRegisteration,
    action,
    check_action_validity,
    create_multiaction,
    list_actions,
    action_affects_db,
)


@pytest.fixture(autouse=True)
def clear_registered_actions():
    """Reset the global registered_actions dict before and after each test."""
    original = action_module.registered_actions.copy()
    action_module.registered_actions.clear()
    yield
    action_module.registered_actions.clear()
    action_module.registered_actions.update(original)


class TestActionRegisteration:
    def test_register_adds_to_global_dict(self):
        func = MagicMock()
        reg = ActionRegisteration(
            function=func, name="test-action", affects_database=False
        )
        assert "test-action" in action_module.registered_actions
        assert action_module.registered_actions["test-action"] is reg

    def test_attributes_stored(self):
        func = MagicMock()
        reg = ActionRegisteration(
            function=func,
            name="my-action",
            affects_database=True,
            dependencies={"dep1", "dep2"},
            connection_required=False,
        )
        assert reg.function is func
        assert reg.name == "my-action"
        assert reg.affects_database is True
        assert reg.dependencies == {"dep1", "dep2"}
        assert reg.connection_required is False

    def test_baseactions_defaults_to_name(self):
        func = MagicMock()
        reg = ActionRegisteration(
            function=func, name="solo-action", affects_database=False
        )
        assert reg.baseactions == {"solo-action"}

    def test_baseactions_custom(self):
        func = MagicMock()
        reg = ActionRegisteration(
            function=func,
            name="combo",
            affects_database=False,
            baseactions={"a", "b"},
        )
        assert reg.baseactions == {"a", "b"}

    def test_overwrite_existing_action(self):
        func1 = MagicMock()
        func2 = MagicMock()
        ActionRegisteration(function=func1, name="dup", affects_database=False)
        reg2 = ActionRegisteration(function=func2, name="dup", affects_database=True)
        assert action_module.registered_actions["dup"] is reg2
        assert action_module.registered_actions["dup"].affects_database is True


class TestActionDecorator:
    def test_registers_with_function_name(self):
        @action()
        def my_deploy(context):
            """Deploy action."""
            pass

        assert "my-deploy" in action_module.registered_actions
        reg = action_module.registered_actions["my-deploy"]
        assert reg.function is my_deploy
        assert reg.affects_database is False

    def test_registers_with_custom_name(self):
        @action(name="custom-name", affects_database=True)
        def some_func(context):
            pass

        assert "custom-name" in action_module.registered_actions
        assert action_module.registered_actions["custom-name"].affects_database is True

    def test_dependencies_stored(self):
        @action(dependencies=["init", "structure"])
        def deploy(context):
            pass

        reg = action_module.registered_actions["deploy"]
        assert reg.dependencies == {"init", "structure"}

    def test_connection_required_default(self):
        @action()
        def simple(context):
            pass

        reg = action_module.registered_actions["simple"]
        assert reg.connection_required is True

    def test_connection_not_required(self):
        @action(connection_required=False)
        def offline(context):
            pass

        reg = action_module.registered_actions["offline"]
        assert reg.connection_required is False

    def test_decorator_returns_original_function(self):
        @action()
        def original(context):
            return 42

        # The decorator should return the original function
        assert original(None) == 42


class TestCreateMultiaction:
    def test_creates_multiaction(self):
        @action(name="step1")
        def step1(context):
            """Step 1."""
            return "s1"

        @action(name="step2", affects_database=True)
        def step2(context):
            """Step 2."""
            return "s2"

        create_multiaction("multi", ["step1", "step2"], description="Run both")
        assert "multi" in action_module.registered_actions
        reg = action_module.registered_actions["multi"]
        assert reg.affects_database is True  # inherited from step2
        assert reg.baseactions == {"step1", "step2"}

    def test_multiaction_executes_subactions(self):
        results = []

        @action(name="a")
        def a_action(context):
            results.append("a")
            return "a"

        @action(name="b")
        def b_action(context):
            results.append("b")
            return "b"

        multi_func = create_multiaction("a-then-b", ["a", "b"])
        output = multi_func("fake_context")
        assert results == ["a", "b"]
        assert output == ["a", "b"]

    def test_multiaction_dependencies_exclude_baseactions(self):
        @action(name="x", dependencies=["y"])
        def x(context):
            pass

        @action(name="y")
        def y(context):
            pass

        create_multiaction("xy", ["x", "y"])
        reg = action_module.registered_actions["xy"]
        # y is a baseaction, so it should NOT appear in dependencies
        assert "y" not in reg.dependencies

    def test_multiaction_connection_required(self):
        @action(name="no-conn", connection_required=False)
        def no_conn(context):
            pass

        @action(name="needs-conn", connection_required=True)
        def needs_conn(context):
            pass

        create_multiaction("mixed", ["no-conn", "needs-conn"])
        reg = action_module.registered_actions["mixed"]
        assert reg.connection_required is True


class TestCheckActionValidity:
    def test_valid_action_with_all_allowed(self):
        @action(name="deploy")
        def deploy(context):
            pass

        assert check_action_validity("deploy", "ALL") is True

    def test_invalid_action_not_registered(self):
        @action(name="deploy")
        def deploy(context):
            pass

        assert check_action_validity("nonexistent", "ALL") is False

    def test_no_actions_defined(self):
        assert check_action_validity("anything", "ALL") is False

    def test_action_not_in_allowed_list(self):
        @action(name="deploy")
        def deploy(context):
            pass

        assert check_action_validity("deploy", ["init", "data"]) is False

    def test_action_in_allowed_list(self):
        @action(name="deploy")
        def deploy(context):
            pass

        assert check_action_validity("deploy", ["deploy", "data"]) is True

    def test_action_not_matching_allowed_string(self):
        @action(name="deploy")
        def deploy(context):
            pass

        assert check_action_validity("deploy", "init") is False

    def test_action_matching_allowed_string(self):
        @action(name="deploy")
        def deploy(context):
            pass

        assert check_action_validity("deploy", "deploy") is True

    def test_action_skipped(self):
        @action(name="deploy")
        def deploy(context):
            pass

        assert (
            check_action_validity("deploy", "ALL", skipped_actions=["deploy"]) is False
        )

    def test_action_not_skipped(self):
        @action(name="deploy")
        def deploy(context):
            pass

        assert (
            check_action_validity("deploy", "ALL", skipped_actions=["init"]) is True
        )


class TestActionAffectsDb:
    def test_registered_action_affects_db(self):
        @action(name="init", affects_database=True)
        def init(context):
            pass

        assert action_affects_db("init") is True

    def test_registered_action_does_not_affect_db(self):
        @action(name="version", affects_database=False)
        def version(context):
            pass

        assert action_affects_db("version") is False

    def test_unregistered_action_returns_false(self):
        assert action_affects_db("nonexistent") is False


class TestListActions:
    def test_list_actions_prints_registered(self, capsys):
        @action(name="deploy")
        def deploy(context):
            """Deploy objects."""
            pass

        @action(name="init")
        def init(context):
            """Initialize database."""
            pass

        list_actions()
        captured = capsys.readouterr()
        assert "deploy" in captured.out
        assert "init" in captured.out
        assert "Deploy objects." in captured.out
        assert "Initialize database." in captured.out

    def test_list_actions_no_doc(self, capsys):
        @action(name="nodoc")
        def nodoc(context):
            pass

        list_actions()
        captured = capsys.readouterr()
        assert "No description available." in captured.out


class TestNotifyDependencies:
    def test_notifies_dependencies(self, caplog):
        import logging

        with caplog.at_level(logging.INFO, logger="ahjo"):

            @action(name="deploy", dependencies=["init"])
            def deploy(context):
                pass

            reg = action_module.registered_actions["deploy"]
            reg.notify_dependencies()

        assert any("init" in record.message for record in caplog.records)

    def test_no_notification_for_complete_build(self, caplog):
        import logging

        with caplog.at_level(logging.INFO, logger="ahjo"):

            @action(name="complete-build", dependencies=["init"])
            def complete_build(context):
                pass

            reg = action_module.registered_actions["complete-build"]
            reg.notify_dependencies()

        assert not any("init" in record.message for record in caplog.records)


class TestImportActions:
    def test_import_nonexistent_file_raises(self):
        with pytest.raises(Exception, match="not found"):
            action_module.import_actions(
                [{"source_file": "nonexistent_module.py", "name": "Missing"}]
            )
