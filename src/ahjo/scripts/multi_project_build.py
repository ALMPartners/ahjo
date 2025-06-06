# Ahjo - Database deployment framework
#
# Copyright 2019 - 2025 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""
Ahjo multi-project-build command entrypoint.
"""

import argparse
from ahjo.operations.general.multi_project_build import run_multi_project_build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config_filename", help="Configuration filename", type=str, nargs="?"
    )
    parser.add_argument(
        "-c",
        "--confirm",
        action="store_true",
        help="Ask for confirmation for ahjo actions.",
    )
    args = parser.parse_args()

    info_msg = "Ahjo multi-project build"
    line = "-" * len(info_msg)
    print(line)
    print(info_msg)
    print(line)

    run_multi_project_build(args.config_filename, not args.confirm)


if __name__ == "__main__":
    main()
