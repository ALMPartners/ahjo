# Ahjo - Database deployment framework
#
# Copyright 2019 - 2025 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""
Ahjo upgrade-project command entrypoint.
"""

import argparse
import sys
from ahjo.operations.general.upgrade import AhjoUpgrade
from ahjo.operations.tsql.db_info import display_db_info
from ahjo.database_utilities.sqla_utilities import test_connection
from ahjo.context import Context, config_is_valid
from ahjo.logging import setup_ahjo_logger
from ahjo.interface_methods import get_config_path, load_conf

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
    args = parser.parse_args()

    config_filename = get_config_path(args.config_filename)
    config_dict = load_conf(config_filename)
    non_interactive = args.non_interactive
    if not config_is_valid(config_dict, non_interactive=non_interactive):
        sys.exit(1)

    # Create context
    context = Context(config_filename)
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
        skip_confirmation=non_interactive,
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
