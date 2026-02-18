# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""
Ahjo config command entrypoint.
"""
import argparse
from ahjo.config import Config
from ahjo.logging import setup_ahjo_logger

logger = setup_ahjo_logger(enable_database_log=False)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--convert-to",
        "-co",
        help="Convert ahjo config file to another format. Supported formats: yaml, json, jsonc",
        choices=["yaml", "yml", "json", "jsonc"],
        required=True,
    )
    parser.add_argument(
        "--config", "-c", help="Path to ahjo config file.", required=True
    )
    parser.add_argument("--output", "-o", help="Path to output file.", required=True)

    args = parser.parse_args()
    convert_to = args.convert_to.lower()
    config = Config(config_filename=args.config, validate=False, key="")

    if args.convert_to in ["yaml", "yml"]:
        config.save_config(output_path=args.output, format=convert_to)
    if args.convert_to in ["json", "jsonc"]:
        config.save_config(output_path=args.output, format=convert_to)


if __name__ == "__main__":
    main()
