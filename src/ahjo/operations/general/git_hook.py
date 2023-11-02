# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

""" Module for Git hook operations. """
import os
from logging import getLogger
from ahjo.operations.general.git_version import get_git_hooks_path
from ahjo.context import AHJO_PATH

logger = getLogger("ahjo")


def install_precommit_scan():
    """ Adds pre-commit scan hook to core.hooksPath. Requires git version 2.9 or newer. """

    # Get the path to the git hooks directory
    git_hooks_path = get_git_hooks_path()
    logger.info("Installing pre-commit hook for ahjo scan.")
    if not os.path.exists(git_hooks_path):
        logger.error(
            f"Directory {git_hooks_path} does not exist. Looks like this is not a Git repository. Aborting."
        )
        return
    
    # Check if pre-commit hook already exists
    precommit_hook_path = os.path.join(git_hooks_path, "pre-commit")
    if os.path.exists(precommit_hook_path):
        logger.warning(f"File {precommit_hook_path} already exists.")
        overwrite = input("Do you want to overwrite the file? (y/n) ")
        if overwrite.lower() != "y":
            logger.info("Aborting.")
            return
    
    # Copy the pre-commit hook from resources/files/git_hooks/pre-commit to the git hooks directory
    hook_script_source_file = os.path.join(AHJO_PATH, "resources/files/git_hooks/pre-commit")
    logger.info(f"Installing pre-commit hook in {precommit_hook_path}")
    try:
        with open(hook_script_source_file, "r", encoding="utf-8") as hook_script:
            precommit_hook_content = hook_script.read()
            with open(precommit_hook_path, "w", encoding="utf-8") as precommit_hook:
                precommit_hook.write(precommit_hook_content)
    except Exception as err:
        logger.error(f"Failed to install pre-commit hook: {err}")
        return
    logger.info(f"Pre-commit hook installed in {precommit_hook_path}")