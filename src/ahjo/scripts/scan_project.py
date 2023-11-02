# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Ahjo scan command entrypoint.
'''
import argparse
import os
import sys
import ahjo
from logging import getLogger
from logging.config import fileConfig
from ahjo.operations.general.scan import scan_project, SCAN_RULES_WHITELIST

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', nargs='*', default=[], help='Files')
    parser.add_argument("-st", "--stage", action="store_true", required=False, help="Scan files in git staging area instead of working directory")
    parser.add_argument("-sr", "--search-rules", help="Search rules for ahjo scan action", nargs="*")
    args = parser.parse_args()

    return scan_project(
        filepaths_to_scan = args.files if len(args.files) > 0 else ["^database/"],
        scan_staging_area = True if args.stage else False,
        search_rules = args.search_rules if args.search_rules and len(args.search_rules) > 0 else SCAN_RULES_WHITELIST,
    )

if __name__ == '__main__':
    matches = main()
    if len(matches) > 0: 
        sys.exit(1)
    sys.exit(0)
