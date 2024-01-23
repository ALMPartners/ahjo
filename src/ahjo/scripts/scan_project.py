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
from ahjo.operations.general.scan import scan_project, DEFAULT_SCAN_RULES
from ahjo.interface_methods import get_config_path, load_yaml_conf

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=False, help="Path to project config file")
    args = parser.parse_args()
    scan_config = load_yaml_conf(args.config if args.config else "ahjo_scan_config.yaml")

    if not scan_config:
        logger.error("Failed to load scan config file.")
        sys.exit(1)

    quiet_mode = scan_config.get("quiet_mode") if scan_config.get("quiet_mode") else True
    search_rules = scan_config.get("search_rules") if scan_config.get("search_rules") else DEFAULT_SCAN_RULES
    scan_stage_only = scan_config.get("scan_stage_only") if scan_config.get("scan_stage_only") else False

    if not quiet_mode:
        logger.info("Scanning files...")

    matches = scan_project(
        scan_staging_area = scan_stage_only,
        search_rules = search_rules,
        log_additional_info = False if quiet_mode else True
    )
    matches_found = len(matches) > 0 if matches else False

    if not quiet_mode:
        if matches_found:
            logger.info("If you want to ignore a match, add it to the ahjo_scan_ignore.yaml file.")
            logger.info("")
        else:
            logger.info("Scan completed. No matches found.")

    if matches_found: 
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()