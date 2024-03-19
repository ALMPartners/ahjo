# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
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
from ahjo.operations.general.scan import scan_project, initialize_scan_config
from ahjo.interface_methods import load_yaml_conf

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--search-rules", required=False, help="Path to ahjo scan rules config file.", default="ahjo_scan_rules.yaml")
    parser.add_argument("-ig", "--ignore-config", required=False, help="Path to ahjo scan ignore config file.", default="ahjo_scan_ignore.yaml")
    parser.add_argument("-st", "--stage", action="store_true", required=False, help="Scan files in git staging area instead of working directory.")
    parser.add_argument("-q", "--quiet", action="store_true", required=False, 
        help="Hide additional status messages and show only the scan matches (if found). This option is used by the pre-commit hook."
    )
    parser.add_argument("-in", "--init", action="store_true", required=False, help="Initialize config files for scan rules and ignored scan results.")
    args = parser.parse_args()
    quiet_mode = args.quiet
    ignore_config_path = args.ignore_config
    rules_config_path = args.search_rules

    if args.init:
        initialize_scan_config(scan_ignore_file = ignore_config_path, scan_rules_file = rules_config_path)
        sys.exit(0)

    scan_config = load_yaml_conf(rules_config_path)

    if not scan_config:
        logger.error("Failed to load scan rules.")
        sys.exit(1)

    if not quiet_mode:
        logger.info("Scanning files...")

    matches = scan_project(**{
        "scan_staging_area": True if args.stage else False,
        "search_rules": scan_config,
        "log_additional_info": False if quiet_mode else True,
        "ignore_config_path": ignore_config_path
    })

    sys.exit(1) if (len(matches) > 0 if matches else False) else sys.exit(0)

if __name__ == '__main__':
    main()