# Ahjo - Database deployment framework
#
# Copyright 2019 - 2025 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for build steps and other callable actions, that can be defined in a modular way."""

import os
import sys
import importlib
import time

from logging import getLogger
from typing import Any, Callable, List, Union

from ahjo.context import Context
from ahjo.interface_methods import are_you_sure, verify_input
from ahjo.operation_manager import OperationManager, format_message
from sqlalchemy.engine import Engine

logger = getLogger("ahjo")

# dict containing information of all defined actions
# action register makes it possible to handle user-defined actions
registered_actions = {}
DEFAULT_ACTIONS_SRC = [{"source_file": "ahjo_actions.py", "name": "Ahjo actions"}]


def action(
    name: str = None,
    affects_database: bool = False,
    dependencies: List[str] = [],
    connection_required: bool = True,
) -> Callable[[Context, Any], Any]:
    """Wrapper function for actions.

    Creates and registers an action.

    Arguments:
    ----------
    name
        The name of the action, that acts as a key.
        Also used in printed messages.
    affects_database
        If true, confirmation for the actions is asked at the start.
    dependencies
        All the actions that need to be done before the action.
        Dependencies cause notifications at action start.
    connection_required
        If True, the action requires a connection to database.

    Returns:
    --------
    function
        Wrapper function for the action.
    """

    def wrapper(func):
        action_name = name
        if action_name is None:
            action_name = func.__name__.replace("_", "-")
        ActionRegisteration(
            function=func,
            name=action_name,
            affects_database=affects_database,
            dependencies=set(dependencies),
            connection_required=connection_required,
        )
        return func

    return wrapper


class ActionRegisteration:
    """The registeration information of an action."""

    def __init__(
        self,
        function: Callable[[Context, Any], Any],
        name: str,
        affects_database: bool,
        dependencies: dict = {},
        baseactions: dict = None,
        connection_required: bool = True,
    ):
        self.function = function
        self.name = name
        self.affects_database = affects_database
        self.dependencies = set(dependencies)
        self.baseactions = baseactions if baseactions is not None else {name}
        self.register()
        self.connection_required = connection_required

    def register(self):
        """Adds self to a global dictionary of all actions."""
        global registered_actions
        registered_actions[self.name] = self

    def pre_exec_check(self, context: Context) -> bool:
        """Prints dependencies and asks permission for database operations.
        Called before action execution.
        """
        self.notify_dependencies()
        if self.affects_database is True:
            conn_info = context.get_conn_info()
            warning_message = (
                f"Warning! You are about to commit changes to server "
                f"{conn_info.get('server')} database {conn_info.get('database')} \n"
            )
            if context.configuration.get("target_database_protected", False):
                return verify_input(
                    message=warning_message,
                    input_to_verify=context.configuration.get(
                        "target_database_name", ""
                    ),
                    input_name="database name",
                    use_logger=True,
                )
            else:
                return are_you_sure(warning_message)
        return True

    def notify_dependencies(self):
        """Notify user if action is dependent of other actions.
        Do not notify user when action 'complete-build' is run.
        """
        if self.name == "complete-build":
            return
        for dep in self.dependencies:
            logger.info(
                "Note ! this command ("
                + self.name
                + ") assumes that the "
                + dep
                + " action has been successfully completed already"
            )


def create_multiaction(
    action_name: str, subactions: List[str], description: str = ""
) -> Callable[[Context, Any], Any]:
    """Creates and registers an action that only executes the subactions in order.
    Dependencies and allowation rules are inferred from subactions.
    Subactions must be defined first, because the function uses registered definitions!

    Argumens
    --------
    action_name
        Name of the new action that acts as a key
    subactions
        The subactions in the execution order.
        The subactions must be registered before the multiaction.
    description
        Human readable action description.

    Returns
    -------
    function
        The combination of subaction functions.
    """
    registerations = [registered_actions[sa] for sa in subactions]
    affects_database = any([r.affects_database for r in registerations])
    connection_required = any([r.connection_required for r in registerations])
    baseactions = {baseaction for r in registerations for baseaction in r.baseactions}
    dependencies = {dep for r in registerations for dep in r.dependencies} - baseactions

    def func(*args, **kwargs):
        returns = [r.function(*args, **kwargs) for r in registerations]
        return returns

    func.__doc__ = description
    ActionRegisteration(
        function=func,
        name=action_name,
        affects_database=affects_database,
        dependencies=dependencies,
        baseactions=baseactions,
        connection_required=connection_required,
    )
    return func


def check_action_validity(
    action_name: str, allowed_actions: Union[str, list], skipped_actions: list = []
) -> bool:
    """Check if given action is permitted and registered.

    Arguments
    ---------
    action_name
        The name of the action to execute
    allowed_actions
        The actions allowed in the configuration file.
    skipped_actions
        The actions that are skipped.
    Returns
    -------
    bool
        Is the action valid or not?
    """
    if (
        isinstance(allowed_actions, str) and allowed_actions != "ALL"
    ) and action_name != allowed_actions:
        logger.error(
            "Action "
            + action_name
            + " is not permitted, allowed action: "
            + allowed_actions
        )
        return False
    if isinstance(allowed_actions, list) and action_name not in allowed_actions:
        logger.error(
            "Action "
            + action_name
            + " is not permitted, allowed actions: "
            + ", ".join(allowed_actions)
        )
        return False
    if isinstance(skipped_actions, list):
        if action_name in skipped_actions:
            logger.info("Action " + action_name + " was skipped.")
            return False
    if len(registered_actions) == 0:
        logger.error("No actions defined")
        return False
    if registered_actions.get(action_name) is None:
        logger.error("No action " + action_name + " found.")
        logger.error("Available actions: " + ", ".join(registered_actions.keys()))
        return False
    return True


def execute_action(
    action_name: str,
    config_filename: str,
    engine: Engine = None,
    skip_confirmation: bool = False,
    context: Context = None,
    *args,
    **kwargs,
):
    """Prepare and execute given action.

    Does the logging and error handling for preparation.

    Arguments
    ---------
    action_name: str
        The name of the action to execute
    config_filename: str
        The name of the config file for context creation.
    engine: sqlalchemy.engine.Engine
        SQL Alchemy engine.
    skip_confirmation: bool
        If True, user confirmation is disabled.
    context: ahjo.context.Context
        Context object. If None, a new one is created.
    """
    logger.info("------", extra={"record_class": "line"})
    with OperationManager('Starting to execute "' + action_name + '"'):
        if context is None:
            context = Context(config_filename, engine)
        # validity check
        action_valid = check_action_validity(
            action_name,
            context.configuration.get("allowed_actions", []),
            skipped_actions=context.configuration.get("skipped_actions", []),
        )
        if not action_valid:
            return
        action = registered_actions.get(action_name)

        # user confirmation
        if not skip_confirmation and not action.pre_exec_check(context):
            return

    start_time = time.time()
    action_output = action.function(context, *args, **kwargs)
    end_time = time.time()
    logger.debug(
        f"Action '{action_name}' executed in {end_time - start_time:.2f} seconds"
    )

    if context.get_enable_transaction():
        context.commit_and_close_transaction()

    return action_output


def list_actions():
    print("List of available actions")
    print("-------------------------------")
    for key, registeration in sorted(registered_actions.items()):
        print(
            f"'{key}': {registeration.function.__doc__ or 'No description available.'}"
        )


def import_actions(
    ahjo_action_files: list = DEFAULT_ACTIONS_SRC, reload_module: bool = False
) -> None:
    """Import actions from user defined action files.

    Arguments
    ---------
    ahjo_action_files: list
        Ahjo action files to be imported.
        If None, default action file (ahjo_actions.py) is imported from current working directory.

    reload_module: bool
        Reload ahjo actions if True.

    """
    try:
        for action_file in ahjo_action_files:

            action_source = action_file["source_file"]
            action_module = (
                action_source.replace(".py", "").replace("/", ".").replace("\\", ".")
            )
            action_name = action_file["name"]

            # Check if action file exists
            if not os.path.exists(action_source):
                logger.info(format_message(f"{action_name} not found"))
                raise Exception(f"{action_name} not found")

            # Load actions
            sys.path.append(os.getcwd())
            imported_module = importlib.import_module(action_module)
            if reload_module:
                importlib.reload(imported_module)

            logger.info(format_message(f"Succesfully loaded {action_name}"))

    except ModuleNotFoundError as e:
        logger.error(
            format_message(
                f"Error while importing modules from {action_source}. Make sure that the modules are installed in the same environment as ahjo."
            )
        )
        if getattr(sys, "frozen", False):  # installed from an msi
            logger.error(
                format_message(
                    "The action file might contain dependencies that are not included in the MSI package. Use a pip-installed version of ahjo and install the custom dependencies with pip."
                )
            )
        raise
    except Exception as e:
        logger.error(format_message(f"Error while loading ahjo actions: {e}"))
        raise


def action_affects_db(action_name: str) -> bool:
    """Check if given action affects database.

    Arguments
    ---------
    action_name: str
        The name of the action to check

    Returns
    -------
    bool
        Does the action affect database?
    """
    if action_name in registered_actions:
        return registered_actions[action_name].affects_database
    else:
        return False
