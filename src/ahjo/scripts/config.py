# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Ahjo config command entrypoint.
'''
import argparse
import os
import ahjo
from logging import getLogger
from logging.config import fileConfig
from ahjo.context import convert_config_to_yaml, convert_config_to_json
from ahjo.interface_methods import load_conf

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--convert-to", "-co",
        help="Convert ahjo config file to another format. Supported formats: yaml, json, jsonc", 
        choices=["yaml", "yml", "json", "jsonc"],
        required=True
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to ahjo config file.",
        required=True
    )
    parser.add_argument(
        "--output", "-o",
        help="Path to output file.",
        required=True
    )

    args = parser.parse_args()
    if load_conf(args.config).get("windows_event_log", False):
        fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger_winLog.ini'))

    if args.convert_to in ["yaml", "yml"]:
        convert_config_to_yaml(
            config_path = args.config,
            output_path = args.output
        )
    if args.convert_to in ["json", "jsonc"]:
        convert_config_to_json(
            config_path = args.config,
            output_path = args.output
        )


if __name__ == '__main__':
    main()