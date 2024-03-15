# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

""" Module for Git hook operations. """
import os
from logging import getLogger
from ahjo.operations.general.git_version import get_git_hooks_path

logger = getLogger("ahjo")

HOOK_CONTENT = r"""#!/usr/bin/env bash

# A Git pre-commit hook that runs ahjo-scan.exe and prevents commit if scan fails.

green='\033[0;32m'
red='\033[0;31m'
no_color='\033[0m'

echo "Scan check started..."
ahjo-scan.exe --search-rules $search_rules_path --ignore-config $ignore_file_path --stage --quiet
exit_status=$?

if [ $exit_status -eq 1 ]; then
    echo "If you want to ignore the scan results, add matches to ahjo_scan_ignore.yaml. Otherwise fix the issues and try again."
    echo -e "${red}Commit aborted.${no_color}"
    exit 1
elif [ $exit_status -eq 0 ]; then
    echo -e "${green}Scan check passed.${no_color}\n"
    exit 0
else 
    this_file_path=$(realpath $0)
    echo "Scan check failed. Make sure ahjo is installed correctly and try again. If you want to commit without scanning, remove this hook from $this_file_path."
    echo -e "${red}Commit aborted.${no_color}"
    exit 1
fi
"""

def install_precommit_scan():
    """ Adds pre-commit scan hook to core.hooksPath. Requires git version 2.9 or newer. """

    # Get the path to the git hooks directory
    git_hooks_path = get_git_hooks_path()
    logger.info("Installing pre-commit hook for ahjo scan.")

    if not os.path.exists(git_hooks_path):
        logger.info(
            f"Directory {git_hooks_path} does not exist. Do you want to create it?"
        )
        create_hook_dir = input("(y/n): ")
        if create_hook_dir.lower() == "y":
            try:
                os.makedirs(git_hooks_path)
            except Exception as err:
                logger.error(f"Failed to create directory {git_hooks_path}: {err}")
                return
        else:
            logger.info("Aborting.")
            return
    
    # Check if pre-commit hook already exists
    precommit_hook_path = os.path.join(git_hooks_path, "pre-commit").replace("\\", "/")
    if os.path.exists(precommit_hook_path):
        logger.warning(f"File {precommit_hook_path} already exists.")
        overwrite = input("Do you want to overwrite the file? (y/n) ")
        if overwrite.lower() != "y":
            logger.info("Aborting.")
            return
    
    # Ask path to the scan rules file (default is .ahjo_scan_rules.yaml)
    logger.info("Enter the path to the scan rules file (default value of .ahjo_scan_rules.yaml will be used if left empty).")
    scan_rules_path = input("Scan rules file path: ").replace("\\", "/")
    if not scan_rules_path: 
        scan_rules_path = "ahjo_scan_rules.yaml"

    # Ask path to the scan ignore file (default is .ahjo_scan_ignore.yaml)
    logger.info("Enter the path to the scan ignore file (default value of .ahjo_scan_ignore.yaml will be used if left empty).")
    scan_ignore_path = input("Scan ignore file path: ").replace("\\", "/")
    if not scan_ignore_path:
        scan_ignore_path = "ahjo_scan_ignore.yaml"

    # Create the pre-commit hook script
    try:
        with open(precommit_hook_path, "w", encoding="utf-8") as precommit_hook:
            precommit_hook.write(
                HOOK_CONTENT.replace(
                    "$search_rules_path", scan_rules_path
                ).replace(
                    "$ignore_file_path", scan_ignore_path
                )    
            )
    except Exception as err:
        logger.error(f"Failed to install pre-commit hook: {err}")
        return
    
    logger.info(f"Pre-commit hook installed in {precommit_hook_path}")