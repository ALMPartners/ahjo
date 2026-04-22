# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Ahjo project initialization command entrypoint."""
import argparse
import os
import sys
from os import getcwd
from ahjo.interface_methods import are_you_sure, remove_special_chars
from ahjo.operations import create_new_project
from ahjo.logging import setup_ahjo_logger

setup_ahjo_logger(enable_database_log=False)


def main():

    parser = argparse.ArgumentParser(
        description="Ahjo project initialization command."
    )
    parser.add_argument(
        "-d",
        "--project-dir",
        required=False,
        default=None,
        help=(
            "Path to the directory where the new project will be created. "
            "If omitted, the current working directory is used."
        ),
    )
    args = parser.parse_args()

    init_location = args.project_dir if args.project_dir else getcwd()
    init_location = os.path.abspath(init_location)

    if not os.path.isdir(init_location):
        print(f"Project directory not found: {init_location}")
        sys.exit(1)

    print("This is Ahjo project initialization command.")

    project_name_raw = input("Enter project name: ")
    project_name = remove_special_chars(project_name_raw)

    project_config_format = (
        input(
            "Select configuration file format (yaml/json/jsonc). Leave empty for jsonc: "
        )
        .lower()
        .strip()
    )
    project_config_format = (
        "jsonc" if project_config_format == "" else project_config_format
    )
    if project_config_format not in ["yaml", "json", "jsonc"]:
        print("Invalid configuration file format. Exiting...")
        sys.exit(1)

    if are_you_sure(
        f"You are about to initialize a new project {project_name} to location {init_location}"
    ):
        create_new_project(
            project_name,
            init_location,
            f"Ahjo - Creating new project {project_name}",
            project_config_format=project_config_format,
        )


if __name__ == "__main__":
    main()
