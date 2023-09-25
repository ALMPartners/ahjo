# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Ahjo upgrade-project command entrypoint.
'''

import argparse
import os
import ahjo.scripts.master_actions
from logging import getLogger
from logging.config import fileConfig
from ahjo.operations.general.upgrade import upgrade
from ahjo.scripts.utils import get_config_path


# load logging config
fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

info_msg = "Ahjo upgrade-project"
line = "-" * len(info_msg)
logger.info(line)
logger.info(info_msg)
logger.info(line)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_filename", help="Configuration filename.", type=str, nargs="?")
    parser.add_argument("-v", "--version", type=str, help="Version to upgrade to.", required=False)
    args = parser.parse_args()

    config_filename = get_config_path(args.config_filename)

    if config_filename is None:
        logger.error("Error: Configuration filename is required.")
        return
    
    upgrade(
        config_filename,
        args.version
    )

    
if __name__ == '__main__':
    main()
