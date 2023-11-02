# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Ahjo scan command entrypoint.
'''
import argparse
import os
import ahjo
from ahjo.operations.general.git_hook import install_precommit_scan
from logging import getLogger
from logging.config import fileConfig

fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
logger = getLogger('ahjo')

def main():
    # Currently only scan script is supported, no need to parse arguments
    #parser = argparse.ArgumentParser()
    #parser.add_argument("--script", choices=["scan"], help="Git hook script name", default="scan")
    #args = parser.parse_args()
    install_precommit_scan()

if __name__ == '__main__':
    main()
