# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import copy
from logging import getLogger
from subprocess import run
from ahjo.interface_methods import load_json_conf, are_you_sure
from ahjo.database_utilities import create_conn_info, create_sqlalchemy_url, create_sqlalchemy_engine
from ahjo.operations.general.git_version import _get_all_tags, _get_git_version, _get_git_commit_info, _get_previous_tag
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

        if upgrade_actions is None:
            raise Exception("Upgrade actions not defined.")

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
            if version not in upgrade_actions:
                raise Exception(f"Version {version} actions are not defined in upgrade actions config file.")
            upgradable_versions = list(version_actions.keys())
            if len(upgradable_versions) == 0:
                raise Exception(f"Database is already up to date. Current database version is {current_db_version}.")
            valid_upgradable_version = upgradable_versions[0]
            if version != valid_upgradable_version:
                raise Exception(f"Version {version} is not the next upgrade. Current database version is {current_db_version}. Use version {valid_upgradable_version} instead.")
            version_actions = {version: version_actions[version]}

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
            run(["git", "checkout", "tags/" + git_version])
            _, checkout_version =_get_git_commit_info()
            if checkout_version != git_version:
                raise Exception(f"Failed to checkout git version: {git_version}")

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


def get_upgradable_version_actions(upgrade_actions: dict, current_db_version: str):
    """Return a dictionary of upgradable versions and their actions."""

    version_actions = copy.deepcopy(upgrade_actions)
    git_tags = _get_all_tags()
    oldest_tag = git_tags[-1]

    # Filter out versions that are older than the current database version
    for version in upgrade_actions:
        if version != oldest_tag:
            previous_version = _get_previous_tag(version)
            if previous_version == current_db_version:
                break
            else:
                version_actions.pop(version)
        else: 
            break

    # Check that the versions in upgrade_actions exist in the repository
    # and they are listed in the correct order
    tag_set = set(git_tags)
    previous_version = None
    for version in version_actions:
        if version not in tag_set:
            raise Exception(f"Git tag {version} does not exist in the repository.")
        if previous_version is not None:
            git_previous_tag = _get_previous_tag(version)
            if previous_version != git_previous_tag:
                raise Exception(f"Git versions in upgrade_actions are not listed in the correct order: {previous_version} -> {version}")
        previous_version = version
        
    return version_actions
