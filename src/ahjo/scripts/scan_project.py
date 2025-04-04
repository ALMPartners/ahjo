# Ahjo - Database deployment framework
#
# Copyright 2019 - 2025 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""
Ahjo scan command entrypoint.
"""
import argparse
import sys
from ahjo.operations.general.scan import AhjoScan
from ahjo.interface_methods import load_yaml_conf
from ahjo.logging import setup_ahjo_logger

logger = setup_ahjo_logger(enable_database_log=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r",
        "--search-rules",
        required=False,
        help="Path to ahjo scan rules config file.",
        default="ahjo_scan_rules.yaml",
    )
    parser.add_argument(
        "-ig",
        "--ignore-config",
        required=False,
        help="Path to ahjo scan ignore config file.",
        default="ahjo_scan_ignore.yaml",
    )
    parser.add_argument(
        "-st",
        "--stage",
        action="store_true",
        required=False,
        help="Scan files in git staging area instead of working directory.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        required=False,
        help="Hide additional status messages and show only the scan matches (if found). This option is used by the pre-commit hook.",
    )
    parser.add_argument(
        "-in",
        "--init",
        action="store_true",
        required=False,
        help="Initialize config files for scan rules and ignored scan results.",
    )
    parser.add_argument(
        "-ai",
        "--add-results-to-ignore",
        action="store_true",
        required=False,
        help="Add found scan results to ignore config file.",
        default=False,
    )
    args = parser.parse_args()
    quiet_mode = args.quiet
    ignore_config_path = args.ignore_config
    rules_config_path = args.search_rules
    scan_config = load_yaml_conf(rules_config_path)

    ahjo_scan = AhjoScan(
        scan_staging_area=True if args.stage else False,
        search_rules=scan_config,
        log_additional_info=False if quiet_mode else True,
        ignore_config_path=ignore_config_path,
        scan_rules_file=rules_config_path,
        add_results_to_ignore=args.add_results_to_ignore,
    )

    if args.init:
        ahjo_scan.initialize_scan_config()
        sys.exit(0)

    if not scan_config:
        logger.error("Failed to load scan rules.")
        sys.exit(1)

    if not quiet_mode:
        logger.info("Scanning files...")

    matches = ahjo_scan.scan_project()

    sys.exit(1) if (len(matches) > 0 if matches else False) else sys.exit(0)


if __name__ == "__main__":
    main()
