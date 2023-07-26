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
from ahjo.scripts.utils import get_config_path

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

info_msg = "    Ahjo - Database deployment framework    "
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
    args = parser.parse_args()
    logger.debug(f'Action:  {args.action}')
    logger.debug(f'Config file:  {args.config_filename}')
    logger.debug(f'File(s):  {args.files}')
    logger.debug(f'Object type:  {args.object_type}')

    if args.action == 'list':
        list_actions()
    else:

        config_filename = get_config_path(args.config_filename)
        if config_filename is None:
            logger.error("Error: Configuration filename is required.")
            return

        kwargs = {"load_collation": True}
        if len(args.files) > 0 : kwargs['files'] = args.files
        if len(args.object_type) > 0 : kwargs['object_type'] = args.object_type[0]
        execute_action(
            *[args.action, config_filename],
            **kwargs
        )

if __name__ == '__main__':
    main()
