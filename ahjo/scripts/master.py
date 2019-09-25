# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
from logging import getLogger
from logging.config import fileConfig

import ahjo.scripts.master_actions
from ahjo.action import execute_action

# load logging config
fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo.complete')

try:
    sys.path.append(os.getcwd())
    import ahjo_actions
    logger.info('Succesfully loaded ahjo_actions.py')
except ImportError:
    logger.error('Failed to load ahjo_actions.py')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", help="Action to execute", type=str)
    parser.add_argument("config_filename", help="Configuration filename", type=str)
    args = parser.parse_args()
    logger.info(f'Action:  {args.action}')
    logger.info(f'Config file:  {args.config_filename}')
    execute_action(args.action, args.config_filename)

if __name__ == '__main__':
    main()
