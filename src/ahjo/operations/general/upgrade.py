# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import copy
import sys
import os
import ahjo.scripts.master_actions
from ahjo.interface_methods import load_conf, are_you_sure
from ahjo.operations.general.git_version import _get_all_tags, _get_git_version, _get_previous_tag, _checkout_tag
from ahjo.operations.general.db_info import print_db_collation
from ahjo.action import execute_action, import_actions, DEFAULT_ACTIONS_SRC
from ahjo.context import Context
from logging import getLogger


sys.path.append(os.getcwd())
logger = getLogger('ahjo')

def upgrade(config_filename: str, context: Context, version: str = None, skip_confirmation: bool = False):
    """Upgrade database with upgrade actions.
    
    Parameters
    ----------
    config_filename : str
        Path to the configuration file.
    context : ahjo.context.Context
        Context object.
    version : str, optional
        Version to be upgraded. If not defined, the next upgradable version is upgraded.
    skip_confirmation : bool, optional
        Skip confirmation prompt. Default is False.
    
    Returns
    -------
    bool
        True if upgrade was successful, otherwise False.
    """
    try:
        # Load settings
        config = load_conf(config_filename)
        upgrade_actions = load_conf(config.get("upgrade_actions_file", f"./upgrade_actions.jsonc"))
        git_table_schema = config.get('git_table_schema', 'dbo')
        git_table = config.get('git_table', 'git_version')
        connectable_type = config.get("context_connectable_type", "engine")
        updated_versions = []

        # Display database collation
        if context.configuration.get("display_db_info", True):
            print_db_collation(context)

        # Get the current git commit from database
        _, _, current_db_version = _get_git_version(context.get_connectable(), git_table_schema, git_table)

        # Select versions to be deployed
        version_actions = get_upgradable_version_actions(upgrade_actions, current_db_version)
        if len(list(version_actions.keys())) == 0:
            logger.info("Database is already up to date. Current database version is " + current_db_version)
            return True

        # Validate user input
        if version is not None:
            version_actions = validate_version(version, version_actions, upgrade_actions, current_db_version)

        if not skip_confirmation:
            # Format are_you_sure message
            are_you_sure_msg = ["You are about to run the following upgrade actions: ", ""]
            for tag in version_actions:
                are_you_sure_msg.append(tag + ":")
                action_names = [action[0] if isinstance(action, list) else action for action in version_actions[tag]]
                are_you_sure_msg.append(" " * 2 + ", ".join(action_names))
            are_you_sure_msg.append("")

            # Confirm action
            if not are_you_sure(are_you_sure_msg, False): return False

        for git_version in version_actions:

            # Checkout the next upgradable git version
            _checkout_tag(git_version)
            config = load_conf(config_filename)

            # Update version info in the database logger
            if config.get("enable_database_logging", True):
                for handler in logger.handlers:
                    if handler.name == "handler_database":
                        handler.flush()
                        handler.db_logger.set_git_commit(git_version)
                        break

            # Reload ahjo actions
            import_actions(
                ahjo_action_files = config.get("ahjo_action_files", DEFAULT_ACTIONS_SRC), 
                reload_module = True
            )

            # Deploy version upgrades
            actions = version_actions[git_version]
            for action in actions:

                # Add parameters
                kwargs = {}
                if isinstance(action, list):
                    action_name = action[0]
                    parameters = action[1]
                    for arg in parameters:
                        kwargs[arg] = parameters[arg]
                else:
                    action_name = action

                # Run action
                execute_action(
                    *[action_name, config_filename, None, True, context],
                    **kwargs
                )

            # Check that the database version was updated
            _, _, db_version = _get_git_version(context.get_connectable(), git_table_schema, git_table)
            if db_version != git_version:
                raise Exception(f"Database (version {db_version}) was not updated to match the git version: {git_version}")
            
            updated_versions.append(db_version)

        if connectable_type == "connection":
            connection = context.get_connectable()
            connection.commit()
            connection.close()
            
    except Exception as error:
        logger.error('Ahjo project upgrade failed:')
        logger.error(error)
        if connectable_type == "connection":
            logger.error('Aborted upgrade. Changes were not committed to the database.')
        return False

    else:
        logger.info("The following versions were successfully upgraded: ")
        for version in updated_versions:
            logger.info(" " * 2 + version)
        logger.info("------")

    return True


def get_upgradable_version_actions(upgrade_actions: dict, current_version: str):
    """Return a dictionary of upgradable versions and their actions."""

    if upgrade_actions is None:
        raise ValueError("Upgrade actions not defined.")

    version_actions = copy.deepcopy(upgrade_actions)
    git_tags = _get_all_tags()
    tag_set = set(git_tags)

    if current_version not in tag_set:
        raise ValueError(f"Current version {current_version} does not exist in the repository.")

    # From upgrade actions, remove versions that are previous to the current version.
    for version in upgrade_actions:
        try:
            previous_version = _get_previous_tag(version)
        except: # No previous version found.
            raise ValueError(f"Upgrade actions cannot be defined for the first version: {version}.")
        else: # Previous version found
            if previous_version == current_version:
                break
            else:
                version_actions.pop(version)

    # Validate versions and actions.
    previous_version = None
    for version in version_actions:

        actions = version_actions[version]

        if not isinstance(actions, list):
            raise ValueError(f"Upgrade actions for version {version} are not defined as list.")
        
        if len(actions) == 0:
            raise ValueError(f"Upgrade actions are not defined for version {version}.")
        
        for action in actions:
            if not isinstance(action, str) and not isinstance(action, list):
                raise ValueError(f"Upgrade action is not defined as string or list.")
            else:
                if isinstance(action, list) and len(action) > 0:
                    if not isinstance(action[0], str):
                        raise ValueError(f"Upgrade action name is not defined as string.")
                    if len(action) >= 1 and not isinstance(action[1], dict):
                        raise ValueError(f"Upgrade action parameters are not defined as dictionary.")

        if version not in tag_set:
            raise ValueError(f"Git tag {version} does not exist in the repository.")
        
        if previous_version is not None:
            git_previous_tag = _get_previous_tag(version)
            if previous_version != git_previous_tag:
                raise ValueError(f"Git versions in upgrade_actions are not listed in the correct order: {previous_version} -> {version}")
        previous_version = version
        
    return version_actions


def validate_version(version: str, version_actions: dict, upgrade_actions: dict, current_db_version: str):
    """Validate that the version is upgradable."""
    if version not in upgrade_actions:
        raise ValueError(f"Version {version} actions are not defined in upgrade actions config file.")
    valid_upgradable_version = list(version_actions.keys())[0]
    if version != valid_upgradable_version:
        raise ValueError(f"Version {version} is not the next upgrade. Current database version is {current_db_version}. Use version {valid_upgradable_version} instead.")
    return {version: version_actions[version]}