# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import ahjo.scripts.master_actions

from logging import getLogger
from logging.config import fileConfig
from ahjo.action import execute_action, list_actions, import_actions
from ahjo.context import get_config_path, config_is_valid

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

info_msg = f"    Ahjo - Database deployment framework    "
line = "-" * len(info_msg)
print(line)
print(info_msg)
print(line)

import_actions()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("action", help="Action to execute", type=str)
    parser.add_argument("config_filename", help="Configuration filename", type=str, nargs='?')
    parser.add_argument('--files', nargs='*', default=[], help='Files')
    parser.add_argument('--object_type', nargs=1, default=[], help='Object type', choices=['view', 'procedure', 'function', 'assembly'])
    parser.add_argument('-ni', '--non-interactive', action='store_true', help='Optional parameter to run ahjo in a non-interactive mode', required=False)
    args = parser.parse_args()
    logger.debug(f'Action:  {args.action}')
    logger.debug(f'Config file:  {args.config_filename}')
    logger.debug(f'File(s):  {args.files}')
    logger.debug(f'Object type:  {args.object_type}')

    if args.action == 'list':
        list_actions()
    else:

        config_path = get_config_path(args.config_filename)
        non_interactive = args.non_interactive
        if not config_is_valid(config_path, non_interactive = non_interactive):
            return

        kwargs = {"load_collation": True}
        if len(args.files) > 0 : kwargs['files'] = args.files
        if len(args.object_type) > 0 : kwargs['object_type'] = args.object_type[0]
        if non_interactive : kwargs['skip_confirmation'] = True
        execute_action(
            *[args.action, config_path],
            **kwargs
        )

if __name__ == '__main__':
    main()
