# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
from logging import getLogger
from logging.config import fileConfig

import ahjo.scripts.master_actions
from ahjo.action import execute_action, list_actions
from ahjo.operation_manager import format_message

# load logging config
fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')


logger.info('------')
if os.path.exists('ahjo_actions.py') or os.path.exists('./ahjo_actions'):
    logger.debug(format_message('ahjo_actions found'))
    try:
        sys.path.append(os.getcwd())
        import ahjo_actions
        logger.info(format_message('Succesfully loaded ahjo_actions'))
    except:
        logger.exception(format_message('Error while loading ahjo_actions'))
        raise
else:
    logger.info(format_message('ahjo_actions not found'))


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
        kwargs = {}
        if len(args.files) > 0 : kwargs['files'] = args.files
        if len(args.object_type) > 0 : kwargs['object_type'] = args.object_type
        execute_action(
            *[args.action, args.config_filename],
            **kwargs
        )

if __name__ == '__main__':
    main()
