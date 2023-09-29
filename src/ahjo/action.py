# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for build steps and other callable actions, that can be defined in a modular way."""

import os
import sys

from logging import getLogger
from typing import Any, Callable, List, Union

from ahjo.context import Context
from ahjo.interface_methods import are_you_sure
from ahjo.operation_manager import OperationManager, format_message
from sqlalchemy.engine import Engine

logger = getLogger('ahjo')

# dict containing information of all defined actions
# action register makes it possible to handle user-defined actions
registered_actions = {}


def action(name: str = None, affects_database: bool = False, dependencies: List[str] = []) -> Callable[[Context, Any], Any]:
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
    """
    def wrapper(func):
        action_name = name
        if action_name is None:
            action_name = func.__name__.replace('_', '-')
        ActionRegisteration(func, action_name,
                            affects_database, set(dependencies))
        return func
    return wrapper


class ActionRegisteration:
    """The registeration information of an action."""

    def __init__(self, function: Callable[[Context, Any], Any], name: str, affects_database: bool, dependencies: dict = {}, baseactions: dict = None):
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

    def pre_exec_check(self, context: Context) -> bool:
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
            logger.info("Note ! this command ("+self.name+") assumes that the " +
                        dep + " action has been successfully completed already")


def create_multiaction(action_name: str, subactions: List[str], description: str = '') -> Callable[[Context, Any], Any]:
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
    baseactions = {
        baseaction for r in registerations for baseaction in r.baseactions}
    dependencies = {
        dep for r in registerations for dep in r.dependencies} - baseactions

    def func(*args, **kwargs):
        returns = [r.function(*args, **kwargs) for r in registerations]
        return returns
    func.__doc__ = description
    ActionRegisteration(func, action_name, affects_database,
                        dependencies, baseactions)
    return func


def check_action_validity(action_name: str, allowed_actions: Union[str, list], skipped_actions: list = []) -> bool:
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
    if (isinstance(allowed_actions, str) and allowed_actions != "ALL") and action_name != allowed_actions:
        logger.error("Action " + action_name + " is not permitted, allowed action: " + allowed_actions)
        return False
    if isinstance(allowed_actions, list) and action_name not in allowed_actions:
        logger.error("Action " + action_name + " is not permitted, allowed actions: " + ', '.join(allowed_actions))
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
        logger.error("Available actions: " +
                     ', '.join(registered_actions.keys()))
        return False
    return True


def execute_action(action_name: str, config_filename: str, engine: Engine = None, skip_confirmation: bool = False, 
        context: Context = None, *args, **kwargs):
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
    logger.info('------')
    with OperationManager('Starting to execute "' + action_name + '"'):
        if context is None:
            context = Context(config_filename, engine)
        # validity check
        action_valid = check_action_validity(
            action_name, 
            context.configuration.get('allowed_actions', []), 
            skipped_actions = context.configuration.get('skipped_actions', [])
        )
        if not action_valid: 
            return
        action = registered_actions.get(action_name)
        
        # user confirmation
        if not skip_confirmation and not action.pre_exec_check(context):
            return
    
    action_output = action.function(context, *args, **kwargs)
    
    if context.get_enable_transaction(): 
        context.commit_and_close_transaction()

    return action_output


def list_actions():
    logger.info('-------------------------------')
    logger.info('List of available actions')
    logger.info('-------------------------------')
    for key, registeration in sorted(registered_actions.items()):
        logger.info(
            f"'{key}': {registeration.function.__doc__ or 'No description available.'}")


def import_actions():
    if os.path.exists('ahjo_actions.py') or os.path.exists('./ahjo_actions'):
        logger.debug(format_message('ahjo_actions found'))
        try:
            sys.path.append(os.getcwd())
            import ahjo_actions
            logger.info(format_message('Succesfully loaded ahjo_actions'))
        except:
            logger.exception(format_message('Error while loading ahjo_actions'))
            raise
    else:
        logger.info(format_message('ahjo_actions not found'))
