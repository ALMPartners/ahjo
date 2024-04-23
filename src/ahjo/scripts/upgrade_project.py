# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Ahjo upgrade-project command entrypoint.
'''

import argparse
import ahjo.scripts.master_actions
import sys
from ahjo.operations.general.upgrade import upgrade
from ahjo.context import config_is_valid
from ahjo.interface_methods import get_config_path, load_conf

info_msg = "Ahjo upgrade-project"
line = "-" * len(info_msg)
print(line)
print(info_msg)
print(line)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_filename", help="Configuration filename.", type=str, nargs="?")
    parser.add_argument("-v", "--version", type=str, help="Version to upgrade to.", required=False)
    parser.add_argument('-ni', '--non-interactive', action='store_true', help='Optional parameter to run ahjo in a non-interactive mode', required=False)
    args = parser.parse_args()

    config_filename = get_config_path(args.config_filename)
    config_dict = load_conf(config_filename)
    non_interactive = args.non_interactive
    if not config_is_valid(config_dict, non_interactive = non_interactive):
        sys.exit(1)

    upgrade_succeeded = upgrade(
        config_filename,
        args.version,
        skip_confirmation = non_interactive
    )
    sys.exit(0) if upgrade_succeeded else sys.exit(1)

    
if __name__ == '__main__':
    main()
