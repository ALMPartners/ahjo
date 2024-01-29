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
from ahjo.operations.general.scan import scan_project
from ahjo.interface_methods import load_yaml_conf

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--search-rules", required=False, help="Path to ahjo scan rules config file.")
    parser.add_argument("-st", "--stage", action="store_true", required=False, help="Scan files in git staging area instead of working directory.")
    parser.add_argument("-q", "--quiet", action="store_true", required=False, 
        help="Hide additional status messages and show only the scan matches (if found). This option is used by the pre-commit hook."
    )
    args = parser.parse_args()

    quiet_mode = args.quiet
    scan_config = load_yaml_conf(args.search_rules if args.search_rules else "ahjo_scan_rules.yaml")

    if not scan_config:
        logger.error("Failed to load scan rules.")
        sys.exit(1)

    if not quiet_mode:
        logger.info("Scanning files...")

    matches = scan_project(**{
        "scan_staging_area": True if args.stage else False,
        "search_rules": scan_config,
        "log_additional_info": False if quiet_mode else True
    })

    matches_found = len(matches) > 0 if matches else False

    if matches_found:
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()