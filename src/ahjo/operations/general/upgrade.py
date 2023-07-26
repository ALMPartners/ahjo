# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import copy
from logging import getLogger
from ahjo.interface_methods import load_json_conf, are_you_sure
from ahjo.database_utilities import create_conn_info, create_sqlalchemy_url, create_sqlalchemy_engine
from ahjo.operations.general.git_version import _get_all_tags, _get_git_version, _get_previous_tag, _checkout_tag
from ahjo.scripts.utils import display_collation_info
from ahjo.action import execute_action


logger = getLogger('ahjo')


def upgrade(config_filename: str, version: str = None):
    """Upgrade database with upgrade actions."""
    try:

        # Load settings
        config = load_json_conf(config_filename)
        upgrade_actions = load_json_conf(config.get("upgrade_actions_file", "./upgrade_actions.jsonc"))
        conn_info = create_conn_info(config)
        git_table_schema = config.get('git_table_schema', 'dbo')
        git_table = config.get('git_table', 'git_version')

        # Create sqlalchemy engine
        engine = create_sqlalchemy_engine(
            create_sqlalchemy_url(conn_info), 
            token = conn_info.get("token")
        )

        # Get the current git commit from database
        _, _, current_db_version = _get_git_version(engine, git_table_schema, git_table)

        # Select versions to be deployed
        version_actions = get_upgradable_version_actions(upgrade_actions, current_db_version)

        # Validate user input
        if version is not None:
            version_actions = validate_version(version, version_actions, upgrade_actions, current_db_version)

        # Display database collation
        display_collation_info(
            engine, 
            config.get("target_database_name"),
            sql_dialect = config.get("sql_dialect", "mssql+pyodbc"),
            config_collation_name = config.get("database_collation", "Latin1_General_CS_AS"),
            config_catalog_collation_type_desc = config.get("catalog_collation_type_desc", "DATABASE_DEFAULT")
        )
        logger.info('------')

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
                    *[action_name, config_filename, engine, True],
                    **kwargs
                )

            # Check that the database version was updated
            _, _, db_version = _get_git_version(engine, git_table_schema, git_table)
            if db_version != git_version:
                raise Exception(f"Database (version {db_version}) was not updated to match the git version: {git_version}")
            
            logger.info(f"Database successfully upgraded to version {db_version}")
            logger.info("------")
            
    except Exception as error:
        # Todo: Add rollback?
        logger.error('Error during ahjo project upgrade:')
        logger.error(error)


def get_upgradable_version_actions(upgrade_actions: dict, current_version: str):
    """Return a dictionary of upgradable versions and their actions."""

    if upgrade_actions is None:
        raise ValueError("Upgrade actions not defined.")

    version_actions = copy.deepcopy(upgrade_actions)
    git_tags = _get_all_tags()
    oldest_tag = git_tags[-1]
    tag_set = set(git_tags)

    if current_version not in tag_set:
        raise ValueError(f"Current version {current_version} does not exist in the repository.")

    # Filter out versions that are older than the current database version
    for version in upgrade_actions:
        if version != oldest_tag:
            previous_version = _get_previous_tag(version)
            if previous_version == current_version:
                break
            else:
                version_actions.pop(version)
        else: 
            break

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

    if len(list(version_actions.keys())) == 0:
        raise ValueError(f"Database is already up to date. Current database version is {current_version}.")
        
    return version_actions


def validate_version(version: str, version_actions: dict, upgrade_actions: dict, current_db_version: str):
    """Validate that the version is upgradable."""
    if version not in upgrade_actions:
        raise ValueError(f"Version {version} actions are not defined in upgrade actions config file.")
    valid_upgradable_version = list(version_actions.keys())[0]
    if version != valid_upgradable_version:
        raise ValueError(f"Version {version} is not the next upgrade. Current database version is {current_db_version}. Use version {valid_upgradable_version} instead.")
    return {version: version_actions[version]}