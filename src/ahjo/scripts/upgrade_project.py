# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""
Ahjo upgrade-project command entrypoint.
"""

import argparse
import os
import sys
from ahjo.operations.general.upgrade import AhjoUpgrade
from ahjo.operations.tsql.db_info import display_db_info
from ahjo.database_utilities.sqla_utilities import test_connection
from ahjo.context import Context
from ahjo.logging import setup_ahjo_logger
from ahjo.config import Config

info_msg = "Ahjo upgrade-project"
line = "-" * len(info_msg)
print(line)
print(info_msg)
print(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config_filename", help="Configuration filename.", type=str, nargs="?"
    )
    parser.add_argument(
        "-v", "--version", type=str, help="Version to upgrade to.", required=False
    )
    parser.add_argument(
        "-ni",
        "--non-interactive",
        action="store_true",
        help="Optional parameter to run ahjo in a non-interactive mode",
        required=False,
    )
    parser.add_argument(
        "-p",
        "--plot",
        action="store_true",
        help="Plot the database schema.",
        required=False,
        default=False,
    )
    parser.add_argument(
        "-d",
        "--project-dir",
        help=(
            "Path to the project directory. Ahjo will change its working "
            "directory to this path before running. If omitted, the project "
            "directory is inferred from the config file location."
        ),
        type=str,
        default=None,
        required=False,
    )
    args = parser.parse_args()
    args_dict = {k: v for k, v in args._get_kwargs()}

    config_filename = Config.get_config_path(args.config_filename)

    # Resolve the config file path against the original working directory
    # and optionally change into the project directory, so that actions can
    # use relative paths like "./database/..." regardless of where ahjo was
    # invoked from.
    if config_filename is not None and not os.path.isabs(config_filename):
        config_filename = os.path.abspath(config_filename)

    project_dir = args.project_dir
    if project_dir is None and config_filename is not None:
        project_dir = os.path.dirname(config_filename)

    if project_dir:
        if not os.path.isdir(project_dir):
            print(f"Project directory not found: {project_dir}")
            sys.exit(1)
        os.chdir(project_dir)

    try:
        context = Context(config_filename, command_line_args=args_dict)
    except Exception as e:
        print(str(e))
        sys.exit(1)

    context.set_enable_transaction(False)

    if context.configuration.get("connect_resiliently", True):
        test_connection(
            engine=context.get_engine(),
            retry_attempts=context.configuration.get("connect_retry_count", 20),
            retry_interval=context.configuration.get("connect_retry_interval", 10),
        )

    # Setup logger
    enable_db_logging = context.configuration.get("enable_database_logging", False)
    try:
        logger = setup_ahjo_logger(
            enable_database_log=enable_db_logging,
            enable_windows_event_log=context.configuration.get(
                "windows_event_log", False
            ),
            enable_sqlalchemy_log=context.configuration.get(
                "enable_sqlalchemy_logging", False
            ),
            context=context,
        )
    except Exception as e:
        print(f"Error setting up logger: {str(e)}")
        sys.exit(1)

    # Display database collation
    if context.configuration.get("display_db_info", True):
        display_db_info(context)

    ahjo_upgrade = AhjoUpgrade(
        config_filename=config_filename,
        context=context,
        version=args.version,
        skip_confirmation=args.non_interactive,
    )
    upgrade_succeeded = ahjo_upgrade.upgrade()

    if enable_db_logging:

        if not upgrade_succeeded:
            context.connection = None
            context.engine = None
            context.set_connectable("engine")

        for handler in logger.handlers:
            if handler.name == "handler_database":
                handler.flush()
                break

    sys.exit(0) if upgrade_succeeded else sys.exit(1)


if __name__ == "__main__":
    main()
