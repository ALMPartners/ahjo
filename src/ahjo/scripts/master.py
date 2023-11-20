# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
import ahjo.scripts.master_actions

from logging import getLogger
from logging.config import fileConfig
from ahjo.action import execute_action, list_actions, import_actions, DEFAULT_ACTIONS_SRC
from ahjo.context import get_config_path, config_is_valid, Context
from ahjo.operations.general.db_info import print_db_collation

try:
    from ahjo.version import version as AHJO_VERSION
except ImportError:
    AHJO_VERSION = "?.?.?"

# Indicator for a frozen executable (e.g. running from an msi installation)
CX_FROZEN_TAG = " (frozen)" if getattr(sys, "frozen", False) else ""

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

info_msg = f"    Ahjo - Database deployment framework v{AHJO_VERSION}{CX_FROZEN_TAG}   "
line = "-" * len(info_msg)
print(line)
print(info_msg)
print(line)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("action", help="Action to execute", type=str)
    parser.add_argument("config_filename", help="Configuration filename", type=str, nargs='?')
    parser.add_argument('--files', nargs='*', default=[], help='Files')
    parser.add_argument('--object_type', nargs=1, default=[], help='Object type', choices=['view', 'procedure', 'function', 'assembly'])
    parser.add_argument('-ni', '--non-interactive', action='store_true', help='Optional parameter to run ahjo in a non-interactive mode', required=False)
    parser.add_argument("-st", "--stage", action="store_true", required=False, help="Scan files in git staging area instead of working directory")
    parser.add_argument("-sr", "--search-rules", help="Search rules for ahjo scan action", nargs="*")
    args = parser.parse_args()
    logger.debug(f'Action:  {args.action}')
    logger.debug(f'Config file:  {args.config_filename}')
    logger.debug(f'File(s):  {args.files}')
    logger.debug(f'Object type:  {args.object_type}')

    config_path = get_config_path(args.config_filename)
    context = Context(config_path)
    import_actions(
        ahjo_action_files = context.configuration.get("ahjo_action_files", DEFAULT_ACTIONS_SRC)
    )

    if args.action == 'list':
        list_actions()
    else:

        non_interactive = args.non_interactive
        if not config_is_valid(config_path, non_interactive = non_interactive):
            return
        
        if context.configuration.get("display_db_info", True):
            print_db_collation(context)
        # Use different logger configuration for Windows Event Log
        # Preferably we should have only one logger configuration, but this is a workaround for now
        if context.configuration.get("windows_event_log", False):
            fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger_winLog.ini'))

        kwargs = {"context": context}
        if len(args.files) > 0 : kwargs['files'] = args.files
        if len(args.object_type) > 0 : kwargs['object_type'] = args.object_type[0]
        if non_interactive : kwargs['skip_confirmation'] = True
        if args.stage : kwargs['scan_staging_area'] = True
        if args.search_rules: kwargs['search_rules'] = args.search_rules
        execute_action(
            *[args.action, config_path],
            **kwargs
        )

if __name__ == '__main__':
    main()
