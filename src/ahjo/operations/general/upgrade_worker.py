# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Worker process for AhjoUpgrade.

Runs a single version's upgrade actions in an isolated Python process.
This prevents self-modifying code issues that occur when git checkout
changes files on disk while the parent process is running.

Usage (called by AhjoUpgrade, not intended for direct use):
    python -m ahjo.operations.general.upgrade_worker \
        --config <config_file> \
        --version <git_version> \
        --actions <json_actions> \
        --git-table-schema <schema> \
        --git-table <table> \
        [--enable-db-logging]
"""

import argparse
import json
import os
import sys

sys.path.append(os.getcwd())


def main():
    parser = argparse.ArgumentParser(
        description="Ahjo upgrade worker - runs upgrade actions for a single version."
    )
    parser.add_argument(
        "--config", required=True, help="Path to the configuration file."
    )
    parser.add_argument(
        "--version", required=True, help="Git version (tag) to upgrade to."
    )
    parser.add_argument(
        "--actions", required=True, help="JSON-encoded list of actions to execute."
    )
    parser.add_argument(
        "--git-table-schema",
        required=True,
        help="Schema of the git version table.",
    )
    parser.add_argument(
        "--git-table", required=True, help="Name of the git version table."
    )
    parser.add_argument(
        "--enable-db-logging",
        action="store_true",
        default=False,
        help="Enable database logging.",
    )
    args = parser.parse_args()

    config_filename = args.config
    git_version = args.version
    actions = json.loads(args.actions)
    git_table_schema = args.git_table_schema
    git_table = args.git_table
    enable_db_logging = args.enable_db_logging

    # Import ahjo modules fresh in this process
    from logging import getLogger

    from ahjo.action import DEFAULT_ACTIONS_SRC, execute_action, import_actions
    from ahjo.config import Config
    from ahjo.context import Context
    from ahjo.logging import setup_ahjo_logger
    from ahjo.operations.general.git_version import _checkout_tag, _get_git_version

    logger = getLogger("ahjo")

    try:
        # Checkout the target git version
        _checkout_tag(git_version)

        # Load config from the checked-out version's files
        config = Config(config_filename=config_filename, validate=True).as_dict()

        # Create a fresh context (new DB connection)
        context = Context(config_filename)
        context.set_enable_transaction(False)

        # Setup logger
        try:
            setup_ahjo_logger(
                enable_database_log=enable_db_logging,
                enable_windows_event_log=config.get("windows_event_log", False),
                enable_sqlalchemy_log=config.get("enable_sqlalchemy_logging", False),
                context=context,
            )
        except Exception as log_error:
            # Log setup failure is non-critical; continue with basic logging
            print(f"Warning: Logger setup failed: {log_error}", file=sys.stderr)

        # Update version info in the database logger
        if enable_db_logging:
            for handler in logger.handlers:
                if handler.name == "handler_database":
                    handler.flush()
                    handler.db_logger.set_git_commit(git_version)
                    break

        logger.info(f"Starting upgrade worker for version {git_version}")

        # Import actions from the checked-out version
        import_actions(
            ahjo_action_files=config.get("ahjo_action_files", DEFAULT_ACTIONS_SRC),
            reload_module=True,
        )

        # Execute each action
        for action in actions:
            kwargs = {}
            if isinstance(action, list):
                action_name = action[0]
                parameters = action[1]
                for arg in parameters:
                    kwargs[arg] = parameters[arg]
            else:
                action_name = action

            execute_action(
                *[action_name, config_filename, None, True, context],
                **kwargs,
            )

        # Verify that the database version was updated
        _, _, db_version = _get_git_version(
            context.get_connectable(), git_table_schema, git_table
        )
        if db_version != git_version:
            raise Exception(
                f"Database (version {db_version}) was not updated to match the git version: {git_version}"
            )

        logger.info(f"Successfully upgraded to version {git_version}")

    except Exception as error:
        logger.error(f"Upgrade worker failed for version {git_version}: {error}")
        sys.exit(1)

    # Flush database log handler before exiting
    if enable_db_logging:
        for handler in logger.handlers:
            if handler.name == "handler_database":
                handler.flush()
                break

    sys.exit(0)


if __name__ == "__main__":
    main()
