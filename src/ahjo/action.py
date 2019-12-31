# Ahjo - Database deployment framework
#
# Copyright 2019, 2020 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for build steps and other callable actions, that can be defined in a modular way."""
from logging import getLogger

from ahjo.interface_methods import are_you_sure
from ahjo.context import Context
from ahjo.operation_manager import OperationManager

logger = getLogger('ahjo')

# dict containing information of all defined actions
# action register makes it possible to handle user-defined actions
registered_actions = {}


def action(name, affects_database, dependencies=[]):
    """Wrapper function for actions.

    Creates and registers an action.

    Arguments:
    ----------
    name: str
        The name of the action, that acts as a key.
        Also used in printed messages.
    affects_database: Boolean
        If true, confirmation for the actions is asked at the start.
    dependencies: list(str)
        All the actions that need to be done before the action.
        Dependencies cause notifications at action start.
    """
    def wrapper(func):
        ActionRegisteration(func, name, affects_database, set(dependencies))
        return func
    return wrapper


class ActionRegisteration:
    """The registeration information of an action."""
    def __init__(self, function, name, affects_database, dependencies={}, baseactions=None):
        self.function = function
        self.name = name
        self.affects_database = affects_database
        self.dependencies = set(dependencies)
        self.baseactions = baseactions if baseactions is not None else {name}
        self.register()

    def register(self):
        """Adds self to a global dictionary of all actions."""
        global registered_actions
        registered_actions[self.name] = self

    def pre_exec_check(self, context):
        """Prints dependencies and asks permission for database operations.
        Called before action execution.
        """
        self.notify_dependencies()
        if self.affects_database is True:
            conn_info = context.get_conn_info()
            warning_message = f"Warning! You are about to commit changes to server " \
                f"{conn_info.get('server')} database {conn_info.get('database')}"
            if not are_you_sure(warning_message):
                return False
        return True

    def notify_dependencies(self):
        """Notify user if action is dependent of other actions.
        Do not notify user when action 'complete-build' is run.
        """
        if self.name == 'complete-build':
            return
        for dep in self.dependencies:
            logger.info("Note ! this command ("+self.name+") assumes that the "+ dep +" action has been successfully completed already")


def create_multiaction(action_name, subactions):
    """Creates and registers an action that only executes the subactions in order.
    Dependencies and allowation rules are inferred from subactions.
    Subactions must be defined first, because the function uses registered definintions!

    Argumens
    --------
    action_name: str
        Name of the new action that acts as a key
    subactions: list(str)
        The subactions in the execution order.
        The subactions must be registered before the multiaction.

    Returns
    -------
    func: function
        The combination of subaction functions.
    """
    global registered_actions
    registerations = [registered_actions[sa] for sa in subactions]
    affects_database = any([r.affects_database for r in registerations])
    baseactions = {baseaction for r in registerations for baseaction in r.baseactions}
    dependencies = {dep for r in registerations for dep in r.dependencies} - baseactions
    def func(*args, **kwargs):
        returns = [r.function(*args, **kwargs) for r in registerations]
        return returns
    ActionRegisteration(func, action_name, affects_database, dependencies, baseactions)
    return func


def check_action_validity(action_name, registered_actions, allowed_actions):
    """Check if given action is permitted and registered.

    Arguments
    ---------
    action_name: str
        The name of the action to execute
    registered_actions: list(str)
        The registered actions: if the action is not registered it cannot be executed.
    allowed_actions: list(str)
        The actions allowed in the configuration file.
    Returns
    -------
    Boolean
        Is the action valid or not?
    """
    if action_name not in allowed_actions and 'ALL' not in allowed_actions:
        logger.error("Action " + action_name + " is not permitted, allowed actions: " + ', '.join(allowed_actions))
        return False
    if len(registered_actions) == 0:
        logger.error("No actions defined")
        return False
    if registered_actions.get(action_name) is None:
        logger.error("No action " + action_name + " found.")
        logger.error("Available actions: " + ', '.join(registered_actions.keys()))
        return False
    return True


def execute_action(action_name, config_filename, *args, **kwargs):
    """Prepares and executes given action.
    Does the logging and error handling for preparation.

    Arguments
    ---------
    action_name: str
        The name of the action to execute
    config_filename: str
        The name of the config file for context creation.
    """
    logger.info('------')
    with OperationManager('Starting to execute "' + action_name + '"'):
        # environment
        context = Context(config_filename)

        # fetching action (if allowed)
        global registered_actions
        if not check_action_validity(action_name, registered_actions, context.configuration.get('allowed_actions', [])):
            return
        action = registered_actions.get(action_name)

        # execution
        if not action.pre_exec_check(context):
            return

    return action.function(context, *args, **kwargs)
