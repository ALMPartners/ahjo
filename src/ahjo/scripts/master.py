# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import argparse
import sys
import importlib
import traceback

from ahjo.action import (
    execute_action,
    list_actions,
    import_actions,
    action_affects_db,
    DEFAULT_ACTIONS_SRC,
)
from ahjo.context import config_is_valid, Context
from ahjo.database_utilities.sqla_utilities import test_connection
from ahjo.interface_methods import get_config_path
from ahjo.operations.tsql.db_info import display_db_info
from ahjo.logging import setup_ahjo_logger

try:
    from ahjo.version import version as AHJO_VERSION
except ImportError:
    AHJO_VERSION = "?.?.?"

# Indicator for a frozen executable (e.g. running from an msi installation)
CX_FROZEN_TAG = " (frozen)" if getattr(sys, "frozen", False) else ""


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("action", help="Name of the action to be run.", type=str)
    parser.add_argument(
        "config_filename",
        help="Path to the project-specific config file. The parameter is optional if the config path is defined in environment variable AHJO_CONFIG_PATH.",
        type=str,
        nargs="?",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Display the version of Ahjo.",
        action="version",
        version=f"%(prog)s {AHJO_VERSION}",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=[],
        help="List of files to be used in action.",
        required=False,
    )
    parser.add_argument(
        "--object_type",
        nargs=1,
        default=[],
        help="Type of database object.",
        choices=["view", "procedure", "function", "assembly"],
        required=False,
    )
    parser.add_argument(
        "-ni",
        "--non-interactive",
        action="store_true",
        help="Optional parameter to run ahjo in a non-interactive mode.",
        required=False,
    )
    parser.add_argument(
        "-sm",
        "--skip-metadata-update",
        action="store_true",
        help="Skip updating documented extended properties to database.",
        required=False,
    )
    parser.add_argument(
        "-sg",
        "--skip-git-update",
        action="store_true",
        help="Skip updating current git version to git version table.",
        required=False,
    )
    parser.add_argument(
        "-sa",
        "--skip-alembic-update",
        action="store_true",
        help="Skip running alembic migrations.",
        required=False,
    )

    known_args = parser.parse_known_args()
    args = known_args[0]
    ahjo_action = args.action
    rest_args = known_args[1]
    args_dict = {k: v for k, v in args._get_kwargs()}
    rest_args_dict = {}

    for i in range(len(rest_args)):
        curr_arg = rest_args[i]
        if curr_arg.startswith("--") or curr_arg.startswith("-"):
            key = curr_arg[2:] if curr_arg.startswith("--") else curr_arg[1:]
            rest_args_dict[key] = []
            i += 1
            while (
                i < len(rest_args)
                and not rest_args[i].startswith("-")
                and not rest_args[i].startswith("--")
            ):
                rest_args_dict[key].append(rest_args[i])
                i += 1

    args_dict.update(rest_args_dict)

    info_msg = (
        f"    Ahjo - Database deployment framework v{AHJO_VERSION}{CX_FROZEN_TAG}   "
    )
    line = "-" * len(info_msg)
    print(line)
    print(info_msg)
    print(line)

    config_path = get_config_path(args.config_filename)
    context = Context(config_path, command_line_args=args_dict)
    sql_dialect = context.get_conn_info().get("dialect", "mssql+pyodbc")

    import_actions(
        ahjo_action_files=context.configuration.get(
            "ahjo_action_files", DEFAULT_ACTIONS_SRC
        )
    )

    if ahjo_action == "list":
        list_actions()
        sys.exit(0)

    action_succeeded = False
    non_interactive = args.non_interactive
    enable_db_logging = context.configuration.get("enable_database_logging", False)
    registered_actions = importlib.import_module(
        "ahjo.scripts.master_actions"
    ).registered_actions
    registered_action = registered_actions.get(ahjo_action, None)

    if registered_action is None:
        print(f"Action '{ahjo_action}' not found.")
        sys.exit(1)

    if (
        context.configuration.get("connect_resiliently", True)
        and registered_action.connection_required
    ):
        test_connection(
            engine=context.get_engine(),
            retry_attempts=context.configuration.get("connect_retry_count", 20),
            retry_interval=context.configuration.get("connect_retry_interval", 10),
        )

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
    except Exception as error:
        print(f"Error setting up logger: {str(error)}")
        sys.exit(1)

    if not config_is_valid(config_path, non_interactive=non_interactive):
        sys.exit(1)

    if (
        sql_dialect == "mssql+pyodbc"
        and context.configuration.get("display_db_info", True)
        and action_affects_db(ahjo_action)
    ):
        display_db_info(context)

    kwargs = {"context": context}
    if len(args.files) > 0:
        kwargs["files"] = args.files
    if len(args.object_type) > 0:
        kwargs["object_type"] = args.object_type[0]
    if non_interactive:
        kwargs["skip_confirmation"] = True
    error_msg = None

    try:
        execute_action(*[ahjo_action, config_path], **kwargs)
        action_succeeded = True
    except Exception:
        error_msg = traceback.format_exc()
        if enable_db_logging:
            context.connection = None
            context.engine = None
            context.set_connectable("engine")

    if error_msg:
        logger.error(str(error_msg))

    if enable_db_logging:
        for handler in logger.handlers:
            if handler.name == "handler_database":
                handler.flush()
                break

    sys.exit(0) if action_succeeded else sys.exit(1)


if __name__ == "__main__":
    main()
