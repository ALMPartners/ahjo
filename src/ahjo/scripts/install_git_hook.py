# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Ahjo scan command entrypoint.
'''
import argparse
import os
import ahjo
from ahjo.operations.general.git_hook import install_precommit_scan
from logging import getLogger
from logging.config import fileConfig

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--search-rules", required=False, help="Path to ahjo scan rules config file.")
    parser.add_argument("-ig", "--ignore-config", required=False, help="Path to ahjo scan ignore config file.")
    args = parser.parse_args()
    install_precommit_scan(scan_rules_path = args.search_rules, ignore_file_path = args.ignore_config)

if __name__ == '__main__':
    main()
