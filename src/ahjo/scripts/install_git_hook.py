# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""
Ahjo scan command entrypoint.
"""
import argparse
from ahjo.operations.general.git_hook import install_precommit_scan
from ahjo.logging import setup_ahjo_logger

logger = setup_ahjo_logger(enable_database_log=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r",
        "--search-rules",
        required=False,
        help="Path to ahjo scan rules config file.",
    )
    parser.add_argument(
        "-ig",
        "--ignore-config",
        required=False,
        help="Path to ahjo scan ignore config file.",
    )
    args = parser.parse_args()
    install_precommit_scan(
        scan_rules_path=args.search_rules, ignore_file_path=args.ignore_config
    )


if __name__ == "__main__":
    main()
