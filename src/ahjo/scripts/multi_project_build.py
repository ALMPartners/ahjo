# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021, 2022 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Ahjo multi-project-build command entrypoint.
'''

import argparse
from ahjo.operations.general.multi_project_build import run_multi_project_build

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_filename", help="Configuration filename", type=str, nargs="?")

    info_msg = "This is Ahjo multi-project build command."
    line = "-" * len(info_msg)
    print(line)
    print('This is Ahjo multi-project build command.')
    print(line)

    run_multi_project_build(
        parser.parse_args().config_filename
    )

if __name__ == '__main__':
    main()
